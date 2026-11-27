param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report,
      [switch]$ExportPSRAM,[switch]$ExportSRAM)
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
 if($ExportPSRAM){
  Copy-Item -LiteralPath "$PSScriptRoot/report_nes_kirby1023_io.tcl" -Destination io.tcl
  & "$q/quartus_sta.exe" -t io.tcl *> "$out/psram-timing.log"
  if($LASTEXITCODE){throw 'PSRAM pin timing failed'}
  Copy-Item -LiteralPath kirby1023-io.tsv -Destination "$out/io.tsv"
  & "$q/quartus_cpf.exe" -c output_files/board.sof board.rbf *> "$out/cpf.log"
  if($LASTEXITCODE){throw 'RBF conversion failed'}
  Copy-Item -LiteralPath board.rbf -Destination $out
 }
 if($ExportSRAM){
  Copy-Item -LiteralPath "$PSScriptRoot/report_ff3_sram1043.tcl" -Destination sram.tcl
  & "$q/quartus_sta.exe" -t sram.tcl sram.tsv *> "$out/sram-timing.log"
  if($LASTEXITCODE){throw 'SRAM pin timing failed'}
  Copy-Item -LiteralPath sram.tsv -Destination $out
 }
}finally{
 if(Test-Path output_files){Get-ChildItem output_files -File|Where-Object {$_.Extension -in '.summary','.rpt','.sof'}|Copy-Item -Destination $out}
 Pop-Location
}
