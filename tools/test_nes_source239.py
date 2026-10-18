# SPDX-License-Identifier: MIT
"""Actual frame201 queries -> encoder239 RAM -> real SPI pins -> C234/231.

Recorded PPU stimuli, host PREPARED ACK and ROM reads are fixtures. This is
not whole-game execution, actual SNES display ACK, placement or physical FPS.
"""
from pathlib import Path
import argparse,json,os,re,shutil,struct,subprocess
from nes_delta231 import ROOT,BASE,sha
from test_nes_source235 import read_records


def testbench():
    s=(ROOT/'tests/nes-functional/geometry230_tb.sv').read_text()
    s=s.replace('module geometry230_tb;','module source239_tb;\n parameter real PHASE=3.5;')
    s=s.replace('always #5 clk=~clk;', 'always #22.727 clk=~clk;\n reg host_clk=0;initial begin #(PHASE);forever #5.952 host_clk=~host_clk;end')
    a=s.index(' reg enable=0;');b=s.index(' reg [106:0] stimulus',a)
    s=s[:a]+r'''
 reg enable=0;wire start_ready,source_done,selected,miso;wire [3:0] source_fault;
 reg ss=1,sck=0,mosi=0;reg [31:0] serial=1;
 reg [7:0] expected[0:5740];integer seen=0,queries=0,cycles=0,prepare=0,blocked=0,overlap=0;
 integer qwait=0,transfer_cycles=0,acks=0,blocks=0,wirebytes=0,bf,stats,record_fd,rec_bytes=0;
 assign exporter_release=0;
 nes_source239 dut(.clk(clk),.host_clk(host_clk),.reset(reset),.abort_source(1'b0),.start(enable),.start_ready(start_ready),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),.content_epoch(32'd1),.frame_serial(serial),
  .patch_count(patch_count),.row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),
  .query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso),.done(source_done),.fault(source_fault));
 always @(posedge clk)if(!reset)begin
  if(dut.encoder.a_we&&dut.encoder.b_we&&dut.encoder.a_addr==dut.encoder.b_addr)$fatal(1,"scratch write collision");
  if((dut.encoder.a_we&&dut.encoder.a_addr>=792)||(dut.encoder.b_we&&dut.encoder.b_addr>=792)||(dut.encoder.base_we&&dut.encoder.base_addr>=5741))$fatal(1,"RAM bounds");
  if(source_fault)$fatal(1,"source239 frame=%0d code=%0d state=%0d cursor=%0d",f,source_fault,dut.encoder.state,dut.encoder.cursor);
  if(query)queries++;
  if(dut.valid&&dut.ready)begin
   if(dut.offset!=seen||dut.value!==expected[seen])$fatal(1,"canonical %0d/%0d",f,seen);seen++;
  end
  if(dut.encoder.state!=dut.encoder.IDLE)begin
   cycles++;
   if(dut.record_valid&&!dut.record_ready)blocked++;
   else if(dut.encoder.state==dut.encoder.WAITACK)qwait++;
   else if(dut.record_valid||dut.encoder.state==dut.encoder.SREAD||dut.byte_valid)transfer_cycles++;
   else prepare++;
  end
  if(dut.record_valid&&dut.record_ready)begin $fwrite(record_fd,"%0d ",dut.record_length);rec_bytes=0;end
  if(dut.byte_valid&&dut.byte_ready)begin
   $fwrite(record_fd,"%02x",dut.byte_data);rec_bytes++;
   if(rec_bytes==dut.record_length)$fwrite(record_fd,"\n");
   if(dut.transport.block_valid[~dut.transport.bank])overlap++;
  end
 end
 reg [7:0] tx[0:258],rx[0:258];integer length;reg [15:0] token,crc;
''' + s[b:]
    a=s.index(' always @(posedge clk)begin\n  ack_valid');b=s.index(' initial begin\n  if(!$value',a)
    bus=(ROOT/'tests/nes-functional/source_spi235_tb.sv').read_text()
    functions=bus[bus.index(' function automatic [7:0] c8'):bus.index(' always @(posedge src_clk)')]
    tasks=bus[bus.index(' task request('):bus.index(' task send(')]
    tasks+=bus[bus.index(' task read_block;'):bus.index(' initial begin\n  if(!GUARDS_ONLY)')]
    s=s[:a]+functions+tasks+r'''
 initial begin : consumer
  integer hf,k;reg ended;
  wait(!reset);wait(first!=0);bf=$fopen("blocks.txt","w");hf=first;
  while(hf<=last)begin
   wait(enable);ended=0;
   while(!ended)begin
    status;
    if(rx[2][0])begin
     read_block;
     $fwrite(bf,"%0d %0d %0d ",hf,token,length);
     for(k=1;k<=length;k++)$fwrite(bf,"%02x",rx[k]);$fwrite(bf,"\n");
     ended=length>=6&&rx[length-5]==255&&rx[length-4]==255&&rx[length-3]==0&&rx[length-2]==4;
     request(8'hd2,token,0);transfer(8);blocks++;
    end
   end
   request(8'hd3,generation,1);transfer(8);acks++;hf++;
  end
  $fclose(bf);
 end
''' + s[b:]
    a=s.index('   name=$sformatf("frame%0d.wire"');b=s.index('\n  end\n  $display',a)
    s=s[:a]+r'''
   name=$sformatf("frame%0d.expected",f);$readmemh(name,expected);
   name=$sformatf("frame%0d.records",f);record_fd=$fopen(name,"w");
   seen=0;queries=0;cycles=0;prepare=0;blocked=0;qwait=0;transfer_cycles=0;overlap=0;
   wait(start_ready);@(negedge clk);enable=1;@(negedge clk);enable=0;
   wait(source_done);@(negedge clk);$fclose(record_fd);
   if(seen!=5741||queries!=group_count*33+224+object_count+exception_count+224+palette_count*32+patch_count*256)$fatal(1,"count/queries");
   $fwrite(stats,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",f,cycles,prepare,blocked,qwait,transfer_cycles,queries,overlap,wirebytes);
   $display("SOURCE239 frame=%0d cycles=%0d prepare=%0d blocked=%0d ackwait=%0d transfer=%0d queries=%0d overlap=%0d",f,cycles,prepare,blocked,qwait,transfer_cycles,queries,overlap);
   manual_release=1;@(negedge clk);manual_release=0;serial++;frames++;
''' + s[b:]
    s=s.replace('  repeat(4)@(negedge clk);reset=0;', '  stats=$fopen("cycles.csv","w");$fwrite(stats,"frame,total,prepare,blocked,ackwait,transfer,queries,overlap,wirebytes_cumulative\\n");\n  repeat(4)@(negedge clk);reset=0;')
    s=s.replace('$display("PASS GEOMETRY230 frames=%0d",frames);$finish;', '$fclose(stats);$display("PASS SOURCE239 frames=%0d",frames);$finish;')
    return s.replace('#1000000000;', '#(64\'d10000000000);')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
    p.add_argument('--last',type=int,default=975);a=p.parse_args();d=a.out.resolve();assert str(d).isascii() and not d.exists()
    assert 905<=a.last<=975 and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    prior=BASE/'probes/nes-source234/test03';board=BASE/'probes/nes-counter224/mapfit02';pins={}
    def copy(f,to=d):
        shutil.copyfile(f,to/f.name);pins[str(f.relative_to(BASE)).replace('\\','/')]=sha(f)
    def run(exe,args,name,cwd=d,timeout=900):
        with (cwd/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(exe),*map(str,args)],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(cwd/(name+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-6000:]
        return t
    qbin=a.questa_bin
    names=['nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181','nes_native_mailbox206']
    for n in names:copy(board/(n+'.sv'))
    for n in ('nes_source_query235','nes_source_spi235','nes_source_encoder239','nes_source239'):
        copy(ROOT/'src/nes/rtl'/(n+'.sv'));names.append(n)
    (d/'source239_tb.sv').write_text(testbench(),encoding='utf-8',newline='\n')
    stimulus=BASE/'probes/nes-geometry230/stim05';e=json.loads((stimulus/'result.json').read_text())
    for row in e['frames']:
        f=row['frame']
        if f>a.last:continue
        assert sha(stimulus/f'frame{f}.hex')==row['stimulus_sha256']
        for ext in ('hex','palette'):copy(stimulus/f'frame{f}.{ext}')
        (d/f'frame{f}.expected').write_text((prior/f'frame{f}.geometry').read_bytes().hex(' '))
        pins[str((prior/f'frame{f}.stream').relative_to(BASE)).replace('\\','/')]=sha(prior/f'frame{f}.stream')
    run(qbin/'vlib.exe',['work'],'vlib')
    run(qbin/'vlog.exe',['-sv',*[n+'.sv' for n in names],'source239_tb.sv'],'vlog')
    t=run(qbin/'vsim.exe',['-c','work.source239_tb',f'+LAST={a.last}','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim')
    assert f'PASS SOURCE239 frames={a.last-904}' in t
    frames={f:bytearray() for f in range(905,a.last+1)};blocks=0
    for line in (d/'blocks.txt').read_text().splitlines():
        f,tok,n,b=line.split();b=bytes.fromhex(b);assert int(tok)==blocks and len(b)==int(n)<=248
        frames[int(f)]+=b;blocks+=1
    host=d/'host';host.mkdir();records=0
    for f,flat in frames.items():
        rr=read_records(prior/f'frame{f}.stream');expected=b''.join(rr)
        assert flat==expected,(f,'SPI bytes',len(flat),len(expected),next((i for i,(x,y) in enumerate(zip(flat,expected)) if x!=y),None))
        actual=[]
        for line in (d/f'frame{f}.records').read_text().splitlines():
            n,b=line.split();b=bytes.fromhex(b);assert len(b)==int(n);actual.append(b)
        assert actual==rr,(f,'record boundaries');records+=len(rr)
        at=0;packed=bytearray()
        for r in rr:packed+=struct.pack('<H',len(r))+flat[at:at+len(r)];at+=len(r)
        (host/f'frame{f}.stream').write_bytes(packed)
    ht='not run: bounded debug prefix';matches=0
    if a.last==975:
        for n in ('palette.bin','wrap.stream','coldwrap.stream'):copy(prior/n,host)
        exe=BASE/'probes/nes-source235/test02/host/host.exe';copy(exe,host)
        ht=run(host/'host.exe',[BASE/'probes/nes-geometry230/rtl02','C:/Users/mohallo/Downloads/test/Super Mario Bros 3 (J).nes',905,975,host],'run',host)
        for f in frames:
            for ext in ('geometry','raw','metadata','packets','plans'):
                assert (host/f'frame{f}.{ext}').read_bytes()==(prior/f'frame{f}.{ext}').read_bytes();matches+=1
    r=dict(passed=True,scope=__doc__,frames=len(frames),blocks=blocks,records=records,payload=sum(map(len,frames.values())),
           exact_c_files=matches,c_output=ht,source_pins=pins,runner_sha256=sha(Path(__file__)),
           query_state_fused=False,full_arm=False,whole_board=False,physical=False,new_fit=False)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
