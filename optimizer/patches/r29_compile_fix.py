from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
path = root / 'src' / 'MerzoOptimizer.Windows' / 'Cleanup' / 'WindowsCleanupService.cs'
s = path.read_text(encoding='utf-8-sig')
marker = '    private async Task<CleanupRunResult> CleanWithoutBackupAsync('
if marker not in s:
    insert_anchor = '    private static async Task RestoreDeletedSubsetAsync('
    if insert_anchor not in s:
        raise SystemExit('R29 cleanup insert anchor missing')
    direct = r'''    private async Task<CleanupRunResult> CleanWithoutBackupAsync(CleanupCategorySnapshot category, FileInfo[] candidates, CancellationToken cancellationToken)
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

'''
    s = s.replace(insert_anchor, direct + insert_anchor, 1)
    path.write_text(s, encoding='utf-8')

# MerzoOperationGuard uses explicit file-system APIs. The WPF app project does not
# import System.IO implicitly in generated temporary builds, so make it explicit.
guard = root / 'src' / 'MerzoOptimizer.App' / 'Operations' / 'MerzoOperationGuard.cs'
g = guard.read_text(encoding='utf-8-sig')
if 'using System.IO;' not in g:
    g = 'using System.IO;\n' + g
guard.write_text(g, encoding='utf-8')

final = path.read_text(encoding='utf-8')
if marker not in final:
    raise SystemExit('R29 CleanWithoutBackupAsync definition still missing')
if 'using System.IO;' not in guard.read_text(encoding='utf-8'):
    raise SystemExit('R29 operation guard System.IO import missing')
print('R29 compile fixes: OK')
