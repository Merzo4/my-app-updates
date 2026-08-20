from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')
def rep(s, old, new, label):
    if old not in s: raise SystemExit(f'R37 network anchor missing: {label}')
    return s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Core network contract.
# -----------------------------------------------------------------------------
core_net = root/'src'/'MerzoOptimizer.Core'/'Network'/'NetworkModels.cs'
write(core_net, r'''namespace MerzoOptimizer.Core.Network;

public sealed record NetworkDiagnosticSnapshot(
    bool NetworkAvailable,
    string AdapterName,
    string AdapterDescription,
    string AdapterType,
    string Status,
    string LinkSpeed,
    string IPv4,
    string Gateway,
    string DnsServers,
    string Dhcp,
    string GatewayTest,
    string DnsTest,
    int ActiveAdapterCount,
    DateTimeOffset CapturedAt)
{
    public string Summary => NetworkAvailable
        ? $"Сеть доступна · активных адаптеров: {ActiveAdapterCount} · {AdapterName}"
        : "Windows не видит активного сетевого подключения";
}

public sealed record NetworkRepairResult(bool Success, string Message, bool RebootRequired, int ExitCode);

public interface INetworkRepairService
{
    Task<NetworkDiagnosticSnapshot> DiagnoseAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> FlushDnsAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> RenewDhcpAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> ResetWinsockAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default);
}
''')

# -----------------------------------------------------------------------------
# Extend elevated helper protocol with one strictly allow-listed NetworkRepair
# operation. No arbitrary executable/arguments are accepted from the UI.
# -----------------------------------------------------------------------------
elev_path = root/'src'/'MerzoOptimizer.Core'/'Elevation'/'ElevationModels.cs'
elev = read(elev_path)
elev = rep(elev, '    RestoreAllActive,\n    Shutdown', '    RestoreAllActive,\n    NetworkRepair,\n    Shutdown', 'elevation enum')
elev = rep(elev, '    public string? DisplayName { get; init; }\n    public Guid? SnapshotId', '    public string? DisplayName { get; init; }\n    public string? NetworkAction { get; init; }\n    public Guid? SnapshotId', 'request action')
write(elev_path, elev)

helper_path = root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
helper = read(helper_path)
helper = rep(helper, 'using System.IO.Pipes;', 'using System.Diagnostics;\nusing System.IO.Pipes;', 'helper diagnostics using')
helper = rep(helper, 'using MerzoOptimizer.Core.Logging;', 'using MerzoOptimizer.Core.Logging;\nusing MerzoOptimizer.Core.Network;', 'helper network using')
helper = rep(helper,
'''            ElevatedOperationKind.RestoreAllActive => await restore.RestoreAllActiveAsync().ConfigureAwait(false),

            _ => throw new NotSupportedException''',
'''            ElevatedOperationKind.RestoreAllActive => await restore.RestoreAllActiveAsync().ConfigureAwait(false),

            ElevatedOperationKind.NetworkRepair => await ExecuteNetworkRepairAsync(
                Require(request.NetworkAction, "Network repair action missing.")).ConfigureAwait(false),

            _ => throw new NotSupportedException''', 'helper switch')
insert_anchor = '    private static ElevatedOperationResponse Success(string requestId, object result) => new()'
network_helper_method = r'''    private static async Task<NetworkRepairResult> ExecuteNetworkRepairAsync(string action)
    {
        var normalized = action.Trim().ToLowerInvariant();
        var (fileName, arguments, rebootRequired, successMessage) = normalized switch
        {
            "flush_dns" => ("ipconfig.exe", "/flushdns", false, "DNS-кэш Windows очищен."),
            "renew_dhcp" => ("ipconfig.exe", "/renew", false, "DHCP-аренда обновлена."),
            "reset_winsock" => ("netsh.exe", "winsock reset", true, "Winsock сброшен. Для полного применения рекомендуется перезагрузка."),
            "reset_tcpip" => ("netsh.exe", "int ip reset", true, "TCP/IP стек сброшен. Для полного применения рекомендуется перезагрузка."),
            _ => throw new NotSupportedException($"Network repair action is not allow-listed: {action}")
        };

        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException($"Не удалось запустить {fileName}.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(normalized == "renew_dhcp" ? 35 : 20));
        try
        {
            await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            return new NetworkRepairResult(false, $"Команда {action} превысила безопасный таймаут.", rebootRequired, -1);
        }
        var output = (await outputTask.ConfigureAwait(false)).Trim();
        var error = (await errorTask.ConfigureAwait(false)).Trim();
        if (process.ExitCode != 0)
        {
            var detail = string.IsNullOrWhiteSpace(error) ? output : error;
            if (detail.Length > 280) detail = detail[..280] + "…";
            return new NetworkRepairResult(false, $"Windows вернула код {process.ExitCode}. {detail}", rebootRequired, process.ExitCode);
        }
        return new NetworkRepairResult(true, successMessage, rebootRequired, process.ExitCode);
    }

'''
if insert_anchor not in helper: raise SystemExit('R37 helper insertion anchor missing')
helper = helper.replace(insert_anchor, network_helper_method + insert_anchor, 1)
write(helper_path, helper)

