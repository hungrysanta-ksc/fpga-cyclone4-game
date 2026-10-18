# SPDX-License-Identifier: MIT
"""Compare current4KiB, direct8KiB and split5KiB receiver ROM storage.

Diagnostic generated RTL only. Same mask receiver bytes in8/5KiB; no FIT.
"""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile
from nes_delta231 import ROOT,sha,once

def sources(original):
 eight=once(original,'parameter PROGRAM_BYTES=4096','parameter PROGRAM_BYTES=8192')
 split=once(original,'module nes_sink_bus165 #(parameter PROGRAM_BYTES=4096)(', 'module nes_sink_bus165(')
 a=split.index(' // 194 may select8192;');b=split.index(' (* altera_attribute=',a)
 split=split[:a]+''' // Same synchronous read stage, explicit4096+1024 blocks.
 (* ramstyle="M9K" *) reg [7:0] program_lo[0:4095];
 (* ramstyle="M9K" *) reg [7:0] program_hi[0:1023];
 initial begin $readmemh("program-lo.hex",program_lo);$readmemh("program-hi.hex",program_hi);end
 reg [7:0] lo_q,hi_q;reg high_q;wire [7:0] rom_data=high_q?hi_q:lo_q;
 reg [23:0] tag;
'''+split[b:]
 split=once(split,'address[14:0]<(PROGRAM_BYTES-64)','address[14:0]<15\'d5056')
 split=once(split,'always @(posedge clk)begin rom_data<=program_rom[address_sync[ROM_BITS-1:0]];tag<=address_sync;end', '''always @(posedge clk)begin
  lo_q<=program_lo[address_sync[11:0]];hi_q<=program_hi[address_sync[9:0]];
  high_q<=address_sync[14:12]!=0;tag<=address_sync;
 end''')
 return {'current4k':original,'direct8k':eight,'split5k':split}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--client',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 client=bytes.fromhex((a.client/'sink-program.hex').read_text());old=bytes.fromhex((a.baseline/'sink-program.hex').read_text());assert len(client)==8192 and len(old)==4096
 body=(a.client/'body.bin').read_bytes();assert 96+len(body)<=5056
 lo=client[:4096];hi=bytearray(client[4096:5120]);hi[-64:]=client[-64:]
 # Exhaustive address projection over the entire LoROM window, including
 # all vectors, filled gaps and both sides of4096/5056. RTL tested separately.
 for addr in range(32768):
  ref=client[addr&8191] if addr<8128 or addr>=32704 else 255
  got=(lo[addr&4095] if addr<4096 else hi[addr&1023]) if addr<5056 or addr>=32704 else 255
  assert got==ref,hex(addr)
 original=ROOT/'src/nes/diagnostic/nes_sink_bus165.sv';variants=sources(original.read_text())
 results={};work=Path(tempfile.mkdtemp(prefix='nes-storage247-'));(out/'work-path.txt').write_text(str(work))
 try:
  for name,source in variants.items():
   d=work/name;d.mkdir();(d/'rom.sv').write_text(source,encoding='utf-8',newline='\n')
   for fn,data in [('sink-program.hex',old if name=='current4k' else client),('program-lo.hex',lo),('program-hi.hex',hi)]:
    (d/fn).write_text(''.join(f'{b:02x}\n' for b in data))
   (d/'source.qpf').write_text('PROJECT_REVISION = "source"\n')
   (d/'source.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_sink_bus165','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name SYSTEMVERILOG_FILE rom.sv'])+'\n')
   with (d/'map.log').open('wb') as log:
    q=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','source'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
   assert q.returncode==0,(name,(d/'map.log').read_text(errors='replace')[-5000:])
   report=(d/'output_files/source.map.rpt').read_text();summary=(d/'output_files/source.map.summary').read_text()
   results[name]=dict(summary=summary,rom_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and 'program_' in l],warnings=[l.strip() for l in (d/'map.log').read_text().splitlines() if 'Warning' in l],rtl_sha256=sha(d/'rom.sv'))
   print(name,summary,flush=True)
 finally:shutil.copytree(work,out/'runs',dirs_exist_ok=True)
 result=dict(passed=True,scope=__doc__,projection_addresses=32768,body_bytes=len(body),split_body_capacity=4960,split_body_free=4960-len(body),variants=results,fit=False,sta=False,physical=False,wholeboard_savings_proven=False,source_sha256=sha(original),client_sha256=sha(a.client/'sink-program.hex'),baseline_sha256=sha(a.baseline/'sink-program.hex'),script_sha256=sha(Path(__file__)))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(__file__,out/'builder.py')

if __name__=='__main__':main()
