namespace MerzoOptimizer.Core.Network;

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
    Task<NetworkRepairResult> ApplyGamingNetworkSafeAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> ApplyGamingNetworkExtremeAsync(CancellationToken cancellationToken = default);
    Task<NetworkRepairResult> RestoreGamingNetworkAsync(CancellationToken cancellationToken = default);
}
