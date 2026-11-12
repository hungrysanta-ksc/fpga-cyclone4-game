param([string]$Out = '../probes/nes-oam746')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $bin = (Get-Item ../.tools/arm-gnu-toolchain-13.3.rel1/*/bin/arm-none-eabi-as.exe).DirectoryName
    & "$bin/arm-none-eabi-as.exe" -mcpu=cortex-m4 -mthumb -o "$Out/probe.o" tools/nes_oam746_probe.S
    if ($LASTEXITCODE) { throw 'Assembly failed' }
    & "$bin/arm-none-eabi-ld.exe" -Ttext=0x0807fa00 -e start746 --defsym=send_tail=0x801e41a --defsym=retry_status=0x8021986 --defsym=submit_tile=0x801f116 --defsym=next_poll=0x80219a0 --defsym=fail_through=0x8021902 --defsym=copy_bytes=0x800c941 -o "$Out/probe.elf" "$Out/probe.o"
    if ($LASTEXITCODE) { throw 'Link failed' }
    & "$bin/arm-none-eabi-objdump.exe" -d "$Out/probe.elf" | Set-Content "$Out/probe.dis"
} finally { Pop-Location }
