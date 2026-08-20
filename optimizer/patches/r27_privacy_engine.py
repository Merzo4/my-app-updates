from pathlib import Path
import os,re,json

root=Path(os.environ.get('SOURCE_ROOT','/mnt/data/mwo_src'))
VERSION='0.1.27'
RUNTIME='0.1.27.0'

# ---------- version / visible identity ----------
proj=root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj'
p=proj.read_text(encoding='utf-8-sig')
p=re.sub(r'\s*<!-- MERZO_R2[67]_VERSION_BEGIN -->.*?<!-- MERZO_R2[67]_VERSION_END -->\s*','\n',p,flags=re.S)
stamp=f'''\n  <!-- MERZO_R27_VERSION_BEGIN -->
  <PropertyGroup>
    <Version>{VERSION}</Version>
    <VersionPrefix>{VERSION}</VersionPrefix>
    <AssemblyVersion>{RUNTIME}</AssemblyVersion>
    <FileVersion>{RUNTIME}</FileVersion>
    <InformationalVersion>{VERSION}</InformationalVersion>
  </PropertyGroup>
  <!-- MERZO_R27_VERSION_END -->\n'''
if '</Project>' not in p: raise SystemExit('Project end tag missing')
p=p.replace('</Project>',stamp+'</Project>',1)
proj.write_text(p,encoding='utf-8')

xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
x=re.sub(r'(<Window\b[^>]*\bTitle=")[^"]*(")',rf'\1Merzo Windows Optimizer — Production {VERSION} · R27 PRIVACY\2',x,count=1,flags=re.S)
x=re.sub(r'Production\s+R\d+(?:\s*·\s*[A-Z ]+)?','Production R27',x)
x=re.sub(r'Production\s+0\.1\.\d+(?:\s*·\s*[A-Z ]+)?',f'Production {VERSION}',x)
x=re.sub(r'v0\.1\.\d+',f'v{VERSION}',x)
x=x.replace('OTA REPAIR ✓','PRIVACY ENGINE ✓').replace('OTA REPAIR','PRIVACY ENGINE')

# ---------- privacy catalog ----------
tweaks_path=root/'data'/'tweaks.json'
tweaks=json.loads(tweaks_path.read_text(encoding='utf-8-sig'))
byid={t['id']:t for t in tweaks}

def add_tag(tid,*tags):
    t=byid.get(tid)
    if not t: return
    arr=t.setdefault('profile_tags',[])
    for tag in tags:
        if tag not in arr: arr.append(tag)

safe_ids=[
 'privacy.activity_history','privacy.tailored_experiences','privacy.advertising_id',
 'privacy.disable_feedback_notifications','privacy.disable_notification_mirroring',
 'privacy.disable_privacy_experience','privacy.limit_diagnostic_logs','privacy.limit_dump_collection',
 'search.disable_search_highlights','ui.disable_consumer_features','ui.disable_windows_spotlight'
]
strict_ids=safe_ids+[
 'privacy.required_diagnostic_data','privacy.disable_cross_device_clipboard','privacy.disable_message_sync',
 'search.disable_web_results','search.disable_cortana','appprivacy.deny_diagnostic_info',
 'appprivacy.deny_background_apps'
]
max_ids=strict_ids+[
 'privacy.disable_clipboard_history','privacy.disable_input_personalization','privacy.disable_system_location',
 'search.disable_location_use','appprivacy.deny_account_info','appprivacy.deny_calendar',
 'appprivacy.deny_call_history','appprivacy.deny_contacts','appprivacy.deny_email','appprivacy.deny_location',
 'appprivacy.deny_messaging','appprivacy.deny_motion','appprivacy.deny_notifications','appprivacy.deny_phone',
 'appprivacy.deny_tasks','appprivacy.deny_unpaired_devices','appprivacy.deny_voice_activation','appprivacy.deny_voice_above_lock'
]
for tid in safe_ids: add_tag(tid,'privacy_safe','privacy_strict','privacy_maximum')
for tid in strict_ids: add_tag(tid,'privacy_strict','privacy_maximum')
for tid in max_ids: add_tag(tid,'privacy_maximum')

