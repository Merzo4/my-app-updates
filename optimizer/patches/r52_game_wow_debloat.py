from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R52 GAME WOW {label} anchor count={c}')
    return s.replace(old,new,1)

# -----------------------------------------------------------------------------
# 1) Catalog: GAME 2.0 inherits the reviewed aggressive process-reduction
# registry rules. EXTREME keeps the process_lite tail. Critical anti-patterns
# remain excluded.
# -----------------------------------------------------------------------------
tp=root/'data'/'tweaks.json'
tweaks=json.loads(read(tp))
for t in tweaks:
    if t.get('scan_only'): continue
    tags=t.setdefault('profile_tags',[])
    if 'process_aggressive' in tags and 'merzo_game' not in tags:
        tags.append('merzo_game')
    if 'merzo_game' in tags and 'merzo_extreme' not in tags:
        tags.append('merzo_extreme')

for forbidden in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    for t in tweaks:
        if t.get('id')==forbidden:
            t['profile_tags']=[x for x in (t.get('profile_tags') or []) if x not in ('merzo_light','merzo_game','merzo_extreme')]
write(tp,json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n')

# Additional service sources: only known services and only when the VM decides
# the related feature is not being used.
sp=root/'data'/'service_rules.json'
services=json.loads(read(sp))
known={str(x.get('service_name','')).lower() for x in services}
extra=[
 ('RetailDemo','Retail Demo Service','SAFE','На обычном пользовательском ПК режим Retail Demo не нужен.','Не отключать на демонстрационных стендах магазина.'),
 ('PhoneSvc','Phone Service','BALANCED','Можно отключать после удаления Phone Link в GAME.','Не отключать, если используется связь телефона с Windows.'),
 ('XblAuthManager','Xbox Live Auth Manager','BALANCED','Можно отключить, если Xbox/Game Pass не используется.','Нужна Xbox/Game Pass и некоторым Microsoft Store играм.'),
 ('XblGameSave','Xbox Live Game Save','BALANCED','Можно отключить без Xbox/Game Pass cloud saves.','Нужна облачным Xbox-сохранениям.'),
 ('XboxNetApiSvc','Xbox Live Networking Service','BALANCED','Можно отключить без Xbox multiplayer/Game Pass.','Нужна Xbox сетевым сценариям.'),
 ('XboxGipSvc','Xbox Accessory Management Service','BALANCED','Можно отключить без Xbox/Game Pass/Xbox accessory scenarios.','Некоторым Xbox-устройствам и играм может быть нужна.'),
]
for name,display,risk,rec,note in extra:
    if name.lower() not in known:
        services.append({'service_name':name,'display_name':display,'risk':risk,'recommendation':rec,'compatibility_note':note})
        known.add(name.lower())
write(sp,json.dumps(services,ensure_ascii=False,indent=2)+'\n')

# -----------------------------------------------------------------------------
# 2) Elevation protocol: fixed GAME debloat operation. UI sends only the mode;
# the elevated helper owns the immutable package allow-list.
# -----------------------------------------------------------------------------
ep=root/'src'/'MerzoOptimizer.Core'/'Elevation'/'ElevationModels.cs'
e=read(ep)
e=once(e,'    UninstallOneDrive,\n    Shutdown','    UninstallOneDrive,\n    GamingDebloat,\n    Shutdown','elevation enum')
write(ep,e)

# -----------------------------------------------------------------------------
# 3) Windows service: read-only package inspection without elevation; mutation
# goes through the allow-listed helper. Never touches user documents.
# -----------------------------------------------------------------------------
gp=root/'src'/'MerzoOptimizer.Windows'/'Gaming'/'WindowsGamingDebloatService.cs'
write(gp,r'''using System.Diagnostics;
using System.Text;
using System.Text.Json;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Windows.Elevation;

namespace MerzoOptimizer.Windows.Gaming;

public sealed record GamingDebloatStatus(
    string Mode,
    int RemovableCount,
    bool XboxGamingInstalled,
    IReadOnlyList<string> RemovablePackages,
    string Summary);

public sealed record GamingDebloatResult(
    bool Success,
    int RemovedCount,
    int FailedCount,
    IReadOnlyList<string> RemovedPackages,
    IReadOnlyList<string> FailedPackages,
    string Message);

public interface IGamingDebloatService
{
    Task<GamingDebloatStatus> InspectAsync(string mode, CancellationToken cancellationToken = default);
    Task<GamingDebloatResult> ApplyAsync(string mode, CancellationToken cancellationToken = default);
}

public sealed class WindowsGamingDebloatService : IGamingDebloatService
{
    private readonly ElevatedOperationBroker _broker;

    private static readonly string[] LightTargets =
    [
        "Microsoft.MicrosoftSolitaireCollection",
        "Clipchamp.Clipchamp",
        "Microsoft.GetHelp",
        "Microsoft.Getstarted",
        "Microsoft.WindowsFeedbackHub",
        "Microsoft.MicrosoftOfficeHub",
        "Microsoft.BingNews",
        "Microsoft.BingWeather"
    ];

    private static readonly string[] GameTargets =
    [
        ..LightTargets,
        "Microsoft.OutlookForWindows",
        "MSTeams",
        "MicrosoftTeams",
        "Microsoft.YourPhone",
        "Microsoft.People",
        "Microsoft.WindowsMaps",
        "Microsoft.549981C3F5F10"
    ];

    private static readonly string[] ExtremeTargets =
    [
        ..GameTargets,
        "Microsoft.ZuneMusic",
        "Microsoft.ZuneVideo",
        "MicrosoftCorporationII.MicrosoftFamily",
        "Microsoft.Windows.DevHome"
    ];

    private static readonly string[] XboxSignals =
    [
        "Microsoft.GamingApp",
        "Microsoft.XboxApp",
        "Microsoft.XboxGamingOverlay",
        "Microsoft.XboxIdentityProvider",
        "Microsoft.XboxGameOverlay",
        "Microsoft.XboxSpeechToTextOverlay"
    ];

    public WindowsGamingDebloatService(ElevatedOperationBroker broker) => _broker = broker;

    public async Task<GamingDebloatStatus> InspectAsync(string mode, CancellationToken cancellationToken = default)
    {
        mode = NormalizeMode(mode);
        var installed = await ReadInstalledPackageNamesAsync(cancellationToken).ConfigureAwait(false);
        var target = Targets(mode);
        var removable = installed.Where(x => target.Contains(x, StringComparer.OrdinalIgnoreCase)).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(x => x).ToArray();
        var xbox = installed.Any(x => XboxSignals.Contains(x, StringComparer.OrdinalIgnoreCase));
        return new GamingDebloatStatus(mode, removable.Length, xbox, removable,
            removable.Length == 0
                ? $"{mode}: consumer Appx уже очищены."
                : $"{mode}: найдено {removable.Length} consumer Appx для удаления; Xbox/Game Pass {(xbox ? "обнаружен — Xbox-службы сохраняются" : "не обнаружен")}." );
    }

    public async Task<GamingDebloatResult> ApplyAsync(string mode, CancellationToken cancellationToken = default)
    {
        mode = NormalizeMode(mode);
        var result = await _broker.ExecuteAsync<JsonElement>(new ElevatedOperationRequest
        {
            RequestId = Guid.NewGuid().ToString("N"),
            Kind = ElevatedOperationKind.GamingDebloat,
            DisplayName = mode
        }, cancellationToken).ConfigureAwait(false);

        static string[] ReadArray(JsonElement root, string name) =>
            root.TryGetProperty(name, out var el) && el.ValueKind == JsonValueKind.Array
                ? el.EnumerateArray().Select(x => x.GetString()).Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => x!).ToArray()
                : Array.Empty<string>();

        var removed = ReadArray(result, "removed");
        var failed = ReadArray(result, "failed");
        var message = result.TryGetProperty("message", out var msg) ? msg.GetString() ?? "Gaming Debloat completed." : "Gaming Debloat completed.";
        return new GamingDebloatResult(true, removed.Length, failed.Length, removed, failed, message);
    }

    private static string NormalizeMode(string value)
    {
        var mode=(value ?? string.Empty).Trim().ToUpperInvariant();
        return mode switch { "LIGHT" or "GAME" or "EXTREME" => mode, _ => throw new InvalidDataException("Gaming Debloat mode is not allow-listed.") };
    }

    private static string[] Targets(string mode) => mode switch
    {
        "LIGHT" => LightTargets,
        "GAME" => GameTargets,
        "EXTREME" => ExtremeTargets,
        _ => Array.Empty<string>()
    };

    private static async Task<HashSet<string>> ReadInstalledPackageNamesAsync(CancellationToken cancellationToken)
    {
        const string script = "$ErrorActionPreference='Stop'; Get-AppxPackage | Select-Object -ExpandProperty Name | Sort-Object -Unique | ConvertTo-Json -Compress";
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
        using var p = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить read-only Appx audit.");
        var stdoutTask=p.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask=p.StandardError.ReadToEndAsync(cancellationToken);
        await p.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout=await stdoutTask.ConfigureAwait(false);
        var stderr=await stderrTask.ConfigureAwait(false);
        if(p.ExitCode!=0) throw new InvalidOperationException("Appx audit: "+stderr.Trim());
        var set=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if(string.IsNullOrWhiteSpace(stdout)) return set;
        using var doc=JsonDocument.Parse(stdout);
        if(doc.RootElement.ValueKind==JsonValueKind.Array)
            foreach(var x in doc.RootElement.EnumerateArray()) if(x.ValueKind==JsonValueKind.String && !string.IsNullOrWhiteSpace(x.GetString())) set.Add(x.GetString()!);
        else if(doc.RootElement.ValueKind==JsonValueKind.String && !string.IsNullOrWhiteSpace(doc.RootElement.GetString())) set.Add(doc.RootElement.GetString()!);
        return set;
    }
}
''')

# -----------------------------------------------------------------------------
# 4) Elevated helper implementation: current-user Appx only. No -AllUsers and
# no Remove-AppxProvisionedPackage. Protected/system packages are absent from
# every list by construction.
# -----------------------------------------------------------------------------
hp=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=read(hp)
h=once(h,
'''            ElevatedOperationKind.UninstallOneDrive => await UninstallOneDriveAsync().ConfigureAwait(false),\n\n            _ => throw new NotSupportedException($"Unsupported elevated operation: {request.Kind}")''',
'''            ElevatedOperationKind.UninstallOneDrive => await UninstallOneDriveAsync().ConfigureAwait(false),\n\n            ElevatedOperationKind.GamingDebloat => await GamingDebloatAsync(request.DisplayName).ConfigureAwait(false),\n\n            _ => throw new NotSupportedException($"Unsupported elevated operation: {request.Kind}")''',
'helper switch')
anchor='''    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeout)\n'''
if anchor not in h: raise SystemExit('R52 helper fixed PowerShell anchor missing')
method=r'''    private static async Task<object> GamingDebloatAsync(string? rawMode)
    {
        var mode=(rawMode ?? string.Empty).Trim().ToUpperInvariant();
        if(mode is not ("LIGHT" or "GAME" or "EXTREME")) throw new InvalidDataException("Gaming Debloat mode failed allow-list.");

        string[] light = [
            "Microsoft.MicrosoftSolitaireCollection","Clipchamp.Clipchamp","Microsoft.GetHelp","Microsoft.Getstarted",
            "Microsoft.WindowsFeedbackHub","Microsoft.MicrosoftOfficeHub","Microsoft.BingNews","Microsoft.BingWeather"
        ];
        string[] game = [..light,"Microsoft.OutlookForWindows","MSTeams","MicrosoftTeams","Microsoft.YourPhone","Microsoft.People","Microsoft.WindowsMaps","Microsoft.549981C3F5F10"];
        string[] extreme = [..game,"Microsoft.ZuneMusic","Microsoft.ZuneVideo","MicrosoftCorporationII.MicrosoftFamily","Microsoft.Windows.DevHome"];
        var targets = mode == "LIGHT" ? light : mode == "GAME" ? game : extreme;

        static string PsQuote(string x) => "'" + x.Replace("'", "''", StringComparison.Ordinal) + "'";
        var literal = string.Join(",", targets.Select(PsQuote));
        var script = string.Join(Environment.NewLine, new[]
        {
            "$ErrorActionPreference='Stop'",
            "$targets=@("+literal+")",
            "$removed=New-Object System.Collections.Generic.List[string]",
            "$failed=New-Object System.Collections.Generic.List[string]",
            "foreach($name in $targets){",
            "  $items=@(Get-AppxPackage -Name $name -ErrorAction SilentlyContinue)",
            "  foreach($pkg in $items){ try { Remove-AppxPackage -Package $pkg.PackageFullName -ErrorAction Stop; $removed.Add($pkg.Name) } catch { $failed.Add($pkg.Name) } }",
            "}",
            "[pscustomobject]@{removed=@($removed);failed=@($failed)} | ConvertTo-Json -Compress"
        });
        var output=await RunFixedPowerShellAsync(script,TimeSpan.FromMinutes(4)).ConfigureAwait(false);
        var line=output.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).LastOrDefault(x=>x.TrimStart().StartsWith("{",StringComparison.Ordinal));
        if(string.IsNullOrWhiteSpace(line)) throw new InvalidOperationException("Gaming Debloat helper did not return JSON result.");
        using var doc=JsonDocument.Parse(line);
        string[] Arr(string n) => doc.RootElement.TryGetProperty(n,out var x) && x.ValueKind==JsonValueKind.Array ? x.EnumerateArray().Select(v=>v.GetString()).Where(v=>!string.IsNullOrWhiteSpace(v)).Select(v=>v!).Distinct(StringComparer.OrdinalIgnoreCase).ToArray() : Array.Empty<string>();
        var removed=Arr("removed"); var failed=Arr("failed");
        return new { removed, failed, message=$"Gaming Debloat {mode}: удалено {removed.Length}, не удалось {failed.Length}. Системные/пользовательские Win32-программы не затрагивались." };
    }

'''
h=h.replace(anchor,method+anchor,1)
write(hp,h)

# -----------------------------------------------------------------------------
# 5) DI and profile engine integration.
# -----------------------------------------------------------------------------
ap=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
a=read(ap)
if 'using MerzoOptimizer.Windows.Gaming;' not in a:
    a=a.replace('using MerzoOptimizer.Windows.OneDrive;','using MerzoOptimizer.Windows.OneDrive;\nusing MerzoOptimizer.Windows.Gaming;',1)
a=once(a,
'''            var oneDriveService = new WindowsOneDriveOptimizationService(_elevationBroker);\n            var startupOptimizerService = new WindowsStartupOptimizerService(tweakService, snapshotService, restoreService);''',
'''            var oneDriveService = new WindowsOneDriveOptimizationService(_elevationBroker);\n            var gamingDebloatService = new WindowsGamingDebloatService(_elevationBroker);\n            var startupOptimizerService = new WindowsStartupOptimizerService(tweakService, snapshotService, restoreService);''','app service')
a=once(a,
'''                oneDriveService,\n                startupOptimizerService,''',
'''                oneDriveService,\n                gamingDebloatService,\n                startupOptimizerService,''','app vm argument')
write(ap,a)

vp=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=read(vp)
if 'using MerzoOptimizer.Windows.Gaming;' not in v:
    v=v.replace('using MerzoOptimizer.Windows.OneDrive;','using MerzoOptimizer.Windows.OneDrive;\nusing MerzoOptimizer.Windows.Gaming;',1)
v=once(v,
'''    private readonly IOneDriveOptimizationService _oneDriveService;\n    private readonly IStartupOptimizerService _startupOptimizer;''',
'''    private readonly IOneDriveOptimizationService _oneDriveService;\n    private readonly IGamingDebloatService _gamingDebloatService;\n    private readonly IStartupOptimizerService _startupOptimizer;''','vm field')
v=once(v,
'''        IOneDriveOptimizationService oneDriveService,\n        IStartupOptimizerService startupOptimizer,''',
'''        IOneDriveOptimizationService oneDriveService,\n        IGamingDebloatService gamingDebloatService,\n        IStartupOptimizerService startupOptimizer,''','vm ctor arg')
v=once(v,
'''        _oneDriveService = oneDriveService;\n        _startupOptimizer = startupOptimizer;''',
'''        _oneDriveService = oneDriveService;\n        _gamingDebloatService = gamingDebloatService;\n        _startupOptimizer = startupOptimizer;''','vm ctor assignment')

# Insert read-only debloat audit before OneDrive preflight.
pre='''        var oneDriveUninstallRequested = false;\n        OneDriveStatus? oneDriveStatus = null;'''
ins=r'''        GamingDebloatStatus? gamingDebloatStatus = null;
        var gamingDebloatRequested = false;
        var gamingDebloatRemoved = 0;
        var gamingDebloatFailed = 0;
        var packageMode = merzoExtreme ? "EXTREME" : merzoGame ? "GAME" : merzoLight ? "LIGHT" : string.Empty;
        if (!string.IsNullOrWhiteSpace(packageMode))
        {
            try
            {
                gamingDebloatStatus = await _dispatcher.RunAsync("Gaming Debloat audit", token => _gamingDebloatService.InspectAsync(packageMode, token), _lifetimeCts.Token);
                gamingDebloatRequested = gamingDebloatStatus.RemovableCount > 0;
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                Stage2StatusText = $"Gaming Debloat audit недоступен: {ex.Message}. Остальные оптимизации продолжат работать.";
            }
        }

        var processObjectsBefore = System.Diagnostics.Process.GetProcesses();
        var processCountBefore = processObjectsBefore.Length;
        foreach (var p in processObjectsBefore) p.Dispose();

        var oneDriveUninstallRequested = false;
        OneDriveStatus? oneDriveStatus = null;'''
v=once(v,pre,ins,'debloat preflight')

# Expand service source reduction. Keep Xbox services only if Xbox/Game Pass was not detected.
old='''            if (gamingPerformance || gamingExtreme || gamingLab)\n            {\n                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service" }) serviceNames.Add(name);\n            }'''
new='''            if (gamingPerformance || gamingExtreme || gamingLab)\n            {\n                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service", "RetailDemo" }) serviceNames.Add(name);\n                if (gamingDebloatStatus is { XboxGamingInstalled: false })\n                    foreach (var name in new[] { "XblAuthManager", "XblGameSave", "XboxNetApiSvc", "XboxGipSvc" }) serviceNames.Add(name);\n                if (gamingDebloatStatus?.RemovablePackages.Contains("Microsoft.YourPhone", StringComparer.OrdinalIgnoreCase) == true) serviceNames.Add("PhoneSvc");\n            }'''
v=once(v,old,new,'game service expansion')

# Step accounting.
v=once(v,
'''        var networkSteps = gamingNetworkMode is null ? 0 : 1;\n        var oneDriveSteps = oneDriveUninstallRequested ? 1 : 0;''',
'''        var networkSteps = gamingNetworkMode is null ? 0 : 1;\n        var gamingDebloatSteps = gamingDebloatRequested ? 1 : 0;\n        var oneDriveSteps = oneDriveUninstallRequested ? 1 : 0;''','step count vars')
v=v.replace('selected.Count == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0 && oneDriveSteps == 0','selected.Count == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0 && gamingDebloatSteps == 0 && oneDriveSteps == 0')
v=v.replace('selected.Count + services.Count + tasks.Count + networkSteps + oneDriveSteps','selected.Count + services.Count + tasks.Count + networkSteps + gamingDebloatSteps + oneDriveSteps')

# Plan text exposes real debloat and process target as a goal, never a guarantee.
v=v.replace('''"merzo_game" => $"GAME — всё из ЛАЙТ + performance/game tweaks, Power Throttling off, снижение фоновой нагрузки и Gaming Network SAFE. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_game" => $"GAME 2.0 — ЛАЙТ + реальный Gaming Debloat ({gamingDebloatStatus?.RemovableCount ?? 0} Appx), Process Reduction, performance/game tweaks и Gaming Network SAFE. Цель на чистой Windows после reboot — примерно 90–120 процессов, фактический результат зависит от драйверов и используемых функций. Services {services.Count}, tasks {tasks.Count}.",''')
v=v.replace('''"merzo_light" => $"ЛАЙТ — Чистая Windows: максимально ограничивает доступную телеметрию, чистит Пуск/рекомендации, снижает фон, настраивает Explorer и OneDrive. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_light" => $"ЛАЙТ — Чистая Windows: privacy/telemetry, чистый Пуск, consumer debloat ({gamingDebloatStatus?.RemovableCount ?? 0} Appx), Explorer и OneDrive. Services {services.Count}, tasks {tasks.Count}.",''')
v=v.replace('''"merzo_extreme" => $"EXTREME — всё из GAME + агрессивная разгрузка, Game DVR off, дополнительные условные службы/задачи и Gaming Network EXTREME. Перед запуском обязателен Recovery Package. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_extreme" => $"EXTREME — GAME 2.0 + расширенный consumer debloat ({gamingDebloatStatus?.RemovableCount ?? 0} Appx), агрессивная разгрузка, Game DVR off и Gaming Network EXTREME. Recovery Package обязателен. Services {services.Count}, tasks {tasks.Count}.",''')

# Confirmation line.
needle='''Gaming Network: {gamingNetworkMode ?? "нет"}\\nOneDrive: {(oneDriveStatus?.Installed == true ? (oneDriveUninstallRequested ? "удаление приложения после Recovery Package" : "политики/автозапуск") : "не установлен")}'''
repl='''Gaming Network: {gamingNetworkMode ?? "нет"}\\nGaming Debloat: {(gamingDebloatRequested ? $"{gamingDebloatStatus?.RemovableCount ?? 0} consumer Appx" : "уже чисто / не требуется")}\\nПроцессы сейчас: {processCountBefore} · GAME-цель после reboot: ~90–120 (не гарантия)\\nOneDrive: {(oneDriveStatus?.Installed == true ? (oneDriveUninstallRequested ? "удаление приложения после Recovery Package" : "политики/автозапуск") : "не установлен")}'''
if needle not in v: raise SystemExit('R52 confirmation Gaming Network anchor missing')
v=v.replace(needle,repl,1)

# Recovery package must exist before any Appx removal. LIGHT/GAME skip destructive
# debloat if restore point cannot be prepared; EXTREME remains fail-closed.
v=v.replace('''        if (merzoExtreme || oneDriveUninstallRequested)\n        {''','''        if (merzoExtreme || oneDriveUninstallRequested || gamingDebloatRequested)\n        {''',1)
v=v.replace('''            if (oneDriveUninstallRequested) recoveryPlan.Add("app:OneDrive/uninstall");''','''            if (gamingDebloatRequested) recoveryPlan.Add($"appx:{packageMode}/consumer-debloat/{gamingDebloatStatus?.RemovableCount ?? 0}");\n            if (oneDriveUninstallRequested) recoveryPlan.Add("app:OneDrive/uninstall");''',1)
v=v.replace('''                token => _recoveryPackageService.CreateAsync(merzoExtreme ? "EXTREME" : "ONEDRIVE", recoveryPlan, token),''','''                token => _recoveryPackageService.CreateAsync(merzoExtreme ? "EXTREME" : merzoGame ? "GAME" : merzoLight ? "LIGHT" : "ONEDRIVE", recoveryPlan, token),''',1)
# In non-EXTREME failure path disable both destructive operations and recalc total.
v=v.replace('''                oneDriveUninstallRequested = false;\n                oneDriveSteps = 0;\n                total = selected.Count + services.Count + tasks.Count + networkSteps;''','''                oneDriveUninstallRequested = false;\n                gamingDebloatRequested = false;\n                oneDriveSteps = 0;\n                gamingDebloatSteps = 0;\n                total = selected.Count + services.Count + tasks.Count + networkSteps;''',1)
v=v.replace('''Полное удаление OneDrive отменено. Остальная ЛАЙТ/GAME оптимизация продолжится только с обратимыми OneDrive policy/startup изменениями.''','''Recovery Package недоступен: удаление Appx/OneDrive отменено. Остальная ЛАЙТ/GAME оптимизация продолжится только обратимыми изменениями.''',1)

# Operation summary.
v=v.replace(''' · OneDrive {(oneDriveUninstallRequested ? "remove" : "policy/keep")}");''',''' · Debloat {(gamingDebloatRequested ? gamingDebloatStatus?.RemovableCount ?? 0 : 0)} Appx · OneDrive {(oneDriveUninstallRequested ? "remove" : "policy/keep")}");''',1)

# Insert destructive Appx step immediately before guarded OneDrive uninstall.
onedrive_anchor='''            if (oneDriveUninstallRequested)\n            {'''
if v.count(onedrive_anchor)!=1: raise SystemExit(f'R52 OneDrive execution anchor count={v.count(onedrive_anchor)}')
debloat_step=r'''            if (gamingDebloatRequested)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: Gaming Debloat {packageMode} — удаление consumer Appx…";
                DeepScanStatusText = $"Gaming Debloat {done + 1}/{total}: {gamingDebloatStatus?.RemovableCount ?? 0} Appx";
                DeepScanSteps.Add($"→ {done + 1}/{total} · Gaming Debloat {packageMode} · consumer Appx only");
                var result = await _dispatcher.RunAsync("Gaming Debloat "+packageMode, token => _gamingDebloatService.ApplyAsync(packageMode, token), _lifetimeCts.Token);
                gamingDebloatRemoved = result.RemovedCount;
                gamingDebloatFailed = result.FailedCount;
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = $"✓ {done}/{total} · Gaming Debloat · удалено {result.RemovedCount} · пропущено/ошибки {result.FailedCount}";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

'''
v=v.replace(onedrive_anchor,debloat_step+onedrive_anchor,1)

# Final real Before/After measurement. Immediate count is informational; final
# target is evaluated after reboot when startup/service changes have settled.
final_anchor='''            Stage2StatusText = gamingBuild\n                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}."'''
if final_anchor not in v: raise SystemExit('R52 final status anchor missing')
final_new=r'''            var processObjectsAfter = System.Diagnostics.Process.GetProcesses();
            var processCountAfter = processObjectsAfter.Length;
            foreach (var p in processObjectsAfter) p.Dispose();

            Stage2StatusText = gamingBuild
                ? $"Gaming Build применён: {done} шагов · Appx удалено {gamingDebloatRemoved} · процессы {processCountBefore} → {processCountAfter} сейчас · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}. После перезагрузки выполните повторный аудит для финального результата."'''
v=v.replace(final_anchor,final_new,1)
# Remove duplicated original ternary line created by replacement continuation.
v=v.replace('''\n                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";\n            DeepScanStatusText''','''\n                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";\n            DeepScanStatusText''',1)
v=v.replace('''DeepScanSteps.Add($"✓ Профиль завершён · Registry/Policy {selected.Count} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"} · Snapshot {appliedSnapshotIds.Count}");''','''DeepScanSteps.Add($"✓ Профиль завершён · Registry/Policy {selected.Count} · services {services.Count} · tasks {tasks.Count} · Appx removed {gamingDebloatRemoved} · Appx failed {gamingDebloatFailed} · процессы {processCountBefore} → {processCountAfter} сейчас · network {gamingNetworkMode ?? "—"} · Snapshot {appliedSnapshotIds.Count}");''',1)
v=v.replace('''Для отключённых служб рекомендуется перезагрузка Windows.''','''Для GAME/EXTREME перезагрузка обязательна: только после неё повторный аудит покажет реальный Process Reduction и окончательно обновлённый Пуск.''',1)
write(vp,v)

# -----------------------------------------------------------------------------
# 6) Builds UI: make the promise precise and measurable, not fake FPS claims.
# -----------------------------------------------------------------------------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=x.replace('R52 WINDOW + SCROLL RELIABILITY','R52 GAME WOW + UI RELIABILITY')
x=x.replace('✓ Performance + Power Throttling off','✓ Gaming Debloat + Process Reduction 2.0',1)
x=x.replace('✓ Жёсткие фоновые службы / задачи','✓ Цель после reboot: ~90–120 процессов*',1)
x=x.replace('✓ Privacy / telemetry — максимально доступно','✓ Privacy / telemetry + Clean Start',1)
# Footer hint once, if a suitable string exists.
x=x.replace('Быстрая автопроверка завершена. Для персональной рекомендации нажмите большую кнопку проверки.',
'''Быстрая автопроверка завершена. *90–120 — ориентир для чистой Windows, не гарантия: драйверы и используемые функции влияют на итог. После reboot повторите аудит.''',1)
write(xp,x)

# Release notes override R52 window-only entry.
rp=root/'data'/'release_notes.json'
data=json.loads(read(rp))
changes=[
 'GAME 2.0 получил реальный Gaming Debloat: удаляются только allow-listed Microsoft consumer Appx текущего пользователя; системные приложения и Win32-программы не затрагиваются.',
 'ЛАЙТ очищает очевидный consumer-bloat; GAME дополнительно убирает Outlook(new), consumer Teams, Phone Link, People/Maps/Cortana при наличии; EXTREME расширяет список.',
 'GAME включает reviewed process_aggressive registry rules и дополнительные условные фоновые службы; Xbox-службы сохраняются, если обнаружен Xbox/Game Pass.',
 'Перед Appx removal обязателен Recovery Package/System Restore; без него destructive-этап LIGHT/GAME пропускается, EXTREME блокируется.',
 'После применения показывается реальное Before/After процессов; ориентир GAME ~90–120 после reboot на чистой Windows не является гарантией.',
 'Исправлены максимизация по рабочей области монитора и прокрутка раскрытых Expander/вложенных областей.',
 'Сохранены R46 security, R48 OTA, R49 Recovery/OneDrive, R50 UI reliability и R51 Widgets/readability.'
]
if isinstance(data,dict):
    data['version']='0.1.52';data['title']='R52 GAME WOW + UI RELIABILITY';data['changes']=changes
elif isinstance(data,list):
    data=[e for e in data if not(isinstance(e,dict) and e.get('version')=='0.1.52')]
    data.insert(0,{'version':'0.1.52','title':'R52 GAME WOW + UI RELIABILITY','changes':changes})
write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')

(root/'R52_GAME_WOW.marker').write_text('R52 GAME WOW\nreal allow-listed Appx debloat + aggressive process-source reduction + measured before/after\n',encoding='utf-8')
print('R52 GAME WOW debloat patch: OK')