# -----------------------------------------------------------------------------
# Windows implementation: read-only diagnostics locally + mutations only via
# the existing UAC helper and the allow-listed operation above.
# -----------------------------------------------------------------------------
win_net = root/'src'/'MerzoOptimizer.Windows'/'Network'/'WindowsNetworkRepairService.cs'
write(win_net, r'''using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Core.Network;
using MerzoOptimizer.Windows.Elevation;

namespace MerzoOptimizer.Windows.Network;

public sealed class WindowsNetworkRepairService(ElevatedOperationBroker broker) : INetworkRepairService
{
    public async Task<NetworkDiagnosticSnapshot> DiagnoseAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var adapters = NetworkInterface.GetAllNetworkInterfaces()
            .Where(static n => n.OperationalStatus == OperationalStatus.Up &&
                               n.NetworkInterfaceType != NetworkInterfaceType.Loopback &&
                               n.NetworkInterfaceType != NetworkInterfaceType.Tunnel)
            .ToArray();
        var adapter = adapters
            .OrderByDescending(HasGateway)
            .ThenByDescending(static n => n.Speed)
            .FirstOrDefault();

        if (adapter is null)
            return new NetworkDiagnosticSnapshot(NetworkInterface.GetIsNetworkAvailable(), "—", "Активный адаптер не найден", "—", "Нет подключения", "—", "—", "—", "—", "—", "Не выполнялся", "Не выполнялся", 0, DateTimeOffset.Now);

        var props = adapter.GetIPProperties();
        var ipv4 = props.UnicastAddresses.FirstOrDefault(static a => a.Address.AddressFamily == AddressFamily.InterNetwork)?.Address.ToString() ?? "—";
        var gateway = props.GatewayAddresses.FirstOrDefault(static g => g.Address.AddressFamily == AddressFamily.InterNetwork)?.Address.ToString() ?? "—";
        var dns = string.Join(", ", props.DnsAddresses.Where(static a => a.AddressFamily == AddressFamily.InterNetwork).Select(static a => a.ToString()));
        if (string.IsNullOrWhiteSpace(dns)) dns = "—";
        string dhcp;
        try { dhcp = props.GetIPv4Properties()?.IsDhcpEnabled == true ? "Включён" : "Статический / выключен"; }
        catch { dhcp = "Не удалось определить"; }

        var gatewayTest = await TestGatewayAsync(gateway, cancellationToken).ConfigureAwait(false);
        var dnsTest = await TestDnsAsync(cancellationToken).ConfigureAwait(false);
        return new NetworkDiagnosticSnapshot(
            NetworkInterface.GetIsNetworkAvailable(), adapter.Name, adapter.Description, adapter.NetworkInterfaceType.ToString(),
            adapter.OperationalStatus == OperationalStatus.Up ? "Подключён" : adapter.OperationalStatus.ToString(),
            FormatSpeed(adapter.Speed), ipv4, gateway, dns, dhcp, gatewayTest, dnsTest, adapters.Length, DateTimeOffset.Now);
    }

    public Task<NetworkRepairResult> FlushDnsAsync(CancellationToken cancellationToken = default) => ExecuteAsync("flush_dns", cancellationToken);
    public Task<NetworkRepairResult> RenewDhcpAsync(CancellationToken cancellationToken = default) => ExecuteAsync("renew_dhcp", cancellationToken);
    public Task<NetworkRepairResult> ResetWinsockAsync(CancellationToken cancellationToken = default) => ExecuteAsync("reset_winsock", cancellationToken);
    public Task<NetworkRepairResult> ResetTcpIpAsync(CancellationToken cancellationToken = default) => ExecuteAsync("reset_tcpip", cancellationToken);

    private Task<NetworkRepairResult> ExecuteAsync(string action, CancellationToken cancellationToken) => broker.ExecuteAsync<NetworkRepairResult>(new ElevatedOperationRequest
    {
        RequestId = Guid.NewGuid().ToString("N"), Kind = ElevatedOperationKind.NetworkRepair, NetworkAction = action
    }, cancellationToken);

    private static bool HasGateway(NetworkInterface adapter)
    {
        try { return adapter.GetIPProperties().GatewayAddresses.Any(static g => g.Address.AddressFamily == AddressFamily.InterNetwork); }
        catch { return false; }
    }

    private static async Task<string> TestGatewayAsync(string gateway, CancellationToken cancellationToken)
    {
        if (!IPAddress.TryParse(gateway, out var address)) return "Шлюз не определён";
        try
        {
            using var ping = new Ping();
            var reply = await ping.SendPingAsync(address, 1400).WaitAsync(TimeSpan.FromSeconds(2), cancellationToken).ConfigureAwait(false);
            return reply.Status == IPStatus.Success ? $"OK · {reply.RoundtripTime} мс" : $"Нет ответа · {reply.Status}";
        }
        catch (OperationCanceledException) { throw; }
        catch { return "Нет ответа"; }
    }

    private static async Task<string> TestDnsAsync(CancellationToken cancellationToken)
    {
        try
        {
            var addresses = await Dns.GetHostAddressesAsync("www.msftconnecttest.com").WaitAsync(TimeSpan.FromSeconds(4), cancellationToken).ConfigureAwait(false);
            return addresses.Length > 0 ? "OK · имена разрешаются" : "DNS не вернул адрес";
        }
        catch (OperationCanceledException) { throw; }
        catch { return "Ошибка разрешения DNS"; }
    }

    private static string FormatSpeed(long bitsPerSecond)
    {
        if (bitsPerSecond <= 0) return "—";
        var mbps = bitsPerSecond / 1_000_000d;
        return mbps >= 1000 ? $"{mbps / 1000:0.##} Гбит/с" : $"{mbps:0.#} Мбит/с";
    }
}
''')

