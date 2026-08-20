$ErrorActionPreference='Stop'
$Repo=(Resolve-Path '.').Path
$Work=Join-Path $Repo 'r48v4'
if(Test-Path $Work){Remove-Item $Work -Recurse -Force}

# Restore immutable R21 source archive.
$parts=Get-ChildItem (Join-Path $Repo 'optimizer/source-min/R21.part*')|Sort-Object Name
if($parts.Count-ne29){throw "Source parts missing: $($parts.Count)"}
$b=[Text.StringBuilder]::new();foreach($p in $parts){[void]$b.Append(((Get-Content $p.FullName -Raw)-replace '\s',''))}
$archive=Join-Path $Repo 'r48v4.tar.xz';[IO.File]::WriteAllBytes($archive,[Convert]::FromBase64String($b.ToString()))
$srcSha=(Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if($srcSha-ne'ce9ca7f8f44464c42165e0a79f3053062dfbe2e0df6b0b8517d1ac7510070d2d'){throw "Source SHA mismatch $srcSha"}
New-Item -ItemType Directory -Force $Work|Out-Null;tar -xf $archive -C $Work
$sln=Get-ChildItem $Work -Recurse -Filter MerzoWindowsOptimizer.sln|Select-Object -First 1
if(-not$sln){throw 'Solution missing'}
$root=$sln.Directory.FullName;$env:SOURCE_ROOT=$root

# Production SelfTest feed contract conversion inherited from current production line.
$self=Join-Path $root 'src\MerzoOptimizer.SelfTest\Program.cs';$s=Get-Content $self -Raw
$s=$s.Replace('"releases/latest", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals"','"releases?per_page=50", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals"')
$old='if (!string.IsNullOrWhiteSpace(owner) || !string.IsNullOrWhiteSpace(repo)) failures.Add("Release feed should remain intentionally unconfigured in transferable DEV package.");'
$new='var prefix = root.TryGetProperty("release_tag_prefix", out var prefixEl) ? prefixEl.GetString() : null; var assetName = root.TryGetProperty("asset_name_contains", out var assetEl) ? assetEl.GetString() : null; if (!string.Equals(owner, "Merzo4", StringComparison.Ordinal) || !string.Equals(repo, "my-app-updates", StringComparison.Ordinal)) failures.Add("Production release feed must be Merzo4/my-app-updates."); if (!string.Equals(prefix, "mwo-v", StringComparison.Ordinal)) failures.Add("Production release tag prefix must be mwo-v."); if (!string.Equals(assetName, "MerzoWindowsOptimizerSetup-win-x64.exe", StringComparison.Ordinal)) failures.Add("Production installer asset name is incorrect.");'
if($s.Contains($old)){$s=$s.Replace($old,$new)};Set-Content $self $s -Encoding UTF8

$patches=@('r24_update_center.py','r24_compile_fix.py','r26_ota_repair.py','r27_privacy_engine.py','r28_profiles_updates_cleanup_ux.py','r29_operation_center.py','r29_compile_fix.py','r30_major_update.py','r30_policy_fix.py','r31_audit_memory.py','r32_performance_engine.py','r33_stability_hotfix.py','r34_ultra_process_feedback.py','r34_task_extension.py','r35_readability_ui.py','r36_gaming_ui_polish.py','r37_operation_ui.py','r37_network_center.py','r37_finalize.py','r38_gaming_catalog.py','r38_gaming_network.py','r38_gaming_ui.py','r38_finalize.py','r39_gaming_build_catalog.py','r39_gaming_build_engine.py','r39_gaming_build_ui.py','r39_finalize.py','r40_network_binding_hotfix.py','r42_full_ui_rework.py','r42_window_contract_fix.py','r43_true_full_ui.py','r44_function_expansion.py','r44_finalize.py','r45_apply_selected_ux.py','r46_security_layout_hardening.py','r46_binding_finalize.py','r47_simple_builds.py','r47_finalize.py','r48_ota_reliability_wrapper.py')
foreach($name in $patches){python (Join-Path $Repo "optimizer/patches/$name");if($LASTEXITCODE-ne0){throw "Patch failed: $name"}}

# Fail-closed source gates before any binary build.
$updater=Join-Path $root 'src\MerzoOptimizer.Windows\Updates\GitHubUpdateService.cs'
$updaterSha=(Get-FileHash $updater -Algorithm SHA256).Hash.ToLowerInvariant()
if($updaterSha-ne'836cb4c90b787c7601032ed657584b28b9c170a6ead413f8427bc96d9faf3bb3'){throw "Updater payload SHA mismatch $updaterSha"}
$u=Get-Content $updater -Raw
foreach($token in @('ResolveBestReleaseAsync','GetJsonWithRetryAsync','releases?per_page=20','matching-refs/tags','releases/tags/','tags?per_page=100','HttpStatusCode.GatewayTimeout','HttpStatusCode.BadGateway','HttpStatusCode.ServiceUnavailable','(HttpStatusCode)429','TimeSpan.FromSeconds(45)','OfficialOwner = "Merzo4"','OfficialRepository = "my-app-updates"','OfficialInstallerName = "MerzoWindowsOptimizerSetup-win-x64.exe"','FixedTimeShaEquals','ParseSidecarSha256','IsOfficialReleaseAssetUrl')){if(-not$u.Contains($token)){throw "Updater gate missing: $token"}}
$x=Get-Content (Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml') -Raw
foreach($token in @('Production 0.1.48','Production R48','Сборки Windows','Экспертные инструменты','ПРОВЕРКА СИСТЕМЫ ГОТОВА','Установить сборку')){if(-not$x.Contains($token)){throw "UI regression: $token"}}
foreach($i in 0..11){if(-not$x.Contains("x:Name=`"PageRoot$i`"")){throw "PageRoot$i missing"}}
foreach($p in Get-ChildItem (Join-Path $root 'src') -Recurse -Filter *.csproj){$z=Get-Content $p.FullName -Raw;if($z-match'<AssemblyVersion>([^<]+)</AssemblyVersion>'-and$Matches[1]-ne'0.1.48.0'){throw "$($p.Name) assembly $($Matches[1])"}}

# Build-Production includes Core SelfTest. Obfuscation stays disabled.
Push-Location $root
try{& .\build\Build-Production.ps1 -Version '0.1.48' -SkipObfuscation;if($LASTEXITCODE-ne0){throw 'Production build failed'}}finally{Pop-Location}
$dist=Join-Path $root 'dist\app'
foreach($name in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){$p=Join-Path $dist $name;if(-not(Test-Path $p)){throw "Missing $name"};$v=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString();if($v-ne'0.1.48.0'){throw "$name version $v"}}
if(Get-ChildItem $dist -Recurse -File|?{$_.Name-match'Obfuscar'}){throw 'Obfuscar artifact detected'}

# Deterministic reproduction: old 0.1.45 client sees 504 three times, then R48 fallback must find exact mwo-v tag.
$smoke=Join-Path $env:RUNNER_TEMP 'r48-504-smoke';New-Item -ItemType Directory -Force $smoke|Out-Null
$wp=[Security.SecurityElement]::Escape((Join-Path $root 'src\MerzoOptimizer.Windows\MerzoOptimizer.Windows.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><AssemblyVersion>0.1.45.0</AssemblyVersion><FileVersion>0.1.45.0</FileVersion></PropertyGroup><ItemGroup><ProjectReference Include="$wp" /></ItemGroup></Project>
"@|Set-Content (Join-Path $smoke 'Smoke.csproj') -Encoding UTF8
@'
using System.Net;using System.Text;using MerzoOptimizer.Windows.Updates;
sealed class F:HttpMessageHandler{public int N;protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage q,CancellationToken c){var u=q.RequestUri!.AbsoluteUri;if(u.Contains("/releases?per_page=20")){N++;return R(HttpStatusCode.GatewayTimeout,"{}");}if(u.Contains("/git/matching-refs/tags/mwo-v"))return R(HttpStatusCode.OK,"[{\"ref\":\"refs/tags/mwo-v0.1.48\"}]");if(u.Contains("/releases/tags/mwo-v0.1.48")){var h=new string('a',64);return R(HttpStatusCode.OK,"{\"tag_name\":\"mwo-v0.1.48\",\"draft\":false,\"prerelease\":false,\"name\":\"R48\",\"assets\":[{\"name\":\"MerzoWindowsOptimizerSetup-win-x64.exe\",\"browser_download_url\":\"https://github.com/Merzo4/my-app-updates/releases/download/mwo-v0.1.48/MerzoWindowsOptimizerSetup-win-x64.exe\",\"digest\":\"sha256:"+h+"\",\"size\":12345},{\"name\":\"MerzoWindowsOptimizerSetup-win-x64.exe.sha256\",\"browser_download_url\":\"https://github.com/Merzo4/my-app-updates/releases/download/mwo-v0.1.48/MerzoWindowsOptimizerSetup-win-x64.exe.sha256\",\"size\":106}]}");}return R(HttpStatusCode.NotFound,"{}");}static Task<HttpResponseMessage> R(HttpStatusCode s,string j)=>Task.FromResult(new HttpResponseMessage(s){Content=new StringContent(j,Encoding.UTF8,"application/json")});}
var dir=Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);var sp=Path.Combine(dir,"update_settings.json");File.WriteAllText(sp,"{\"auto_check\":true,\"auto_download\":false,\"auto_install\":false,\"provider\":\"GitHub\",\"repository_owner\":\"Merzo4\",\"repository_name\":\"my-app-updates\",\"release_tag_prefix\":\"mwo-v\",\"asset_name_contains\":\"MerzoWindowsOptimizerSetup-win-x64.exe\",\"installer_silent_args\":\"/SILENT\"}");var f=new F();using var svc=new GitHubUpdateService(sp,Path.Combine(dir,"updates"),f);var r=await svc.CheckAsync();if(!r.Success||!r.UpdateAvailable||r.LatestVersion!="0.1.48"||f.N!=3)throw new Exception($"Fallback failed: success={r.Success} latest={r.LatestVersion} calls={f.N} msg={r.Message}");Console.WriteLine("R48_R45_504_FALLBACK_PASS");
'@|Set-Content (Join-Path $smoke 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $smoke 'Smoke.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R45 504 fallback runtime smoke failed'}

# Finished EXE must remain alive.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe';$proc=Start-Process $exe -WorkingDirectory $dist -PassThru;Start-Sleep 20;if($proc.HasExited){throw "Finished EXE exited $($proc.ExitCode)"};Stop-Process -Id $proc.Id -Force

# Build portable and installer, then hash exactly what will be published.
$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip';if(Test-Path $zip){Remove-Item $zip -Force};Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal
$iscc=@('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe')|?{Test-Path $_}|Select-Object -First 1
if(-not$iscc){throw 'ISCC missing'}
Push-Location $root;try{& $iscc '/DMyAppVersion=0.1.48' '.\installer\MerzoWindowsOptimizer.iss';if($LASTEXITCODE-ne0){throw 'Installer failed'}}finally{Pop-Location}
$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe';$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant();$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant();"$ih  MerzoWindowsOptimizerSetup-win-x64.exe"|Set-Content "$installer.sha256" -Encoding ascii;"$zh  MerzoWindowsOptimizer-portable-win-x64.zip"|Set-Content "$zip.sha256" -Encoding ascii
Write-Host "R48_INSTALLER_SHA256=$ih"

# Publish only after every gate above is green.
if(-not$env:GH_TOKEN){throw 'GH_TOKEN missing'}
$tag='mwo-v0.1.48';gh release delete $tag --repo $env:GITHUB_REPOSITORY --yes 2>$null;if($LASTEXITCODE-ne0){$global:LASTEXITCODE=0};git push origin ":refs/tags/$tag" 2>$null;if($LASTEXITCODE-ne0){$global:LASTEXITCODE=0}
$notes=Join-Path $env:RUNNER_TEMP 'r48-release.txt';@'
R48 OTA RELIABILITY

• Исправляет 504 Gateway Timeout старого R45 Update Center.
• Retry для 408/429/500/502/503/504 и timeout.
• Fallback: matching mwo-v tags → exact release-by-tag → lightweight tags endpoint.
• Строгая R46 проверка official repo / exact installer / URL / size / digest / SHA sidecar сохранена.
• R47 SIMPLE BUILDS и Snapshot/Verify/Undo сохранены.
'@|Set-Content $notes -Encoding UTF8
$files=@($installer,"$installer.sha256",$zip,"$zip.sha256")
gh release create $tag --repo $env:GITHUB_REPOSITORY --target $env:GITHUB_SHA --title 'Merzo Windows Optimizer 0.1.48 (R48 OTA RELIABILITY)' --notes-file $notes @files
if($LASTEXITCODE-ne0){throw 'Release publish failed'}

"R48_ROOT=$root" >> $env:GITHUB_ENV
Write-Host 'R48_RELEASE_PASS'
