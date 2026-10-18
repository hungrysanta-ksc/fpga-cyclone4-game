# SPDX-License-Identifier: MIT
param([Parameter(Mandatory)][string]$Out,[int]$Last=975)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$base=Split-Path $root -Parent
$wrapper=Join-Path $base 'probes/questa-license/probe_float.ps1'
$expected='C08B0ABF2B41A9028D3BD61FAFDE972B31ABEF3C80FD97E9907C7DEBA66BD2F2'
if((Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash -ne $expected){throw 'Verified FLOAT wrapper changed.'}
if(Get-NetTCPConnection -LocalPort 18000 -State Listen -ErrorAction SilentlyContinue){throw 'FLOAT port already in use; leave its owner running.'}
$private=Join-Path ([IO.Path]::GetTempPath()) ('nes-source243-float-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $private | Out-Null
function Q([string]$s){return "'"+$s.Replace("'","''")+"'"}
$text=[IO.File]::ReadAllText($wrapper)
$needle='$probeDir=Join-Path $env:TEMP ''gbc-salt-floating-probe'''
if(-not $text.Contains($needle)){throw 'Unexpected wrapper path.'}
$text=$text.Replace($needle,('$probeDir='+(Q (Join-Path $private 'server'))))
$copy=Join-Path $private 'float.ps1'
[IO.File]::WriteAllText($copy,$text,[Text.UTF8Encoding]::new($true))
$python='C:/Users/mohallo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$questa='C:/altera_standard/25.1std/questa_fse/win64'
$script='test_nes_operand243.py'
$argsList=@($python,'-B','-X','utf8',(Join-Path $PSScriptRoot $script),'--out',[IO.Path]::GetFullPath($Out),'--questa-bin',$questa)

$body='$ErrorActionPreference=''Stop'''+"`n"+'Set-Location -LiteralPath '+(Q $root)+"`n"+'& '+(($argsList | ForEach-Object {Q $_}) -join ' ')+"`n"+'if($LASTEXITCODE -ne 0){throw "Operand243 test failed; inspect its raw logs."}'+"`n"
$job=Join-Path $private 'job.ps1'
[IO.File]::WriteAllText($job,$body,[Text.UTF8Encoding]::new($true))
& pwsh -NoProfile -File $copy -RunOnly -AfterSmokeScript $job -QuestaBin $questa
if($LASTEXITCODE -ne 0){throw 'Operand243 failed; no fallback to uncounted license.'}
