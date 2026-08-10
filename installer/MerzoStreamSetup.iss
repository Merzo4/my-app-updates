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

function PythonExeWorks(const ExePath: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if (ExePath = '') or (not FileExists(ExePath)) then
    Exit;

  if Exec(
    ExePath,
    '-c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)"',
    '',
    SW_SHOWNORMAL,
    ewWaitUntilTerminated,
    ResultCode) then
  begin
    Result := ResultCode = 0;
  end;
end;

function PythonFromRegistry(const RootKey: HKEY): String;
var
  InstallPath: String;
  ExePath: String;
begin
  Result := '';

  if RegQueryStringValue(
    RootKey,
    'Software\Python\PythonCore\3.12\InstallPath',
    'ExecutablePath',
    ExePath) then
  begin
    if PythonExeWorks(ExePath) then
    begin
      Result := ExePath;
      Exit;
    end;
  end;

  InstallPath := '';
  if RegQueryStringValue(
    RootKey,
    'Software\Python\PythonCore\3.12\InstallPath',
    '',
    InstallPath) then
  begin
    ExePath := AddBackslash(InstallPath) + 'python.exe';
    if PythonExeWorks(ExePath) then
    begin
      Result := ExePath;
      Exit;
    end;
  end;
end;

function PythonFromLauncher: String;
var
  PyLauncher: String;
  ResultCode: Integer;
  Output: TExecOutput;
  Candidate: String;
begin
  Result := '';
  PyLauncher := ExpandConstant('{win}\py.exe');

  if not FileExists(PyLauncher) then
    Exit;

  try
    if ExecAndCaptureOutput(
      PyLauncher,
      '-3.12 -c "import sys; print(sys.executable)"',
      '',
      SW_SHOWNORMAL,
      ewWaitUntilTerminated,
      ResultCode,
      Output) then
    begin
      if (ResultCode = 0) and (Length(Output.StdOut) > 0) then
      begin
        Candidate := Trim(Output.StdOut[0]);
        if PythonExeWorks(Candidate) then
        begin
          Result := Candidate;
          Exit;
        end;
      end;
    end;
  except
    Log('Python launcher detection failed: ' + GetExceptionMessage);
  end;
end;

function FindPython312Exe: String;
var
  Candidate: String;
begin
  Result := '';

  Candidate := PythonFromRegistry(HKEY_CURRENT_USER);
  if Candidate <> '' then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := PythonFromRegistry(HKEY_LOCAL_MACHINE);
  if Candidate <> '' then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := ExpandConstant('{autopf}\Python312\python.exe');
  if PythonExeWorks(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := ExpandConstant('{localappdata}\Programs\Python\Python312\python.exe');
  if PythonExeWorks(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := PythonFromLauncher;
  if Candidate <> '' then
  begin
    Result := Candidate;
    Exit;
  end;
end;

function Python312Available: Boolean;
begin
  Result := FindPython312Exe <> '';
end;

procedure ExecChecked(
  const ExePath: String;
  const Params: String;
  const WorkingDir: String;
  const ErrorText: String);
var
  ResultCode: Integer;
begin
  if not Exec(
    ExePath,
    Params,
    WorkingDir,
    SW_SHOWNORMAL,
    ewWaitUntilTerminated,
    ResultCode) then
  begin
    RaiseException(
      ErrorText + #13#10 +
      'Windows: ' + SysErrorMessage(ResultCode));
  end;

  if ResultCode <> 0 then
  begin
    RaiseException(
      ErrorText + #13#10 +
      'Код завершения: ' + IntToStr(ResultCode));
  end;
end;

procedure PreparePythonRuntime;
var
  PythonExe: String;
  RuntimeRoot: String;
  RuntimeParent: String;
  VenvPython: String;
  RequirementsPath: String;
  RequirementsHash: String;
  MarkerPath: String;
  MarkerText: AnsiString;
  NeedRequirements: Boolean;
begin
  PythonExe := FindPython312Exe;
  if PythonExe = '' then
    RaiseException('Python 3.12 не найден после установки.');

  Log('Python 3.12 detected: ' + PythonExe);

  RuntimeRoot :=
    ExpandConstant('{localappdata}\MerzoStreamSuite\runtime\py312');
  RuntimeParent := ExtractFileDir(RuntimeRoot);
  VenvPython := AddBackslash(RuntimeRoot) + 'Scripts\python.exe';
  RequirementsPath :=
    AddBackslash(WizardDirValue) +
    'versions\' + ReleaseVersion + '\requirements.txt';
  MarkerPath := AddBackslash(RuntimeRoot) + '.requirements.sha256';

  if not FileExists(RequirementsPath) then
    RaiseException('В установленной версии отсутствует requirements.txt.');

  ForceDirectories(RuntimeParent);

  WizardForm.StatusLabel.Caption :=
    'Подготовка изолированного Python окружения MerzoStream Suite...';

  if not FileExists(VenvPython) then
  begin
    if DirExists(RuntimeRoot) then
      DelTree(RuntimeRoot, True, True, True);

    ExecChecked(
      PythonExe,
      '-m venv "' + RuntimeRoot + '"',
      '',
      'Не удалось создать Python-окружение MerzoStream Suite.');
  end;

  if not FileExists(VenvPython) then
    RaiseException('Python-окружение создано некорректно.');

  RequirementsHash := Lowercase(GetSHA256OfFile(RequirementsPath));
  NeedRequirements := True;

  MarkerText := '';
  if FileExists(MarkerPath) then
  begin
    if LoadStringFromFile(MarkerPath, MarkerText) then
      NeedRequirements :=
        Lowercase(Trim(String(MarkerText))) <> RequirementsHash;
  end;

  if NeedRequirements then
  begin
    WizardForm.StatusLabel.Caption :=
      'Установка компонентов MerzoStream Suite...';

    ExecChecked(
      VenvPython,
      '-m pip install --disable-pip-version-check ' +
      '--no-warn-script-location -r "' + RequirementsPath + '"',
      ExtractFileDir(RequirementsPath),
      'Не удалось установить Python-компоненты MerzoStream Suite.');

    if not SaveStringToFile(
      MarkerPath,
      AnsiString(RequirementsHash),
      False) then
    begin
      RaiseException('Не удалось сохранить состояние Python-компонентов.');
    end;
  end;

  Log('MerzoStream Python runtime is ready: ' + VenvPython);
end;

function IsValidReleaseChar(const C: Char): Boolean;
begin
  Result :=
    ((C >= '0') and (C <= '9')) or
    ((C >= 'a') and (C <= 'z')) or
    ((C >= 'A') and (C <= 'Z')) or
    (C = '.');
end;

function ValidReleaseVersion(const Value: String): Boolean;
var
  I: Integer;
begin
  Result :=
    (Value <> '') and
    (Pos('..', Value) = 0) and
    (Pos('/', Value) = 0) and
    (Pos('\', Value) = 0);

  if Result then
  begin
    for I := 1 to Length(Value) do
    begin
      if not IsValidReleaseChar(Value[I]) then
      begin
        Result := False;
        Break;
      end;
    end;
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

    { 1. Download tiny install channel descriptor }
    DownloadPage.Clear;
    DownloadPage.Add(ChannelUrl, 'MerzoStreamSuite-latest.ini', '');
    DownloadPage.Show;
    try
      DownloadPage.Download;
    finally
      DownloadPage.Hide;
    end;

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
    try
      DownloadPage.Download;
    finally
      DownloadPage.Hide;
    end;

    ReleaseZipPath := ExpandConstant('{tmp}\MerzoStreamSuite-latest.zip');
    PythonInstallerPath := ExpandConstant('{tmp}\python-3.12.10-amd64.exe');

    { 3. Extract immutable version directory }
    TargetVersionDir := AddBackslash(WizardDirValue) + 'versions\' + ReleaseVersion;
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
  except
    Result := GetExceptionMessage;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  PythonExe: String;
begin
  if CurStep = ssPostInstall then
  begin
    PythonExe := FindPython312Exe;

    if PythonExe = '' then
    begin
      WizardForm.StatusLabel.Caption :=
        'Установка Python 3.12 для MerzoStream Suite...';

      Params :=
        '/quiet InstallAllUsers=1 ' +
        'PrependPath=0 AppendPath=0 ' +
        'Include_exe=1 Include_lib=1 Include_pip=1 Include_dev=1 ' +
        'Include_launcher=1 InstallLauncherAllUsers=1 ' +
        'Include_test=0 Include_doc=0 Shortcuts=0';

      if not Exec(
        PythonInstallerPath,
        Params,
        '',
        SW_SHOWNORMAL,
        ewWaitUntilTerminated,
        ResultCode) then
      begin
        RaiseException(
          'Не удалось запустить установщик Python 3.12.' + #13#10 +
          SysErrorMessage(ResultCode));
      end;

      if ResultCode <> 0 then
      begin
        RaiseException(
          'Установщик Python завершился с кодом ' +
          IntToStr(ResultCode) + '.');
      end;

      PythonExe := FindPython312Exe;
      if PythonExe = '' then
      begin
        RaiseException(
          'Python 3.12 установлен, но не удалось определить путь к python.exe.' + #13#10 +
          'Setup проверил реестр PythonCore, C:\Windows\py.exe и стандартные пути.');
      end;
    end;

    PreparePythonRuntime;

    WizardForm.StatusLabel.Caption :=
      'MerzoStream Suite установлен и готов к запуску.';
  end;
end;

