# SPDX-License-Identifier: MIT
"""One whole-board Lite MAP: charge STOP ownership on cleaned268 boundary."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,sha,once
from nes_joint269 import flow_patch


def rom_patch(src):
 s=src['nes_sink_bus165.sv']
 s=once(s,'parameter ROM_ONLY=0)', 'parameter ROM_ONLY=0,parameter KEEP_ROM=0)')
 s=once(s,'wire read_active=active&&!reset&&!read_n&&write_n;', 'wire read_active=((active&&!reset)||(ROM_ONLY&&KEEP_ROM&&rom_select))&&!read_n&&write_n;')
 s=once(s,'   address_meta<=0;address_sync<=0;address_previous<=0;', '   address_previous<=0;')
 s=once(s,'   address_meta<=address;address_sync<=address_meta;address_previous<=address_sync;', '   address_previous<=address_sync;')
 s=once(s,' always @(posedge clk)begin rom_data<=', ''' generate if(KEEP_ROM)begin
  always @(posedge clk)begin address_meta<=address;address_sync<=address_meta;end
 end else begin
  always @(posedge clk or posedge reset)begin
   if(reset)begin address_meta<=0;address_sync<=0;end
   else begin address_meta<=address;address_sync<=address_meta;end
  end
 end endgenerate
 always @(posedge clk)begin rom_data<=''')
 src['nes_sink_bus165.sv']=s
 s=src['nes_sink_bridge165.sv']
 s=once(s,'module nes_sink_bridge165(', 'module nes_sink_bridge165 #(parameter KEEP_ROM=0)(')
 s=once(s,'#(.ROM_ONLY(1))', '#(.ROM_ONLY(1),.KEEP_ROM(KEEP_ROM))')
 s=once(s," assign oe_n=raw_cancel?1'b1:bus_oe;\n assign dir=!raw_cancel&&bus_dir;", ''' wire program_read=KEEP_ROM&&address[23:16]==0&&address[15]&&!romsel_n&&!read_n&&write_n;
 assign oe_n=(raw_cancel&&!program_read)?1'b1:bus_oe;
 assign dir=(!raw_cancel||program_read)&&bus_dir;''')
 src['nes_sink_bridge165.sv']=s
 return src


def top_patch(s):
 s=once(s,'nes_sink_bridge165 sink(', 'nes_sink_bridge165 #(.KEEP_ROM(1)) sink(')
 s=once(s,' assign consumer_oe=core_reset||(sink_oe204==bus_oe_n);', ''' // Configuration owns the local program ROM even while RUN is stopped.
 // Keep only program/status reads alive; raw power/clock loss still disables IO.
 wire stop_read269=!SNES_READ_IN&&SNES_WRITE_IN&&SNES_ADDR_IN[23:16]==0&&
   ((SNES_ADDR_IN[15]&&!SNES_ROMSEL_IN)||SNES_ADDR_IN==24'h006001);
 assign consumer_oe=power_reset||!host_locked||(core_reset&&!stop_read269)||(sink_oe204==bus_oe_n);''')
 return s


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 old=BASE/'probes/nes-joint268/board01';pins={}
 for f in old.rglob('*'):
  rel=f.relative_to(old)
  if any(x in ('work','db','incremental_db','output_files') for x in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   t=d/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);pins[rel.as_posix()]=sha(f)
 (d/'nes_mux260.sv').write_text(flow_patch((d/'nes_mux260.sv').read_text()),encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/Path(__file__).name)
 for n,s in rom_patch({n:(d/n).read_text() for n in ['nes_sink_bus165.sv','nes_sink_bridge165.sv']}).items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 (d/'fxpak_nes_screen137_top.sv').write_text(top_patch((d/'fxpak_nes_screen137_top.sv').read_text()),encoding='utf-8',newline='\n')
 with (d/'map.log').open('wb') as f:r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 result=dict(passed=r.returncode==0 and not undriven,summary=(d/'output_files/board.map.summary').read_text(),input_hashes=pins,changed_hashes={n:sha(d/n) for n in ['nes_mux260.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','fxpak_nes_screen137_top.sv']},script_sha256=sha(Path(__file__)),undriven_outputs=undriven,FIT=False,STA=False,scope=__doc__)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['summary']);assert result['passed']


if __name__=='__main__':main()