# -----------------------------------------------------------------------------
# ViewModel network state/commands.
# -----------------------------------------------------------------------------
vm_path = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
vm = read(vm_path)
vm = rep(vm, 'using MerzoOptimizer.Core.Models;', 'using MerzoOptimizer.Core.Models;\nusing MerzoOptimizer.Core.Network;', 'vm using')
vm = rep(vm, '    private readonly IUpdateService _updateService;', '    private readonly IUpdateService _updateService;\n    private readonly INetworkRepairService _networkRepairService;', 'vm field')
vm = rep(vm, '    private string _powerLiveText = "Live-монитор ещё не запущен";', '''    private string _powerLiveText = "Live-монитор ещё не запущен";
    private bool _isNetworkBusy;
    private double _networkProgress;
    private string _networkStatusText = "Нажмите «Диагностика», чтобы проверить активное подключение.";
    private string _networkAdapterText = "—";
    private string _networkIpText = "—";
    private string _networkGatewayText = "—";
    private string _networkDnsText = "—";
    private string _networkDhcpText = "—";
    private string _networkSpeedText = "—";
    private string _networkGatewayTestText = "—";
    private string _networkDnsTestText = "—";
    private string _networkOperationText = "Repair Center готов. Никакие сетевые настройки автоматически не меняются.";''', 'network state')
