# SPDX-License-Identifier: MIT
"""Run the joined geometry/raster lease on the actual SMB3 core.

This does not force CPU/PPU state, supply buttons or install firmware. Complete
CHR for subsequent PC comparison comes from the private ROM, not hardware fill.
"""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha
from nes_native_fetch165 import PORTS as FETCH_PORTS
from nes_native_frame165 import prepare,PORTS as FRAME_PORTS,BINDING,FILES
from nes_native_raster165 import PORTS as RASTER_PORTS

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--frames',type=int,default=20);a=p.parse_args()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost' and sha(a.rom)==ROM_SHA
 inputs=prepare(a.evidence,a.out);text=(ROOT/'tests/nes-functional/game147_tb.sv').read_text()
 def edit(old,new):
  nonlocal text
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
 edit('module game147_tb;','module native_frame165_tb;')
 ports=(FETCH_PORTS+RASTER_PORTS).replace('output wire','wire').replace('output reg','wire').replace(',\n',';\n')
 ports+='''wire [13:0] native_chr_logical;wire [21:0] game148_hint_physical;
 wire [63:0] ppu_fault_state154;wire game147_prefetch_hint,game160_restart_hint;
 wire [7:0] native_oam_address=0;wire [7:0] native_oam_data;wire native_oam_write;
'''
 edit('wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;',ports+'wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;')
 edit('nes_rom_early rom_service(','''nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),''')
 edit('if(frame<=2 || frame%10==0 || frame==target)fp=', 'if(frame>0)fp=')

 monitor=FRAME_PORTS.replace(',input wire',';input wire').replace(',output wire',';output wire').replace('input wire','reg').replace('output wire','wire').replace(',\n',';\n')
 monitor+=r'''
 integer native_dump_done=0,native_dump_frame,native_dump_file,native_states,k,q,limit;
 initial begin
  native_release_frame=0;native_query=0;native_query_kind=0;native_query_index=0;native_query_generation=0;
  native_states=$fopen("states.tsv","w");
  forever begin
   wait(native_frame_owned);@(negedge clk);native_dump_frame=frame;
   $fwrite(native_states,"%0d %0d %0d %07h %0d %0d %0d %0d %0d %0d\n",native_generation,frame,
    native_geometry_valid,native_errors,native_scroll_seen,native_row_count,native_group_count,native_object_count,native_exception_count,native_palette_count);
   $fflush(native_states);
   native_dump_file=$fopen($sformatf("frame-%0d.dump",frame),"w");
   $fwrite(native_dump_file,"H %0d %02h %0d %0d %0d %0d\n",native_geometry_valid,native_errors,
    native_row_count,native_group_count,native_object_count,native_exception_count);
   if(native_geometry_valid)begin
    for(k=0;k<7;k=k+1)begin
     case(k)
      0:limit=native_group_count*33;1,4:limit=224;2:limit=native_object_count;
      3:limit=native_exception_count;5:limit=native_palette_count*32;6:limit=8192;
     endcase
     for(q=0;q<limit;q=q+1)begin
      native_query=1;native_query_kind=k;native_query_index=q;native_query_generation=native_generation;
      @(negedge clk);if(!native_response || !native_hit)$fatal(1,"joined valid query failed kind=%0d index=%0d",k,q);
      $fwrite(native_dump_file,"%0d %0d %016h\n",k,q,native_data);native_query=0;@(negedge clk);
     end
    end
   end
   $fclose(native_dump_file);native_dump_done=native_dump_frame;
   native_release_frame=1;@(negedge clk);native_release_frame=0;wait(!native_frame_owned);
  end
 end
'''
 declarations,body=monitor.split(' initial begin',1)
 edit(' reg clk=0,mem_clk=0,reset_request=1;',declarations+'\n reg clk=0,mem_clk=0,reset_request=1;')
 edit('endmodule',' initial begin'+body+BINDING+'\nendmodule')
 edit('$display("PASS GAME147 frames=', 'wait(native_dump_done==frame);$display("PASS GAME147 frames=')
 (a.out/'native_frame165_tb.sv').write_text(text,encoding='utf8')
 image=a.rom.read_bytes()
 for n,b in [('prg',image[16:0x40010]),('chr',image[0x40010:])]:
  (a.out/(n+'.hex')).write_text(''.join(f'{v:02x}\n' for v in b))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 additions=FILES+['nes_native_ciram165.sv']
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,*additions,'native_frame165_tb.sv'],'vlog')
 s=run('vsim',['-c','work.native_frame165_tb',f'+FRAMES={a.frames}','-do','onerror {quit -code 1}; run -all; quit -f'],'core')
 assert 'PASS GAME147 frames=' in s
 result=dict(passed=True,rom_sha256=ROM_SHA,frames=a.frames,inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_native_frame165.py','tools/nes_native_frame165.py']+['src/nes/diagnostic/'+n for n in FILES]},
  raw_sha256={n:sha(a.out/n) for n in ['states.tsv','core.log']},
  scope='Joined fetch, compact and specialized raster directly driven by actual SMB3 CPU/PPU/MMC3/70ns reader. Preloaded ROM, no buttons; no physical CHR fill/host/SNES/fit proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual native stream collection',flush=True)
if __name__=='__main__':main()
