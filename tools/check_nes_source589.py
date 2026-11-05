# SPDX-License-Identifier: MIT
"""Source589 paired-clock RTL/SPI test and equal-boundary Lite MAP preparation.

The query oracle uses pinned captures; no collector/ROM/ARM/display timing claim.
"""
import argparse,hashlib,json,re,shutil,subprocess,zipfile
from pathlib import Path
from check_nes_game478 import encode
from check_nes_combined586 import packets
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

TOP=r'''
module nes_region589 #(parameter CANDIDATE=1)(
 input wire clk,host_clk,reset,enable,frame_owned,geometry_valid,
 input wire [15:0] generation,input wire [31:0] epoch,
 input wire [5:0] groups,palettes,input wire [7:0] objects,exceptions,rows,input wire [2:0] patches,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,output wire [15:0] query_generation,
 input wire response,hit,input wire [63:0] data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output wire release_frame,output wire [3:0] source_fault,output wire host_fault,packet_fault
);
 wire av,aa,ar,ack;wire [15:0] ag;wire [16:0] ad;
 nes_native_mailbox165 #(.WIDTH(17)) prepared(.src_clk(host_clk),.dst_clk(clk),.reset(reset),
  .src_valid(av),.src_ready(ar),.src_data({aa,ag}),.dst_valid(ack),.dst_ready(1'b1),.dst_data(ad));
 generate if(CANDIDATE)begin:newpath
  wire bv,br,seal,dv,dr,sent,tv,tr,hv,hr;wire [8:0] len;wire [7:0] db;wire [68:0] td,hd;
  nes_source589 source(.clk(clk),.reset(reset),.enable(enable),.frame_owned(frame_owned),.geometry_valid(geometry_valid),
   .frame_generation(generation),.content_epoch(epoch),.group_count(groups),.palette_count(palettes),
   .object_count(objects),.exception_count(exceptions),.row_count(rows),.patch_count(patches),
   .query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
   .block_valid(bv),.block_ready(br),.block_length(len),.block_seal(seal),.byte_valid(dv),.byte_ready(dr),.byte_data(db),
   .packet_sent(sent),.ack_valid(ack),.ack_accept(ad[16]),.ack_generation(ad[15:0]),.release_frame(release_frame),.fault(source_fault),.busy());
  nes_packet589 packer(.clk(clk),.reset(reset),.block_valid(bv),.block_ready(br),.block_length(len),.block_seal(seal),
   .byte_valid(dv),.byte_ready(dr),.byte_data(db),.tx_valid(tv),.tx_ready(tr),.tx_data(td),.packet_sent(sent),.fault(packet_fault));
  nes_native_mailbox165 #(.WIDTH(69)) records(.src_clk(clk),.dst_clk(host_clk),.reset(reset),
   .src_valid(tv),.src_ready(tr),.src_data(td),.dst_valid(hv),.dst_ready(hr),.dst_data(hd));
  nes_native_spi589 spi(.clk(host_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
   .selected(selected),.miso(miso),.record_valid(hv),.record_ready(hr),.record_data(hd),.ack_valid(av),.ack_ready(ar),.ack_accept(aa),.ack_generation(ag),.fault(host_fault));
 end else begin:oldpath
  wire tv,tr,hv,hr;wire [95:0] td,hd;
  assign packet_fault=0;
  nes_native_export203 #(.MAX_CYCLES(33554432)) source(.clk(clk),.reset(reset),.enable(enable),.frame_owned(frame_owned),.geometry_valid(geometry_valid),
   .frame_generation(generation),.group_count(groups),.palette_count(palettes),.object_count(objects),.exception_count(exceptions),.row_count(rows),.patch_count(patches),
   .query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
   .tx_valid(tv),.tx_ready(tr),.tx_data(td),.ack_valid(ack),.ack_accept(ad[16]),.ack_generation(ad[15:0]),.ack_ready(),.release_frame(release_frame),.error(source_fault),.busy(),.observe_state177());
  nes_native_mailbox165 #(.WIDTH(96)) records(.src_clk(clk),.dst_clk(host_clk),.reset(reset),
   .src_valid(tv),.src_ready(tr),.src_data(td),.dst_valid(hv),.dst_ready(hr),.dst_data(hd));
  nes_native_spi165 spi(.clk(host_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
   .selected(selected),.miso(miso),.record_valid(hv),.record_ready(hr),.record_data(hd),.ack_valid(av),.ack_ready(ar),.ack_accept(aa),.ack_generation(ag),.fault(host_fault));
 end endgenerate
endmodule
'''