vm = rep(vm, '        IPowerProfileService powerProfiles,\n        IUpdateService updateService)', '        IPowerProfileService powerProfiles,\n        IUpdateService updateService,\n        INetworkRepairService networkRepairService)', 'ctor parameter')
vm = rep(vm, '        _updateService = updateService;', '        _updateService = updateService;\n        _networkRepairService = networkRepairService;', 'ctor assignment')
vm = rep(vm, '        InstallUpdateCommand = new AsyncRelayCommand(InstallUpdateAsync, () => !IsUpdateBusy && _downloadedUpdate is { Success: true });', '''        InstallUpdateCommand = new AsyncRelayCommand(InstallUpdateAsync, () => !IsUpdateBusy && _downloadedUpdate is { Success: true });
        DiagnoseNetworkCommand = new AsyncRelayCommand(DiagnoseNetworkAsync, () => !IsNetworkBusy);
        FlushDnsCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Очистка DNS", "DNS-кэш будет очищен. Это не удаляет сетевые профили.", _networkRepairService.FlushDnsAsync, confirm: false), () => !IsNetworkBusy);
        RenewDhcpCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Обновление DHCP", "Сетевое соединение может кратковременно прерваться. Продолжить?", _networkRepairService.RenewDhcpAsync, confirm: true), () => !IsNetworkBusy);
        ResetWinsockCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Сброс Winsock", "Winsock будет возвращён к стандартному состоянию Windows. Может потребоваться перезагрузка. Продолжить?", _networkRepairService.ResetWinsockAsync, confirm: true), () => !IsNetworkBusy);
        ResetTcpIpCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Сброс TCP/IP", "TCP/IP стек будет сброшен встроенной командой Windows. Может потребоваться перезагрузка. Продолжить?", _networkRepairService.ResetTcpIpAsync, confirm: true), () => !IsNetworkBusy);
        RepairNetworkCommand = new AsyncRelayCommand(RepairNetworkAsync, () => !IsNetworkBusy);''', 'network commands')
vm = rep(vm, '    public AsyncRelayCommand InstallUpdateCommand { get; }', '''    public AsyncRelayCommand InstallUpdateCommand { get; }
    public AsyncRelayCommand DiagnoseNetworkCommand { get; }
    public AsyncRelayCommand FlushDnsCommand { get; }
    public AsyncRelayCommand RenewDhcpCommand { get; }
    public AsyncRelayCommand ResetWinsockCommand { get; }
    public AsyncRelayCommand ResetTcpIpCommand { get; }
    public AsyncRelayCommand RepairNetworkCommand { get; }''', 'command properties')
vm = rep(vm, '    public ObservableCollection<string> DeepScanSteps { get; } = [];', '    public ObservableCollection<string> DeepScanSteps { get; } = [];\n    public ObservableCollection<string> NetworkOperationSteps { get; } = [];', 'network steps')

prop_anchor = '    public string ProcessReductionStatusText\n'
network_props = r'''    public bool IsNetworkBusy
    {
        get => _isNetworkBusy;
        private set
        {
            if (!SetProperty(ref _isNetworkBusy, value)) return;
            DiagnoseNetworkCommand.RaiseCanExecuteChanged(); FlushDnsCommand.RaiseCanExecuteChanged(); RenewDhcpCommand.RaiseCanExecuteChanged();
            ResetWinsockCommand.RaiseCanExecuteChanged(); ResetTcpIpCommand.RaiseCanExecuteChanged(); RepairNetworkCommand.RaiseCanExecuteChanged();
        }
    }
    public double NetworkProgress { get => _networkProgress; private set => SetProperty(ref _networkProgress, value); }
    public string NetworkStatusText { get => _networkStatusText; private set => SetProperty(ref _networkStatusText, value); }
    public string NetworkAdapterText { get => _networkAdapterText; private set => SetProperty(ref _networkAdapterText, value); }
    public string NetworkIpText { get => _networkIpText; private set => SetProperty(ref _networkIpText, value); }
    public string NetworkGatewayText { get => _networkGatewayText; private set => SetProperty(ref _networkGatewayText, value); }
    public string NetworkDnsText { get => _networkDnsText; private set => SetProperty(ref _networkDnsText, value); }
    public string NetworkDhcpText { get => _networkDhcpText; private set => SetProperty(ref _networkDhcpText, value); }
    public string NetworkSpeedText { get => _networkSpeedText; private set => SetProperty(ref _networkSpeedText, value); }
    public string NetworkGatewayTestText { get => _networkGatewayTestText; private set => SetProperty(ref _networkGatewayTestText, value); }
    public string NetworkDnsTestText { get => _networkDnsTestText; private set => SetProperty(ref _networkDnsTestText, value); }
    public string NetworkOperationText { get => _networkOperationText; private set => SetProperty(ref _networkOperationText, value); }

'''
if prop_anchor not in vm: raise SystemExit('R37 network property anchor missing')
vm = vm.replace(prop_anchor, network_props + prop_anchor, 1)

