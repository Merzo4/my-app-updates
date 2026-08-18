# CI rerun marker: WebView2 profile must live in writable LocalAppData
import os, pathlib
root = pathlib.Path(os.environ["MERZO_SRC"])
main = root / "src" / "MerzoStream.Host" / "MainForm.cs"
s = main.read_text(encoding="utf-8-sig")
old = '''            _nativeStatus.Text = "MerzoStream Pure .NET\\r\\nИнициализация WebView2…";
            await _webView.EnsureCoreWebView2Async();
            var uiFolder = AppPaths.ActiveUi(_root);
'''
new = '''            _nativeStatus.Text = "MerzoStream Pure .NET\\r\\nИнициализация WebView2…";

            // WebView2 must never create its profile beside the executable. A normal
            // machine-wide install lives under Program Files, which is intentionally
            // read-only for a non-elevated desktop process. Keep all mutable browser
            // profile/cache data in the user's LocalAppData instead.
            var webViewData = Path.Combine(AppPaths.DataDirectory(), "WebView2");
            Directory.CreateDirectory(webViewData);
            var webViewEnvironment = await CoreWebView2Environment.CreateAsync(userDataFolder: webViewData);
            await _webView.EnsureCoreWebView2Async(webViewEnvironment);
            var uiFolder = AppPaths.ActiveUi(_root);
'''
if old not in s:
    raise SystemExit("MainForm WebView2 init marker not found")
s = s.replace(old, new, 1)
oldcatch = '''            LogHostError(ex);
            MessageBox.Show(ex.Message + "\\r\\n\\r\\nЛог: " + Path.Combine(AppPaths.DotNetLogDirectory(), "host.log"), "MerzoStream Pure .NET", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
'''
newcatch = '''            LogHostError(ex);
            ShowDarkStartupError(ex.Message + "\\r\\n\\r\\nЛог: " + Path.Combine(AppPaths.DotNetLogDirectory(), "host.log"));
        }
    }

    private void ShowDarkStartupError(string message)
    {
        try
        {
            using var dialog = new Form
            {
                Text = "MerzoStream Suite — ошибка запуска",
                StartPosition = FormStartPosition.CenterScreen,
                FormBorderStyle = FormBorderStyle.FixedDialog,
                MaximizeBox = false,
                MinimizeBox = false,
                ShowInTaskbar = false,
                BackColor = Color.FromArgb(7, 11, 18),
                ForeColor = Color.FromArgb(233, 241, 249),
                ClientSize = new Size(620, 250)
            };

            var title = new Label
            {
                Text = "MERZOSTREAM SUITE  •  ОШИБКА ЗАПУСКА",
                ForeColor = Color.FromArgb(34, 211, 238),
                Font = new Font("Segoe UI Semibold", 12F, FontStyle.Bold),
                AutoSize = false,
                Location = new Point(24, 20),
                Size = new Size(570, 30)
            };
            var body = new Label
            {
                Text = message,
                ForeColor = Color.FromArgb(203, 213, 225),
                Font = new Font("Segoe UI", 9.5F),
                AutoEllipsis = true,
                Location = new Point(24, 62),
                Size = new Size(570, 120)
            };
            var ok = new Button
            {
                Text = "ПОНЯТНО",
                DialogResult = DialogResult.OK,
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(8, 145, 178),
                ForeColor = Color.White,
                Location = new Point(444, 198),
                Size = new Size(150, 34),
                Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold)
            };
            ok.FlatAppearance.BorderColor = Color.FromArgb(34, 211, 238);
            dialog.Controls.Add(title);
            dialog.Controls.Add(body);
            dialog.Controls.Add(ok);
            dialog.AcceptButton = ok;
            dialog.ShowDialog(this);
        }
        catch { }
    }
'''
if oldcatch not in s:
    raise SystemExit("MainForm startup error marker not found")
s = s.replace(oldcatch, newcatch, 1)
main.write_text(s, encoding="utf-8", newline="\r\n")

notes = root / "RELEASE_NOTES_0.1.0n.md"
nt = notes.read_text(encoding="utf-8-sig")
section = '''\n## Installer R3 — Program Files WebView2 fix\n- WebView2 profile/cache moved out of `Program Files` into `%LOCALAPPDATA%\\MerzoStreamSuite\\0.1.0-dotnet\\WebView2`.\n- MerzoStream no longer requires write access inside its installation directory after setup.\n- Startup errors now use a branded dark MerzoStream dialog instead of a white Windows message box.\n'''
if "## Installer R3 — Program Files WebView2 fix" not in nt:
    notes.write_text(nt.rstrip()+"\n"+section, encoding="utf-8", newline="\n")
print("0.1.0n INSTALLER R3 APPLY PASS: WebView2 user profile -> LocalAppData + dark startup errors")
