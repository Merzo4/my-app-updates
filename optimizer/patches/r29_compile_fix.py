from pathlib import Path
import os,re

root = Path(os.environ['SOURCE_ROOT'])
path = root / 'src' / 'MerzoOptimizer.Windows' / 'Cleanup' / 'WindowsCleanupService.cs'
s = path.read_text(encoding='utf-8-sig')
marker = '    private async Task<CleanupRunResult> CleanWithoutBackupAsync('
if marker not in s:
    insert_anchor = '    private static async Task RestoreDeletedSubsetAsync('
    if insert_anchor not in s:
        raise SystemExit('R29 cleanup insert anchor missing')
    direct = r'''    private async Task<CleanupRunResult> CleanWithoutBackupAsync(CleanupCategorySnapshot category, FileInfo[] candidates, CancellationToken cancellationToken)
    {
        long deletedBytes = 0;
        var deletedCount = 0;
        var skipped = 0;
        foreach (var file in candidates)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                var length = file.Exists ? file.Length : 0;
                if (file.Exists) File.Delete(file.FullName);
                deletedBytes += length;
                deletedCount++;
            }
            catch (IOException) { skipped++; }
            catch (UnauthorizedAccessException) { skipped++; }
        }

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Cleanup",
            Action = $"Очистка без backup: {category.Name}",
            Status = "Success",
            TweakId = $"cleanup.{category.Id}",
            OldValue = $"{deletedCount} files / {deletedBytes} bytes",
            NewValue = "No backup (user choice)",
            Details = $"Irreversible cleanup requested by user; skipped locked/protected: {skipped}."
        }, cancellationToken).ConfigureAwait(false);

        return new CleanupRunResult
        {
            Success = true,
            Changed = deletedCount > 0,
            SnapshotId = null,
            ArchivedFileCount = deletedCount,
            OriginalBytes = deletedBytes,
            BackupBytes = 0,
            NetFreedBytes = deletedBytes,
            Message = deletedCount == 0
                ? $"Ничего не удалено. Занятых/защищённых файлов пропущено: {skipped}."
                : $"Очищено без резервной копии: {deletedCount} файлов, освобождено {deletedBytes} байт. Пропущено: {skipped}."
        };
    }

'''
    s = s.replace(insert_anchor, direct + insert_anchor, 1)
    path.write_text(s, encoding='utf-8')

# MerzoOperationGuard uses explicit file-system APIs.
guard = root / 'src' / 'MerzoOptimizer.App' / 'Operations' / 'MerzoOperationGuard.cs'
g = guard.read_text(encoding='utf-8-sig')
if 'using System.IO;' not in g:
    g = 'using System.IO;\n' + g
guard.write_text(g, encoding='utf-8')

# R28 accidentally placed "Ход очистки" inside Audit. R29 owns the correction:
# remove that user-visible block and insert a richer progress tab into Cleanup.
xaml = root / 'src' / 'MerzoOptimizer.App' / 'MainWindow.xaml'
x = xaml.read_text(encoding='utf-8-sig')
x = re.sub(r'\n\s*<TabItem Header="Ход очистки" Style="\{StaticResource SubTabItem\}">.*?</TabItem>\n', '\n', x, count=1, flags=re.S)

