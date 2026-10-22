# SPDX-License-Identifier: MIT
"""Actual collector/source/core and all ARM260 map batches, with explicit fixture boundaries.

Non-map accepted streams, H2 and manifests remain pinned255 fixtures. The bus
service model charges500 master clocks/setup and400ns/byte; it is not a CPU.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,struct
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint261 import sources
from probe_nes_joint255 import tb as prior_tb

EXTRA=r'''
 parameter integer RPC=0,NEG=0,WINDOW=4;
 reg [23:0] bus_address=0;reg bus_read=1,bus_write=1;reg [7:0] bus_in=0;
 wire [7:0] bus_out;wire bus_valid,lease_valid,waiting_display,lease_fault,flow_fault,flow_retired,rack,staged,receipt_committed,idready;
 reg idvalid=0,ev=0;wire er;wire [31:0] next_token;
 reg target_waiting=0,finished261=0;integer map_at=0,map_batches=0,map_ranges=0,map_bytes=0;
 reg [7:0] packet261[0:255],map_mem[0:65535],map_expected[0:4095],map_actual[0:4095];
 integer lens261[0:255],packet_count,packet_seq261=0,mapfd,events261,receipt_ticks=0,receipt_start=0;
 realtime source_end261,output_end261;
 always @(posedge clk)if(!reset)begin
  if((flow_fault||lease_fault)&&!NEG)$fatal(1,"joint261 flow/lease fault %0d %0d state=%0d",flow_fault,lease_fault,dut.flow.state);
  if(dut.source_selected&&dut.output_selected)$fatal(1,"shared SPI double owner");
  if(dut.rv&&v_ready)receipt_start=$time;
  if(dut.flow.ns==2&&v_ready)begin receipt_ticks++;$fwrite(events261,"receipt,%0d,%0t,%0t\n",f,$time,$time-receipt_start);end
 end
 task rd261(input [23:0] a,output reg [7:0] b);begin
  @(negedge host_clk);bus_address=a;bus_read=0;#200;if(!bus_valid)$fatal(1,"invalid bus %h",a);b=bus_out;bus_read=1;#200;
 end endtask
 task wr261(input [23:0] a,input [7:0] b);begin
  @(negedge host_clk);bus_address=a;bus_in=b;bus_write=0;#200;bus_write=1;#200;
 end endtask
 task token261(input [31:0] n);begin for(integer i=0;i<4;i++)wr261(24'h00604c+i,n>>(8*i));end endtask
 task maps261;
 integer k,j,n,total,skip_bytes,before_receipts;reg [15:0] crc261;reg [63:0] desc;reg [31:0] reserved261;
 begin
  // Skip only the old map stream fixture; the actual ARM batch descriptors
  // independently drive core receipt updates and are checked against metadata.
  skip_bytes=c[11:0]*2;
  while(cmds[cmd_at][63:60]==2&&cmds[cmd_at][32])begin
   skip_bytes+=cmds[cmd_at][11:0]*2;cmd_at++;
  end
  stream_at+=skip_bytes;sink_at+=skip_bytes;
  name=$sformatf("map%0d.hex",f);$readmemh(name,map_mem);
  name=$sformatf("map%0d.lens",f);$readmemh(name,lens261);packet_count=lens261[0];map_at=0;accepted+=lens261[254];
  name=$sformatf("map%0d.expected",f);$readmemh(name,map_expected);
  before_receipts=receipt_ticks;reserved261=next_token;
  for(j=0;j<packet_count;j++)begin
   wait((dut.flow.queue.accepted-dut.flow.queue.retired)<WINDOW);
   n=lens261[j+1];for(k=0;k<n;k++)packet261[k]=map_mem[map_at+k];map_at+=n;
   // Ordinary/tile commands still use the fixture boundary: bind sequence and
   // token to this test's live namespace, preserving every map descriptor/value.
   packet261[2]=packet_seq261;packet261[3]=packet_seq261>>8;
   for(k=0;k<4;k++)packet261[16+k]=reserved261>>(8*k);
   reserved261+=packet261[0]==14?packet261[20]:1;
   target_waiting=1;
   tx[0]=8'he1;crc261=c16(16'hffff,8'he1);
   for(k=0;k<n;k++)begin tx[k+1]=packet261[k];crc261=c16(crc261,packet261[k]);end
   tx[n+1]=crc261[15:8];tx[n+2]=crc261[7:0];transfer(n+3);
   if(WINDOW==1)begin wait(dut.flow.queue.retired==dut.flow.queue.accepted);repeat(8)@(negedge host_clk);end
   packet_seq261++;map_batches++;
  end
  wait(dut.flow.queue.retired==dut.flow.queue.accepted&&dut.flow.state==dut.flow.IDLE&&dut.flow.owner==dut.flow.NONE);repeat(4)@(negedge clk);
  if(receipt_ticks-before_receipts!=lens261[255])$fatal(1,"missing per-range receipts %0d/%0d",receipt_ticks-before_receipts,lens261[255]);
  ranges+=lens261[255];map_ranges+=lens261[255];map_bytes+=lens261[254];
  $fwrite(events261,"maps_done,%0d,%0t,%0d\n",f,$time,packet_count);
 end endtask
 initial begin : bus261
 integer i,n,base261;reg [31:0] tok261;reg [7:0] val261;
 if(!RPC&&!NEG)begin
  wait(!reset);
  forever begin
   @(negedge host_clk);
   if(dut.flow.state==dut.flow.DMA&&staged)begin
    n=dut.flow.chunk_length;base261=dut.flow.first*2;tok261=dut.flow.chunk_token;
    #23280;
    for(i=0;i<n;i++)begin
     rd261(24'h400800+i,val261);
     if(val261!==map_expected[base261+i])$fatal(1,"actual map DMA mismatch frame%0d byte%0d",f,base261+i);
     map_actual[base261+i]=val261;
    end
    token261(tok261);wr261(24'h006050,8'ha5);
    wait(dut.flow.state!=dut.flow.DMA);
   end else if(v_sealed&&dut.flow.state==dut.flow.IDLE)begin
    repeat(4)@(negedge host_clk);token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);
    wait(!v_sealed);
   end
  end
 end
 end

 initial begin : negative261
 reg [7:0] frozen261[0:1023];reg [7:0] b261;integer n261;reg [31:0] tok261;
 if(NEG)begin
  wait(target_waiting);wait(dut.flow.state==dut.flow.DMA&&staged);
  n261=dut.flow.chunk_length;tok261=dut.flow.chunk_token;
  if(NEG==1)begin token261(tok261);wr261(24'h006058,8'h5a);end
  if(NEG==2||NEG==3||NEG==4||NEG==6)begin
   for(integer i=0;i<(NEG==3?n261-1:n261);i++)rd261(24'h400800+i,b261);
   token261(tok261+(NEG==2));wr261(24'h006050,8'ha5);
   if(NEG==4)begin wait(receipt_committed);@(negedge clk);test_abort=1;end
   if(NEG==6)begin wait(dut.core.encoder.state==dut.core.encoder.V_RWRITE);@(negedge clk);test_abort=1;end
  end
  if(NEG==5)begin @(negedge clk);test_drop=1;end
  wait(source_fault);repeat(4)@(negedge clk);
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"completion after cancellation");
  for(integer i=0;i<1024;i++)frozen261[i]=dut.core.memory[i];
  repeat(256)@(negedge clk);
  for(integer i=0;i<1024;i++)if(frozen261[i]!==dut.core.memory[i])$fatal(1,"RAM mutated after cancellation");
  $display("PASS JOINT261 NEG=%0d fault=%0d",NEG,source_fault);$finish;
 end
 end
'''


def tb():
 s=prior_tb().replace('joint255_tb','joint261_tb')
 s=s.replace('dut.','dut.core.')
 s=once(s,'wire release_frame=manual_release|exporter_release;','wire release_frame;')
 s=once(s,' nes_joint255 dut(',EXTRA[:EXTRA.index(' task rd261')]+'''\n nes_joint261 dut(
 .capture_begin(capture_begin),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(test_drop),.reader_drained(1'b1),
 .release_frame(release_frame),.lease_valid(lease_valid),.waiting_display(waiting_display),.lease_fault(lease_fault),
 .retired(flow_retired),.display_ack(rack),.identity_valid(idvalid),.identity_ready(idready),.bank(~serial[0]),
 .address(bus_address),.read_n(bus_read),.write_n(bus_write),.data_in(bus_in),.data_out(bus_out),.bus_valid(bus_valid),
 .staged(staged),.receipt_committed(receipt_committed),.flow_fault(flow_fault),
 .tile_valid(1'b0),.tile_ready(),.tile_data(8'd0),.tile_index(5'd0),.tile_length(6'd16),.tile_kind(2'd0),.tile_slot(10'd0),.tile_generation(generation),
 .end_valid(ev),.end_ready(er),.end_generation(generation),.ordinary_ready(),.next_token(next_token),''')
 s=once(s,' task output_frame;',EXTRA[EXTRA.index(' task rd261'):]+'\n task output_frame;')
 s=once(s,'.v_display_ack(v_display_ack),','')
 s=once(s,'   if(GUARD==4)begin','''   if(op==2&&c[32])begin maps261();continue;end
   if(op==5)begin wait(flow_retired);@(negedge clk);continue;end
   if(GUARD==4)begin''')
 s=once(s,'   output_frame();','''   source_end261=$realtime;
   repeat(3)@(negedge clk);
   if(owned||!lease_valid||!waiting_display)$fatal(1,"input to display lease");
   wait(ss);repeat(400)@(negedge host_clk);
   wait(idready);@(negedge clk);idvalid=1;@(negedge clk);idvalid=0;
   wait(er);@(negedge clk);ev=1;@(negedge clk);ev=0;packet_seq261=0;
   output_frame();
   output_end261=$realtime;
   if(lease_valid||waiting_display||owned)$fatal(1,"final ACK failed to retire lease");
   $fwrite(events261,"frame_done,%0d,%0t,%0t\\n",f,$time,output_end261-source_end261);''')
 s=once(s,'  repeat(4)@(negedge clk);reset=0;','  events261=$fopen("joint-events.csv","w");\n  repeat(4)@(negedge clk);reset=0;')
 s=once(s,'$display("PASS JOINT255 frames=%0d",frames);$finish;','$display("PASS JOINT261 frames=%0d batches=%0d ranges=%0d map_bytes=%0d",frames,map_batches,map_ranges,map_bytes);finished261=1;if(!RPC)$finish;')
 s=once(s,'if(source_fault&&GUARD==0)','if(source_fault&&GUARD==0&&!NEG)')
 return s


def packets(path):
 b=path.read_bytes();out=[];at=0
 while at<len(b):
  n=int.from_bytes(b[at:at+2],'little');at+=2;out.append(b[at:at+n]);at+=n
 assert at==len(b);return out


def prepare(d,last,single=False):
 d.mkdir(parents=True);pins={}
 def copy(f):pins[f.relative_to(BASE).as_posix()]=sha(f);shutil.copyfile(f,d/f.name)
 src=sources()
 for n,s in src.items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 board=BASE/'probes/nes-counter224/mapfit02'
 for n in ['nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181','nes_native_mailbox206','nes_domain_reset124']:
  copy(board/(n+'.sv'));src[n+'.sv']=''
 for n in ['nes_capture_lease201','nes_bulk_aperture188']:copy(ROOT/'src/nes/rtl'/(n+'.sv'));src[n+'.sv']=''
 old=BASE/'probes/nes-joint255/test03'
 for n in ['commands.hex','expected.hex','certs.hex','hashes.hex','stream.hex','sink.hex']:copy(old/n)
 batch_stats=[]
 commands=[int(x,16) for x in (d/'commands.hex').read_text().split()]
 receipt_image=bytearray.fromhex((d/'expected.hex').read_text());maps={};bank_images=[None,None]
 for f in range(905,last+1):
  for ext in ['hex','palette','expected']:copy(old/f'frame{f}.{ext}')
  pth=BASE/f'probes/nes-batch260/arm01/frame{f}.packets';pins[pth.relative_to(BASE).as_posix()]=sha(pth)
  pp=[p for p in packets(pth) if p[0]==14];rr=[]
  for p in pp:
   at=21
   for _ in range(p[20]):
    off=int.from_bytes(p[at:at+2],'little');n=p[at+2];at+=3;rr.append((off,p[at:at+n]));at+=n
   assert at==len(p)
  if single:
   expanded=[]
   for off,data in rr:
    h=bytearray(pp[0][:16]);h[0]=12;h[10:12]=(off//2).to_bytes(2,'little');h[12:14]=(len(data)+4).to_bytes(2,'little');h[14:16]=len(data).to_bytes(2,'little')
    expanded.append(bytes(h)+bytes(4)+data)
   pp=expanded
  lengths=[len(pp),*[len(p) for p in pp]];lengths+=[0]*(255-len(lengths));lengths+=[len(rr)];lengths[254]=sum(len(data) for _,data in rr)
  (d/f'map{f}.hex').write_text(b''.join(pp).hex(' '),encoding='utf-8')
  (d/f'map{f}.lens').write_text('\n'.join(f'{n:x}' for n in lengths)+'\n',encoding='utf-8')
  expected=BASE/f'probes/nes-wholepath247/jointdecode-test02/run/expected-{f-904}.bin';pins[expected.relative_to(BASE).as_posix()]=sha(expected)
  meta=expected.read_bytes()[:4096]
  coverage=bytearray(256);bank=(f-905)%2
  restored=bytearray(bank_images[bank]) if bank_images[bank] is not None else bytearray(4096)
  for off,data in rr:
   assert meta[off:off+len(data)]==data
   restored[off:off+len(data)]=data
   for word in range(off//2,(off+len(data))//2):
    assert not coverage[word//8]&(1<<(word%8));coverage[word//8]|=1<<(word%8)
  assert restored==meta,('missing changed map words',f)
  if bank_images[bank] is None:assert coverage==bytes([255])*256
  bank_images[bank]=restored;maps[f]=coverage
  receipt_image[(f-905)*754+498:(f-904)*754]=coverage
  (d/f'map{f}.expected').write_text(meta.hex(' '),encoding='utf-8')
  batch_stats.append(dict(frame=f,packets=len(pp),ranges=len(rr),wire_bytes=sum(len(p)+3 for p in pp)))
 # Prior250 used gap16. ARM260 uses its actual sparse spans, so the required
 # per-frame map receipt is rebuilt from those descriptors after independent
 # reconstruction against each bank's last displayed image.
 frame=904;check=0
 for i,cmd in enumerate(commands):
  if cmd>>60==1:frame+=1;check=0
  elif cmd>>60==3:
   if frame in maps and check>=166:commands[i]=(cmd&~255)|maps[frame][check-166]
   check+=1
 (d/'commands.hex').write_text('\n'.join(f'{c:016x}' for c in commands)+'\n',encoding='utf-8')
 (d/'expected.hex').write_text(receipt_image.hex(' '),encoding='utf-8')
 testbench=tb()
 (d/'joint261_tb.sv').write_text(testbench,encoding='utf-8',newline='\n')
 for n in ['nes_joint261.py','probe_nes_joint261.py']:copy(ROOT/'tools'/n)
 return src,pins,batch_stats


def run(exe,args,d,label,timeout=1200):
 with (d/(label+'.log')).open('wb') as log:r=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 s=(d/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6500:];return s


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--last',type=int,default=975);p.add_argument('--single',action='store_true');p.add_argument('--guards',action='store_true');a=p.parse_args()
 d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.last,a.single)
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint261_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','work.joint261_tb',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
 assert f'PASS JOINT261 frames={a.last-904}' in log
 flat={}
 for line in (d/'blocks.txt').read_text().splitlines():
  frame,tok,n,b=line.split();flat.setdefault(int(frame),bytearray()).extend(bytes.fromhex(b))
 for frame,b in flat.items():
  old=BASE/'probes/nes-joint249/blocktest03';size=int((old/f'frame{frame}.meta').read_text().split()[0]);assert b==bytes.fromhex((old/f'frame{frame}.expected.hex').read_text())[:size]
 guards=[]
 if a.guards:
  for case in range(1,7):
   gd=d/f'guard{case:02}';gd.mkdir()
   for fixture in d.iterdir():
    if fixture.suffix in ['.hex','.palette','.expected','.lens']:shutil.copyfile(fixture,gd/fixture.name)
   run(a.questa_bin/'vmap.exe',['-c'],gd,'vmap0');run(a.questa_bin/'vmap.exe',['work',str(d/'work')],gd,'vmap')
   log=run(a.questa_bin/'vsim.exe',['-c','work.joint261_tb',f'-gNEG={case}','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],gd,'vsim')
   assert f'PASS JOINT261 NEG={case}' in log;guards.append(case)
 r=dict(passed=True,guards=guards,frames=len(flat),single=a.single,source_bytes=sum(map(len,flat.values())),map_frames=stats,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,scope=__doc__,full_ARM=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(log[-1700:])

if __name__=='__main__':main()
