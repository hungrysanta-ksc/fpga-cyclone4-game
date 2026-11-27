param([string]$Board,[string]$Output,[string]$Slot,[int]$Frames=24,[switch]$Guards)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/..").Path
$work=(Resolve-Path "$repo/../probes/nes-ff3-1045").Path
if(!$Board){$Board="$work/board-final"}
if(!$Output){$Output="$work/final"}
$out=[IO.Directory]::CreateDirectory($Output).FullName
$py="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$env:FF3_CHECKPOINT_BOARD=(Resolve-Path $Board).Path
$env:FF3_REPLAY_OUT=$out
$env:FF3_OPENING_FRAMES=$Frames
if($Slot){$env:FF3_PHYSICAL_SLOT=(Resolve-Path -LiteralPath $Slot).Path}
else{Remove-Item Env:FF3_PHYSICAL_SLOT -ErrorAction SilentlyContinue}
if($Guards){& "$PSScriptRoot/check_ff3_guards1045.ps1" -Board $env:FF3_CHECKPOINT_BOARD -Report $out}
& $py "$repo/tools/check_ff3_checkpoint_rtl.py"
if($LASTEXITCODE){throw 'FF3 source replay failed'}
