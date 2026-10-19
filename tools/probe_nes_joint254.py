# SPDX-License-Identifier: MIT
"""Collector/query/projector -> N5 -> physical SPI pins; consumed-output fixture.

Actual C252 certificates are checked in RTL. Output bytes/ranges and display
ACK are fixtures; no new ARM RUN, output transport parser or SNES execution.
"""
from pathlib import Path
import argparse,ctypes,json,os,re,shutil,subprocess,binascii
from collections import defaultdict
from nes_delta231 import ROOT,BASE,sha,once
from nes_joint254 import sources
from test_nes_source237 import testbench as old_tb
from analyze_nes_relocation247 import project
from analyze_nes_binding252 import active,u16

OUTPUT=r'''
 reg v_begin_valid=0,v_target_bank=0,v_range_valid=0,v_map_range=0,v_check_valid=0,v_finish_valid=0,v_all_consumed=0,v_display_ack=0;
 reg [2:0] v_raw_count=0;reg [11:0] v_first=0,v_count=0;reg [7:0] v_check_value=0;
 wire v_ready,v_sealed,output_phase;
 reg h_start=0,h_valid=0;reg [1:0] h_kind=0;reg [3:0] h_index=0;reg [7:0] h_data=0;wire h_ready;
 reg [10:0] h_scroll_length=0;reg [23:0] h_table_lengths=0;reg [31:0] h_display_base=0;reg [7:0] h_mask=0;
 reg [63:0] cmds[0:100000];reg [7:0] receipts[0:71*754-1],certs[0:71*32-1],hashes[0:71*64-1];
 integer cmd_at=0,op,out_fd,out_cycles=0,hash_cycles=0,crc_cycles=0;reg [63:0] c;
 integer hash_sent=0,cert_sent=0;reg in_cert=0,skip_hash=0,test_abort=0,test_drop=0,test_gen=0;
 reg [7:0] keep[0:395];
 task clear_output;
 begin v_begin_valid=0;v_range_valid=0;v_check_valid=0;v_finish_valid=0;v_display_ack=0;h_start=0;h_valid=0;end
 endtask
 always @(posedge clk)if(!reset&&output_phase&&dut.encoder.state!=dut.encoder.V_CLEARALL)begin
  out_cycles++;
  if(dut.encoder.state>=dut.encoder.H_BYTES)hash_cycles++;
 end
 always @(posedge clk)if(!reset&&dut.transport_crc_pending)begin
  crc_cycles++;
  if(dut.byte_valid&&dut.byte_ready)$fatal(1,"CRC ownership collision");
 end
 task output_frame;
 integer g,j;
 begin
  g=f-905;op=0;out_cycles=0;hash_cycles=0;
  h_scroll_length={certs[g*32+15],certs[g*32+14]};
  h_table_lengths={certs[g*32+18],certs[g*32+17],certs[g*32+16]};h_mask=certs[g*32+19];
  h_display_base=g>=2?g-1:0;
  while(op!=5)begin
   c=cmds[cmd_at];cmd_at++;op=c[63:60];
   if(GUARD==4)begin
    if(op==10)skip_hash=c[3:0]==15;
    else if(op!=11)skip_hash=0;
    if(skip_hash)continue;
   end
   if(op==7)begin
    if(!v_sealed||source_fault)$fatal(1,"output not sealed");
    for(j=0;j<754;j++)if(dut.memory[j<332?j:j+64]!==receipts[g*754+j])$fatal(1,"receipt frame%0d byte%0d",f,j);
    for(j=0;j<64;j++)if(dut.memory[332+j]!==hashes[g*64+j])$fatal(1,"CRC RAM frame%0d byte%0d",f,j);
    $fwrite(out_fd,"%0d,%0d,%0d,%0d\n",f,out_cycles,hash_cycles,crc_cycles);
    if(GUARD>=12)begin
     @(negedge clk);
     if(GUARD==12)test_abort=1;else if(GUARD==13)test_drop=1;else test_gen=1;
     #1;if(v_sealed)$fatal(1,"seal visible after cancellation");
     wait(source_fault);wait(1'b0);
    end
   end else begin
    if(op==11)wait(h_ready);else if(op!=5)wait(v_ready);
    @(negedge clk);clear_output();
    case(op)
     1:begin v_begin_valid=1;v_target_bank=c[0]^(GUARD==11);v_raw_count=c[6:4];end
     2:begin v_range_valid=1;v_map_range=c[32];v_first=c[23:12];v_count=c[11:0];end
     3:begin v_check_valid=1;v_check_value=c[7:0];end
     4:begin v_finish_valid=1;v_all_consumed=c[0];end
     5:v_display_ack=1;
     10:begin h_start=1;h_kind=0;h_index=(GUARD==5&&c[3:0]==1)?0:c[3:0];end
     11:begin
      h_valid=1;h_data=c[7:0];
      if(in_cert)begin
       if((GUARD==1&&cert_sent==22)||(GUARD==2&&cert_sent==8)||(GUARD==3&&cert_sent==30))h_data=c[7:0]^1;
       cert_sent++;
      end else begin hash_sent++;if(GUARD==6&&hash_sent==7)test_abort=1;end
     end
     12:begin h_start=1;h_kind=1;if(GUARD==8)v_display_ack=1;end
     13:begin
      h_start=1;h_kind=2;in_cert=1;cert_sent=0;
      if(GUARD==7)begin h_start=0;v_finish_valid=1;v_all_consumed=1;end
     end
     default:$fatal(1,"output command %0d",op);
    endcase
    @(negedge clk);clear_output();
   end
  end
  wait(start_ready);
 end
 endtask
'''


