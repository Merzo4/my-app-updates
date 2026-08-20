from pathlib import Path
import os,re
root=Path(os.environ['SOURCE_ROOT'])

# Keep multi-product GitHub release filtering correct.
update=root/'src'/'MerzoOptimizer.Windows'/'Updates'/'GitHubUpdateService.cs'
u=update.read_text(encoding='utf-8-sig')
u=u.replace('var tag = release.TryGetProperty("tag_name", out var tagEl) ? tagEl.GetString() ?? string.Empty : string.Empty;', 'var candidateTag = release.TryGetProperty("tag_name", out var tagEl) ? tagEl.GetString() ?? string.Empty : string.Empty;')
u=u.replace('if (!tag.StartsWith(Settings.ReleaseTagPrefix, StringComparison.OrdinalIgnoreCase))', 'if (!candidateTag.StartsWith(Settings.ReleaseTagPrefix, StringComparison.OrdinalIgnoreCase))')
u=u.replace('var version = ParseTaggedVersion(tag, Settings.ReleaseTagPrefix);', 'var version = ParseTaggedVersion(candidateTag, Settings.ReleaseTagPrefix);')
update.write_text(u,encoding='utf-8')

vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')
if 'using System.Diagnostics;' not in s:
    s=s.replace('using System.ComponentModel;', 'using System.ComponentModel;\nusing System.Diagnostics;')
if 'private bool _isUpdateBusy;' not in s:
    s=s.replace('private bool _initialized;', 'private bool _initialized;\n    private bool _isUpdateBusy;')
s=s.replace('CheckUpdatesCommand = new AsyncRelayCommand(CheckUpdatesAsync, () => !IsStage2Busy);', 'CheckUpdatesCommand = new AsyncRelayCommand(CheckUpdatesAsync, () => !IsUpdateBusy);')
s=s.replace('DownloadUpdateCommand = new AsyncRelayCommand(DownloadUpdateAsync, () => !IsStage2Busy && _lastUpdateCheck is { UpdateAvailable: true, Success: true });', 'DownloadUpdateCommand = new AsyncRelayCommand(DownloadUpdateAsync, () => !IsUpdateBusy && _lastUpdateCheck is { UpdateAvailable: true, Success: true });')
s=s.replace('if (_updateService.Settings.AutoCheck) await CheckUpdatesAsync(silent: true);', 'if (_updateService.Settings.AutoCheck) _ = CheckUpdatesAsync(silent: true);')
s=s.replace('UpdatePolicyText = $"Автопроверка: {(_updateService.Settings.AutoCheck ? "Вкл" : "Выкл")} · автоскачивание: {(_updateService.Settings.AutoDownload ? "Вкл" : "Выкл")} · автоустановка: gated";', 'UpdatePolicyText = $"Автопроверка: {(_updateService.Settings.AutoCheck ? "Вкл" : "Выкл")} · SHA-256: обязательно · установка: по подтверждению";')

if 'public bool IsUpdateBusy' not in s:
    marker='    public string TweakSearchText\n'
    prop='''    public bool IsUpdateBusy
    {
        get => _isUpdateBusy;
        private set
        {
            if (!SetProperty(ref _isUpdateBusy, value)) return;
            CheckUpdatesCommand.RaiseCanExecuteChanged();
            DownloadUpdateCommand.RaiseCanExecuteChanged();
        }
    }

'''
    if marker not in s: raise SystemExit('TweakSearchText marker missing')
    s=s.replace(marker,prop+marker,1)

