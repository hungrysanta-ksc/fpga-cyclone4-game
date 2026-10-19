# SPDX-License-Identifier: MIT
"""Prefetched source plus descriptor/accepted-byte receipt comparison.

Same-clock sink is modeled memory, not physical SNES execution. CRC tail and
scroll remain C byte fixtures; SPI packet parsing/queue retirement is unbound.
"""
from probe_nes_joint254 import *
import probe_nes_joint254 as old
from nes_joint255 import sources

def fixtures(d,pin,update_padding=False):
    old.fixtures(d,pin,update_padding)
    prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run'
    commands=[int(v,16) for v in (d/'commands.hex').read_text().split()]
    payload=bytearray();dest=[];g=0
    for c in commands:
        op=c>>60
        if op==1:
            g+=1;meta=pin(prior/f'expected-{g}.bin').read_bytes()
            bank=pin(prior/f'bank-{g}.bin').read_bytes()
            assert len(meta)==8570 and len(bank)==24576
        if op!=2:continue
        mode=(c>>32)&1;first=(c>>12)&4095;count=c&4095
        for unit in range(first,first+count):
            if mode:data=meta[unit*2:unit*2+2]
            elif unit<1024:data=bank[unit*16:unit*16+16]
            elif unit<1152:
                at=16384+(unit-1024)*32;data=bank[at:at+32]
            elif unit<1184:
                at=4096+(unit-1152)*16;data=meta[at:at+16]
            else:
                assert unit<1312
                at=5152+1121+(unit-1184)*16;data=meta[at:at+16]
            assert len(data)==(2 if mode else 32 if 1024<=unit<1152 else 16)
            payload+=data
            dest.extend((mode<<17)|(unit<<5)|lane for lane in range(len(data)))
    assert len(payload)==len(dest)
    (d/'stream.hex').write_text(payload.hex(' '))
    (d/'sink.hex').write_text('\n'.join(f'{v:05x}' for v in dest)+'\n')
    (d/'stream-meta.json').write_text(json.dumps(dict(bytes=len(payload),frames=g))+'\n')


STREAM_TB=r'''
 reg stream_valid=0,sink_ready=0;reg [7:0] stream_data=0;wire stream_ready,sink_valid;
 wire [7:0] sink_data;wire [1:0] sink_kind;wire [11:0] sink_unit;wire [4:0] sink_lane;
 reg [7:0] stream_bytes[0:999999];reg [17:0] sink_addresses[0:999999];
 reg [7:0] sink_memory[0:2*131072-1];
 integer stream_stage_cycles=0;
 integer stream_at=0,sink_at=0,accepted=0,stalled=0,ranges=0,stream_clock=0,stream_fd;
 reg [7:0] range_receipt[0:817];reg stream_testing=0;
 always @(posedge clk)if(!reset)begin
  if(STREAM_STATE)stream_stage_cycles++;
  if(sink_valid&&!sink_ready)stalled++;
  if(sink_valid&&sink_ready)begin
   if(test_abort||test_drop||test_gen||source_fault)$fatal(1,"sink accepted after cancellation");
   if(sink_data!==stream_bytes[sink_at]||{sink_kind,sink_unit,sink_lane}!=={1'b0,sink_addresses[sink_at]})
    $fatal(1,"sink mismatch frame%0d byte%0d kind%0d unit%0d lane%0d",f,sink_at,sink_kind,sink_unit,sink_lane);
   sink_memory[(f-905)%2*131072+sink_kind*65536+sink_unit*32+sink_lane]=sink_data;
   accepted++;sink_at++;
  end
 end
 task send_range(input reg [63:0] descriptor);
 integer n,k,j,before_count,range_start;reg took;
 begin
  n=descriptor[11:0]*(descriptor[32]?2:(descriptor[23:12]>=1024&&descriptor[23:12]<1152)?32:16);
  before_count=accepted;range_start=stream_at;ranges++;
  for(j=0;j<818;j++)range_receipt[j]=dut.memory[j];
  for(k=0;k<n;k++)begin
   @(negedge clk);stream_valid=1;stream_data=stream_bytes[stream_at];sink_ready=1;took=0;
   if(k==n-1)begin
    sink_ready=0;
    repeat(256)begin
     @(negedge clk);
     if(v_ready||v_sealed)$fatal(1,"range retired before final byte");
     for(j=0;j<818;j++)if(range_receipt[j]!==dut.memory[j])$fatal(1,"early receipt write");
    end
    sink_ready=1;
   end
   if(GUARD==22&&k==7)test_abort=1;
   if(GUARD==23&&k==7)v_finish_valid=1;
   if(GUARD==24&&k==7)test_drop=1;
   if(GUARD==25&&k==7)v_display_ack=1;
   while(!took)begin
    @(posedge clk);took=stream_ready;
    if(!took)begin @(negedge clk);stream_clock++;sink_ready=stream_clock%7!=0;end
   end
   @(negedge clk);stream_valid=0;stream_data=8'ha5;sink_ready=0;stream_at++;
   if(k%11==0)repeat(2)@(negedge clk);
  end
  wait(v_ready);@(negedge clk);
  for(j=range_start;j<stream_at;j++)begin
   if(sink_memory[(f-905)%2*131072+sink_addresses[j][17]*65536+sink_addresses[j][16:0]]!==stream_bytes[j])$fatal(1,"sink memory mismatch");
  end
  if(accepted-before_count!=n||stream_at!=sink_at)$fatal(1,"accepted count mismatch");
 end
 endtask
'''


