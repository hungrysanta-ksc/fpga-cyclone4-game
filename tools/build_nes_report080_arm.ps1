param([Parameter(Mandatory=$true)][string]$SourceRoot,[Parameter(Mandatory=$true)][string]$ArmBin,[Parameter(Mandatory=$true)][string]$HostGcc,[Parameter(Mandatory=$true)][string]$Make,[Parameter(Mandatory=$true)][string]$UnixBin,[Parameter(Mandatory=$true)][string]$MiniImage)
# Reuse the exact079 compiler/tool flags and pinned mini image. The output
# subdirectory retains obj-report079; VERSION in the new tree identifies080.
# No edits to the079 builder or079 evidence are performed.
& "$PSScriptRoot/build_nes_report079_arm.ps1" @PSBoundParameters
Write-Output '080 compile-only candidate uses the unchanged079 build driver.'
