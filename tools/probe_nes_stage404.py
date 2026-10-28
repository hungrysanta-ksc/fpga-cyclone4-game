# SPDX-License-Identifier: MIT
"""Check a staging scratch-sharing candidate; not a whole-controller replacement."""
import argparse
import hashlib
import json
from pathlib import Path

from nes_delta231 import BASE
from probe_nes_joint396_edges import STAGE


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    d = a.out.resolve()
    d.mkdir(parents=True, exist_ok=False)
    original = (BASE / 'probes/nes-joint402/build07/nes_stage396.sv').read_text()
    # The existing arbiter prevents P_STAMP and B_CAP from running together.
    # Keep all other staging control, RAM ports, and published ABI unchanged.
    candidate = original.replace('reg [31:0] token,stamp;', 'reg [31:0] token,stamp;')
    assert candidate.count('reg [31:0] copied_stamp;') == 1
    candidate = candidate.replace('reg [31:0] copied_stamp;', '')
    candidate = candidate.replace('copied_stamp', 'stamp')
    # The original resets both registers; after sharing reset only once.
    candidate = candidate.replace('stamp<=0;copied_length<=0;bs<=B_IDLE;bind_lane<=0;stamp<=0;',
                                  'copied_length<=0;bs<=B_IDLE;bind_lane<=0;stamp<=0;')
    assert 'copied_stamp' not in candidate
    (d / 'nes_stage396.sv').write_text(candidate, newline='\n')
    tb = STAGE.replace('nes_stage396 dut(.*);',
                       '''reg meta_pause398=0; wire meta_atomic398;
 integer arbiter_cycle=0, read_pauses=0, bind_pauses=0;
 always @(negedge clk) begin
  arbiter_cycle=arbiter_cycle+1;
  meta_pause398=(arbiter_cycle%7)<3;
  if(meta_pause398 && dut.ps==dut.P_READ) read_pauses=read_pauses+1;
  if(meta_pause398 && dut.binding && dut.bs==dut.B_READ) bind_pauses=bind_pauses+1;
 end
 nes_stage396 dut(.*);''')
    tb = tb.replace('for(integer i=0;i<112;i++)tile(i);', '''
  // Commit a second tile in the same cycle as consumption of the first.
  tile(0); open_job(1,32,0);
  fork
   tile(1);
   begin
    wait(dut.ps==dut.P_RETURN); @(negedge clk); consume=1; consume_token=begin_token;
    tick(); @(negedge clk); consume=0; begin_token++;
   end
  join
  if(dut.used!=32 || dut.stamps!=1 || dut.head!=32)
   $fatal(1,"simultaneous commit/consume lost an event");
  open_job(1,32,1); verify(1,32,1);
  if(!tile_empty)$fatal(1,"simultaneous case not drained");
  @(negedge clk);reset=1;repeat(3)tick();@(negedge clk);reset=0;
  for(integer i=0;i<112;i++)tile(i);''')
    tb = tb.replace('$display("STAGE396 PASS', '''if(read_pauses==0 || bind_pauses==0)$fatal(1,"metadata pause not exercised");
  $display("STAGE404 pauses read=%0d bind=%0d",read_pauses,bind_pauses);
  $display("STAGE396 PASS''')
    tb = tb.replace('initial begin #2000000;', '''
 always @(posedge clk) if (!reset && active) begin
  if (dut.ps != dut.P_IDLE && dut.binding && dut.bs == dut.B_CAP)
   $fatal(1, "copy and bind share scratch simultaneously");
 end
 initial begin #2000000;''')
    (d / 'stage404_tb.sv').write_text(tb, newline='\n')
    job = '''$ErrorActionPreference='Stop'
$out='%s'
$tmp=Join-Path $env:TEMP ('nes-stage404-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
Copy-Item -LiteralPath (Join-Path $out 'nes_stage396.sv'),(Join-Path $out 'stage404_tb.sv') -Destination $tmp
Set-Location -LiteralPath $tmp
try {
& 'C:/altera_standard/25.1std/questa_fse/win64/vlib.exe' work *> vlib.log
if($LASTEXITCODE -ne 0){throw 'vlib failed'}
& 'C:/altera_standard/25.1std/questa_fse/win64/vlog.exe' -sv nes_stage396.sv stage404_tb.sv *> vlog.log
if($LASTEXITCODE -ne 0){throw 'vlog failed'}
& 'C:/altera_standard/25.1std/questa_fse/win64/vsim.exe' -c work.stage396_tb -do 'onerror {quit -code 1};run -all;quit -f' *> simulation.log
if($LASTEXITCODE -ne 0){throw 'simulation failed'}
if(-not (Select-String -Quiet -Path simulation.log -Pattern 'STAGE396 PASS')){throw 'missing PASS'}
} finally { Copy-Item -Path '*.log' -Destination $out -ErrorAction SilentlyContinue }
''' % str(d).replace("'", "''")
    (d / 'job.ps1').write_text(job, encoding='utf-8-sig', newline='\n')
    print(json.dumps({'baseline': digest(BASE / 'probes/nes-joint402/build07/nes_stage396.sv'),
                      'candidate': digest(d / 'nes_stage396.sv'), 'out': str(d)}))


if __name__ == '__main__':
    main()
