$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-carts1059").Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$job=New-Item -Type Directory -Path (Join-Path $env:TEMP ('cart-state-'+[guid]::NewGuid().ToString('N')))
Push-Location $job.FullName
try {
 & "$q/vlib.exe" work
 foreach($m in 5,7,21){
  Copy-Item "$out/board-$m/cart_nrom.sv","$root/tests/nes-functional/cart_state1059_tb.sv" . -Force
  & "$q/vlog.exe" -sv cart_nrom.sv cart_state1059_tb.sv *> "$out/mapper-$m.compile.log"
  if($LASTEXITCODE){throw "vlog $m"}
  & "$q/vsim.exe" -c -suppress 3009 cart_state1059_tb "+mapper=$m" -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/mapper-$m.test.log"
  if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath "$out/mapper-$m.test.log" -Pattern '^# PASS')){throw "mapper $m"}
 }
 Copy-Item "$root/tests/nes-functional/page_receipt1058_tb.sv" .
 foreach($v in 1058,1059){
  Copy-Item "$out/../nes-carts$v/board-7/nes_chr_snapshot.sv" . -Force
  $tb=(Get-Content page_receipt1058_tb.sv -Raw).Replace('task seal;','integer copies=0; always @(negedge clk) if(!s.we_n)copies++; task seal;').Replace('put(47);','copies=0;put(47);').Replace('if(fine || mask','$display("MIRROR_BYTES %0d",copies);if(fine || mask')
  Set-Content -LiteralPath mirror.sv -Value $tb
  & "$q/vlog.exe" -sv nes_chr_snapshot.sv mirror.sv *> "$out/mirror-$v.compile.log"
  if($LASTEXITCODE){throw 'mirror compile'}
  & "$q/vsim.exe" -c -suppress 3009 page_receipt1058_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/mirror-$v.test.log"
  if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath "$out/mirror-$v.test.log" -Pattern '^# PASS')){throw "mirror $v"}
 }
} finally {Pop-Location}