start=s.find('    private Task CheckUpdatesAsync() => CheckUpdatesAsync(silent: false);')
end=s.find('    private async Task RunRecoveryTestAsync()', start)
if start < 0 or end < 0: raise SystemExit('Update method block markers missing')
methods=r'''    private Task CheckUpdatesAsync() => CheckUpdatesAsync(silent: false);

    private async Task CheckUpdatesAsync(bool silent)
    {
        if (_disposed || IsUpdateBusy) return;
        IsUpdateBusy = true;
        try
        {
            UpdateStatusText = "Проверяю GitHub Releases…";
            _lastUpdateCheck = await _dispatcher.RunAsync("Update check", token => _updateService.CheckAsync(token), _lifetimeCts.Token);
            UpdateStatusText = _lastUpdateCheck.Message;
            UpdateLatestText = _lastUpdateCheck.UpdateAvailable ? _lastUpdateCheck.LatestVersion : (_lastUpdateCheck.Configured ? "Актуально" : "Feed не настроен");
            DownloadUpdateCommand.RaiseCanExecuteChanged();
            if (!silent && _lastUpdateCheck is { Success: true, UpdateAvailable: true } available)
                MessageBox.Show($"Доступно обновление {available.LatestVersion}.\n\n{available.ReleaseName}\n\nНажмите «Скачать и установить». Merzo скачает installer, проверит SHA-256 и только потом предложит установку.", "Merzo Windows Optimizer — обновление найдено", MessageBoxButton.OK, MessageBoxImage.Information);
            else if (!silent && !_lastUpdateCheck.Success)
                MessageBox.Show(_lastUpdateCheck.Message, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            UpdateStatusText = $"Ошибка проверки обновлений: {ex.Message}";
            if (!silent) MessageBox.Show(UpdateStatusText, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally { IsUpdateBusy = false; }
    }

    private async Task DownloadUpdateAsync()
    {
        if (_disposed || IsUpdateBusy || _lastUpdateCheck is not { UpdateAvailable: true, Success: true } update) return;
        IsUpdateBusy = true;
        try
        {
            UpdateStatusText = $"Скачиваю {update.LatestVersion} и проверяю SHA-256…";
            var result = await _dispatcher.RunAsync("Update download", token => _updateService.DownloadAsync(update, token), _lifetimeCts.Token);
            UpdateStatusText = result.Message;
            if (!result.Success)
            {
                MessageBox.Show(result.Message, "Merzo Windows Optimizer — обновление", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            if (!IsInstalledLayout())
            {
                MessageBox.Show($"Обновление проверено и сохранено:\n{result.FilePath}\n\nЭта копия запущена как Portable/DEV. Автоматическая установка доступна только установленной версии.", "Обновление проверено", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }
            var answer = MessageBox.Show($"SHA-256 подтверждён.\n\nУстановить {update.LatestVersion} сейчас?\n\nMerzo запустит проверенный installer с UAC, закроется, обновится поверх текущей версии и запустится снова.", "Merzo Windows Optimizer — готово к установке", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (answer != MessageBoxResult.Yes) return;
            LaunchVerifiedInstallerAndRestart(result.FilePath);
        }
        catch (Exception ex)
        {
            UpdateStatusText = $"Не удалось установить обновление: {ex.Message}";
            MessageBox.Show(UpdateStatusText, "Merzo Windows Optimizer — обновление", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            if (Application.Current?.Dispatcher?.HasShutdownStarted != true) IsUpdateBusy = false;
        }
    }

    private static bool IsInstalledLayout()
    {
        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        if (string.IsNullOrWhiteSpace(programFiles)) return false;
        programFiles = Path.GetFullPath(programFiles).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return baseDir.StartsWith(programFiles + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }

    private static void LaunchVerifiedInstallerAndRestart(string installerPath)
    {
        if (string.IsNullOrWhiteSpace(installerPath) || !File.Exists(installerPath)) throw new FileNotFoundException("Проверенный installer не найден.", installerPath);
        var currentExe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "MerzoWindowsOptimizer.exe");
        var installer = Process.Start(new ProcessStartInfo
        {
            FileName = installerPath,
            Arguments = "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS",
            UseShellExecute = true,
            Verb = "runas"
        }) ?? throw new InvalidOperationException("Windows не запустила installer.");
        var restartScript = Path.Combine(Path.GetTempPath(), $"MerzoWindowsOptimizer_UpdateRestart_{Guid.NewGuid():N}.ps1");
        var escapedExe = currentExe.Replace("'", "''");
        var script = $"$ErrorActionPreference='SilentlyContinue'`r`nWait-Process -Id {installer.Id}`r`nStart-Sleep -Milliseconds 1200`r`nif (Test-Path -LiteralPath '{escapedExe}') {{ Start-Process -FilePath '{escapedExe}' }}`r`nRemove-Item -LiteralPath $PSCommandPath -Force`r`n";
        File.WriteAllText(restartScript, script);
        Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"{restartScript}\"",
            UseShellExecute = false,
            CreateNoWindow = true
        });
        Application.Current.Shutdown();
    }

'''
s=s[:start]+methods+s[end:]
vm.write_text(s,encoding='utf-8')

xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
# Change button labels by command binding, independent of existing attribute text/order.
x=re.sub(r'(<Button\b(?=[^>]*Command="\{Binding CheckUpdatesCommand\}")[^>]*\bContent=")[^"]*(")', r'\1Проверить обновления\2', x)
x=re.sub(r'(<Button\b(?=[^>]*Command="\{Binding DownloadUpdateCommand\}")[^>]*\bContent=")[^"]*(")', r'\1Скачать и установить\2', x)
x=x.replace('Автопроверка релизов · SHA-256 verification · безопасное staged-download', 'GitHub Releases · обязательная SHA-256 проверка · установка только после подтверждения')
x=x.replace('Title="Merzo Windows Optimizer — R20 · Scan First &amp; Lite Build"', 'Title="Merzo Windows Optimizer — Production 0.1.24"')
x=x.replace('·  On-demand UAC + Scan First R20', '·  Production R24 · Online Update Ready')
xaml.write_text(x,encoding='utf-8')

cs=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml.cs'
c=cs.read_text(encoding='utf-8-sig')
c=re.sub(r'\n    private void TitleBar_MouseLeftButtonDown\(object sender, MouseButtonEventArgs e\)\n    \{.*?\n    \}\n', '\n', c, flags=re.S)
cs.write_text(c,encoding='utf-8')

final=vm.read_text(encoding='utf-8')
for token in ['IsUpdateBusy','LaunchVerifiedInstallerAndRestart','Verb = "runas"']:
    if token not in final: raise SystemExit(f'Updater patch missing token: {token}')
xfinal=xaml.read_text(encoding='utf-8')
if 'Проверить обновления' not in xfinal or 'Скачать и установить' not in xfinal: raise SystemExit('Updater XAML patch missing')
if 'DragMove();' in cs.read_text(encoding='utf-8'): raise SystemExit('R23 drag hotfix regressed')
print('R24 updater patch contract: OK')
