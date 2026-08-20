from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s): p.write_text(s, encoding='utf-8')
def rep(s, old, new, label):
    if old not in s:
        raise SystemExit(f'R38 network anchor missing: {label}')
    return s.replace(old, new, 1)

# Core service contract.
p = root/'src'/'MerzoOptimizer.Core'/'Network'/'NetworkModels.cs'
s = read(p)
s = rep(s,
'''    Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default);
}''',
'''    Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> ApplyGamingNetworkSafeAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> ApplyGamingNetworkExtremeAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> RestoreGamingNetworkAsync(CancellationToken cancellationToken = default);
}''', 'core interface')
write(p, s)

# Windows implementation forwards only fixed allow-listed action names.
p = root/'src'/'MerzoOptimizer.Windows'/'Network'/'WindowsNetworkRepairService.cs'
s = read(p)
s = rep(s,
'''    public Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default) => ExecuteAsync("reset_tcpip", cancellationToken);

    private Task<NetworkRepairResult> ExecuteAsync''',
'''    public Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default) => ExecuteAsync("reset_tcpip", cancellationToken);
    public Task<NetworkRepairResult> ApplyGamingNetworkSafeAsync(CancellationToken cancellationToken = default) => ExecuteAsync("gaming_network_safe", cancellationToken);
    public Task<NetworkRepairResult> ApplyGamingNetworkExtremeAsync(CancellationToken cancellationToken = default) => ExecuteAsync("gaming_network_extreme", cancellationToken);
    public Task<NetworkRepairResult> RestoreGamingNetworkAsync(CancellationToken cancellationToken = default) => ExecuteAsync("restore_gaming_network", cancellationToken);

    private Task<NetworkRepairResult> ExecuteAsync''', 'windows methods')
write(p, s)

# Elevated helper: fixed PowerShell scripts, no UI supplied executable or arguments.
p = root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
s = read(p)
if 'using System.Text;' not in s:
    s = s.replace('using System.Diagnostics;', 'using System.Diagnostics;\nusing System.Text;', 1)
s = rep(s,
'''        var normalized = action.Trim().ToLowerInvariant();
        var (fileName, arguments, rebootRequired, successMessage) = normalized switch''',
'''        var normalized = action.Trim().ToLowerInvariant();
        if (normalized is "gaming_network_safe" or "gaming_network_extreme" or "restore_gaming_network")
            return await ExecuteGamingNetworkPresetAsync(normalized).ConfigureAwait(false);

        var (fileName, arguments, rebootRequired, successMessage) = normalized switch''', 'helper special dispatch')

