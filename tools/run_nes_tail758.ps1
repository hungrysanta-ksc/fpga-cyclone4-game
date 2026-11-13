param(
    [Parameter(Mandatory)][ValidateSet('control','word','tail','burst','compact')][string]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot = $env:TEMP,
    [string]$RunLabel,
    [string]$Python = (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $repo
try {
    $arm = "../probes/nes-tail758/arm-$Variant/src"
    $client = "../probes/nes-static751/sharedfast"
    if($Variant -eq 'control'){$arm="../probes/nes-credit753/arm-prefix/src"}
    if(!$RunLabel){$RunLabel=$Variant}
    $out = Join-Path $TraceRoot "nes-tail758-$RunLabel$Phase"
    if (Test-Path -LiteralPath $out) { throw "Use a fresh output path: $out" }
    $log = Join-Path $TraceRoot "nes-tail758-$RunLabel$Phase.log"
    & $Python -X utf8 tools/test_nes_tail758.py --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
        --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
        --sender653 "$TraceRoot/nes-reader661-sender/sender.json" --client $client `
        --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 `
        --fixture ../probes/nes-dense519/fixture02 --plans ../probes/nes-seal538/plans01 `
        --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
        --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" `
        --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> $log
    if ($LASTEXITCODE) { throw "758 $Variant phase $Phase failed ($LASTEXITCODE)" }
} finally { Pop-Location }
