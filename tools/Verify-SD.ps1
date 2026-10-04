param([Parameter(Mandatory=$true)][string]$SdRoot)
$ErrorActionPreference='Stop'
$expected=@{
 'firmware.stm'='16b0ed2decd79a289d95a98c075b18d5f086a6e138d7f1f7f1af067d50d95dd5'
 'fpga_egbc.bi3'='0bdcb9f995496ea314a41a0b624f1b9c98bc702f2929ab578b5e300c1d4bf647'
 'gbc_snes.bin'='7a36dc1fa4355d804ee72ca4aed18250c00c92bd3d8a469c16d8970def8e20ca'
}
foreach($name in $expected.Keys){
 $file=Join-Path (Join-Path $SdRoot 'sd2snes') $name
 $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLowerInvariant()
 if($actual -ne $expected[$name]){throw "Hash mismatch: $name"}
 Write-Output "OK $name"
}
Write-Output 'C44 firmware + C43 FPGA/renderer verified. No SD files were changed.'