anchor = '    private static ElevatedOperationResponse Success(string requestId, object result) => new()'
method = r'''    private static async Task<NetworkRepairResult> ExecuteGamingNetworkPresetAsync(string action)
    {
        var baseline = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MerzoWindowsOptimizer", "network-gaming-baseline.json");
        Directory.CreateDirectory(Path.GetDirectoryName(baseline)!);
        var baselinePs = baseline.Replace("'", "''", StringComparison.Ordinal);

        string script;
        string successMessage;
        if (action == "gaming_network_safe")
        {
            script = """
$ErrorActionPreference='Stop'
netsh int tcp set global rss=enabled | Out-Null
netsh int tcp set global autotuninglevel=normal | Out-Null
$a=Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -and $_.HardwareInterface} | Sort-Object LinkSpeed -Descending | Select-Object -First 1
if($a){ try { Set-NetAdapterRss -Name $a.Name -Enabled $true -NoRestart -ErrorAction Stop } catch {} }
Write-Output 'RSS включён; TCP Auto-Tuning установлен Normal. Адаптер не перезапускался.'
""";
            successMessage = "Gaming Network SAFE применён: RSS включён, TCP Auto-Tuning = Normal. Соединение не перезапускалось.";
        }
        else if (action == "gaming_network_extreme")
        {
            script = $$"""
$ErrorActionPreference='Stop'
$a=Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -and $_.HardwareInterface} | Sort-Object LinkSpeed -Descending | Select-Object -First 1
if(-not $a){ throw 'Активный аппаратный сетевой адаптер не найден.' }
$rss=Get-NetAdapterRss -Name $a.Name -ErrorAction SilentlyContinue
$rsc=Get-NetAdapterRsc -Name $a.Name -ErrorAction SilentlyContinue
$pm=Get-NetAdapterPowerManagement -Name $a.Name -ErrorAction SilentlyContinue
$im=Get-NetAdapterAdvancedProperty -Name $a.Name -AllProperties -ErrorAction SilentlyContinue | Where-Object {$_.RegistryKeyword -match 'InterruptModeration'} | Select-Object -First 1
[pscustomobject]@{
 Name=$a.Name
 RssEnabled=if($rss){[bool]$rss.Enabled}else{$null}
 RscIPv4=if($rsc){[bool]$rsc.IPv4Enabled}else{$null}
 RscIPv6=if($rsc){[bool]$rsc.IPv6Enabled}else{$null}
 SelectiveSuspend=if($pm){[string]$pm.SelectiveSuspend}else{$null}
 DeviceSleepOnDisconnect=if($pm){[string]$pm.DeviceSleepOnDisconnect}else{$null}
 InterruptDisplayName=if($im){[string]$im.DisplayName}else{$null}
 InterruptDisplayValue=if($im){[string]$im.DisplayValue}else{$null}
} | ConvertTo-Json | Set-Content -LiteralPath '{{baselinePs}}' -Encoding UTF8
$applied=0
netsh int tcp set global rss=enabled | Out-Null; $applied++
netsh int tcp set global autotuninglevel=normal | Out-Null; $applied++
try { Set-NetAdapterRss -Name $a.Name -Enabled $true -NoRestart -ErrorAction Stop; $applied++ } catch {}
try { Disable-NetAdapterRsc -Name $a.Name -NoRestart -ErrorAction Stop; $applied++ } catch {}
try { Disable-NetAdapterPowerManagement -Name $a.Name -SelectiveSuspend -DeviceSleepOnDisconnect -NoRestart -ErrorAction Stop; $applied++ } catch {}
if($im){ try { Set-NetAdapterAdvancedProperty -Name $a.Name -RegistryKeyword $im.RegistryKeyword -RegistryValue 0 -NoRestart -ErrorAction Stop; $applied++ } catch {} }
Write-Output ("EXTREME applied="+$applied+" adapter="+$a.Name+". Baseline saved. No adapter restart was forced.")
""";
            successMessage = "Gaming Network EXTREME применён. Сохранён baseline адаптера; RSS/Auto-Tuning нормализованы, а поддерживаемые low-latency параметры применены без принудительного перезапуска адаптера.";
        }
        else
        {
            script = $$"""
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath '{{baselinePs}}')){ throw 'Baseline Gaming Network не найден. Сначала примените EXTREME.' }
$b=Get-Content -LiteralPath '{{baselinePs}}' -Raw | ConvertFrom-Json
$a=Get-NetAdapter -Name $b.Name -ErrorAction Stop
if($null -ne $b.RssEnabled){ try { Set-NetAdapterRss -Name $a.Name -Enabled ([bool]$b.RssEnabled) -NoRestart -ErrorAction Stop } catch {} }
if($null -ne $b.RscIPv4 -or $null -ne $b.RscIPv6){
 try { Set-NetAdapterRsc -Name $a.Name -IPv4Enabled ([bool]$b.RscIPv4) -IPv6Enabled ([bool]$b.RscIPv6) -NoRestart -ErrorAction Stop } catch {}
}
if($b.SelectiveSuspend -or $b.DeviceSleepOnDisconnect){
 try { Set-NetAdapterPowerManagement -Name $a.Name -SelectiveSuspend $b.SelectiveSuspend -DeviceSleepOnDisconnect $b.DeviceSleepOnDisconnect -NoRestart -ErrorAction Stop } catch {}
}
if($b.InterruptDisplayName -and $b.InterruptDisplayValue){
 try { Set-NetAdapterAdvancedProperty -Name $a.Name -DisplayName $b.InterruptDisplayName -DisplayValue $b.InterruptDisplayValue -NoRestart -ErrorAction Stop } catch {}
}
netsh int tcp set global rss=enabled | Out-Null
netsh int tcp set global autotuninglevel=normal | Out-Null
Remove-Item -LiteralPath '{{baselinePs}}' -Force -ErrorAction SilentlyContinue
Write-Output ('Gaming Network baseline restored for '+$a.Name+'. TCP defaults left at RSS enabled / Auto-Tuning Normal.')
""";
            successMessage = "Gaming Network baseline восстановлен для адаптера. TCP оставлен в рекомендуемом состоянии RSS Enabled / Auto-Tuning Normal.";
        }

        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить Windows PowerShell для Gaming Network.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(40));
        try
        {
            await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            return new NetworkRepairResult(false, "Gaming Network превысил безопасный таймаут 40 секунд.", false, -1);
        }
        var output = (await outputTask.ConfigureAwait(false)).Trim();
        var error = (await errorTask.ConfigureAwait(false)).Trim();
        if (process.ExitCode != 0)
        {
            var detail = string.IsNullOrWhiteSpace(error) ? output : error;
            if (detail.Length > 500) detail = detail[..500] + "…";
            return new NetworkRepairResult(false, $"Gaming Network: Windows вернула код {process.ExitCode}. {detail}", false, process.ExitCode);
        }
        var suffix = string.IsNullOrWhiteSpace(output) ? string.Empty : $"\n{output}";
        return new NetworkRepairResult(true, successMessage + suffix, false, process.ExitCode);
    }

'''
if anchor not in s:
    raise SystemExit('R38 helper method anchor missing')
