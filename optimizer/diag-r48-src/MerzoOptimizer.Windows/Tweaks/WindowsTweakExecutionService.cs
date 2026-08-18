using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Safety;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;
using MerzoOptimizer.Windows.RegistryAccess;
using MerzoOptimizer.Windows.SystemInfo;

namespace MerzoOptimizer.Windows.Tweaks;

public sealed class WindowsTweakExecutionService : ITweakExecutionService
{
    private readonly ISnapshotService _snapshots;
    private readonly IRestoreService _restore;
    private readonly ISafetyEngine _safety;
    private readonly IAuditLogger _logger;
    private readonly RegistryTweakAccessor _registry = new();

    public WindowsTweakExecutionService(
        ISnapshotService snapshots,
        IRestoreService restore,
        ISafetyEngine safety,
        IAuditLogger logger)
    {
        _snapshots = snapshots;
        _restore = restore;
        _safety = safety;
        _logger = logger;
    }

    public Task<TweakStateResult> GetStateAsync(
        TweakDefinition tweak,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var windowsBuild = Environment.OSVersion.Version.Build;
        if (tweak.MinWindowsBuild is int minBuild && windowsBuild < minBuild)
        {
            return Task.FromResult(new TweakStateResult
            {
                State = TweakState.Unknown,
                DisplayText = "Недоступен",
                Details = $"Требуется Windows build {minBuild}+; текущий build {windowsBuild}.",
                IsSupported = false
            });
        }

        if (tweak.RegistryActions.Count == 0)
        {
            return Task.FromResult(new TweakStateResult
            {
                State = TweakState.Unknown,
                DisplayText = "Нет действий",
                Details = "В каталоге отсутствуют registry_actions."
            });
        }

        var matches = tweak.RegistryActions.Count(_registry.MatchesDesiredValue);
        var state = matches switch
        {
            0 => TweakState.NotApplied,
            _ when matches == tweak.RegistryActions.Count => TweakState.Applied,
            _ => TweakState.Mixed
        };

        return Task.FromResult(new TweakStateResult
        {
            State = state,
            DisplayText = state switch
            {
                TweakState.Applied => "Применён",
                TweakState.NotApplied => "Не применён",
                TweakState.Mixed => "Частично",
                _ => "Неизвестно"
            },
            Details = $"Совпадает {matches} из {tweak.RegistryActions.Count} значений."
        });
    }

    public async Task<TweakApplyResult> ApplyAsync(
        TweakDefinition tweak,
        CancellationToken cancellationToken = default)
    {
        if (tweak.ScanOnly)
        {
            return new TweakApplyResult
            {
                Success = false,
                Changed = false,
                Message = "Этот известный твик добавлен в базу только для обнаружения. Автоприменение намеренно заблокировано."
            };
        }

        var safety = _safety.Evaluate(tweak, AdminService.IsAdministrator(), Environment.OSVersion.Version.Build);
        if (!safety.Allowed)
        {
            await LogResultAsync(tweak, "Blocked", safety.Message, cancellationToken).ConfigureAwait(false);
            return new TweakApplyResult
            {
                Success = false,
                Changed = false,
                Message = safety.Message
            };
        }

        var current = await GetStateAsync(tweak, cancellationToken).ConfigureAwait(false);
        if (current.State == TweakState.Applied)
        {
            return new TweakApplyResult
            {
                Success = true,
                Changed = false,
                Message = "Твик уже находится в целевом состоянии."
            };
        }

        var snapshot = await _snapshots.CreateForTweakAsync(
            tweak,
            $"Перед применением {tweak.Name}",
            cancellationToken).ConfigureAwait(false);

        try
        {
            foreach (var action in tweak.RegistryActions)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var oldEntry = _registry.Capture(action);
                _registry.Apply(action);

                await _logger.WriteAsync(new AuditLogEntry
                {
                    Category = "Tweak",
                    Action = $"Apply registry {action.Hive}\\{action.KeyPath}\\{action.ValueName}",
                    Status = "Success",
                    TweakId = tweak.Id,
                    OldValue = RegistryTweakAccessor.Describe(oldEntry),
                    NewValue = RegistryTweakAccessor.Describe(action),
                    Details = $"Snapshot {snapshot.Id} создан до изменения."
                }, cancellationToken).ConfigureAwait(false);
            }

            await LogResultAsync(tweak, "Success", $"Применён. Snapshot {snapshot.Id}", cancellationToken)
                .ConfigureAwait(false);

            return new TweakApplyResult
            {
                Success = true,
                Changed = true,
                SnapshotId = snapshot.Id,
                Message = $"Применено с защитным snapshot. Snapshot: {snapshot.Id.ToString()[..8]}."
            };
        }
        catch (Exception ex)
        {
            var rollback = await _restore.RestoreAsync(snapshot.Id, CancellationToken.None).ConfigureAwait(false);
            var details = rollback.Success
                ? $"Применение не удалось; автоматический rollback выполнен. {ex}"
                : $"Применение не удалось; rollback тоже завершился ошибкой: {rollback.Message}. {ex}";

            await LogResultAsync(tweak, "Error", details, CancellationToken.None).ConfigureAwait(false);

            return new TweakApplyResult
            {
                Success = false,
                Changed = false,
                SnapshotId = snapshot.Id,
                Message = rollback.Success
                    ? $"Ошибка применения. Исходное состояние автоматически восстановлено: {ex.Message}"
                    : $"Ошибка применения и rollback: {ex.Message} / {rollback.Message}"
            };
        }
    }

    private Task LogResultAsync(
        TweakDefinition tweak,
        string status,
        string details,
        CancellationToken cancellationToken) =>
        _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Tweak",
            Action = tweak.Name,
            Status = status,
            TweakId = tweak.Id,
            Details = details
        }, cancellationToken);
}
