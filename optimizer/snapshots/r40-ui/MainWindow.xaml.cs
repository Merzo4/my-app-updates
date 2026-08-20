using System.Windows;
using System.Runtime.InteropServices;
using System.Windows.Interop;
using System.Windows.Input;

namespace MerzoOptimizer.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }


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

    private void Dashboard_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 0;
    private void Audit_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 1;
    private void Tweaks_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 2;
    private void Startup_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 3;
    private void Cleanup_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 4;
    private void ServicesTasks_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 5;
    private void GamingDev_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 6;
    private void Network_Click(object sender, RoutedEventArgs e)
    {
        MainTabs.SelectedIndex = 7;
        if (DataContext is ViewModels.MainWindowViewModel vm && vm.DiagnoseNetworkCommand.CanExecute(null))
            vm.DiagnoseNetworkCommand.Execute(null);
    }
    private void Power_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 8;
    private void Updates_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 9;
    private void Restore_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 10;
    private void Logs_Click(object sender, RoutedEventArgs e) => MainTabs.SelectedIndex = 11;
    private void OpenOptimization_Click(object sender, RoutedEventArgs e) { TweaksNav.IsChecked = true; MainTabs.SelectedIndex = 2; }
    private void OpenUpdatesFromNotice_Click(object sender, RoutedEventArgs e)
    {
        UpdatesNav.IsChecked = true;
        MainTabs.SelectedIndex = 9;
        if (DataContext is ViewModels.MainWindowViewModel vm) vm.DismissStartupUpdateNotice();
    }


    private void Minimize_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void MaximizeRestore_Click(object sender, RoutedEventArgs e) => ToggleMaximizeRestore();
    private void Close_Click(object sender, RoutedEventArgs e) => Close();

    private void ToggleMaximizeRestore()
    {
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal
            : WindowState.Maximized;
    }
    public void OpenOptimizationFromRecommendation()
    {
        MainTabs.SelectedIndex = 2;
        TweaksNav.IsChecked = true;
    }

}
