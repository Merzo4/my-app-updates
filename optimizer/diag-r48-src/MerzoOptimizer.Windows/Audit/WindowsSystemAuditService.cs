using MerzoOptimizer.Core.Audit;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Models;
using MerzoOptimizer.Windows.Power;
using MerzoOptimizer.Windows.Startup;
using MerzoOptimizer.Windows.Storage;
using MerzoOptimizer.Windows.SystemInfo;

namespace MerzoOptimizer.Windows.Audit;

public sealed class WindowsSystemAuditService : ISystemAuditService
{
    private readonly IAuditLogger _logger;
    private readonly HealthScoreCalculator _healthScoreCalculator = new();

    public WindowsSystemAuditService(IAuditLogger logger)
    {
        _logger = logger;
    }

    public async Task<SystemAuditSnapshot> RunAsync(CancellationToken cancellationToken = default)
    {
        if (!OperatingSystem.IsWindows())
            throw new PlatformNotSupportedException("Merzo Windows Optimizer audit requires Windows.");

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Audit",
            Action = "SystemAudit",
            Status = "Started",
            Details = "Read-only Stage 1 Audit 2.0 started."
        }, cancellationToken).ConfigureAwait(false);

        try
        {
            var windows = WindowsInfoReader.Read();
            var memory = WindowsMemoryReader.Read();
            var cpuTask = HardwareInfoReader.ReadCpuAsync(cancellationToken);
            var gpus = HardwareInfoReader.ReadGpus();
            var processes = ProcessScanner.Scan();
            var isAdmin = AdminService.IsAdministrator();
            var startup = StartupScanner.Scan();
            var storage = StorageScanner.Scan();
            var powerPlan = await PowerPlanReader.ReadActivePlanAsync(cancellationToken).ConfigureAwait(false);
            var cpu = await cpuTask.ConfigureAwait(false);
            var systemDrive = Path.GetPathRoot(Environment.SystemDirectory) ?? "C:\\";

            var health = _healthScoreCalculator.Calculate(
                memory,
                processes.TotalCount,
                startup,
                storage,
                systemDrive);

            var snapshot = new SystemAuditSnapshot
            {
                Windows = windows,
                Cpu = cpu,
                Gpus = gpus,
                Memory = memory,
                ProcessCount = processes.TotalCount,
                SystemProcessCount = processes.SystemCount,
                UserProcessCount = processes.UserCount,
                TopProcesses = processes.TopProcesses,
                IsAdministrator = isAdmin,
                ActivePowerPlan = powerPlan,
                StartupItems = startup,
                Storage = storage,
                Health = health
            };

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Audit",
                Action = "SystemAudit",
                Status = "Completed",
                Details = $"CPU={cpu.Name}; CPUUsage={cpu.UsagePercent:F1}%; Processes={processes.TotalCount}; Startup={startup.Count}; RAM={memory.UsedPercent:F1}%; Health={health.Score}"
            }, cancellationToken).ConfigureAwait(false);

            return snapshot;
        }
        catch (Exception ex)
        {
            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Audit",
                Action = "SystemAudit",
                Status = "Failed",
                Details = ex.ToString()
            }, CancellationToken.None).ConfigureAwait(false);

            throw;
        }
    }
}
