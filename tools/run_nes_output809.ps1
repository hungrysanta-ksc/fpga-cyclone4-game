param(
    [Parameter(Mandatory)][ValidateSet('807','809','810','810B','810C','810D','810E','810F','810G','810H','810I','811','812','812B','812C')][string]$Variant,
    [Parameter(Mandatory)][ValidateSet(1,2)][int]$Phase,
    [Parameter(Mandatory)][string]$Game,
    [string]$TraceRoot=(Join-Path $env:LOCALAPPDATA 'Temp'),
    [string]$Python=(Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference='Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $images=@{
        '807'=@('base','nes-obj807/link807')
        '809'=@('fold','nes-output809/link807')
        '810'=@('order810','nes-order810/link807')
        '810B'=@('order810b','nes-order810b/link807')
        '810C'=@('order810c','nes-order810c/final807')
        '810D'=@('order810d','nes-order810d/link807')
        '810E'=@('order810e','nes-order810e/ship807')
        '810F'=@('order810f','nes-order810f/link807')
        '810G'=@('order810g','nes-order810g/final807')
        '810H'=@('order810h','nes-order810h/link807')
        '810I'=@('order810i','nes-order810i/link807')
        '811'=@('mmc811','nes-trial811/link811')
        '812'=@('mmc812','nes-trial811/link812')
        '812B'=@('mmc812b','nes-trial811/link812b')
        '812C'=@('mmc812c','nes-trial811/link812c')
    }
    $label,$build=$images[$Variant]
    $arm="../probes/$build/src"
    $client=if($Variant -in '812','812B','812C'){'../probes/nes-longrun694/client01'}else{'../probes/nes-complete685/client01'}
    $out=Join-Path $TraceRoot "nes-output809-$label-p$Phase"
    if(Test-Path -LiteralPath $out){throw "Output already exists: $out"}
    & $Python -X utf8 tools/replay_nes_output768.py run $Variant ../probes/nes-output768-inputs --arm $arm --game $Game --emit --geometry650 --commit-pop-bound `
      --rtl-evidence "$TraceRoot/nes-bonus703-status01/result.json" --board689 "$TraceRoot/nes-bg707-board04" `
      --sender653 "$TraceRoot/nes-output768-sender/joint-sender.json" --client $client `
      --samples "$TraceRoot/nes-snoop601-trace01/stim.tsv" --data ../probes/nes-delta231/test07 --fixture ../probes/nes-output768-inputs/fixture `
      --plans ../probes/nes-output768-inputs/plans --capture ../probes/nes-output489/audit01 --calendar "$TraceRoot/nes-service509-rom03" `
      --driver503 analysis/hardware503-mmc502.json --mesen "$TraceRoot/nes-map628-mesen/Mesen.exe" --start-clock (7288416+($Phase-1)*178684) --out $out --keep-run *> "$out.log"
    if($LASTEXITCODE){throw "Replay failed. See $out.log"}
} finally {Pop-Location}