def tb():
    s=old_tb().replace('source237_tb','joint254_tb').replace('nes_source237 dut','nes_joint254 dut')
    s=s.replace('parameter real PHASE=3.5;', 'parameter real PHASE=3.5;parameter integer GUARD=0;')
    s=s.replace(".abort_source(1'b0)",'.abort_source(test_abort)')
    s=s.replace('.frame_owned(owned)', '.frame_owned(owned&&!test_drop)').replace('.frame_generation(generation)', ".frame_generation(generation^{15'd0,test_gen})")
    s=s.replace('.hit(hit),.data(data),', ".hit(hit),.data((GUARD==9&&query_kind==4)?data^64'h8000000000000000:data),")
    s=s.replace('if(source_fault)$fatal', 'if(source_fault&&GUARD==0)$fatal')
    s=s.replace('expected[0:5740]','expected[0:4397]')
    s=s.replace('dut.valid&&dut.ready','dut.in_valid&&dut.in_ready').replace('dut.offset','dut.in_offset').replace('dut.value','dut.in_data')
    s=s.replace('>=635','>=512').replace('>=5741','>=4398').replace('seen!=5741','seen!=4398')
    s=s.replace('if(dut.encoder.state!=dut.encoder.IDLE)', 'if(dut.encoder.state!=dut.encoder.IDLE&&!output_phase)')
    a=OUTPUT.index(' task clear_output;')
    s=s.replace(' reg enable=0;',OUTPUT[:a]+'\n reg enable=0;')
    s=s.replace(' initial begin : consumer',OUTPUT[a:]+'\n initial begin : consumer')
    s=s.replace(' initial begin : consumer', r'''
 initial begin : negative
  reg [7:0] stopped[0:1023];integer code;
  if(GUARD)begin
   wait(source_fault!=0);repeat(3)@(negedge clk);
   code=GUARD>=13?2:GUARD==12?4:(GUARD==4||GUARD==7||GUARD==9)?3:GUARD==5?2:GUARD==6?4:GUARD==8?5:GUARD==10?5:7;
   if(source_fault!=code||v_sealed||start_ready||h_ready||v_ready)$fatal(1,"guard%0d expected%0d actual%0d",GUARD,code,source_fault);
   for(integer j=0;j<1024;j++)stopped[j]=dut.memory[j];
   repeat(12)@(negedge clk);
   for(integer j=0;j<1024;j++)if(stopped[j]!==dut.memory[j])$fatal(1,"write after fault");
   $display("PASS GUARD254 case=%0d code=%0d",GUARD,source_fault);$finish;
  end
 end
 initial begin : consumer''')
    s=s.replace('wait(enable);ended=0;', "wait(enable);ended=0;if(GUARD==10)begin request(8'hd3,generation,1);transfer(8);end")
    ports=['v_begin_valid','v_target_bank','v_raw_count','v_range_valid','v_map_range','v_first','v_count','v_check_valid','v_check_value','v_finish_valid','v_all_consumed','v_display_ack','v_ready','v_sealed','h_start','h_kind','h_index','h_valid','h_data','h_ready','h_scroll_length','h_table_lengths','h_display_base','h_mask','output_phase']
    s=s.replace('.fault(source_fault));','.fault(source_fault),'+','.join('.'+n+'('+n+')' for n in ports)+');')
    s=s.replace('   wait(start_ready);@(negedge clk);enable=1;', '   wait(start_ready);for(integer j=0;j<396;j++)keep[j]=dut.memory[j];crc_cycles=0;\n   @(negedge clk);enable=1;')
    s=s.replace('   manual_release=1;', '''   for(integer j=0;j<396;j++)if(keep[j]!==dut.memory[j])$fatal(1,"persistent state clobbered");
   output_frame();
   manual_release=1;''')
    s=s.replace('  stats=$fopen', '''  $readmemh("commands.hex",cmds);$readmemh("expected.hex",receipts);$readmemh("certs.hex",certs);$readmemh("hashes.hex",hashes);
  out_fd=$fopen("output-cycles.csv","w");$fwrite(out_fd,"frame,total,hash_states,transport_crc_cycles\\n");
  stats=$fopen''')
    return s.replace('PASS SOURCE237','PASS JOINT254')


