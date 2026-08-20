$ErrorActionPreference='Stop'

$v1='.\optimizer\scripts\r53_release_v1.ps1'
$v2='.\optimizer\scripts\r53_release_v2.ps1'
$v5='.\optimizer\scripts\r53_release_v5.ps1'
$legacy='.\optimizer\scripts\r49_release.ps1'
$originalV1=Get-Content $v1 -Raw
$originalV2=Get-Content $v2 -Raw
$originalV5=Get-Content $v5 -Raw
$originalLegacy=Get-Content $legacy -Raw

function Convert-R53ScriptToR54Bridge([string]$text) {
    # Preserve old R53 scripts in git; transform only the generated production
    # execution copy. 0.1.54 is deliberately three-part so public 0.1.53 can
    # serialize it without losing the revision/tag identity.
    $text=$text.Replace('0.1.53.1','0.1.54.0')
    $text=$text.Replace('0.1.53','0.1.54')
    $text=$text.Replace('Production R53.1','Production R54')
    $text=$text.Replace('Production R53','Production R54')
    $text=$text.Replace('Production R54 · 0.1.54.0','Production R54 · 0.1.54')
    $text=$text.Replace('R53 HOTFIX 1','R53 GAME HOTFIX BRIDGE')
    return $text
}

try {
    # The old R49 OTA smoke verifies 504 -> refs -> exact-release fallback. In
    # R54 GetCurrentVersion correctly comes from MerzoOptimizer.Windows itself,
    # so the synthetic fallback release is the SAME version as the tested DLL
    # and UpdateAvailable must be false. Keep all fallback assertions (success,
    # selected version, three retries); stop requiring a logically-wrong update.
    $fallbackOld='if(!r.Success||!r.UpdateAvailable||r.LatestVersion!="0.1.49"||f.N!=3)throw new Exception($"Fallback failed success={r.Success} latest={r.LatestVersion} calls={f.N} msg={r.Message}");'
    $fallbackNew='if(!r.Success||r.LatestVersion!="0.1.49"||f.N!=3)throw new Exception($"Fallback failed success={r.Success} latest={r.LatestVersion} calls={f.N} msg={r.Message}");'
    if(($originalLegacy.Split($fallbackOld).Count-1)-ne1){throw 'R54 bridge R49 fallback smoke anchor mismatch'}
    $patchedLegacy=$originalLegacy.Replace($fallbackOld,$fallbackNew)
    Set-Content $legacy $patchedLegacy -Encoding UTF8

    $patchedV1=Convert-R53ScriptToR54Bridge $originalV1

    # The deepest generated R49 build receives -Version. After the generic
    # conversion this is 0.1.54.0; keep file/assembly version four-part while
    # the public/tag version stays three-part 0.1.54.
    if(-not$patchedV1.Contains("-Version ''0.1.54.0''")){throw 'R54 bridge Build-Production version anchor missing'}
    if(-not$patchedV1.Contains("`$src=`$src.Replace('0.1.52','0.1.54')")){throw 'R54 bridge source-promotion anchor missing'}
    if(-not$patchedV1.Contains("if(`$v-ne'0.1.54.0')")){throw 'R54 bridge DLL version gate missing'}
    Set-Content $v1 $patchedV1 -Encoding UTF8

    # R53 V2 wraps V1 and has its own literal production-identity anchor. It is
    # an inherited build check, not product code. Adapt only the runner copy so
    # it validates R54 while the canonical R53 V2 script remains unchanged.
    $patchedV2=Convert-R53ScriptToR54Bridge $originalV2
    if(-not$patchedV2.Contains("`$src=`$src.Replace('Production R52','Production R54')")){throw 'R54 bridge V2 identity anchor missing after conversion'}
    if(-not$patchedV2.Contains("'Production R54 · 0.1.54'")){throw 'R54 bridge V2 exact title anchor missing after conversion'}
    Set-Content $v2 $patchedV2 -Encoding UTF8

    $patchedV5=Convert-R53ScriptToR54Bridge $originalV5
    $oldChain="'r53_game_apply_hotfix.py','r53_version_finalize.py')"
    $newChain="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py')"
    if(($patchedV5.Split($oldChain).Count-1)-ne1){throw 'R54 bridge V5 patch-chain anchor mismatch'}
    $patchedV5=$patchedV5.Replace($oldChain,$newChain)

    # r54_updater_bridge writes the public Inno version as exact three-part
    # 0.1.54, while assemblies are 0.1.54.0.
    $patchedV5=$patchedV5.Replace('#define MyAppVersion "0.1.54.0"','#define MyAppVersion "0.1.54"')
    $patchedV5=$patchedV5.Replace('AppVersion=0.1.54.0','AppVersion=0.1.54')
    $patchedV5=$patchedV5.Replace('Production R54 · 0.1.54.0','Production R54 · 0.1.54')
    $patchedV5=$patchedV5.Replace('Text="R53.1"','Text="R54"')

    # Require the bridge marker and updater non-truncation contract before any
    # artifact can be accepted by the outer wrapper.
    $markerAnchor="if(!(Test-Path (Join-Path `$root 'R53_GAME_APPLY_HOTFIX.marker'))){throw 'R53 GAME apply hotfix marker missing'}"
    $markerNew=$markerAnchor+"`r`n    if(!(Test-Path (Join-Path `$root 'R54_R53_HOTFIX_BRIDGE.marker'))){throw 'R54 updater bridge marker missing'}"
    if(($patchedV5.Split($markerAnchor).Count-1)-ne1){throw 'R54 bridge marker gate anchor mismatch'}
    $patchedV5=$patchedV5.Replace($markerAnchor,$markerNew)
    Set-Content $v5 $patchedV5 -Encoding UTF8

    & $v5
    if($LASTEXITCODE-ne0){throw "R54 bridge inherited production gates failed: $LASTEXITCODE"}
    if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R54 bridge SOURCE_ROOT missing'}

    $root=$env:SOURCE_ROOT
    $updater=Join-Path $root 'src\MerzoOptimizer.Windows\Updates\GitHubUpdateService.cs'
    $xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
    $iss=Join-Path $root 'installer\MerzoWindowsOptimizer.iss'
    foreach($p in @($updater,$xaml,$iss)){if(!(Test-Path $p)){throw "R54 bridge final source missing: $p"}}
    $u=Get-Content $updater -Raw
    $ui=Get-Content $xaml -Raw
    $i=Get-Content $iss -Raw

    foreach($bad in @('LatestVersion = bestVersion.ToString(3),','LatestVersion = latest.ToString(3),','GetEntryAssembly()?.GetName().Version?.ToString(3)')){
        if($u.Contains($bad)){throw "R54 updater truncation regression: $bad"}
    }
    foreach($good in @('LatestVersion = FormatVersion(bestVersion),','LatestVersion = FormatVersion(latest),','typeof(GitHubUpdateService).Assembly.GetName().Version','return version.ToString(4);')){
        if(-not$u.Contains($good)){throw "R54 updater bridge contract missing: $good"}
    }
    if(-not$ui.Contains('Production R54 · 0.1.54')){throw 'R54 visible version missing'}
    if(-not$ui.Contains('Text="R54"')){throw 'R54 navigation badge missing'}
    if(-not$i.Contains('#define MyAppVersion "0.1.54"') -and -not$i.Contains('AppVersion=0.1.54')){throw 'R54 Inno public version missing'}

    $dist=Join-Path $root 'dist\app'
    foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
        $p=Join-Path $dist $n
        if(!(Test-Path $p)){throw "R54 missing $n"}
        $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
        if($version-ne'0.1.54.0'){throw "R54 $n version=$version"}
    }

    # Reflection-level parser regression gate against the finished updater DLL.
    # This proves future four-part tags remain four-part after the bridge.
    $probe=Join-Path $env:RUNNER_TEMP 'r54_parser_probe.ps1'
    @'
