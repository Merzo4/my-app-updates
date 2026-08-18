using System.IO.Compression;
using MerzoOptimizer.Core.Cleanup;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Windows.SystemInfo;

namespace MerzoOptimizer.Windows.Cleanup;

public sealed class WindowsCleanupService : ICleanupService
{
    private static readonly TimeSpan MinimumAge = TimeSpan.FromHours(24);
    private readonly ISnapshotService _snapshots;
    private readonly IAuditLogger _logger;
    private readonly string _backupDirectory;

    public WindowsCleanupService(ISnapshotService snapshots, IAuditLogger logger, string? backupDirectory = null)
    {
        _snapshots = snapshots;
        _logger = logger;
        _backupDirectory = backupDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MerzoWindowsOptimizer",
            "cleanup-backups");
        Directory.CreateDirectory(_backupDirectory);
    }

    public Task<IReadOnlyList<CleanupCategorySnapshot>> ScanAsync(CancellationToken cancellationToken = default)
    {
        var categories = BuildCategories();
        var result = new List<CleanupCategorySnapshot>(categories.Count);

        foreach (var category in categories)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var files = EnumerateEligibleFiles(category.RootPath, cancellationToken).ToArray();
            result.Add(category with
            {
                EligibleFileCount = files.Length,
                EligibleBytes = files.Sum(static f => TryGetLength(f)),
                CanClean = files.Length > 0 && (!category.RequiresAdmin || AdminService.IsAdministrator())
            });
        }

        return Task.FromResult<IReadOnlyList<CleanupCategorySnapshot>>(result);
    }

    public async Task<CleanupRunResult> CleanAsync(string categoryId, bool createBackup = true, CancellationToken cancellationToken = default)
    {
        var category = BuildCategories().FirstOrDefault(c => string.Equals(c.Id, categoryId, StringComparison.OrdinalIgnoreCase));
        if (category is null)
        {
            return new CleanupRunResult { Success = false, Changed = false, Message = "Категория очистки не найдена." };
        }

        if (category.RequiresAdmin && !AdminService.IsAdministrator())
        {
            return new CleanupRunResult { Success = false, Changed = false, Message = "Для этой категории требуются права администратора." };
        }

        var candidates = EnumerateEligibleFiles(category.RootPath, cancellationToken).ToArray();
        if (candidates.Length == 0)
        {
            return new CleanupRunResult { Success = true, Changed = false, Message = "Подходящих временных файлов старше 24 часов не найдено." };
        }

        if (!createBackup)
            return await CleanWithoutBackupAsync(category, candidates, cancellationToken).ConfigureAwait(false);

        var token = Guid.NewGuid().ToString("N");
        var archivePath = Path.Combine(_backupDirectory, $"cleanup-{DateTime.Now:yyyyMMdd-HHmmss}-{token}.zip");
        var archived = new List<CleanupArchiveEntrySnapshot>();
        ChangeSnapshot? snapshot = null;

        try
        {
            using (var archiveStream = new FileStream(archivePath, FileMode.CreateNew, FileAccess.ReadWrite, FileShare.None))
            using (var archive = new ZipArchive(archiveStream, ZipArchiveMode.Create, leaveOpen: false))
            {
                var index = 0;
                foreach (var file in candidates)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    try
                    {
                        var entryName = $"files/{index++:D6}.bin";
                        var entry = archive.CreateEntry(entryName, CompressionLevel.Optimal);
                        using var source = new FileStream(file.FullName, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                        using var target = entry.Open();
                        await source.CopyToAsync(target, cancellationToken).ConfigureAwait(false);
                        archived.Add(new CleanupArchiveEntrySnapshot
                        {
                            OriginalPath = file.FullName,
                            ArchiveEntryName = entryName,
                            OriginalBytes = file.Length
                        });
                    }
                    catch (IOException)
                    {
                        // Locked/volatile temp files are deliberately skipped.
                    }
                    catch (UnauthorizedAccessException)
                    {
                        // Protected temp files are deliberately skipped.
                    }
                }
            }

            if (archived.Count == 0)
            {
                TryDelete(archivePath);
                return new CleanupRunResult { Success = true, Changed = false, Message = "Файлы найдены, но все они заняты или защищены. Ничего не изменено." };
            }

            var originalBytes = archived.Sum(static f => f.OriginalBytes);
            var backupBytes = new FileInfo(archivePath).Length;
            if (backupBytes >= originalBytes)
            {
                TryDelete(archivePath);
                return new CleanupRunResult
                {
                    Success = true,
                    Changed = false,
                    ArchivedFileCount = archived.Count,
                    OriginalBytes = originalBytes,
                    BackupBytes = backupBytes,
                    NetFreedBytes = 0,
                    Message = "Очистка отменена: резервная ZIP-копия не дала экономии места. Исходные файлы не удалялись."
                };
            }

            var cleanupSnapshot = new CleanupArchiveSnapshot
            {
                CategoryId = category.Id,
                CategoryName = category.Name,
                ArchivePath = archivePath,
                Files = archived
            };

            snapshot = await _snapshots.CreateForCleanupAsync(
                $"cleanup.{category.Id}",
                $"Очистка: {category.Name}",
                $"Перед безопасной очисткой {category.Name}",
                cleanupSnapshot,
                cancellationToken).ConfigureAwait(false);

            long deletedBytes = 0;
            var deleted = new List<CleanupArchiveEntrySnapshot>();
            foreach (var item in archived)
            {
                try
                {
                    if (!File.Exists(item.OriginalPath))
                        break;
                    File.Delete(item.OriginalPath);
                    deletedBytes += item.OriginalBytes;
                    deleted.Add(item);
                }
                catch (IOException)
                {
                    break;
                }
                catch (UnauthorizedAccessException)
                {
                    break;
                }
            }

            if (deleted.Count != archived.Count)
            {
                await RestoreDeletedSubsetAsync(archivePath, deleted, CancellationToken.None).ConfigureAwait(false);
                await _snapshots.MarkRestoredAsync(snapshot.Id, DateTimeOffset.Now, CancellationToken.None).ConfigureAwait(false);
                TryDelete(archivePath);

                await _logger.WriteAsync(new AuditLogEntry
                {
                    Category = "Cleanup",
                    Action = $"Очистка {category.Name}",
                    Status = "Rollback",
                    TweakId = $"cleanup.{category.Id}",
                    Details = $"Удаление остановлено после {deleted.Count} из {archived.Count}; удалённые файлы автоматически возвращены. Snapshot {snapshot.Id} помечен восстановленным."
                }, CancellationToken.None).ConfigureAwait(false);

                return new CleanupRunResult
                {
                    Success = true,
                    Changed = false,
                    SnapshotId = snapshot.Id,
                    ArchivedFileCount = archived.Count,
                    OriginalBytes = originalBytes,
                    BackupBytes = backupBytes,
                    NetFreedBytes = 0,
                    Message = "Очистка отменена: один из временных файлов изменился или заблокировался. Уже удалённые файлы автоматически восстановлены."
                };
            }

            var deletedCount = deleted.Count;
            var netFreed = Math.Max(0, deletedBytes - backupBytes);
            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Cleanup",
                Action = $"Очистка {category.Name}",
                Status = "Success",
                TweakId = $"cleanup.{category.Id}",
                OldValue = $"{deletedCount} files / {deletedBytes} bytes",
                NewValue = $"ZIP backup {backupBytes} bytes",
                Details = $"Snapshot {snapshot.Id}; reversible ZIP backup: {archivePath}"
            }, cancellationToken).ConfigureAwait(false);

            return new CleanupRunResult
            {
                Success = true,
                Changed = true,
                SnapshotId = snapshot.Id,
                ArchivedFileCount = deletedCount,
                OriginalBytes = deletedBytes,
                BackupBytes = backupBytes,
                NetFreedBytes = netFreed,
                Message = $"Безопасно очищено файлов: {deletedCount}. Создан ZIP-backup и snapshot {snapshot.Id.ToString("N")[..8]}."
            };
        }
        catch
        {
            if (snapshot is null)
                TryDelete(archivePath);
            throw;
        }
    }

    private async Task<CleanupRunResult> CleanWithoutBackupAsync(CleanupCategorySnapshot category, FileInfo[] candidates, CancellationToken cancellationToken)
    {
        long deletedBytes = 0;
        var deletedCount = 0;
        var skipped = 0;
        foreach (var file in candidates)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                var length = file.Exists ? file.Length : 0;
                if (file.Exists) File.Delete(file.FullName);
                deletedBytes += length;
                deletedCount++;
            }
            catch (IOException) { skipped++; }
            catch (UnauthorizedAccessException) { skipped++; }
        }

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Cleanup",
            Action = $"Очистка без backup: {category.Name}",
            Status = "Success",
            TweakId = $"cleanup.{category.Id}",
            OldValue = $"{deletedCount} files / {deletedBytes} bytes",
            NewValue = "No backup (user choice)",
            Details = $"Irreversible cleanup requested by user; skipped locked/protected: {skipped}."
        }, cancellationToken).ConfigureAwait(false);

        return new CleanupRunResult
        {
            Success = true,
            Changed = deletedCount > 0,
            SnapshotId = null,
            ArchivedFileCount = deletedCount,
            OriginalBytes = deletedBytes,
            BackupBytes = 0,
            NetFreedBytes = deletedBytes,
            Message = deletedCount == 0
                ? $"Ничего не удалено. Занятых/защищённых файлов пропущено: {skipped}."
                : $"Очищено без резервной копии: {deletedCount} файлов, освобождено {deletedBytes} байт. Пропущено: {skipped}."
        };
    }

    private static async Task RestoreDeletedSubsetAsync(
        string archivePath,
        IReadOnlyList<CleanupArchiveEntrySnapshot> deleted,
        CancellationToken cancellationToken)
    {
        if (deleted.Count == 0 || !File.Exists(archivePath))
            return;

        using var archive = ZipFile.OpenRead(archivePath);
        var entries = archive.Entries.ToDictionary(static e => e.FullName, StringComparer.Ordinal);
        foreach (var file in deleted)
        {
            if (File.Exists(file.OriginalPath))
                continue;
            if (!entries.TryGetValue(file.ArchiveEntryName, out var entry))
                continue;

            var parent = Path.GetDirectoryName(file.OriginalPath);
            if (!string.IsNullOrWhiteSpace(parent))
                Directory.CreateDirectory(parent);

            await using var source = entry.Open();
            await using var target = new FileStream(file.OriginalPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            await source.CopyToAsync(target, cancellationToken).ConfigureAwait(false);
        }
    }

    private static IReadOnlyList<CleanupCategorySnapshot> BuildCategories()
    {
        var userTemp = Path.GetTempPath().TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        var windowsTemp = Path.Combine(windows, "Temp");
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var programData = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);

        return
        [
            Category("user_temp", "Временные файлы пользователя", "Файлы из %TEMP%, которые не изменялись более 24 часов. Занятые файлы пропускаются.", userTemp, false),
            Category("windows_temp", "Windows Temp", @"Старые файлы C:\Windows\Temp. Системные блокировки не обходятся.", windowsTemp, true),
            Category("directx_shader_cache", "DirectX Shader Cache", "Старые элементы пользовательского D3DSCache; будут созданы заново при необходимости.", Path.Combine(local, "D3DSCache"), false),
            Category("user_crash_dumps", "Crash Dumps пользователя", "Старые дампы приложений из %LOCALAPPDATA%\\CrashDumps.", Path.Combine(local, "CrashDumps"), false),
            Category("windows_minidumps", "Windows Minidumps", "Старые минидампы Windows; только файлы старше 24 часов и только с backup.", Path.Combine(windows, "Minidump"), true),
            Category("wer_user_archive", "WER пользователя", "Архив старых отчётов Windows Error Reporting текущего пользователя.", Path.Combine(local, "Microsoft", "Windows", "WER", "ReportArchive"), false),
            Category("wer_system_archive", "WER system archive", "Старые системные архивы Windows Error Reporting.", Path.Combine(programData, "Microsoft", "Windows", "WER", "ReportArchive"), true),
            Category("wer_system_queue", "WER system queue", "Старые элементы очереди Windows Error Reporting; только старше 24 часов.", Path.Combine(programData, "Microsoft", "Windows", "WER", "ReportQueue"), true)
        ];
    }

    private static CleanupCategorySnapshot Category(string id, string name, string description, string rootPath, bool requiresAdmin) => new()
    {
        Id = id,
        Name = name,
        Description = description,
        RootPath = rootPath,
        RequiresAdmin = requiresAdmin
    };

    private static IEnumerable<FileInfo> EnumerateEligibleFiles(string rootPath, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(rootPath) || !Directory.Exists(rootPath))
            yield break;

        var cutoffUtc = DateTime.UtcNow - MinimumAge;
        var pending = new Stack<string>();
        pending.Push(rootPath);

        while (pending.Count > 0)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var directory = pending.Pop();

            string[] files;
            try { files = Directory.GetFiles(directory); }
            catch (UnauthorizedAccessException) { continue; }
            catch (IOException) { continue; }

            foreach (var filePath in files)
            {
                cancellationToken.ThrowIfCancellationRequested();
                FileInfo? info = null;
                var eligible = false;
                try
                {
                    info = new FileInfo(filePath);
                    eligible = (info.Attributes & FileAttributes.ReparsePoint) == 0 && info.LastWriteTimeUtc <= cutoffUtc;
                }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }

                if (eligible && info is not null)
                    yield return info;
            }

            string[] directories;
            try { directories = Directory.GetDirectories(directory); }
            catch (UnauthorizedAccessException) { continue; }
            catch (IOException) { continue; }

            foreach (var child in directories)
            {
                try
                {
                    var attributes = File.GetAttributes(child);
                    if ((attributes & FileAttributes.ReparsePoint) == 0)
                        pending.Push(child);
                }
                catch { }
            }
        }
    }

    private static long TryGetLength(FileInfo file)
    {
        try
        {
            file.Refresh();
            return file.Exists ? file.Length : 0L;
        }
        catch (IOException) { return 0L; }
        catch (UnauthorizedAccessException) { return 0L; }
    }

    private static void TryDelete(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); } catch { }
    }
}
