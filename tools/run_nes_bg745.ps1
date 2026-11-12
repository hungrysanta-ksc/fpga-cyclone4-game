param(
    [Parameter(Mandatory)][ValidateSet('arm','control','live','budget','input','matched','reserved','priced')][string]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot = $env:TEMP,
    [string]$Python = (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $repo
try {
    $arm = switch ($Variant) {
        'input' { '../probes/nes-bg745/input-long/src' }
        'budget' { '../probes/nes-bg745/budget-long/src' }
        { $_ -in ('arm','live') } { '../probes/nes-bg745/long02/src' }
        default { '../probes/nes-pair727/arm01/src' }
    }
    $runner = switch ($Variant) {
        'arm' { 'tools/test_nes_observer717.py' }
        { $_ -in ('matched','reserved','priced') } { 'tools/test_nes_handoff745.py' }
        default { 'tools/test_nes_arm745.py' }
    }
    $extra = @()
    if ($Variant -eq 'reserved') { $extra = @('--reserve') }
    if ($Variant -eq 'priced') { $extra = @('--reserve','--input-first') }
    $out = Join-Path $TraceRoot "nes-bg745-$Variant$Phase"
    if (Test-Path -LiteralPath $out) { throw "Use a fresh output path: $out" }
    $log = "../probes/nes-bg745/$Variant$Phase.log"
    & $Python -X utf8 $runner @extra --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
        --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
        --sender653 "$TraceRoot/nes-reader661-sender/sender.json" --client ../probes/nes-longrun694/client01 `
        --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 `
        --fixture ../probes/nes-dense519/fixture02 --plans ../probes/nes-seal538/plans01 `
        --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
        --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" `
        --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> $log
    if ($LASTEXITCODE) { throw "745 $Variant phase $Phase failed ($LASTEXITCODE)" }
} finally { Pop-Location }
