param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $Board).Path
$out=(New-Item -Type Directory -Path $Report).FullName
$job=Join-Path $env:TEMP ('ff3-fit-'+[guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $source -Destination $job -Recurse
$q='C:/altera_lite/25.1std/quartus/bin64'
$py="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
Push-Location $job
try {
 & "$q/quartus_map.exe" board *> "$out/map.log"
 if($LASTEXITCODE){throw 'map failed'}
 & $py "$PSScriptRoot/bind_ff3_constraints1037.py" $job
 if($LASTEXITCODE){throw 'merge audit failed'}
 & "$q/quartus_fit.exe" board *> "$out/fit.log"
 if($LASTEXITCODE){throw 'fit failed'}
 & "$q/quartus_sta.exe" board *> "$out/sta.log"
 if($LASTEXITCODE){throw 'STA failed'}
 & "$q/quartus_asm.exe" board *> "$out/asm.log"
 if($LASTEXITCODE){throw 'assembler failed'}
}finally{
 if(Test-Path output_files){Get-ChildItem output_files -File|Where-Object {$_.Extension -in '.summary','.rpt','.sof'}|Copy-Item -Destination $out}
 Pop-Location
}
