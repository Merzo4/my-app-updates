from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')

# -----------------------------------------------------------------------------
# Unified Merzo themed dialogs: native white MessageBox must not leak into the
# dark shell. This is intentionally code-only WPF so every existing caller can
# be redirected without introducing another XAML resource dependency.
# -----------------------------------------------------------------------------
dialog_path = root/'src'/'MerzoOptimizer.App'/'MerzoDialog.cs'
dialog_code = r'''using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace MerzoOptimizer.App;

public static class MerzoDialog
{
    public static MessageBoxResult Show(string message) =>
        Show(message, "Merzo Windows Optimizer", MessageBoxButton.OK, MessageBoxImage.None);

    public static MessageBoxResult Show(string message, string caption) =>
        Show(message, caption, MessageBoxButton.OK, MessageBoxImage.None);

    public static MessageBoxResult Show(string message, string caption, MessageBoxButton buttons) =>
        Show(message, caption, buttons, MessageBoxImage.None);

    public static MessageBoxResult Show(string message, string caption, MessageBoxButton buttons, MessageBoxImage icon)
    {
        var result = buttons switch
        {
            MessageBoxButton.YesNo => MessageBoxResult.No,
            MessageBoxButton.YesNoCancel => MessageBoxResult.Cancel,
            MessageBoxButton.OKCancel => MessageBoxResult.Cancel,
            _ => MessageBoxResult.OK
        };

        var window = new Window
        {
            Title = caption,
            Width = 510,
            MinWidth = 430,
            MaxWidth = 650,
            SizeToContent = SizeToContent.Height,
            WindowStyle = WindowStyle.None,
            ResizeMode = ResizeMode.NoResize,
            ShowInTaskbar = false,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = Brushes.Transparent,
            AllowsTransparency = true,
            FontFamily = new FontFamily("Segoe UI"),
            Foreground = B("#EEF5F5"),
            Topmost = false
        };

        var owner = Application.Current?.Windows.OfType<Window>().FirstOrDefault(static w => w.IsActive)
                    ?? Application.Current?.MainWindow;
        if (owner is { IsVisible: true } && !ReferenceEquals(owner, window))
            window.Owner = owner;
        else
            window.WindowStartupLocation = WindowStartupLocation.CenterScreen;

        var shell = new Border
        {
            Background = B("#0E151C"),
            BorderBrush = B("#2A5E59"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(13),
            Padding = new Thickness(0),
            Effect = new System.Windows.Media.Effects.DropShadowEffect
            {
                BlurRadius = 24, ShadowDepth = 5, Opacity = 0.42, Color = Colors.Black
            }
        };
        window.Content = shell;

        var layout = new Grid();
        layout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(46) });
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        shell.Child = layout;

        var titleGrid = new Grid { Background = B("#101A21") };
        titleGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        titleGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        titleGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(42) });
        titleGrid.MouseLeftButtonDown += (_, e) => { if (e.ButtonState == MouseButtonState.Pressed) window.DragMove(); };
        Grid.SetRow(titleGrid, 0);
        layout.Children.Add(titleGrid);

        var badge = new Border
        {
            Width = 27, Height = 27, CornerRadius = new CornerRadius(8), Margin = new Thickness(12, 0, 9, 0),
            Background = B("#173733"), BorderBrush = B("#2B6B64"), BorderThickness = new Thickness(1),
            VerticalAlignment = VerticalAlignment.Center
        };
        badge.Child = new TextBlock
        {
            Text = "M", Foreground = B("#67BEB4"), FontWeight = FontWeights.Bold, FontSize = 13,
            HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center
        };
        titleGrid.Children.Add(badge);

        var title = new TextBlock
        {
            Text = string.IsNullOrWhiteSpace(caption) ? "Merzo Windows Optimizer" : caption,
            FontSize = 13.2, FontWeight = FontWeights.SemiBold, Foreground = B("#F2F7F7"),
            VerticalAlignment = VerticalAlignment.Center, TextTrimming = TextTrimming.CharacterEllipsis
        };
        Grid.SetColumn(title, 1); titleGrid.Children.Add(title);

        var close = CreateButton("×", false, 34);
        close.FontSize = 18; close.Margin = new Thickness(2, 6, 7, 6);
        close.Click += (_, _) => window.Close();
        Grid.SetColumn(close, 2); titleGrid.Children.Add(close);

        var body = new Grid { Margin = new Thickness(18, 17, 18, 13) };
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(42) });
        body.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        Grid.SetRow(body, 1); layout.Children.Add(body);

        var iconBorder = new Border
        {
            Width = 34, Height = 34, CornerRadius = new CornerRadius(17),
            Background = B(IconBackground(icon)), BorderBrush = B(IconColor(icon)), BorderThickness = new Thickness(1),
            VerticalAlignment = VerticalAlignment.Top, Margin = new Thickness(0, 1, 8, 0)
        };
        iconBorder.Child = new TextBlock
        {
            Text = IconGlyph(icon), Foreground = B(IconColor(icon)), FontWeight = FontWeights.Bold,
            FontSize = 16, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center
        };
        body.Children.Add(iconBorder);

        var textPanel = new StackPanel();
        var eyebrow = new TextBlock
        {
            Text = IconEyebrow(icon), Foreground = B("#6FA9A3"), FontSize = 10.2,
            FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 0, 0, 5)
        };
        var messageText = new TextBlock
        {
            Text = message ?? string.Empty, Foreground = B("#DCE8E8"), FontSize = 12.2,
            TextWrapping = TextWrapping.Wrap, LineHeight = 18, MaxWidth = 540
        };
        textPanel.Children.Add(eyebrow); textPanel.Children.Add(messageText);
        Grid.SetColumn(textPanel, 1); body.Children.Add(textPanel);

        var footer = new Border
        {
            Background = B("#0B1117"), BorderBrush = B("#202D35"), BorderThickness = new Thickness(0, 1, 0, 0),
            Padding = new Thickness(15, 10, 15, 11)
        };
        Grid.SetRow(footer, 2); layout.Children.Add(footer);
        var buttonsPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        footer.Child = buttonsPanel;

        void Add(string label, MessageBoxResult value, bool primary)
        {
            var b = CreateButton(label, primary, label.Length > 8 ? 112 : 88);
            b.Margin = new Thickness(6, 0, 0, 0);
            b.Click += (_, _) => { result = value; window.Close(); };
            buttonsPanel.Children.Add(b);
        }

        switch (buttons)
        {
            case MessageBoxButton.YesNo:
                Add("Нет", MessageBoxResult.No, false); Add("Да", MessageBoxResult.Yes, true); break;
            case MessageBoxButton.YesNoCancel:
                Add("Отмена", MessageBoxResult.Cancel, false); Add("Нет", MessageBoxResult.No, false); Add("Да", MessageBoxResult.Yes, true); break;
            case MessageBoxButton.OKCancel:
                Add("Отмена", MessageBoxResult.Cancel, false); Add("Продолжить", MessageBoxResult.OK, true); break;
            default:
                Add("Понятно", MessageBoxResult.OK, true); break;
        }

        window.PreviewKeyDown += (_, e) =>
        {
            if (e.Key != Key.Escape) return;
            if (buttons == MessageBoxButton.OK) result = MessageBoxResult.OK;
            window.Close();
        };
        window.ShowDialog();
        return result;
    }

    private static Button CreateButton(string text, bool primary, double minWidth)
    {
        var bg = primary ? "#1E504C" : "#151E26";
        var border = primary ? "#2F756D" : "#2B3943";
        var hover = primary ? "#285F5A" : "#1C2933";
        var button = new Button
        {
            Content = text, MinWidth = minWidth, Height = 32, Padding = new Thickness(11, 3, 11, 3),
            Background = B(bg), Foreground = B("#EDF5F4"), BorderBrush = B(border), BorderThickness = new Thickness(1),
            FontSize = 11.2, FontWeight = FontWeights.SemiBold, Cursor = Cursors.Hand
        };
        var template = new ControlTemplate(typeof(Button));
        var factory = new FrameworkElementFactory(typeof(Border));
        factory.Name = "border";
        factory.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        factory.SetBinding(Border.BorderBrushProperty, new System.Windows.Data.Binding("BorderBrush") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        factory.SetBinding(Border.BorderThicknessProperty, new System.Windows.Data.Binding("BorderThickness") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        factory.SetValue(Border.CornerRadiusProperty, new CornerRadius(8));
        var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
        presenter.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        presenter.SetValue(ContentPresenter.VerticalAlignmentProperty, VerticalAlignment.Center);
        factory.AppendChild(presenter);
        template.VisualTree = factory;
        var hoverTrigger = new Trigger { Property = Button.IsMouseOverProperty, Value = true };
        hoverTrigger.Setters.Add(new Setter(Button.BackgroundProperty, B(hover)));
        template.Triggers.Add(hoverTrigger);
        button.Template = template;
        return button;
    }

    private static SolidColorBrush B(string hex) => new((Color)ColorConverter.ConvertFromString(hex)!);
    private static string IconGlyph(MessageBoxImage icon) => icon switch
    {
        MessageBoxImage.Error => "×", MessageBoxImage.Warning => "!", MessageBoxImage.Question => "?", _ => "i"
    };
    private static string IconEyebrow(MessageBoxImage icon) => icon switch
    {
        MessageBoxImage.Error => "ОШИБКА", MessageBoxImage.Warning => "ВАЖНО", MessageBoxImage.Question => "ПОДТВЕРЖДЕНИЕ", _ => "РЕЗУЛЬТАТ"
    };
    private static string IconColor(MessageBoxImage icon) => icon switch
    {
        MessageBoxImage.Error => "#E77878", MessageBoxImage.Warning => "#D7A85B", MessageBoxImage.Question => "#6EB7B0", _ => "#62B4AC"
    };
    private static string IconBackground(MessageBoxImage icon) => icon switch
    {
        MessageBoxImage.Error => "#321C22", MessageBoxImage.Warning => "#33291A", MessageBoxImage.Question => "#17312F", _ => "#17312F"
    };
}
'''
write(dialog_path, dialog_code)

