# SPDX-License-Identifier: MIT
"""Replay the exact board collector/fill/export instantiations and query mux.

Only PPU interface stimulus, memory replies and host backpressure/ACK are models.
The direct board source fragments are pinned; this is not a physical SPI test.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def bench(board):
    j=(board/'nes_live_joint.sv').read_text()
    c=(ROOT/'tests/nes-functional/collect181_tb.sv').read_text()
    # Preserve exact live module instances and the arbitration mux declarations.
    blocks=[j[j.index('wire native_release_frame'):j.index('wire native_boot_miso')]]
    for first,last in [('wire [2:0] native_patch_count181;','nes_native_arbiter165 native_arbiter('),
                       ('wire [3:0] native_export_state177;','nes_native_mailbox165 #(.WIDTH(96))')]:
        blocks.append(j[j.index(first):j.index(last)])
    head=c[:c.index(' reg query=')]
    head=head.replace('module collect181_tb;','module board181_join_tb;').replace('release_frame=0,','')
    s=head+'\n'+'\n'.join(blocks)
    aliases={'tap_ce':'ppu_ce','cycle':'dot','native_bg_low':'bg_low','native_bg_high':'bg_high',
        'native_obj_low':'obj_low','native_obj_high':'obj_high','native_obj_valid':'obj_valid','native_extra_sprites':'extra_sprites',
        'tap_attribute':'bg_attribute','native_obj_attribute':'obj_attribute','native_obj_x':'obj_x',
        'ppumem_read':'ppu_read','rom_ppu_valid':'ppu_valid','native_chr_logical':'logical_address','ppumem_addr':'physical_address',
        'native_scroll_v':'scroll_v','native_scroll_t':'scroll_t','native_fine_x':'fine_x','native_pattern_mode':'pattern_mode',
        'native_display_mask':'display_mask','native_palette':'palette','native_scroll_access':'scroll_access'}
    widths={'tap_ce':1,'cycle':9,'native_bg_low':1,'native_bg_high':1,'native_obj_low':1,'native_obj_high':1,
        'native_obj_valid':1,'native_extra_sprites':1,'tap_attribute':2,'native_obj_attribute':8,'native_obj_x':8,
        'ppumem_read':1,'rom_ppu_valid':1,'native_chr_logical':14,'ppumem_addr':22,'native_scroll_v':15,'native_scroll_t':15,
        'native_fine_x':3,'native_pattern_mode':3,'native_display_mask':8,'native_palette':192,'native_scroll_access':1}
    # Insert aliases before their use for strict Questa declaration ordering.
    a='\n'.join('wire ['+str(widths[n]-1)+':0] '+n+'='+v+';' for n,v in aliases.items())+'\n'
    a+='wire [24:0] native_observe_errors180;wire native_collecting180;\n'
    s=head+'\n'+a+'\n'.join(blocks)
    tasks=c[c.index(' integer scenario='):c.index(' task readword')]
    tasks=tasks.replace('release_frame=1;','reset=1;').replace('release_frame=0;','reset=0;').replace('query=0;','')
    tasks=tasks.replace('wait(initialized)','wait(native_initialized)').replace('if(!owned)','if(!native_frame_owned)')
    tasks=tasks.replace('dut.','native_frame.')
    s+=tasks
    s+='''
reg memory_response=0;reg [21:0] memory_address=0;reg [15:0] memory_generation=0;reg [7:0] memory_data=0;
assign native_arbiter_fault=0;assign native_fill_ready=1;assign native_fill_idle=!memory_response;
assign native_fill_response=memory_response;assign native_fill_reply_address=memory_address;
assign native_fill_reply_generation=memory_generation;assign native_fill_data=memory_data;assign native_fill_mem_error=0;
reg ack=0;assign native_ack_valid=ack;assign native_ack_data={1'b1,native_generation};
integer clocks=0,raw=0,chr=0,begins=0,ends=0,completed=0,stalls=0,rawqueries=0,fillqueries=0;
reg ended_chr=0;reg [95:0] held;reg held_valid=0;
assign native_tx_ready=(clocks%11<6);
always @(posedge clk)begin
 memory_response<=native_fill_request;
 if(native_fill_request)begin memory_address<=native_fill_address;memory_generation<=native_fill_generation;memory_data<=native_fill_address[7:0]^8'h5a;end
 clocks<=clocks+1;ack<=0;
 if(!reset)begin
  if(native_fill_busy && native_response)$fatal(1,"fill response leaked to exporter");
  if(native_fill_query)fillqueries++;
  if(native_query && native_query_kind==7)rawqueries++;
  if(held_valid && (!native_tx_valid || native_tx_data!==held))$fatal(1,"unstable held record");
  held_valid<=native_tx_valid&&!native_tx_ready;held<=native_tx_data;
  if(native_tx_valid&&!native_tx_ready)stalls++;
  if(native_tx_valid&&native_tx_ready)begin
   case(native_tx_data[95:93])
    7:case(native_tx_data[76:64])
      0:begin if(native_tx_data[63:48]!=16'h1811 || native_tx_data[2:0]!=2)$fatal(1,"wrong header/patch count");begins++;end
      1:begin if(!ended_chr||raw!=512)$fatal(1,"early END");ends++;ack<=1;end
      2:$fatal(1,"unexpected ABORT %h",native_tx_data);
      3:completed++;
      4:begin if(ended_chr||chr==0)$fatal(1,"CHR end");ended_chr=1;end
      default:$fatal(1,"unknown control");endcase
    4:begin
       if(native_tx_data[76:64]==185 && native_tx_data[63:0]!==(64'd1<<49))$fatal(1,"first raw descriptor");
       if(native_tx_data[76:64]==186 && native_tx_data[63:0]!==((64'd1<<49)|(64'd1<<50)))$fatal(1,"second raw descriptor");
      end
    6:if(ended_chr)begin
       if(native_tx_data[76:64]!=raw || native_tx_data[63:0]!==64'(pixel(185+raw/256,raw%256)))$fatal(1,"raw color/address %0d",raw);
       raw++;
      end else chr++;
   endcase
  end
 end
end
initial begin
 repeat(3)tick();reset=0;clear(1);frame();
 wait(native_release_frame);repeat(5)tick();
 if(begins!=1||ends!=1||completed!=1||raw!=512||rawqueries!=512||fillqueries==0||stalls==0||native_frame_owned||native_fill_busy)
  $fatal(1,"join terminal begin%0d end%0d commit%0d raw%0d queries%0d/%0d",begins,ends,completed,raw,rawqueries,fillqueries);
 $display("PASS BOARD181JOIN raw=%0d chr=%0d fillqueries=%0d stalls=%0d commits=%0d",raw,chr,fillqueries,stalls,completed);$finish;
end
initial begin #30000000;$fatal(1,"join watchdog");end
endmodule
'''
    return s

def main():
    p=argparse.ArgumentParser()
    for n in ['board','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True)
    pins=json.loads((a.board/'preparation.json').read_bytes())['sources']
    names=['nes_native_planes165.sv','nes_native_fill165.sv','nes_native_export181.sv','nes_patch_rows181.sv',
        'nes_patch_capture181.sv','nes_native_frame181.sv','nes_native_compact181.sv','nes_native_raster181.sv']
    for n in names+['nes_live_joint.sv']:assert sha(a.board/n)==pins[n],n
    for n in names:shutil.copy2(a.board/n,a.out/n)
    (a.out/'bench.sv').write_text(bench(a.board),encoding='utf8')
    for exe,args in [('vlib',['work']),('vlog',['-sv',*names,'bench.sv']),
                     ('vsim',['-c','work.board181_join_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
        with (a.out/(exe+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        text=(a.out/(exe+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:]
    m=re.search(r'PASS BOARD181JOIN raw=(\d+) chr=(\d+) fillqueries=(\d+) stalls=(\d+) commits=(\d+)',text);assert m
    result=dict(passed=True,raw_pixels=int(m[1]),chr_bytes=int(m[2]),fill_queries=int(m[3]),backpressure_cycles=int(m[4]),commits=int(m[5]),
        sources={n:pins[n] for n in names+['nes_live_joint.sv']},runner_sha256=sha(Path(__file__)),
        generated_bench_sha256=sha(a.out/'bench.sv'),physical=False,scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])

if __name__=='__main__':main()
