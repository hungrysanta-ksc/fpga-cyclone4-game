# SPDX-License-Identifier: MIT
param(
 [Parameter(Mandatory)][string]$Python,
 [Parameter(Mandatory)][string]$FloatWrapper,
 [Parameter(Mandatory)][string]$QuestaBin,
 [Parameter(Mandatory)][string]$Out
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$wrapper=(Resolve-Path -LiteralPath $FloatWrapper).Path
$pythonPath=(Resolve-Path -LiteralPath $Python).Path
$driver='nes_diag_safety_memory_checks.py'
# Catch transformation-script syntax errors before starting the FLOAT session.
& $pythonPath -B -X utf8 -c "import ast,pathlib,sys; [ast.parse(p.read_text(encoding='utf-8')) for p in [pathlib.Path(sys.argv[1])]]" (Join-Path $PSScriptRoot $driver)
if($LASTEXITCODE -ne 0){throw 'H1 board driver syntax check failed before license startup.'}
$questa=(Resolve-Path -LiteralPath $QuestaBin).Path
$output=[IO.Path]::GetFullPath($Out)
if(Test-Path -LiteralPath $output){throw 'Output must be a fresh directory.'}
if($output -match '[^\x00-\x7F]'){throw 'Questa output must use an ASCII path.'}
$expected='C08B0ABF2B41A9028D3BD61FAFDE972B31ABEF3C80FD97E9907C7DEBA66BD2F2'
if((Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash -ne $expected){throw 'FLOAT wrapper changed; review it before updating its pinned hash.'}
$private=Join-Path ([IO.Path]::GetTempPath()) ('nes-float-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $private | Out-Null
function Quote-Literal([string]$s){return "'"+$s.Replace("'","''")+"'"}
# Preserve historical wrapper/server logs: only its private working directory changes.
$original=[IO.File]::ReadAllText($wrapper)
$needle='$probeDir=Join-Path $env:TEMP ''gbc-salt-floating-probe'''
if(-not $original.Contains($needle)){throw 'Unexpected FLOAT wrapper output path.'}
$copy=$original.Replace($needle,('$probeDir='+ (Quote-Literal (Join-Path $private 'server'))))
$privateWrapper=Join-Path $private 'float.ps1'
[IO.File]::WriteAllText($privateWrapper,$copy,[Text.UTF8Encoding]::new($true))
$job=Join-Path $private 'job.ps1'
$arguments=@($pythonPath,'-B','-X','utf8',(Join-Path $PSScriptRoot $driver),'--out',$output,'--questa-bin',$questa)

$command='& '+(($arguments | ForEach-Object {Quote-Literal $_}) -join ' ')
$body='$ErrorActionPreference=''Stop'''+"`n"+'Set-Location -LiteralPath '+(Quote-Literal $root)+"`n"+$command+"`n"+'if($LASTEXITCODE -ne 0){throw "NES functional command failed ($LASTEXITCODE); see raw output logs."}'+"`n"
[IO.File]::WriteAllText($job,$body,[Text.UTF8Encoding]::new($true))
# Child shell contains all environment changes. Existing wrapper owns server startup/finally shutdown.
& pwsh -NoProfile -File $privateWrapper -RunOnly -AfterSmokeScript $job -QuestaBin $questa *> (Join-Path $private 'wrapper-output.log')
$code=$LASTEXITCODE
if(Test-Path -LiteralPath $output){
 $audit=@{wrapper_sha256=$expected.ToLower();mode='RunOnly';license='existing free Starter FLOAT';exit_code=$code;private_runtime=$private}
 $audit | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'license-route.local.json') -Encoding utf8
}
if($code -ne 0){throw "NES job failed ($code). Inspect compile.log and per-case simulation logs; do not fall back to an uncounted license."}

if($code -eq 0){Write-Output 'PASS diagnostic memory timing job through existing FLOAT route; see simulation result.'}
