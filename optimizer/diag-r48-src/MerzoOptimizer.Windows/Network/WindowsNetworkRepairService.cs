using System.Net;
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
    public Task<NetworkRepairResult> ApplyGamingNetworkSafeAsync(CancellationToken cancellationToken = default) => ExecuteAsync("gaming_network_safe", cancellationToken);
    public Task<NetworkRepairResult> ApplyGamingNetworkExtremeAsync(CancellationToken cancellationToken = default) => ExecuteAsync("gaming_network_extreme", cancellationToken);
    public Task<NetworkRepairResult> RestoreGamingNetworkAsync(CancellationToken cancellationToken = default) => ExecuteAsync("restore_gaming_network", cancellationToken);

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
