$ErrorActionPreference='Stop'
$tags=@('981profile','981pair','981ready','981rank','981rankpair')
& "$PSScriptRoot/check_nes_e9_head980.ps1" -Tags $tags

# Carry the actual CHR row RAM from generation 905 to the return of the
# first OBJ. Judge the shared port at the ARM schedule's recorded grants.
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$tmp=Join-Path $env:LOCALAPPDATA 'Temp'
$failures=@()
Push-Location (Join-Path $tmp 'nes-trial816-board964')
try {
    foreach ($tag in '981profile','981pair') {
        foreach ($phase in 1,2) {
            $base=Join-Path $tmp "nes-tile821-obj-jointmirror-p$phase-$tag-cold-pair"
            $previous=$null
            foreach ($g in 905..911) {
                $d=Join-Path $base "gen$g"
                $options=@("+trace=$d",'+all_e8_differences')
                if ($previous) { $options+="+previous_rows=$previous" }
                if ($g -eq 911) { $options+='+admission954'; $options+='+multiple965' }
                $page=Get-Content -LiteralPath "$d/mail964.txt"
                if ($page -ne 'none') {
                    $at,$packet=$page -split ' '
                    $options+="+page_at=$at"; $options+="+page_bytes=$packet"
                }
                $log=Join-Path $d 'chain981.log'
                & "$bin/vsim.exe" -c -gREPLAY=1 -gRETAIN951=1 "-gG=$g" work980.tb_nes_port914 @options -do 'onerror {quit -code 1}; run -all; quit -code 0' *> $log
                if ($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath $log -Pattern 'PASS914 trace')) {
                    $failures+="$tag phase $phase generation $g"
                    break
                }
                $previous=Join-Path $d 'rows-out951.hex'
            }
        }
    }
} finally { Pop-Location }
if ($failures.Count) { throw ("RTL replay failed in " + ($failures -join ', ')) }