param([string]$Dll)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
  $asm=[Reflection.Assembly]::LoadFrom($Dll)
  $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
  if(!$type){throw 'GitHubUpdateService missing'}
  $flags=[Reflection.BindingFlags]'NonPublic,Static'
  $parse=$type.GetMethod('ParseTaggedVersion',$flags)
  $format=$type.GetMethod('FormatVersion',$flags)
  if(!$parse -or !$format){throw 'R54 parser/formatter private methods missing'}
  $v=$parse.Invoke($null,@('mwo-v0.1.54.1','mwo-v'))
  if(!$v -or $v.ToString() -ne '0.1.54.1'){throw "ParseTaggedVersion lost revision: $v"}
  $formatted=[string]$format.Invoke($null,@($v))
  if($formatted-ne'0.1.54.1'){throw "FormatVersion lost revision: $formatted"}
  $old=$parse.Invoke($null,@('mwo-v0.1.54','mwo-v'))
  if(!$old -or $old.ToString() -ne '0.1.54'){throw "Three-part parsing regressed: $old"}
  Write-Host 'R54_FOUR_PART_VERSION_PARSER_PASS'
}
finally {Pop-Location}
'@ | Set-Content $probe -Encoding UTF8
    & pwsh -NoLogo -NoProfile -File $probe -Dll (Join-Path $dist 'MerzoOptimizer.Windows.dll')
    if($LASTEXITCODE-ne0){throw 'R54 four-part parser reflection gate failed'}

    $notes=Join-Path $root 'dist\R53_RELEASE_NOTES.md'
    if(!(Test-Path $notes)){throw 'R54 bridge release notes base missing'}
    @'

## 0.1.54 — R53 GAME HOTFIX DELIVERY BRIDGE

- Исправлен фактический откат GAME на `r53.process.service_host_density`. Общий запрет ADVANCED/EXPERT сохранён; автоматически разрешено только точное встроенное действие Service Host Density с проверкой ID, GAME/EXTREME tags и Registry-контракта.
- Версия 0.1.54 выбрана намеренно как совместимый трёхчастный bridge: публичная R53 0.1.53 умеет разобрать четырёхчастный tag, но обрезает `LatestVersion` через `ToString(3)` и затем отклоняет URL `mwo-v0.1.53.1` как несовпадающий.
- Updater исправлен: `LatestVersion` больше не теряет revision, текущая версия берётся из assembly самого updater-компонента, а будущие `0.1.x.y` hotfix-релизы проходят официальный URL/digest contract без обрезания.
- Исправлены оставшиеся подписи R52/R53.1; интерфейс bridge показывает R54 / 0.1.54.
'@ | Add-Content $notes -Encoding UTF8
    Write-Host 'R54_R53_HOTFIX_BRIDGE_ALL_GATES_PASS'
}
finally {
    Set-Content $v1 $originalV1 -Encoding UTF8
    Set-Content $v2 $originalV2 -Encoding UTF8
    Set-Content $v5 $originalV5 -Encoding UTF8
    Set-Content $legacy $originalLegacy -Encoding UTF8
}