def fixtures(d,pin,update_padding=False):
    prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run'
    packets=defaultdict(list)
    for f in sorted(prior.glob('req-*.bin')):
        b=pin(f).read_bytes();packets[u16(b,8)].append(b)
    dll=pin(BASE/'probes/nes-joint252/test03/binding.dll')
    lib=ctypes.CDLL(str(dll));fn=lib.cert252;ptr=ctypes.POINTER(ctypes.c_ubyte)
    fn.argtypes=[ptr]+[ctypes.c_uint]*9+[ptr];fn.restype=ctypes.c_int
    old=[int(v,16) for v in pin(BASE/'probes/nes-joint250/receipt02/commands.hex').read_text().split()]
    at=0;commands=[];certificates=bytearray();hh=bytearray(64);hashes=bytearray()
    expected=bytearray.fromhex(pin(BASE/'probes/nes-joint250/receipt02/expected.hex').read_text())
    def cmd(op,v=0):commands.append((op<<60)|v)
    for g in range(1,72):
        bundle=bytearray(pin(prior/f'expected-{g}.bin').read_bytes()[5152:])
        if update_padding and g in (3,4):
            for j in (2,7,12,15):bundle[3169+16*j]^=1
        seal=next(b for b in packets[g] if b[0]==3);raw=u16(seal,38);mask=u16(seal,34);n=active(bundle,raw)[0][1]
        cert=(ctypes.c_ubyte*32)();assert fn((ctypes.c_ubyte*3418).from_buffer_copy(bundle),mask,raw,n,1,g,g,max(0,g-2),(g-1)%2,1,cert)
        cert=bytes(cert);certificates+=cert
        updates={}
        for b in packets[g]:
            if b[1]!=5 or b[0] not in (2,4,5):continue
            pos=u16(b,10);data=b[16:]
            if b[0] in (4,5):data*=u16(b,14)//len(data)
            for j in range(16):
                lo=3169+j*16;hi=min(3418,lo+16)
                if max(lo,pos)<min(hi,pos+len(data)):
                    assert pos<=lo and pos+len(data)>=hi and j not in updates
                    updates[j]=data[lo-pos:hi-pos]
        if update_padding and g in (3,4):
            for j in (2,7,12,15):updates[j]=bundle[3169+16*j:min(3418,3169+16*(j+1))]
        inserted=False;checks=0
        while True:
            c=old[at];at+=1;op=c>>60
            if op==2 and not (c>>32)&1:
                first=(c>>12)&4095;count=c&4095
                count=min(first+count,1312)-first
                if count>0:cmd(2,(first<<12)|count)
            else:
                if op==3 and not inserted:
                    for j,data in sorted(updates.items()):
                        cmd(10,j)
                        for v in data:cmd(11,v)
                        pos=((g-1)%2)*32+2*j;hh[pos:pos+2]=binascii.crc_hqx(data,65535).to_bytes(2,'little')
                    inserted=True
                if op==3:
                    if update_padding and g in (3,4) and checks in (164,165):
                        extra=0x84 if checks==164 else 0x90;c|=extra
                        expected[(g-1)*754+332+checks]|=extra
                    checks+=1
                if op==4:
                    cmd(12)
                    for v in bundle[:n]:cmd(11,v)
                    cmd(13)
                    for v in cert:cmd(11,v)
                commands.append(c)
            if op==5:break
        hashes+=hh
    (d/'commands.hex').write_text('\n'.join(f'{c:016x}' for c in commands)+'\n')
    (d/'certs.hex').write_text(certificates.hex(' '));(d/'hashes.hex').write_text(hashes.hex(' '))
    (d/'expected.hex').write_text(expected.hex(' '))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path)
    p.add_argument('--variant',choices=['fsm','joint'],default='joint');p.add_argument('--last',type=int,default=975);p.add_argument('--guards',action='store_true');p.add_argument('--update-padding',action='store_true');p.add_argument('--map-test',type=Path);a=p.parse_args()
    d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True);pins={}
    def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    def copy(f):shutil.copyfile(pin(f),d/f.name)
    def run(exe,args,label):
        with (d/(label+'.log')).open('wb') as log:q=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=1800,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-7000:];return log
    src=sources(a.variant)
    for n,s in src.items():(d/n).write_text(s,newline='\n')
    for n in ('nes_joint254.py','probe_nes_joint254.py'):copy(ROOT/'tools'/n)
    for n in ('nes_joint253.py','probe_nes_joint253.py','nes_phase251.py','nes_block249_rtl.py','nes_receipt250.py','nes_delta231.py','test_nes_source237.py','analyze_nes_relocation247.py','analyze_nes_binding252.py'):
        pin(ROOT/'tools'/n)
    for n in ('nes_source_query235.sv','nes_source_spi235.sv'):pin(BASE/'probes/nes-source240/board01'/n)
    board=BASE/'probes/nes-counter224/mapfit02';copy(board/'nes_native_mailbox206.sv');src['nes_native_mailbox206.sv']=(d/'nes_native_mailbox206.sv').read_text()
    hashes={n:sha(d/n) for n in src}
    if a.map_test:
        prior=json.loads(pin(a.map_test/'result.json').read_text());assert prior['passed'] and hashes==prior['rtl_hashes']
        (d/'joint.qpf').write_text('PROJECT_REVISION = "joint"\n')
        (d/'joint.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_joint254','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in src]])+'\n')
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
        (d/'joint254_tb.sv').write_text(tb_candidate(tb()) if a.variant=='joint' else tb(),newline='\n')
        run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint254_tb.sv'],'vlog')
        log=run(a.questa_bin/'vsim.exe',['-c','work.joint254_tb',f'+LAST={a.last}','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim')
        assert f'PASS JOINT254 frames={a.last-904}' in log
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
            for case in range(1,22) if a.variant=='joint' else range(1,15):
                gd=d/f'guard{case:02}';gd.mkdir()
                for n in ('commands.hex','expected.hex','certs.hex','hashes.hex','frame905.hex'):shutil.copyfile(d/n,gd/n)
                shutil.copyfile(d/'frame905.palette',gd/'frame905.palette')
                shutil.copyfile(d/'frame905.expected',gd/'frame905.expected')
                with (gd/'vmap.log').open('wb') as out:
                    for args in (['-c'],['work',str(d/'work')]):
                        q=subprocess.run([str(a.questa_bin/'vmap.exe'),*args],cwd=gd,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                        assert q.returncode==0
                with (gd/'vsim.log').open('wb') as out:
                    q=subprocess.run([str(a.questa_bin/'vsim.exe'),'-c','work.joint254_tb',f'-gGUARD={case}','+LAST=905','-do','onerror {quit -code 1}; run -all; quit -f'],cwd=gd,stdout=out,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
                text=(gd/'vsim.log').read_text(errors='replace');assert q.returncode==0 and f'PASS GUARD254 case={case}' in text,text[-4000:]
                guards.append(case)
        result=dict(passed=True,frames=len(flat),blocks=blocks,payload=sum(map(len,flat.values())),receipt_bytes=754*len(flat),shadow_bytes=64*len(flat),guards=guards,incremental_shadow_granules=8 if a.update_padding else 0)
        print(json.dumps(result))
    result.update(variant=a.variant,scope=__doc__,rtl_hashes=hashes,input_hashes=pins,full_arm=False,SNES=False,output_parser=False,physical=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def tb_candidate(s):
    s=once(s,' reg [10:0] h_scroll_length=0;reg [23:0] h_table_lengths=0;reg [31:0] h_display_base=0;reg [7:0] h_mask=0;',
           ' reg context_valid=0;reg [7:0] context_data=0;wire context_ready;')
    for n in ('h_scroll_length','h_table_lengths','h_display_base','h_mask'):
        s=s.replace(',.'+n+'('+n+')','')
    s=s.replace('.output_phase(output_phase)', '.output_phase(output_phase),.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready)')
    a=s.index('  h_scroll_length=');b=s.index('  while(op!=5)',a)
    s=s[:a]+r'''
  in_cert=0;
  for(j=0;j<32;j++)begin
   wait(context_ready);@(negedge clk);context_valid=1;context_data=certs[g*32+j];
   if((GUARD==1&&j==22)||(GUARD==2&&j==8)||(GUARD==3&&j==30))context_data=context_data^1;
   if(GUARD==15&&j==7)test_abort=1;
   if(GUARD==16&&j==7)v_begin_valid=1;
   if(GUARD==17&&(j==14||j==15))context_data=0;
   if(GUARD==18&&j==16)context_data=0;
   if(GUARD==19&&j>=26&&j<=29)context_data=certs[g*32+j-18];
   if(GUARD==20&&j==24)context_data=context_data^1;
   if(GUARD==21&&j==19)context_data=0;
   @(negedge clk);context_valid=0;context_data=8'ha5;
  end
'''+s[b:]
    s=s.replace('   if(op==7)begin', '   if(op==11&&in_cert)continue;\n   if(op==7)begin')
    # The 32 staged bytes are the single certificate wire copy. H_CERT now
    # replays shared RAM internally; external data is deliberately unrelated.
    s=s.replace('code=GUARD>=13?', 'code=GUARD==15?4:GUARD>=16?7:GUARD>=13?')
    s=s.replace('    for(j=0;j<754;j++)', '    for(j=0;j<32;j++)if(dut.memory[832+j]!==certs[g*32+j])$fatal(1,"context RAM changed");\n    for(j=0;j<754;j++)')
    s=s.replace(' task clear_output;', r'''
 always @(posedge clk)if(!reset&&output_phase)begin
  if(dut.ram_a_we&&dut.ram_a_addr>817)$fatal(1,"output A ownership");
  if(dut.ram_b_we&&(dut.ram_b_addr<832||dut.ram_b_addr>863))$fatal(1,"context B ownership");
  if(dut.ram_a_we&&dut.ram_b_we&&dut.ram_a_addr==dut.ram_b_addr)$fatal(1,"phase RAM collision");
 end
 task clear_output;''')
    return s

if __name__=='__main__':main()
