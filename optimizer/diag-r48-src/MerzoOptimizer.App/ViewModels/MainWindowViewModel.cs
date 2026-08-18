using System.Collections.ObjectModel;
using System.IO;
using System.ComponentModel;
using System.Diagnostics;
using System.Windows;
using System.Windows.Threading;
using MerzoOptimizer.App.Operations;
using MerzoOptimizer.App.Audit;
using MerzoOptimizer.Core.Audit;
using MerzoOptimizer.Core.Diagnostics;
using MerzoOptimizer.Core.Cleanup;
using MerzoOptimizer.Core.Debloat;
using MerzoOptimizer.Core.Dispatching;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Models;
using MerzoOptimizer.Core.Network;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Startup;
using MerzoOptimizer.Core.Services;
using MerzoOptimizer.Core.ScheduledTasks;
using MerzoOptimizer.Core.Power;
using MerzoOptimizer.Core.Updates;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.App.ViewModels;

public sealed class MainWindowViewModel : ObservableObject, IDisposable
{
    private readonly ISystemAuditService _auditService;
    private readonly IAsyncOperationDispatcher _dispatcher;
    private readonly IAuditLogger _logger;
    private readonly ITweakExecutionService _tweakService;
    private readonly ISnapshotService _snapshotService;
    private readonly IRestoreService _restoreService;
    private readonly IRecoveryDiagnosticService _recoveryDiagnosticService;
    private readonly IStartupOptimizerService _startupOptimizer;
    private readonly ICleanupService _cleanupService;
    private readonly IDebloatScanner _debloatScanner;
    private readonly IServiceOptimizationService _serviceAudit;
    private readonly IScheduledTaskOptimizationService _taskAudit;
    private readonly IPowerProfileService _powerProfiles;
    private readonly IUpdateService _updateService;
    private readonly INetworkRepairService _networkRepairService;
    private readonly AuditStateStore _auditStateStore = new();
    private PersistedAuditState? _persistedAudit;
    private AuditRecommendationReport? _pendingAuditRecommendation;
    private readonly CancellationTokenSource _lifetimeCts = new();
    private bool _disposed;
    private bool _initialized;
    private bool _isUpdateBusy;
    private CancellationTokenSource? _deepScanCts;
    private CancellationTokenSource? _deepScanStageCts;
    private CancellationTokenSource? _cleanupScanCts;
    private CancellationTokenSource? _cleanupOperationCts;
    private bool _isCleanupScanning;
    private bool _isCleanupOperationRunning;
    private bool _isCleanupIndeterminate;
    private CancellationTokenSource? _updateOperationCts;
    private readonly DispatcherTimer _powerRefreshTimer = new() { Interval = TimeSpan.FromSeconds(4) };
    private bool _isPowerRefreshing;
    private double _updateProgress;
    private bool _isUpdateProgressVisible;
    private bool _isUpdateProgressIndeterminate;
    private string _updatePhaseText = "Ожидание";
    private string _updateTransferText = "0 Б / 0 Б";
    private string _updateSpeedText = "—";
    private string _powerLiveText = "Live-монитор ещё не запущен";
    private bool _isNetworkBusy;
    private double _networkProgress;
    private string _networkStatusText = "Нажмите «Диагностика», чтобы проверить активное подключение.";
    private string _networkAdapterText = "—";
    private string _networkIpText = "—";
    private string _networkGatewayText = "—";
    private string _networkDnsText = "—";
    private string _networkDhcpText = "—";
    private string _networkSpeedText = "—";
    private string _networkGatewayTestText = "—";
    private string _networkDnsTestText = "—";
    private string _networkOperationText = "Repair Center готов. Никакие сетевые настройки автоматически не меняются.";

    private bool _isBusy;
    private bool _isStage2Busy;
    private bool _hasActiveSnapshots;
    private string _statusText = "Готов к первому аудиту.";
    private string _stage2StatusText = "Snapshot / Restore / Safety готовы к проверке.";
    private string _snapshotSummaryText = "Активных snapshot: 0";
    private string _windowsText = "—";
    private string _cpuText = "—";
    private string _gpuText = "—";
    private string _ramText = "—";
    private string _processText = "—";
    private string _processDetailText = "После аудита будет показан разбор.";
    private string _performanceProcessSummaryText = "Performance Advisor появится после аудита.";
    private string _performanceDeltaText = "Сравнение нагрузки появится после повторного аудита.";
    private string _processReductionStatusText = "После аудита Merzo покажет безопасные источники фоновой нагрузки.";
    private string _feedbackText = string.Empty;
    private string _feedbackStatusText = "Отчёт отправляется только после вашего действия. GitHub-токен в программу не встроен.";
    private bool _isStartupUpdateNoticeVisible;
    private string _startupUpdateNoticeText = "Новая версия Merzo Windows Optimizer готова.";
    private string _startupUpdateNoticeDetailText = "Откройте Update Center, чтобы посмотреть изменения и установить обновление.";
    private string _startupText = "—";
    private string _storageText = "—";
    private string _storageDetailText = "—";
    private string _powerPlanText = "—";
    private string _adminText = "Обычный";
    private string _healthScoreText = "—";
    private string _healthRatingText = "Оценка появится после аудита";
    private string _lastAuditText = "Ещё не запускался";
    private string _auditFreshnessText = "Аудит ещё не сохранён";
    private string _auditCatalogText = "Каталог оптимизаций: —";
    private string _auditButtonText = "Запустить полный аудит";
    private string _recoveryTestStatusText = "Проверка Undo: ещё не запускалась";
    private string _startupOptimizerStatusText = "Автозагрузка: готова к сканированию";
    private string _cleanupStatusText = "Очистка: готова к сканированию";
    private string _cleanupOperationTitle = "Очистка ещё не запускалась";
    private string _cleanupOperationPhase = "Выберите категорию или пакет для очистки";
    private string _cleanupOperationDetail = "Здесь будет показано, что именно делает программа.";
    private string _cleanupOperationResult = "ZIP-backup + Snapshot + проверка результата";
    private double _cleanupProgress;
    private int _selectedCleanupTabIndex;
    private string _debloatStatusText = "Debloat: Appx только аудит; удаление заблокировано до гарантированного Undo";
    private string _selectedTweaksText = "Выбрано: 0";
    private string _servicesTasksStatusText = "Службы / задачи: готовы к безопасному аудиту";
    private string _privacyStatusText = "Телеметрия: готова к privacy-аудиту";
    private string _privacySummaryText = "Документированные privacy-политики + telemetry services/tasks";
    private string _smartAuditOverallText = "Smart Audit 2.0 появится после проверки.";
    private string _smartAuditRecommendationText = "Сначала выполните аудит — Merzo сформирует персональный план.";
    private string _smartAuditPrivacyText = "Privacy: —";
    private string _smartAuditPerformanceText = "Performance: —";
    private string _smartAuditGamingText = "Gaming: —";
    private string _smartAuditStartupText = "Startup: —";
    private string _smartAuditServicesText = "Services / Tasks: —";
    private string _smartAuditCleanupText = "Cleanup: —";
    private string _profilePlanText = "План применения появится после выбора профиля.";
    private string _privacyCoverageText = "SAFE / STRICT / MAXIMUM будут рассчитаны после аудита.";
    private string _startupManagerSummaryText = "Startup Manager 2.0 ещё не сканировал систему.";
    private string _debloatClassificationText = "Debloat 2.0: сначала выполните Appx-аудит.";
    private string _tweakSearchText = string.Empty;
    private string _selectedTweakCategory = "Все";
    private string _cleanupSelectionText = "Выбрано для очистки: 0";
    private string _powerStatusText = "Питание: готово";
    private string _updateStatusText = "Обновления: ещё не проверялись";
    private string _updateLatestText = "—";
    private string _updatePolicyText = "—";
    private string _updateRepositoryText = "—";
    private string _updateReleaseTitleText = "Что нового в текущей версии";
    private string _updateReleaseNotesText = "Список изменений появится после проверки обновлений.";
    private string _deepScanStatusText = "Большая проверка ещё не запускалась";
    private string _deepScanSummaryText = "База готова к анализу системы";
    private string _profileRecommendationText = "Сначала запустите проверку — после неё Merzo сам выделит рекомендуемый уровень.";
    private string _recommendedProfileTitle = "STANDARD";
    private string _recommendedProfileReason = "Рекомендация появится после полной проверки системы.";
    private string _lightProfileAvailableText = "После проверки";
    private string _standardProfileAvailableText = "После проверки";
    private string _maximumProfileAvailableText = "После проверки";
    private string _liteBuildProfileAvailableText = "После проверки";
    private string _activePowerSchemeName = "—";
    private string _powerSchemeCountText = "Схемы питания ещё не проверены";
    private bool _hasOptimizationScanResults;
    private bool _isLightRecommended;
    private bool _isStandardRecommended = true;
    private bool _isMaximumRecommended;
    private bool _isBalancedPowerActive;
    private bool _isPerformancePowerActive;
    private double _deepScanProgress;
    private bool _isDeepScanning;
    private int _selectedOptimizationTabIndex;
    private string? _selectedProfileTag;
    private string? _lastNotifiedUpdateVersion;
    private UpdateCheckResult? _lastUpdateCheck;
    private UpdateDownloadResult? _downloadedUpdate;

