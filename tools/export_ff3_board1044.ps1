param([Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$out=(Resolve-Path $Report).Path
$match=Select-String -LiteralPath "$out/fit.log" -Pattern 'File: (.+?/ff3-fit-[0-9a-f]+)/' | Select-Object -First 1
if(!$match){throw 'missing routed Quartus project'}
$project=$match.Matches[0].Groups[1].Value
if((Get-FileHash "$out/board.sof").Hash -ne (Get-FileHash "$project/output_files/board.sof").Hash){throw 'different route'}
$q='C:/altera_lite/25.1std/quartus/bin64'
Push-Location $project
try{
 Copy-Item -LiteralPath "$PSScriptRoot/report_nes_kirby1023_io.tcl" -Destination psram1044.tcl
 Copy-Item -LiteralPath "$PSScriptRoot/report_ff3_sram1043.tcl" -Destination sram1044.tcl
 & "$q/quartus_sta.exe" -t psram1044.tcl *> "$out/psram-timing.log"
 if($LASTEXITCODE){throw 'PSRAM pin timing'}
 Copy-Item -LiteralPath 'kirby1023-io.tsv' -Destination "$out/io.tsv"
 & "$q/quartus_sta.exe" -t sram1044.tcl sram1044.tsv *> "$out/sram-timing.log"
 if($LASTEXITCODE){throw 'SRAM pin timing'}
 Copy-Item -LiteralPath sram1044.tsv -Destination "$out/sram.tsv"
 & "$q/quartus_cpf.exe" -c output_files/board.sof board.rbf *> "$out/cpf.log"
 if($LASTEXITCODE){throw 'programming conversion'}
 Copy-Item -LiteralPath board.rbf -Destination "$out/board.rbf"
}finally{Pop-Location}