progress_tab = r'''
                        <TabItem Header="Ход очистки" Style="{StaticResource SubTabItem}">
                            <Grid Margin="0,4,0,0">
                                <Grid.RowDefinitions><RowDefinition Height="126"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                <Border Grid.Row="0" Background="#101B22" BorderBrush="#2A4B54" BorderThickness="1" CornerRadius="9" Padding="11,8" Margin="0,0,0,7">
                                    <Grid>
                                        <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                        <Grid Grid.Row="0">
                                            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                            <StackPanel><TextBlock Text="{Binding CleanupOperationTitle, Mode=OneWay}" FontSize="12.5" FontWeight="SemiBold"/><TextBlock Text="{Binding CleanupOperationPhase, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="9" FontWeight="SemiBold" Margin="0,2,0,0"/></StackPanel>
                                            <Border Grid.Column="1" Background="#173A35" BorderBrush="#2B655A" BorderThickness="1" CornerRadius="10" Padding="8,3" Margin="8,0,6,0" VerticalAlignment="Center"><TextBlock Text="{Binding CleanupProgressText, Mode=OneWay}" Foreground="{StaticResource Accent}" FontWeight="Bold" FontSize="9"/></Border>
                                            <Button Grid.Column="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding CancelCleanupOperationCommand}" Content="Отменить" MinWidth="82" VerticalAlignment="Center"/>
                                        </Grid>
                                        <ProgressBar Grid.Row="1" Value="{Binding CleanupProgress, Mode=OneWay}" Maximum="100" Height="6" Margin="0,9,0,6"/>
                                        <Grid Grid.Row="2"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                                            <StackPanel Grid.Column="0"><TextBlock Text="Сейчас выполняется" Style="{StaticResource Eyebrow}"/><TextBlock Text="{Binding CleanupOperationDetail, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.5" TextWrapping="Wrap" Margin="0,2,12,0"/></StackPanel>
                                            <StackPanel Grid.Column="1"><TextBlock Text="Защита / результат" Style="{StaticResource Eyebrow}"/><TextBlock Text="{Binding CleanupOperationResult, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.5" TextWrapping="Wrap" Margin="0,2,0,0"/></StackPanel>
                                        </Grid>
                                    </Grid>
                                </Border>
                                <Border Grid.Row="1" Background="#0F151C" BorderBrush="{StaticResource BorderSoft}" BorderThickness="1" CornerRadius="9" Padding="8">
                                    <Grid><Grid.RowDefinitions><RowDefinition Height="26"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock Text="Этапы операции" FontSize="10.5" FontWeight="SemiBold"/><TextBlock Grid.Column="1" Text="Подготовка → Backup (по выбору) → Snapshot/Очистка → Проверка" Foreground="{StaticResource TextMuted}" FontSize="8"/></Grid>
                                        <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><ItemsControl ItemsSource="{Binding CleanupOperationSteps}"><ItemsControl.ItemTemplate><DataTemplate><Border Background="#121B24" BorderBrush="#202C39" BorderThickness="1" CornerRadius="7" Padding="8,5" Margin="0,0,0,4"><TextBlock Text="{Binding}" Foreground="{StaticResource TextSecondary}" FontSize="8.8" TextWrapping="Wrap"/></Border></DataTemplate></ItemsControl.ItemTemplate></ItemsControl></ScrollViewer>
                                    </Grid>
                                </Border>
                            </Grid>
                        </TabItem>
'''
cleanup_start = x.find('Text="Очистка / Debloat"', 200)
if cleanup_start < 0:
    raise SystemExit('R29 cleanup section missing')
# Use the Services section as an unambiguous boundary, then insert before the Cleanup TabControl close.
cleanup_end = x.find('<!-- Services + Scheduled Tasks reversible control -->', cleanup_start)
if cleanup_end < 0:
    raise SystemExit('R29 cleanup section end missing')
cleanup_slice = x[cleanup_start:cleanup_end]
if 'Header="Ход очистки"' not in cleanup_slice:
    tail = '                    </TabControl>\n                </Grid>\n            </TabItem>\n\n            '
    rel = cleanup_slice.rfind(tail)
    if rel < 0:
        raise SystemExit('R29 cleanup TabControl tail missing')
    insert_at = cleanup_start + rel
    x = x[:insert_at] + progress_tab + x[insert_at:]
xaml.write_text(x, encoding='utf-8')

final = path.read_text(encoding='utf-8')
xf = xaml.read_text(encoding='utf-8')
if marker not in final:
    raise SystemExit('R29 CleanWithoutBackupAsync definition still missing')
if 'using System.IO;' not in guard.read_text(encoding='utf-8'):
    raise SystemExit('R29 operation guard System.IO import missing')
if 'Command="{Binding CancelCleanupOperationCommand}"' not in xf:
    raise SystemExit('R29 cleanup cancel button missing')
a = xf.find('Text="Аудит системы"'); b = xf.find('Text="Оптимизация"', a)
if a >= 0 and b > a and 'Header="Ход очистки"' in xf[a:b]:
    raise SystemExit('R29 cleanup progress still in Audit')
c = xf.find('Text="Очистка / Debloat"', b)
d = xf.find('<!-- Services + Scheduled Tasks reversible control -->', c)
if c < 0 or d < 0 or 'Header="Ход очистки"' not in xf[c:d]:
    raise SystemExit('R29 cleanup progress not in Cleanup')
print('R29 compile/UI fixes: OK')
