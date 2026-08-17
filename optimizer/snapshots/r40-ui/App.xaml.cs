using System.IO;
using System.Windows;
using System.Windows.Threading;
using MerzoOptimizer.App.ViewModels;
using MerzoOptimizer.Core.Dispatching;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Safety;
using MerzoOptimizer.Windows.Audit;
using MerzoOptimizer.Windows.Cleanup;
using MerzoOptimizer.Windows.Debloat;
using MerzoOptimizer.Windows.Startup;
using MerzoOptimizer.Windows.Diagnostics;
using MerzoOptimizer.Windows.Restore;
using MerzoOptimizer.Windows.Snapshots;
using MerzoOptimizer.Windows.Tweaks;
using MerzoOptimizer.Windows.Services;
using MerzoOptimizer.Windows.ScheduledTasks;
using MerzoOptimizer.Windows.Power;
using MerzoOptimizer.Windows.Updates;
using MerzoOptimizer.Windows.Elevation;
using MerzoOptimizer.Windows.Network;

namespace MerzoOptimizer.App;

public partial class App : Application
{
    private static readonly string CrashLogDirectory = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "MerzoWindowsOptimizer",
        "logs");

    private AsyncOperationDispatcher? _dispatcher;
    private MainWindowViewModel? _viewModel;
    private ElevatedOperationBroker? _elevationBroker;
    private Mutex? _singleInstanceMutex;

    protected override async void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;

        try
        {
            _singleInstanceMutex = new Mutex(initiallyOwned: true, name: @"Local\MerzoWindowsOptimizer.SingleInstance", createdNew: out var firstInstance);
            if (!firstInstance)
            {
                global::MerzoOptimizer.App.MerzoDialog.Show("Merzo Windows Optimizer уже запущен. Закройте существующее окно или фоновый экземпляр перед запуском второго.", "Merzo Windows Optimizer", MessageBoxButton.OK, MessageBoxImage.Warning);
                Shutdown(2);
                return;
            }
            Directory.CreateDirectory(CrashLogDirectory);
            WriteStartupDiagnostic("Application startup entered.");

            ShutdownMode = ShutdownMode.OnMainWindowClose;
            base.OnStartup(e);

            var logger = new JsonLinesAuditLogger();
            _dispatcher = new AsyncOperationDispatcher(maxConcurrency: 2);

            var auditService = new WindowsSystemAuditService(logger);
            var snapshotService = new WindowsSnapshotService();
            var safetyEngine = new SafetyEngine();

            // R21: normal-user shell; privileged mutations are delegated to the elevated helper.
            var appDataRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer");
            _elevationBroker = new ElevatedOperationBroker(
                snapshotService.SnapshotDirectory,
                logger.LogDirectory,
                Path.Combine(appDataRoot, "cleanup-backups"));
            var localRestoreService = new WindowsRestoreService(snapshotService, logger);
            var localTweakService = new WindowsTweakExecutionService(
                snapshotService,
                localRestoreService,
                safetyEngine,
                logger);

            var restoreService = new ElevationAwareRestoreService(localRestoreService, snapshotService, _elevationBroker);
            var tweakService = new ElevationAwareTweakExecutionService(localTweakService, _elevationBroker);
            var recoveryDiagnosticService = new SafeRecoveryDiagnosticService(logger);
            var startupOptimizerService = new WindowsStartupOptimizerService(tweakService, snapshotService, restoreService);
            var cleanupService = new ElevationAwareCleanupService(new WindowsCleanupService(snapshotService, logger), _elevationBroker);
            var debloatScanner = new WindowsDebloatScanner();
            var serviceAudit = new ElevationAwareServiceOptimizationService(
                new WindowsServiceAuditService(snapshotService, localRestoreService, logger), _elevationBroker);
            var taskAudit = new ElevationAwareScheduledTaskOptimizationService(
                new WindowsScheduledTaskAuditService(snapshotService, localRestoreService, logger), _elevationBroker);
            var powerProfiles = new ElevationAwarePowerProfileService(
                new WindowsPowerProfileService(snapshotService, localRestoreService, logger), _elevationBroker);
            var updateService = new GitHubUpdateService();
            var networkRepairService = new WindowsNetworkRepairService(_elevationBroker);

            _viewModel = new MainWindowViewModel(
                auditService,
                _dispatcher,
                logger,
                tweakService,
                snapshotService,
                restoreService,
                recoveryDiagnosticService,
                startupOptimizerService,
                cleanupService,
                debloatScanner,
                serviceAudit,
                taskAudit,
                powerProfiles,
                updateService,
                networkRepairService);

            var pendingMarker = Path.Combine(appDataRoot, "updates", "pending-startup-update.txt");
            var pendingVersion = File.Exists(pendingMarker) ? File.ReadAllText(pendingMarker).Trim() : string.Empty;
            var splash = new StartupSplashWindow(!string.IsNullOrWhiteSpace(pendingVersion), string.IsNullOrWhiteSpace(pendingVersion) ? "0.1.40" : pendingVersion);
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            splash.Show();
            splash.SetStatus("Инициализирую ядро и состояние Windows…", "Проверяю Snapshot/Restore, автозагрузку, очистку, службы и активный режим питания.");

            var window = new MainWindow { DataContext = _viewModel };
            MainWindow = window;
            if (_viewModel is not null) await _viewModel.InitializeAsync();
            splash.SetStatus("Основная программа готова.", "Открываю интерфейс и завершаю экран запуска…");
            await Task.Delay(220);
            window.Show();
            ShutdownMode = ShutdownMode.OnMainWindowClose;
            splash.Close();
            try { if (File.Exists(pendingMarker)) File.Delete(pendingMarker); } catch { }
            ReleaseNotesWindow.ShowCurrentReleaseIfNeeded(window);
            AuditRecommendationsWindow.ShowIfPending(window, _viewModel);
            ShowPendingCrashReport(window);
            WriteStartupDiagnostic("Main window shown successfully after splash initialization. Production shell + on-demand elevated helper initialized.");
        }
        catch (Exception ex)
        {
            HandleFatalStartupException(ex, "Startup");
            Shutdown(1);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        try
        {
            _viewModel?.Dispose();
            if (_elevationBroker is not null)
                _elevationBroker.DisposeAsync().AsTask().GetAwaiter().GetResult();
            _singleInstanceMutex?.Dispose();
            WriteStartupDiagnostic($"Application exit. Code={e.ApplicationExitCode}.");
        }
        catch (Exception ex)
        {
            WriteCrashLog(ex, "OnExit cleanup");
        }
        finally
        {
            DispatcherUnhandledException -= OnDispatcherUnhandledException;
            AppDomain.CurrentDomain.UnhandledException -= OnUnhandledException;
        }

        base.OnExit(e);
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        HandleFatalStartupException(e.Exception, "DispatcherUnhandledException");
        e.Handled = true;
        Shutdown(1);
    }

    private static void OnUnhandledException(object? sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex)
            WriteCrashLog(ex, "AppDomain.UnhandledException");
        else
            WriteStartupDiagnostic($"Unhandled non-Exception object: {e.ExceptionObject}");
    }

    private static void HandleFatalStartupException(Exception ex, string source)
    {
        var path = WriteCrashLog(ex, source);

        global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Merzo Windows Optimizer encountered a startup error.\n\n" +
            $"A diagnostic log was saved here:\n{path}\n\n" +
            $"Error: {ex.Message}",
            "Merzo Windows Optimizer — startup error",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }

    private static string WriteCrashLog(Exception ex, string source)
    {
        Directory.CreateDirectory(CrashLogDirectory);
        var path = Path.Combine(CrashLogDirectory, $"startup-crash-{DateTime.Now:yyyyMMdd-HHmmss}.log");
        File.WriteAllText(path,
            $"Timestamp: {DateTimeOffset.Now:O}{Environment.NewLine}" +
            $"Source: {source}{Environment.NewLine}" +
            $"OS: {Environment.OSVersion}{Environment.NewLine}" +
            $"64-bit OS: {Environment.Is64BitOperatingSystem}{Environment.NewLine}" +
            $"64-bit process: {Environment.Is64BitProcess}{Environment.NewLine}" +
            $".NET: {Environment.Version}{Environment.NewLine}" +
            $"Base directory: {AppContext.BaseDirectory}{Environment.NewLine}" +
            $"Exception:{Environment.NewLine}{ex}{Environment.NewLine}");
        return path;
    }

    private static void ShowPendingCrashReport(Window owner)
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

            var answer = global::MerzoOptimizer.App.MerzoDialog.Show(owner,
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
            var title = "[Crash][R40] Автоматический отчёт Merzo Windows Optimizer";
            var body = "Версия: 0.1.36 / Production R38\n\nДиагностика предыдущего сбоя:\n```text\n" + raw + "\n```\n\nПожалуйста, добавьте шаги, после которых возникла ошибка.";
            var url = "https://github.com/Merzo4/my-app-updates/issues/new?title=" + Uri.EscapeDataString(title) + "&body=" + Uri.EscapeDataString(body);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch
        {
            // Crash reporting must never make startup fail.
        }
    }

    private static void WriteStartupDiagnostic(string message)
    {
        try
        {
            Directory.CreateDirectory(CrashLogDirectory);
            var path = Path.Combine(CrashLogDirectory, "startup-session.log");
            File.AppendAllText(path, $"{DateTimeOffset.Now:O} | {message}{Environment.NewLine}");
        }
        catch
        {
            // Diagnostics must never prevent the application from starting or closing.
        }
    }
}