method_anchor = '    private async Task RefreshPowerAsync'
network_methods = r'''    private async Task DiagnoseNetworkAsync()
    {
        if (IsNetworkBusy) return;
        IsNetworkBusy = true;
        NetworkProgress = 12;
        NetworkStatusText = "Проверяю активный адаптер, IP, шлюз и DNS…";
        try
        {
            var snapshot = await _dispatcher.RunAsync("Network diagnostics", token => _networkRepairService.DiagnoseAsync(token), _lifetimeCts.Token);
            ApplyNetworkSnapshot(snapshot);
            NetworkProgress = 100;
            NetworkOperationSteps.Clear();
            NetworkOperationSteps.Add($"✓ Адаптер: {snapshot.AdapterName} · {snapshot.Status} · {snapshot.LinkSpeed}");
            NetworkOperationSteps.Add($"✓ IPv4: {snapshot.IPv4} · шлюз: {snapshot.Gateway}");
            NetworkOperationSteps.Add($"{(snapshot.GatewayTest.StartsWith("OK", StringComparison.OrdinalIgnoreCase) ? "✓" : "!")} Шлюз: {snapshot.GatewayTest}");
            NetworkOperationSteps.Add($"{(snapshot.DnsTest.StartsWith("OK", StringComparison.OrdinalIgnoreCase) ? "✓" : "!")} DNS: {snapshot.DnsTest}");
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkStatusText = $"Ошибка диагностики: {ex.Message}";
            NetworkOperationText = "Диагностика не изменила настройки Windows.";
        }
        finally { IsNetworkBusy = false; }
    }

    private void ApplyNetworkSnapshot(NetworkDiagnosticSnapshot snapshot)
    {
        NetworkStatusText = snapshot.Summary;
        NetworkAdapterText = $"{snapshot.AdapterName} · {snapshot.AdapterDescription}";
        NetworkIpText = snapshot.IPv4;
        NetworkGatewayText = snapshot.Gateway;
        NetworkDnsText = snapshot.DnsServers;
        NetworkDhcpText = snapshot.Dhcp;
        NetworkSpeedText = snapshot.LinkSpeed;
        NetworkGatewayTestText = snapshot.GatewayTest;
        NetworkDnsTestText = snapshot.DnsTest;
        NetworkOperationText = $"Диагностика завершена {snapshot.CapturedAt:HH:mm:ss}. Проверка только читает состояние сети.";
    }

    private async Task RunNetworkActionAsync(string title, string warning, Func<CancellationToken, Task<NetworkRepairResult>> action, bool confirm)
    {
        if (IsNetworkBusy) return;
        if (confirm)
        {
            var answer = global::MerzoOptimizer.App.MerzoDialog.Show(warning, $"Merzo — {title}", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (answer != MessageBoxResult.Yes) return;
        }
        IsNetworkBusy = true; NetworkProgress = 10; NetworkOperationSteps.Clear();
        NetworkStatusText = $"{title}: выполняется…"; NetworkOperationText = warning;
        NetworkOperationSteps.Add($"▶ {title}: передано защищённому UAC-helper");
        try
        {
            var result = await _dispatcher.RunAsync($"Network repair: {title}", action, _lifetimeCts.Token);
            NetworkProgress = 100;
            NetworkOperationSteps[0] = $"{(result.Success ? "✓" : "!")} {title}: {result.Message}";
            NetworkStatusText = result.Success ? $"{title}: готово" : $"{title}: Windows сообщила об ошибке";
            NetworkOperationText = result.Message;
            global::MerzoOptimizer.App.MerzoDialog.Show(result.Message + (result.RebootRequired ? "\n\nРекомендуется перезагрузить Windows." : string.Empty), $"Merzo — {title}", MessageBoxButton.OK, result.Success ? MessageBoxImage.Information : MessageBoxImage.Warning);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkProgress = 0; NetworkStatusText = $"{title}: ошибка"; NetworkOperationText = ex.Message;
            NetworkOperationSteps.Add($"! {ex.Message}");
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.Message, $"Merzo — {title}", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally { IsNetworkBusy = false; }
    }

    private async Task RepairNetworkAsync()
    {
        if (IsNetworkBusy) return;
        var answer = global::MerzoOptimizer.App.MerzoDialog.Show(
            "Merzo выполнит безопасную последовательность встроенных команд Windows:\n\n1. Очистка DNS\n2. Обновление DHCP\n3. Сброс Winsock\n4. Сброс TCP/IP\n\nWi‑Fi профили, пароли, VPN-профили и IPv6 не удаляются. После Winsock/TCP-IP рекомендуется перезагрузка. Продолжить?",
            "Merzo — восстановление сети Windows", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (answer != MessageBoxResult.Yes) return;

        IsNetworkBusy = true; NetworkProgress = 0; NetworkOperationSteps.Clear();
        NetworkStatusText = "Восстанавливаю сетевой стек Windows…";
        var actions = new (string Name, Func<CancellationToken, Task<NetworkRepairResult>> Run)[]
        {
            ("Очистка DNS", _networkRepairService.FlushDnsAsync),
            ("Обновление DHCP", _networkRepairService.RenewDhcpAsync),
            ("Сброс Winsock", _networkRepairService.ResetWinsockAsync),
            ("Сброс TCP/IP", _networkRepairService.ResetTcpIpAsync)
        };
        foreach (var a in actions) NetworkOperationSteps.Add($"○ {a.Name}");
        var success = 0; var reboot = false;
        try
        {
            for (var i = 0; i < actions.Length; i++)
            {
                NetworkOperationSteps[i] = $"▶ {actions[i].Name}…";
                NetworkOperationText = $"Шаг {i + 1}/{actions.Length}: {actions[i].Name}";
                var r = await _dispatcher.RunAsync($"Network repair {i + 1}: {actions[i].Name}", actions[i].Run, _lifetimeCts.Token);
                if (r.Success) success++;
                reboot |= r.RebootRequired;
                NetworkOperationSteps[i] = $"{(r.Success ? "✓" : "!")} {actions[i].Name} · {r.Message}";
                NetworkProgress = (i + 1) * 100d / actions.Length;
            }
            NetworkStatusText = $"Восстановление сети завершено: {success}/{actions.Length} шагов успешно";
            NetworkOperationText = reboot ? "Операция завершена. Рекомендуется перезагрузка Windows." : "Операция завершена.";
            global::MerzoOptimizer.App.MerzoDialog.Show($"Восстановление сети завершено: {success}/{actions.Length} шагов.\n\nWi‑Fi/VPN профили не удалялись.{(reboot ? "\nРекомендуется перезагрузка Windows." : string.Empty)}", "Merzo — сеть восстановлена", MessageBoxButton.OK, success == actions.Length ? MessageBoxImage.Information : MessageBoxImage.Warning);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkStatusText = "Восстановление сети остановлено ошибкой"; NetworkOperationText = ex.Message;
            NetworkOperationSteps.Add($"! {ex.Message}");
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.Message, "Merzo — ошибка восстановления сети", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally { IsNetworkBusy = false; }
    }

'''
if method_anchor not in vm: raise SystemExit('R37 network method anchor missing')
vm = vm.replace(method_anchor, network_methods + method_anchor, 1)
write(vm_path, vm)

