using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Core.Safety;

public sealed record SafetyCheckResult
{
    public bool Allowed { get; init; }
    public required string Message { get; init; }
}

public interface ISafetyEngine
{
    SafetyCheckResult Evaluate(TweakDefinition tweak, bool isAdministrator, int windowsBuild);
}

public sealed class SafetyEngine : ISafetyEngine
{
    public SafetyCheckResult Evaluate(TweakDefinition tweak, bool isAdministrator, int windowsBuild)
    {
        if (tweak.Risk is TweakRisk.Advanced or TweakRisk.Expert)
        {
            return new SafetyCheckResult
            {
                Allowed = false,
                Message = "R20 не применяет ADVANCED/EXPERT автоматически. Эти уровни будут доступны только в отдельном ручном режиме."
            };
        }

        if (tweak.RegistryActions.Count == 0)
        {
            return new SafetyCheckResult
            {
                Allowed = false,
                Message = "У твика нет документированных действий для применения."
            };
        }

        if (tweak.RequiresAdmin && !isAdministrator)
        {
            return new SafetyCheckResult
            {
                Allowed = false,
                Message = "Для этого изменения нужны права администратора."
            };
        }

        if (tweak.MinWindowsBuild is int minBuild && windowsBuild < minBuild)
        {
            return new SafetyCheckResult
            {
                Allowed = false,
                Message = $"Твик требует Windows build {minBuild} или новее. Текущий build: {windowsBuild}."
            };
        }

        return new SafetyCheckResult
        {
            Allowed = true,
            Message = tweak.Risk == TweakRisk.Balanced
                ? "BALANCED совместим: требуется явное подтверждение пользователя; перед изменением будет создан snapshot."
                : "SAFE совместим: перед изменением будет создан snapshot."
        };
    }
}
