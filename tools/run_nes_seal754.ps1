param(
    [Parameter(Mandatory)][ValidateSet('geometry','section','both','raw','shared','combined')][string]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot = $env:TEMP,
    [string]$Python = (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $repo
try {
    $arm = "../probes/nes-seal754/arm-$Variant/src"
    $client = "../probes/nes-static751/sharedfast"
    if ($Variant -eq "raw") {
        $arm = "../probes/nes-credit753/arm-prefix/src"
        $client = "../probes/nes-seal754/raw"
    }
    if ($Variant -eq "combined") {
        $arm = "../probes/nes-seal754/arm-shared/src"
        $client = "../probes/nes-seal754/raw"
    }
    $out = Join-Path $TraceRoot "nes-seal754-$Variant$Phase"
    if (Test-Path -LiteralPath $out) { throw "Use a fresh output path: $out" }
    $log = Join-Path $TraceRoot "nes-seal754-$Variant$Phase.log"
    & $Python -X utf8 tools/test_nes_static751.py --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
        --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
        --sender653 "$TraceRoot/nes-reader661-sender/sender.json" --client $client `
        --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 `
        --fixture ../probes/nes-dense519/fixture02 --plans ../probes/nes-seal538/plans01 `
        --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
        --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" `
        --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> $log
    if ($LASTEXITCODE) { throw "754 $Variant phase $Phase failed ($LASTEXITCODE)" }
} finally { Pop-Location }