def tb(variant="joint"):
    s=old.tb_candidate(old.tb()).replace('254','255')
    a=STREAM_TB.index(' always @')
    s=once(s,' reg enable=0;',STREAM_TB[:a]+'\n reg enable=0;')
    s=once(s,' task output_frame;',STREAM_TB[a:]+'\n task output_frame;')
    ports=['stream_valid','stream_data','stream_ready','sink_valid','sink_ready','sink_data','sink_kind','sink_unit','sink_lane']
    s=once(s,' initial begin : negative', ''' initial begin : query_cancel
  if(GUARD==27||GUARD==28)begin
   wait(query&&query_kind==4);@(negedge clk);
   if(GUARD==27)test_abort=1;else test_gen=1;
  end
 end
 initial begin : negative''')
    s=once(s,'.fault(source_fault),','.fault(source_fault),'+','.join('.'+n+'('+n+')' for n in ports)+',')
    s=s.replace('    if(GUARD>=12)begin','    if(GUARD>=12&&GUARD<=14)begin')
    s=once(s,'    @(negedge clk);clear_output();\n   end\n  end', '    @(negedge clk);clear_output();\n    if(op==2)send_range(c);\n   end\n  end')
    s=s.replace('v_count=c[11:0];end','v_count=GUARD==26?33:c[11:0];end')
    s=s.replace('code=GUARD==15?', 'code=GUARD==27?4:GUARD==28?2:GUARD==22?4:GUARD==23?9:GUARD==24?2:GUARD==25?5:GUARD==26?(2):GUARD==15?')
    # Reference adapter rejects descriptor overflow with its local fault9.
    s=s.replace('if(source_fault!=code||', 'if((source_fault!=code&&!(GUARD==26&&source_fault==9))||')
    s=s.replace('dut.ram_b_addr<832||dut.ram_b_addr>863', '(dut.ram_b_addr>331&&dut.ram_b_addr<832)||dut.ram_b_addr>863')
    s=s.replace('  g=f-905;op=0;out_cycles=0;hash_cycles=0;', '  g=f-905;op=0;out_cycles=0;hash_cycles=0;accepted=0;stalled=0;ranges=0;stream_stage_cycles=0;')
    s=s.replace('    $fwrite(out_fd,', '    $fwrite(stream_fd,"%0d,%0d,%0d,%0d,%0d\\n",f,accepted,stalled,ranges,stream_stage_cycles);\n    $fwrite(out_fd,')
    s=s.replace('  $readmemh("commands.hex",cmds);', '  $readmemh("stream.hex",stream_bytes);$readmemh("sink.hex",sink_addresses);\n  stream_fd=$fopen("stream-cycles.csv","w");$fwrite(stream_fd,"frame,accepted,stalled,ranges,stream_stage_cycles\\n");\n  $readmemh("commands.hex",cmds);')
    return s.replace('STREAM_STATE','dut.encoder.state==dut.encoder.V_STREAM' if variant=='joint' else 'dut.adapter.state==dut.adapter.STREAM')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path)
    p.add_argument('--variant',choices=['reference','joint'],default='joint');p.add_argument('--last',type=int,default=975);p.add_argument('--guards',action='store_true');p.add_argument('--guard-cases',nargs='+',type=int);p.add_argument('--update-padding',action='store_true');p.add_argument('--map-test',type=Path);a=p.parse_args()
    d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True);pins={}
    def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    def copy(f):shutil.copyfile(pin(f),d/f.name)
    def run(exe,args,label):
        with (d/(label+'.log')).open('wb') as log:q=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=1800,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-7000:];return log
    src=sources(a.variant)
    for n,s in src.items():(d/n).write_text(s,newline='\n')
    for n in ('nes_joint255.py','probe_nes_joint255.py'):copy(ROOT/'tools'/n)
    for n in ('nes_joint254.py','probe_nes_joint254.py','nes_joint253.py','probe_nes_joint253.py','nes_phase251.py','nes_block249_rtl.py','nes_receipt250.py','nes_delta231.py','test_nes_source237.py','analyze_nes_relocation247.py','analyze_nes_binding252.py'):
        pin(ROOT/'tools'/n)
    for n in ('nes_source_query235.sv','nes_source_spi235.sv'):pin(BASE/'probes/nes-source240/board01'/n)
    board=BASE/'probes/nes-counter224/mapfit02';copy(board/'nes_native_mailbox206.sv');src['nes_native_mailbox206.sv']=(d/'nes_native_mailbox206.sv').read_text()
    hashes={n:sha(d/n) for n in src}
    if a.map_test:
        prior=json.loads(pin(a.map_test/'result.json').read_text());assert prior['passed'] and hashes==prior['rtl_hashes']
        (d/'joint.qpf').write_text('PROJECT_REVISION = "joint"\n')
        (d/'joint.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_joint255','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in src]])+'\n')
        run('C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe',['joint'],'map')
        summary=(d/'output_files/joint.map.summary').read_text();report=(d/'output_files/joint.map.rpt').read_text()
        result=dict(passed=True,summary=summary,ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and ('base_' in l or 'memory' in l)],fit=False,sta=False);print(summary)
    else:
        assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
        if a.update_padding:assert a.last==908 and not a.guards
        fixtures(d,pin,a.update_padding)
        for n in ('nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181'):
            copy(board/(n+'.sv'));src[n+'.sv']=(d/(n+'.sv')).read_text()
        for f in range(905,a.last+1):
            for ext in ('hex','palette'):copy(BASE/f'probes/nes-geometry230/stim05/frame{f}.{ext}')
            g=pin(BASE/f'probes/nes-source234/test03/frame{f}.geometry').read_bytes()
            (d/f'frame{f}.expected').write_text((g[:3872]+project(g)+g[5664:]).hex(' '))
        (d/'joint255_tb.sv').write_text(tb(a.variant),newline='\n')
        run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint255_tb.sv'],'vlog')
        log=run(a.questa_bin/'vsim.exe',['-c','work.joint255_tb',f'+LAST={a.last}','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim')
        assert f'PASS JOINT255 frames={a.last-904}' in log
        flat=defaultdict(bytearray);blocks=0
        for line in (d/'blocks.txt').read_text().splitlines():
            f,t,n,b=line.split();data=bytes.fromhex(b);assert int(t)==blocks and len(data)==int(n);flat[int(f)]+=data;blocks+=1
        for f,b in flat.items():
            want=bytes.fromhex(pin(BASE/f'probes/nes-joint249/blocktest03/frame{f}.expected.hex').read_text())
            size=int(pin(BASE/f'probes/nes-joint249/blocktest03/frame{f}.meta').read_text().split()[0]);want=want[:size]
            assert b==want,(f,'SPI source bytes mismatch')
        guards=[]
        if a.guards:
            # Each run has its own working directory; no successful evidence is overwritten.
            for case in (a.guard_cases or range(1,29)):
                assert 1<=case<=28
                gd=d/f'guard{case:02}';gd.mkdir()
                for n in ('commands.hex','expected.hex','certs.hex','hashes.hex','stream.hex','sink.hex','frame905.hex'):shutil.copyfile(d/n,gd/n)
                shutil.copyfile(d/'frame905.palette',gd/'frame905.palette')
                shutil.copyfile(d/'frame905.expected',gd/'frame905.expected')
                with (gd/'vmap.log').open('wb') as out:
                    for args in (['-c'],['work',str(d/'work')]):
                        q=subprocess.run([str(a.questa_bin/'vmap.exe'),*args],cwd=gd,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                        assert q.returncode==0
                with (gd/'vsim.log').open('wb') as out:
                    q=subprocess.run([str(a.questa_bin/'vsim.exe'),'-c','work.joint255_tb',f'-gGUARD={case}','+LAST=905','-do','onerror {quit -code 1}; run -all; quit -f'],cwd=gd,stdout=out,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
                text=(gd/'vsim.log').read_text(errors='replace');assert q.returncode==0 and f'PASS GUARD255 case={case}' in text,text[-4000:]
                guards.append(case)
        result=dict(passed=True,frames=len(flat),blocks=blocks,payload=sum(map(len,flat.values())),receipt_bytes=754*len(flat),shadow_bytes=64*len(flat),guards=guards,incremental_shadow_granules=8 if a.update_padding else 0)
        print(json.dumps(result))
    result.update(variant=a.variant,scope=__doc__,rtl_hashes=hashes,input_hashes=pins,full_arm=False,SNES=False,output_parser=False,physical=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=="__main__":main()