# -----------------------------------------------------------------------------
# App composition.
# -----------------------------------------------------------------------------
app_path = root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
app = read(app_path)
# add Windows.Network using near other Windows namespaces
using_candidates = [line for line in app.splitlines() if line.startswith('using MerzoOptimizer.Windows.')]
if 'using MerzoOptimizer.Windows.Network;' not in app:
    anchor = using_candidates[-1] if using_candidates else None
    if not anchor: raise SystemExit('R37 app Windows using anchor missing')
    app = app.replace(anchor, anchor + '\nusing MerzoOptimizer.Windows.Network;', 1)
app = rep(app, '            var updateService = new GitHubUpdateService();', '            var updateService = new GitHubUpdateService();\n            var networkRepairService = new WindowsNetworkRepairService(_elevationBroker);', 'network composition')
app = rep(app, '                powerProfiles,\n                updateService);', '                powerProfiles,\n                updateService,\n                networkRepairService);', 'network ctor arg')
write(app_path, app)

# -----------------------------------------------------------------------------
# Navigation + real Network tab.
# -----------------------------------------------------------------------------
xaml_path = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml_path)
placeholder = re.search(r'<TextBlock\s+Text="Repair / Network"[^>]*/>', x)
if not placeholder: raise SystemExit('R37 Repair / Network placeholder missing')
gaming = re.search(r'<RadioButton[^>]*x:Name="GamingDevNav"[^>]*/>', x)
if not gaming: raise SystemExit('R37 Gaming nav template missing')
nav = gaming.group(0)
nav = re.sub(r'x:Name="GamingDevNav"', 'x:Name="NetworkNav"', nav)
nav = re.sub(r'Content="[^"]*Gaming / Developer"', 'Content="⌁  Repair / Network"', nav)
nav = nav.replace('Click="GamingDev_Click"', 'Click="Network_Click"')
x = x[:placeholder.start()] + nav + x[placeholder.end():]

