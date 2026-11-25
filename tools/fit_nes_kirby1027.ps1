param([Parameter(Mandatory)] [string]$Board, [Parameter(Mandatory)] [string]$Out)
$ErrorActionPreference='Stop'
$src=(Resolve-Path -LiteralPath $Board).Path
$report=(New-Item -ItemType Directory -Path $Out -ErrorAction Stop).FullName
$job=Join-Path $env:TEMP ('nes-kirby1027-'+[guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $src -Destination $job -Recurse
Copy-Item "$PSScriptRoot/report_nes_kirby1023_io.tcl" "$job/io.tcl"
$q='C:/altera_lite/25.1std/quartus/bin64'
Push-Location -LiteralPath $job
try {
 & "$q/quartus_sh.exe" --flow compile board *> "$report/compile.log"
 if ($LASTEXITCODE) {throw 'Full compilation failed'}
 & "$q/quartus_sta.exe" -t io.tcl *> "$report/io.log"
 if ($LASTEXITCODE) {throw 'PSRAM timing report failed'}
 Copy-Item kirby1023-io.tsv "$report/io.tsv"
 & "$q/quartus_cpf.exe" -c output_files/board.sof board.rbf *> "$report/cpf.log"
 if ($LASTEXITCODE) {throw 'RBF conversion failed'}
 Copy-Item board.rbf $report
} finally {
 Get-ChildItem output_files -File | Where-Object { $_.Extension -in '.summary','.rpt','.sof' } | Copy-Item -Destination $report
 Pop-Location
}
