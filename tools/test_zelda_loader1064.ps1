$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out=(Resolve-Path (Join-Path $root '../probes/nes-headers1064')).Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$work=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('loader1064-'+[guid]::NewGuid().ToString('N')))
Push-Location $work.FullName
try {
 & "$q/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$q/vlog.exe" -sv "$out/board-1/nes_rom_loader.sv" "$root/tests/nes-functional/ff3_load_count_tb.sv" *> "$out/loader-compile.log"
 if($LASTEXITCODE){throw 'vlog'}
 & "$q/vsim.exe" -c ff3_load_count_tb -gBYTES=262144 -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/loader.log"
 if($LASTEXITCODE -or !(Select-String -Quiet -Path "$out/loader.log" -Pattern '^# PASS FF3 loader 262144')){throw 'MMC1 loader count/START/STOP'}
}finally{Pop-Location}