power_text = x.find('Text="Питание"')
if power_text < 0: power_text = x.find('Text="Power')
if power_text < 0: raise SystemExit('R37 power tab anchor missing')
power_tab = x.rfind('<TabItem', 0, power_text)
if power_tab < 0: raise SystemExit('R37 power TabItem start missing')
network_tab = r'''            <!-- R37 Repair / Network Center -->
            <TabItem>
                <Grid Margin="11,8,11,9">
                    <Grid.RowDefinitions><RowDefinition Height="43"/><RowDefinition Height="61"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                    <Grid Grid.Row="0">
                        <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                        <StackPanel><TextBlock Style="{StaticResource PageTitle}" Text="Repair / Network"/><TextBlock Text="Диагностика и штатное восстановление сетевого стека Windows — без сомнительных ping/TCP-хаков" Foreground="{StaticResource TextMuted}" FontSize="10.4"/></StackPanel>
                        <Button Grid.Column="1" Style="{StaticResource CompactPrimaryButton}" Command="{Binding DiagnoseNetworkCommand}" Content="Диагностика" MinWidth="108" VerticalAlignment="Center"/>
                    </Grid>
                    <Border Grid.Row="1" Background="#101B22" BorderBrush="#2A5A56" BorderThickness="1" CornerRadius="9" Padding="10,7" Margin="0,2,0,7">
                        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="115"/></Grid.ColumnDefinitions>
                            <StackPanel><TextBlock Text="{Binding NetworkStatusText, Mode=OneWay}" FontSize="11.5" FontWeight="SemiBold"/><TextBlock Text="{Binding NetworkOperationText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.7" Margin="0,2,8,0" TextTrimming="CharacterEllipsis"/></StackPanel>
                            <StackPanel Grid.Column="1" VerticalAlignment="Center"><TextBlock Text="{Binding NetworkProgress, StringFormat={}{0:0}%}" Foreground="#6FC1B7" FontSize="10.5" FontWeight="Bold" HorizontalAlignment="Right"/><ProgressBar Value="{Binding NetworkProgress}" Maximum="100" Height="5" Margin="0,4,0,0"/></StackPanel>
                        </Grid>
                    </Border>
                    <Grid Grid.Row="2"><Grid.ColumnDefinitions><ColumnDefinition Width="1.05*"/><ColumnDefinition Width="8"/><ColumnDefinition Width="0.95*"/></Grid.ColumnDefinitions>
                        <ScrollViewer Grid.Column="0" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
                            <StackPanel>
                                <Border Style="{StaticResource CardBorder}" Padding="11" Margin="0,0,0,7"><StackPanel>
                                    <TextBlock Text="Активное подключение" FontSize="12.5" FontWeight="SemiBold"/>
                                    <TextBlock Text="{Binding NetworkAdapterText}" Foreground="{StaticResource TextSecondary}" FontSize="10.5" Margin="0,3,0,7" TextWrapping="Wrap"/>
                                    <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="92"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions><Grid.RowDefinitions><RowDefinition/><RowDefinition/><RowDefinition/><RowDefinition/><RowDefinition/></Grid.RowDefinitions>
                                        <TextBlock Text="IPv4" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Column="1" Text="{Binding NetworkIpText}" FontWeight="SemiBold"/>
                                        <TextBlock Grid.Row="1" Text="Шлюз" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Row="1" Grid.Column="1" Text="{Binding NetworkGatewayText}"/>
                                        <TextBlock Grid.Row="2" Text="DNS" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Row="2" Grid.Column="1" Text="{Binding NetworkDnsText}" TextWrapping="Wrap"/>
                                        <TextBlock Grid.Row="3" Text="DHCP" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Row="3" Grid.Column="1" Text="{Binding NetworkDhcpText}"/>
                                        <TextBlock Grid.Row="4" Text="Скорость" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Row="4" Grid.Column="1" Text="{Binding NetworkSpeedText}"/>
                                    </Grid>
                                </StackPanel></Border>
                                <Border Style="{StaticResource CardBorder}" Padding="11"><StackPanel>
                                    <TextBlock Text="Проверка соединения" FontSize="12.2" FontWeight="SemiBold"/>
                                    <Grid Margin="0,7,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="100"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions><Grid.RowDefinitions><RowDefinition/><RowDefinition/></Grid.RowDefinitions>
                                        <TextBlock Text="Шлюз" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Column="1" Text="{Binding NetworkGatewayTestText}"/>
                                        <TextBlock Grid.Row="1" Text="DNS lookup" Foreground="{StaticResource TextMuted}"/><TextBlock Grid.Row="1" Grid.Column="1" Text="{Binding NetworkDnsTestText}"/>
                                    </Grid>
                                </StackPanel></Border>
                            </StackPanel>
                        </ScrollViewer>
                        <ScrollViewer Grid.Column="2" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
                            <StackPanel>
                                <Border Style="{StaticResource CardBorder}" Padding="11" Margin="0,0,0,7"><StackPanel>
                                    <TextBlock Text="Быстрый Repair" FontSize="12.5" FontWeight="SemiBold"/><TextBlock Text="Только встроенные команды Windows. UAC запрашивается в момент изменения." Foreground="{StaticResource TextMuted}" FontSize="9.8" TextWrapping="Wrap" Margin="0,2,0,8"/>
                                    <UniformGrid Columns="2" Rows="2">
                                        <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding FlushDnsCommand}" Content="Очистить DNS" Margin="0,0,5,5"/>
                                        <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding RenewDhcpCommand}" Content="Обновить DHCP" Margin="0,0,0,5"/>
                                        <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ResetWinsockCommand}" Content="Сбросить Winsock" Margin="0,0,5,0"/>
                                        <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ResetTcpIpCommand}" Content="Сбросить TCP/IP"/>
                                    </UniformGrid>
                                    <Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding RepairNetworkCommand}" Content="Восстановить сеть Windows" Margin="0,9,0,0" Height="36"/>
                                    <TextBlock Text="Не отключает IPv6, не меняет MTU/TCP autotuning и не удаляет Wi‑Fi/VPN профили. Winsock/TCP-IP reset может потребовать перезагрузку." Foreground="#B69A6A" FontSize="9.5" TextWrapping="Wrap" Margin="0,7,0,0"/>
                                </StackPanel></Border>
                                <Border Style="{StaticResource CardBorder}" Padding="10"><StackPanel><TextBlock Text="Ход восстановления" FontSize="11.8" FontWeight="SemiBold" Margin="0,0,0,6"/><ItemsControl ItemsSource="{Binding NetworkOperationSteps}"><ItemsControl.ItemTemplate><DataTemplate><Border Background="#121B24" BorderBrush="#23333D" BorderThickness="1" CornerRadius="7" Padding="7,5" Margin="0,0,0,4"><TextBlock Text="{Binding}" Foreground="{StaticResource TextSecondary}" FontSize="9.9" TextWrapping="Wrap"/></Border></DataTemplate></ItemsControl.ItemTemplate></ItemsControl></StackPanel></Border>
                            </StackPanel>
                        </ScrollViewer>
                    </Grid>
                </Grid>
            </TabItem>

'''
x = x[:power_tab] + network_tab + x[power_tab:]
write(xaml_path, x)

