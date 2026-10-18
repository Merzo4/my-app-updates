using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Microsoft.Win32;
using WinFormsTimer = System.Windows.Forms.Timer;

namespace MerzoOptimizer.TestCenter;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        var smoke = args.Contains("--smoke-test", StringComparer.OrdinalIgnoreCase);
        try
        {
            using var mutex = new Mutex(true, "MerzoOptimizerLocalTestCenter", out bool created);
            if (!created)
            {
                if (smoke) return 20;
                MessageBox.Show("Merzo Optimizer Test Center уже запущен.", "Merzo Optimizer Test Center",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 20;
            }
            try
            {
                using var form = new LabForm(smoke);
                Application.Run(form);
                return form.ExitCode;
            }
            finally
            {
                try { mutex.ReleaseMutex(); } catch (ApplicationException) { }
            }
        }
        catch (Exception ex)
        {
            var lab = Environment.GetEnvironmentVariable("MWO_LAB_ROOT") ?? @"D:\MerzoOptimizer-LocalLab";
            try
            {
                Directory.CreateDirectory(Path.Combine(lab, "Logs"));
                File.WriteAllText(Path.Combine(lab, "Logs", "native-gui-error.log"), ex.ToString());
            }
            catch { /* fallback to message */ }
            if (!smoke) MessageBox.Show(ex.Message, "Test Center — ошибка запуска", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}

internal sealed class LabForm : Form
{
    private readonly string _root = Environment.GetEnvironmentVariable("MWO_LAB_ROOT") ?? @"D:\MerzoOptimizer-LocalLab";
    private readonly string _app;
    private readonly string _runner;
    private readonly string _log;
    private readonly string _result;
    private readonly string _source;
    private readonly string _pwsh;
    private readonly bool _smoke;
    private readonly WinFormsTimer _timer = new() { Interval = 600 };
    private readonly List<Button> _actionButtons = [];
    private readonly Button _destructive;
    private readonly Button _stop;
    private readonly Label _autoReportStatus;
    private readonly Button _retryReport;
    private readonly Label _status;
    private readonly Label _environment;
    private readonly Label _sourceLabel;
    private readonly Label _safetyLabel;
    private readonly Label _resultLabel;
    private readonly RichTextBox _journal;
    private readonly ListView _checks;
    private Process? _running;
    private long _logOffset;
    private bool _busy;
    private bool _closeRequested;
    private bool _currentActionIsProfile;
    private string _version = "0.2.3";
    private string _targetBranch = "mwo-r57-safe-background-actions";
    public int ExitCode { get; private set; }

    private static readonly Color Background = Color.FromArgb(8, 20, 28);
    private static readonly Color Panel = Color.FromArgb(13, 34, 43);
    private static readonly Color PanelAlt = Color.FromArgb(18, 44, 54);
    private static readonly Color Foreground = Color.FromArgb(230, 240, 242);
    private static readonly Color Muted = Color.FromArgb(137, 163, 169);
    private static readonly Color Accent = Color.FromArgb(70, 188, 177);
    private static readonly Color Green = Color.FromArgb(76, 196, 147);
    private static readonly Color Red = Color.FromArgb(225, 88, 88);
    private static readonly Color Amber = Color.FromArgb(227, 174, 73);

    public LabForm(bool smoke)
    {
        _smoke = smoke;
        _app = Path.Combine(_root, "App");
        _runner = Path.Combine(_app, "Run-Profile.ps1");
        _log = Path.Combine(_root, "Logs", "Current.log");
        _result = Path.Combine(_root, "Results", "Latest", "LAB-RESULT.json");
        _source = Path.Combine(_root, "Source");
        _pwsh = @"C:\Program Files\PowerShell\7\pwsh.exe";

        if (!File.Exists(_runner) || !File.Exists(_pwsh))
            throw new FileNotFoundException("Test Center requires Run-Profile.ps1 and PowerShell 7.");
        string profile = Path.Combine(_app, "local-lab-profile.json");
        if (File.Exists(profile))
        {
            using JsonDocument doc = JsonDocument.Parse(File.ReadAllText(profile));
            if (doc.RootElement.TryGetProperty("testCenterVersion", out var v))
                _version = v.GetString() ?? _version;
            if (doc.RootElement.TryGetProperty("targetBranch", out var b))
                _targetBranch = b.GetString() ?? _targetBranch;
        }

        Text = "Merzo Optimizer Local Test Center";
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(1040, 640);
        MinimumSize = new Size(1040, 640);
        MaximizeBox = true;
        BackColor = Background;
        ForeColor = Foreground;
        Font = new Font("Segoe UI", 9f);
        DoubleBuffered = true;

        var top = new Panel { Bounds = new Rectangle(0, 0, 1040, 60), BackColor = Color.FromArgb(7, 25, 33), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
        Controls.Add(top);
        top.Controls.Add(new Label { Text = "MERZO OPTIMIZER  •  LOCAL TEST CENTER",
            ForeColor = Foreground, Font = new Font("Segoe UI Semibold", 15),
            AutoSize = true, Location = new Point(18, 8) });
        top.Controls.Add(new Label { Text = "Нативная оболочка EXE  •  локальные проверки и автоотчёты  •  v" + _version,
            ForeColor = Muted, AutoSize = true, Location = new Point(20, 36) });
        _status = new Label { Text = "ГОТОВ", ForeColor = Accent, BackColor = PanelAlt,
            TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(900, 15, 120, 30), Anchor = AnchorStyles.Right | AnchorStyles.Top };
        top.Controls.Add(_status);

        var nav = new Panel { Bounds = new Rectangle(0, 60, 205, 580), BackColor = Color.FromArgb(9, 27, 35), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Bottom };
        Controls.Add(nav);
        nav.Controls.Add(new Label { Text = "ПРОФИЛИ", AutoSize = true, ForeColor = Muted, Location = new Point(14, 14) });

        Button MakeButton(string caption, int y, Color color, Action onClick, bool track = true)
        {
            var button = new Button
            {
                Text = caption, Bounds = new Rectangle(12, y, 178, 35),
                BackColor = Panel, ForeColor = color, FlatStyle = FlatStyle.Flat,
                Cursor = Cursors.Hand, TabStop = true
            };
            button.FlatAppearance.BorderColor = Color.FromArgb(35, 91, 99);
            button.Click += (_, _) => onClick();
            nav.Controls.Add(button);
            if (track) _actionButtons.Add(button);
            return button;
        }

        MakeButton("Диагностика", 40, Foreground, () => StartProfile("Diagnostics"));
        MakeButton("Обновить Source", 79, Foreground, () => StartProfile("Sync"));
        MakeButton("QUICK", 128, Accent, () => StartProfile("Quick"));
        MakeButton("FULL SAFE", 167, Green, () => StartProfile("FullSafe"));
        _destructive = MakeButton("GAME → RESTORE", 216, Red, RunDestructive, false);
        MakeButton("Открыть тестовую", 265, Foreground, () =>
        {
            string exe = Path.Combine(_root, "TestBuild", "Current", "App", "MerzoWindowsOptimizer.exe");
            if (!File.Exists(exe)) { MessageBox.Show("Нет TestBuild\\Current. Сначала запусти FULL SAFE.", "Test Center"); return; }
            Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(exe)! });
        });
        MakeButton("Открыть результаты", 304, Foreground, () => OpenFolder(Path.Combine(_root, "Results", "Latest")));
        MakeButton("Собрать evidence", 343, Foreground, () => StartUtility("PACK-EVIDENCE.ps1"));
        _autoReportStatus = new Label
        {
            Text = "АВТООТЧЁТ: проверка...",
            ForeColor = Muted, BackColor = Panel,
            Bounds = new Rectangle(12, 380, 178, 36),
            TextAlign = ContentAlignment.MiddleCenter
        };
        nav.Controls.Add(_autoReportStatus);
        _retryReport = MakeButton("Повторить отправку", 416, Amber,
            () => StartUtility("PUBLISH-EVIDENCE.ps1", "-FlushQueue"), false);
        _retryReport.Bounds = new Rectangle(12, 416, 178, 25);
        _retryReport.Visible = false;
        MakeButton("Открыть D:\\ Lab", 445, Foreground, () => OpenFolder(_root));
        _stop = MakeButton("Остановить", 487, Amber, StopProfile, false);
        _stop.Enabled = false;
        nav.Controls.Add(new Label { Text = "PROTECTED • GAME BLOCKED", ForeColor = Green,
            Bounds = new Rectangle(12, 529, 178, 38), BackColor = Panel, TextAlign = ContentAlignment.MiddleLeft });

        var main = new Panel { Bounds = new Rectangle(205, 60, 835, 580), BackColor = Background,
            Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top | AnchorStyles.Bottom };
        Controls.Add(main);
        Label MakeCard(string caption, int x, int width)
        {
            var p = new Panel { Bounds = new Rectangle(x, 12, width, 78), BackColor = Panel, Anchor = AnchorStyles.Top };
            main.Controls.Add(p);
            p.Controls.Add(new Label { Text = caption, ForeColor = Muted, AutoSize = true, Location = new Point(10, 8) });
            var value = new Label { Text = "—", ForeColor = Foreground,
                Font = new Font("Segoe UI Semibold", 9.5f),
                Bounds = new Rectangle(10, 29, width - 20, 43) };
            p.Controls.Add(value);
            return value;
        }
        _environment = MakeCard("СРЕДА", 14, 175);
        _sourceLabel = MakeCard("SOURCE", 199, 235);
        _safetyLabel = MakeCard("БЕЗОПАСНОСТЬ", 444, 175);
        _resultLabel = MakeCard("ПОСЛЕДНИЙ РЕЗУЛЬТАТ", 629, 192);
        main.Controls.Add(new Label { Text = "ЖУРНАЛ", ForeColor = Muted,
            AutoSize = true, Location = new Point(14, 102) });
        _journal = new RichTextBox
        {
            Bounds = new Rectangle(14, 123, 807, 245), ReadOnly = true,
            BackColor = Color.FromArgb(6, 18, 24), ForeColor = Foreground,
            BorderStyle = BorderStyle.None, Font = new Font("Consolas", 9)
        };
        main.Controls.Add(_journal);
        main.Controls.Add(new Label { Text = "ПРОВЕРКИ", ForeColor = Muted,
            AutoSize = true, Location = new Point(14, 382) });
        _checks = new ListView
        {
            View = View.Details, FullRowSelect = true,
            Bounds = new Rectangle(14, 403, 807, 160), BackColor = Color.FromArgb(7, 22, 29),
            ForeColor = Foreground, BorderStyle = BorderStyle.None
        };
        _checks.Columns.Add("Статус", 85);
        _checks.Columns.Add("Проверка", 225);
        _checks.Columns.Add("Результат", 470);
        main.Controls.Add(_checks);

        Shown += (_, _) =>
        {
            RefreshCards();
            RefreshAutoReportStatus();
            if (!_smoke)
            {
                try
                {
                    Directory.CreateDirectory(Path.Combine(_root, "State"));
                    File.WriteAllText(Path.Combine(_root, "State", "native-gui-shown.json"),
                        JsonSerializer.Serialize(new { visible = Visible, version = _version, pid = Environment.ProcessId, at = DateTimeOffset.UtcNow }));
                }
                catch (Exception ex) { Debug.WriteLine(ex); }
            }
            if (_smoke)
            {
                Console.WriteLine("LOCAL_NATIVE_TEST_CENTER_SMOKE_PASS");
                ExitCode = 0;
                BeginInvoke(Close);
            }
            else _timer.Start();
        };
        _timer.Tick += (_, _) => Poll();
        FormClosing += OnClosing;
    }

    private void OpenFolder(string folder)
    {
        Directory.CreateDirectory(folder);
        Process.Start(new ProcessStartInfo("explorer.exe", $"\"{folder}\"") { UseShellExecute = true });
    }

    private string OsLabel()
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion");
            var build = int.TryParse(key?.GetValue("CurrentBuildNumber")?.ToString(), out int n)
                ? n : Environment.OSVersion.Version.Build;
            string family = build >= 22000 ? "Windows 11" : "Windows 10";
            string edition = key?.GetValue("EditionID")?.ToString() ?? "";
            string suffix = edition.StartsWith("Professional", StringComparison.OrdinalIgnoreCase) ? " Pro" :
                edition.StartsWith("Core", StringComparison.OrdinalIgnoreCase) ? " Home" :
                edition.StartsWith("Enterprise", StringComparison.OrdinalIgnoreCase) ? " Enterprise" :
                edition.StartsWith("Education", StringComparison.OrdinalIgnoreCase) ? " Education" : "";
            string release = key?.GetValue("DisplayVersion")?.ToString() ?? "";
            var ubr = key?.GetValue("UBR")?.ToString();
            return $"{family}{suffix}\n{release} • {build}{(string.IsNullOrWhiteSpace(ubr) ? "" : "." + ubr)}";
        }
        catch
        {
            return $"Windows (NT {Environment.OSVersion.Version})";
        }
    }

    private void RefreshCards()
    {
        _environment.Text = OsLabel();
        _sourceLabel.Text = Directory.Exists(Path.Combine(_source, ".git"))
            ? GetSourceIdentity() : "Source ещё не подготовлен";
        _safetyLabel.Text = IsArmed() ? "LAB ONLY\nSYSTEM MUTATION: ARMED" : "PROTECTED\nSystem mutation blocked";
        _safetyLabel.ForeColor = IsArmed() ? Red : Green;
        _destructive.Enabled = !_busy && IsArmed();
        if (File.Exists(_result))
        {
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(_result));
                var root = doc.RootElement;
                var status = GetProp(root, "conclusion");
                var profile = GetProp(root, "profile");
                var sha = GetProp(root, "sourceCommit");
                _resultLabel.Text = $"{status} • {profile}\n{(sha.Length > 10 ? sha[..10] : (sha.Length == 0 ? "no-source" : sha))}";
                _resultLabel.ForeColor = status == "PASS" ? Green : Red;
            }
            catch { _resultLabel.Text = "Ошибка чтения результата"; }
        }
        else { _resultLabel.Text = "Нет запусков"; _resultLabel.ForeColor = Muted; }
    }

    // The report result (PASS/FAIL) and its delivery status are separate concepts.
    // This indicator is sourced from the backend's persisted upload receipt and queue.
    private void RefreshAutoReportStatus()
    {
        try
        {
            int pending = 0;
            var queue = Path.Combine(_root, "State", "EvidenceQueue");
            if (Directory.Exists(queue))
                pending = Directory.EnumerateFiles(queue, "*.json", SearchOption.TopDirectoryOnly).Count();
            string state = "";
            string when = "";
            var statusPath = Path.Combine(_root, "State", "EvidencePublishStatus.json");
            if (File.Exists(statusPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(statusPath));
                state = GetProp(doc.RootElement, "state");
                when = GetProp(doc.RootElement, "updatedAt");
            }

            bool recentlySending = false;
            if (state == "SENDING" &&
                DateTimeOffset.TryParse(when, CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal, out var stamped))
                recentlySending = (DateTimeOffset.UtcNow - stamped).TotalMinutes < 2;

            _retryReport.Visible = false;
            if (_busy && _currentActionIsProfile)
            {
                _autoReportStatus.Text = "АВТООТЧЁТ\nпосле проверки";
                _autoReportStatus.ForeColor = Muted;
            }
            else if (recentlySending || (_busy && !_currentActionIsProfile))
            {
                _autoReportStatus.Text = "АВТООТЧЁТ\nотправляется...";
                _autoReportStatus.ForeColor = Amber;
            }
            else if (pending > 0 || state == "DEFERRED" || state == "SENDING")
            {
                _autoReportStatus.Text = "АВТООТЧЁТ\nв очереди: " + pending;
                _autoReportStatus.ForeColor = Amber;
                _retryReport.Visible = pending > 0;
                _retryReport.Enabled = pending > 0 && !_busy;
            }
            else if (state == "PUBLISHED")
            {
                _autoReportStatus.Text = "АВТООТЧЁТ\n✓ отправлено в GitHub";
                _autoReportStatus.ForeColor = Green;
            }
            else
            {
                _autoReportStatus.Text = "АВТООТЧЁТ\nожидает проверки";
                _autoReportStatus.ForeColor = Muted;
            }
        }
        catch (IOException) { /* State file may be mid-write; retry on next timer tick. */ }
        catch (UnauthorizedAccessException) { _autoReportStatus.Text = "АВТООТЧЁТ\nнет доступа к статусу"; _autoReportStatus.ForeColor = Red; }
        catch (JsonException) { _autoReportStatus.Text = "АВТООТЧЁТ\nчтение статуса..."; _autoReportStatus.ForeColor = Amber; }
    }

    private string GetSourceIdentity()
    {
        try
        {
            var head = File.ReadAllText(Path.Combine(_source, ".git", "HEAD")).Trim();
            var branch = head.StartsWith("ref: refs/heads/", StringComparison.Ordinal) ? head["ref: refs/heads/".Length..] : _targetBranch;
            string? sha = null;
            if (head.StartsWith("ref:", StringComparison.Ordinal))
            {
                var path = Path.Combine(_source, ".git", head[5..].Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(path)) sha = File.ReadAllText(path).Trim();
            }
            else sha = head;
            return $"{branch}\n{(sha is { Length: >= 10 } ? sha[..10] : "see Source")}";
        }
        catch { return _targetBranch + "\nSource"; }
    }

    private bool IsArmed()
    {
        try
        {
            var path = Path.Combine(_root, "State", "ALLOW-SYSTEM-MUTATION.json");
            if (!File.Exists(path)) return false;
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var root = doc.RootElement;
            return root.TryGetProperty("labOnly", out var lab) && lab.GetBoolean() &&
                root.TryGetProperty("machineName", out var machine) &&
                string.Equals(machine.GetString(), Environment.MachineName, StringComparison.OrdinalIgnoreCase);
        }
        catch { return false; }
    }

    private static string GetProp(JsonElement element, string name) =>
        element.TryGetProperty(name, out var p) ? p.ToString() : "";

    private void StartProfile(string profile, bool elevate = false)
    {
        if (_busy) return;
        _currentActionIsProfile = true;
        StartPwsh(Path.Combine(_app, "Run-Profile.ps1"),
            $"-Profile {profile}", elevate);
    }

    private void StartUtility(string script, string args = "")
    {
        if (_busy) return;
        var path = Path.Combine(_app, script);
        if (!File.Exists(path)) { MessageBox.Show($"Файл не найден: {path}"); return; }
        _currentActionIsProfile = false;
        StartPwsh(path, args, false);
    }

    private static string Quote(string s) => "\"" + s.Replace("\"", "\\\"") + "\"";

    private void StartPwsh(string script, string args, bool elevate)
    {
        _journal.Clear();
        _checks.Items.Clear();
        _logOffset = 0;
        SetBusy(true);
        var psi = new ProcessStartInfo(_pwsh,
            $"-NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File {Quote(script)} {args}")
        {
            WorkingDirectory = _app,
            UseShellExecute = elevate,
            CreateNoWindow = !elevate,
            WindowStyle = ProcessWindowStyle.Hidden
        };
        if (elevate) psi.Verb = "runas";
        try
        {
            _running = Process.Start(psi) ?? throw new InvalidOperationException("Unable to start PowerShell backend");
        }
        catch (Exception ex)
        {
            SetBusy(false, "FAIL");
            MessageBox.Show(ex.Message, "Test Center — ошибка запуска", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void RunDestructive()
    {
        if (!IsArmed() || _busy) return;
        var answer = MessageBox.Show("Этот профиль применит GAME-настройки и затем RestoreAll. Только на выделенной лабораторной Windows. Продолжить?",
            "DESTRUCTIVE LAB", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
        if (answer == DialogResult.Yes) StartProfile("Destructive", true);
    }

    private void StopProfile()
    {
        if (_running == null) return;
        if (MessageBox.Show("Остановить выполняемую проверку?", "Test Center", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
            return;
        try { if (!_running.HasExited) _running.Kill(entireProcessTree: true); } catch { }
        _running.Dispose(); _running = null;
        SetBusy(false, "STOPPED");
    }

    private void SetBusy(bool busy, string status = "")
    {
        _busy = busy;
        foreach (var button in _actionButtons) button.Enabled = !busy;
        _destructive.Enabled = !busy && IsArmed();
        _stop.Enabled = busy;
        _status.Text = busy ? "RUNNING" : string.IsNullOrWhiteSpace(status) ? "ГОТОВ" : status;
        _status.ForeColor = busy ? Amber : status == "PASS" ? Green : status == "FAIL" ? Red : Accent;
        RefreshAutoReportStatus();
    }

    private void Poll()
    {
        try
        {
            if (File.Exists(_log))
            {
                using var stream = new FileStream(_log, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                if (stream.Length < _logOffset) _logOffset = 0;
                if (stream.Length > _logOffset)
                {
                    stream.Seek(_logOffset, SeekOrigin.Begin);
                    byte[] bytes = new byte[(int)Math.Min(16384, stream.Length - _logOffset)];
                    int count = stream.Read(bytes, 0, bytes.Length);
                    if (count > 0)
                    {
                        _logOffset += count;
                        _journal.AppendText(Encoding.UTF8.GetString(bytes, 0, count));
                        if (_journal.TextLength > 120000) _journal.Text = _journal.Text[^80000..];
                        _journal.SelectionStart = _journal.TextLength;
                        _journal.ScrollToCaret();
                    }
                }
            }
            RefreshAutoReportStatus();
            if (_running is { HasExited: true })
            {
                int code = _running.ExitCode;
                _running.Dispose();
                _running = null;
                if (_currentActionIsProfile) LoadResult(code);
                else RefreshCards();
                SetBusy(false, code == 0 ? (_currentActionIsProfile ? "PASS" : "DONE") : "FAIL");
            }
        }
        catch (IOException) { }
        catch (Exception ex)
        {
            _status.Text = "WARN";
            _status.ForeColor = Amber;
            Debug.WriteLine(ex);
        }
    }

    private void LoadResult(int exitCode)
    {
        _checks.Items.Clear();
        if (!File.Exists(_result)) { RefreshCards(); return; }
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(_result));
            foreach (var stage in doc.RootElement.GetProperty("stages").EnumerateArray())
            {
                var state = GetProp(stage, "state");
                var item = new ListViewItem(state) { ForeColor = state == "PASS" ? Green : state == "FAIL" ? Red : Foreground };
                item.SubItems.Add(GetProp(stage, "name"));
                item.SubItems.Add(GetProp(stage, "summary"));
                _checks.Items.Add(item);
            }
        }
        catch (Exception ex) { _journal.AppendText("\nUnable to parse result: " + ex.Message); }
        RefreshCards();
    }

    private void OnClosing(object? sender, FormClosingEventArgs e)
    {
        if (_busy && !_closeRequested)
        {
            if (MessageBox.Show("Проверка ещё выполняется. Закрыть GUI и остановить её?",
                "Test Center", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
            {
                e.Cancel = true; return;
            }
            _closeRequested = true;
            try { if (_running is { HasExited: false }) _running.Kill(entireProcessTree: true); } catch { }
        }
        _timer.Stop();
        try { File.Delete(Path.Combine(_root, "State", "native-gui-shown.json")); } catch { }
        _running?.Dispose();
    }
}