    public MainWindowViewModel(
        ISystemAuditService auditService,
        IAsyncOperationDispatcher dispatcher,
        IAuditLogger logger,
        ITweakExecutionService tweakService,
        ISnapshotService snapshotService,
        IRestoreService restoreService,
        IRecoveryDiagnosticService recoveryDiagnosticService,
        IStartupOptimizerService startupOptimizer,
        ICleanupService cleanupService,
        IDebloatScanner debloatScanner,
        IServiceOptimizationService serviceAudit,
        IScheduledTaskOptimizationService taskAudit,
        IPowerProfileService powerProfiles,
        IUpdateService updateService,
        INetworkRepairService networkRepairService)
    {
        _auditService = auditService;
        _dispatcher = dispatcher;
        _logger = logger;
        _tweakService = tweakService;
        _snapshotService = snapshotService;
        _restoreService = restoreService;
        _recoveryDiagnosticService = recoveryDiagnosticService;
        _startupOptimizer = startupOptimizer;
        _cleanupService = cleanupService;
        _debloatScanner = debloatScanner;
        _serviceAudit = serviceAudit;
        _taskAudit = taskAudit;
        _powerProfiles = powerProfiles;
        _updateService = updateService;
        _networkRepairService = networkRepairService;
        UpdatePolicyText = $"Автопроверка: {(_updateService.Settings.AutoCheck ? "Вкл" : "Выкл")} · SHA-256: обязательно · скачивание и установка: только по подтверждению";
        UpdateRepositoryText = string.IsNullOrWhiteSpace(_updateService.Settings.RepositoryOwner) || string.IsNullOrWhiteSpace(_updateService.Settings.RepositoryName)
            ? "Release feed не настроен"
            : $"{_updateService.Settings.RepositoryOwner}/{_updateService.Settings.RepositoryName} · {_updateService.Settings.ReleaseTagPrefix}*";

        RunAuditCommand = new AsyncRelayCommand(RunAuditAsync, () => !IsBusy);
        RefreshStage2Command = new AsyncRelayCommand(RefreshStage2StateAsync, () => !IsStage2Busy);
        RestoreAllCommand = new AsyncRelayCommand(RestoreAllAsync, () => !IsStage2Busy && HasActiveSnapshots);
        RunRecoveryTestCommand = new AsyncRelayCommand(RunRecoveryTestAsync, () => !IsStage2Busy);
        RefreshStartupOptimizerCommand = new AsyncRelayCommand(RefreshStartupOptimizerAsync);
        RefreshCleanupCommand = new AsyncRelayCommand(RefreshCleanupAsync, () => !IsCleanupScanning);
        CancelCleanupOperationCommand = new AsyncRelayCommand(CancelCleanupOperationAsync, () => IsCleanupScanning || IsCleanupOperationRunning);
        RefreshDebloatCommand = new AsyncRelayCommand(RefreshDebloatAsync);
        SelectSafeProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("safe_clean"), () => !IsStage2Busy);
        SelectBalancedProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("balanced"), () => !IsStage2Busy);
        SelectMaximumSafeProfileCommand = new AsyncRelayCommand(SelectMaximumSafeAsync, () => !IsStage2Busy);
        SelectPrivacyProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Privacy", "Search" }, safeOnly: true), () => !IsStage2Busy);
        SelectInterfaceProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Debloat", "Notifications" }, safeOnly: true), () => !IsStage2Busy);
        SelectBackgroundProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("background_light"), () => !IsStage2Busy);
        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_build_safe", "GAME BUILD SAFE"), () => !IsStage2Busy);
        SelectGamingPerformanceCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_build_performance", "GAME BUILD PERFORMANCE"), () => !IsStage2Busy);
        SelectGamingExtremeCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_build_extreme", "GAME BUILD EXTREME"), () => !IsStage2Busy);
        SelectGamingLabCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_build_lab", "GAME BUILD LAB"), () => !IsStage2Busy);
        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("DEVELOPER", new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);
        SelectPerformanceProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("performance"), () => !IsStage2Busy);
        SelectProcessSafeCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_safe", "SAFE"), () => !IsStage2Busy);
        SelectProcessAggressiveCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_aggressive", "AGGRESSIVE"), () => !IsStage2Busy);
        SelectProcessLiteCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_lite", "LITE-LIKE"), () => !IsStage2Busy);
        OpenBugReportCommand = new AsyncRelayCommand(() => OpenFeedbackIssueAsync("Ошибка"));
        OpenFeatureRequestCommand = new AsyncRelayCommand(() => OpenFeedbackIssueAsync("Предложение"));
        SaveDiagnosticsCommand = new AsyncRelayCommand(SaveDiagnosticsAsync);
        RunDeepOptimizationScanCommand = new AsyncRelayCommand(RunDeepOptimizationScanAsync, () => !IsDeepScanning);
        CancelDeepOptimizationScanCommand = new AsyncRelayCommand(CancelDeepOptimizationScanAsync, () => IsDeepScanning);
        SelectLightProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("merzo_light"), () => !IsStage2Busy && !IsDeepScanning);
        SelectStandardProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("merzo_game", "ИГРОВАЯ СБОРКА"), () => !IsStage2Busy && !IsDeepScanning);
        SelectMaximumProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("merzo_extreme", "EXTREME СБОРКА"), () => !IsStage2Busy && !IsDeepScanning);
        SelectLiteBuildProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("lite_build"), () => !IsStage2Busy && !IsDeepScanning);
        ClearTweakSelectionCommand = new AsyncRelayCommand(ClearTweakSelectionAsync, () => !IsStage2Busy);
        ApplySelectedTweaksCommand = new AsyncRelayCommand(ApplySelectedTweaksAsync, () => !IsStage2Busy && SafeTweaks.Any(static x => x.IsSelected));
        CleanAllSafeCommand = new AsyncRelayCommand(CleanAllSafeAsync, () => !IsStage2Busy && CleanupCategories.Any(static x => x.Snapshot.CanClean));
        RefreshServicesTasksCommand = new AsyncRelayCommand(RefreshServicesTasksAsync);
        RefreshPrivacyCommand = new AsyncRelayCommand(RefreshPrivacyAsync, () => !IsStage2Busy);
        ApplyPrivacySafeCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_safe", "БЕЗОПАСНЫЙ", includeCoreServices: false, includeWerService: false, includeTasks: false), () => !IsStage2Busy);
        ApplyPrivacyStrictCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_strict", "СТРОГИЙ", includeCoreServices: true, includeWerService: false, includeTasks: true), () => !IsStage2Busy);
        ApplyPrivacyMaximumCommand = new AsyncRelayCommand(() => ApplyPrivacyProfileAsync("privacy_maximum", "МАКСИМАЛЬНЫЙ", includeCoreServices: true, includeWerService: true, includeTasks: true), () => !IsStage2Busy);
        SelectAllCleanupCommand = new AsyncRelayCommand(SelectAllCleanupAsync, () => !IsStage2Busy);
        ClearCleanupSelectionCommand = new AsyncRelayCommand(ClearCleanupSelectionAsync, () => !IsStage2Busy);
        CleanSelectedCommand = new AsyncRelayCommand(CleanSelectedAsync, () => !IsStage2Busy && CleanupCategories.Any(static x => x.IsSelected && x.CanClean));
        ActivateBalancedPowerCommand = new AsyncRelayCommand(() => ActivatePowerAsync("SCHEME_BALANCED", "Сбалансированный"), () => !IsStage2Busy);
        ActivatePerformancePowerCommand = new AsyncRelayCommand(() => ActivatePowerAsync("SCHEME_MIN", "Высокая производительность"), () => !IsStage2Busy);
        RestorePowerCommand = new AsyncRelayCommand(RestorePowerAsync, () => !IsStage2Busy);
        CheckUpdatesCommand = new AsyncRelayCommand(CheckUpdatesAsync, () => !IsUpdateBusy);
        DismissStartupUpdateNoticeCommand = new AsyncRelayCommand(() => { DismissStartupUpdateNotice(); return Task.CompletedTask; });
        DownloadUpdateCommand = new AsyncRelayCommand(DownloadUpdateAsync, () => !IsUpdateBusy && _lastUpdateCheck is { UpdateAvailable: true, Success: true });
        CancelUpdateCommand = new AsyncRelayCommand(CancelUpdateAsync, () => IsUpdateBusy && _updateOperationCts is not null);
        InstallUpdateCommand = new AsyncRelayCommand(InstallUpdateAsync, () => !IsUpdateBusy && _downloadedUpdate is { Success: true });
        DiagnoseNetworkCommand = new AsyncRelayCommand(DiagnoseNetworkAsync, () => !IsNetworkBusy);
        FlushDnsCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Очистка DNS", "DNS-кэш будет очищен. Это не удаляет сетевые профили.", _networkRepairService.FlushDnsAsync, confirm: false), () => !IsNetworkBusy);
        RenewDhcpCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Обновление DHCP", "Сетевое соединение может кратковременно прерваться. Продолжить?", _networkRepairService.RenewDhcpAsync, confirm: true), () => !IsNetworkBusy);
        ResetWinsockCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Сброс Winsock", "Winsock будет возвращён к стандартному состоянию Windows. Может потребоваться перезагрузка. Продолжить?", _networkRepairService.ResetWinsockAsync, confirm: true), () => !IsNetworkBusy);
        ResetTcpIpCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Сброс TCP/IP", "TCP/IP стек будет сброшен встроенной командой Windows. Может потребоваться перезагрузка. Продолжить?", _networkRepairService.ResetTcpIpAsync, confirm: true), () => !IsNetworkBusy);
        RepairNetworkCommand = new AsyncRelayCommand(RepairNetworkAsync, () => !IsNetworkBusy);
        ApplyGamingNetworkSafeCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Gaming Network SAFE", "Merzo включит RSS и вернёт TCP Auto-Tuning в Normal. Это штатные параметры Windows. Продолжить?", _networkRepairService.ApplyGamingNetworkSafeAsync, confirm: true), () => !IsNetworkBusy);
        ApplyGamingNetworkExtremeCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Gaming Network EXTREME", "Экспериментальный low-latency режим: Merzo сохранит baseline активного адаптера, затем попробует отключить RSC, энергосбережение адаптера и Interrupt Moderation, если драйвер это поддерживает. Возможен больший расход CPU/энергии. Продолжить?", _networkRepairService.ApplyGamingNetworkExtremeAsync, confirm: true), () => !IsNetworkBusy);
        RestoreGamingNetworkCommand = new AsyncRelayCommand(() => RunNetworkActionAsync("Вернуть Gaming Network", "Будет восстановлен baseline адаптера, сохранённый перед EXTREME. TCP RSS/Auto-Tuning останутся в нормальном состоянии Windows. Продолжить?", _networkRepairService.RestoreGamingNetworkAsync, confirm: true), () => !IsNetworkBusy);

        _powerRefreshTimer.Tick += PowerRefreshTimerOnTick;

        _dispatcher.StateChanged += DispatcherOnStateChanged;
        LoadSafeTweaks();
    }

    public AsyncRelayCommand RunAuditCommand { get; }
    public AsyncRelayCommand RefreshStage2Command { get; }
    public AsyncRelayCommand RestoreAllCommand { get; }
    public AsyncRelayCommand RunRecoveryTestCommand { get; }
    public AsyncRelayCommand RefreshStartupOptimizerCommand { get; }
    public AsyncRelayCommand RefreshCleanupCommand { get; }
    public AsyncRelayCommand CancelCleanupOperationCommand { get; }
    public AsyncRelayCommand RefreshDebloatCommand { get; }
    public AsyncRelayCommand SelectSafeProfileCommand { get; }
    public AsyncRelayCommand SelectBalancedProfileCommand { get; }
    public AsyncRelayCommand SelectMaximumSafeProfileCommand { get; }
    public AsyncRelayCommand SelectPrivacyProfileCommand { get; }
    public AsyncRelayCommand SelectInterfaceProfileCommand { get; }
    public AsyncRelayCommand SelectBackgroundProfileCommand { get; }
    public AsyncRelayCommand SelectGamingProfileCommand { get; }
    public AsyncRelayCommand SelectGamingPerformanceCommand { get; }
    public AsyncRelayCommand SelectGamingExtremeCommand { get; }
    public AsyncRelayCommand SelectGamingLabCommand { get; }
    public AsyncRelayCommand SelectDeveloperProfileCommand { get; }
    public AsyncRelayCommand SelectPerformanceProfileCommand { get; }
    public AsyncRelayCommand SelectProcessSafeCommand { get; }
    public AsyncRelayCommand SelectProcessAggressiveCommand { get; }
    public AsyncRelayCommand SelectProcessLiteCommand { get; }
    public AsyncRelayCommand OpenBugReportCommand { get; }
    public AsyncRelayCommand OpenFeatureRequestCommand { get; }
    public AsyncRelayCommand SaveDiagnosticsCommand { get; }
    public AsyncRelayCommand RunDeepOptimizationScanCommand { get; }
    public AsyncRelayCommand CancelDeepOptimizationScanCommand { get; }
    public AsyncRelayCommand SelectLightProfileCommand { get; }
    public AsyncRelayCommand SelectStandardProfileCommand { get; }
    public AsyncRelayCommand SelectMaximumProfileCommand { get; }
    public AsyncRelayCommand SelectLiteBuildProfileCommand { get; }
    public AsyncRelayCommand ClearTweakSelectionCommand { get; }
    public AsyncRelayCommand ApplySelectedTweaksCommand { get; }
    public AsyncRelayCommand CleanAllSafeCommand { get; }
    public AsyncRelayCommand RefreshServicesTasksCommand { get; }
    public AsyncRelayCommand RefreshPrivacyCommand { get; }
    public AsyncRelayCommand ApplyPrivacySafeCommand { get; }
    public AsyncRelayCommand ApplyPrivacyStrictCommand { get; }
    public AsyncRelayCommand ApplyPrivacyMaximumCommand { get; }
    public AsyncRelayCommand SelectAllCleanupCommand { get; }
    public AsyncRelayCommand ClearCleanupSelectionCommand { get; }
    public AsyncRelayCommand CleanSelectedCommand { get; }
    public AsyncRelayCommand ActivateBalancedPowerCommand { get; }
    public AsyncRelayCommand ActivatePerformancePowerCommand { get; }
    public AsyncRelayCommand RestorePowerCommand { get; }
    public AsyncRelayCommand CheckUpdatesCommand { get; }
    public AsyncRelayCommand DismissStartupUpdateNoticeCommand { get; }
    public AsyncRelayCommand DownloadUpdateCommand { get; }
    public AsyncRelayCommand CancelUpdateCommand { get; }
    public AsyncRelayCommand InstallUpdateCommand { get; }
    public AsyncRelayCommand DiagnoseNetworkCommand { get; }
    public AsyncRelayCommand FlushDnsCommand { get; }
    public AsyncRelayCommand RenewDhcpCommand { get; }
    public AsyncRelayCommand ResetWinsockCommand { get; }
    public AsyncRelayCommand ResetTcpIpCommand { get; }
    public AsyncRelayCommand RepairNetworkCommand { get; }
    public AsyncRelayCommand ApplyGamingNetworkSafeCommand { get; }
    public AsyncRelayCommand ApplyGamingNetworkExtremeCommand { get; }
    public AsyncRelayCommand RestoreGamingNetworkCommand { get; }

    public ObservableCollection<StartupItemSnapshot> StartupItems { get; } = [];
    public ObservableCollection<StorageSnapshot> StorageItems { get; } = [];
    public ObservableCollection<ProcessSnapshot> TopProcesses { get; } = [];
    public ObservableCollection<string> HealthExplanations { get; } = [];
    public ObservableCollection<TweakCardViewModel> SafeTweaks { get; } = [];
    public ObservableCollection<TweakCardViewModel> IndividualTweaks { get; } = [];
    public ObservableCollection<TweakCardViewModel> SelectedTweaks { get; } = [];
    public ObservableCollection<string> TweakCategories { get; } = ["Все"];
    public ObservableCollection<SnapshotItemViewModel> Snapshots { get; } = [];
    public ObservableCollection<StartupItemViewModel> StartupOptimizerItems { get; } = [];
    public ObservableCollection<CleanupCategoryViewModel> CleanupCategories { get; } = [];
    public ObservableCollection<string> CleanupOperationSteps { get; } = [];
    public ObservableCollection<DebloatAppSnapshot> DebloatApps { get; } = [];
    public ObservableCollection<ServiceItemViewModel> ServiceAuditItems { get; } = [];
    public ObservableCollection<ScheduledTaskItemViewModel> ScheduledTaskAuditItems { get; } = [];
    public ObservableCollection<PowerSchemeInfo> PowerSchemes { get; } = [];
    public ObservableCollection<string> DeepScanSteps { get; } = [];
    public ObservableCollection<string> NetworkOperationSteps { get; } = [];

    public bool IsNetworkBusy
    {
        get => _isNetworkBusy;
        private set
        {
            if (!SetProperty(ref _isNetworkBusy, value)) return;
            DiagnoseNetworkCommand.RaiseCanExecuteChanged(); FlushDnsCommand.RaiseCanExecuteChanged(); RenewDhcpCommand.RaiseCanExecuteChanged();
            ResetWinsockCommand.RaiseCanExecuteChanged(); ResetTcpIpCommand.RaiseCanExecuteChanged(); RepairNetworkCommand.RaiseCanExecuteChanged();
            ApplyGamingNetworkSafeCommand.RaiseCanExecuteChanged(); ApplyGamingNetworkExtremeCommand.RaiseCanExecuteChanged(); RestoreGamingNetworkCommand.RaiseCanExecuteChanged();
        }
    }
    public double NetworkProgress { get => _networkProgress; private set => SetProperty(ref _networkProgress, value); }
    public string NetworkStatusText { get => _networkStatusText; private set => SetProperty(ref _networkStatusText, value); }
    public string NetworkAdapterText { get => _networkAdapterText; private set => SetProperty(ref _networkAdapterText, value); }
    public string NetworkIpText { get => _networkIpText; private set => SetProperty(ref _networkIpText, value); }
    public string NetworkGatewayText { get => _networkGatewayText; private set => SetProperty(ref _networkGatewayText, value); }
    public string NetworkDnsText { get => _networkDnsText; private set => SetProperty(ref _networkDnsText, value); }
    public string NetworkDhcpText { get => _networkDhcpText; private set => SetProperty(ref _networkDhcpText, value); }
    public string NetworkSpeedText { get => _networkSpeedText; private set => SetProperty(ref _networkSpeedText, value); }
    public string NetworkGatewayTestText { get => _networkGatewayTestText; private set => SetProperty(ref _networkGatewayTestText, value); }
    public string NetworkDnsTestText { get => _networkDnsTestText; private set => SetProperty(ref _networkDnsTestText, value); }
    public string NetworkOperationText { get => _networkOperationText; private set => SetProperty(ref _networkOperationText, value); }

    public string ProcessReductionStatusText
    {
        get => _processReductionStatusText;
        private set => SetProperty(ref _processReductionStatusText, value);
    }

    public string FeedbackText
    {
        get => _feedbackText;
        set => SetProperty(ref _feedbackText, value ?? string.Empty);
    }

    public string FeedbackStatusText
    {
        get => _feedbackStatusText;
        private set => SetProperty(ref _feedbackStatusText, value);
    }

    public string LogDirectory => _logger.LogDirectory;
    public string SnapshotDirectory => _snapshotService.SnapshotDirectory;

    public bool IsBusy
    {
        get => _isBusy;
        private set
        {
            if (SetProperty(ref _isBusy, value))
                RunAuditCommand.RaiseCanExecuteChanged();
        }
    }

    public bool IsStage2Busy
    {
        get => _isStage2Busy;
        private set
        {
            if (!SetProperty(ref _isStage2Busy, value))
                return;

            RefreshStage2Command.RaiseCanExecuteChanged();
            RestoreAllCommand.RaiseCanExecuteChanged();
            RunRecoveryTestCommand.RaiseCanExecuteChanged();
            RefreshStartupOptimizerCommand.RaiseCanExecuteChanged();
            RefreshCleanupCommand.RaiseCanExecuteChanged();
            RefreshDebloatCommand.RaiseCanExecuteChanged();
            SelectSafeProfileCommand.RaiseCanExecuteChanged();
            SelectBalancedProfileCommand.RaiseCanExecuteChanged();
            SelectMaximumSafeProfileCommand.RaiseCanExecuteChanged();
            SelectPrivacyProfileCommand.RaiseCanExecuteChanged();
            SelectInterfaceProfileCommand.RaiseCanExecuteChanged();
            SelectBackgroundProfileCommand.RaiseCanExecuteChanged();
            SelectGamingProfileCommand.RaiseCanExecuteChanged();
            SelectGamingPerformanceCommand.RaiseCanExecuteChanged();
            SelectGamingExtremeCommand.RaiseCanExecuteChanged();
            SelectGamingLabCommand.RaiseCanExecuteChanged();
            SelectDeveloperProfileCommand.RaiseCanExecuteChanged();
            SelectPerformanceProfileCommand.RaiseCanExecuteChanged();
            RunDeepOptimizationScanCommand.RaiseCanExecuteChanged();
            CancelDeepOptimizationScanCommand.RaiseCanExecuteChanged();
            SelectLightProfileCommand.RaiseCanExecuteChanged();
            SelectStandardProfileCommand.RaiseCanExecuteChanged();
            SelectMaximumProfileCommand.RaiseCanExecuteChanged();
            SelectLiteBuildProfileCommand.RaiseCanExecuteChanged();
            ClearTweakSelectionCommand.RaiseCanExecuteChanged();
            ApplySelectedTweaksCommand.RaiseCanExecuteChanged();
            CleanAllSafeCommand.RaiseCanExecuteChanged();
            RefreshServicesTasksCommand.RaiseCanExecuteChanged();
            RefreshPrivacyCommand.RaiseCanExecuteChanged();
            ApplyPrivacySafeCommand.RaiseCanExecuteChanged();
            ApplyPrivacyStrictCommand.RaiseCanExecuteChanged();
            ApplyPrivacyMaximumCommand.RaiseCanExecuteChanged();
            SelectAllCleanupCommand.RaiseCanExecuteChanged();
            ClearCleanupSelectionCommand.RaiseCanExecuteChanged();
            CleanSelectedCommand.RaiseCanExecuteChanged();
            ActivateBalancedPowerCommand.RaiseCanExecuteChanged();
            ActivatePerformancePowerCommand.RaiseCanExecuteChanged();
            RestorePowerCommand.RaiseCanExecuteChanged();
            CheckUpdatesCommand.RaiseCanExecuteChanged();
            DownloadUpdateCommand.RaiseCanExecuteChanged();
            CancelUpdateCommand.RaiseCanExecuteChanged();
            InstallUpdateCommand.RaiseCanExecuteChanged();
            InstallUpdateCommand.RaiseCanExecuteChanged();
        }
    }

    public bool HasActiveSnapshots
    {
        get => _hasActiveSnapshots;
        private set
        {
            if (SetProperty(ref _hasActiveSnapshots, value))
                RestoreAllCommand.RaiseCanExecuteChanged();
            RunRecoveryTestCommand.RaiseCanExecuteChanged();
        }
    }

    public string StatusText { get => _statusText; private set => SetProperty(ref _statusText, value); }
    public string Stage2StatusText { get => _stage2StatusText; private set => SetProperty(ref _stage2StatusText, value); }
    public string SnapshotSummaryText { get => _snapshotSummaryText; private set => SetProperty(ref _snapshotSummaryText, value); }
    public string WindowsText { get => _windowsText; private set => SetProperty(ref _windowsText, value); }
    public string CpuText { get => _cpuText; private set => SetProperty(ref _cpuText, value); }
    public string GpuText { get => _gpuText; private set => SetProperty(ref _gpuText, value); }
    public string RamText { get => _ramText; private set => SetProperty(ref _ramText, value); }
    public string ProcessText { get => _processText; private set => SetProperty(ref _processText, value); }
    public string ProcessDetailText { get => _processDetailText; private set => SetProperty(ref _processDetailText, value); }
    public string PerformanceProcessSummaryText { get => _performanceProcessSummaryText; private set => SetProperty(ref _performanceProcessSummaryText, value); }
    public string PerformanceDeltaText { get => _performanceDeltaText; private set => SetProperty(ref _performanceDeltaText, value); }
    public bool IsStartupUpdateNoticeVisible { get => _isStartupUpdateNoticeVisible; private set => SetProperty(ref _isStartupUpdateNoticeVisible, value); }
    public string StartupUpdateNoticeText { get => _startupUpdateNoticeText; private set => SetProperty(ref _startupUpdateNoticeText, value); }
    public string StartupUpdateNoticeDetailText { get => _startupUpdateNoticeDetailText; private set => SetProperty(ref _startupUpdateNoticeDetailText, value); }
    public string StartupText { get => _startupText; private set => SetProperty(ref _startupText, value); }
    public string StorageText { get => _storageText; private set => SetProperty(ref _storageText, value); }
    public string StorageDetailText { get => _storageDetailText; private set => SetProperty(ref _storageDetailText, value); }
    public string PowerPlanText { get => _powerPlanText; private set => SetProperty(ref _powerPlanText, value); }
    public string AdminText { get => _adminText; private set => SetProperty(ref _adminText, value); }
    public string HealthScoreText { get => _healthScoreText; private set => SetProperty(ref _healthScoreText, value); }
    public string HealthRatingText { get => _healthRatingText; private set => SetProperty(ref _healthRatingText, value); }
    public string LastAuditText { get => _lastAuditText; private set => SetProperty(ref _lastAuditText, value); }
    public string AuditFreshnessText { get => _auditFreshnessText; private set => SetProperty(ref _auditFreshnessText, value); }
    public string AuditCatalogText { get => _auditCatalogText; private set => SetProperty(ref _auditCatalogText, value); }
    public string AuditButtonText { get => _auditButtonText; private set => SetProperty(ref _auditButtonText, value); }
    public string RecoveryTestStatusText { get => _recoveryTestStatusText; private set => SetProperty(ref _recoveryTestStatusText, value); }
    public string StartupOptimizerStatusText { get => _startupOptimizerStatusText; private set => SetProperty(ref _startupOptimizerStatusText, value); }
    public string CleanupStatusText { get => _cleanupStatusText; private set => SetProperty(ref _cleanupStatusText, value); }
    public bool IsCleanupScanning
    {
        get => _isCleanupScanning;
        private set { if (!SetProperty(ref _isCleanupScanning, value)) return; RefreshCleanupCommand.RaiseCanExecuteChanged(); CancelCleanupOperationCommand.RaiseCanExecuteChanged(); }
    }
    public bool IsCleanupOperationRunning
    {
        get => _isCleanupOperationRunning;
        private set { if (!SetProperty(ref _isCleanupOperationRunning, value)) return; CancelCleanupOperationCommand.RaiseCanExecuteChanged(); }
    }
    public bool IsCleanupIndeterminate { get => _isCleanupIndeterminate; private set => SetProperty(ref _isCleanupIndeterminate, value); }
    public string CleanupOperationTitle { get => _cleanupOperationTitle; private set => SetProperty(ref _cleanupOperationTitle, value); }
    public string CleanupOperationPhase { get => _cleanupOperationPhase; private set => SetProperty(ref _cleanupOperationPhase, value); }
    public string CleanupOperationDetail { get => _cleanupOperationDetail; private set => SetProperty(ref _cleanupOperationDetail, value); }
    public string CleanupOperationResult { get => _cleanupOperationResult; private set => SetProperty(ref _cleanupOperationResult, value); }
    public double CleanupProgress { get => _cleanupProgress; private set { if (SetProperty(ref _cleanupProgress, Math.Clamp(value, 0, 100))) RaisePropertyChanged(nameof(CleanupProgressText)); } }
    public string CleanupProgressText => $"{CleanupProgress:0}%";
    public int SelectedCleanupTabIndex { get => _selectedCleanupTabIndex; set => SetProperty(ref _selectedCleanupTabIndex, value); }
    public string DebloatStatusText { get => _debloatStatusText; private set => SetProperty(ref _debloatStatusText, value); }
    public string SelectedTweaksText { get => _selectedTweaksText; private set => SetProperty(ref _selectedTweaksText, value); }
    public string ServicesTasksStatusText { get => _servicesTasksStatusText; private set => SetProperty(ref _servicesTasksStatusText, value); }
    public string PrivacyStatusText { get => _privacyStatusText; private set => SetProperty(ref _privacyStatusText, value); }
    public string PrivacySummaryText { get => _privacySummaryText; private set => SetProperty(ref _privacySummaryText, value); }
    public string SmartAuditOverallText { get => _smartAuditOverallText; private set => SetProperty(ref _smartAuditOverallText, value); }
    public string SmartAuditRecommendationText { get => _smartAuditRecommendationText; private set => SetProperty(ref _smartAuditRecommendationText, value); }
    public string SmartAuditPrivacyText { get => _smartAuditPrivacyText; private set => SetProperty(ref _smartAuditPrivacyText, value); }
    public string SmartAuditPerformanceText { get => _smartAuditPerformanceText; private set => SetProperty(ref _smartAuditPerformanceText, value); }
    public string SmartAuditGamingText { get => _smartAuditGamingText; private set => SetProperty(ref _smartAuditGamingText, value); }
    public string SmartAuditStartupText { get => _smartAuditStartupText; private set => SetProperty(ref _smartAuditStartupText, value); }
    public string SmartAuditServicesText { get => _smartAuditServicesText; private set => SetProperty(ref _smartAuditServicesText, value); }
    public string SmartAuditCleanupText { get => _smartAuditCleanupText; private set => SetProperty(ref _smartAuditCleanupText, value); }
    public string ProfilePlanText { get => _profilePlanText; private set => SetProperty(ref _profilePlanText, value); }
    public string PrivacyCoverageText { get => _privacyCoverageText; private set => SetProperty(ref _privacyCoverageText, value); }
    public string StartupManagerSummaryText { get => _startupManagerSummaryText; private set => SetProperty(ref _startupManagerSummaryText, value); }
    public string DebloatClassificationText { get => _debloatClassificationText; private set => SetProperty(ref _debloatClassificationText, value); }
    public string CleanupSelectionText { get => _cleanupSelectionText; private set => SetProperty(ref _cleanupSelectionText, value); }
    public string PowerStatusText { get => _powerStatusText; private set => SetProperty(ref _powerStatusText, value); }
    public string UpdateStatusText { get => _updateStatusText; private set => SetProperty(ref _updateStatusText, value); }
    public string UpdateLatestText { get => _updateLatestText; private set => SetProperty(ref _updateLatestText, value); }
    public string UpdatePolicyText { get => _updatePolicyText; private set => SetProperty(ref _updatePolicyText, value); }
    public string UpdateRepositoryText { get => _updateRepositoryText; private set => SetProperty(ref _updateRepositoryText, value); }
    public string UpdateReleaseTitleText { get => _updateReleaseTitleText; private set => SetProperty(ref _updateReleaseTitleText, value); }
    public string UpdateReleaseNotesText { get => _updateReleaseNotesText; private set => SetProperty(ref _updateReleaseNotesText, value); }
    public double UpdateProgress { get => _updateProgress; private set { if (SetProperty(ref _updateProgress, Math.Clamp(value, 0, 100))) RaisePropertyChanged(nameof(UpdateProgressText)); } }
    public string UpdateProgressText => $"{UpdateProgress:0}%";
    public bool IsUpdateProgressVisible { get => _isUpdateProgressVisible; private set => SetProperty(ref _isUpdateProgressVisible, value); }
    public bool IsUpdateProgressIndeterminate { get => _isUpdateProgressIndeterminate; private set => SetProperty(ref _isUpdateProgressIndeterminate, value); }
    public string UpdatePhaseText { get => _updatePhaseText; private set => SetProperty(ref _updatePhaseText, value); }
    public string UpdateTransferText { get => _updateTransferText; private set => SetProperty(ref _updateTransferText, value); }
    public string UpdateSpeedText { get => _updateSpeedText; private set => SetProperty(ref _updateSpeedText, value); }
    public string PowerLiveText { get => _powerLiveText; private set => SetProperty(ref _powerLiveText, value); }
    public string DeepScanStatusText { get => _deepScanStatusText; private set => SetProperty(ref _deepScanStatusText, value); }
    public string DeepScanSummaryText { get => _deepScanSummaryText; private set => SetProperty(ref _deepScanSummaryText, value); }
    public string ProfileRecommendationText { get => _profileRecommendationText; private set => SetProperty(ref _profileRecommendationText, value); }
    public string RecommendedProfileTitle { get => _recommendedProfileTitle; private set => SetProperty(ref _recommendedProfileTitle, value); }
    public string RecommendedProfileReason { get => _recommendedProfileReason; private set => SetProperty(ref _recommendedProfileReason, value); }
    public string LightProfileAvailableText { get => _lightProfileAvailableText; private set => SetProperty(ref _lightProfileAvailableText, value); }
    public string StandardProfileAvailableText { get => _standardProfileAvailableText; private set => SetProperty(ref _standardProfileAvailableText, value); }
    public string MaximumProfileAvailableText { get => _maximumProfileAvailableText; private set => SetProperty(ref _maximumProfileAvailableText, value); }
    public string LiteBuildProfileAvailableText { get => _liteBuildProfileAvailableText; private set => SetProperty(ref _liteBuildProfileAvailableText, value); }
    public string ActivePowerSchemeName { get => _activePowerSchemeName; private set => SetProperty(ref _activePowerSchemeName, value); }
    public string PowerSchemeCountText { get => _powerSchemeCountText; private set => SetProperty(ref _powerSchemeCountText, value); }
    public bool HasOptimizationScanResults { get => _hasOptimizationScanResults; private set => SetProperty(ref _hasOptimizationScanResults, value); }
    public bool IsLightRecommended { get => _isLightRecommended; private set => SetProperty(ref _isLightRecommended, value); }
    public bool IsStandardRecommended { get => _isStandardRecommended; private set => SetProperty(ref _isStandardRecommended, value); }
    public bool IsMaximumRecommended { get => _isMaximumRecommended; private set => SetProperty(ref _isMaximumRecommended, value); }
    public bool IsBalancedPowerActive { get => _isBalancedPowerActive; private set => SetProperty(ref _isBalancedPowerActive, value); }
    public bool IsPerformancePowerActive { get => _isPerformancePowerActive; private set => SetProperty(ref _isPerformancePowerActive, value); }
    public double DeepScanProgress { get => _deepScanProgress; private set => SetProperty(ref _deepScanProgress, value); }
    public int SelectedOptimizationTabIndex { get => _selectedOptimizationTabIndex; set => SetProperty(ref _selectedOptimizationTabIndex, value); }
    public bool IsDeepScanning
    {
        get => _isDeepScanning;
        private set
        {
            if (!SetProperty(ref _isDeepScanning, value)) return;
            RunDeepOptimizationScanCommand.RaiseCanExecuteChanged();
            SelectLightProfileCommand.RaiseCanExecuteChanged();
            SelectStandardProfileCommand.RaiseCanExecuteChanged();
            SelectMaximumProfileCommand.RaiseCanExecuteChanged();
            SelectLiteBuildProfileCommand.RaiseCanExecuteChanged();
        }
    }

    public bool IsUpdateBusy
    {
        get => _isUpdateBusy;
        private set
        {
            if (!SetProperty(ref _isUpdateBusy, value)) return;
            CheckUpdatesCommand.RaiseCanExecuteChanged();
            DownloadUpdateCommand.RaiseCanExecuteChanged();
        }
    }

    public string TweakSearchText
    {
        get => _tweakSearchText;
        set
        {
            if (SetProperty(ref _tweakSearchText, value))
                RefreshIndividualTweaks();
        }
    }

    public string SelectedTweakCategory
    {
        get => _selectedTweakCategory;
        set
        {
            if (SetProperty(ref _selectedTweakCategory, string.IsNullOrWhiteSpace(value) ? "Все" : value))
                RefreshIndividualTweaks();
        }
    }

    public async Task InitializeAsync()
    {
        if (_initialized || _disposed)
            return;

        _initialized = true;
        _persistedAudit = await _auditStateStore.LoadLatestAsync(_lifetimeCts.Token);
        if (_persistedAudit is not null)
        {
            ApplySnapshot(_persistedAudit.Snapshot);
            AuditButtonText = "Обновить аудит";
            AuditFreshnessText = $"Сохранённый аудит загружен · {_persistedAudit.SavedAt.LocalDateTime:dd.MM.yyyy HH:mm}";
            StatusText = "Последний аудит восстановлен с диска. Проверяю актуальность каталога…";
        }
        await RefreshStage2StateAsync();
        await RefreshStartupOptimizerAsync();
        await RefreshCleanupAsync();
        await RefreshDebloatAsync();
        await RefreshServicesTasksAsync();
        UpdatePrivacySummary();
        await RefreshPowerAsync();
        if (!_powerRefreshTimer.IsEnabled) _powerRefreshTimer.Start();
        UpdateOptimizationScanSummary(autoScan: true);
        await EvaluateAuditFreshnessAfterStartupAsync();
        LoadLocalReleaseNotes();
        if (_updateService.Settings.AutoCheck) _ = CheckUpdatesAsync(silent: true);
    }

    private void LoadSafeTweaks()
    {
        try
        {
            var path = Path.Combine(AppContext.BaseDirectory, "data", "tweaks.json");
            foreach (var tweak in TweakCatalogLoader.Load(path))
            {
                var card = new TweakCardViewModel(tweak, ApplyTweakAsync, RestoreTweakAsync);
                card.PropertyChanged += TweakCardOnPropertyChanged;
                SafeTweaks.Add(card);
            }

            foreach (var category in SafeTweaks.Select(static x => x.CategoryDisplay).Distinct(StringComparer.CurrentCultureIgnoreCase).OrderBy(static x => x, StringComparer.CurrentCultureIgnoreCase))
                if (!TweakCategories.Contains(category))
                    TweakCategories.Add(category);

            RefreshTweakViews();
            UpdateSelectedTweaksText();
        }
        catch (Exception ex)
        {
            Stage2StatusText = $"Каталог твиков не загружен: {ex.Message}";
        }
    }

    private async Task RefreshStage2StateAsync()
    {
        if (_disposed)
            return;

        Stage2StatusText = "Проверка текущего состояния и snapshot…";

        try
        {
            foreach (var card in SafeTweaks)
            {
                var state = await _tweakService.GetStateAsync(card.Definition, (_deepScanStageCts?.Token ?? _lifetimeCts.Token));
                var snapshot = await _snapshotService.GetLatestActiveForTweakAsync(card.Id, (_deepScanStageCts?.Token ?? _lifetimeCts.Token));
                card.UpdateState(state, snapshot);
            }

            await RefreshSnapshotsAsync();
            Stage2StatusText = "SAFE/BALANCED: каждое Apply создаёт snapshot; профили применяются пакетно с rollback при ошибке.";
            if (_initialized) UpdateOptimizationScanSummary(autoScan: false);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            Stage2StatusText = "Проверка остановлена при закрытии приложения.";
        }
        catch (Exception ex)
        {
            Stage2StatusText = $"Ошибка Stage 2: {ex.Message}";
        }
        finally
        {
        }
    }

    private async Task RefreshSnapshotsAsync()
    {
        var snapshots = await _snapshotService.ListAsync(_lifetimeCts.Token);

        Snapshots.Clear();
        foreach (var snapshot in snapshots)
            Snapshots.Add(new SnapshotItemViewModel(snapshot, RestoreSnapshotAsync));

        var activeCount = snapshots.Count(static s => !s.IsRestored);
        HasActiveSnapshots = activeCount > 0;
        SnapshotSummaryText = $"Активных snapshot: {activeCount} · всего: {snapshots.Count}";
    }

    private async Task ApplyTweakAsync(TweakCardViewModel card)
    {
        var actionPreview = FormatActionPreview(card.Definition);
        var effect = string.IsNullOrWhiteSpace(card.ExpectedEffect)
            ? string.Empty
            : $"\n\nОжидаемый эффект:\n{card.ExpectedEffect}";

        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Применить {card.Risk}-твик?\n\n{card.Name}\n\n{card.Description}{effect}\n\n" +
            $"Что будет изменено:\n{actionPreview}\n\n" +
            "До изменения Merzo Windows Optimizer сохранит исходные значения в snapshot. " +
            "Восстановление будет доступно сразу после применения." +
            (card.Definition.Risk == TweakRisk.Balanced ? "\n\nBALANCED может отключить функцию, которой вы пользуетесь." : string.Empty),
            card.Definition.Risk == TweakRisk.Balanced ? "Merzo Windows Optimizer — BALANCED" : "Merzo Windows Optimizer — SAFE",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (confirmation != MessageBoxResult.Yes)
            return;

        card.SetBusy(true);
        IsStage2Busy = true;
        Stage2StatusText = $"Создаю snapshot и применяю: {card.Name}…";

        try
        {
            var result = await _dispatcher.RunAsync(
                $"Apply tweak {card.Id}",
                token => _tweakService.ApplyAsync(card.Definition, token),
                _lifetimeCts.Token);

            card.SetResult(result.Message);
            Stage2StatusText = result.Message;

            if (!result.Success)
            {
                global::MerzoOptimizer.App.MerzoDialog.Show(
                    result.Message,
                    "Merzo Windows Optimizer — изменение не применено",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
            }

            await RefreshStage2StateAsync();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            Stage2StatusText = "Операция остановлена при закрытии приложения.";
        }
        catch (Exception ex)
        {
            Stage2StatusText = $"Ошибка применения: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Tweak error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            card.SetBusy(false);
            IsStage2Busy = false;
        }
    }

    private async Task RestoreTweakAsync(TweakCardViewModel card)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Вернуть последнее сохранённое состояние для:\n\n{card.Name}?",
            "Merzo Windows Optimizer — Undo",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (confirmation != MessageBoxResult.Yes)
            return;

        card.SetBusy(true);
        IsStage2Busy = true;
        Stage2StatusText = $"Восстанавливаю: {card.Name}…";

        try
        {
            var result = await _dispatcher.RunAsync(
                $"Restore tweak {card.Id}",
                token => _restoreService.RestoreLatestForTweakAsync(card.Id, token),
                _lifetimeCts.Token);

            card.SetResult(result.Message);
            Stage2StatusText = result.Message;
            await RefreshStage2StateAsync();
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            Stage2StatusText = $"Ошибка Undo: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Restore error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            card.SetBusy(false);
            IsStage2Busy = false;
        }
    }

    private async Task RestoreSnapshotAsync(SnapshotItemViewModel item)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Восстановить snapshot {item.ShortId}?\n\n{item.Name}",
            "Merzo Windows Optimizer — Restore snapshot",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (confirmation != MessageBoxResult.Yes)
            return;

        item.SetBusy(true);
        IsStage2Busy = true;

        try
        {
            var result = await _dispatcher.RunAsync(
                $"Restore snapshot {item.ShortId}",
                token => _restoreService.RestoreAsync(item.Id, token),
                _lifetimeCts.Token);

            Stage2StatusText = result.Message;
            if (!result.Success)
            {
                global::MerzoOptimizer.App.MerzoDialog.Show(result.Message, "Merzo Windows Optimizer — Restore error", MessageBoxButton.OK, MessageBoxImage.Warning);
            }

            await RefreshStage2StateAsync();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            Stage2StatusText = "Restore остановлен при закрытии приложения.";
        }
        catch (Exception ex)
        {
            Stage2StatusText = $"Ошибка Restore: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Restore error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            item.SetBusy(false);
            IsStage2Busy = false;
        }
    }

    private async Task RestoreAllAsync()
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            "Restore All вернёт все активные snapshot в обратном порядке, от новых к старым. Продолжить?",
            "Merzo Windows Optimizer — Restore All",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning);

        if (confirmation != MessageBoxResult.Yes)
            return;

        IsStage2Busy = true;
        Stage2StatusText = "Restore All…";

        try
        {
            var result = await _dispatcher.RunAsync(
                "Restore all active snapshots",
                token => _restoreService.RestoreAllActiveAsync(token),
                _lifetimeCts.Token);

            Stage2StatusText = result.Message;
            await RefreshStage2StateAsync();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            Stage2StatusText = "Restore All остановлен при закрытии приложения.";
        }
        catch (Exception ex)
        {
            Stage2StatusText = $"Ошибка Restore All: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Restore All error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsStage2Busy = false;
        }
    }

    private async Task RefreshStartupOptimizerAsync()
    {
        if (_disposed)
            return;

        StartupOptimizerStatusText = "Сканирую HKCU/HKLM Run и активные startup-snapshot…";
        try
        {
            var items = await _dispatcher.RunAsync(
                "Startup Optimizer scan",
                token => _startupOptimizer.ScanAsync(token),
                (_deepScanStageCts?.Token ?? _lifetimeCts.Token));

            StartupOptimizerItems.Clear();
            foreach (var item in items)
                StartupOptimizerItems.Add(new StartupItemViewModel(item, DisableStartupAsync, RestoreStartupAsync));

            var enabled = items.Count(static i => i.IsEnabled);
            var disabled = items.Count(static i => !i.IsEnabled && i.HasRestorePoint);
            StartupOptimizerStatusText = $"Найдено: {enabled} активных · отключено Merzo: {disabled}. Startup Folder и другие источники учитываются в общем Audit.";
            UpdateR44IntelligenceSummary();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            StartupOptimizerStatusText = $"Ошибка Startup Optimizer: {ex.Message}";
        }
        finally
        {
        }
    }

    private async Task DisableStartupAsync(StartupItemViewModel row)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Отключить автозагрузку?\n\n{row.Name}\n{row.Command}\n\n" +
            "Будет удалена только конкретная запись Run. До изменения создаётся snapshot, поэтому запись можно вернуть.",
            "Merzo Windows Optimizer — Startup Optimizer",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (confirmation != MessageBoxResult.Yes)
            return;

        row.SetBusy(true);
        IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync(
                $"Disable startup {row.Name}",
                token => _startupOptimizer.DisableAsync(row.Item, token),
                _lifetimeCts.Token);

            StartupOptimizerStatusText = result.Message;
            if (!result.Success)
                global::MerzoOptimizer.App.MerzoDialog.Show(result.Message, "Startup Optimizer", MessageBoxButton.OK, MessageBoxImage.Warning);

            await RefreshSnapshotsAsync();
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            StartupOptimizerStatusText = $"Ошибка отключения: {ex.Message}";
        }
        finally
        {
            row.SetBusy(false);
            IsStage2Busy = false;
        }

        await RefreshStartupOptimizerAsync();
    }

    private async Task RestoreStartupAsync(StartupItemViewModel row)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Вернуть автозагрузку?\n\n{row.Name}\n\nБудет восстановлено точное значение из последнего активного snapshot.",
            "Merzo Windows Optimizer — Restore startup",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes)
            return;

        row.SetBusy(true);
        IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync(
                $"Restore startup {row.Name}",
                token => _startupOptimizer.RestoreAsync(row.Item, token),
                _lifetimeCts.Token);
            StartupOptimizerStatusText = result.Message;
            await RefreshSnapshotsAsync();
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            StartupOptimizerStatusText = $"Ошибка восстановления: {ex.Message}";
        }
        finally
        {
            row.SetBusy(false);
            IsStage2Busy = false;
        }

        await RefreshStartupOptimizerAsync();
    }

    private async Task RefreshCleanupAsync()
    {
        if (_disposed) return;
        if (IsCleanupScanning)
        {
            var answer = global::MerzoOptimizer.App.MerzoDialog.Show("Сканирование очистки уже выполняется. Остановить старую проверку и запустить новую?", "Merzo — сканирование уже запущено", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (answer != MessageBoxResult.Yes) return;
            _cleanupScanCts?.Cancel();
            await Task.Delay(150);
        }

        if (!TryBeginOperation("cleanup-scan", out var lease)) return;
        using (lease)
        {
            _cleanupScanCts?.Dispose();
            _cleanupScanCts = CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token);
            _cleanupScanCts.CancelAfter(TimeSpan.FromSeconds(45));
            IsCleanupScanning = true;
            IsCleanupIndeterminate = true;
            SelectedCleanupTabIndex = 2;
            CleanupOperationTitle = "Сканирование очистки";
            CleanupOperationPhase = "Поиск временных файлов";
            CleanupOperationDetail = "Проверяю категории и подсчитываю файлы. Интерфейс программы остаётся доступным.";
            CleanupOperationResult = "Если Windows не ответит за 45 секунд, проверка будет остановлена, а программу не заблокирует.";
            CleanupOperationSteps.Clear(); CleanupOperationSteps.Add("→ Сканирование запущено"); CleanupProgress=0;
            CleanupStatusText = "Сканирование: анализирую категории…";
            try
            {
                var categories = await _dispatcher.RunAsync("Cleanup scan", token => _cleanupService.ScanAsync(token), _cleanupScanCts.Token);
                CleanupCategories.Clear();
                foreach (var category in categories)
                {
                    var row = new CleanupCategoryViewModel(category, CleanCategoryAsync);
                    row.PropertyChanged += CleanupCategoryOnPropertyChanged;
                    CleanupCategories.Add(row);
                }
                CleanupProgress=100; IsCleanupIndeterminate=false;
                CleanupOperationPhase="Сканирование завершено";
                CleanupOperationDetail=$"Проверено категорий: {categories.Count}";
                CleanupOperationResult=$"Найдено: {FormatBytes(categories.Sum(static c=>c.EligibleBytes))}.";
                CleanupOperationSteps.Add($"✓ Готово · категорий {categories.Count} · {CleanupOperationResult}");
                CleanupStatusText = $"Категорий: {categories.Count} · найдено: {FormatBytes(categories.Sum(static c => c.EligibleBytes))} · файлы младше 24 часов не трогаем.";
                UpdateCleanupSelectionText(); CleanAllSafeCommand.RaiseCanExecuteChanged(); CleanSelectedCommand.RaiseCanExecuteChanged();
                UpdateR44IntelligenceSummary();
            }
            catch (OperationCanceledException)
            {
                IsCleanupIndeterminate=false;
                CleanupOperationPhase="Сканирование остановлено";
                CleanupOperationResult=_lifetimeCts.IsCancellationRequested ? "Приложение закрывается." : "Проверка отменена пользователем или по таймауту. Можно запустить её повторно.";
                CleanupOperationSteps.Add("■ Сканирование остановлено; зависшая проверка больше не блокирует повторный запуск.");
                CleanupStatusText=CleanupOperationResult;
            }
            catch (Exception ex)
            {
                IsCleanupIndeterminate=false; CleanupStatusText=$"Ошибка Cleanup scan: {ex.Message}"; CleanupOperationPhase="Ошибка сканирования"; CleanupOperationResult=ex.Message;
            }
            finally { IsCleanupScanning=false; _cleanupScanCts?.Dispose(); _cleanupScanCts=null; }
        }
    }

    private void BeginCleanupVisual(string title, int categories, int files, long bytes)
    {
        SelectedCleanupTabIndex = 2;
        CleanupOperationSteps.Clear();
        CleanupProgress = 0;
        CleanupOperationTitle = title;
        CleanupOperationPhase = "Подготовка";
        CleanupOperationDetail = $"Категорий: {categories} · файлов: {files} · исходный объём: {FormatBytes(bytes)}";
        CleanupOperationResult = "Режим резервирования выбирает пользователь перед запуском.";
        CleanupOperationSteps.Add($"● Подготовка · категорий {categories} · файлов {files} · {FormatBytes(bytes)}");
    }

    private void SetCleanupVisual(double progress, string phase, string detail, string? result = null)
    {
        CleanupProgress = progress;
        CleanupOperationPhase = phase;
        CleanupOperationDetail = detail;
        if (!string.IsNullOrWhiteSpace(result)) CleanupOperationResult = result;
    }

    private async Task CleanCategoryAsync(CleanupCategoryViewModel card)
    {
        var choice = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Очистить категорию?\n\n{card.Name}\n{card.FileCountText} · {card.SizeText}\n{card.RootPath}\n\nДА — создать ZIP-backup + Snapshot и сохранить возможность Undo.\nНЕТ — удалить без backup; это освободит больше места, но вернуть файлы через Undo будет нельзя.\nОТМЕНА — ничего не делать.",
            "Merzo Windows Optimizer — способ очистки", MessageBoxButton.YesNoCancel, MessageBoxImage.Question);
        if (choice == MessageBoxResult.Cancel) return;
        var createBackup = choice == MessageBoxResult.Yes;
        if (!createBackup && global::MerzoOptimizer.App.MerzoDialog.Show("Вы выбрали очистку БЕЗ резервной копии. Удалённые файлы этой операции нельзя будет вернуть через Merzo Undo. Продолжить?", "Подтверждение необратимой очистки", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        if (!TryBeginOperation("cleanup-run", out var lease)) return;
        using (lease)
        {
            _cleanupOperationCts?.Dispose(); _cleanupOperationCts=CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token);
            IsCleanupOperationRunning=true; IsCleanupIndeterminate=true;
            BeginCleanupVisual($"Очистка: {card.Name}", 1, card.Snapshot.EligibleFileCount, card.EligibleBytes);
            CleanupOperationSteps.Add($"→ Режим: {(createBackup ? "с ZIP-backup + Undo" : "без backup · необратимо")}");
            CleanupOperationSteps.Add($"→ Путь · {card.RootPath}");
            SetCleanupVisual(15,"Подготовка",$"Проверяю категорию «{card.Name}».",createBackup?"Будет создан ZIP-backup + Snapshot.":"Backup отключён пользователем. Undo для файлов недоступен.");
            card.SetBusy(true);
            try
            {
                SetCleanupVisual(30,createBackup?"Backup → Snapshot → Очистка":"Очистка без backup",createBackup?"Сохраняю файлы, создаю Snapshot и удаляю исходники.":"Удаляю только подходящие временные файлы; занятые и защищённые пропускаются.");
                var result=await _dispatcher.RunAsync($"Cleanup {card.Id}", token=>_cleanupService.CleanAsync(card.Id,createBackup,token),_cleanupOperationCts.Token);
                IsCleanupIndeterminate=false; SetCleanupVisual(90,"Проверка результата","Проверяю итог операции…");
                CleanupStatusText=result.Changed?$"{result.Message} Освобождено: {FormatBytes(result.NetFreedBytes)}.":result.Message;
                if(result.Changed)
                {
                    CleanupOperationSteps.Add($"✓ Удалено: {result.ArchivedFileCount} · освобождено {FormatBytes(result.NetFreedBytes)}");
                    SetCleanupVisual(100,"Готово",$"Категория «{card.Name}» обработана.",createBackup?$"Undo доступен · Snapshot {(result.SnapshotId is Guid id?id.ToString("N")[..8]:"—")}":"Очистка выполнена без backup по выбору пользователя.");
                }
                else { CleanupOperationSteps.Add($"✓ Без изменений · {result.Message}"); SetCleanupVisual(100,"Готово без изменений",result.Message); }
                global::MerzoOptimizer.App.MerzoDialog.Show(CleanupStatusText+"\n\nПодробности остаются на вкладке «Ход очистки».","Merzo — очистка завершена",MessageBoxButton.OK,result.Success?MessageBoxImage.Information:MessageBoxImage.Warning);
                if(createBackup) await RefreshSnapshotsAsync();
            }
            catch(OperationCanceledException)
            {
                IsCleanupIndeterminate=false; CleanupStatusText="Очистка остановлена."; CleanupOperationSteps.Add("■ Операция отменена пользователем."); SetCleanupVisual(CleanupProgress,"Остановлено","Запрос отменён.",createBackup?"Созданные безопасные данные остаются доступными для восстановления, если успели сохраниться.":"Удалённые до отмены файлы без backup вернуть нельзя.");
            }
            catch(Exception ex)
            {
                IsCleanupIndeterminate=false; CleanupStatusText=$"Ошибка очистки: {ex.Message}"; CleanupOperationSteps.Add($"✕ Ошибка · {ex.Message}"); SetCleanupVisual(CleanupProgress,"Ошибка","Операция остановлена.",ex.Message);
            }
            finally { card.SetBusy(false); IsCleanupOperationRunning=false; _cleanupOperationCts?.Dispose(); _cleanupOperationCts=null; }
            _ = RefreshCleanupAsync();
        }
    }

    private async Task RefreshDebloatAsync()
    {
        if (_disposed)
            return;

        DebloatStatusText = "Сканирую необязательные Appx…";
        try
        {
            var apps = await _dispatcher.RunAsync(
                "Debloat Appx scan",
                token => _debloatScanner.ScanAsync(token),
                (_deepScanStageCts?.Token ?? _lifetimeCts.Token));

            DebloatApps.Clear();
            foreach (var app in apps)
                DebloatApps.Add(app);

            DebloatStatusText = $"Найдено необязательных Appx: {apps.Count(static a => a.Installed)}. Удаление остаётся заблокированным до гарантированного Undo для Appx.";
            UpdateR44IntelligenceSummary();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            DebloatStatusText = $"Appx-аудит недоступен: {ex.Message}";
        }
        finally
        {
        }
    }

    private async Task RunDeepOptimizationScanAsync()
    {
        if (_disposed) return;
        if (IsDeepScanning) { global::MerzoOptimizer.App.MerzoDialog.Show("Проверка уже выполняется. Используйте кнопку «Отменить», если хотите остановить её.","Merzo — проверка уже запущена",MessageBoxButton.OK,MessageBoxImage.Information); return; }
        if(!TryBeginOperation("optimization-scan",out var lease))return;
        using(lease)
        {
            _deepScanCts?.Dispose(); _deepScanCts=CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token);
            IsDeepScanning=true; SelectedOptimizationTabIndex=4; DeepScanSteps.Clear(); DeepScanProgress=0; DeepScanStatusText="Запуск проверки…";
            DeepScanSummaryText=$"База: {SafeTweaks.Count} правил + Startup + Cleanup + Services + Tasks + Power + Appx. Каждый этап ограничен по времени.";
            try
            {
                await RunDeepScanStageAsync(1,8,"Windows / build / оборудование",RunAuditAsync);
                await RunDeepScanStageAsync(2,8,$"База твиков ({SafeTweaks.Count} правил)",RefreshStage2StateAsync);
                await RunDeepScanStageAsync(3,8,"Автозагрузка",RefreshStartupOptimizerAsync);
                await RunDeepScanStageAsync(4,8,"Очистка и размеры кэшей",RefreshCleanupAsync);
                await RunDeepScanStageAsync(5,8,"Службы и Scheduled Tasks",RefreshServicesTasksAsync);
                await RunDeepScanStageAsync(6,8,"Power plans",RefreshPowerAsync);
                await RunDeepScanStageAsync(7,8,"Appx / Debloat audit",RefreshDebloatAsync);
                await RunDeepScanStageAsync(8,8,"Итог и профили",()=>{UpdateOptimizationScanSummary(false);return Task.CompletedTask;});
                _deepScanCts.Token.ThrowIfCancellationRequested(); DeepScanProgress=100;DeepScanStatusText="Глубокая проверка завершена";HasOptimizationScanResults=true;SelectedOptimizationTabIndex=0;DeepScanSteps.Add("✓ Готово — рекомендация сформирована.");
            }
            catch(OperationCanceledException){DeepScanStatusText="Проверка отменена. Можно сразу запустить новую.";DeepScanSteps.Add("■ Проверка остановлена; busy-состояние сброшено.");}
            catch(Exception ex){DeepScanStatusText=$"Проверка завершена с ошибкой: {ex.Message}";DeepScanSteps.Add($"✕ {ex.Message}");}
            finally{_deepScanStageCts?.Cancel();_deepScanStageCts?.Dispose();_deepScanStageCts=null;_deepScanCts?.Dispose();_deepScanCts=null;IsDeepScanning=false;}
        }
    }

    private async Task RunDeepScanStageAsync(int stage,int total,string name,Func<Task> action)
    {
        _deepScanCts?.Token.ThrowIfCancellationRequested(); _deepScanStageCts?.Dispose(); _deepScanStageCts=CancellationTokenSource.CreateLinkedTokenSource(_deepScanCts?.Token ?? _lifetimeCts.Token);
        DeepScanStatusText=$"Этап {stage}/{total}: {name}"; DeepScanProgress=(stage-1)*100.0/total; DeepScanSteps.Add($"→ {stage}/{total} · {name}…");
        var task=action(); var timeout=Task.Delay(TimeSpan.FromSeconds(35),_deepScanStageCts.Token); var completed=await Task.WhenAny(task,timeout);
        if(completed!=task)
        {
            _deepScanStageCts.Cancel(); DeepScanSteps[DeepScanSteps.Count-1]=$"⚠ {stage}/{total} · {name} · превышено 35 сек, этап остановлен; проверка продолжится"; DeepScanProgress=stage*100.0/total; return;
        }
        try{await task;}catch(OperationCanceledException) when(!(_deepScanCts?.IsCancellationRequested??false)){DeepScanSteps[DeepScanSteps.Count-1]=$"⚠ {stage}/{total} · {name} · отменено/таймаут";return;}
        DeepScanProgress=stage*100.0/total;DeepScanSteps[DeepScanSteps.Count-1]=$"✓ {stage}/{total} · {name}";
    }

    private Task CancelDeepOptimizationScanAsync(){_deepScanCts?.Cancel();DeepScanStatusText="Отмена проверки…";return Task.CompletedTask;}
    private Task CancelCleanupOperationAsync(){_cleanupScanCts?.Cancel();_cleanupOperationCts?.Cancel();CleanupOperationPhase="Отмена операции…";return Task.CompletedTask;}

    private bool TryBeginOperation(string key,out MerzoOperationGuard? lease)
    {
        if(MerzoOperationGuard.TryAcquire(key,out lease,out var active))return true;
        var message=$"Такая операция уже отмечена как выполняющаяся.\n\nОперация: {key}\nPID: {active?.ProcessId}\nЗапущена: {active?.StartedAt.LocalDateTime:G}\nПроцесс: {active?.ProcessName}\n\nЕсли это зависший экземпляр Merzo, закрыть его принудительно?";
        var answer=global::MerzoOptimizer.App.MerzoDialog.Show(message,"Merzo — обнаружена дублирующая фоновая операция",MessageBoxButton.YesNoCancel,MessageBoxImage.Warning);
        if(answer==MessageBoxResult.Yes && active is not null && MerzoOperationGuard.TryTerminateOwned(active)){global::MerzoOptimizer.App.MerzoDialog.Show("Старый экземпляр Merzo закрыт. Запустите операцию ещё раз.","Merzo",MessageBoxButton.OK,MessageBoxImage.Information);} 
        return false;
    }

    private void UpdateR44IntelligenceSummary()
    {
        var applicable = SafeTweaks.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var applied = applicable.Count(static x => x.IsApplied);
        var available = applicable.Count(static x => !x.IsApplied);
        var unsupported = SafeTweaks.Count(static x => !x.IsSupported);

        var privacy = SafeTweaks.Where(card =>
            card.ProfileTags.Contains("privacy_safe", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("privacy_strict", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("privacy_maximum", StringComparer.OrdinalIgnoreCase)).ToArray();
        var privacyApplicable = privacy.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var privacyApplied = privacyApplicable.Count(static x => x.IsApplied);
        var privacyAvailable = privacyApplicable.Count(static x => !x.IsApplied);

        var performance = SafeTweaks.Where(card =>
            card.ProfileTags.Contains("performance", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("process_safe", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("process_lite", StringComparer.OrdinalIgnoreCase)).ToArray();
        var performanceApplicable = performance.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var performanceApplied = performanceApplicable.Count(static x => x.IsApplied);
        var performanceAvailable = performanceApplicable.Count(static x => !x.IsApplied);

        var gaming = SafeTweaks.Where(card =>
            card.ProfileTags.Contains("gaming_build_safe", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("gaming_build_performance", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("gaming_build_extreme", StringComparer.OrdinalIgnoreCase) ||
            card.ProfileTags.Contains("gaming_build_lab", StringComparer.OrdinalIgnoreCase)).ToArray();
        var gamingApplicable = gaming.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var gamingApplied = gamingApplicable.Count(static x => x.IsApplied);
        var gamingAvailable = gamingApplicable.Count(static x => !x.IsApplied);

        var startupActiveManageable = StartupOptimizerItems.Count(static x => x.Item.IsEnabled && x.Item.CanManage);
        var startupProtected = StartupOptimizerItems.Count(static x => x.Item.IsEnabled && !x.Item.CanManage);
        var startupDisabledByMerzo = StartupOptimizerItems.Count(static x => !x.Item.IsEnabled && x.Item.HasRestorePoint);
        var serviceCandidates = ServiceAuditItems.Count(static x => x.Snapshot.CanManage && !x.Snapshot.IsDisabled);
        var taskCandidates = ScheduledTaskAuditItems.Count(static x => x.Snapshot.CanManage && x.Snapshot.Enabled);
        var cleanupBytes = CleanupCategories.Where(static x => x.CanClean).Sum(static x => x.EligibleBytes);

        SmartAuditOverallText = $"Твики: применено {applied} · доступно {available} · не применимо {unsupported}. Проверка остаётся read-only до явного Apply.";
        SmartAuditPrivacyText = $"{privacyApplied}/{privacyApplicable.Length} настроено · ещё {privacyAvailable}";
        SmartAuditPerformanceText = $"{performanceApplied}/{performanceApplicable.Length} настроено · ещё {performanceAvailable}";
        SmartAuditGamingText = $"{gamingApplied}/{gamingApplicable.Length} настроено · ещё {gamingAvailable}";
        SmartAuditStartupText = $"Run: {startupActiveManageable} управляемых · {startupProtected} защищённых · {startupDisabledByMerzo} отключено Merzo";
        SmartAuditServicesText = $"Кандидаты: службы {serviceCandidates} · задачи {taskCandidates}";
        SmartAuditCleanupText = $"Можно безопасно очистить: {FormatBytesCompact(cleanupBytes)}";
        SmartAuditRecommendationText = $"Рекомендуется {RecommendedProfileTitle}. Merzo применит только отсутствующие поддерживаемые правила; уже настроенное повторно не меняется.";

        var privacySafe = CountProfileAvailable("privacy_safe");
        var privacyStrict = CountProfileAvailable("privacy_strict");
        var privacyMaximum = CountProfileAvailable("privacy_maximum");
        PrivacyCoverageText = $"SAFE: ещё {privacySafe} · STRICT: ещё {privacyStrict} · MAXIMUM: ещё {privacyMaximum}. Состояния берутся из фактического аудита, а не из предположений.";

        var selected = SafeTweaks.Where(static x => x.IsSelected).ToArray();
        var selectedSafe = selected.Count(static x => x.Definition.Risk == TweakRisk.Safe);
        var selectedBalanced = selected.Count(static x => x.Definition.Risk == TweakRisk.Balanced);
        ProfilePlanText = selected.Length == 0
            ? "Выберите сборку: Merzo покажет план до любых изменений."
            : $"План: {selected.Length} твиков · SAFE {selectedSafe} · BALANCED {selectedBalanced} · затем Snapshot → Apply → Verify → Undo/Restore.";

        StartupManagerSummaryText = $"Run-управление: {startupActiveManageable} активных · защищено {startupProtected} · отключено Merzo {startupDisabledByMerzo}. Общий аудит источников: {StartupItems.Count}.";

        var installed = DebloatApps.Where(static x => x.Installed).ToArray();
        string[] consumerTokens = ["Clipchamp", "Solitaire", "GetHelp", "Getstarted", "BingNews", "BingWeather"];
        string[] protectedTokens = ["WindowsStore", "SecHealthUI", "ShellExperienceHost", "StartMenuExperienceHost", "DesktopAppInstaller", "VCLibs", "UI.Xaml", "AAD.BrokerPlugin", "AccountsControl"];
        var obviousConsumer = installed.Count(app => consumerTokens.Any(token => app.PackageName?.Contains(token, StringComparison.OrdinalIgnoreCase) == true));
        var protectedSystem = installed.Count(app => protectedTokens.Any(token => app.PackageName?.Contains(token, StringComparison.OrdinalIgnoreCase) == true));
        var optional = Math.Max(0, installed.Length - obviousConsumer - protectedSystem);
        DebloatClassificationText = $"Consumer bloat: {obviousConsumer} · по желанию: {optional} · системные/защищённые: {protectedSystem}. Удаление остаётся audit-only до гарантированного Undo.";
    }

    private void UpdateOptimizationScanSummary(bool autoScan)
    {
        var applicable = SafeTweaks.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();
        var already = applicable.Count(static x => x.IsApplied);
        var available = applicable.Count(static x => !x.IsApplied);
        var mixed = SafeTweaks.Count(static x => x.StateText == "Частично");
        var unsupported = SafeTweaks.Count(static x => !x.IsSupported);
        var knownBuildDetected = SafeTweaks.Count(static x => x.Definition.ScanOnly && x.IsApplied);
        var knownBuildPartial = SafeTweaks.Count(static x => x.Definition.ScanOnly && x.StateText == "Частично");

        var light = CountProfileAvailable("merzo_light");
        var standard = CountProfileAvailable("merzo_game");
        var maximum = CountProfileAvailable("merzo_extreme");
        var liteBuild = CountProfileAvailable("lite_build");
        var startupCandidates = StartupOptimizerItems.Count(static x => x.Item.IsEnabled && x.Item.CanManage && !x.Item.HasRestorePoint);
        var serviceCandidates = ServiceAuditItems.Count(static x => x.Snapshot.CanManage && !x.Snapshot.IsDisabled);
        var taskCandidates = ScheduledTaskAuditItems.Count(static x => x.Snapshot.CanManage && x.Snapshot.Enabled);
        var cleanupBytes = CleanupCategories.Where(static x => x.CanClean).Sum(static x => x.EligibleBytes);
        var appxCandidates = DebloatApps.Count(static x => x.Installed);

        LightProfileAvailableText = light == 0 ? "ЛАЙТ уже настроен" : $"ЛАЙТ · ещё {light} изменений";
        StandardProfileAvailableText = standard == 0 ? "GAME уже настроен" : $"GAME · ещё {standard} изменений";
        MaximumProfileAvailableText = maximum == 0 ? "EXTREME уже настроен" : $"EXTREME · ещё {maximum} изменений";
        LiteBuildProfileAvailableText = liteBuild == 0 ? "Уже настроено · Privacy MAX" : $"Ещё {liteBuild} изменений · Privacy MAX";

        DeepScanSummaryText =
            $"База {SafeTweaks.Count}: уже оптимизировано {already} · доступно {available} · частично {mixed} · не применимо {unsupported} · " +
            $"сборочных маркеров найдено {knownBuildDetected + knownBuildPartial}. Startup: {startupCandidates} · службы: {serviceCandidates} · задачи: {taskCandidates} · Appx: {appxCandidates} · очистка: {FormatBytesCompact(cleanupBytes)}.";

        var appliedRatio = applicable.Length == 0 ? 1.0 : already / (double)applicable.Length;
        string recommendedId;
        if (available <= 8 || appliedRatio >= 0.70)
        {
            recommendedId = "light";
            RecommendedProfileReason = $"Система уже сильно настроена: применено {already} из {applicable.Length} обратимых правил. ЛАЙТ добавит только недостающие изменения и полностью проверит privacy/telemetry.";
        }
        else
        {
            recommendedId = "standard";
            RecommendedProfileReason = knownBuildDetected > 0
                ? $"Найдено {knownBuildDetected} известных сборочных твиков. GAME дополнит их только отсутствующими обратимыми настройками."
                : $"Доступно ещё {available} обратимых настроек. Для игрового ПК GAME даёт ЛАЙТ-базу плюс производительность и сетевой игровой профиль.";
        }

        IsLightRecommended = recommendedId == "light";
        IsStandardRecommended = recommendedId == "standard";
        IsMaximumRecommended = recommendedId == "maximum";
        RecommendedProfileTitle = recommendedId == "light" ? "ЛАЙТ" : recommendedId == "standard" ? "GAME" : "EXTREME";

        ProfileRecommendationText =
            $"Рекомендуется {RecommendedProfileTitle}. ЛАЙТ: {light} · GAME: {standard} · EXTREME: {maximum}. " +
            (knownBuildDetected > 0
                ? $"Эта Windows уже содержит {knownBuildDetected} известных сборочных настроек — Merzo не применит их повторно."
                : "Опасные/устаревшие сборочные правила проверяются отдельно и автоматически не применяются.");

        UpdateR44IntelligenceSummary();

        if (autoScan)
            DeepScanStatusText = "Быстрая автопроверка завершена. Для персональной рекомендации нажмите большую кнопку проверки.";
    }

    private int CountProfileAvailable(string tag) =>
        SafeTweaks.Count(card => !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied && card.ProfileTags.Contains(tag, StringComparer.OrdinalIgnoreCase));

    private static string FormatBytesCompact(long bytes)
    {
        if (bytes >= 1024L * 1024 * 1024) return $"{bytes / (1024d * 1024 * 1024):0.0} GB";
        if (bytes >= 1024L * 1024) return $"{bytes / (1024d * 1024):0.0} MB";
        if (bytes >= 1024) return $"{bytes / 1024d:0.0} KB";
        return $"{bytes} B";
    }

    private void TweakCardOnPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(TweakCardViewModel.IsSelected))
            return;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        ApplySelectedTweaksCommand.RaiseCanExecuteChanged();
    }

    private void UpdateSelectedTweaksText()
    {
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedTweaksText = selected == 0 ? "Ничего не выбрано" : $"Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";
        UpdateR44IntelligenceSummary();
    }

    private void RefreshTweakViews()
    {
        RefreshIndividualTweaks();
        RefreshSelectedTweaks();
    }

    private void RefreshSelectedTweaks()
    {
        SelectedTweaks.Clear();
        foreach (var card in SafeTweaks.Where(static x => x.IsSelected))
            SelectedTweaks.Add(card);
    }

    private void RefreshIndividualTweaks()
    {
        var category = SelectedTweakCategory;
        var query = TweakSearchText.Trim();

        var items = SafeTweaks.Where(card =>
            (string.Equals(category, "Все", StringComparison.OrdinalIgnoreCase) || string.Equals(card.CategoryDisplay, category, StringComparison.CurrentCultureIgnoreCase)) &&
            (query.Length == 0 || card.Name.Contains(query, StringComparison.CurrentCultureIgnoreCase) ||
             card.Description.Contains(query, StringComparison.CurrentCultureIgnoreCase) ||
             card.CategoryDisplay.Contains(query, StringComparison.CurrentCultureIgnoreCase)))
            .OrderBy(static x => x.Definition.Risk)
            .ThenBy(static x => x.CategoryDisplay, StringComparer.CurrentCultureIgnoreCase)
            .ThenBy(static x => x.Name, StringComparer.CurrentCultureIgnoreCase)
            .ToArray();

        IndividualTweaks.Clear();
        foreach (var card in items)
            IndividualTweaks.Add(card);
    }

    private Task SelectMaximumSafeAsync()
    {
        foreach (var card in SafeTweaks)
            card.IsSelected = card.Definition.Risk == TweakRisk.Safe && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        return Task.CompletedTask;
    }

    private Task SelectGamingTaggedPresetAsync(string tag, string title)
    {
        _selectedProfileTag = tag;
        foreach (var card in SafeTweaks)
        {
            var match = card.Definition.ProfileTags?.Contains(tag, StringComparer.OrdinalIgnoreCase) == true;
            card.IsSelected = match && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        }
        RefreshSelectedTweaks();
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedOptimizationTabIndex = 3;
        SelectedTweaksText = selected == 0
            ? $"{title}: новых неприменённых настроек нет"
            : $"{title} · Выбрано: {selected} · SAFE: {safe} · BALANCED/EXPERIMENTAL: {balanced}";
        Stage2StatusText = selected == 0
            ? $"{title}: Registry/Policy уже настроены; при применении Gaming Build всё равно будут проверены его службы/задачи и сеть."
            : $"{title}: выбрано {selected} Registry/Policy. После подтверждения Merzo также проверит подходящие службы/задачи и Gaming Network. Всё выполняется по этапам с Snapshot/Undo.";
        return Task.CompletedTask;
    }

    private async Task SelectNamedCategoryPresetAsync(string title, IReadOnlyCollection<string> categories, bool safeOnly)
    {
        await SelectCategoryProfileAsync(categories, safeOnly);
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedOptimizationTabIndex = 3;
        // UI contract examples: GAMING · Выбрано / DEVELOPER · Выбрано.
        SelectedTweaksText = selected == 0
            ? $"{title}: новых неприменённых настроек нет"
            : $"{title} · Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";
        Stage2StatusText = selected == 0
            ? $"{title}: подходящие настройки уже применены или не поддерживаются на этом ПК."
            : $"{title} загружен: {selected} настроек. Проверьте вкладку «Выбранное» и применяйте только после просмотра списка.";
    }

    private Task SelectCategoryProfileAsync(IReadOnlyCollection<string> categories, bool safeOnly)
    {
        _selectedProfileTag = null;
        foreach (var card in SafeTweaks)
        {
            var categoryMatch = categories.Contains(card.Category, StringComparer.OrdinalIgnoreCase);
            var riskMatch = !safeOnly || card.Definition.Risk == TweakRisk.Safe;
            card.IsSelected = categoryMatch && riskMatch && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        }
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        SelectedOptimizationTabIndex = 3;
        return Task.CompletedTask;
    }

    private Task SelectProfileAsync(string profileTag)
    {
        _selectedProfileTag = profileTag;
        foreach (var card in SafeTweaks)
            card.IsSelected = !card.Definition.ScanOnly && card.ProfileTags.Contains(profileTag, StringComparer.OrdinalIgnoreCase) && card.IsSupported && !card.IsApplied;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        SelectedOptimizationTabIndex = 3;
        Stage2StatusText = profileTag switch
        {
            "merzo_light" => "ЛАЙТ выбран: чистая Windows, максимальная privacy/telemetry-разгрузка, реклама/предложения, фон и безопасные процессы. Проводник → Этот компьютер; классическое контекстное меню — на Windows 11.",
            "merzo_game" => "GAME выбран: всё из ЛАЙТ + игровые/performance-твики и Gaming Network SAFE.",
            "merzo_extreme" => "EXTREME выбран: всё из GAME + максимально агрессивная обратимая разгрузка и Gaming Network EXTREME.",
            "light" => "LIGHT выбран: базовая оптимизация + безопасная приватность.",
            "standard" => "STANDARD выбран: оптимизация + строгая privacy/telemetry-настройка.",
            "maximum" => "MAXIMUM выбран: глубокая оптимизация + максимальная обратимая приватность.",
            "lite_build" => "LITE BUILD выбран: расширенный профиль + максимальная privacy/telemetry-настройка.",
            "background_light" => "ФОНОВАЯ РАЗГРУЗКА выбрана: Edge/Widgets/background apps/sync и безопасные источники лишнего фона. Просмотрите список перед применением.",
            "performance" => "PERFORMANCE выбран: приоритет отзывчивости и меньшего фонового потребления; возможен больший расход энергии.",
            _ => "Профиль выбран."
        };
        return Task.CompletedTask;
    }

    private Task ClearTweakSelectionAsync()
    {
        _selectedProfileTag = null;
        foreach (var card in SafeTweaks)
            card.IsSelected = false;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        return Task.CompletedTask;
    }

    private async Task ApplySelectedTweaksAsync()
    {
        var selected = SafeTweaks.Where(static c => c.IsSelected && !c.Definition.ScanOnly && c.IsSupported && !c.IsApplied).ToArray();
        var profileTag = _selectedProfileTag;
        var merzoLight = profileTag == "merzo_light";
        var merzoGame = profileTag == "merzo_game";
        var merzoExtreme = profileTag == "merzo_extreme";
        var gamingSafe = profileTag == "gaming_build_safe";
        var gamingPerformance = profileTag == "gaming_build_performance" || merzoGame;
        var gamingExtreme = profileTag == "gaming_build_extreme" || merzoExtreme;
        var gamingLab = profileTag == "gaming_build_lab";
        var gamingBuild = gamingSafe || gamingPerformance || gamingExtreme || gamingLab;
        var gamingNetworkMode = gamingExtreme || gamingLab ? "EXTREME" : gamingBuild ? "SAFE" : null;
        var profileIncludesTelemetry = merzoLight || merzoGame || merzoExtreme || profileTag is "standard" or "maximum" or "lite_build" || gamingPerformance || gamingExtreme || gamingLab;
        var profileIncludesWer = merzoLight || merzoGame || merzoExtreme || profileTag is "maximum" or "lite_build" || gamingExtreme || gamingLab;

        IReadOnlyList<ServiceAuditItem> services = Array.Empty<ServiceAuditItem>();
        IReadOnlyList<ScheduledTaskAuditItem> tasks = Array.Empty<ScheduledTaskAuditItem>();
        if (profileIncludesTelemetry)
        {
            var serviceSnapshot = await _serviceAudit.ScanAsync(_lifetimeCts.Token);
            var serviceNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "DiagTrack", "dmwappushservice" };
            if (profileIncludesWer) serviceNames.Add("WerSvc");
            if (gamingPerformance || gamingExtreme || gamingLab)
            {
                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service" }) serviceNames.Add(name);
            }
            if (gamingExtreme || gamingLab)
            {
                foreach (var name in new[] { "icssvc", "SCardSvr", "ScDeviceEnum", "SCPolicySvc", "SensorDataService", "SensorService", "SensrSvc", "SEMgrSvc" }) serviceNames.Add(name);
            }
            if (gamingLab)
            {
                serviceNames.Add("TabletInputService");
                serviceNames.Add("WbioSrvc");
            }
            services = serviceSnapshot.Where(x => serviceNames.Contains(x.ServiceName) && x.CanManage && !x.IsDisabled).ToArray();

            var taskSnapshot = await _taskAudit.ScanAsync(_lifetimeCts.Token);
            tasks = taskSnapshot.Where(x => x.CanManage && x.Enabled && IsPrivacyTelemetryTask(x) &&
                (profileIncludesWer || !x.FullPath.Contains(@"\Microsoft\Windows\Windows Error Reporting\", StringComparison.OrdinalIgnoreCase))).ToArray();
        }

        var networkSteps = gamingNetworkMode is null ? 0 : 1;
        if (selected.Length == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0)
        {
            Stage2StatusText = "В выбранном профиле нет неприменённых изменений.";
            return;
        }

        var balancedCount = selected.Count(static c => c.Definition.Risk == TweakRisk.Balanced);
        var registryActions = selected.Sum(static c => c.Definition.RegistryActions.Count);
        var total = selected.Length + services.Count + tasks.Count + networkSteps;
        var profileText = profileTag switch
        {
            "merzo_light" => $"ЛАЙТ — Чистая Windows: максимальная privacy/telemetry-разгрузка, меньше рекламы/фона, Explorer UX и безопасное сокращение процессов. Services {services.Count}, tasks {tasks.Count}.",
            "merzo_game" => $"GAME — всё из ЛАЙТ + performance/game tweaks, снижение фоновой нагрузки и Gaming Network SAFE. Services {services.Count}, tasks {tasks.Count}.",
            "merzo_extreme" => $"EXTREME — всё из GAME + агрессивная разгрузка Windows, дополнительные условные службы/задачи и Gaming Network EXTREME. Services {services.Count}, tasks {tasks.Count}.",
            "light" => "Privacy SAFE: безопасные privacy-политики без отключения telemetry-служб.",
            "standard" => $"Privacy STRICT: telemetry services {services.Count}, telemetry tasks {tasks.Count}.",
            "maximum" => $"Privacy MAX: telemetry/WER services {services.Count}, telemetry/WER tasks {tasks.Count}.",
            "lite_build" => $"Privacy MAX для LITE BUILD: services {services.Count}, tasks {tasks.Count}.",
            "gaming_build_safe" => "GAME BUILD SAFE: безопасные игровые/фоновые твики + Gaming Network SAFE. Системные службы автоматически не отключаются.",
            "gaming_build_performance" => $"GAME BUILD PERFORMANCE: игровые и performance-твики + снижение источников фоновых процессов + {services.Count} подходящих служб + {tasks.Count} telemetry tasks + Gaming Network SAFE.",
            "gaming_build_extreme" => $"GAME BUILD EXTREME: агрессивная разгрузка Windows + {services.Count} условных служб + {tasks.Count} задач + Gaming Network EXTREME с сохранением baseline адаптера.",
            "gaming_build_lab" => $"GAME BUILD LAB: EXTREME + экспериментальные scheduler/GPU/MMCSS-твики и дополнительные условные службы. Это режим для A/B тестов, а не универсальный пресет.",
            _ => "Ручной набор: дополнительные службы и сеть автоматически не изменяются."
        };
        var warning = balancedCount > 0 ? $"\nBALANCED/EXPERIMENTAL твиков: {balancedCount}." : string.Empty;
        var gamingWarning = gamingExtreme || gamingLab
            ? "\n\nВНИМАНИЕ: EXTREME может отключить условные фоновые функции Hotspot/Smart Card/Sensors и изменить параметры сетевого адаптера. Defender, Windows Update, Store, IPv6 и pagefile не отключаются. Все поддерживаемые изменения остаются под Snapshot/Undo."
            : string.Empty;
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Применить выбранный пакет?\n\nRegistry/Policy: {selected.Length}\nRegistry-операций: {registryActions}\nСлужб/фоновых источников: {services.Count}\nScheduled Tasks: {tasks.Count}\nGaming Network: {gamingNetworkMode ?? "нет"}{warning}\n\n{profileText}{gamingWarning}\n\nКаждая поддерживаемая системная операция идёт через Snapshot → Apply → Verify → Log → Undo. При ошибке уже выполненные Snapshot-изменения этого запуска восстанавливаются автоматически.",
            gamingBuild ? "Merzo Windows Optimizer — Gaming Build" : "Merzo Windows Optimizer — применение профиля",
            MessageBoxButton.YesNo,
            (balancedCount > 0 || profileIncludesTelemetry || gamingExtreme || gamingLab) ? MessageBoxImage.Warning : MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes) return;

        SelectedOptimizationTabIndex = 4;
        DeepScanSteps.Clear();
        DeepScanProgress = 0;
        DeepScanStatusText = $"Применение профиля: 0/{total}";
        DeepScanSteps.Add($"План запущен · всего шагов {total} · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"}");
        IsStage2Busy = true;
        var appliedSnapshotIds = new List<Guid>();
        var done = 0;
        var gamingExtremeTouched = false;
        try
        {
            foreach (var card in selected)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: {card.Name}…";
                DeepScanStatusText = $"Registry/Policy {done + 1}/{total}: {card.Name}";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
                DeepScanSteps.Add($"→ {done + 1}/{total} · {card.Name}");
                var result = await _dispatcher.RunAsync($"Cumulative tweak {card.Id}", token => _tweakService.ApplyAsync(card.Definition, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{card.Name}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                var snapshotLabel = result.SnapshotId is Guid snapshotGuid ? $" · snapshot {snapshotGuid.ToString("N")[..8]}" : string.Empty;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · {card.Name}{snapshotLabel}" : $"✓ {done}/{total} · {card.Name} · уже настроено";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            foreach (var item in services)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение службы {item.DisplayName}…";
                DeepScanStatusText = $"Background service {done + 1}/{total}: {item.DisplayName}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · служба {item.DisplayName}");
                var result = await _dispatcher.RunAsync($"Profile service {item.ServiceName}", token => _serviceAudit.DisableAsync(item.ServiceName, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.DisplayName}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · служба {item.DisplayName} отключена" : $"✓ {done}/{total} · служба {item.DisplayName} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            foreach (var item in tasks)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение фоновой задачи {item.Name}…";
                DeepScanStatusText = $"Scheduled task {done + 1}/{total}: {item.Name}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · задача {item.FullPath}");
                var result = await _dispatcher.RunAsync($"Profile task {item.FullPath}", token => _taskAudit.DisableAsync(item.Path, item.Name, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.FullPath}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · задача {item.Name} отключена" : $"✓ {done}/{total} · задача {item.Name} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            if (gamingNetworkMode is not null)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: Gaming Network {gamingNetworkMode}…";
                DeepScanStatusText = $"Gaming Network {done + 1}/{total}: {gamingNetworkMode}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · Gaming Network {gamingNetworkMode}");
                if (gamingNetworkMode == "EXTREME") gamingExtremeTouched = true;
                var result = gamingNetworkMode == "EXTREME"
                    ? await _dispatcher.RunAsync("Gaming Build Network EXTREME", token => _networkRepairService.ApplyGamingNetworkExtremeAsync(token), _lifetimeCts.Token)
                    : await _dispatcher.RunAsync("Gaming Build Network SAFE", token => _networkRepairService.ApplyGamingNetworkSafeAsync(token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException(result.Message);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = $"✓ {done}/{total} · Gaming Network {gamingNetworkMode}";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            Stage2StatusText = gamingBuild
                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}."
                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";
            DeepScanStatusText = $"План завершён: {done}/{total} · Snapshot {appliedSnapshotIds.Count}";
            DeepScanProgress = 100;
            DeepScanSteps.Add($"✓ Профиль завершён · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"} · Snapshot {appliedSnapshotIds.Count}");
            foreach (var card in selected) card.IsSelected = false;
            _selectedProfileTag = null;
            RefreshSelectedTweaks();
            global::MerzoOptimizer.App.MerzoDialog.Show(Stage2StatusText + "\n\nПодробный ход операции сохранён на вкладке «Ход работы». Для отключённых служб рекомендуется перезагрузка Windows.", "Merzo Windows Optimizer — профиль применён", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            if (gamingExtremeTouched)
            {
                try { await _dispatcher.RunAsync("Rollback Gaming Network", token => _networkRepairService.RestoreGamingNetworkAsync(token), CancellationToken.None); } catch { }
            }
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback canceled snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Пакет остановлен · восстановление выполнено";
            Stage2StatusText = appliedSnapshotIds.Count > 0 ? "Пакет остановлен; изменения этого запуска восстановлены." : "Пакет остановлен.";
        }
        catch (Exception ex)
        {
            DeepScanStatusText = "Ошибка · выполняется восстановление…";
            if (gamingExtremeTouched)
            {
                try { await _dispatcher.RunAsync("Rollback Gaming Network", token => _networkRepairService.RestoreGamingNetworkAsync(token), CancellationToken.None); } catch { }
            }
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Аварийное восстановление завершено";
            Stage2StatusText = $"Пакет отменён и восстановлен: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(Stage2StatusText, "Merzo Windows Optimizer — восстановление", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsStage2Busy = false;
            if (!_lifetimeCts.IsCancellationRequested)
            {
                await RefreshStage2StateAsync();
                await RefreshServicesTasksAsync();
            }
        }
    }

    private void CleanupCategoryOnPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(CleanupCategoryViewModel.IsSelected)) return;
        UpdateCleanupSelectionText();
        CleanSelectedCommand.RaiseCanExecuteChanged();
    }

    private void UpdateCleanupSelectionText()
    {
        var selected = CleanupCategories.Where(static x => x.IsSelected && x.CanClean).ToArray();
        var bytes = selected.Sum(static x => x.EligibleBytes);
        CleanupSelectionText = selected.Length == 0
            ? "Ничего не выбрано"
            : $"Выбрано: {selected.Length} · {CleanupCategoryViewModel.FormatBytes(bytes)}";
    }

    private Task SelectAllCleanupAsync()
    {
        foreach (var row in CleanupCategories) row.IsSelected = row.CanClean;
        UpdateCleanupSelectionText();
        CleanSelectedCommand.RaiseCanExecuteChanged();
        return Task.CompletedTask;
    }

    private Task ClearCleanupSelectionAsync()
    {
        foreach (var row in CleanupCategories) row.IsSelected = false;
        UpdateCleanupSelectionText();
        CleanSelectedCommand.RaiseCanExecuteChanged();
        return Task.CompletedTask;
    }

    private async Task CleanSelectedAsync()
    {
        var categories = CleanupCategories.Where(static c => c.IsSelected && c.CanClean).ToArray();
        await CleanCategoryPackAsync(categories, "Очистить выбранные категории?");
    }

    private async Task CleanCategoryPackAsync(IReadOnlyList<CleanupCategoryViewModel> categories, string title)
    {
        if (categories.Count == 0) return;
        var bytes=categories.Sum(static c=>c.EligibleBytes); var files=categories.Sum(static c=>c.Snapshot.EligibleFileCount);
        var choice=global::MerzoOptimizer.App.MerzoDialog.Show($"{title}\n\nКатегорий: {categories.Count}\nФайлов: {files}\nОбъём: {FormatBytes(bytes)}\n\nДА — ZIP-backup + Snapshot для каждой категории.\nНЕТ — очистка без backup, Undo файлов будет недоступен.\nОТМЕНА — ничего не делать.","Merzo — пакетная очистка",MessageBoxButton.YesNoCancel,MessageBoxImage.Question);
        if(choice==MessageBoxResult.Cancel)return; var createBackup=choice==MessageBoxResult.Yes;
        if(!createBackup && global::MerzoOptimizer.App.MerzoDialog.Show("Пакет будет очищен БЕЗ резервных копий. Вернуть удалённые файлы через Undo нельзя. Продолжить?","Необратимая очистка",MessageBoxButton.YesNo,MessageBoxImage.Warning)!=MessageBoxResult.Yes)return;
        if(!TryBeginOperation("cleanup-run",out var lease))return;
        using(lease)
        {
            _cleanupOperationCts?.Dispose(); _cleanupOperationCts=CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token); IsCleanupOperationRunning=true;
            BeginCleanupVisual("Пакетная очистка",categories.Count,files,bytes); CleanupOperationSteps.Add($"→ Режим: {(createBackup?"с backup + Undo":"без backup · необратимо")}");
            var snapshots=new List<Guid>(); long freed=0; int cleaned=0;
            try
            {
                for(var i=0;i<categories.Count;i++)
                {
                    _cleanupOperationCts.Token.ThrowIfCancellationRequested(); var category=categories[i];
                    IsCleanupIndeterminate=true; SetCleanupVisual(i*95.0/categories.Count,$"Категория {i+1} из {categories.Count}",$"{category.Name}\n{category.RootPath}",$"Удалено: {cleaned} · освобождено {FormatBytes(freed)}");
                    CleanupOperationSteps.Add($"→ {i+1}/{categories.Count} · {category.Name}");
                    var result=await _dispatcher.RunAsync($"Cleanup pack {category.Id}",token=>_cleanupService.CleanAsync(category.Id,createBackup,token),_cleanupOperationCts.Token);
                    if(!result.Success)throw new InvalidOperationException(result.Message);
                    if(result.Changed){freed+=result.NetFreedBytes;cleaned+=result.ArchivedFileCount;if(result.SnapshotId is Guid id)snapshots.Add(id);CleanupOperationSteps.Add($"✓ {category.Name} · {result.ArchivedFileCount} файлов · {FormatBytes(result.NetFreedBytes)}");}
                }
                IsCleanupIndeterminate=false; SetCleanupVisual(100,"Готово",$"Обработано категорий: {categories.Count}",createBackup?$"Snapshot: {snapshots.Count} · освобождено {FormatBytes(freed)}":$"Без backup · освобождено {FormatBytes(freed)}");
                CleanupStatusText=$"Очистка завершена · удалено {cleaned} файлов · освобождено {FormatBytes(freed)}.";
            }
            catch(OperationCanceledException)
            {
                IsCleanupIndeterminate=false; CleanupStatusText="Пакетная очистка остановлена пользователем."; CleanupOperationSteps.Add("■ Операция отменена."); SetCleanupVisual(CleanupProgress,"Остановлено",CleanupStatusText,createBackup?"Уже созданные Snapshot сохранены.":"Режим без backup: уже удалённые файлы восстановить нельзя.");
            }
            catch(Exception ex){IsCleanupIndeterminate=false;CleanupStatusText=$"Очистка остановлена: {ex.Message}";CleanupOperationSteps.Add($"✕ {ex.Message}");SetCleanupVisual(CleanupProgress,"Ошибка",ex.Message);}
            finally{IsCleanupOperationRunning=false;_cleanupOperationCts?.Dispose();_cleanupOperationCts=null;if(createBackup&&!_lifetimeCts.IsCancellationRequested)await RefreshSnapshotsAsync();_ = RefreshCleanupAsync();}
        }
    }

    private async Task CleanAllSafeAsync()
    {
        var categories = CleanupCategories.Where(static c => c.CanClean).ToArray();
        await CleanCategoryPackAsync(categories, "Очистить все доступные SAFE-категории?");
    }

    private async Task RefreshPrivacyAsync()
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
        var answer = global::MerzoOptimizer.App.MerzoDialog.Show(
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
            global::MerzoOptimizer.App.MerzoDialog.Show(PrivacyStatusText + "\n\nРекомендуется перезагрузка, чтобы отключённые службы гарантированно не стартовали снова.", "Privacy & Telemetry", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            foreach (var id in snapshots.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Privacy rollback {id:N}", token => _restoreService.RestoreAsync(id, token), CancellationToken.None);
            PrivacyStatusText = $"Privacy-пакет откатан: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(PrivacyStatusText, "Privacy & Telemetry — rollback", MessageBoxButton.OK, MessageBoxImage.Warning);
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

    private async Task RefreshServicesTasksAsync()
    {
        if (_disposed) return;
        ServicesTasksStatusText = "Сканирую службы и Scheduled Tasks…";
        var serviceError = string.Empty;
        var taskError = string.Empty;
        try
        {
            ServiceAuditItems.Clear();
            ScheduledTaskAuditItems.Clear();
            var activeSnapshots = (await _snapshotService.ListAsync((_deepScanStageCts?.Token ?? _lifetimeCts.Token))).Where(static x => !x.IsRestored).ToArray();

            try
            {
                var services = await _dispatcher.RunAsync("Services audit", token => _serviceAudit.ScanAsync(token), (_deepScanStageCts?.Token ?? _lifetimeCts.Token));
                foreach (var item in services)
                {
                    var hasRestore = activeSnapshots.Any(s => string.Equals(s.TweakId, $"service.{item.ServiceName}", StringComparison.OrdinalIgnoreCase));
                    ServiceAuditItems.Add(new ServiceItemViewModel(item, hasRestore, DisableServiceAsync, RestoreServiceAsync));
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException) { serviceError = ex.Message; }

            try
            {
                var tasks = await _dispatcher.RunAsync("Scheduled Tasks audit", token => _taskAudit.ScanAsync(token), (_deepScanStageCts?.Token ?? _lifetimeCts.Token));
                foreach (var item in tasks)
                {
                    var id = TaskOperationId(item.Path, item.Name);
                    var hasRestore = activeSnapshots.Any(s => string.Equals(s.TweakId, id, StringComparison.OrdinalIgnoreCase));
                    ScheduledTaskAuditItems.Add(new ScheduledTaskItemViewModel(item, hasRestore, DisableScheduledTaskAsync, RestoreScheduledTaskAsync));
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException) { taskError = ex.Message; }

            var errors = string.IsNullOrWhiteSpace(serviceError) && string.IsNullOrWhiteSpace(taskError)
                ? "Disable/Restore доступны только для правил SAFE/BALANCED; KEEP остаётся заблокирован."
                : $"Частичные ошибки: службы={serviceError}; задачи={taskError}";
            ServicesTasksStatusText = $"Службы: {ServiceAuditItems.Count} · задачи: {ScheduledTaskAuditItems.Count}. {errors}";
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
    }

    private async Task DisableServiceAsync(ServiceItemViewModel row)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Отключить запуск службы?\n\n{row.DisplayName}\n{row.ServiceName}\nRisk: {row.Risk}\n\n{row.Recommendation}\n\n" +
            "Merzo сохранит исходный Start value в snapshot. Текущая служба не будет принудительно завершена — меняется только тип следующего запуска.",
            "Merzo Windows Optimizer — Service Optimizer",
            MessageBoxButton.YesNo,
            row.Risk == "SAFE" ? MessageBoxImage.Question : MessageBoxImage.Warning);
        if (confirmation != MessageBoxResult.Yes) return;

        row.SetBusy(true); IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync($"Disable service {row.ServiceName}", token => _serviceAudit.DisableAsync(row.ServiceName, token), _lifetimeCts.Token);
            ServicesTasksStatusText = result.Message;
            if (!result.Success) global::MerzoOptimizer.App.MerzoDialog.Show(result.Message, "Service Optimizer", MessageBoxButton.OK, MessageBoxImage.Warning);
            await RefreshSnapshotsAsync();
        }
        finally { row.SetBusy(false); IsStage2Busy = false; }
        await RefreshServicesTasksAsync();
    }

    private async Task RestoreServiceAsync(ServiceItemViewModel row)
    {
        if (global::MerzoOptimizer.App.MerzoDialog.Show($"Вернуть тип запуска службы из snapshot?\n\n{row.DisplayName}", "Restore service", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        row.SetBusy(true); IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync($"Restore service {row.ServiceName}", token => _serviceAudit.RestoreAsync(row.ServiceName, token), _lifetimeCts.Token);
            ServicesTasksStatusText = result.Message;
            await RefreshSnapshotsAsync();
        }
        finally { row.SetBusy(false); IsStage2Busy = false; }
        await RefreshServicesTasksAsync();
    }

    private async Task DisableScheduledTaskAsync(ScheduledTaskItemViewModel row)
    {
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Отключить Scheduled Task?\n\n{row.Path}{row.Name}\nRisk: {row.Risk}\n\n{row.Recommendation}\n\nПеред изменением создаётся snapshot.",
            "Merzo Windows Optimizer — Scheduled Tasks",
            MessageBoxButton.YesNo,
            row.Risk == "SAFE" ? MessageBoxImage.Question : MessageBoxImage.Warning);
        if (confirmation != MessageBoxResult.Yes) return;
        row.SetBusy(true); IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync($"Disable task {row.Name}", token => _taskAudit.DisableAsync(row.Path, row.Name, token), _lifetimeCts.Token);
            ServicesTasksStatusText = result.Message;
            if (!result.Success) global::MerzoOptimizer.App.MerzoDialog.Show(result.Message, "Scheduled Tasks", MessageBoxButton.OK, MessageBoxImage.Warning);
            await RefreshSnapshotsAsync();
        }
        finally { row.SetBusy(false); IsStage2Busy = false; }
        await RefreshServicesTasksAsync();
    }

    private async Task RestoreScheduledTaskAsync(ScheduledTaskItemViewModel row)
    {
        if (global::MerzoOptimizer.App.MerzoDialog.Show($"Вернуть состояние Scheduled Task из snapshot?\n\n{row.Path}{row.Name}", "Restore Scheduled Task", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        row.SetBusy(true); IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync($"Restore task {row.Name}", token => _taskAudit.RestoreAsync(row.Path, row.Name, token), _lifetimeCts.Token);
            ServicesTasksStatusText = result.Message;
            await RefreshSnapshotsAsync();
        }
        finally { row.SetBusy(false); IsStage2Busy = false; }
        await RefreshServicesTasksAsync();
    }

    private static string TaskOperationId(string path, string name)
    {
        static string Normalize(string value) => new(value.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());
        return $"task.{Normalize(path)}.{Normalize(name)}";
    }

    private async Task DiagnoseNetworkAsync()
    {
        if (IsNetworkBusy) return;
        IsNetworkBusy = true;
        NetworkProgress = 12;
        NetworkStatusText = "Проверяю активный адаптер, IP, шлюз и DNS…";
        try
        {
            var snapshot = await _dispatcher.RunAsync("Network diagnostics", token => _networkRepairService.DiagnoseAsync(token), _lifetimeCts.Token);
            ApplyNetworkSnapshot(snapshot);
            NetworkProgress = 100;
            NetworkOperationSteps.Clear();
            NetworkOperationSteps.Add($"✓ Адаптер: {snapshot.AdapterName} · {snapshot.Status} · {snapshot.LinkSpeed}");
            NetworkOperationSteps.Add($"✓ IPv4: {snapshot.IPv4} · шлюз: {snapshot.Gateway}");
            NetworkOperationSteps.Add($"{(snapshot.GatewayTest.StartsWith("OK", StringComparison.OrdinalIgnoreCase) ? "✓" : "!")} Шлюз: {snapshot.GatewayTest}");
            NetworkOperationSteps.Add($"{(snapshot.DnsTest.StartsWith("OK", StringComparison.OrdinalIgnoreCase) ? "✓" : "!")} DNS: {snapshot.DnsTest}");
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkStatusText = $"Ошибка диагностики: {ex.Message}";
            NetworkOperationText = "Диагностика не изменила настройки Windows.";
        }
        finally { IsNetworkBusy = false; }
    }

    private void ApplyNetworkSnapshot(NetworkDiagnosticSnapshot snapshot)
    {
        NetworkStatusText = snapshot.Summary;
        NetworkAdapterText = $"{snapshot.AdapterName} · {snapshot.AdapterDescription}";
        NetworkIpText = snapshot.IPv4;
        NetworkGatewayText = snapshot.Gateway;
        NetworkDnsText = snapshot.DnsServers;
        NetworkDhcpText = snapshot.Dhcp;
        NetworkSpeedText = snapshot.LinkSpeed;
        NetworkGatewayTestText = snapshot.GatewayTest;
        NetworkDnsTestText = snapshot.DnsTest;
        NetworkOperationText = $"Диагностика завершена {snapshot.CapturedAt:HH:mm:ss}. Проверка только читает состояние сети.";
    }

    private async Task RunNetworkActionAsync(string title, string warning, Func<CancellationToken, Task<NetworkRepairResult>> action, bool confirm)
    {
        if (IsNetworkBusy) return;
        if (confirm)
        {
            var answer = global::MerzoOptimizer.App.MerzoDialog.Show(warning, $"Merzo — {title}", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (answer != MessageBoxResult.Yes) return;
        }
        IsNetworkBusy = true; NetworkProgress = 10; NetworkOperationSteps.Clear();
        NetworkStatusText = $"{title}: выполняется…"; NetworkOperationText = warning;
        NetworkOperationSteps.Add($"▶ {title}: передано защищённому UAC-helper");
        try
        {
            var result = await _dispatcher.RunAsync($"Network repair: {title}", action, _lifetimeCts.Token);
            NetworkProgress = 100;
            NetworkOperationSteps[0] = $"{(result.Success ? "✓" : "!")} {title}: {result.Message}";
            NetworkStatusText = result.Success ? $"{title}: готово" : $"{title}: Windows сообщила об ошибке";
            NetworkOperationText = result.Message;
            global::MerzoOptimizer.App.MerzoDialog.Show(result.Message + (result.RebootRequired ? "\n\nРекомендуется перезагрузить Windows." : string.Empty), $"Merzo — {title}", MessageBoxButton.OK, result.Success ? MessageBoxImage.Information : MessageBoxImage.Warning);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkProgress = 0; NetworkStatusText = $"{title}: ошибка"; NetworkOperationText = ex.Message;
            NetworkOperationSteps.Add($"! {ex.Message}");
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.Message, $"Merzo — {title}", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally { IsNetworkBusy = false; }
    }

    private async Task RepairNetworkAsync()
    {
        if (IsNetworkBusy) return;
        var answer = global::MerzoOptimizer.App.MerzoDialog.Show(
            "Merzo выполнит безопасную последовательность встроенных команд Windows:\n\n1. Очистка DNS\n2. Обновление DHCP\n3. Сброс Winsock\n4. Сброс TCP/IP\n\nWi‑Fi профили, пароли, VPN-профили и IPv6 не удаляются. После Winsock/TCP-IP рекомендуется перезагрузка. Продолжить?",
            "Merzo — восстановление сети Windows", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (answer != MessageBoxResult.Yes) return;

        IsNetworkBusy = true; NetworkProgress = 0; NetworkOperationSteps.Clear();
        NetworkStatusText = "Восстанавливаю сетевой стек Windows…";
        var actions = new (string Name, Func<CancellationToken, Task<NetworkRepairResult>> Run)[]
        {
            ("Очистка DNS", _networkRepairService.FlushDnsAsync),
            ("Обновление DHCP", _networkRepairService.RenewDhcpAsync),
            ("Сброс Winsock", _networkRepairService.ResetWinsockAsync),
            ("Сброс TCP/IP", _networkRepairService.ResetTcpIpAsync)
        };
        foreach (var a in actions) NetworkOperationSteps.Add($"○ {a.Name}");
        var success = 0; var reboot = false;
        try
        {
            for (var i = 0; i < actions.Length; i++)
            {
                NetworkOperationSteps[i] = $"▶ {actions[i].Name}…";
                NetworkOperationText = $"Шаг {i + 1}/{actions.Length}: {actions[i].Name}";
                var r = await _dispatcher.RunAsync($"Network repair {i + 1}: {actions[i].Name}", actions[i].Run, _lifetimeCts.Token);
                if (r.Success) success++;
                reboot |= r.RebootRequired;
                NetworkOperationSteps[i] = $"{(r.Success ? "✓" : "!")} {actions[i].Name} · {r.Message}";
                NetworkProgress = (i + 1) * 100d / actions.Length;
            }
            NetworkStatusText = $"Восстановление сети завершено: {success}/{actions.Length} шагов успешно";
            NetworkOperationText = reboot ? "Операция завершена. Рекомендуется перезагрузка Windows." : "Операция завершена.";
            global::MerzoOptimizer.App.MerzoDialog.Show($"Восстановление сети завершено: {success}/{actions.Length} шагов.\n\nWi‑Fi/VPN профили не удалялись.{(reboot ? "\nРекомендуется перезагрузка Windows." : string.Empty)}", "Merzo — сеть восстановлена", MessageBoxButton.OK, success == actions.Length ? MessageBoxImage.Information : MessageBoxImage.Warning);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested) { }
        catch (Exception ex)
        {
            NetworkStatusText = "Восстановление сети остановлено ошибкой"; NetworkOperationText = ex.Message;
            NetworkOperationSteps.Add($"! {ex.Message}");
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.Message, "Merzo — ошибка восстановления сети", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally { IsNetworkBusy = false; }
    }

    private async Task RefreshPowerAsync()
    {
        if (_disposed || _isPowerRefreshing) return;
        _isPowerRefreshing = true;
        try
        {
            var schemes = await _dispatcher.RunAsync("Power schemes", token => _powerProfiles.ListSchemesAsync(token), (_deepScanStageCts?.Token ?? _lifetimeCts.Token));
            PowerSchemes.Clear();
            foreach (var scheme in schemes) PowerSchemes.Add(scheme);
            var active = schemes.FirstOrDefault(static x => x.IsActive);
            ActivePowerSchemeName = active?.Name ?? "Не определён";
            PowerSchemeCountText = $"Найдено схем: {schemes.Count}";
            IsBalancedPowerActive = active?.Guid.Equals("381b4222-f694-41f0-9685-ff5bb260df2e", StringComparison.OrdinalIgnoreCase) == true;
            IsPerformancePowerActive = active?.Guid.Equals("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", StringComparison.OrdinalIgnoreCase) == true;
            PowerStatusText = active is null ? "Активный план питания не определён" : $"Сейчас используется: {active.Name}";
            PowerLiveText = $"LIVE · Windows Power API · обновлено {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            ActivePowerSchemeName = "Ошибка чтения";
            PowerSchemeCountText = "Схемы недоступны";
            IsBalancedPowerActive = false;
            IsPerformancePowerActive = false;
            PowerStatusText = $"Power: {ex.Message}";
            PowerLiveText = "Live-монитор: ошибка чтения";
        }
        finally { _isPowerRefreshing = false; }
    }

    private async void PowerRefreshTimerOnTick(object? sender, EventArgs e)
    {
        if (_disposed || IsStage2Busy) return;
        await RefreshPowerAsync();
    }

    private async Task ActivatePowerAsync(string alias, string displayName)
    {
        if (global::MerzoOptimizer.App.MerzoDialog.Show($"Переключить Windows на профиль «{displayName}»?\n\nТекущий план будет сохранён в snapshot и доступен через Undo.", "Профиль питания", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync($"Power {displayName}", token => _powerProfiles.ActivateAsync(alias, displayName, token), _lifetimeCts.Token);
            PowerStatusText = result.Message;
            PowerLiveText = $"Изменено через Merzo · {DateTime.Now:HH:mm:ss}";
            await RefreshSnapshotsAsync();
            await RefreshPowerAsync();
        }
        finally { IsStage2Busy = false; }
    }

    private async Task RestorePowerAsync()
    {
        IsStage2Busy = true;
        try
        {
            var result = await _dispatcher.RunAsync("Restore power profile", token => _powerProfiles.RestoreLastAsync(token), _lifetimeCts.Token);
            PowerStatusText = result.Message;
            await RefreshSnapshotsAsync();
            await RefreshPowerAsync();
        }
        finally { IsStage2Busy = false; }
    }

    private void LoadLocalReleaseNotes()
    {
        try
        {
            var local = global::MerzoOptimizer.App.ReleaseNotesWindow.LoadCurrentRelease();
            UpdateReleaseTitleText = local.Title;
            UpdateReleaseNotesText = local.FormattedNotes;
        }
        catch
        {
            UpdateReleaseTitleText = "Что нового в текущей версии";
            UpdateReleaseNotesText = "Список изменений будет загружен при проверке обновлений.";
        }
    }

    private Task CheckUpdatesAsync() => CheckUpdatesAsync(silent: false);

    private async Task CheckUpdatesAsync(bool silent)
    {
        if (_disposed || IsUpdateBusy) return;
        IsUpdateBusy = true;
        try
        {
            UpdateStatusText = "Проверяю GitHub Releases…";
            _lastUpdateCheck = await _dispatcher.RunAsync("Update check", token => _updateService.CheckAsync(token), _lifetimeCts.Token);
            UpdateStatusText = _lastUpdateCheck.Message;
            UpdateLatestText = _lastUpdateCheck.UpdateAvailable ? _lastUpdateCheck.LatestVersion : (_lastUpdateCheck.Configured ? "Актуально" : "Feed не настроен");
            if (_lastUpdateCheck.Success)
            {
                UpdateReleaseTitleText = string.IsNullOrWhiteSpace(_lastUpdateCheck.ReleaseName) ? $"Версия {_lastUpdateCheck.LatestVersion}" : _lastUpdateCheck.ReleaseName;
                if (!string.IsNullOrWhiteSpace(_lastUpdateCheck.Notes)) UpdateReleaseNotesText = _lastUpdateCheck.Notes;
            }
            DownloadUpdateCommand.RaiseCanExecuteChanged();
            if (silent && _lastUpdateCheck is { Success: true, UpdateAvailable: true } startupUpdate && !string.Equals(_lastNotifiedUpdateVersion, startupUpdate.LatestVersion, StringComparison.OrdinalIgnoreCase))
            {
                _lastNotifiedUpdateVersion = startupUpdate.LatestVersion;
                StartupUpdateNoticeText = $"Доступна версия {startupUpdate.LatestVersion}";
                StartupUpdateNoticeDetailText = string.IsNullOrWhiteSpace(startupUpdate.ReleaseName)
                    ? "Откройте Update Center, чтобы посмотреть изменения и установить обновление."
                    : startupUpdate.ReleaseName;
                IsStartupUpdateNoticeVisible = true;
            }
            if (!silent && _lastUpdateCheck is { Success: true, UpdateAvailable: true } available)
                global::MerzoOptimizer.App.MerzoDialog.Show($"Доступно обновление {available.LatestVersion}.\n\n{available.ReleaseName}\n\nНажмите «Скачать и установить». Merzo скачает installer, проверит SHA-256 и только потом предложит установку.", "Merzo Windows Optimizer — обновление найдено", MessageBoxButton.OK, MessageBoxImage.Information);
            else if (!silent && !_lastUpdateCheck.Success)
                global::MerzoOptimizer.App.MerzoDialog.Show(_lastUpdateCheck.Message, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            UpdateStatusText = $"Ошибка проверки обновлений: {ex.Message}";
            if (!silent) global::MerzoOptimizer.App.MerzoDialog.Show(UpdateStatusText, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally { IsUpdateBusy = false; }
    }

    private Task InstallUpdateAsync() => DownloadUpdateAsync();

    private Task CancelUpdateAsync()
    {
        _updateOperationCts?.Cancel();
        UpdatePhaseText = "Отмена…";
        UpdateStatusText = "Отменяю загрузку обновления…";
        return Task.CompletedTask;
    }

    private async Task DownloadUpdateAsync()
    {
        if (_disposed || IsUpdateBusy || _lastUpdateCheck is not { UpdateAvailable: true, Success: true } update) return;
        IsUpdateBusy = true;
        _updateOperationCts?.Cancel();
        _updateOperationCts?.Dispose();
        _updateOperationCts = CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token);
        IsUpdateProgressVisible = true;
        IsUpdateProgressIndeterminate = true;
        UpdateProgress = 0;
        UpdatePhaseText = "Подготовка";
        UpdateTransferText = update.AssetSize > 0 ? $"0 Б / {FormatBytes(update.AssetSize)}" : "Определяю размер…";
        UpdateSpeedText = "—";
        try
        {
            UpdateStatusText = $"Подготавливаю загрузку {update.LatestVersion}…";
            var progress = new Progress<UpdateProgressInfo>(ApplyUpdateProgress);
            var result = await _dispatcher.RunAsync("Update download", async token =>
            {
                using var linked = CancellationTokenSource.CreateLinkedTokenSource(token, _updateOperationCts.Token);
                return await _updateService.DownloadAsync(update, progress, linked.Token);
            }, _updateOperationCts.Token);
            _downloadedUpdate = result;
            InstallUpdateCommand.RaiseCanExecuteChanged();
            UpdateStatusText = result.Message;
            if (!result.Success)
            {
                UpdatePhaseText = "Ошибка";
                global::MerzoOptimizer.App.MerzoDialog.Show(result.Message, "Merzo Windows Optimizer — обновление", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            UpdateProgress = 100;
            IsUpdateProgressIndeterminate = false;
            UpdatePhaseText = "Готово к установке";
            UpdateSpeedText = "SHA-256 ✓";
            if (!IsInstalledLayout())
            {
                global::MerzoOptimizer.App.MerzoDialog.Show($"Обновление проверено и сохранено:\n{result.FilePath}\n\nЭта копия запущена как Portable/DEV. Автоматическая установка доступна только установленной версии.", "Обновление проверено", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }
            var answer = global::MerzoOptimizer.App.MerzoDialog.Show($"Загрузка завершена. SHA-256 подтверждён.\n\nУстановить {update.LatestVersion} сейчас?\n\nПосле UAC Merzo закроется, обновится и покажет экран запуска до полной загрузки новой версии.", "Merzo Windows Optimizer — готово к установке", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (answer != MessageBoxResult.Yes) return;
            UpdatePhaseText = "Запуск установки";
            UpdateStatusText = $"Запускаю установку {update.LatestVersion}…";
            WritePendingUpdateMarker(update.LatestVersion);
            LaunchVerifiedInstallerAndRestart(result.FilePath);
        }
        catch (OperationCanceledException)
        {
            UpdatePhaseText = "Отменено";
            UpdateStatusText = "Загрузка обновления отменена пользователем.";
            IsUpdateProgressIndeterminate = false;
        }
        catch (Exception ex)
        {
            UpdatePhaseText = "Ошибка";
            UpdateStatusText = $"Не удалось установить обновление: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(UpdateStatusText, "Merzo Windows Optimizer — обновление", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            _updateOperationCts?.Dispose();
            _updateOperationCts = null;
            if (Application.Current?.Dispatcher?.HasShutdownStarted != true) IsUpdateBusy = false;
        }
    }

    private void ApplyUpdateProgress(UpdateProgressInfo info)
    {
        IsUpdateProgressVisible = true;
        IsUpdateProgressIndeterminate = info.IsIndeterminate;
        if (!info.IsIndeterminate || info.Percent > 0) UpdateProgress = info.Percent;
        UpdatePhaseText = info.Phase switch
        {
            "prepare" => "Подготовка",
            "checksum" => "Контрольная сумма",
            "download" => "Скачивание",
            "verify" => "Проверка SHA-256",
            "finalize" => "Подготовка установки",
            "ready" => "Готово",
            "cancelled" => "Отменено",
            "error" => "Ошибка",
            _ => info.Phase
        };
        if (!string.IsNullOrWhiteSpace(info.Message)) UpdateStatusText = info.Message;
        if (info.TotalBytes > 0)
            UpdateTransferText = $"{FormatBytes(info.BytesReceived)} / {FormatBytes(info.TotalBytes)}";
        else if (info.BytesReceived > 0)
            UpdateTransferText = FormatBytes(info.BytesReceived);
        UpdateSpeedText = info.BytesPerSecond > 0 ? $"{FormatBytes((long)info.BytesPerSecond)}/с" : info.Phase == "verify" ? "Проверяю файл…" : UpdateSpeedText;
    }

    private static void WritePendingUpdateMarker(string version)
    {
        try
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "updates");
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "pending-startup-update.txt"), version);
        }
        catch { }
    }

    private static bool IsInstalledLayout()
    {
        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        if (string.IsNullOrWhiteSpace(programFiles)) return false;
        programFiles = Path.GetFullPath(programFiles).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return baseDir.StartsWith(programFiles + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }

    private static void LaunchVerifiedInstallerAndRestart(string installerPath)
    {
        if (string.IsNullOrWhiteSpace(installerPath) || !File.Exists(installerPath)) throw new FileNotFoundException("Проверенный installer не найден.", installerPath);
        var currentExe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "MerzoWindowsOptimizer.exe");
        var installer = Process.Start(new ProcessStartInfo
        {
            FileName = installerPath,
            Arguments = "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-",
            UseShellExecute = true,
            Verb = "runas"
        }) ?? throw new InvalidOperationException("Windows не запустила installer.");
        var restartScript = Path.Combine(Path.GetTempPath(), $"MerzoWindowsOptimizer_UpdateRestart_{Guid.NewGuid():N}.ps1");
        var escapedExe = currentExe.Replace("'", "''");
        var script = $"$ErrorActionPreference='SilentlyContinue'`r`nWait-Process -Id {installer.Id}`r`nStart-Sleep -Milliseconds 1500`r`nfor($i=0;$i -lt 12;$i++) {{ if(Get-Process -Name 'MerzoWindowsOptimizer' -ErrorAction SilentlyContinue) {{ break }}; if(Test-Path -LiteralPath '{escapedExe}') {{ Start-Process -FilePath '{escapedExe}'; Start-Sleep -Milliseconds 700; if(Get-Process -Name 'MerzoWindowsOptimizer' -ErrorAction SilentlyContinue) {{ break }} }}; Start-Sleep -Seconds 1 }}`r`nRemove-Item -LiteralPath $PSCommandPath -Force`r`n";
        File.WriteAllText(restartScript, script);
        Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"{restartScript}\"",
            UseShellExecute = false,
            CreateNoWindow = true
        });
        Application.Current.Shutdown();
    }

    private async Task RunRecoveryTestAsync()
    {
        IsStage2Busy = true;
        RecoveryTestStatusText = "Проверка Undo: выполняется…";
        Stage2StatusText = "Проверяю реальный Snapshot → Apply → Restore в безопасном HKCU sandbox…";

        try
        {
            var result = await _dispatcher.RunAsync(
                "Safe recovery self-test",
                token => _recoveryDiagnosticService.RunAsync(token),
                _lifetimeCts.Token);

            RecoveryTestStatusText = result.Success
                ? "Проверка Undo: PASS · исходное состояние восстановлено"
                : $"Проверка Undo: {result.Message}";
            Stage2StatusText = result.Message;

            global::MerzoOptimizer.App.MerzoDialog.Show(
                result.Details is null ? result.Message : $"{result.Message}\n\n{result.Details}",
                "Merzo Windows Optimizer — проверка восстановления",
                MessageBoxButton.OK,
                result.Success ? MessageBoxImage.Information : MessageBoxImage.Warning);

            await RefreshStage2StateAsync();
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            RecoveryTestStatusText = "Проверка Undo: остановлена при закрытии";
        }
        catch (Exception ex)
        {
            RecoveryTestStatusText = $"Проверка Undo: FAIL · {ex.Message}";
            Stage2StatusText = RecoveryTestStatusText;
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Recovery test error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsStage2Busy = false;
        }
    }

    private async Task RunAuditAsync()
    {
        IsBusy = true;
        StatusText = "Сканирование Windows…";

        try
        {
            var snapshot = await _dispatcher.RunAsync(
                "System Audit",
                token => _auditService.RunAsync(token),
                (_deepScanStageCts?.Token ?? _lifetimeCts.Token));

            var previousPerformanceSnapshot = _persistedAudit?.Snapshot;
            ApplySnapshot(snapshot);
            if (previousPerformanceSnapshot is not null)
            {
                var processDelta = snapshot.ProcessCount - previousPerformanceSnapshot.ProcessCount;
                var ramDelta = snapshot.Memory.UsedBytes / 1024d / 1024d - previousPerformanceSnapshot.Memory.UsedBytes / 1024d / 1024d;
                PerformanceDeltaText = $"С прошлого аудита: процессы {previousPerformanceSnapshot.ProcessCount} → {snapshot.ProcessCount} ({processDelta:+#;-#;0}); RAM {previousPerformanceSnapshot.Memory.UsedPercent:F1}% → {snapshot.Memory.UsedPercent:F1}% ({ramDelta:+0;-0;0} МБ).";
            }
            else
            {
                PerformanceDeltaText = "Создан performance baseline. После следующего аудита Merzo покажет разницу по процессам и RAM.";
            }
            var catalog = AuditStateStore.CaptureCurrent(SafeTweaks.Select(static x => x.Id));
            await _auditStateStore.SaveAsync(snapshot, catalog, _lifetimeCts.Token);
            _persistedAudit = new PersistedAuditState { AppVersion = catalog.AppVersion, SavedAt = DateTimeOffset.Now, Snapshot = snapshot, Catalog = catalog };
            AuditFreshnessText = $"Аудит сохранён · {snapshot.CapturedAt.LocalDateTime:dd.MM.yyyy HH:mm}";
            AuditCatalogText = $"Каталог: {catalog.TweakIds.Count} твиков · {catalog.ServiceRuleIds.Count} служб · {catalog.TaskRuleIds.Count} правил задач";
            StatusText = "Аудит завершён и сохранён. Системные настройки не изменялись.";
            AuditButtonText = "Повторить аудит";
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested || _deepScanStageCts?.IsCancellationRequested == true)
        {
            StatusText = "Аудит остановлен.";
        }
        catch (Exception ex)
        {
            StatusText = $"Ошибка аудита: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(ex.ToString(), "Merzo Windows Optimizer — Audit error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task EvaluateAuditFreshnessAfterStartupAsync()
    {
        var current = AuditStateStore.CaptureCurrent(SafeTweaks.Select(static x => x.Id));
        AuditCatalogText = $"Каталог: {current.TweakIds.Count} твиков · {current.ServiceRuleIds.Count} служб · {current.TaskRuleIds.Count} правил задач";
        var pendingMarker = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "updates", "pending-startup-update.txt");
        var startedAfterUpdate = File.Exists(pendingMarker);

        if (_persistedAudit is null)
        {
            AuditFreshnessText = startedAfterUpdate ? "После обновления создаю первый постоянный аудит…" : "Сохранённого аудита пока нет";
            if (!startedAfterUpdate) return;
            StatusText = "После обновления: сохраняю baseline и проверяю новые рекомендации…";
            await RunAuditAsync();
            BuildFirstPersistentAuditRecommendation(current);
            return;
        }

        var diff = AuditStateStore.Compare(_persistedAudit.Catalog, current);
        if (!diff.HasChanges)
        {
            AuditFreshnessText = $"Аудит актуален · сохранён {_persistedAudit.SavedAt.LocalDateTime:dd.MM.yyyy HH:mm}";
            StatusText = "Сохранённый аудит актуален для текущей базы Merzo.";
            return;
        }

        AuditFreshnessText = $"Каталог изменился · новых правил: {diff.AddedTotal}";
        StatusText = "Обнаружены новые/изменённые правила. Выполняю безопасный Smart Re-Audit…";
        await RunAuditAsync();
        BuildCatalogDiffRecommendation(diff);
    }

    private void BuildFirstPersistentAuditRecommendation(AuditCatalogManifest current)
    {
        var newCards = SafeTweaks.Where(static x => x.ProfileTags.Contains("r32_new", StringComparer.OrdinalIgnoreCase)).ToArray();
        var recommended = newCards.Where(static x => !x.Definition.ScanOnly && x.IsSupported && !x.IsApplied).ToArray();
        var configured = newCards.Count(static x => x.IsApplied);
        var serviceNames = new HashSet<string>(new[] { "AJRouter", "WpcMonSvc", "wisvc" }, StringComparer.OrdinalIgnoreCase);
        var presentServices = ServiceAuditItems.Count(x => serviceNames.Contains(x.ServiceName));
        var added = newCards.Length + 3;
        var details = BuildRecommendationDetails(newCards, recommended, presentServices, 0, firstBaseline: true);
        _pendingAuditRecommendation = new AuditRecommendationReport(
            "После обновления аудит обновлён автоматически",
            $"Merzo создал постоянный baseline и проверил новые правила версии 0.1.33. Найдено рекомендаций: {recommended.Length + presentServices}.",
            details, added, recommended.Length + presentServices, configured, true);
    }

    private void BuildCatalogDiffRecommendation(AuditCatalogDiff diff)
    {
        var addedSet = new HashSet<string>(diff.AddedTweaks, StringComparer.OrdinalIgnoreCase);
        var newCards = SafeTweaks.Where(x => addedSet.Contains(x.Id)).ToArray();
        var recommended = newCards.Where(static x => !x.Definition.ScanOnly && x.IsSupported && !x.IsApplied).ToArray();
        var configured = newCards.Count(static x => x.IsApplied);
        var newServices = ServiceAuditItems.Count(x => diff.AddedServices.Contains(x.ServiceName, StringComparer.OrdinalIgnoreCase));
        var newTasks = ScheduledTaskAuditItems.Count(x => diff.AddedTasks.Any(pattern => x.Snapshot.FullPath.Contains(pattern, StringComparison.OrdinalIgnoreCase)));
        var details = BuildRecommendationDetails(newCards, recommended, newServices, newTasks, firstBaseline: false);
        _pendingAuditRecommendation = new AuditRecommendationReport(
            "После обновления найдены новые рекомендации",
            $"База Merzo изменилась: новых правил {diff.AddedTotal}. Smart Re-Audit завершён автоматически.",
            details, diff.AddedTotal, recommended.Length + newServices + newTasks, configured, true);
    }

    private static string BuildRecommendationDetails(IReadOnlyList<TweakCardViewModel> cards, IReadOnlyList<TweakCardViewModel> recommended, int services, int tasks, bool firstBaseline)
    {
        var lines = new List<string>();
        if (firstBaseline) lines.Add("R31 уже сохранял аудит. R32 использует его как baseline и сравнивает performance-каталог по точным ID правил.");
        if (recommended.Count > 0)
        {
            lines.Add("Рекомендуется посмотреть новые твики:");
            foreach (var card in recommended.Take(14)) lines.Add($"• {card.Name} — {card.Risk}");
            if (recommended.Count > 14) lines.Add($"• …ещё {recommended.Count - 14}");
        }
        if (cards.Count > 0 && recommended.Count == 0) lines.Add("Новые твики уже настроены вашей Windows/сборкой или не применимы к этому ПК.");
        if (services > 0) lines.Add($"Новых рекомендаций по обнаруженным службам: {services}.");
        if (tasks > 0) lines.Add($"Новых рекомендаций по Scheduled Tasks: {tasks}.");
        lines.Add("Автоматического применения нет: решение всегда остаётся за пользователем.");
        return string.Join(Environment.NewLine, lines);
    }

    private async Task SelectProcessReductionProfileAsync(string tag, string title)
    {
        await SelectProfileAsync(tag);
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        ProcessReductionStatusText = $"{title}: подготовлено {selected} обратимых настроек. Ничего ещё не применено — проверьте список во вкладке «Выбранное».";
        SelectedOptimizationTabIndex = 3;
    }

    private Task OpenFeedbackIssueAsync(string kind)
    {
        try
        {
            var description = string.IsNullOrWhiteSpace(FeedbackText) ? "Опишите проблему или предложение здесь." : FeedbackText.Trim();
            var title = $"[Merzo R38][{kind}] {description.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? kind}";
            if (title.Length > 120) title = title[..120];
            var body = $"Тип: {kind}\nВерсия Merzo: 0.1.36 / Production R38\nWindows: {WindowsText}\nCPU: {CpuText}\nRAM: {RamText}\nПроцессы: {ProcessText}\nПоследний аудит: {LastAuditText}\nUpdate status: {UpdateStatusText}\n\nОписание пользователя:\n{description}\n\nПримечание: личные файлы, пароли и токены Merzo к этому отчёту не прикладывает автоматически.";
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
            var zipPath = Path.Combine(rootPath, $"MerzoDiagnostics-R46-{DateTime.Now:yyyyMMdd-HHmmss}.zip");
            using var archive = System.IO.Compression.ZipFile.Open(zipPath, System.IO.Compression.ZipArchiveMode.Create);
            var entry = archive.CreateEntry("diagnostics.txt", System.IO.Compression.CompressionLevel.Optimal);
            using (var writer = new StreamWriter(entry.Open(), System.Text.Encoding.UTF8))
            {
                writer.WriteLine("Merzo Windows Optimizer diagnostics — privacy-safe summary");
                writer.WriteLine($"Timestamp: {DateTimeOffset.Now:O}");
                writer.WriteLine("Version: 0.1.36 / Production R38");
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

    public void DismissStartupUpdateNotice() => IsStartupUpdateNoticeVisible = false;

    public AuditRecommendationReport? TakePendingAuditRecommendation()
    {
        var report = _pendingAuditRecommendation;
        _pendingAuditRecommendation = null;
        return report;
    }

    private void ApplySnapshot(SystemAuditSnapshot snapshot)
    {
        WindowsText = $"{snapshot.Windows.ProductName} {snapshot.Windows.DisplayVersion} · build {snapshot.Windows.Build}";
        CpuText = $"{snapshot.Cpu.Name} · {snapshot.Cpu.UsagePercent:F0}% сейчас";
        GpuText = snapshot.Gpus.Count == 0
            ? "GPU: не удалось определить"
            : $"GPU: {string.Join(" · ", snapshot.Gpus.Select(static g => g.Name))}";
        RamText = $"{FormatBytes(snapshot.Memory.UsedBytes)} / {FormatBytes(snapshot.Memory.TotalBytes)} ({snapshot.Memory.UsedPercent:F1}%)";
        ProcessText = snapshot.ProcessCount.ToString();
        ProcessDetailText = $"Системных: {snapshot.SystemProcessCount} · пользовательских: {snapshot.UserProcessCount}";
        StartupText = snapshot.StartupItems.Count.ToString();
        PowerPlanText = snapshot.ActivePowerPlan;
        AdminText = snapshot.IsAdministrator ? "Администратор" : "Обычный";
        HealthScoreText = $"{snapshot.Health.Score}/100";
        HealthRatingText = snapshot.Health.Rating;
        LastAuditText = snapshot.CapturedAt.LocalDateTime.ToString("dd.MM.yyyy HH:mm:ss");

        var systemDrive = Path.GetPathRoot(Environment.SystemDirectory) ?? "C:\\";
        var mainDrive = snapshot.Storage.FirstOrDefault(s =>
            string.Equals(s.Name.TrimEnd('\\'), systemDrive.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase));

        if (mainDrive is null)
        {
            StorageText = $"{snapshot.Storage.Count} дисков";
            StorageDetailText = "Системный диск не определён";
        }
        else
        {
            StorageText = $"{FormatBytes(mainDrive.FreeBytes)} из {FormatBytes(mainDrive.TotalBytes)}";
            StorageDetailText = $"{mainDrive.Name.TrimEnd('\\')} · свободно {mainDrive.FreePercent:F1}%";
        }

        StartupItems.Clear();
        foreach (var item in snapshot.StartupItems)
            StartupItems.Add(item);

        StorageItems.Clear();
        foreach (var item in snapshot.Storage)
            StorageItems.Add(item);

        TopProcesses.Clear();
        foreach (var item in snapshot.TopProcesses)
            TopProcesses.Add(item);
        var backgroundCandidates = snapshot.TopProcesses.Count(static p => p.IsLikelyBackgroundCandidate);
        PerformanceProcessSummaryText = $"Процессов: {snapshot.ProcessCount} · пользовательских: {snapshot.UserProcessCount} · в TOP-{snapshot.TopProcesses.Count} кандидатов на фоновую разгрузку: {backgroundCandidates}.";
        ProcessReductionStatusText = $"Найдено {backgroundCandidates} кандидатов среди TOP-{snapshot.TopProcesses.Count}. Выберите SAFE / AGGRESSIVE / LITE-LIKE — Merzo только подготовит обратимый набор для просмотра.";

        HealthExplanations.Clear();
        foreach (var note in snapshot.Health.Explanations)
            HealthExplanations.Add(note);
    }

    private void DispatcherOnStateChanged(object? sender, OperationStateChangedEventArgs e)
    {
        if (_disposed || Application.Current is null)
            return;

        Application.Current.Dispatcher.Invoke(() =>
        {
            if (e.OperationName == "System Audit" && e.State == OperationState.Running)
                StatusText = "AuditEngine работает через центральный async-dispatcher…";
        });
    }

    public void Dispose()
    {
        _deepScanCts?.Cancel(); _cleanupScanCts?.Cancel(); _cleanupOperationCts?.Cancel(); _updateOperationCts?.Cancel();
        _powerRefreshTimer.Stop(); _powerRefreshTimer.Tick -= PowerRefreshTimerOnTick;
        if (_disposed)
            return;

        _disposed = true;
        _lifetimeCts.Cancel();
        _dispatcher.StateChanged -= DispatcherOnStateChanged;
        if (_updateService is IDisposable updateDisposable)
            updateDisposable.Dispose();
        _updateOperationCts?.Dispose();
        _lifetimeCts.Dispose();
    }


    private static string FormatActionPreview(TweakDefinition tweak)
    {
        return string.Join(Environment.NewLine, tweak.RegistryActions.Select(action =>
        {
            var hive = action.Hive == RegistryHiveScope.LocalMachine ? "HKLM" : "HKCU";
            if (action.Mode == RegistryTweakActionMode.DeleteValue)
                return $"• {hive}\\{action.KeyPath}\\{action.ValueName} → удалить значение (snapshot сохранит оригинал)";

            var value = action.ValueType switch
            {
                RegistryTweakValueType.DWord or RegistryTweakValueType.QWord => action.IntegerValue?.ToString() ?? "0",
                RegistryTweakValueType.String or RegistryTweakValueType.ExpandString => action.StringValue ?? string.Empty,
                _ => "<binary/multi>"
            };

            return $"• {hive}\\{action.KeyPath}\\{action.ValueName} = {value} ({action.ValueType})";
        }));
    }

    private static string FormatBytes(ulong bytes) => FormatBytes(bytes > long.MaxValue ? long.MaxValue : (long)bytes);

    private static string FormatBytes(long bytes)
    {
        string[] units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
        double value = bytes;
        var index = 0;

        while (value >= 1024 && index < units.Length - 1)
        {
            value /= 1024;
            index++;
        }

        return $"{value:F1} {units[index]}";
    }
}
