using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Core.Audit;

public interface ISystemAuditService
{
    Task<SystemAuditSnapshot> RunAsync(CancellationToken cancellationToken = default);
}