cs_path = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml.cs'
cs = read(cs_path)
cs = rep(cs, 'private void GamingDev_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 6;\n    private void Power_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 7;\n    private void Updates_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 8;\n    private void Restore_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 9;\n    private void Logs_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 10;', '''private void GamingDev_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 6;
    private void Network_Click(object sender, RoutedEventArgs e)
    {
        MainTabs.SelectedIndex = 7;
        if (DataContext is ViewModels.MainWindowViewModel vm && vm.DiagnoseNetworkCommand.CanExecute(null))
            vm.DiagnoseNetworkCommand.Execute(null);
    }
    private void Power_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 8;
    private void Updates_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 9;
    private void Restore_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 10;
    private void Logs_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 11;''', 'nav indices')
# Startup update notice must open shifted Updates tab.
cs = cs.replace('MainTabs.SelectedIndex = 8;', 'MainTabs.SelectedIndex = 9;', 1) if 'OpenUpdatesFromNotice_Click' in cs else cs
# The replace above may hit the new Power/Updates block if performed blindly; normalize exact handler afterwards.
cs = cs.replace('private void Power_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 9;', 'private void Power_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 8;')
# Ensure OpenUpdatesFromNotice body is 9 using regex.
cs = re.sub(r'(private void OpenUpdatesFromNotice_Click\([^)]*\)\s*\{.*?MainTabs\.SelectedIndex\s*=\s*)\d+(;)', r'\g<1>9\2', cs, flags=re.S)
write(cs_path, cs)

print('R37 Repair / Network Center patch: OK')