s = s.replace(anchor, method + anchor, 1)
write(p, s)

# ViewModel commands.
p = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s = read(p)
s = rep(s,
'''        RepairNetworkCommand = new AsyncRelayCommand(RepairNetworkAsync, () => !IsNetworkBusy);''',
'''        RepairNetworkCommand = new AsyncRelayCommand(RepairNetworkAsync, () => !IsNetworkBusy);
        ApplyGamingNetworkSafeCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Gaming Network SAFE", "Merzo включит RSS и вернёт TCP Auto-Tuning в Normal. Это штатные параметры Windows. Продолжить?", _networkRepairService.ApplyGamingNetworkSafeAsync, confirm: true), () => !IsNetworkBusy);
        ApplyGamingNetworkExtremeCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Gaming Network EXTREME", "Экспериментальный low-latency режим: Merzo сохранит baseline активного адаптера, затем попробует отключить RSC, энергосбережение адаптера и Interrupt Moderation, если драйвер это поддерживает. Возможен больший расход CPU/энергии. Продолжить?", _networkRepairService.ApplyGamingNetworkExtremeAsync, confirm: true), () => !IsNetworkBusy);
        RestoreGamingNetworkCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Вернуть Gaming Network", "Будет восстановлен baseline адаптера, сохранённый перед EXTREME. TCP RSS/Auto-Tuning останутся в нормальном состоянии Windows. Продолжить?", _networkRepairService.RestoreGamingNetworkAsync, confirm: true), () => !IsNetworkBusy);''', 'vm command init')
s = rep(s,
'''    public AsyncRelayCommand RepairNetworkCommand { get; }''',
'''    public AsyncRelayCommand RepairNetworkCommand { get; }
    public AsyncRelayCommand ApplyGamingNetworkSafeCommand { get; }
    public AsyncRelayCommand ApplyGamingNetworkExtremeCommand { get; }
    public AsyncRelayCommand RestoreGamingNetworkCommand { get; }''', 'vm command props')
s = rep(s,
'''            ResetWinsockCommand.RaiseCanExecuteChanged(); ResetTcpIpCommand.RaiseCanExecuteChanged(); RepairNetworkCommand.RaiseCanExecuteChanged();''',
'''            ResetWinsockCommand.RaiseCanExecuteChanged(); ResetTcpIpCommand.RaiseCanExecuteChanged(); RepairNetworkCommand.RaiseCanExecuteChanged();
            ApplyGamingNetworkSafeCommand.RaiseCanExecuteChanged(); ApplyGamingNetworkExtremeCommand.RaiseCanExecuteChanged(); RestoreGamingNetworkCommand.RaiseCanExecuteChanged();''', 'vm network busy refresh')
write(p, s)

# Add Gaming Network controls to Repair / Network page.
p = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s = read(p)
anchor = '''                                <Border Style="{StaticResource CardBorder}" Padding="11" Margin="0,0,0,7"><StackPanel>
                                    <TextBlock Text="Быстрый Repair"'''
insert = '''                                <Border Style="{StaticResource CardBorder}" Padding="11" Margin="0,0,0,7"><StackPanel>
                                    <TextBlock Text="Gaming Network" FontSize="12.5" FontWeight="SemiBold"/>
                                    <TextBlock Text="SAFE нормализует TCP. EXTREME сохраняет baseline и применяет поддерживаемые low-latency параметры адаптера без принудительного reconnect." Foreground="{StaticResource TextMuted}" FontSize="9.7" TextWrapping="Wrap" Margin="0,2,0,8"/>
                                    <UniformGrid Columns="2" Rows="1">
                                        <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyGamingNetworkSafeCommand}" Content="LOW LATENCY SAFE" Margin="0,0,5,0"/>
                                        <Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding ApplyGamingNetworkExtremeCommand}" Content="EXTREME"/>
                                    </UniformGrid>
                                    <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding RestoreGamingNetworkCommand}" Content="Вернуть baseline EXTREME" Margin="0,6,0,0"/>
                                    <TextBlock Text="EXTREME может увеличить CPU/энергопотребление. Если драйвер не поддерживает отдельный параметр, Merzo пропустит его вместо случайной записи в реестр драйвера." Foreground="#B69A6A" FontSize="9.3" TextWrapping="Wrap" Margin="0,6,0,0"/>
                                </StackPanel></Border>
''' + anchor
if anchor not in s:
    raise SystemExit('R38 Gaming Network XAML anchor missing')
s = s.replace(anchor, insert, 1)
write(p, s)

print('R38 gaming network patch: OK')
