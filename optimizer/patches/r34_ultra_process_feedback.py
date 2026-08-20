from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(path):
    return path.read_text(encoding='utf-8-sig')

def write(path, text):
    path.write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R34 anchor missing: {label}')
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Catalog: additional reversible policies + process-reduction profile tags.
# Only add a registry action if the same hive/key/value is not already present.
# -----------------------------------------------------------------------------
tweak_path = root / 'data' / 'tweaks.json'
tweaks = json.loads(read(tweak_path))
ids = {x.get('id') for x in tweaks}
existing_actions = set()
for item in tweaks:
    for a in item.get('registry_actions') or []:
        existing_actions.add((str(a.get('hive','')).lower(), str(a.get('key_path','')).lower(), str(a.get('value_name','')).lower()))

def add_tweak(item):
    if item['id'] in ids:
        return False
    acts = item.get('registry_actions') or []
    # Avoid duplicate cards that manipulate exactly the same policy/value.
    if acts and all((str(a.get('hive','')).lower(), str(a.get('key_path','')).lower(), str(a.get('value_name','')).lower()) in existing_actions for a in acts):
        return False
    tweaks.append(item)
    ids.add(item['id'])
    for a in acts:
        existing_actions.add((str(a.get('hive','')).lower(), str(a.get('key_path','')).lower(), str(a.get('value_name','')).lower()))
    return True

def dword(tid, name, category, risk, admin, restart, description, effect, tags, hive, key, value_name, value):
    return {
        'id': tid, 'name': name, 'category': category, 'risk': risk,
        'requires_admin': admin, 'requires_restart': restart, 'scan_only': False,
        'description': description, 'expected_effect': effect,
        'profile_tags': tags,
        'registry_actions': [{
            'hive': hive, 'key_path': key, 'value_name': value_name,
            'value_type': 'DWord', 'integer_value': value
        }]
    }