TB=r'''
`timescale 1ns/1ps
module source589_tb;
 parameter real PHASE=3.5;
 reg clk=0,host_clk=0,run_nes=1,run_host=1,reset=1,enable=0,owned=0,geometry=1;
 always #22.727 if(run_nes)clk=~clk;
 initial begin #(PHASE);forever #5.952 if(run_host)host_clk=~host_clk;end
 reg [15:0] generation=905;reg [31:0] epoch=1;
 reg [5:0] groups,palettes;reg [7:0] objects,exceptions,rows=224;reg [2:0] patches;
 wire query,release_frame,selected,miso,hfault,pfault;wire [3:0] sfault;
 wire [2:0] qkind;wire [12:0] qindex;wire [15:0] qgen;
 reg response=0,hit=0;reg [63:0] data=0;reg ss=1,sck=0,mosi=0;
 reg [63:0] values[0:16383];integer delay=0;reg [63:0] pending;
 integer cycles=0,queries=0,blocks=0,wirebytes=0,fd,cf,stats,f,last=957,k,n,i,prepared=0;
 integer waits=0,ramwrites=0,crcbytes=0,stalls=0,guards=0;reg checking=1;
 reg [7:0] tx[0:258],rx[0:258];reg [15:0] token,crc;
 string filename;integer c0,c1,c2,c3,c4,c5,patch;
 nes_region589 dut(.clk(clk),.host_clk(host_clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(geometry),
  .generation(generation),.epoch(epoch),.groups(groups),.palettes(palettes),.objects(objects),.exceptions(exceptions),.rows(rows),.patches(patches),
  .query(query),.query_kind(qkind),.query_index(qindex),.query_generation(qgen),.response(response),.hit(hit),.data(data),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso),.release_frame(release_frame),.source_fault(sfault),.host_fault(hfault),.packet_fault(pfault));
 always @(posedge clk)begin
  response<=0;
  if(reset)begin delay<=0;response<=0;hit<=0;end
  else begin
   if(query)begin
    if(delay||qgen!=generation)$fatal(1,"query ownership");
    pending<=values[qkind*2048+qindex];delay<=3+(qindex%3);queries++;
   end
   if(delay)begin delay<=delay-1;if(delay==1)begin data<=pending;response<=1;hit<=1;end end
   if(enable)begin
    cycles++;
    if(dut.newpath.source.state==dut.newpath.source.QWAIT)waits++;
    if(dut.newpath.source.state==dut.newpath.source.WRITE)begin
     ramwrites++;if(dut.newpath.source.addr>=2560)$fatal(1,"RAM bounds");
    end
    if(dut.newpath.source.state==dut.newpath.source.STORE)crcbytes++;
    if(dut.newpath.tv&&!dut.newpath.tr)stalls++;
    if(checking&&(sfault||hfault||pfault))$fatal(1,"fault frame%0d src%0d host%0d packet%0d state%0d",generation,sfault,hfault,pfault,dut.newpath.source.state);
   end
   if(release_frame)owned<=0;
  end
 end
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer i;begin c=c0^b;for(i=0;i<8;i++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer i;begin c=c0^{b,8'd0};for(i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 task request(input [7:0] cmd,input [15:0] tok,input [7:0] arg);
  integer i;reg [7:0] c;begin tx[0]=cmd;tx[1]=0;tx[2]=tok[15:8];tx[3]=tok[7:0];tx[4]=arg;tx[5]=~arg;c=0;
   for(i=0;i<6;i++)c=c8(c,tx[i]);tx[6]=c;tx[7]=8'ha5;end
 endtask
 task transfer(input integer size);
  integer a,b;begin #2000;ss=0;#2000;
   for(a=0;a<size;a++)begin rx[a]=0;for(b=7;b>=0;b--)begin
    mosi=tx[a][b];#190.476190476;sck=1;rx[a][b]=selected?miso:0;#190.476190476;sck=0;
   end end #2000;ss=1;#2000;wirebytes+=size;
  end
 endtask
 task status;
  integer a;reg [7:0] c;begin request(8'hd0,0,0);transfer(8);c=0;
   for(a=1;a<7;a++)c=c8(c,rx[a]);if(rx[1]!=8'hd6||rx[7]!=c||rx[2][7])$fatal(1,"status");end
 endtask
 task fresh;
  begin checking=0;reset=1;enable=0;owned=0;ss=1;sck=0;run_nes=1;run_host=1;
   #1000;epoch=epoch+1;reset=0;repeat(20)@(negedge clk);owned=1;enable=1;
  end
 endtask
 task stop_checks;
  integer g,t,b;reg [7:0] frozen;
  begin
   checking=0;
   for(g=0;g<5;g++)begin
    fresh;
    case(g)
     0:wait(dut.newpath.source.state==dut.newpath.source.WRITE);
     1:wait(dut.newpath.source.state==dut.newpath.source.RAMWAIT);
     default:wait(dut.newpath.spi.sealed);
    endcase
    @(negedge clk);frozen=dut.newpath.source.mem[0];
    if(g==3)run_nes=0;if(g==4)run_host=0;
    reset=1;#1000;
    if(query||dut.newpath.tv||selected)$fatal(1,"STOP while paused");
    run_nes=1;run_host=1;repeat(8)@(negedge clk);
    if(dut.newpath.source.mem[0]!==frozen||dut.newpath.source.valid_base||dut.newpath.spi.sealed||dut.ack)$fatal(1,"STOP residue");
    enable=0;owned=0;reset=0;repeat(20)@(negedge clk);guards++;
   end
   for(g=0;g<2;g++)begin
    fresh;wait(dut.newpath.spi.sealed);status;t={rx[3],rx[4]};n={rx[5],rx[6]};
    if(g==1)begin for(b=0;b<259;b++)tx[b]=0;tx[0]=8'hd1;transfer(n+3);end
    request(8'hd2,t+g,0);transfer(8);
    if(!hfault||!dut.newpath.spi.sealed||dut.newpath.spi.token!=t)$fatal(1,"invalid POP ownership");guards++;
   end
   fresh;prepared=0;
   while(!prepared)begin
    status;
    if(rx[2][0])begin
     n={rx[5],rx[6]};t={rx[3],rx[4]};for(b=0;b<259;b++)tx[b]=0;tx[0]=8'hd1;transfer(n+3);
     prepared=n>=8&&rx[n-7]==1&&rx[n-6]==8'hf0;
     request(8'hd2,t,0);transfer(8);
    end
   end
   request(8'hd3,generation+16'd1,1);transfer(8);repeat(20)@(negedge clk);
   if(sfault!=5||dut.newpath.source.valid_base||dut.newpath.spi.sealed)$fatal(1,"stale PREPARE accepted");guards++;
   reset=1;enable=0;owned=0;
  end
 endtask
 initial begin
  if($value$plusargs("LAST=%d",last))begin end
  fd=$fopen("blocks.txt","w");stats=$fopen("stats.txt","w");#1000;reset=0;
  for(f=905;f<=last;f++)begin
   @(negedge clk);generation=f;
   filename=$sformatf("frame%0d.values",f);$readmemh(filename,values);
   filename=$sformatf("frame%0d.counts",f);cf=$fopen(filename,"r");
   if($fscanf(cf,"%d %d %d %d %d %d %d",c0,c1,c2,c3,c4,c5,patch)!=7)$fatal(1,"counts");$fclose(cf);
   groups=c0/33;palettes=c5/32;objects=c2;exceptions=c3;patches=patch;
   cycles=0;queries=0;waits=0;ramwrites=0;crcbytes=0;stalls=0;prepared=0;owned=1;enable=1;
   begin: consume
    bit complete;complete=0;
    while(!complete)begin
     status;
     if(rx[2][0])begin
      n={rx[5],rx[6]};token={rx[3],rx[4]};if(n<1||n>254)$fatal(1,"length");
      // Hold sealed data across a delayed read; the producer must backpressure.
      if(blocks%7==0)#100000;
      for(i=0;i<259;i++)tx[i]=0;tx[0]=8'hd1;transfer(n+3);
      crc=16'hffff;for(k=1;k<=n;k++)crc=c16(crc,rx[k]);if(crc!={rx[n+1],rx[n+2]})$fatal(1,"CRC");
      $fwrite(fd,"%0d %0d %0d ",f,token,n);for(k=1;k<=n;k++)$fwrite(fd,"%02x",rx[k]);$fwrite(fd,"\n");
      complete=n==8&&rx[1]==3&&rx[2]==8'hf0;
      prepared=n>=8&&rx[n-7]==1&&rx[n-6]==8'hf0;
      request(8'hd2,token,0);transfer(8);status;if({rx[3],rx[4]}!=token+16'd1)$fatal(1,"retire");
      if(prepared)begin request(8'hd3,generation,1);transfer(8);end
      blocks++;
     end
    end
   end
   wait(!owned);@(negedge clk);enable=0;
   $fwrite(stats,"%0d %0d %0d %0d %0d %0d %0d\n",f,cycles,queries,waits,ramwrites,crcbytes,stalls);
   $display("FRAME589 %0d cycles%0d queries%0d",f,cycles,queries);
   repeat(20)@(negedge clk);
  end
  $fclose(fd);$fclose(stats);stop_checks;
  if(guards!=8)$fatal(1,"guard count");
  $display("PASS SOURCE589 frames%0d guards%0d",last-904,guards);$finish;
 end
 initial begin #2000000000;$fatal(1,"watchdog frame%0d state%0d at%0d n%0d kind%0d",f,dut.newpath.source.state,dut.newpath.source.at,dut.newpath.source.n,dut.newpath.source.kind);end
endmodule
'''

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    pins=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())['FPGA_inputs']
    for name in ('nes_native_spi165.sv','nes_native_mailbox165.sv','nes_native_export203.sv'):
        assert sha(a.board/name)==pins[name]['sha256'];shutil.copyfile(a.board/name,a.out/name)
    shutil.copyfile(ROOT/'rtl/nes_source589.sv',a.out/'nes_source589.sv')
    s=(a.board/'nes_native_spi165.sv').read_text().replace('nes_native_spi165','nes_native_spi589').replace('[95:0]','[68:0]')
    lo=s.index(' function automatic [3:0] width');hi=s.index(' function automatic [15:0] crc16',lo);s=s[:lo]+s[hi:]
    lo=s.index(' wire [15:0] tag=');hi=s.index(' (* async_reg=',lo)
    s=s[:lo]+''' wire [7:0] pack_byte=held[63:0]>>(position*8);
 assign record_ready=!reset&&!sealed&&!encoding&&used<=248;
'''+s[hi:]
    lo=s.index('   if(record_valid&&record_ready)');hi=s.index('   if(encoding)',lo)
    s=s[:lo]+'''   if(record_valid&&record_ready)begin
    if(record_data[67:64]==0||record_data[67:64]>8||used+record_data[67:64]>256)fault<=1;
    else begin held<=record_data;position<=0;total<=record_data[67:64];encoding<=1;end
   end
'''+s[hi:]
    s=s.replace("if(used+1>244 || (held[95:93]==7&&held[76:64]!=0&&held[76:64]<13'h800))sealed<=1;","if(held[68])sealed<=1;")
    assert '[95:' not in s
    (a.out/'nes_native_spi589.sv').write_text(s,encoding='utf8',newline='\n')
    (a.out/'nes_region589.sv').write_text(TOP,encoding='utf8',newline='\n')
    (a.out/'source589_tb.sv').write_text(TB,encoding='utf8',newline='\n')
    prior=None;expected={};pinned=json.loads((ROOT/'analysis/body581-verification.json').read_text())['inputs']
    with zipfile.ZipFile(a.archive) as z:
        for g in range(905,a.last+1):
            geom=z.read(f'data/frame{g}.geometry');raw=z.read(f'data/frame{g}.raw')
            assert hashlib.sha256(geom).hexdigest()==pinned[f'frame{g}.geometry']
            assert hashlib.sha256(raw).hexdigest()==pinned[f'frame{g}.raw']
            arrays=encode(geom,raw,g)[2]+[list(raw)]
            lines=[]
            for k,values in enumerate(arrays):
                if values:lines += [f'@{(7 if k==6 else k)*2048:x}']+[f'{v:016x}' for v in values]
            (a.out/f'frame{g}.values').write_text('\n'.join(lines)+'\n')
            (a.out/f'frame{g}.counts').write_text(' '.join(map(str,[*map(len,arrays[:6]),len(raw)//256])))
            expected[str(g)]=[b.hex() for b in packets(geom,raw,g,g-904,prior)[0]];prior=arrays
    (a.out/'expected.private.json').write_text(json.dumps(expected))
    (a.out/'inputs.json').write_text(json.dumps({p.name:sha(p) for p in a.out.iterdir() if p.suffix=='.sv'},indent=2))

def run(a):
    q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    def command(exe,args,name):
        with (a.out/(name+'.log')).open('wb') as log:
            p=subprocess.run([str(q/exe),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        assert p.returncode==0,(name,p.returncode)
    command('vlib.exe',['work'],'vlib')
    command('vlog.exe',['-sv',*[p.name for p in a.out.glob('*.sv')]],'vlog')
    command('vsim.exe',['-c','work.source589_tb',f'+LAST={a.last}','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim')
    text=(a.out/'vsim.log').read_text(errors='replace');assert f'PASS SOURCE589 frames{a.last-904}' in text,text[-1800:]
    expected=json.loads((a.out/'expected.private.json').read_text());actual={k:[] for k in expected};token=0
    for line in (a.out/'blocks.txt').read_text().splitlines():
        g,t,n,h=line.split();assert int(t)==token and int(n)*2==len(h);token+=1;actual[g].append(h)
    assert actual==expected,[(g,len(actual[g]),len(expected[g]),next((i for i,(x,y) in enumerate(zip(actual[g],expected[g])) if x!=y),None)) for g in expected if actual[g]!=expected[g]][:4]
    assert 'guards8' in text
    result=dict(passed=True,frames=len(actual),packets=token,guards=8,stats=(a.out/'stats.txt').read_text(),
                source_pins=json.loads((a.out/'inputs.json').read_text()),scope=__doc__,ARM=False,whole_board=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('stats','source_pins')},indent=2))

def mapping(a):
    a.out.mkdir(parents=True,exist_ok=False)
    device=re.search(r'-name DEVICE (\S+)',(a.board/'board.qsf').read_text())[1]
    results={}
    for candidate in (0,1):
        d=a.out/('candidate' if candidate else 'reference');d.mkdir()
        if candidate and a.reuse_candidate:
            old=a.reuse_candidate/'candidate'
            for p in old.rglob('*'):
                rel=p.relative_to(old)
                if not p.is_file() or any(x in ('db','incremental_db') for x in rel.parts):continue
                if p.suffix in ('.sv','.qsf','.qpf','.rpt','.summary') or p.name=='map.log':
                    dest=d/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
            results['candidate']=json.loads((a.reuse_candidate/'result.json').read_text())['results']['candidate']
            results['candidate']['reused_reason']='Candidate elaboration unchanged; corrected only reference MAX_CYCLES to pinned board33554432.'
            continue
        for p in a.inputs.glob('*.sv'):
            if p.name=='source589_tb.sv':continue
            shutil.copyfile(p,d/p.name)
        p=d/'nes_region589.sv';p.write_text(TOP.replace('parameter CANDIDATE=1',f'parameter CANDIDATE={candidate}'),encoding='utf8',newline='\n')
        qsf=['set_global_assignment -name FAMILY "Cyclone IV E"',f'set_global_assignment -name DEVICE {device}',
             'set_global_assignment -name TOP_LEVEL_ENTITY nes_region589','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files']
        qsf += ['set_global_assignment -name SYSTEMVERILOG_FILE '+p.name for p in d.glob('*.sv')]
        (d/'region.qsf').write_text('\n'.join(qsf)+'\n');(d/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
        pins={p.name:sha(p) for p in d.iterdir() if p.is_file()}
        with (d/'map.log').open('wb') as log:
            rc=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','region'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW).returncode
        assert rc==0,(d,rc)
        summary=(d/'output_files/region.map.summary').read_text()
        results[d.name]=dict(summary=summary,inputs=pins,log_sha256=sha(d/'map.log'))
        print(d.name,summary)
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,scope='Equal live-port source/mailbox/SPI region MAP; not whole FIT/STA',results=results),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run','map']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--inputs',type=Path)
    p.add_argument('--reuse-candidate',type=Path)
    p.add_argument('--board',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--last',type=int,default=957)
    a=p.parse_args();{'prepare':prepare,'run':run,'map':mapping}[a.mode](a)
