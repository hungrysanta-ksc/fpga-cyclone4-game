param([string]$Out = '../probes/nes-credit747', [switch]$Debt)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $bin = (Get-Item ../.tools/arm-gnu-toolchain-13.3.rel1/*/bin/arm-none-eabi-as.exe).DirectoryName
    if ($Debt) {
        & "$bin/arm-none-eabi-as.exe" -mcpu=cortex-m4 -mthumb -o "$Out/debt.o" tools/nes_credit747_debt.S
        if ($LASTEXITCODE) { throw 'Debt assembly failed' }
        & "$bin/arm-none-eabi-ld.exe" -Ttext=0x0807fd00 -e hold747 --defsym=poll_fail=0x801f08a --defsym=submit_obj=0x801f116 --defsym=drain_window=0x80219b3 -o "$Out/debt.elf" "$Out/debt.o"
        if ($LASTEXITCODE) { throw 'Debt link failed' }
        return
    }
    & "$bin/arm-none-eabi-as.exe" -mcpu=cortex-m4 -mthumb -o "$Out/probe.o" tools/nes_credit747.S
    if ($LASTEXITCODE) { throw 'Assembly failed' }
    & "$bin/arm-none-eabi-ld.exe" -Ttext=0x0807fc00 -e begin747 --defsym=status_arg=0x802190c --defsym=guard_loop=0x801987e --defsym=repeat_wait=0x8019892 -o "$Out/probe.elf" "$Out/probe.o"
    if ($LASTEXITCODE) { throw 'Link failed' }
    & "$bin/arm-none-eabi-objdump.exe" -d "$Out/probe.elf" | Set-Content "$Out/probe.dis"
} finally { Pop-Location }