# Redirect every native MessageBox inside the App assembly to the themed dialog.
app_src = root/'src'/'MerzoOptimizer.App'
for cs in app_src.rglob('*.cs'):
    if cs.name == 'MerzoDialog.cs':
        continue
    s = read(cs)
    s = s.replace('System.Windows.MessageBox.Show(', 'global::MerzoOptimizer.App.MerzoDialog.Show(')
    s = re.sub(r'(?<![\w.])MessageBox\.Show\(', 'global::MerzoOptimizer.App.MerzoDialog.Show(', s)
    write(cs, s)

# -----------------------------------------------------------------------------
# Operation Center: preserve the existing live bindings/engine, but present the
# real progress in the same clear hierarchy as Update Center.
# -----------------------------------------------------------------------------
xaml_path = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml_path)
start = x.find('<TabItem Header="Ход работы"')
if start < 0:
    raise SystemExit('R37: operation tab anchor missing')
end = x.find('</TabItem>', start)
if end < 0:
    raise SystemExit('R37: operation tab end missing')
end += len('</TabItem>')
new_tab = r'''<TabItem Header="Ход работы" Style="{StaticResource SubTabItem}">
                                <Grid Margin="0,5,0,0">
                                    <Grid.RowDefinitions><RowDefinition Height="142"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                    <Border Grid.Row="0" Background="#101B22" BorderBrush="#2A5A56" BorderThickness="1" CornerRadius="10" Padding="12,9" Margin="0,0,0,7">
                                        <Grid>
                                            <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                            <Grid Grid.Row="0">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <StackPanel>
                                                    <TextBlock Text="Центр выполнения" FontSize="14.5" FontWeight="SemiBold"/>
                                                    <TextBlock Text="Живой ход операции · ничего не скрывается в фоне" Foreground="{StaticResource TextMuted}" FontSize="10.2" Margin="0,2,0,0"/>
                                                </StackPanel>
                                                <Border Grid.Column="1" Background="#173733" BorderBrush="#2C6A63" BorderThickness="1" CornerRadius="11" Padding="9,4" VerticalAlignment="Center">
                                                    <TextBlock Text="{Binding DeepScanProgress, StringFormat={}{0:0}%}" Foreground="#72C3B9" FontSize="12" FontWeight="Bold"/>
                                                </Border>
                                            </Grid>
                                            <TextBlock Grid.Row="1" Text="{Binding DeepScanStatusText, Mode=OneWay}" Foreground="#D9E8E7" FontSize="11.7" FontWeight="SemiBold" Margin="0,8,0,0" TextTrimming="CharacterEllipsis"/>
                                            <ProgressBar Grid.Row="2" Value="{Binding DeepScanProgress, Mode=OneWay}" Maximum="100" Height="7" Margin="0,8,0,7"/>
                                            <Grid Grid.Row="3">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <StackPanel Orientation="Horizontal">
                                                    <Border Background="#152128" CornerRadius="7" Padding="7,3" Margin="0,0,5,0"><TextBlock Text="1  Snapshot" FontSize="9.7" Foreground="#A8C1C0"/></Border>
                                                    <Border Background="#152128" CornerRadius="7" Padding="7,3" Margin="0,0,5,0"><TextBlock Text="2  Apply" FontSize="9.7" Foreground="#A8C1C0"/></Border>
                                                    <Border Background="#152128" CornerRadius="7" Padding="7,3" Margin="0,0,5,0"><TextBlock Text="3  Verify" FontSize="9.7" Foreground="#A8C1C0"/></Border>
                                                    <Border Background="#152128" CornerRadius="7" Padding="7,3" Margin="0,0,5,0"><TextBlock Text="4  Log" FontSize="9.7" Foreground="#A8C1C0"/></Border>
                                                    <Border Background="#17332F" CornerRadius="7" Padding="7,3"><TextBlock Text="Undo ready" FontSize="9.7" Foreground="#6FC1B7"/></Border>
                                                </StackPanel>
                                                <Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding CancelDeepOptimizationScanCommand}" Content="Отменить" MinWidth="86"/>
                                            </Grid>
                                        </Grid>
                                    </Border>
                                    <Border Grid.Row="1" Background="#0F151C" BorderBrush="{StaticResource BorderSoft}" BorderThickness="1" CornerRadius="10" Padding="9">
                                        <Grid>
                                            <Grid.RowDefinitions><RowDefinition Height="31"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                            <Grid Grid.Row="0">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <StackPanel Orientation="Horizontal"><TextBlock Text="Этапы операции" FontSize="11.8" FontWeight="SemiBold"/><Border Background="#17312E" CornerRadius="7" Padding="6,2" Margin="8,0,0,0"><TextBlock Text="LIVE" Foreground="#69BDB4" FontSize="9.3" FontWeight="Bold"/></Border></StackPanel>
                                                <TextBlock Grid.Column="1" Text="Snapshot → Apply → Verify → Log → Undo" Foreground="{StaticResource TextMuted}" FontSize="9.6" VerticalAlignment="Center"/>
                                            </Grid>
                                            <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">
                                                <ItemsControl ItemsSource="{Binding DeepScanSteps}">
                                                    <ItemsControl.ItemTemplate><DataTemplate>
                                                        <Border Background="#121B24" BorderBrush="#23333D" BorderThickness="1" CornerRadius="8" Padding="9,6" Margin="0,0,0,5">
                                                            <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="24"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                                                                <Border Width="15" Height="15" CornerRadius="8" Background="#173A35" BorderBrush="#34786F" BorderThickness="1" VerticalAlignment="Center"><TextBlock Text="✓" Foreground="#70C2B7" FontSize="9" HorizontalAlignment="Center" VerticalAlignment="Center"/></Border>
                                                                <TextBlock Grid.Column="1" Text="{Binding}" FontSize="10.6" Foreground="{StaticResource TextSecondary}" TextWrapping="Wrap" VerticalAlignment="Center"/>
                                                            </Grid>
                                                        </Border>
                                                    </DataTemplate></ItemsControl.ItemTemplate>
                                                </ItemsControl>
                                            </ScrollViewer>
                                        </Grid>
                                    </Border>
                                </Grid>
                            </TabItem>'''
x = x[:start] + new_tab + x[end:]
write(xaml_path, x)

# Make applying a prepared set immediately reveal the real live operation tab.
vm_path = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
vm = read(vm_path)
method_start = vm.find('private async Task ApplySelectedTweaksAsync')
if method_start < 0:
    raise SystemExit('R37: ApplySelectedTweaksAsync missing')
next_method = vm.find('\n    private ', method_start + 20)
if next_method < 0: next_method = len(vm)
section = vm[method_start:next_method]
if 'SelectedOptimizationTabIndex = 3;' not in section:
    # Insert after the first busy transition inside this exact method.
    section2 = section.replace('IsStage2Busy = true;', 'IsStage2Busy = true;\n        SelectedOptimizationTabIndex = 3;', 1)
    if section2 == section:
        # fallback before try block
        section2 = section.replace('try\n        {', 'SelectedOptimizationTabIndex = 3;\n\n        try\n        {', 1)
    section = section2
vm = vm[:method_start] + section + vm[next_method:]
write(vm_path, vm)

print('R37 themed dialogs + operation visualization patch: OK')
