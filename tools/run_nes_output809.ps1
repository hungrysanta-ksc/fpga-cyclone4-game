param(
    [Parameter(Mandatory)][ValidateSet(807,809)][int]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot=(Join-Path $env:LOCALAPPDATA 'Temp'),
    [string]$Python=(Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference='Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $label='base'
    $arm='../probes/nes-obj807/link807/src'
    if($Variant -eq 809){$label='fold';$arm='../probes/nes-output809/link807/src'}
    $out=Join-Path $TraceRoot "nes-output809-$label-p$Phase"
    if(Test-Path -LiteralPath $out){throw "Output already exists: $out"}
    & $Python -X utf8 tools/replay_nes_output768.py run $Variant ../probes/nes-output768-inputs --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
      --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
      --sender653 "$TraceRoot/nes-output768-sender/joint-sender.json" --client ../probes/nes-complete685/client01 `
      --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 --fixture ../probes/nes-output768-inputs/fixture `
      --plans ../probes/nes-output768-inputs/plans --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
      --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> "$out.log"
    if($LASTEXITCODE){throw "Replay failed. See $out.log"}
} finally {Pop-Location}