new_rules = [
    dword('r34.widgets.disable_widgets_policy','Отключить Windows Widgets политикой','Background','Safe',True,True,
          'Запрещает Widgets на уровне устройства. Политика поддерживается Windows 11 Pro/Enterprise/Education; на неподдерживаемой редакции Windows просто не применит её поведение.',
          'Может убрать Widget/WebView фон и сетевую активность, если Widgets не используются.',
          ['r34_new','process_safe','process_aggressive','process_lite','performance','background_light','standard','maximum','lite_build'],
          'LocalMachine',r'SOFTWARE\Policies\Microsoft\Dsh','AllowNewsAndInterests',0),
    dword('r34.consumer.disable_consumer_experiences','Отключить Microsoft consumer experiences','Background','Safe',True,False,
          'Отключает автоматические consumer-предложения и часть пост-OOBE рекомендаций Microsoft через документированную Cloud Content policy.',
          'Меньше фоновых предложений/установок consumer-контента и меньше лишнего сетевого шума.',
          ['r34_new','process_safe','process_aggressive','process_lite','performance','standard','maximum','lite_build'],
          'LocalMachine',r'SOFTWARE\Policies\Microsoft\Windows\CloudContent','DisableWindowsConsumerFeatures',1),
    dword('r34.delivery.limit_background_bandwidth','Ограничить фон Delivery Optimization до 20%','Network','Safe',True,False,
          'Ограничивает суммарную фоновую полосу Delivery Optimization до 20% доступной пропускной способности.',
          'Фоновые обновления меньше конкурируют с играми, браузером и стримом за канал.',
          ['r34_new','process_safe','process_aggressive','process_lite','performance','standard','maximum','lite_build'],
          'LocalMachine',r'SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization','DOPercentageMaxBackgroundBandwidth',20),
    dword('r34.edge.disable_startup_boost','Не запускать Edge через Startup Boost','Edge','Safe',True,False,
          'Официальная Edge policy запрещает запуск процессов Edge при входе в Windows ради Startup Boost.',
          'Уменьшает число фоновых Edge-процессов после входа, если Startup Boost не нужен.',
          ['r34_new','process_safe','process_aggressive','process_lite','performance','background_light','standard','maximum','lite_build'],
          'LocalMachine',r'SOFTWARE\Policies\Microsoft\Edge','StartupBoostEnabled',0),
    dword('r34.edge.disable_background_mode','Не оставлять Edge в фоне после закрытия','Edge','Safe',True,False,
          'Официальная Edge policy запрещает продолжать работу background apps после закрытия последнего окна браузера.',
          'Edge и его фоновые приложения не должны оставаться запущенными только из-за background mode.',
          ['r34_new','process_safe','process_aggressive','process_lite','performance','background_light','standard','maximum','lite_build'],
          'LocalMachine',r'SOFTWARE\Policies\Microsoft\Edge','BackgroundModeEnabled',0),
    dword('r34.explorer.disable_sync_provider_notifications','Отключить рекламу провайдеров синхронизации в Проводнике','Explorer','Safe',False,False,
          'Отключает Show sync provider notifications в Проводнике.',
          'Меньше рекламных/облачных подсказок в Explorer без удаления облачных клиентов.',
          ['r34_new','process_safe','process_aggressive','process_lite','light','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced','ShowSyncProviderNotifications',0),
    dword('r34.start.disable_program_tracking','Не отслеживать часто запускаемые программы для Start','Interface','Safe',False,False,
          'Отключает пользовательский трекинг часто запускаемых программ для рекомендаций меню Пуск.',
          'Снижает лишнюю персонализацию и обновление списка рекомендаций.',
          ['r34_new','process_aggressive','process_lite','light','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced','Start_TrackProgs',0),
    dword('r34.search.disable_dynamic_search_box','Отключить динамические Search highlights','Search','Safe',False,False,
          'Отключает динамический контент/подсветки в поисковой строке для текущего пользователя.',
          'Меньше динамического контента в Search и более спокойный интерфейс.',
          ['r34_new','process_aggressive','process_lite','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\SearchSettings','IsDynamicSearchBoxEnabled',0),
    dword('r34.content.disable_silent_apps','Запретить тихую установку consumer-приложений','Debloat','Safe',False,False,
          'Отключает SilentInstalledAppsEnabled для Content Delivery Manager.',
          'Windows меньше добавляет consumer-приложений в профиль пользователя без явного запроса.',
          ['r34_new','process_safe','process_aggressive','process_lite','light','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager','SilentInstalledAppsEnabled',0),
    dword('r34.content.disable_preinstalled_apps','Не предлагать предустановленные consumer-приложения','Debloat','Safe',False,False,
          'Отключает повторную активацию предложений предустановленных consumer-приложений в пользовательском профиле.',
          'Меньше лишних предложений и фоновой подготовки consumer-приложений.',
          ['r34_new','process_safe','process_aggressive','process_lite','light','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager','PreInstalledAppsEnabled',0),
    dword('r34.content.disable_oem_preinstalled_apps','Отключить OEM consumer-предложения','Debloat','Safe',False,False,
          'Отключает OEM-предложения Content Delivery Manager для текущего пользователя.',
          'Меньше OEM/consumer-рекомендаций после обновлений и входа в систему.',
          ['r34_new','process_aggressive','process_lite','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager','OemPreInstalledAppsEnabled',0),
    dword('r34.content.disable_soft_landing','Отключить Soft Landing подсказки Windows','Notifications','Safe',False,False,
          'Отключает SoftLandingEnabled в Content Delivery Manager.',
          'Меньше фоновых советов и рекламных сценариев после обновлений Windows.',
          ['r34_new','process_aggressive','process_lite','light','standard','maximum','lite_build'],
          'CurrentUser',r'SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager','SoftLandingEnabled',0),
    dword('r34.remote.disable_remote_assistance','Отключить Remote Assistance, если не используется','Background','Balanced',True,True,
          'Запрещает unsolicited/запрашиваемую Remote Assistance через системную политику. Не применять, если вы реально пользуетесь удалённой помощью Windows.',
          'Убирает ненужную поверхность удалённой помощи на ПК, где она не используется.',
          ['r34_new','process_lite','maximum','lite_build'],
          'LocalMachine',r'SYSTEM\CurrentControlSet\Control\Remote Assistance','fAllowToGetHelp',0),
]
added = sum(1 for rule in new_rules if add_tweak(rule))

# Reuse the existing, already-reviewed R32 catalog for three nested Process Reduction profiles.
# The buttons only select entries for review; application still goes through the normal Snapshot/Undo flow.
safe_ids = {
    'performance.disable_startup_delay','edge.disable_new_tab_prerender','browser.chrome.disable_background_mode',
    'r34.widgets.disable_widgets_policy','r34.consumer.disable_consumer_experiences','r34.delivery.limit_background_bandwidth',
    'r34.edge.disable_startup_boost','r34.edge.disable_background_mode','r34.content.disable_silent_apps',
    'r34.content.disable_preinstalled_apps','r34.explorer.disable_sync_provider_notifications'
}
aggressive_ids = safe_ids | {
    'background.force_deny_windows_apps','background.disable_cross_device_experiences','background.disable_setting_sync',
    'performance.disable_power_throttling','r34.start.disable_program_tracking','r34.search.disable_dynamic_search_box',
    'r34.content.disable_oem_preinstalled_apps','r34.content.disable_soft_landing'
}
for item in tweaks:
    if item.get('scan_only'):
        continue
    tags = item.setdefault('profile_tags', [])
    tid = item.get('id','')
    if tid in safe_ids:
        for tag in ('process_safe','process_aggressive','process_lite'):
            if tag not in tags: tags.append(tag)
    elif tid in aggressive_ids:
        for tag in ('process_aggressive','process_lite'):
            if tag not in tags: tags.append(tag)
    elif 'lite_build' in tags and item.get('category') in {'Background','Gaming','Edge','Debloat','Notifications','Search','Performance','Privacy'}:
        if 'process_lite' not in tags: tags.append('process_lite')

write(tweak_path, json.dumps(tweaks, ensure_ascii=False, indent=2) + '\n')

# -----------------------------------------------------------------------------
# Service/Task Advisor expansion: conditional process sources, not blind kills.
# -----------------------------------------------------------------------------
service_path = root / 'data' / 'service_rules.json'
services = json.loads(read(service_path))
existing_services = {str(x.get('service_name','')).lower() for x in services}
service_rules = [
    ('Fax','Fax','SAFE','Можно отключить, если факс не используется.','Условно: не влияет на печать обычных принтеров, но нужен факс-сценариям.'),
    ('icssvc','Windows Mobile Hotspot Service','BALANCED','Можно отключить, если никогда не используете Мобильный хот-спот.','Нужна для раздачи подключения/части hotspot-сценариев.'),
    ('SCardSvr','Smart Card','BALANCED','Можно отключить на домашнем ПК без смарт-карт.','Не отключать в корпоративной среде со smart card / сертификатами.'),
    ('ScDeviceEnum','Smart Card Device Enumeration Service','BALANCED','Можно отключить без смарт-карт и smart-card readers.','Связана с обнаружением устройств смарт-карт.'),
    ('SCPolicySvc','Smart Card Removal Policy','BALANCED','Можно отключить без smart-card logon.','Корпоративные политики smart-card logon могут зависеть от неё.'),
    ('WbioSrvc','Windows Biometric Service','BALANCED','Можно отключить, если нет Windows Hello fingerprint/биометрии.','Не отключать, если входите отпечатком/биометрией.'),
    ('SensorDataService','Sensor Data Service','BALANCED','Можно отключить на стационарном ПК без датчиков.','Не отключать на планшетах/ноутбуках, где нужны датчики.'),
    ('SensorService','Sensor Service','BALANCED','Можно отключить при отсутствии датчиков/автоповорота.','Условная служба устройств с датчиками.'),
    ('SensrSvc','Sensor Monitoring Service','BALANCED','Можно отключить при отсутствии датчиков освещения/ориентации.','Может влиять на автоматическую яркость/ориентацию.'),
    ('MapsBroker','Downloaded Maps Manager','SAFE','Можно отключить, если офлайн-карты Windows не используются.','Не требуется обычному браузерному картографическому сервису.'),
    ('SEMgrSvc','Payments and NFC/SE Manager','BALANCED','Можно отключить на ПК без NFC/платёжных сценариев.','Не отключать на устройствах с соответствующим hardware/scenario.'),
    ('diagnosticshub.standardcollector.service','Microsoft Diagnostics Hub Standard Collector','BALANCED','Можно отключить, если не используете Visual Studio Diagnostics/Performance tools.','Разработчикам может быть нужен для диагностических инструментов.'),
    ('RemoteRegistry','Remote Registry','SAFE','На обычном домашнем ПК рекомендуется держать отключённой, если удалённое администрирование реестра не используется.','Корпоративное администрирование может использовать эту службу.'),
    ('TabletInputService','Touch Keyboard and Handwriting Panel','BALANCED','Можно рассмотреть отключение только на десктопе без touch/pen/экранной клавиатуры.','Может влиять на touch keyboard, handwriting и связанные shell-сценарии.'),
]
for name, display, risk, rec, dep in service_rules:
    if name.lower() not in existing_services:
        services.append({'service_name':name,'display_name':display,'risk':risk,'recommendation':rec,'dependency_note':dep})
        existing_services.add(name.lower())
write(service_path, json.dumps(services, ensure_ascii=False, indent=2) + '\n')

task_path = root / 'data' / 'task_rules.json'
tasks = json.loads(read(task_path))
existing_patterns = {str(x.get('pattern','')).lower() for x in tasks}
task_rules = [
    (r'\\Microsoft\\Windows\\Maps\\','SAFE','Можно отключать задачи Maps, если офлайн-карты Windows не используются.'),
    (r'\\Microsoft\\Windows\\Feedback\\Siuf\\','SAFE','Feedback/Siuf можно отключить в privacy/performance-сценарии, если отправка отзывов не нужна.'),
    (r'\\Microsoft\\Windows\\Location\\','BALANCED','Отключать только если геолокация и location-based функции не используются.'),
    (r'\\Microsoft\\Windows\\FamilySafety\\','BALANCED','Отключать только если Microsoft Family Safety не используется.'),
    (r'\\Microsoft\\Windows\\Mobile Broadband Accounts\\','BALANCED','Можно отключать на ПК без WWAN/eSIM/mobile broadband.'),
    (r'\\Microsoft\\Windows\\RetailDemo\\','SAFE','Retail Demo задачи не нужны обычной домашней/рабочей установке Windows.'),
    (r'\\Microsoft\\Windows\\Shell\\FamilySafety','BALANCED','Family Safety shell-задачи нужны только при использовании семейных ограничений.'),
]
for pattern, risk, rec in task_rules:
    if pattern.lower() not in existing_patterns:
        tasks.append({'pattern':pattern,'risk':risk,'recommendation':rec})
        existing_patterns.add(pattern.lower())
write(task_path, json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')

# -----------------------------------------------------------------------------
# Process model: human source/tier/potential. No direct process termination.
# -----------------------------------------------------------------------------
model_path = root / 'src' / 'MerzoOptimizer.Core' / 'Models' / 'SystemAuditSnapshot.cs'
model = read(model_path)
old = '    public string PerformanceClass => PerformanceAdvisor.Classify(Name, IsSystemSession);\n    public string PerformanceAdvice => PerformanceAdvisor.Advice(Name, IsSystemSession);\n}'
new = '    public string PerformanceClass => PerformanceAdvisor.Classify(Name, IsSystemSession);\n    public string PerformanceAdvice => PerformanceAdvisor.Advice(Name, IsSystemSession);\n    public string SourceHint => PerformanceAdvisor.SourceHint(Name, IsSystemSession);\n    public string ReductionTier => PerformanceAdvisor.ReductionTier(Name, IsSystemSession);\n    public string ReductionPotential => PerformanceAdvisor.ReductionPotential(Name, IsSystemSession);\n}'
model = replace_once(model, old, new, 'process computed properties')
anchor = '    public static string Advice(string name, bool system)\n    {'
methods = '''    public static string SourceHint(string name, bool system)\n    {\n        if (system || Critical.Contains(name)) return "Windows / системная служба";\n        if (name.Contains("onedrive", StringComparison.OrdinalIgnoreCase)) return "OneDrive · синхронизация / автозапуск";\n        if (name.Contains("msedge", StringComparison.OrdinalIgnoreCase)) return "Edge · Startup Boost / Background Mode / WebView";\n        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase)) return "Windows Widgets / WebView";\n        if (name.Contains("phone", StringComparison.OrdinalIgnoreCase)) return "Phone Link / мобильные функции";\n        if (name.Contains("gamebar", StringComparison.OrdinalIgnoreCase) || name.Contains("xbox", StringComparison.OrdinalIgnoreCase)) return "Xbox / Game Bar background";\n        if (name.Contains("steam", StringComparison.OrdinalIgnoreCase) || name.Contains("epic", StringComparison.OrdinalIgnoreCase)) return "Игровой launcher / web helper";\n        if (name.Contains("teams", StringComparison.OrdinalIgnoreCase) || name.Contains("discord", StringComparison.OrdinalIgnoreCase) || name.Contains("spotify", StringComparison.OrdinalIgnoreCase)) return "Автозагрузка пользовательского приложения";\n        if (name.Contains("adobe", StringComparison.OrdinalIgnoreCase) || name.Contains("ccx", StringComparison.OrdinalIgnoreCase) || name.Contains("updater", StringComparison.OrdinalIgnoreCase)) return "Updater / helper / background agent";\n        if (name.Contains("dropbox", StringComparison.OrdinalIgnoreCase) || name.Contains("googledrive", StringComparison.OrdinalIgnoreCase)) return "Облачная синхронизация";\n        if (name.Contains("chrome", StringComparison.OrdinalIgnoreCase) || name.Contains("brave", StringComparison.OrdinalIgnoreCase) || name.Contains("opera", StringComparison.OrdinalIgnoreCase)) return "Браузер · background mode / extensions";\n        return "Пользовательское приложение / источник требует проверки";\n    }\n\n    public static string ReductionTier(string name, bool system)\n    {\n        if (system || Critical.Contains(name)) return "KEEP";\n        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase) || name.Contains("msedge", StringComparison.OrdinalIgnoreCase) || name.Contains("chrome", StringComparison.OrdinalIgnoreCase) || name.Contains("brave", StringComparison.OrdinalIgnoreCase) || name.Contains("opera", StringComparison.OrdinalIgnoreCase)) return "SAFE";\n        if (name.Contains("onedrive", StringComparison.OrdinalIgnoreCase) || name.Contains("phone", StringComparison.OrdinalIgnoreCase) || name.Contains("xbox", StringComparison.OrdinalIgnoreCase) || name.Contains("gamebar", StringComparison.OrdinalIgnoreCase)) return "AGGRESSIVE";\n        if (IsBackgroundCandidate(name)) return "РУЧНОЙ";\n        return "—";\n    }\n\n    public static string ReductionPotential(string name, bool system)\n    {\n        if (system || Critical.Contains(name)) return "Не трогать";\n        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase) || name.Contains("msedge", StringComparison.OrdinalIgnoreCase) || name.Contains("onedrive", StringComparison.OrdinalIgnoreCase)) return "Высокий";\n        if (IsBackgroundCandidate(name)) return "Средний";\n        return "Низкий / неизвестно";\n    }\n\n'''
model = replace_once(model, anchor, methods + anchor, 'performance advisor methods')
write(model_path, model)

# Expand audit process table from TOP-30 to TOP-50. This is display/audit only.
scanner_path = root / 'src' / 'MerzoOptimizer.Windows' / 'SystemInfo' / 'ProcessScanner.cs'
scanner = read(scanner_path).replace('public static ProcessScanResult Scan(int topCount = 30)', 'public static ProcessScanResult Scan(int topCount = 50)', 1)
write(scanner_path, scanner)

# -----------------------------------------------------------------------------
# ViewModel: Process Reduction selectors + Feedback Center + diagnostics ZIP.
# -----------------------------------------------------------------------------
vm_path = root / 'src' / 'MerzoOptimizer.App' / 'ViewModels' / 'MainWindowViewModel.cs'
vm = read(vm_path)
vm = replace_once(vm,
    '    private string _performanceDeltaText = "Сравнение нагрузки появится после повторного аудита.";\n',
    '    private string _performanceDeltaText = "Сравнение нагрузки появится после повторного аудита.";\n'
    '    private string _processReductionStatusText = "После аудита Merzo покажет безопасные источники фоновой нагрузки.";\n'
    '    private string _feedbackText = string.Empty;\n'
    '    private string _feedbackStatusText = "Отчёт отправляется только после вашего действия. GitHub-токен в программу не встроен.";\n',
    'R34 fields')

vm = replace_once(vm,
    '        SelectPerformanceProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("performance"), () => !IsStage2Busy);\n',
    '        SelectPerformanceProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("performance"), () => !IsStage2Busy);\n'
    '        SelectProcessSafeCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_safe", "SAFE"), () => !IsStage2Busy);\n'
    '        SelectProcessAggressiveCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_aggressive", "AGGRESSIVE"), () => !IsStage2Busy);\n'
    '        SelectProcessLiteCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_lite", "LITE-LIKE"), () => !IsStage2Busy);\n'
    '        OpenBugReportCommand = new AsyncRelayCommand(() => OpenFeedbackIssueAsync("Ошибка"));\n'
    '        OpenFeatureRequestCommand = new AsyncRelayCommand(() => OpenFeedbackIssueAsync("Предложение"));\n'
    '        SaveDiagnosticsCommand = new AsyncRelayCommand(SaveDiagnosticsAsync);\n',
    'R34 commands ctor')

vm = replace_once(vm,
    '    public AsyncRelayCommand SelectPerformanceProfileCommand { get; }\n',
    '    public AsyncRelayCommand SelectPerformanceProfileCommand { get; }\n'
    '    public AsyncRelayCommand SelectProcessSafeCommand { get; }\n'
    '    public AsyncRelayCommand SelectProcessAggressiveCommand { get; }\n'
    '    public AsyncRelayCommand SelectProcessLiteCommand { get; }\n'
    '    public AsyncRelayCommand OpenBugReportCommand { get; }\n'
    '    public AsyncRelayCommand OpenFeatureRequestCommand { get; }\n'
    '    public AsyncRelayCommand SaveDiagnosticsCommand { get; }\n',
    'R34 command properties')

# Add bindable properties before LogDirectory, a stable nearby anchor.
props = '''    public string ProcessReductionStatusText\n    {\n        get => _processReductionStatusText;\n        private set => SetProperty(ref _processReductionStatusText, value);\n    }\n\n    public string FeedbackText\n    {\n        get => _feedbackText;\n        set => SetProperty(ref _feedbackText, value ?? string.Empty);\n    }\n\n    public string FeedbackStatusText\n    {\n        get => _feedbackStatusText;\n        private set => SetProperty(ref _feedbackStatusText, value);\n    }\n\n'''
vm = replace_once(vm, '    public string LogDirectory => _logger.LogDirectory;\n', props + '    public string LogDirectory => _logger.LogDirectory;\n', 'R34 bindable properties')

# Update process audit summary and Process Reduction state.
old_summary = '        PerformanceProcessSummaryText = $"Процессов: {snapshot.ProcessCount} · пользовательских: {snapshot.UserProcessCount} · в TOP-{snapshot.TopProcesses.Count} кандидатов на фоновую разгрузку: {backgroundCandidates}.";\n'
new_summary = old_summary + '        ProcessReductionStatusText = $"Найдено {backgroundCandidates} кандидатов среди TOP-{snapshot.TopProcesses.Count}. Выберите SAFE / AGGRESSIVE / LITE-LIKE — Merzo только подготовит обратимый набор для просмотра.";\n'
vm = replace_once(vm, old_summary, new_summary, 'R34 process summary')

helpers = r'''    private async Task SelectProcessReductionProfileAsync(string tag, string title)
    {
        await SelectProfileAsync(tag);
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        ProcessReductionStatusText = $"{title}: подготовлено {selected} обратимых настроек. Ничего ещё не применено — проверьте список во вкладке «Выбранное».";
        SelectedOptimizationTabIndex = 2;
    }

    private Task OpenFeedbackIssueAsync(string kind)
    {
        try
        {
            var description = string.IsNullOrWhiteSpace(FeedbackText) ? "Опишите проблему или предложение здесь." : FeedbackText.Trim();
            var title = $"[Merzo R34][{kind}] {description.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? kind}";
            if (title.Length > 120) title = title[..120];
            var body = $"Тип: {kind}\nВерсия Merzo: 0.1.34 / Production R34\nWindows: {WindowsText}\nCPU: {CpuText}\nRAM: {RamText}\nПроцессы: {ProcessText}\nПоследний аудит: {LastAuditText}\nUpdate status: {UpdateStatusText}\n\nОписание пользователя:\n{description}\n\nПримечание: личные файлы, пароли и токены Merzo к этому отчёту не прикладывает автоматически.";
            var url = "https://github.com/Merzo4/my-app-updates/issues/new?title=" + Uri.EscapeDataString(title) + "&body=" + Uri.EscapeDataString(body);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(url) { UseShellExecute = true });
            FeedbackStatusText = "GitHub Issue подготовлен в браузере. Проверьте текст и нажмите Submit new issue.";
        }
        catch (Exception ex)
        {
            FeedbackStatusText = $"Не удалось открыть GitHub: {ex.Message}. Можно сохранить диагностический ZIP и приложить его вручную.";
        }
        return Task.CompletedTask;
    }

    private Task SaveDiagnosticsAsync()
    {
        try
        {
            var rootPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "Diagnostics");
            Directory.CreateDirectory(rootPath);
            var zipPath = Path.Combine(rootPath, $"MerzoDiagnostics-R34-{DateTime.Now:yyyyMMdd-HHmmss}.zip");
            using var archive = System.IO.Compression.ZipFile.Open(zipPath, System.IO.Compression.ZipArchiveMode.Create);
            var entry = archive.CreateEntry("diagnostics.txt", System.IO.Compression.CompressionLevel.Optimal);
            using (var writer = new StreamWriter(entry.Open(), System.Text.Encoding.UTF8))
            {
                writer.WriteLine("Merzo Windows Optimizer diagnostics — privacy-safe summary");
                writer.WriteLine($"Timestamp: {DateTimeOffset.Now:O}");
                writer.WriteLine("Version: 0.1.34 / Production R34");
                writer.WriteLine($"Windows: {WindowsText}");
                writer.WriteLine($"CPU: {CpuText}");
                writer.WriteLine($"GPU: {GpuText}");
                writer.WriteLine($"RAM: {RamText}");
                writer.WriteLine($"Processes: {ProcessText} ({ProcessDetailText})");
                writer.WriteLine($"Power: {PowerPlanText}");
                writer.WriteLine($"Last audit: {LastAuditText}");
                writer.WriteLine($"Audit freshness: {AuditFreshnessText}");
                writer.WriteLine($"Stage2: {Stage2StatusText}");
                writer.WriteLine($"Deep scan: {DeepScanStatusText}");
                writer.WriteLine($"Updates: {UpdateStatusText}");
                writer.WriteLine();
                writer.WriteLine("User description:");
                writer.WriteLine(string.IsNullOrWhiteSpace(FeedbackText) ? "(not provided)" : FeedbackText.Trim());
                writer.WriteLine();
                writer.WriteLine("This ZIP intentionally excludes browser history, documents, passwords, tokens and user file contents.");
            }
            FeedbackStatusText = $"Диагностика сохранена: {zipPath}";
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("explorer.exe", $"/select,\"{zipPath}\"") { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            FeedbackStatusText = $"Не удалось сохранить диагностику: {ex.Message}";
        }
        return Task.CompletedTask;
    }

'''
vm = replace_once(vm, '    public void DismissStartupUpdateNotice() => IsStartupUpdateNoticeVisible = false;\n', helpers + '    public void DismissStartupUpdateNotice() => IsStartupUpdateNoticeVisible = false;\n', 'R34 helper methods')
write(vm_path, vm)

# -----------------------------------------------------------------------------
# XAML: Process Reduction Engine + Feedback form in Audit.
# -----------------------------------------------------------------------------
xaml_path = root / 'src' / 'MerzoOptimizer.App' / 'MainWindow.xaml'
x = read(xaml_path)
x = x.replace('Production R33', 'Production R34').replace('v0.1.33', 'v0.1.34')
old_process = '''                            <Grid>\n                                <Grid.RowDefinitions><RowDefinition Height="46"/><RowDefinition Height="*"/></Grid.RowDefinitions>\n                                <Border Grid.Row="0" Background="#101B22" BorderBrush="#2A4B54" BorderThickness="1" CornerRadius="8" Padding="9,5" Margin="0,0,0,5">\n                                    <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>\n                                        <StackPanel VerticalAlignment="Center"><TextBlock Text="{Binding PerformanceProcessSummaryText, Mode=OneWay}" FontSize="9.5" FontWeight="SemiBold"/><TextBlock Text="Merzo не убивает процессы вслепую — показывает источник нагрузки и предлагает отключить причину автозапуска/фона." Foreground="{StaticResource TextMuted}" FontSize="7.9" TextTrimming="CharacterEllipsis"/></StackPanel>\n                                        <Button Grid.Column="1" Style="{StaticResource CompactPrimaryButton}" Command="{Binding SelectBackgroundProfileCommand}" Click="OpenOptimization_Click" Content="Подготовить разгрузку" VerticalAlignment="Center"/>\n                                    </Grid>\n                                </Border>\n                                <DataGrid Grid.Row="1" ItemsSource="{Binding TopProcesses}" AutoGenerateColumns="False" IsReadOnly="True">\n                                    <DataGrid.Columns>\n                                        <DataGridTextColumn Header="Процесс" Binding="{Binding Name, Mode=OneWay}" Width="150"/>\n                                        <DataGridTextColumn Header="RAM" Binding="{Binding WorkingSetHuman, Mode=OneWay}" Width="80"/>\n                                        <DataGridTextColumn Header="Тип" Binding="{Binding PerformanceClass, Mode=OneWay}" Width="100"/>\n                                        <DataGridTextColumn Header="Рекомендация" Binding="{Binding PerformanceAdvice, Mode=OneWay}" Width="*"/>\n                                        <DataGridTextColumn Header="PID" Binding="{Binding ProcessId, Mode=OneWay}" Width="58"/>\n                                    </DataGrid.Columns>\n                                </DataGrid>\n                            </Grid>'''
new_process = '''                            <Grid>\n                                <Grid.RowDefinitions><RowDefinition Height="88"/><RowDefinition Height="*"/></Grid.RowDefinitions>\n                                <Border Grid.Row="0" Background="#101B22" BorderBrush="#2A4B54" BorderThickness="1" CornerRadius="8" Padding="9,6" Margin="0,0,0,5">\n                                    <Grid><Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="30"/></Grid.RowDefinitions>\n                                        <StackPanel><TextBlock Text="{Binding PerformanceProcessSummaryText, Mode=OneWay}" FontSize="9.4" FontWeight="SemiBold"/><TextBlock Text="{Binding ProcessReductionStatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="7.9" TextWrapping="Wrap"/></StackPanel>\n                                        <StackPanel Grid.Row="1" Orientation="Horizontal" HorizontalAlignment="Right">\n                                            <Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding SelectProcessSafeCommand}" Click="OpenOptimization_Click" Content="SAFE" MinWidth="70" Margin="0,3,5,0" ToolTip="Фоновые источники с минимальным риском"/>\n                                            <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectProcessAggressiveCommand}" Click="OpenOptimization_Click" Content="AGGRESSIVE" MinWidth="92" Margin="0,3,5,0" ToolTip="Более глубокая разгрузка — проверьте функции перед применением"/>\n                                            <Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectProcessLiteCommand}" Click="OpenOptimization_Click" Content="LITE-LIKE" MinWidth="82" Margin="0,3,0,0" ToolTip="Максимальная обратимая разгрузка без отключения Defender/Windows Update/IPv6/pagefile"/>\n                                        </StackPanel>\n                                    </Grid>\n                                </Border>\n                                <DataGrid Grid.Row="1" ItemsSource="{Binding TopProcesses}" AutoGenerateColumns="False" IsReadOnly="True">\n                                    <DataGrid.Columns>\n                                        <DataGridTextColumn Header="Процесс" Binding="{Binding Name, Mode=OneWay}" Width="115"/>\n                                        <DataGridTextColumn Header="RAM" Binding="{Binding WorkingSetHuman, Mode=OneWay}" Width="64"/>\n                                        <DataGridTextColumn Header="Источник" Binding="{Binding SourceHint, Mode=OneWay}" Width="185"/>\n                                        <DataGridTextColumn Header="Режим" Binding="{Binding ReductionTier, Mode=OneWay}" Width="78"/>\n                                        <DataGridTextColumn Header="Потенциал" Binding="{Binding ReductionPotential, Mode=OneWay}" Width="82"/>\n                                        <DataGridTextColumn Header="Рекомендация" Binding="{Binding PerformanceAdvice, Mode=OneWay}" Width="*"/>\n                                        <DataGridTextColumn Header="PID" Binding="{Binding ProcessId, Mode=OneWay}" Width="52"/>\n                                    </DataGrid.Columns>\n                                </DataGrid>\n                            </Grid>'''
x = replace_once(x, old_process, new_process, 'process reduction XAML')

feedback_tab = '''                        <TabItem Header="Обратная связь" Style="{StaticResource SubTabItem}">\n                            <Grid Margin="2,6,2,2">\n                                <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>\n                                <Border Background="#101B22" BorderBrush="#2A4B54" BorderThickness="1" CornerRadius="8" Padding="10,7" Margin="0,0,0,6">\n                                    <StackPanel><TextBlock Text="Центр обратной связи" FontSize="12" FontWeight="SemiBold"/><TextBlock Text="Опишите ошибку, зависание или идею. Merzo откроет заранее заполненный GitHub Issue — отправка произойдёт только после вашего подтверждения в браузере." Foreground="{StaticResource TextMuted}" FontSize="8.6" TextWrapping="Wrap" Margin="0,3,0,0"/></StackPanel>\n                                </Border>\n                                <TextBox Grid.Row="1" Text="{Binding FeedbackText, UpdateSourceTrigger=PropertyChanged}" AcceptsReturn="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto" Padding="9" Margin="0,0,0,6" ToolTip="Что произошло, что вы ожидали и как повторить проблему"/>\n                                <Border Grid.Row="2" Background="#111A20" BorderBrush="{StaticResource BorderSoft}" BorderThickness="1" CornerRadius="8" Padding="8,6">\n                                    <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>\n                                        <TextBlock Text="{Binding FeedbackStatusText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.2" TextWrapping="Wrap" VerticalAlignment="Center" Margin="0,0,8,0"/>\n                                        <Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding SaveDiagnosticsCommand}" Content="Диагностический ZIP" Margin="0,0,5,0"/>\n                                        <Button Grid.Column="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding OpenFeatureRequestCommand}" Content="Предложить функцию" Margin="0,0,5,0"/>\n                                        <Button Grid.Column="3" Style="{StaticResource CompactPrimaryButton}" Command="{Binding OpenBugReportCommand}" Content="Сообщить об ошибке"/>\n                                    </Grid>\n                                </Border>\n                            </Grid>\n                        </TabItem>\n'''
# Insert into Audit sub-tab control after Storage and before its closing TabControl.
audit_tail = '''                        </TabItem>\n\n                    </TabControl>\n                </Grid>\n            </TabItem>'''
x = replace_once(x, audit_tail, '                        </TabItem>\n\n' + feedback_tab + '                    </TabControl>\n                </Grid>\n            </TabItem>', 'feedback tab')
write(xaml_path, x)

# -----------------------------------------------------------------------------
# Crash Reporter: existing crash logging now gets a one-time next-launch prompt.
# -----------------------------------------------------------------------------
app_path = root / 'src' / 'MerzoOptimizer.App' / 'App.xaml.cs'
app = read(app_path)
app = app.replace('string.IsNullOrWhiteSpace(pendingVersion) ? "0.1.33" : pendingVersion', 'string.IsNullOrWhiteSpace(pendingVersion) ? "0.1.34" : pendingVersion', 1)
app = replace_once(app,
    '            AuditRecommendationsWindow.ShowIfPending(window, _viewModel);\n            WriteStartupDiagnostic("Main window shown successfully after splash initialization. Production shell + on-demand elevated helper initialized.");\n',
    '            AuditRecommendationsWindow.ShowIfPending(window, _viewModel);\n            ShowPendingCrashReport(window);\n            WriteStartupDiagnostic("Main window shown successfully after splash initialization. Production shell + on-demand elevated helper initialized.");\n',
    'crash reporter startup call')
crash_method = r'''    private static void ShowPendingCrashReport(Window owner)
    {
        try
        {
            if (!Directory.Exists(CrashLogDirectory)) return;
            var latest = Directory.GetFiles(CrashLogDirectory, "startup-crash-*.log")
                .OrderByDescending(File.GetLastWriteTimeUtc)
                .FirstOrDefault();
            if (string.IsNullOrWhiteSpace(latest)) return;

            var uiDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "ui");
            Directory.CreateDirectory(uiDir);
            var marker = Path.Combine(uiDir, "last-seen-crash.txt");
            var fingerprint = Path.GetFileName(latest);
            if (File.Exists(marker) && string.Equals(File.ReadAllText(marker).Trim(), fingerprint, StringComparison.OrdinalIgnoreCase)) return;

            var answer = MessageBox.Show(owner,
                "В предыдущем запуске Merzo был сохранён отчёт об ошибке.\n\n" +
                "Хотите открыть подготовленный GitHub Issue? Перед отправкой вы сможете проверить текст. Личные документы, пароли и токены автоматически не отправляются.",
                "Merzo Windows Optimizer — найден отчёт об ошибке",
                MessageBoxButton.YesNo,
                MessageBoxImage.Warning);
            File.WriteAllText(marker, fingerprint);
            if (answer != MessageBoxResult.Yes) return;

            var raw = File.ReadAllText(latest);
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (!string.IsNullOrWhiteSpace(home)) raw = raw.Replace(home, "%USERPROFILE%", StringComparison.OrdinalIgnoreCase);
            if (raw.Length > 6000) raw = raw[..6000] + "\n…truncated…";
            var title = "[Crash][R34] Автоматический отчёт Merzo Windows Optimizer";
            var body = "Версия: 0.1.34 / Production R34\n\nДиагностика предыдущего сбоя:\n```text\n" + raw + "\n```\n\nПожалуйста, добавьте шаги, после которых возникла ошибка.";
            var url = "https://github.com/Merzo4/my-app-updates/issues/new?title=" + Uri.EscapeDataString(title) + "&body=" + Uri.EscapeDataString(body);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch
        {
            // Crash reporting must never make startup fail.
        }
    }

'''
app = replace_once(app, '    private static void WriteStartupDiagnostic(string message)\n', crash_method + '    private static void WriteStartupDiagnostic(string message)\n', 'crash reporter method')
write(app_path, app)

# -----------------------------------------------------------------------------
# R34 branding/version/release notes. Keep R33 no-obfuscation safety strategy.
# -----------------------------------------------------------------------------
for csproj in (root / 'src').glob('*/**/*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>', '<Version>0.1.34</Version>', s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>', '<AssemblyVersion>0.1.34.0</AssemblyVersion>', s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>', '<FileVersion>0.1.34.0</FileVersion>', s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>', '<InformationalVersion>0.1.34</InformationalVersion>', s)
    write(csproj, s)

notes_path = root / 'data' / 'release_notes.json'
notes = {
    'version':'0.1.34',
    'title':'R34 ULTRA PROCESS & FEEDBACK',
    'summary':'Process Reduction Engine, SAFE/AGGRESSIVE/LITE-LIKE, Feedback Center, Crash Reporter и новая волна безопасных Windows-настроек.',
    'added':[
        'Process Reduction Engine: источник фоновой нагрузки, режим снижения и потенциал для TOP-50 процессов.',
        'Три уровня разгрузки SAFE / AGGRESSIVE / LITE-LIKE. Кнопки только готовят список — применение остаётся через Snapshot/Undo.',
        'Feedback Center: ошибка/предложение, prefilled GitHub Issue без встроенного GitHub token, privacy-safe diagnostic ZIP.',
        'Crash Reporter: после сохранённого сбоя при следующем запуске один раз предлагается открыть подготовленный GitHub Issue.',
        'Расширены Services Advisor и Scheduled Tasks Advisor условными правилами для Fax, Smart Card, Sensors, Biometrics, Maps, Mobile Hotspot, NFC, Diagnostics Hub и других необязательных источников.',
        'Добавлены/уточнены политики Widgets, Microsoft consumer experiences, Delivery Optimization background bandwidth, Edge Startup Boost/background mode и дополнительные consumer/UI настройки.'
    ],
    'changed':[
        'Аудит процессов расширен с TOP-30 до TOP-50.',
        'Процессы больше не оцениваются только по имени и RAM: интерфейс показывает вероятный источник, SAFE/AGGRESSIVE/KEEP и ожидаемый потенциал разгрузки.',
        'LITE-LIKE остаётся обратимым и не включает отключение Defender, Windows Update, IPv6, pagefile или timer/HPET-хаки.',
        'R34 продолжает безопасную R33-схему без Obfuscar до отдельного исправления защиты сборок.'
    ],
    'fixed':[
        'Сохраняются runtime stability gates R33 для generic/non-generic async dispatcher.',
        'Уведомление о новой версии при запуске остаётся постоянным до открытия Update Center или ручного закрытия.'
    ]
}
write(notes_path, json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
(root / 'R34_ULTRA_PROCESS_FEEDBACK.marker').write_text('R34 ULTRA PROCESS & FEEDBACK\n', encoding='utf-8')

print(f'R34 patch OK tweaks={len(tweaks)} (+{added}) services={len(services)} tasks={len(tasks)}')