new_tweaks=[
 {
  'id':'privacy.disable_one_settings_downloads','name':'Отключить OneSettings / Services Configuration','category':'Privacy','risk':'Balanced','requires_admin':True,'requires_restart':False,
  'description':'Запрещает Windows загружать динамическую конфигурацию OneSettings для компонентов, включая Connected User Experiences/Telemetry.',
  'expected_effect':'Меньше фоновых обращений компонентов Windows за удалённой конфигурацией; Windows Update, Store и Defender не отключаются.',
  'source_note':'Microsoft DataCollection policy: DisableOneSettingsDownloads.',
  'profile_tags':['privacy_strict','privacy_maximum','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'DisableOneSettingsDownloads','value_type':'DWord','integer_value':1}],
  'min_windows_build':18363
 },
 {
  'id':'privacy.block_device_name_in_diagnostics','name':'Не отправлять имя устройства в диагностике','category':'Privacy','risk':'Safe','requires_admin':True,'requires_restart':False,
  'description':'Явно запрещает включать имя компьютера в диагностические данные Windows.',
  'expected_effect':'Имя устройства не добавляется в Windows diagnostic data.',
  'source_note':'Microsoft System policy: AllowDeviceNameInDiagnosticData.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'AllowDeviceNameInTelemetry','value_type':'DWord','integer_value':0}],
  'min_windows_build':17763
 },
 {
  'id':'privacy.lock_diagnostic_optin','name':'Заблокировать повышение уровня диагностики','category':'Privacy','risk':'Balanced','requires_admin':True,'requires_restart':False,
  'description':'Блокирует пользовательский интерфейс изменения diagnostic data, чтобы Windows/пользователь случайно не повысили уровень сбора.',
  'expected_effect':'Выбранный политикой уровень диагностических данных остаётся зафиксирован.',
  'source_note':'Microsoft System policy: ConfigureTelemetryOptInSettingsUx.',
  'profile_tags':['privacy_strict','privacy_maximum','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'ConfigureTelemetryOptInSettingsUx','value_type':'DWord','integer_value':1}],
  'min_windows_build':17134
 },
 {
  'id':'privacy.disable_diagnostic_change_notifications','name':'Отключить уведомления об изменении диагностики','category':'Privacy','risk':'Safe','requires_admin':True,'requires_restart':False,
  'description':'Отключает уведомления Windows о смене diagnostic data opt-in.',
  'expected_effect':'Меньше системных prompts вокруг диагностических данных.',
  'source_note':'Microsoft System policy: ConfigureTelemetryOptInChangeNotification.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'ConfigureTelemetryOptInChangeNotification','value_type':'DWord','integer_value':1}],
  'min_windows_build':17134
 },
 {
  'id':'privacy.disable_enterprise_auth_proxy_telemetry','name':'Запретить телеметрии использовать authenticated proxy','category':'Privacy','risk':'Balanced','requires_admin':True,'requires_restart':False,
  'description':'Запрещает Connected User Experiences and Telemetry автоматически использовать authenticated proxy для отправки данных.',
  'expected_effect':'Дополнительное ограничение сетевого пути telemetry service без блокировки обычного системного proxy.',
  'source_note':'Microsoft System policy: DisableEnterpriseAuthProxy.',
  'profile_tags':['privacy_strict','privacy_maximum','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'DisableEnterpriseAuthProxy','value_type':'DWord','integer_value':1}],
  'min_windows_build':16299
 },
 {
  'id':'privacy.security_level_diagnostic_data','name':'Минимальный Security diagnostic level (если редакция поддерживает)','category':'Privacy','risk':'Balanced','requires_admin':True,'requires_restart':False,
  'description':'Устанавливает AllowTelemetry=0. На поддерживаемых Enterprise/Education/Server это Security level; на других редакциях Windows применяет минимально разрешённый эквивалент.',
  'expected_effect':'Максимально низкий поддерживаемый редакцией уровень диагностических данных.',
  'source_note':'Microsoft System policy: AllowTelemetry value 0 is edition-dependent.',
  'profile_tags':['privacy_maximum','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection','value_name':'AllowTelemetry','value_type':'DWord','integer_value':0}],
  'min_windows_build':10240
 },
 {
  'id':'privacy.disable_windows_error_reporting','name':'Отключить отправку Windows Error Reporting','category':'Privacy','risk':'Balanced','requires_admin':True,'requires_restart':False,
  'description':'Отключает отправку отчётов Windows Error Reporting в Microsoft.',
  'expected_effect':'Отчёты о сбоях приложений и Windows не отправляются автоматически наружу.',
  'source_note':'Microsoft Windows Error Reporting policy: Disabled.',
  'profile_tags':['privacy_strict','privacy_maximum','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Error Reporting','value_name':'Disabled','value_type':'DWord','integer_value':1}]
 },
 {
  'id':'privacy.wer_no_additional_data','name':'Запретить WER отправлять дополнительные данные','category':'Privacy','risk':'Safe','requires_admin':True,'requires_restart':False,
  'description':'Автоматически отклоняет запросы на дополнительные данные в Windows Error Reporting.',
  'expected_effect':'Даже при локальном создании отчёта дополнительные данные не отправляются автоматически.',
  'source_note':'Microsoft Windows Error Reporting policy: DontSendAdditionalData.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Error Reporting','value_name':'DontSendAdditionalData','value_type':'DWord','integer_value':1}],
  'min_windows_build':19041
 },
 {
  'id':'privacy.disable_spotlight_action_center','name':'Отключить Spotlight в центре уведомлений','category':'Privacy','risk':'Safe','requires_admin':False,'requires_restart':False,
  'description':'Отключает облачные Spotlight-предложения в центре уведомлений.',
  'expected_effect':'Меньше облачного рекомендательного контента и запросов за ним.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'CurrentUser','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent','value_name':'DisableWindowsSpotlightOnActionCenter','value_type':'DWord','integer_value':1}],
  'min_windows_build':15063
 },
 {
  'id':'privacy.disable_spotlight_settings','name':'Отключить Spotlight-рекомендации в Settings','category':'Privacy','risk':'Safe','requires_admin':False,'requires_restart':False,
  'description':'Отключает рекомендации Windows Spotlight в приложении Параметры.',
  'expected_effect':'Меньше облачного рекомендательного контента в Settings.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'CurrentUser','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent','value_name':'DisableWindowsSpotlightOnSettings','value_type':'DWord','integer_value':1}],
  'min_windows_build':17134
 },
 {
  'id':'privacy.disable_welcome_experience','name':'Отключить Windows Welcome Experience','category':'Privacy','risk':'Safe','requires_admin':False,'requires_restart':False,
  'description':'Отключает облачный welcome/onboarding контент после обновлений и входа.',
  'expected_effect':'Меньше предложений и сетевого контента после обновлений Windows.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'CurrentUser','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent','value_name':'DisableWindowsSpotlightWindowsWelcomeExperience','value_type':'DWord','integer_value':1}],
  'min_windows_build':15063
 },
 {
  'id':'privacy.disable_windows_tips','name':'Отключить Windows Tips / soft landing','category':'Privacy','risk':'Safe','requires_admin':True,'requires_restart':False,
  'description':'Отключает системные tips/soft landing, которые используют облачный контент.',
  'expected_effect':'Меньше фонового рекомендательного контента и подсказок.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent','value_name':'DisableSoftLanding','value_type':'DWord','integer_value':1}],
  'min_windows_build':14393
 },
 {
  'id':'privacy.disable_consumer_account_state_content','name':'Отключить cloud consumer account state content','category':'Privacy','risk':'Safe','requires_admin':True,'requires_restart':False,
  'description':'Отключает облачный consumer account state content в интерфейсах Windows.',
  'expected_effect':'Windows использует локальный fallback вместо облачного consumer state content.',
  'profile_tags':['privacy_safe','privacy_strict','privacy_maximum','light','standard','maximum','lite_build'],
  'registry_actions':[{'hive':'LocalMachine','key_path':'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent','value_name':'DisableConsumerAccountStateContent','value_type':'DWord','integer_value':1}],
  'min_windows_build':18363
 }
]
for nt in new_tweaks:
    if nt['id'] not in byid:
        tweaks.append(nt); byid[nt['id']]=nt

