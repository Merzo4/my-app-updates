from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')
s=s.replace('OnPropertyChanged(nameof(CleanupProgressText));','RaisePropertyChanged(nameof(CleanupProgressText));')
s=s.replace('result.SnapshotId?.ToString("N")[..8]', 'result.SnapshotId is Guid cleanupSnapshotId ? cleanupSnapshotId.ToString("N")[..8] : "—"')
vm.write_text(s,encoding='utf-8')
print('R28 compile compatibility fix: OK')
