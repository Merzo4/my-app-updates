using System.Diagnostics;
using System.Text;
using System.Text.Json;
using MerzoOptimizer.Core.Debloat;

namespace MerzoOptimizer.Windows.Debloat;

public sealed class WindowsDebloatScanner : IDebloatScanner
{
    private static readonly (string Id, string DisplayName, string PackageName, string Recommendation)[] Rules =
    [
        ("clipchamp", "Clipchamp", "Clipchamp.Clipchamp", "Можно удалить, если видеоредактор не используется. R20 пока только проверяет наличие: удаление будет включено после гарантированного Restore."),
        ("news", "Microsoft News", "Microsoft.BingNews", "Необязательное новостное приложение."),
        ("weather", "Microsoft Weather", "Microsoft.BingWeather", "Необязательно, если штатная погода не используется."),
        ("solitaire", "Microsoft Solitaire Collection", "Microsoft.MicrosoftSolitaireCollection", "Развлекательное приложение; кандидат LITE BUILD."),
        ("office_hub", "Microsoft 365 / Office Hub", "Microsoft.MicrosoftOfficeHub", "Опциональный hub; не удаляет установленный Office."),
        ("feedback_hub", "Feedback Hub", "Microsoft.WindowsFeedbackHub", "Опционально для обычного пользователя; полезно для отправки отзывов Microsoft."),
        ("maps", "Windows Maps", "Microsoft.WindowsMaps", "Опциональное приложение карт."),
        ("people", "Microsoft People", "Microsoft.People", "Опциональное приложение контактов старого поколения."),
        ("xbox_app", "Xbox app", "Microsoft.GamingApp", "Кандидат LITE BUILD, если Xbox/Game Pass не используется."),
        ("xbox_overlay", "Xbox Game Bar", "Microsoft.XboxGamingOverlay", "Кандидат LITE BUILD, если Game Bar и запись игр не нужны."),
        ("xbox_identity", "Xbox Identity Provider", "Microsoft.XboxIdentityProvider", "Удалять только если точно не используются Xbox/Microsoft Store игры."),
        ("xbox_speech", "Xbox Speech To Text Overlay", "Microsoft.XboxSpeechToTextOverlay", "Опциональный Xbox-компонент."),
        ("get_help", "Get Help", "Microsoft.GetHelp", "Опциональное приложение поддержки."),
        ("get_started", "Get Started / Tips", "Microsoft.Getstarted", "Опциональные советы Windows."),
        ("phone_link", "Phone Link", "Microsoft.YourPhone", "Кандидат, если связь телефона с ПК не используется."),
        ("teams", "Microsoft Teams", "MSTeams", "Кандидат, если Teams не используется."),
        ("dev_home", "Dev Home", "Microsoft.Windows.DevHome", "Опционально; оставить разработчикам, которым нужен Dev Home."),
        ("todo", "Microsoft To Do", "Microsoft.Todos", "Опциональный менеджер задач."),
        ("sound_recorder", "Sound Recorder", "Microsoft.WindowsSoundRecorder", "Опциональное приложение записи звука."),
        ("cortana_legacy", "Cortana (legacy)", "Microsoft.549981C3F5F10", "Старый Cortana package; кандидат при наличии на поддерживаемой Windows."),
        ("zune_music", "Media Player / Groove package", "Microsoft.ZuneMusic", "Мультимедийное приложение; удалять только если есть замена."),
        ("zune_video", "Movies & TV", "Microsoft.ZuneVideo", "Опциональный видеоплеер."),
        ("quick_assist", "Quick Assist", "MicrosoftCorporationII.QuickAssist", "Оставить, если нужна удалённая помощь; иначе опционально."),
        ("power_automate", "Power Automate", "Microsoft.PowerAutomateDesktop", "Опционально, если desktop automation не используется.")
    ];

    public async Task<IReadOnlyList<DebloatAppSnapshot>> ScanAsync(CancellationToken cancellationToken = default)
    {
        var installed = await ReadInstalledPackageNamesAsync(cancellationToken).ConfigureAwait(false);

        return Rules.Select(rule => new DebloatAppSnapshot
        {
            Id = rule.Id,
            DisplayName = rule.DisplayName,
            PackageName = rule.PackageName,
            Installed = installed.Contains(rule.PackageName),
            Status = installed.Contains(rule.PackageName) ? "Установлено" : "Не найдено",
            Recommendation = rule.Recommendation,
            RemovalEnabled = false
        }).ToArray();
    }

    private static async Task<HashSet<string>> ReadInstalledPackageNamesAsync(CancellationToken cancellationToken)
    {
        const string command = "$OutputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); " +
                               "Get-AppxPackage | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress";

        var startInfo = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"{command}\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Не удалось запустить PowerShell для Appx-аудита.");

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        try
        {
            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch { }
            throw;
        }
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);

        if (process.ExitCode != 0)
            throw new InvalidOperationException($"Get-AppxPackage завершился с кодом {process.ExitCode}: {stderr.Trim()}");

        var result = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (string.IsNullOrWhiteSpace(stdout))
            return result;

        using var json = JsonDocument.Parse(stdout);
        if (json.RootElement.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in json.RootElement.EnumerateArray())
                if (item.ValueKind == JsonValueKind.String && item.GetString() is { Length: > 0 } name)
                    result.Add(name);
        }
        else if (json.RootElement.ValueKind == JsonValueKind.String && json.RootElement.GetString() is { Length: > 0 } single)
        {
            result.Add(single);
        }

        return result;
    }
}