tweaks_path.write_text(json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# ---------- telemetry services/tasks catalog ----------
services_path=root/'data'/'service_rules.json'
services=json.loads(services_path.read_text(encoding='utf-8-sig'))
existing={s['service_name'].lower() for s in services}
for s in [
 {'service_name':'DiagTrack','display_name':'Connected User Experiences and Telemetry','risk':'Balanced','recommendation':'Telemetry core service. В STRICT/MAXIMUM может быть отключена с snapshot; изменение типа запуска применяется безопасно и обратимо.','dependency_note':'Не отключает Windows Update, Store или Defender.'},
 {'service_name':'dmwappushservice','display_name':'Device Management Wireless Application Protocol Push','risk':'Balanced','recommendation':'Связанная с telemetry/device-management служба. В STRICT/MAXIMUM может быть отключена, если присутствует.','dependency_note':'На части Windows 11 служба отсутствует.'},
 {'service_name':'WerSvc','display_name':'Windows Error Reporting Service','risk':'Balanced','recommendation':'MAXIMUM privacy: отключает фоновую службу WER. Локальная диагностика сбоев станет менее информативной.','dependency_note':'Только MAXIMUM; Windows Update/Store/Defender не затрагиваются.'}
]:
    if s['service_name'].lower() not in existing: services.append(s)
services_path.write_text(json.dumps(services,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

tasks_path=root/'data'/'task_rules.json'
tasks=json.loads(tasks_path.read_text(encoding='utf-8-sig'))
patterns={t['pattern'].lower() for t in tasks}
for t in [
 {'pattern':'\\Microsoft\\Windows\\Feedback\\Siuf\\','risk':'Balanced','recommendation':'Feedback/Siuf telemetry tasks: STRICT/MAXIMUM privacy candidate.'},
 {'pattern':'\\Microsoft\\Windows\\Windows Error Reporting\\','risk':'Balanced','recommendation':'WER scheduled tasks: MAXIMUM privacy candidate; отключение обратимо через snapshot.'}
]:
    if t['pattern'].lower() not in patterns: tasks.append(t)
tasks_path.write_text(json.dumps(tasks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# ---------- ViewModel privacy engine ----------
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')

field_anchor='    private string _servicesTasksStatusText = "Службы / задачи: готовы к безопасному аудиту";\n'
if '_privacyStatusText' not in s:
    s=s.replace(field_anchor,field_anchor+'    private string _privacyStatusText = "Телеметрия: готова к privacy-аудиту";\n    private string _privacySummaryText = "Документированные privacy-политики + telemetry services/tasks";\n',1)

cmd_anchor='        RefreshServicesTasksCommand = new AsyncRelayCommand(RefreshServicesTasksAsync, () => !IsStage2Busy);\n'
if 'ApplyPrivacySafeCommand =' not in s:
    insert=cmd_anchor+'''        RefreshPrivacyCommand = new AsyncRelayCommand(RefreshPrivacyAsync, () => !IsStage2Busy);
        ApplyPrivacySafeCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_safe", "БЕЗОПАСНЫЙ", includeCoreServices: false, includeWerService: false, includeTasks: false), () => !IsStage2Busy);
        ApplyPrivacyStrictCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_strict", "СТРОГИЙ", includeCoreServices: true, includeWerService: false, includeTasks: true), () => !IsStage2Busy);
        ApplyPrivacyMaximumCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_maximum", "МАКСИМАЛЬНЫЙ", includeCoreServices: true, includeWerService: true, includeTasks: true), () => !IsStage2Busy);
'''
    s=s.replace(cmd_anchor,insert,1)

prop_anchor='    public AsyncRelayCommand RefreshServicesTasksCommand { get; }\n'
if 'public AsyncRelayCommand RefreshPrivacyCommand' not in s:
    s=s.replace(prop_anchor,prop_anchor+'''    public AsyncRelayCommand RefreshPrivacyCommand { get; }
    public AsyncRelayCommand ApplyPrivacySafeCommand { get; }
    public AsyncRelayCommand ApplyPrivacyStrictCommand { get; }
    public AsyncRelayCommand ApplyPrivacyMaximumCommand { get; }
''',1)

status_anchor='    public string ServicesTasksStatusText { get => _servicesTasksStatusText; private set => SetProperty(ref _servicesTasksStatusText, value); }\n'
if 'public string PrivacyStatusText' not in s:
    s=s.replace(status_anchor,status_anchor+'    public string PrivacyStatusText { get => _privacyStatusText; private set => SetProperty(ref _privacyStatusText, value); }\n    public string PrivacySummaryText { get => _privacySummaryText; private set => SetProperty(ref _privacySummaryText, value); }\n',1)

raise_anchor='            RefreshServicesTasksCommand.RaiseCanExecuteChanged();\n'
if 'RefreshPrivacyCommand.RaiseCanExecuteChanged();' not in s:
    s=s.replace(raise_anchor,raise_anchor+'            RefreshPrivacyCommand.RaiseCanExecuteChanged();\n            ApplyPrivacySafeCommand.RaiseCanExecuteChanged();\n            ApplyPrivacyStrictCommand.RaiseCanExecuteChanged();\n            ApplyPrivacyMaximumCommand.RaiseCanExecuteChanged();\n',1)

init_anchor='        await RefreshServicesTasksAsync();\n        await RefreshPowerAsync();\n'
if 'UpdatePrivacySummary();' not in s[s.find('public async Task InitializeAsync'):s.find('private void LoadSafeTweaks')]:
    s=s.replace(init_anchor,'        await RefreshServicesTasksAsync();\n        UpdatePrivacySummary();\n        await RefreshPowerAsync();\n',1)

method_anchor='    private async Task RefreshServicesTasksAsync()\n'
if 'private async Task ApplyPrivacyProfileAsync' not in s:
    privacy_methods=r'''    private async Task RefreshPrivacyAsync()
    {
        if (_disposed || IsStage2Busy) return;
        PrivacyStatusText = "Проверяю privacy policies, telemetry services и scheduled tasks…";
        await RefreshStage2StateAsync();
        await RefreshServicesTasksAsync();
        UpdatePrivacySummary();
    }

    private void UpdatePrivacySummary()
    {
        var registry = SafeTweaks.Where(static x => x.ProfileTags.Contains("privacy_maximum", StringComparer.OrdinalIgnoreCase) && !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var registryApplied = registry.Count(static x => x.IsApplied);
        var telemetryServices = ServiceAuditItems.Where(static x =>
            string.Equals(x.ServiceName, "DiagTrack", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(x.ServiceName, "dmwappushservice", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(x.ServiceName, "WerSvc", StringComparison.OrdinalIgnoreCase)).ToArray();
        var servicesDisabled = telemetryServices.Count(static x => x.Snapshot.IsDisabled);
        var telemetryTasks = ScheduledTaskAuditItems.Where(static x => IsPrivacyTelemetryTask(x.Snapshot)).ToArray();
        var tasksDisabled = telemetryTasks.Count(static x => !x.Snapshot.Enabled);
        PrivacyStatusText = $"Privacy policies: {registryApplied}/{registry.Length} · telemetry services: {servicesDisabled}/{telemetryServices.Length} · tasks: {tasksDisabled}/{telemetryTasks.Length}";
        PrivacySummaryText = "SAFE не ломает функции. STRICT отключает telemetry core + CEIP/feedback tasks. MAXIMUM дополнительно отключает WER, location/input/cloud sync; Camera/Mic, Windows Update, Store, Defender и IPv6 не отключаются автоматически.";
    }

    private async Task ApplyPrivacyProfileAsync(string profileTag, string title, bool includeCoreServices, bool includeWerService, bool includeTasks)
    {
        if (_disposed || IsStage2Busy) return;

        var selected = SafeTweaks.Where(card =>
            !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied &&
            card.ProfileTags.Contains(profileTag, StringComparer.OrdinalIgnoreCase)).ToArray();
        var serviceSnapshot = await _serviceAudit.ScanAsync(_lifetimeCts.Token);
        var serviceNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (includeCoreServices) { serviceNames.Add("DiagTrack"); serviceNames.Add("dmwappushservice"); }
        if (includeWerService) serviceNames.Add("WerSvc");
        var services = serviceSnapshot.Where(x => serviceNames.Contains(x.ServiceName) && x.CanManage && !x.IsDisabled).ToArray();
        IReadOnlyList<ScheduledTaskAuditItem> taskSnapshot = includeTasks ? await _taskAudit.ScanAsync(_lifetimeCts.Token) : Array.Empty<ScheduledTaskAuditItem>();
        var tasks = taskSnapshot.Where(x => x.CanManage && x.Enabled && IsPrivacyTelemetryTask(x)).ToArray();

        if (selected.Length == 0 && services.Length == 0 && tasks.Length == 0)
        {
            PrivacyStatusText = $"{title}: всё доступное уже находится в целевом состоянии.";
            UpdatePrivacySummary();
            return;
        }

        var warning = title == "БЕЗОПАСНЫЙ"
            ? "Этот профиль не отключает системные службы и не трогает location/camera/microphone."
            : title == "СТРОГИЙ"
                ? "STRICT отключит DiagTrack/dmwappushservice (если присутствуют) и telemetry/feedback scheduled tasks."
                : "MAXIMUM дополнительно отключит Windows Error Reporting service и более жёсткие privacy-функции. Камера/микрофон, Update, Store, Defender и IPv6 останутся рабочими.";
        var answer = MessageBox.Show(
            $"Применить профиль приватности {title}?\n\nRegistry/policy: {selected.Length}\nСлужбы: {services.Length}\nScheduled Tasks: {tasks.Length}\n\n{warning}\n\nПеред каждым изменением создаётся snapshot; при ошибке весь пакет этого запуска откатывается.",
            "Merzo Windows Optimizer — Privacy & Telemetry",
            MessageBoxButton.YesNo,
            title == "БЕЗОПАСНЫЙ" ? MessageBoxImage.Question : MessageBoxImage.Warning);
        if (answer != MessageBoxResult.Yes) return;

        IsStage2Busy = true;
        var snapshots = new List<Guid>();
        var total = selected.Length + services.Length + tasks.Length;
        var done = 0;
        try
        {
            PrivacyStatusText = $"{title}: запускаю пакет 0/{total}…";
            foreach (var card in selected)
            {
                var result = await _dispatcher.RunAsync($"Privacy tweak {card.Id}", token => _tweakService.ApplyAsync(card.Definition, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{card.Name}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) snapshots.Add(id);
                done++; PrivacyStatusText = $"{title}: {done}/{total} · {card.Name}";
            }
            foreach (var item in services)
            {
                var result = await _dispatcher.RunAsync($"Privacy service {item.ServiceName}", token => _serviceAudit.DisableAsync(item.ServiceName, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.DisplayName}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) snapshots.Add(id);
                done++; PrivacyStatusText = $"{title}: {done}/{total} · служба {item.DisplayName}";
            }
            foreach (var item in tasks)
            {
                var result = await _dispatcher.RunAsync($"Privacy task {item.FullPath}", token => _taskAudit.DisableAsync(item.Path, item.Name, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.FullPath}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) snapshots.Add(id);
                done++; PrivacyStatusText = $"{title}: {done}/{total} · задача {item.Name}";
            }
            PrivacyStatusText = $"{title}: применено {done}/{total} · snapshot {snapshots.Count}.";
            MessageBox.Show(PrivacyStatusText + "\n\nРекомендуется перезагрузка, чтобы отключённые службы гарантированно не стартовали снова.", "Privacy & Telemetry", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            foreach (var id in snapshots.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Privacy rollback {id:N}", token => _restoreService.RestoreAsync(id, token), CancellationToken.None);
            PrivacyStatusText = $"Privacy-пакет откатан: {ex.Message}";
            MessageBox.Show(PrivacyStatusText, "Privacy & Telemetry — rollback", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            IsStage2Busy = false;
            if (!_lifetimeCts.IsCancellationRequested)
            {
                await RefreshStage2StateAsync();
                await RefreshServicesTasksAsync();
                UpdatePrivacySummary();
            }
        }
    }

    private static bool IsPrivacyTelemetryTask(ScheduledTaskAuditItem item)
    {
        var full = item.FullPath;
        if (full.Contains(@"\Microsoft\Windows\Customer Experience Improvement Program\", StringComparison.OrdinalIgnoreCase)) return true;
        if (full.Contains(@"\Microsoft\Windows\Feedback\Siuf\", StringComparison.OrdinalIgnoreCase)) return true;
        if (full.Contains(@"\Microsoft\Windows\Windows Error Reporting\", StringComparison.OrdinalIgnoreCase)) return true;
        if (full.Contains(@"\Microsoft\Windows\Application Experience\", StringComparison.OrdinalIgnoreCase))
        {
            return item.Name.Equals("Microsoft Compatibility Appraiser", StringComparison.OrdinalIgnoreCase)
                || item.Name.Equals("ProgramDataUpdater", StringComparison.OrdinalIgnoreCase)
                || item.Name.Equals("StartupAppTask", StringComparison.OrdinalIgnoreCase)
                || item.Name.Contains("Appraiser", StringComparison.OrdinalIgnoreCase);
        }
        return false;
    }

'''
    if method_anchor not in s: raise SystemExit('RefreshServicesTasksAsync anchor missing')
    s=s.replace(method_anchor,privacy_methods+method_anchor,1)

vm.write_text(s,encoding='utf-8')

# ---------- XAML Privacy tab ----------
privacy_tab=r'''

                            <TabItem Header="Телеметрия" Style="{StaticResource SubTabItem}">
                                <Grid Margin="0,4,0,0">
                                    <Grid.RowDefinitions><RowDefinition Height="44"/><RowDefinition Height="88"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                    <Border Grid.Row="0" Background="#102A26" BorderBrush="#2B655A" BorderThickness="1" CornerRadius="8" Padding="9,6" Margin="0,0,0,6">
                                        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                            <StackPanel><TextBlock Text="Privacy &amp; Telemetry Engine" FontSize="11.5" FontWeight="SemiBold" Foreground="{StaticResource Accent}"/><TextBlock Text="{Binding PrivacyStatusText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.4" Margin="0,2,8,0" TextTrimming="CharacterEllipsis"/></StackPanel>
                                            <Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding RefreshPrivacyCommand}" Content="Проверить" VerticalAlignment="Center"/>
                                        </Grid>
                                    </Border>
                                    <Grid Grid.Row="1">
                                        <Grid.ColumnDefinitions><ColumnDefinition Width="1*"/><ColumnDefinition Width="1*"/><ColumnDefinition Width="1*"/></Grid.ColumnDefinitions>
                                        <Border Grid.Column="0" Background="#121D1B" BorderBrush="#285449" BorderThickness="1" CornerRadius="8" Padding="9,7" Margin="0,0,6,0"><StackPanel><TextBlock Text="БЕЗОПАСНЫЙ" Foreground="{StaticResource Accent}" FontSize="10.5" FontWeight="Bold"/><TextBlock Text="Реклама, Activity History, Spotlight, tailored experiences, diagnostic extras. Без отключения служб." Foreground="{StaticResource TextMuted}" FontSize="8" TextWrapping="Wrap" Height="36"/><Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding ApplyPrivacySafeCommand}" Content="Применить SAFE" HorizontalAlignment="Right"/></StackPanel></Border>
                                        <Border Grid.Column="1" Background="#211F15" BorderBrush="#5E4C20" BorderThickness="1" CornerRadius="8" Padding="9,7" Margin="0,0,6,0"><StackPanel><TextBlock Text="СТРОГИЙ" Foreground="{StaticResource Warning}" FontSize="10.5" FontWeight="Bold"/><TextBlock Text="SAFE + Required diagnostics + OneSettings/WER policy + DiagTrack + CEIP/feedback tasks." Foreground="{StaticResource TextMuted}" FontSize="8" TextWrapping="Wrap" Height="36"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyPrivacyStrictCommand}" Content="Применить STRICT" HorizontalAlignment="Right"/></StackPanel></Border>
                                        <Border Grid.Column="2" Background="#21171A" BorderBrush="#633642" BorderThickness="1" CornerRadius="8" Padding="9,7"><StackPanel><TextBlock Text="МАКСИМАЛЬНЫЙ" Foreground="#FF9AAA" FontSize="10.5" FontWeight="Bold"/><TextBlock Text="STRICT + WER service + location/input/cloud sync + расширенный App Privacy. Критическое сохраняем." Foreground="{StaticResource TextMuted}" FontSize="8" TextWrapping="Wrap" Height="36"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyPrivacyMaximumCommand}" Content="Применить MAX" HorizontalAlignment="Right"/></StackPanel></Border>
                                    </Grid>
                                    <Border Grid.Row="2" Background="#111820" BorderBrush="{StaticResource BorderSoft}" BorderThickness="1" CornerRadius="8" Padding="10,8" Margin="0,7,0,0">
                                        <StackPanel><TextBlock Text="Что именно контролируется" FontSize="11" FontWeight="SemiBold"/><TextBlock Text="{Binding PrivacySummaryText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.6" TextWrapping="Wrap" Margin="0,5,0,6"/><TextBlock Text="✓ Diagnostic data / OneSettings / device name  ·  ✓ Advertising ID / Activity History  ·  ✓ Tailored Experiences / Spotlight / Tips  ·  ✓ CEIP / Feedback / Compatibility tasks  ·  ✓ DiagTrack / dmwappushservice  ·  ✓ Windows Error Reporting  ·  ✓ App Privacy / Location / Voice / cloud sync" Foreground="{StaticResource TextMuted}" FontSize="8.2" TextWrapping="Wrap"/><Border Background="#0F2721" BorderBrush="#1F4B40" BorderThickness="1" CornerRadius="6" Padding="7,4" Margin="0,8,0,0"><TextBlock Text="Не используем hosts-блоклисты и не отключаем Windows Update, Microsoft Store, Defender, IPv6, Camera/Mic автоматически." Foreground="{StaticResource Accent}" FontSize="8.3" TextWrapping="Wrap"/></Border></StackPanel>
                                    </Border>
                                </Grid>
                            </TabItem>
'''
opt_tail='''                            </TabItem>\n                        </TabControl>\n                    </Grid>\n                </Grid>\n            </TabItem>\n\n            <!-- Stage 3: Startup Optimizer -->'''
if 'Header="Телеметрия"' not in x:
    idx=x.find(opt_tail)
    if idx<0: raise SystemExit('Optimization TabControl tail not found')
    insert_at=idx+len('                            </TabItem>')
    x=x[:insert_at]+privacy_tab+x[insert_at:]

x=x.replace('Production R21: Check → Download → SHA-256 → Install.','Production R27: Privacy Engine + OTA + SHA-256 + Install.')

xaml.write_text(x,encoding='utf-8')

# ---------- screen capture compatibility ----------
cs=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml.cs'
c=cs.read_text(encoding='utf-8-sig')
if 'using System.Runtime.InteropServices;' not in c:
    c=c.replace('using System.Windows;','using System.Windows;\nusing System.Runtime.InteropServices;\nusing System.Windows.Interop;',1)
if 'SetWindowDisplayAffinity' not in c:
    constructor='''    public MainWindow()\n    {\n        InitializeComponent();\n    }\n'''
    addition=constructor+r'''

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        // R27: explicitly keep the window capturable. Merzo never enables
        // WDA_EXCLUDEFROMCAPTURE/WDA_MONITOR; this also clears stale affinity.
        var hwnd = new WindowInteropHelper(this).Handle;
        if (hwnd != IntPtr.Zero)
            _ = SetWindowDisplayAffinity(hwnd, WdaNone);
    }

    private const uint WdaNone = 0x00000000;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SetWindowDisplayAffinity(IntPtr hWnd, uint dwAffinity);
'''
    if constructor not in c: raise SystemExit('MainWindow constructor anchor missing')
    c=c.replace(constructor,addition,1)
cs.write_text(c,encoding='utf-8')

# ---------- self-test R27 gates ----------
st=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
q=st.read_text(encoding='utf-8-sig')
q=re.sub(r'Merzo Windows Optimizer — .*?SelfTest R\d+','Merzo Windows Optimizer — PRODUCTION R27 PRIVACY SelfTest',q,count=1)
q=q.replace('R20 validation passed: scan-first UX, 100-rule database, cascade profiles + LITE BUILD, protected Defender markers, Unicode power UI, updater foundation and on-demand UAC helper architecture.',
            'R27 validation passed: scan-first UX, privacy/telemetry profiles, Snapshot+Undo, protected security components, Unicode power UI, OTA updater and on-demand UAC helper architecture.')
needle='''    var advancedProbe = new TweakDefinition\n'''
if 'privacy.disable_one_settings_downloads' not in q:
    gate='''    foreach (var id in new[] { "privacy.disable_one_settings_downloads", "privacy.block_device_name_in_diagnostics", "privacy.disable_windows_error_reporting", "privacy.security_level_diagnostic_data" })\n        if (!tweaks.Any(x => string.Equals(x.Id, id, StringComparison.OrdinalIgnoreCase))) failures.Add($"R27 privacy rule missing: {id}");\n    foreach (var tag in new[] { "privacy_safe", "privacy_strict", "privacy_maximum" })\n        if (!tweaks.Any(x => !x.ScanOnly && x.ProfileTags.Contains(tag, StringComparer.OrdinalIgnoreCase))) failures.Add($"R27 privacy profile tag missing: {tag}");\n\n'''
    if needle not in q: raise SystemExit('SelfTest advancedProbe anchor missing')
    q=q.replace(needle,gate+needle,1)
ui_anchor='''    if (xaml.Contains("Text=\"{Binding Id, Mode=OneWay}\"", StringComparison.Ordinal)) failures.Add("Technical tweak IDs must stay hidden from user cards.");\n'''
if 'ApplyPrivacyMaximumCommand' not in q:
    q=q.replace(ui_anchor,ui_anchor+'    foreach (var token in new[] { "Header=\\\"Телеметрия\\\"", "ApplyPrivacySafeCommand", "ApplyPrivacyStrictCommand", "ApplyPrivacyMaximumCommand", "PrivacyStatusText" }) if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R27 privacy UI missing: {token}");\n',1)
st.write_text(q,encoding='utf-8')

# ---------- source-level gates ----------
fx=xaml.read_text(encoding='utf-8')
fv=vm.read_text(encoding='utf-8')
fc=cs.read_text(encoding='utf-8')
ft=json.loads(tweaks_path.read_text(encoding='utf-8'))
ids={t['id'] for t in ft}
for token in ['Production R27','Header="Телеметрия"','ApplyPrivacyMaximumCommand','PrivacyStatusText']:
    if token not in fx and token not in fv: raise SystemExit(f'R27 visible/privacy token missing: {token}')
for tid in ['privacy.disable_one_settings_downloads','privacy.block_device_name_in_diagnostics','privacy.disable_windows_error_reporting','privacy.security_level_diagnostic_data']:
    if tid not in ids: raise SystemExit(f'R27 tweak missing: {tid}')
for tag in ['privacy_safe','privacy_strict','privacy_maximum']:
    if not any(tag in t.get('profile_tags',[]) for t in ft): raise SystemExit(f'R27 tag missing: {tag}')
if 'SetWindowDisplayAffinity' not in fc or 'WdaNone' not in fc: raise SystemExit('R27 screen capture compatibility patch missing')
print(f'R27 privacy patch: OK · tweaks={len(ft)}')
