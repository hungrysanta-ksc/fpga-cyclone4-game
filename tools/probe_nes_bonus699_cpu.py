"""Actual selected T65 executes target ROM FB29..FB34 and F794=7E.

Only reset vector and a RAM setup stub are fixture inputs. CHR and the ROM IRQ
instruction/data bytes are unchanged. PPU boundary/OAM phases are controlled;
this is not a full-game boot or the board's host/tile traffic simulation.
"""
from pathlib import Path
import argparse,json,shutil
import probe_nes_bonus698_boundary as boundary
import probe_nes_bonus698 as base

BODY=r'''
 reg [8:0] dot699=249;reg render699=0,ce699=0;
 reg [7:0] oam699=8'hff;
 integer scenario,tick699,start699,step699,failed,checked,first_raw,commit_tick,old_requests,new_requests;
 reg [63:0] first_fault,first_ppu;
 initial begin
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr);
  // Private fixture reset vector; the actual ROM code and CHR stay untouched.
  prg['h3fffc]='h00;prg['h3fffd]='h04;
  force dut.core.ppu.cycle=dot699;force dut.core.ppu.scanline=9'd192;
  force dut.core.ppu.bg_patt1=0;force dut.core.ppu.obj_size1=1;force dut.core.ppu.obj_patt1=1;
  force dut.core.ppu.is_rendering_d=render699;force dut.core.ppu.is_rendering=render699;
  force dut.core.ppu.rendering_enabled=render699;
  force dut.core.ppu.oam_bus=oam699;force dut.core.ppu.in_range=(scenario>=4);
  force dut.core.ppu.vram=15'd0;force dut.core.ppu.read_2007_delayed=0;force dut.core.ppu.write_2007_delayed=0;
  force dut.core.ppu.ce=ce699;force dut.core.ppu.read=0;force dut.core.ppu.write=0;force tap_ce=ce699;
  for(scenario=0;scenario<8;scenario++)begin
   @(negedge clk);reset_request=1;render699=0;ce699=0;dot699=249;
   repeat(8)@(negedge clk);reset_request=0;
   wait(memory_ready);@(negedge clk);
   // SEI; LDA45/STA8000; LDA23/STA8001; LDY03; LDX00; JMP FB29.
   local_memory.cpu_ram.mem['h400]='h78;
   local_memory.cpu_ram.mem['h401]='ha9;local_memory.cpu_ram.mem['h402]='h45;
   local_memory.cpu_ram.mem['h403]='h8d;local_memory.cpu_ram.mem['h404]='h00;local_memory.cpu_ram.mem['h405]='h80;
   local_memory.cpu_ram.mem['h406]='ha9;local_memory.cpu_ram.mem['h407]='h23;
   local_memory.cpu_ram.mem['h408]='h8d;local_memory.cpu_ram.mem['h409]='h01;local_memory.cpu_ram.mem['h40a]='h80;
   local_memory.cpu_ram.mem['h40b]='ha0;local_memory.cpu_ram.mem['h40c]='h03;
   local_memory.cpu_ram.mem['h40d]='ha2;local_memory.cpu_ram.mem['h40e]='h00;
   local_memory.cpu_ram.mem['h40f]='h4c;local_memory.cpu_ram.mem['h410]='h29;local_memory.cpu_ram.mem['h411]='hfb;
   failed=0;checked=0;start699=-1;first_raw=-1;commit_tick=-1;old_requests=0;new_requests=0;
   first_fault=0;first_ppu=0;
   for(tick699=0;tick699<2000;tick699++)begin
    @(negedge clk);
    if(start699<0 && dut.core.cpu_rnw && dut.core.cpu_addr_full==24'hf794)start699=tick699;
    step699=start699<0?-1:tick699-start699-9+(scenario%4);
    dot699=step699<0?249:249+step699/4;ce699=step699>=0 && step699%4==3;
    render699=step699>=32;
    // Captured dummy Y=F8 and an in-range sprite Y=B8. Identical lower
    // fine-row/attribute/tile bits make both fetch the real target 1FE7.
    oam699=dot699==257?(scenario<4?8'hf8:8'hb8):8'hff;
    @(posedge clk);
    if(start699>=0 && !dut.core.cpu_rnw && dut.core.cpu_addr_full==24'h8001 && dut.core.cpu_dout==8'h7e)begin
     if(first_raw<0)first_raw=step699;
     if(dut.core.cart_ce)commit_tick=step699;
    end
    if(rom_request && rom_address==22'h208fe7)old_requests++;
    if(rom_request && rom_address==22'h21fbe7)new_requests++;
    if(fault_trigger&&!failed)begin failed=1;first_fault=fault_context;first_ppu=ppu_fault_state154;end
    if(ce699&&ppumem_read&&ppumem_addr>=22'h200000&&ppumem_addr<22'h220000&&!failed)begin
     if(ppumem_addr!==dut.core.chr_linaddr || ppumem_addr!==22'h21fbe7 || native_chr_logical!==14'h1fe7)
      $fatal(1,"sample did not use independent committed mapper address");
     if(!rom_ppu_valid||ppumem_din!==chr[ppumem_addr[16:0]])$fatal(1,"CPU independent CHR byte mismatch");checked++;
    end
    if(start699>=0)$display("CPU699 scenario=%0d step=%0d div=%0d cpu=%h/%b/%h dot=%0d logical=%h mapped=%h req=%b/%h reply=%b/%h bank=%h fault=%b",
     scenario,step699,dut.core.div_cpu,dut.core.cpu_addr_full,dut.core.cpu_rnw,dut.core.cpu_dout,
     dot699,native_chr_logical,ppumem_addr,rom_request,rom_address,rom_response,rom_response_address,dut.core.multi_mapper.mapper.chr_bank_5,fault_trigger);
    if(step699>=59)break;
   end
   if(start699<0||first_raw<0||commit_tick<0)$fatal(1,"Actual T65 did not execute target write");
   $display("CASE699CPU scenario=%0d failed=%0d error=%0d raw=%0d commit=%0d checked=%0d old=%0d new=%0d context=%h ppu=%h",
    scenario,failed,rom_error_code,first_raw,commit_tick,checked,old_requests,new_requests,first_fault,first_ppu);
   @(negedge clk);reset_request=1;render699=0;ce699=0;
   repeat(20)@(negedge clk);
   if(rom_fault||rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"CPU STOP did not quiesce");
  end
  $display("DONE698 actual T65 target ROM, independent bytes and STOP");$finish;
 end
 initial begin #10000000;$fatal(1,"CPU boundary watchdog");end
endmodule
'''

