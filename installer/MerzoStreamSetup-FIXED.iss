#define MyAppName "MerzoStream Suite"
#define MyAppPublisher "Merzo4"
#define MyAppURL "https://github.com/Merzo4/my-app-updates"

[Setup]
AppId={{B56A0D35-75CF-4EF4-8F4A-6A13CB8EC1B5}
AppName={#MyAppName}
AppVersion=1.0
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={autopf}\MerzoStreamSuite
DefaultGroupName=MerzoStream Suite
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupArchitecture=x64
WizardStyle=modern
WizardResizable=no
Compression=lzma2
SolidCompression=yes
ArchiveExtraction=full
OutputDir=output
OutputBaseFilename=MerzoStreamSetup
UninstallDisplayName=MerzoStream Suite
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UsePreviousAppDir=yes
AllowNoIcons=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: checkedonce

[Dirs]
Name: "{app}\launcher"
Name: "{app}\versions"
Name: "{app}\shared"

[Files]
Source: "assets\MerzoStreamSuite.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\launcher\BackgroundCheck.ps1"; DestDir: "{app}\launcher"; Flags: ignoreversion
Source: "assets\launcher\MerzoStreamLauncher.ps1"; DestDir: "{app}\launcher"; Flags: ignoreversion
Source: "assets\launcher\Updater5.ps1"; DestDir: "{app}\launcher"; Flags: ignoreversion
Source: "assets\launcher\config.json"; DestDir: "{app}\launcher"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\MerzoStream Suite"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\MerzoStreamLauncher.ps1"""; WorkingDir: "{app}"
Name: "{autodesktop}\MerzoStream Suite"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\MerzoStreamLauncher.ps1"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\MerzoStreamLauncher.ps1"" -NoUpdate"; WorkingDir: "{app}"; Description: "Запустить MerzoStream Suite"; Flags: postinstall nowait skipifsilent runasoriginaluser

[Code]
const
  ChannelUrl = 'https://github.com/Merzo4/my-app-updates/releases/latest/download/MerzoStreamSuite-latest.ini';
  PythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe';
  PythonSHA256 = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb';

var
  DownloadPage: TDownloadWizardPage;
  ReleaseVersion: String;
  ReleaseSHA256: String;
  ReleaseZipURL: String;
  ReleaseZipPath: String;
  PythonInstallerPath: String;
  NeedPython: Boolean;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

function Python312Available: Boolean;
var
  ResultCode: Integer;
  PyLauncher: String;
begin
  Result := False;
  PyLauncher := ExpandConstant('{sys}\py.exe');
  if FileExists(PyLauncher) then
  begin
    if Exec(PyLauncher,
      '-3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Result := ResultCode = 0;
  end;
end;

function ValidReleaseVersion(const Value: String): Boolean;
var
  I: Integer;
begin
  Result := (Value <> '') and (Pos('..', Value) = 0) and (Pos('/', Value) = 0) and (Pos('\\', Value) = 0);
  if Result then
    for I := 1 to Length(Value) do
      if not (Value[I] in ['0'..'9', 'a'..'z', 'A'..'Z', '.']) then
      begin
        Result := False;
        Break;
      end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ChannelPath: String;
  TargetVersionDir: String;
  ManifestPath: String;
  ManifestText: AnsiString;
begin
  Result := '';
  NeedPython := not Python312Available;

  try
    DownloadPage := CreateDownloadPage(
      'Загрузка MerzoStream Suite',
      'Setup скачивает последнюю опубликованную версию и проверяет её целостность.',
      @OnDownloadProgress);
    DownloadPage.ShowBaseNameInsteadOfUrl := True;

    try
      { 1. Download tiny install channel descriptor }
      DownloadPage.Clear;
      DownloadPage.Add(ChannelUrl, 'MerzoStreamSuite-latest.ini', '');
      DownloadPage.Show;
      DownloadPage.Download;
      DownloadPage.Hide;

      ChannelPath := ExpandConstant('{tmp}\MerzoStreamSuite-latest.ini');
      ReleaseVersion := Trim(GetIniString('Release', 'Version', '', ChannelPath));
      ReleaseSHA256 := Lowercase(Trim(GetIniString('Release', 'SHA256', '', ChannelPath)));
      ReleaseZipURL := Trim(GetIniString('Release', 'URL', '', ChannelPath));

      if not ValidReleaseVersion(ReleaseVersion) then
        RaiseException('Некорректная версия в канале установки.');
      if Length(ReleaseSHA256) <> 64 then
        RaiseException('В канале установки отсутствует корректный SHA-256.');
      if ReleaseZipURL = '' then
        RaiseException('В канале установки отсутствует URL пакета.');

      { 2. Download application package and Python when necessary }
      DownloadPage.Clear;
      DownloadPage.Add(ReleaseZipURL, 'MerzoStreamSuite-latest.zip', ReleaseSHA256);
      if NeedPython then
        DownloadPage.Add(PythonUrl, 'python-3.12.10-amd64.exe', PythonSHA256);

      DownloadPage.Show;
      DownloadPage.Download;
      DownloadPage.Hide;

      ReleaseZipPath := ExpandConstant('{tmp}\MerzoStreamSuite-latest.zip');
      PythonInstallerPath := ExpandConstant('{tmp}\python-3.12.10-amd64.exe');

      { 3. Extract immutable version directory }
      TargetVersionDir := AddBackslash(WizardDirValue) + 'versions\\' + ReleaseVersion;
      if DirExists(TargetVersionDir) then
        DelTree(TargetVersionDir, True, True, True);
      ForceDirectories(TargetVersionDir);
      ExtractArchive(ReleaseZipPath, TargetVersionDir, '', True, nil);

      { 4. Sanity check the package identity }
      ManifestPath := AddBackslash(TargetVersionDir) + 'release_manifest.json';
      if not FileExists(ManifestPath) then
        RaiseException('Пакет не содержит release_manifest.json.');
      if not LoadStringFromFile(ManifestPath, ManifestText) then
        RaiseException('Не удалось прочитать release_manifest.json.');
      if Pos('"version": "' + ReleaseVersion + '"', String(ManifestText)) = 0 then
        RaiseException('Версия внутри пакета не совпадает с каналом установки.');

    finally
      if DownloadPage.Visible then
        DownloadPage.Hide;
    end;
  except
    Result := GetExceptionMessage;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
    if NeedPython and (not Python312Available) then
    begin
      WizardForm.StatusLabel.Caption := 'Установка Python 3.12 для MerzoStream Suite...';
      Params := '/quiet InstallAllUsers=1 PrependPath=0 AppendPath=0 Include_launcher=1 ' +
        'InstallLauncherAllUsers=1 Include_test=0 Include_doc=0 Shortcuts=0';

      if not Exec(PythonInstallerPath, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
        RaiseException('Не удалось запустить установщик Python 3.12.');
      if ResultCode <> 0 then
        RaiseException(Format('Установщик Python завершился с кодом %d.', [ResultCode]));
      if not Python312Available then
        RaiseException('Python 3.12 не обнаружен после установки.');
    end;

    WizardForm.StatusLabel.Caption := 'MerzoStream Suite установлен.';
  end;
end;
