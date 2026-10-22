# SPDX-License-Identifier: MIT
"""Live logical RTL/65816 file-bus coupling for one real map range.

The host bus is stretched by RPC. CPU clock counts and RTL counts are separate;
they are NOT a physical timing result. Remaining255 frame output uses fixtures.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, struct, subprocess, time
from nes_slice257 import sources
from nes_delta231 import ROOT, BASE, sha, once
from probe_nes_joint255 import tb as prior_tb
from build_nes_trace_replay import Code


EXTRA = r'''
 parameter integer SG=0;
 reg os=1,oc=0,om=0;wire omi;
 reg [23:0] bus_address=0;reg bus_read=1,bus_write=1;reg [7:0] bus_in=0;
 wire [7:0] bus_out;wire bus_valid;
 wire rv,rdone,rack,flow_retired,staged,receipt_committed,flow_fault;
 wire [11:0] rf,range_count257;wire idready;
 reg idvalid=0,target_started=0,target_waiting=0,finished257=0;
 wire lease_valid,lease_fault,waiting_display,retire_permitted,export_permitted;
 wire [15:0] display_gen;wire [31:0] display_epoch;
 nes_capture_lease201 lease(.clk(clk),.reset(reset),.stop(test_abort||flow_fault||source_fault!=0),.capture_begin(capture_begin),
 .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
 .export_release(source_done),.export_error(source_fault),.source_ready(1'b1),.source_is_rom(1'b1),
 .source_writing(test_drop),.live_epoch(32'd1),.reader_drained(1'b1),.retire_commit(rack),.retire_generation(display_gen),
 .release_frame(effective_release),.lease_valid(lease_valid),.retire_permitted(retire_permitted),
 .export_permitted(export_permitted),.captured_epoch(display_epoch),.captured_generation(display_gen),.waiting_display(waiting_display),.fault(lease_fault));
 nes_range257 flow(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.cancel(test_abort||lease_fault||source_fault!=0),
 .identity_valid(idvalid),.identity_ready(idready),.serial(serial),.generation(display_gen),.bank(1'b0),
 .SPI_SS(os),.SPI_SCK(oc),.SPI_MOSI(om),.miso(omi),
 .address(bus_address),.read_n(bus_read),.write_n(bus_write),.data_in(bus_in),.data_out(bus_out),.bus_valid(bus_valid),
 .range_valid(rv),.range_ready(v_ready),.range_first(rf),.range_count(range_count257),.range_dma_done(rdone),
 .sealed(v_sealed),.core_idle(start_ready),.display_ack(rack),.retired(flow_retired),
 .staged(staged),.receipt_committed(receipt_committed),.fault(flow_fault));
 integer eventfd,nes_ticks=0;reg prior_staged=0,prior_receipt=0,prior_seal=0;
 always @(posedge clk)begin
  nes_ticks++;
  if(!reset)begin
   if(source_done)$fwrite(eventfd,"input_done,%0d\n",nes_ticks);
   if(staged&&!prior_staged)$fwrite(eventfd,"staged,%0d\n",nes_ticks);
   if(rv&&v_ready)$fwrite(eventfd,"dma_done_range,%0d\n",nes_ticks);
   if(receipt_committed&&!prior_receipt)$fwrite(eventfd,"receipt,%0d\n",nes_ticks);
   if(v_sealed&&!prior_seal)$fwrite(eventfd,"sealed,%0d\n",nes_ticks);
   if(rack)$fwrite(eventfd,"display_ack,%0d\n",nes_ticks);
   if(flow_fault&&!SG)$fatal(1,"FLOW257 fault state=%0d queue=%0d",flow.state,flow.qfault);
   if(lease_fault&&!SG)$fatal(1,"LEASE257 fault");
  end
  prior_staged<=staged;prior_receipt<=receipt_committed;prior_seal<=v_sealed;
 end
 reg [7:0] packet257[0:99];reg [7:0] saved_receipt[0:255];
 task output_byte(input reg [7:0] value);
 begin
  for(integer bitno=7;bitno>=0;bitno--)begin
   om=value[bitno];#190;oc=1;#190;oc=0;
  end
 end endtask
 task selected_range(input reg [63:0] desc);
 integer n,k,fd;reg [15:0] crc257;
 begin
  target_started=1;n=desc[11:0]*2;
  if(!lease_valid||owned||!waiting_display)$fatal(1,"collector not released into display lease");
  for(k=0;k<256;k++)saved_receipt[k]=dut.memory[562+k];
  for(k=0;k<100;k++)packet257[k]=0;
  packet257[0]=9;packet257[4]=serial[7:0];packet257[8]=display_gen[7:0];packet257[9]=display_gen[15:8];
  packet257[10]=desc[19:12];packet257[11]={4'd0,desc[23:20]};packet257[12]=n+4;packet257[14]=n;
  packet257[16]=1;packet257[18]=8'h57;packet257[19]=2;
  if(SG==8)packet257[8]=packet257[8]^1;
  if(SG==9)packet257[1]=1;
  for(k=0;k<n;k++)packet257[20+k]=stream_bytes[stream_at+k];
  fd=$fopen("selected.hex","w");for(k=0;k<n;k++)$fwrite(fd,"%02x\n",packet257[20+k]);$fclose(fd);
  fd=$fopen("selected-meta.txt","w");$fwrite(fd,"%0d %0d\n",desc[23:12],n);$fclose(fd);
  @(negedge host_clk);os=0;crc257=c16(16'hffff,8'he1);output_byte(8'he1);
  for(k=0;k<n+20;k++)begin output_byte(packet257[k]);crc257=c16(crc257,packet257[k]);end
  output_byte(crc257[15:8]);output_byte(crc257[7:0]^(SG==7));#190;os=1;
  wait(staged);repeat(32)@(negedge host_clk);
  if(flow.queue.retired!=1||flow.queue.accepted!=1)$fatal(1,"packet credit not retired after staging");
  for(k=0;k<256;k++)if(dut.memory[562+k]!==saved_receipt[k])$fatal(1,"early receipt at staging");
  target_waiting=1;
  while(!receipt_committed)begin
   @(negedge clk);
   if(!rv&&!rdone&&flow.ns==0&&flow.state==flow.DMA)
    for(k=0;k<256;k++)if(dut.memory[562+k]!==saved_receipt[k])$fatal(1,"early receipt before DMA token");
  end
  target_waiting=0;
  stream_at+=n;sink_at+=n;accepted+=n;ranges++;
 end endtask
'''


def testbench():
    s = prior_tb().replace('joint255_tb','slice257_tb').replace('nes_joint255 dut','nes_joint257 dut')
    s = once(s, ' wire exporter_release;wire release_frame=manual_release|exporter_release;',
             ' wire exporter_release,effective_release;wire release_frame=effective_release;')
    s = once(s, 'nes_joint257 dut(', EXTRA+'\n nes_joint257 dut(')
    s = once(s, 'nes_joint257 dut(', 'nes_joint257 dut(.display_lease(lease_valid),.display_generation(display_gen^{15\'d0,test_gen}),.display_epoch(display_epoch),.range_external(rv),.range_dma_done(rdone),')
    s = once(s, '.abort_source(test_abort)', '.abort_source(test_abort||flow_fault)')
    s = once(s, 'source_fault&&GUARD==0', 'source_fault&&GUARD==0&&SG==0')
    for name, value in [('v_range_valid','v_range_valid||rv'),('v_map_range','rv?1\'b1:v_map_range'),('v_first','rv?rf:v_first'),('v_count','rv?range_count257:v_count'),('v_display_ack','rack')]:
        s = once(s, f'.{name}({name})', f'.{name}({value})')
    s = once(s, '  while(op!=5)begin', '  while(op!=5)begin')
    s = once(s, '   if(GUARD==4)begin', '''
   if(op==2&&c[32]&&!target_started)begin selected_range(c);continue;end
   if(op==5)begin wait(flow_retired);@(negedge clk);continue;end
   if(GUARD==4)begin''')
    s = once(s, '   output_frame();', '''
   repeat(3)@(negedge clk);
   if(owned||!lease_valid)$fatal(1,"input/display phase lease mismatch");
   wait(idready);@(negedge clk);idvalid=1;@(negedge clk);idvalid=0;
   output_frame();''')
    s = once(s, '  repeat(4)@(negedge clk);reset=0;', '  eventfd=$fopen("events.csv","w");\n  repeat(4)@(negedge clk);reset=0;')
    s = once(s, '$display("PASS JOINT255 frames=%0d",frames);$finish;', '$display("PASS SLICE257 frames=%0d",frames);finished257=1;')
    return s


def rom(out):
    c = Code(0x8000)
    c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
    for a,v in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x2115,0x80)]:c.store(a,v)
    c.label('ready');c.absolute(0xad,0x6040);c.branch(0xf0,'ready')
    c.emit(0xc2,0x20);c.absolute(0xad,0x6044);c.emit(0x18,0x69,0,0x40);c.absolute(0x8d,0x2116)
    c.absolute(0xad,0x6042);c.absolute(0x8d,0x4305)
    c.emit(0xe2,0x20)
    for a,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
    def token():
        for i in range(4):c.absolute(0xad,0x6048+i);c.absolute(0x8d,0x604c+i)
    token();c.store(0x6050,0xa5)
    c.label('receipt');c.absolute(0xad,0x6051);c.branch(0xf0,'receipt')
    c.label('sealed');c.absolute(0xad,0x6052);c.branch(0xf0,'sealed')
    c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
    c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
    c.store(0x2107,0x40);c.store(0x2100,15)
    token();c.store(0x6058,0x5a)
    c.label('done');c.branch(0x80,'done')
    data=c.finish();r=bytearray([255])*32768;r[:len(data)]=data
    r[0x7fc0:0x7fd5]=b'NES257 RANGE DMA TEST '.ljust(21,b' ')[:21]
    r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
    checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum)
    (out/'slice.sfc').write_bytes(r)
    return len(data)


LUA = r'''
local seq=0
local trace=assert(io.open(OUT..'/cpu-bus.csv','w'))
local function rpc(op,a,v)
 seq=seq+1
 local f=assert(io.open(OUT..'/request.tmp','w'));f:write(string.format('%d %d %d',op,a,v or 0));f:close()
 assert(os.rename(OUT..'/request.tmp',OUT..'/req'..seq))
 local deadline=os.time()+90
 local answer=nil
 repeat answer=io.open(OUT..'/rsp'..seq,'r');assert(os.time()<deadline,'RTL RPC timeout')until answer
 local value=tonumber(answer:read('*a'));answer:close();assert(value and value>=0,'RTL rejected bus')
 trace:write(string.format('%d,%d,%d,%d,%d\n',seq,op,a,op==0 and value or v,emu.getState().masterClock));trace:flush()
 return value
end
local bytes={};local dma_start=nil;local dma_end=nil;local displayed=false
emu.addMemoryCallback(function(a,v)
 local x=rpc(0,a,0)
 if a>=0x400800 then bytes[#bytes+1]=x end
 return x
end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function(a,v)return rpc(0,a,0)end,emu.callbackType.read,0x6040,0x6052)
emu.addMemoryCallback(function(a,v)
 if a==0x6050 then dma_end=emu.getState().masterClock end
 if a==0x6058 then
  assert(displayed and dma_end and #bytes>0,'early final ACK')
  local meta=assert(io.open(OUT..'/selected-meta.txt','r'));local first,n=meta:read('*n','*n');meta:close()
  assert(#bytes==n)
  local exp=assert(io.open(OUT..'/selected.hex','r'));local i=0
  for line in exp:lines()do
   local expected=tonumber(line,16);assert(bytes[i+1]==expected,'RTL aperture byte mismatch')
   assert(emu.read(0x8000+first*2+i,emu.memType.snesVideoRam)==expected,'actual DMA VRAM mismatch');i=i+1
  end
  exp:close();assert(i==n)
 end
 rpc(1,a,v)
 if a==0x6058 then
  rpc(2,0,0)
  local f=assert(io.open(OUT..'/cpu-result.json','w'))
  f:write(string.format('{"passed":true,"dma_bytes":%d,"dma_start_master":%d,"consume_master":%d,"final_ack_master":%d}',#bytes,dma_start,dma_end,emu.getState().masterClock));f:close()
  trace:close();emu.stop(0)
 end
end,emu.callbackType.write,0x604c,0x6058)
emu.addMemoryCallback(function(a,v)dma_start=emu.getState().masterClock end,emu.callbackType.write,0x420b)
emu.addMemoryCallback(function(a,v)if v==0x40 then displayed=true end end,emu.callbackType.write,0x2107)
'''

TCL = r'''
onerror {quit -code 1}
set root sim:/slice257_tb
for {set n 0} {$n<1000} {incr n} {
 run 100 us
 if {[examine -radix unsigned $root/target_waiting] == 1} {break}
}
if {[examine -radix unsigned $root/target_waiting] != 1} {error "no staged range"}
set f [open ready.txt w];puts $f ready;close $f
set seq 1
while {$seq<100000} {
 if {![file exists req$seq]} {after 1;continue}
 set f [open req$seq r];set cmd [read $f];close $f
 lassign $cmd op address value
 if {$op==2} {
  run 100 us
  if {[examine -radix unsigned $root/finished257] != 1} {error "missing final RTL retirement"}
  set f [open rsp$seq.tmp w];puts $f 0;close $f
  file rename rsp$seq.tmp rsp$seq
  quit -code 0
 }
 force -deposit $root/bus_address 10#$address
 force -deposit $root/bus_in 10#$value
 if {$op==0} {force -deposit $root/bus_read 0} else {force -deposit $root/bus_write 0}
 run 200 ns
 if {$op==0} {
  if {[examine -radix unsigned $root/bus_valid] != 1} {error "invalid bus read"}
  set value [examine -radix unsigned $root/bus_out]
 }
 force -deposit $root/bus_read 1
 force -deposit $root/bus_write 1
 run 200 ns
 if {$op==0 && $value==0 && ($address==24657 || $address==24658)} {run 100 us}
 set f [open rsp$seq.tmp w];puts $f $value;close $f
 file rename rsp$seq.tmp rsp$seq
 incr seq
}
error "RPC count exceeded"
'''

GUARD_TCL = r'''
onerror {quit -code 1}
set root sim:/slice257_tb
proc val {name} {global root;return [examine -radix unsigned $root/$name]}
proc bus {op addr value} {
 global root
 force -deposit $root/bus_address 10#$addr
 force -deposit $root/bus_in 10#$value
 if {$op==0} {force -deposit $root/bus_read 0} else {force -deposit $root/bus_write 0}
 run 200 ns
 if {$op==0 && [val bus_valid]!=1} {error "guard invalid read"}
 force -deposit $root/bus_read 1
 force -deposit $root/bus_write 1
 run 200 ns
}
proc token {wrong} {
 bus 1 24652 [expr {1 ^ $wrong}]
 bus 1 24653 0
 bus 1 24654 87
 bus 1 24655 2
}
for {set n 0} {$n<1000} {incr n} {
 run 100 us
 if {[val target_waiting]==1 || [val source_fault]!=0} {break}
}
if {$case<7} {
 if {[val target_waiting]!=1} {error "guard no staged range"}
 if {$case==2 || $case==6} {
  for {set i 0} {$i<64} {incr i} {bus 0 [expr {4196352+$i}] 0}
 }
 if {$case==1 || $case==2 || $case==6} {
  token [expr {$case==2}];bus 1 24656 165
 }
 if {$case==3} {token 0;bus 1 24664 90}
 if {$case==4} {
  for {set i 0} {$i<8} {incr i} {bus 0 [expr {4196352+$i}] 0}
  force -deposit $root/test_abort 1
 }
 if {$case==5} {force -deposit $root/test_gen 1}
 if {$case==6} {
  run 2 us
  if {[val receipt_committed]!=1 || [val flow/read_count]!=64} {error "missing first receipt"}
  token 0;bus 1 24656 165
 }
 run 2 us
}
if {[val source_fault]==0 || [val rack]!=0 || [val flow_retired]!=0 || [val v_sealed]!=0 || [val staged]!=0 || [val waiting_display]!=0} {error "guard cancellation fault=[val source_fault] ack=[val rack] retired=[val flow_retired] sealed=[val v_sealed] staged=[val staged] lease=[val waiting_display]"}
set frozen {}
for {set i 0} {$i<1024} {incr i} {lappend frozen [examine -radix hex $root/dut/memory($i)]}
run 2 us
for {set i 0} {$i<1024} {incr i} {
 if {[lindex $frozen $i] ne [examine -radix hex $root/dut/memory($i)]} {error "RAM write after fault"}
}
puts "PASS SLICE257 GUARD $case fault=[val source_fault]"
quit -code 0
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--questa-bin',type=Path,required=True)
    p.add_argument('--guards',action='store_true')
    a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    d.mkdir(parents=True);pins={}
    def copy(f):
        pins[f.relative_to(BASE).as_posix()]=sha(f);shutil.copyfile(f,d/f.name)
    src=sources()
    for name,s in src.items():(d/name).write_text(s,encoding='utf-8',newline='\n')
    board=BASE/'probes/nes-counter224/mapfit02'
    for n in ['nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181','nes_native_mailbox206','nes_domain_reset124']:
        copy(board/(n+'.sv'));src[n+'.sv']=''
    for n in ['nes_capture_lease201','nes_bulk_aperture188']:
        copy(ROOT/'src/nes/rtl'/(n+'.sv'));src[n+'.sv']=''
    old=BASE/'probes/nes-joint255/test03'
    for n in ['commands.hex','expected.hex','certs.hex','hashes.hex','stream.hex','sink.hex','frame905.hex','frame905.palette','frame905.expected']:copy(old/n)
    for n in ['nes_slice257.py','probe_nes_slice257.py']:copy(ROOT/'tools'/n)
    (d/'slice257_tb.sv').write_text(testbench(),encoding='utf-8',newline='\n')
    body=rom(d)
    (d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\n'+LUA,encoding='utf-8',newline='\n')
    (d/'rpc.do').write_text(TCL,encoding='utf-8',newline='\n')
    def run(name,args):
        with (d/(name+'.log')).open('wb') as f:
            q=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(name+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-6000:]
    run('vlib',['work']);run('vlog',['-sv',*src,'slice257_tb.sv'])
    mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (d/'vsim.log').open('wb') as vf,(d/'mesen.log').open('wb') as mf:
        sim=subprocess.Popen([str(a.questa_bin/'vsim.exe'),'-c','-voptargs=+acc','work.slice257_tb','+LAST=905','-do','do rpc.do'],cwd=d,env=env,stdout=vf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        cpu=None
        try:
            deadline=time.monotonic()+120
            while not (d/'ready.txt').exists():
                assert sim.poll() is None,(d/'vsim.log').read_text(errors='replace')[-5000:]
                assert time.monotonic()<deadline,'RTL initialization timeout'
                time.sleep(.05)
            cpu=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(d/'slice.sfc'),'--timeout=180','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            deadline=time.monotonic()+200
            while cpu.poll() is None:
                if sim.poll() is not None:
                    assert sim.returncode==0,(d/'vsim.log').read_text(errors='replace')[-5000:]
                assert time.monotonic()<deadline,'CPU execution timeout'
                time.sleep(.05)
            cr=cpu.returncode;sr=sim.wait(timeout=10)
            assert cr==sr==0,(cr,sr,(d/'mesen.log').read_text(errors='replace')[-4000:],(d/'vsim.log').read_text(errors='replace')[-4000:])
        finally:
            for proc in (cpu,sim):
                if proc and proc.poll() is None:proc.kill();proc.wait()
    log=(d/'vsim.log').read_text(errors='replace')
    assert 'PASS SLICE257 frames=1' in log and not re.search(r'\*\* (Error|Fatal):',log)
    flat=bytearray()
    for line in (d/'blocks.txt').read_text().splitlines():
        frame,tok,n,hexdata=line.split();b=bytes.fromhex(hexdata);assert len(b)==int(n);flat+=b
    prior=BASE/'probes/nes-joint249/blocktest03'
    size=int((prior/'frame905.meta').read_text().split()[0])
    assert flat==bytes.fromhex((prior/'frame905.expected.hex').read_text())[:size]
    guards=[]
    if a.guards:
        for case in range(1,10):
            gd=d/f'guard{case:02}';gd.mkdir()
            for n in ['commands.hex','expected.hex','certs.hex','hashes.hex','stream.hex','sink.hex','frame905.hex','frame905.palette','frame905.expected']:
                shutil.copyfile(d/n,gd/n)
            (gd/'guard.do').write_text(f'set case {case}\n'+GUARD_TCL,encoding='utf-8',newline='\n')
            with (gd/'vmap.log').open('wb') as f:
                for args in (['-c'],['work',str(d/'work')]):
                    q=subprocess.run([str(a.questa_bin/'vmap.exe'),*args],cwd=gd,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    assert q.returncode==0
            with (gd/'vsim.log').open('wb') as f:
                q=subprocess.run([str(a.questa_bin/'vsim.exe'),'-c','-voptargs=+acc','work.slice257_tb',f'-gSG={case}','+LAST=905','-do','do guard.do'],cwd=gd,stdout=f,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
            gl=(gd/'vsim.log').read_text(errors='replace')
            assert q.returncode==0 and f'PASS SLICE257 GUARD {case} ' in gl,gl[-4000:]
            guards.append(case);print(f'PASS guard {case}',flush=True)
    result=dict(passed=True,scope=__doc__,cpu=json.loads((d/'cpu-result.json').read_text()),rom_body_bytes=body,
        rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,rom_sha256=sha(d/'slice.sfc'),
        mesen_sha256=sha(mesen),physical=False,full_ARM=False,whole_board=False,new_FIT=False,
        source_SPI_bytes=len(flat),guards=guards,other_ranges_and_H2='prior255 fixtures',timing='logical RPC with stretched host bus; no physical latency or60fps inference')
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result['cpu']))


if __name__=='__main__':main()