def prepare(board,rom,out,phase,arbiter=False):
    boundary.prepare(board,rom,out,phase)
    p=out/'game147_tb.sv';s=p.read_text();s=s[:s.index(' reg [8:0] dot698=249;')]+BODY
    if arbiter:
        s=s.replace('.native_fill_slot(),','.native_fill_slot(native_fill_slot699),',1)
        s=s.replace(' nes_probe dut(', ' wire native_fill_slot699,native_core_safe699;\n nes_probe dut(',1)
        s=s.replace('nes_rom_early rom_service(', 'nes_rom_early rom_service(.native_core_safe(native_core_safe699),',1)
        start=s.index(' nes_rom_physical #');end=s.index(' reg [7:0] prg',start)
        physical=s[start:end]
        for n in ('ready','request','address','response','error','response_address','data'):
            physical=physical.replace('(rom_'+n+')','(mem_'+n+'699)')
        s=s[:start]+r'''
 wire mem_ready699,mem_request699,mem_response699,mem_error699;
 wire [21:0] mem_address699,mem_response_address699;wire [7:0] mem_data699;
 wire fill_ready699,fill_response699,fill_error699,arbiter_fault699;
 wire [21:0] fill_response_address699;wire [15:0] fill_response_generation699;wire [7:0] fill_data699;
 integer grants699=0,replies699=0;
 nes_native_arbiter165 #(.SOURCE_HOLDS_KEY(1)) arbiter(
 .clk(clk),.reset(reset),.slot(native_fill_slot699),.core_safe(native_core_safe699),
 .core_request(rom_request),.core_address(rom_address),.core_ready(rom_ready),.core_response(rom_response),.core_error(rom_error),.core_response_address(rom_response_address),.core_data(rom_data),
 .fill_request(1'b1),.fill_abort(reset),.fill_address(22'h200100),.fill_generation(16'd699),.fill_ready(fill_ready699),.fill_idle(),.fill_response(fill_response699),.fill_error(fill_error699),.fill_response_address(fill_response_address699),.fill_response_generation(fill_response_generation699),.fill_data(fill_data699),
 .mem_ready(mem_ready699),.mem_request(mem_request699),.mem_address(mem_address699),.mem_response(mem_response699),.mem_error(mem_error699),.mem_response_address(mem_response_address699),.mem_data(mem_data699),.fault(arbiter_fault699));
 always @(posedge clk)if(!reset)begin
  if(arbiter_fault699)$fatal(1,"actual arbiter fault");
  if(fill_ready699)begin
   if(!native_fill_slot699||!native_core_safe699||rom_request)$fatal(1,"unqualified fill");
   if(start699>=0)$fatal(1,"fill entered rendering boundary");grants699++;
  end
  if(fill_response699)begin
   if(fill_error699||fill_response_address699!=22'h200100||fill_response_generation699!=699||fill_data699!==chr['h100])$fatal(1,"fill receipt mismatch");replies699++;
  end
 end
'''+physical+s[end:]
        s=s.replace('reg [8:0] dot699=249;', 'reg [8:0] line699=243,dot699=249;')
        s=s.replace("force dut.core.ppu.scanline=9'd192",'force dut.core.ppu.scanline=line699')
        s=s.replace("local_memory.cpu_ram.mem['h40f]='h4c;local_memory.cpu_ram.mem['h410]='h29;local_memory.cpu_ram.mem['h411]='hfb;", """local_memory.cpu_ram.mem['h40f]='had;local_memory.cpu_ram.mem['h410]='h93;local_memory.cpu_ram.mem['h411]='hf7;
   local_memory.cpu_ram.mem['h412]='had;local_memory.cpu_ram.mem['h413]='h93;local_memory.cpu_ram.mem['h414]='hf7;
   local_memory.cpu_ram.mem['h415]='h4c;local_memory.cpu_ram.mem['h416]='h29;local_memory.cpu_ram.mem['h417]='hfb;""")
        s=s.replace('failed=0;checked=0;start699=-1;', 'grants699=0;replies699=0;line699=243;failed=0;checked=0;start699=-1;')
        s=s.replace('step699=start699<0?', 'line699=start699<0?243:192;\n    step699=start699<0?')
        s=s.replace('if(start699<0||first_raw<0', 'if(grants699<1||replies699!=grants699)$fatal(1,"missing actual fill competition");\n   $display("FILL699 grants=%0d replies=%0d",grants699,replies699);\n   if(start699<0||first_raw<0')
        # Questa requires the monitor's referenced bench variables declared first.
        a=s.index(' always @(posedge clk)if(!reset)begin');b=s.index(' nes_rom_physical #',a)
        monitor=s[a:b];s=s[:a]+s[b:]
        s=s.replace(' initial begin\n  $readmemh',monitor+' initial begin\n  $readmemh',1)
        shutil.copyfile(board/'nes_native_arbiter165.sv',out/'nes_native_arbiter165.sv')
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m['stage']=699;m['scope']=__doc__
    m['sources']['game147_tb.sv']=base.sha(p)
    if arbiter:m['sources']['nes_native_arbiter165.sv']=base.sha(out/'nes_native_arbiter165.sv')
    m['actual_arbiter']=arbiter
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5)
    p.add_argument('--arbiter',action='store_true')
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase,a.arbiter)
