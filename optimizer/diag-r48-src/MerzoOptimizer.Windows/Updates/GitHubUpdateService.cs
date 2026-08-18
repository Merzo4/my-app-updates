using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using MerzoOptimizer.Core.Updates;

namespace MerzoOptimizer.Windows.Updates;

public sealed class GitHubUpdateService : IUpdateService, IDisposable
{
    private const string OfficialOwner = "Merzo4";
    private const string OfficialRepository = "my-app-updates";
    private const string OfficialTagPrefix = "mwo-v";
    private const string OfficialInstallerName = "MerzoWindowsOptimizerSetup-win-x64.exe";
    private const long MaximumInstallerBytes = 512L * 1024L * 1024L;

    private readonly HttpClient _http;
    private readonly string _updateDirectory;
    public UpdateSettings Settings { get; }

    public GitHubUpdateService(string? settingsPath = null, string? updateDirectory = null, HttpMessageHandler? handler = null)
    {
        settingsPath ??= Path.Combine(AppContext.BaseDirectory, "data", "update_settings.json");
        Settings = LoadSettings(settingsPath);
        _updateDirectory = Path.GetFullPath(updateDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MerzoWindowsOptimizer",
            "updates"));
        Directory.CreateDirectory(_updateDirectory);

        _http = handler is null ? new HttpClient() : new HttpClient(handler, disposeHandler: true);
        _http.Timeout = TimeSpan.FromSeconds(45);
        _http.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue("MerzoWindowsOptimizer", GetCurrentVersion()));
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
        _http.DefaultRequestHeaders.Add("X-GitHub-Api-Version", "2022-11-28");
    }

    public async Task<UpdateCheckResult> CheckAsync(CancellationToken cancellationToken = default)
    {
        var current = GetCurrentVersion();
        if (!HasOfficialProductionConfiguration())
        {
            return new UpdateCheckResult
            {
                Success = false,
                Configured = false,
                CurrentVersion = current,
                Message = "Канал обновлений отклонён: Production принимает обновления только из официального Merzo4/my-app-updates."
            };
        }

        try
        {
            var resolved = await ResolveBestReleaseAsync(cancellationToken).ConfigureAwait(false);
            if (resolved.Release is null || resolved.Version is null)
            {
                return new UpdateCheckResult
                {
                    Success = true,
                    Configured = true,
                    CurrentVersion = current,
                    LatestVersion = current,
                    Message = $"Релизы {OfficialTagPrefix}* пока не опубликованы."
                };
            }

            var root = resolved.Release.Value;
            var bestVersion = resolved.Version!;
            var tag = root.GetProperty("tag_name").GetString() ?? string.Empty;
            var releaseName = root.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? tag : tag;
            var body = root.TryGetProperty("body", out var bodyEl) ? bodyEl.GetString() ?? string.Empty : string.Empty;

            JsonElement? selected = null;
            JsonElement? checksum = null;
            if (root.TryGetProperty("assets", out var assets) && assets.ValueKind == JsonValueKind.Array)
            {
                foreach (var asset in assets.EnumerateArray())
                {
                    var name = asset.TryGetProperty("name", out var an) ? an.GetString() ?? string.Empty : string.Empty;
                    if (name.Equals(OfficialInstallerName, StringComparison.Ordinal))
                        selected = asset.Clone();
                    else if (name.Equals(OfficialInstallerName + ".sha256", StringComparison.Ordinal))
                        checksum = asset.Clone();
                }
            }

            if (selected is null || checksum is null)
                return Failure(current, bestVersion, "Release найден, но отсутствует точная пара installer + SHA-256 sidecar. Обновление отклонено.");

            var a = selected.Value;
            var assetName = a.TryGetProperty("name", out var assetNameEl) ? assetNameEl.GetString() ?? string.Empty : string.Empty;
            var assetUrl = a.TryGetProperty("browser_download_url", out var assetUrlEl) ? assetUrlEl.GetString() ?? string.Empty : string.Empty;
            var digest = a.TryGetProperty("digest", out var digestEl) ? digestEl.GetString() ?? string.Empty : string.Empty;
            var size = a.TryGetProperty("size", out var sizeEl) ? sizeEl.GetInt64() : 0L;
            var checksumUrl = checksum.Value.TryGetProperty("browser_download_url", out var checksumUrlEl) ? checksumUrlEl.GetString() ?? string.Empty : string.Empty;

            var digestHex = ExtractSha256Digest(digest);
            if (!assetName.Equals(OfficialInstallerName, StringComparison.Ordinal) ||
                !IsValidSha256(digestHex) ||
                size <= 0 || size > MaximumInstallerBytes ||
                !IsOfficialReleaseAssetUrl(assetUrl, tag, OfficialInstallerName) ||
                !IsOfficialReleaseAssetUrl(checksumUrl, tag, OfficialInstallerName + ".sha256"))
            {
                return Failure(current, bestVersion, "Метаданные installer не прошли Production-проверку происхождения/размера/SHA-256.");
            }

            var updateAvailable = bestVersion > ParseVersion(current);
            return new UpdateCheckResult
            {
                Success = true,
                Configured = true,
                UpdateAvailable = updateAvailable,
                CurrentVersion = current,
                LatestVersion = bestVersion.ToString(3),
                ReleaseName = releaseName,
                Notes = body,
                AssetName = OfficialInstallerName,
                AssetUrl = assetUrl,
                AssetDigest = "sha256:" + digestHex,
                ChecksumUrl = checksumUrl,
                AssetSize = size,
                Message = updateAvailable ? $"Доступна версия {bestVersion.ToString(3)}." : "Установлена актуальная версия."
            };
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new UpdateCheckResult
            {
                Success = false,
                Configured = true,
                CurrentVersion = current,
                Message = "GitHub не ответил вовремя. Merzo выполнил повторные попытки и резервную проверку; попробуйте ещё раз через несколько секунд."
            };
        }
        catch (Exception ex)
        {
            return new UpdateCheckResult
            {
                Success = false,
                Configured = true,
                CurrentVersion = current,
                Message = $"Ошибка проверки обновлений после повторных и резервных запросов: {ex.Message}"
            };
        }
    }

    private async Task<(JsonElement? Release, Version? Version)> ResolveBestReleaseAsync(CancellationToken cancellationToken)
    {
        Exception? listFailure = null;
        try
        {
            var releasesUrl = $"https://api.github.com/repos/{OfficialOwner}/{OfficialRepository}/releases?per_page=20";
            var releases = await GetJsonWithRetryAsync(releasesUrl, 3, cancellationToken).ConfigureAwait(false);
            var best = SelectBestRelease(releases);
            if (best.Release is not null)
                return best;
        }
        catch (Exception ex) when (ex is not OperationCanceledException || !cancellationToken.IsCancellationRequested)
        {
            listFailure = ex;
        }

        // API fallback: fetch only matching MWO tag refs, then request one exact release.
        // This avoids the heavy /releases list endpoint that can intermittently return 502/503/504.
        Exception? refFailure = null;
        try
        {
            var refsUrl = $"https://api.github.com/repos/{OfficialOwner}/{OfficialRepository}/git/matching-refs/tags/{OfficialTagPrefix}";
            var refs = await GetJsonWithRetryAsync(refsUrl, 3, cancellationToken).ConfigureAwait(false);
            var bestTag = SelectBestTagFromRefs(refs);
            if (!string.IsNullOrWhiteSpace(bestTag))
                return await ResolveExactReleaseAsync(bestTag, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not OperationCanceledException || !cancellationToken.IsCancellationRequested)
        {
            refFailure = ex;
        }

        // Second lightweight fallback for GitHub installations/proxies where matching-refs is unavailable.
        try
        {
            var tagsUrl = $"https://api.github.com/repos/{OfficialOwner}/{OfficialRepository}/tags?per_page=100";
            var tags = await GetJsonWithRetryAsync(tagsUrl, 2, cancellationToken).ConfigureAwait(false);
            var bestTag = SelectBestTagFromTags(tags);
            if (!string.IsNullOrWhiteSpace(bestTag))
                return await ResolveExactReleaseAsync(bestTag, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not OperationCanceledException || !cancellationToken.IsCancellationRequested)
        {
            var details = string.Join(" | ", new[] { listFailure?.Message, refFailure?.Message, ex.Message }.Where(x => !string.IsNullOrWhiteSpace(x)));
            throw new HttpRequestException($"GitHub update API временно недоступен. {details}", ex);
        }

        return (null, null);
    }

    private async Task<(JsonElement? Release, Version? Version)> ResolveExactReleaseAsync(string tag, CancellationToken cancellationToken)
    {
        var version = ParseTaggedVersion(tag, OfficialTagPrefix);
        if (version is null)
            return (null, null);
        var url = $"https://api.github.com/repos/{OfficialOwner}/{OfficialRepository}/releases/tags/{Uri.EscapeDataString(tag)}";
        var release = await GetJsonWithRetryAsync(url, 3, cancellationToken).ConfigureAwait(false);
        if (release.ValueKind != JsonValueKind.Object)
            return (null, null);
        if (release.TryGetProperty("draft", out var draft) && draft.GetBoolean())
            return (null, null);
        if (release.TryGetProperty("prerelease", out var prerelease) && prerelease.GetBoolean())
            return (null, null);
        var returnedTag = release.TryGetProperty("tag_name", out var tagEl) ? tagEl.GetString() ?? string.Empty : string.Empty;
        if (!returnedTag.Equals(tag, StringComparison.Ordinal))
            throw new InvalidDataException("GitHub release-by-tag вернул неожиданный tag_name.");
        return (release.Clone(), version);
    }

    private static (JsonElement? Release, Version? Version) SelectBestRelease(JsonElement releases)
    {
        if (releases.ValueKind != JsonValueKind.Array)
            return (null, null);
        JsonElement? bestRelease = null;
        Version? bestVersion = null;
        foreach (var release in releases.EnumerateArray())
        {
            if (release.TryGetProperty("draft", out var draft) && draft.GetBoolean()) continue;
            if (release.TryGetProperty("prerelease", out var prerelease) && prerelease.GetBoolean()) continue;
            var tag = release.TryGetProperty("tag_name", out var tagEl) ? tagEl.GetString() ?? string.Empty : string.Empty;
            if (!tag.StartsWith(OfficialTagPrefix, StringComparison.Ordinal)) continue;
            var version = ParseTaggedVersion(tag, OfficialTagPrefix);
            if (version is null) continue;
            if (bestVersion is null || version > bestVersion)
            {
                bestVersion = version;
                bestRelease = release.Clone();
            }
        }
        return (bestRelease, bestVersion);
    }

    private static string? SelectBestTagFromRefs(JsonElement refs)
    {
        if (refs.ValueKind != JsonValueKind.Array) return null;
        string? bestTag = null;
        Version? bestVersion = null;
        foreach (var item in refs.EnumerateArray())
        {
            var value = item.TryGetProperty("ref", out var refEl) ? refEl.GetString() ?? string.Empty : string.Empty;
            const string prefix = "refs/tags/";
            if (!value.StartsWith(prefix, StringComparison.Ordinal)) continue;
            var tag = value[prefix.Length..];
            if (!tag.StartsWith(OfficialTagPrefix, StringComparison.Ordinal)) continue;
            var version = ParseTaggedVersion(tag, OfficialTagPrefix);
            if (version is null) continue;
            if (bestVersion is null || version > bestVersion) { bestVersion = version; bestTag = tag; }
        }
        return bestTag;
    }

    private static string? SelectBestTagFromTags(JsonElement tags)
    {
        if (tags.ValueKind != JsonValueKind.Array) return null;
        string? bestTag = null;
        Version? bestVersion = null;
        foreach (var item in tags.EnumerateArray())
        {
            var tag = item.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? string.Empty : string.Empty;
            if (!tag.StartsWith(OfficialTagPrefix, StringComparison.Ordinal)) continue;
            var version = ParseTaggedVersion(tag, OfficialTagPrefix);
            if (version is null) continue;
            if (bestVersion is null || version > bestVersion) { bestVersion = version; bestTag = tag; }
        }
        return bestTag;
    }

    private async Task<JsonElement> GetJsonWithRetryAsync(string url, int attempts, CancellationToken cancellationToken)
    {
        Exception? last = null;
        for (var attempt = 1; attempt <= attempts; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                using var response = await _http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
                if (response.IsSuccessStatusCode)
                {
                    await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
                    using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);
                    return doc.RootElement.Clone();
                }

                if (!IsTransientStatus(response.StatusCode))
                    response.EnsureSuccessStatusCode();

                last = new HttpRequestException($"HTTP {(int)response.StatusCode} ({response.ReasonPhrase}) from GitHub.");
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                last = new TimeoutException("GitHub request timeout.");
            }
            catch (HttpRequestException ex)
            {
                last = ex;
            }

            if (attempt < attempts)
            {
                var delay = TimeSpan.FromMilliseconds(attempt switch { 1 => 350, 2 => 900, _ => 1800 });
                await Task.Delay(delay, cancellationToken).ConfigureAwait(false);
            }
        }
        throw new HttpRequestException($"GitHub request failed after {attempts} attempts: {last?.Message}", last);
    }

    private static bool IsTransientStatus(HttpStatusCode status) => status is
        HttpStatusCode.RequestTimeout or
        (HttpStatusCode)429 or
        HttpStatusCode.InternalServerError or
        HttpStatusCode.BadGateway or
        HttpStatusCode.ServiceUnavailable or
        HttpStatusCode.GatewayTimeout;

    public Task<UpdateDownloadResult> DownloadAsync(UpdateCheckResult update, CancellationToken cancellationToken = default) =>
        DownloadAsync(update, progress: null, cancellationToken);

    public async Task<UpdateDownloadResult> DownloadAsync(UpdateCheckResult update, IProgress<UpdateProgressInfo>? progress, CancellationToken cancellationToken = default)
    {
        string? metadataError = null;
        if (!HasOfficialProductionConfiguration())
            return new UpdateDownloadResult { Success = false, Message = "Конфигурация обновлений не является официальной." };
        if (!ValidateDownloadMetadata(update, out metadataError))
            return new UpdateDownloadResult { Success = false, Message = metadataError ?? "Метаданные обновления отклонены." };

        progress?.Report(new UpdateProgressInfo { Phase = "prepare", Message = "Проверяю происхождение и две SHA-256…", IsIndeterminate = true });

        var digestSha = ExtractSha256Digest(update.AssetDigest);
        string sidecarSha;
        try
        {
            progress?.Report(new UpdateProgressInfo { Phase = "checksum", Message = "Сверяю GitHub digest и SHA-256 sidecar…", IsIndeterminate = true });
            var checksumText = await _http.GetStringAsync(update.ChecksumUrl, cancellationToken).ConfigureAwait(false);
            sidecarSha = ParseSidecarSha256(checksumText);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            return new UpdateDownloadResult { Success = false, Message = $"Не удалось проверить SHA-256 sidecar: {ex.Message}" };
        }

        if (!IsValidSha256(digestSha) || !IsValidSha256(sidecarSha) || !FixedTimeShaEquals(digestSha, sidecarSha))
            return new UpdateDownloadResult { Success = false, Message = "GitHub digest и SHA-256 sidecar не совпадают. Обновление отклонено." };

        var path = Path.Combine(_updateDirectory, OfficialInstallerName);
        var temp = path + ".part";

        try
        {
            using var response = await _http.GetAsync(update.AssetUrl, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            if (response.Content.Headers.ContentLength is long headerSize && headerSize != update.AssetSize)
                return new UpdateDownloadResult { Success = false, Message = "Размер installer в HTTP-ответе не совпал с GitHub metadata." };

            var total = update.AssetSize;
            var buffer = new byte[128 * 1024];
            long received = 0;
            long lastReceived = 0;
            var watch = Stopwatch.StartNew();
            var lastReport = TimeSpan.Zero;

            progress?.Report(new UpdateProgressInfo
            {
                Phase = "download",
                Message = "Скачиваю официальный installer…",
                TotalBytes = total,
                IsIndeterminate = false
            });

            await using (var source = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false))
            await using (var target = new FileStream(temp, FileMode.Create, FileAccess.Write, FileShare.None, buffer.Length, useAsync: true))
            {
                while (true)
                {
                    var read = await source.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken).ConfigureAwait(false);
                    if (read <= 0) break;
                    received += read;
                    if (received > total)
                        throw new InvalidDataException("Installer превысил заявленный GitHub размер.");
                    await target.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);

                    var elapsedSinceReport = watch.Elapsed - lastReport;
                    if (elapsedSinceReport.TotalMilliseconds >= 120 || received >= total)
                    {
                        var delta = received - lastReceived;
                        var speed = elapsedSinceReport.TotalSeconds > 0 ? delta / elapsedSinceReport.TotalSeconds : 0;
                        var percent = Math.Clamp(received * 100.0 / total, 0, 100);
                        progress?.Report(new UpdateProgressInfo
                        {
                            Phase = "download",
                            Message = $"Скачивание {percent:0}%",
                            BytesReceived = received,
                            TotalBytes = total,
                            Percent = percent,
                            BytesPerSecond = speed,
                            IsIndeterminate = false
                        });
                        lastReport = watch.Elapsed;
                        lastReceived = received;
                    }
                }
                await target.FlushAsync(cancellationToken).ConfigureAwait(false);
            }

            if (received != total)
                throw new InvalidDataException($"Installer скачан не полностью: {received} из {total} байт.");

            progress?.Report(new UpdateProgressInfo { Phase = "verify", Message = "Повторно считаю SHA-256 installer…", BytesReceived = received, TotalBytes = total, Percent = 100, IsIndeterminate = true });
            var actual = await ComputeSha256Async(temp, cancellationToken).ConfigureAwait(false);
            if (!FixedTimeShaEquals(digestSha, actual))
            {
                TryDelete(temp);
                progress?.Report(new UpdateProgressInfo { Phase = "error", Message = "SHA-256 не совпал. Файл удалён.", Percent = 100 });
                return new UpdateDownloadResult { Success = false, VerifiedSha256 = actual, Message = "SHA-256 installer не совпал. Загруженный файл удалён." };
            }

            File.Move(temp, path, overwrite: true);
            progress?.Report(new UpdateProgressInfo { Phase = "ready", Message = "Источник, размер и SHA-256 подтверждены. Готово к установке.", BytesReceived = received, TotalBytes = total, Percent = 100 });
            return new UpdateDownloadResult
            {
                Success = true,
                FilePath = path,
                VerifiedSha256 = actual,
                VerifiedSize = received,
                Message = $"Installer проверен: источник GitHub + размер + двойная SHA-256."
            };
        }
        catch (OperationCanceledException)
        {
            TryDelete(temp);
            progress?.Report(new UpdateProgressInfo { Phase = "cancelled", Message = "Загрузка обновления отменена. Временный файл удалён." });
            throw;
        }
        catch (Exception ex)
        {
            TryDelete(temp);
            progress?.Report(new UpdateProgressInfo { Phase = "error", Message = $"Ошибка безопасной загрузки: {ex.Message}" });
            return new UpdateDownloadResult { Success = false, Message = $"Ошибка загрузки обновления: {ex.Message}" };
        }
    }

    public UpdateInstallResult LaunchInstaller(UpdateDownloadResult download)
    {
        var installed = IsInstalledLayout();
        if (!installed)
        {
            return new UpdateInstallResult
            {
                Success = false,
                InstalledLayout = false,
                Message = "Автоустановка доступна только установленной версии. DEV/portable-сборка не перезаписывается."
            };
        }

        if (!download.Success || string.IsNullOrWhiteSpace(download.FilePath) || !IsValidSha256(download.VerifiedSha256) || download.VerifiedSize <= 0)
            return new UpdateInstallResult { Success = false, InstalledLayout = true, Message = "Нет подтверждённого installer для запуска." };

        try
        {
            var canonical = Path.GetFullPath(download.FilePath);
            if (!IsPathInsideDirectory(canonical, _updateDirectory) ||
                !Path.GetFileName(canonical).Equals(OfficialInstallerName, StringComparison.Ordinal) ||
                !File.Exists(canonical))
                return new UpdateInstallResult { Success = false, InstalledLayout = true, Message = "Installer находится вне защищённой папки обновлений или имеет неверное имя." };

            string actual;
            long size;
            using (var input = new FileStream(canonical, FileMode.Open, FileAccess.Read, FileShare.None))
            {
                size = input.Length;
                actual = Convert.ToHexString(SHA256.HashData(input)).ToLowerInvariant();
            }

            if (size != download.VerifiedSize || !FixedTimeShaEquals(download.VerifiedSha256, actual))
            {
                TryDelete(canonical);
                return new UpdateInstallResult { Success = false, InstalledLayout = true, Message = "Installer изменился после проверки. Файл удалён, запуск заблокирован." };
            }

            Process.Start(new ProcessStartInfo
            {
                FileName = canonical,
                Arguments = Settings.InstallerSilentArgs,
                UseShellExecute = true,
                WorkingDirectory = _updateDirectory
            });

            return new UpdateInstallResult
            {
                Success = true,
                InstalledLayout = true,
                Message = "Installer повторно проверен непосредственно перед запуском и передан Windows."
            };
        }
        catch (Exception ex)
        {
            return new UpdateInstallResult { Success = false, InstalledLayout = true, Message = $"Не удалось безопасно запустить installer: {ex.Message}" };
        }
    }

    private bool ValidateDownloadMetadata(UpdateCheckResult update, out string? error)
    {
        error = null;
        if (!update.Success || !update.UpdateAvailable)
        {
            error = "Нет доступного обновления для скачивания.";
            return false;
        }
        if (!update.AssetName.Equals(OfficialInstallerName, StringComparison.Ordinal) || update.AssetSize <= 0 || update.AssetSize > MaximumInstallerBytes)
        {
            error = "Имя или размер installer не прошли Production-проверку.";
            return false;
        }
        var tag = OfficialTagPrefix + update.LatestVersion;
        if (!IsOfficialReleaseAssetUrl(update.AssetUrl, tag, OfficialInstallerName) ||
            !IsOfficialReleaseAssetUrl(update.ChecksumUrl, tag, OfficialInstallerName + ".sha256"))
        {
            error = "URL обновления не относится к официальному Merzo4/my-app-updates release.";
            return false;
        }
        if (!IsValidSha256(ExtractSha256Digest(update.AssetDigest)))
        {
            error = "GitHub asset digest отсутствует или повреждён.";
            return false;
        }
        return true;
    }

    private bool HasOfficialProductionConfiguration() =>
        string.Equals(Settings.Provider, "GitHub", StringComparison.Ordinal) &&
        string.Equals(Settings.RepositoryOwner, OfficialOwner, StringComparison.Ordinal) &&
        string.Equals(Settings.RepositoryName, OfficialRepository, StringComparison.Ordinal) &&
        string.Equals(Settings.ReleaseTagPrefix, OfficialTagPrefix, StringComparison.Ordinal) &&
        string.Equals(Settings.AssetNameContains, OfficialInstallerName, StringComparison.Ordinal);

    private static UpdateCheckResult Failure(string current, Version latest, string message) => new()
    {
        Success = false,
        Configured = true,
        CurrentVersion = current,
        LatestVersion = latest.ToString(3),
        Message = message
    };

    private static bool IsOfficialReleaseAssetUrl(string value, string expectedTag, string expectedName)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri)) return false;
        if (!uri.Scheme.Equals(Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase) ||
            !uri.Host.Equals("github.com", StringComparison.OrdinalIgnoreCase) ||
            !string.IsNullOrEmpty(uri.UserInfo) ||
            !uri.IsDefaultPort ||
            !string.IsNullOrEmpty(uri.Fragment))
            return false;

        var expectedPath = $"/{OfficialOwner}/{OfficialRepository}/releases/download/{expectedTag}/{expectedName}";
        return Uri.UnescapeDataString(uri.AbsolutePath).Equals(expectedPath, StringComparison.Ordinal);
    }

    private static string ExtractSha256Digest(string value)
    {
        if (!value.StartsWith("sha256:", StringComparison.OrdinalIgnoreCase)) return string.Empty;
        return value[7..].Trim().ToLowerInvariant();
    }

    private static string ParseSidecarSha256(string text)
    {
        var token = text.Trim().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? string.Empty;
        return token.Trim().ToLowerInvariant();
    }

    private static bool IsValidSha256(string value) => value.Length == 64 && value.All(Uri.IsHexDigit);

    private static bool FixedTimeShaEquals(string left, string right)
    {
        if (!IsValidSha256(left) || !IsValidSha256(right)) return false;
        return CryptographicOperations.FixedTimeEquals(Convert.FromHexString(left), Convert.FromHexString(right));
    }

    private static async Task<string> ComputeSha256Async(string path, CancellationToken cancellationToken)
    {
        await using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None, 128 * 1024, useAsync: true);
        return Convert.ToHexString(await SHA256.HashDataAsync(input, cancellationToken).ConfigureAwait(false)).ToLowerInvariant();
    }

    private static bool IsPathInsideDirectory(string path, string directory)
    {
        var relative = Path.GetRelativePath(Path.GetFullPath(directory), Path.GetFullPath(path));
        return !Path.IsPathRooted(relative) &&
               !relative.Equals("..", StringComparison.Ordinal) &&
               !relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }

    private static void TryDelete(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); } catch { }
    }

    private static UpdateSettings LoadSettings(string path)
    {
        try
        {
            if (!File.Exists(path)) return new UpdateSettings();
            return JsonSerializer.Deserialize<UpdateSettings>(File.ReadAllText(path), new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
            }) ?? new UpdateSettings();
        }
        catch { return new UpdateSettings(); }
    }

    private static string GetCurrentVersion() => Assembly.GetEntryAssembly()?.GetName().Version?.ToString(3) ?? "0.1.48";

    private static Version ParseVersion(string value)
    {
        value = value.Trim().TrimStart('v', 'V');
        var numeric = new string(value.TakeWhile(c => char.IsDigit(c) || c == '.').ToArray());
        return Version.TryParse(numeric, out var parsed) ? parsed : new Version(0, 0);
    }

    private static Version? ParseTaggedVersion(string tag, string prefix)
    {
        var value = tag.StartsWith(prefix, StringComparison.Ordinal) ? tag[prefix.Length..] : tag;
        value = value.Trim().TrimStart('v', 'V');
        var numeric = new string(value.TakeWhile(c => char.IsDigit(c) || c == '.').ToArray());
        return Version.TryParse(numeric, out var parsed) ? parsed : null;
    }

    private static bool IsInstalledLayout()
    {
        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        var programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        return (!string.IsNullOrWhiteSpace(programFiles) && baseDir.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase)) ||
               (!string.IsNullOrWhiteSpace(programFilesX86) && baseDir.StartsWith(programFilesX86, StringComparison.OrdinalIgnoreCase));
    }

    public void Dispose() => _http.Dispose();
}
