param(
    [Parameter(Mandatory)][ValidateSet('measured','eager','fold','debt','linked','foldlink','debtlink')][string]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot = $env:TEMP,
    [string]$Python = (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $repo
try {
    $arm = '../probes/nes-pair727/arm01/src'
    $runner = 'tools/test_nes_credit747.py'
    $extra = @('--policy', $Variant)
    if ($Variant -in ('linked','foldlink','debtlink')) {
        $arm = '../probes/nes-credit747/long/src'
        if ($Variant -eq 'foldlink') { $arm = '../probes/nes-credit747/foldlong/src' }
        if ($Variant -eq 'debtlink') { $arm = '../probes/nes-credit747/debtlong/src' }
        $runner = 'tools/test_nes_oam746.py'
        $extra = @()
    }
    $out = Join-Path $TraceRoot "nes-credit747-$Variant$Phase"
    if (Test-Path -LiteralPath $out) { throw "Use a fresh output path: $out" }
    $log = "../probes/nes-credit747/$Variant$Phase.log"
    & $Python -X utf8 $runner @extra --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
        --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
        --sender653 "$TraceRoot/nes-reader661-sender/sender.json" --client ../probes/nes-longrun694/client01 `
        --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 `
        --fixture ../probes/nes-dense519/fixture02 --plans ../probes/nes-seal538/plans01 `
        --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
        --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" `
        --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> $log
    if ($LASTEXITCODE) { throw "747 $Variant phase $Phase failed ($LASTEXITCODE)" }
} finally { Pop-Location }
