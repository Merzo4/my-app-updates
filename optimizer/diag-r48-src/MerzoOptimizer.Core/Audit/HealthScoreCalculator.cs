using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Core.Audit;

public sealed class HealthScoreCalculator
{
    public HealthScoreResult Calculate(
        MemorySnapshot memory,
        int processCount,
        IReadOnlyList<StartupItemSnapshot> startup,
        IReadOnlyList<StorageSnapshot> storage,
        string systemDrive)
    {
        var score = 100;
        var notes = new List<string>();

        if (memory.UsedPercent >= 90)
        {
            score -= 15;
            notes.Add("RAM используется на 90% или больше: −15.");
        }
        else if (memory.UsedPercent >= 80)
        {
            score -= 8;
            notes.Add("RAM используется на 80% или больше: −8.");
        }
        else if (memory.UsedPercent >= 70)
        {
            score -= 4;
            notes.Add("RAM используется на 70% или больше: −4.");
        }
        else
        {
            notes.Add($"Использование RAM {memory.UsedPercent:F1}% — штрафа нет.");
        }

        if (startup.Count > 15)
        {
            var deduction = Math.Min(20, (startup.Count - 15) * 2);
            score -= deduction;
            notes.Add($"Автозагрузка содержит {startup.Count} элементов: −{deduction}.");
        }
        else if (startup.Count > 10)
        {
            score -= 4;
            notes.Add($"Автозагрузка содержит {startup.Count} элементов: −4.");
        }
        else
        {
            notes.Add($"Автозагрузка: {startup.Count} элементов — штрафа нет.");
        }

        // Process count is only a weak signal. Modern Windows legitimately runs many processes,
        // so it contributes only a small deduction at high counts.
        if (processCount >= 300)
        {
            score -= 12;
            notes.Add($"Активно {processCount} процессов: −12. Требуется разбор фоновых потребителей.");
        }
        else if (processCount >= 230)
        {
            score -= 7;
            notes.Add($"Активно {processCount} процессов: −7. Это повышенный фон, но не приговор само по себе.");
        }
        else if (processCount >= 180)
        {
            score -= 3;
            notes.Add($"Активно {processCount} процессов: −3. Количество процессов учитывается с малым весом.");
        }
        else
        {
            notes.Add($"Активно {processCount} процессов — штрафа нет.");
        }

        var normalizedSystemDrive = NormalizeDrive(systemDrive);
        var systemDisk = storage.FirstOrDefault(s => NormalizeDrive(s.Name) == normalizedSystemDrive);
        if (systemDisk is not null)
        {
            if (systemDisk.FreePercent < 10)
            {
                score -= 20;
                notes.Add("На системном диске свободно меньше 10%: −20.");
            }
            else if (systemDisk.FreePercent < 20)
            {
                score -= 10;
                notes.Add("На системном диске свободно меньше 20%: −10.");
            }
            else
            {
                notes.Add($"На системном диске свободно {systemDisk.FreePercent:F1}% — штрафа нет.");
            }
        }

        score = Math.Clamp(score, 0, 100);
        var rating = score switch
        {
            >= 95 => "Отличное состояние",
            >= 85 => "Хорошее состояние",
            >= 70 => "Есть что оптимизировать",
            >= 50 => "Требует внимания",
            _ => "Нужна диагностика"
        };

        return new HealthScoreResult(score, rating, notes);
    }

    private static string NormalizeDrive(string? value) =>
        (value ?? string.Empty).Trim().TrimEnd('\\').ToUpperInvariant();
}
