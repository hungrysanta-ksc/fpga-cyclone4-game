# SPDX-License-Identifier: MIT
"""Bounded semantic/shift encoder experiment, not a collector or product wire.

Remove the old raster codec at its source, retain row shifts, literal gaps,
CRC, raw, admission, stalled publication and ACK lifetimes. Geometry input
is an already validated4398B projection fixture; query/projector is excluded.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha,once
from analyze_nes_relocation247 import project
from analyze_nes_path236 import variant


def encoder():
    s=(BASE/'probes/nes-source240/board01/nes_source_encoder240.sv').read_text()
    s=s.replace('nes_source_encoder240','nes_source_encoder249').replace('5741','4398')
    s=s.replace('base_hi[0:2047]','base_hi[0:511]').replace('base_addr[10:0]','base_addr[8:0]')
    s=s.replace('cursor<2112||(cursor>=3872&&cursor<5664)','cursor<2112')
    s=once(s,'if(cursor<2112)state<=ROWREAD;else state<=MASKREAD;','state<=ROWREAD;')
    s=once(s,'else begin row_size<=cursor<2112?66:8;state<=FETCH;end','else begin row_size<=66;state<=FETCH;end')
    # Cut the entire obsolete raster controller, not just its output choice.
    a=s.index('    COPYREAD:state<=COPYWRITE;');b=s.index('    GEOTRAILER:',a)
    s=s[:a]+s[b:]
    a=s.index('     if(raster_mode&&old_byte!=new_byte');b=s.index('     state<=LAFTER;',a)
    s=s[:a]+s[b:]
    a=s.index('     else if(raster_mode&&cheap_cost+3+lit_used>=13)');b=s.index('    LH0:',a)
    s=s[:a]+'     else begin cheap_target<=0;state<=LH0;end\n'+s[b:]
    s=once(s,'LH2:if(cheap_target)begin build_i<=0;state<=COPYREAD;end else state<=LDONE;','LH2:state<=LDONE;')
    a=s.index('     if(cheap_target)begin cheap_cost<=cheap_cost+3+lit_used;');b=s.index('    GEOTRAILER:',a)
    s=s[:a]+'     emit_record(lit_used+3,S_FLUSH,0,0);\n    end\n'+s[b:]
    s=s.replace('L_MAP:state<=MAPLNEXT;L_RASTER:state<=RASTERNEXT;','L_MAP:state<=MAPLNEXT;')
    s=s.replace('F_LITERAL:state<=LITERAL;F_GROUP:state<=GROUPOUT;F_RAW:state<=RAWDONE;',
                'F_LITERAL:state<=LITERAL;F_RAW:state<=RAWDONE;')
    s=s.replace('S_GROUP:state<=GROUPDONE;S_CHEAP:state<=CHEAPNEXT;S_RAW:state<=RAWSTART;',
                'S_RAW:state<=RAWSTART;')
    s=s.replace('   RASTERDONE:expanded_delta={5\'d0,rows,3\'d0};\n','')
    s=s.replace("   CHEAPDONE:expanded_delta={8'd0,record_length}-16'd3;\n",'')
    s=once(s,'state==SHIFTDONE||state==RASTERDONE||state==CHEAPDONE||','state==SHIFTDONE||')
    s=s.replace('(state==LDONE&&!cheap_target&&!raw_mode)','(state==LDONE&&!raw_mode)')
    s=once(s,"wire [8:0] lit_target=cheap_target?C+cheap_cost:P;","wire [8:0] lit_target=P;")
    s=s.replace('   S_GROUP:if(rec_i>=5)send_addr=M+special_i;\n','').replace('   S_CHEAP:send_addr=C+cheap_i+rec_i;\n','')
    a=s.index('   COPYREAD,COPYWRITE:begin');b=s.index('   SHIFTBUILD:',a);s=s[:a]+s[b:]
    a=s.index('   RASTERBUILD:begin');b=s.index('   GEOTRAILER,ENDTRAILER:',a);s=s[:a]+s[b:]
    # Dead enum/register declarations remain as source history; synthesis must
    # eliminate them. A MAP report is not proof of the missing query/projector.
    return s


TB=r'''
`timescale 1ns/1ps
module source249_tb;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,start=0,abort_source=0,owned=1,geometry_valid=1;
 reg [15:0] generation=1;reg [31:0] serial=1,epoch=1;reg [2:0] patches=0;
 wire start_ready,in_ready,raw_query,record_valid,byte_valid,ack_ready,done;
 wire [12:0] raw_index;wire [7:0] length,value;wire flush;wire [3:0] fault;
 reg in_valid=0;reg [7:0] in_data=0;reg [12:0] in_offset=0;
 reg raw_response=0;reg [63:0] raw_data=0;
 reg ack_valid=0,ack_accept=1;reg [15:0] ack_generation=1;
 reg [7:0] geometry[0:4397],raw[0:2047],expected[0:65535];
 reg [7:0] expected_length[0:8191];
 integer tick=0,seen=0,record_i=0,record_bytes=0,f,fd,cycles,prepared,total_expected,total_records,raw_length;
 integer boundary_fd;string path;reg hold=0;reg [7:0] held;
 wire record_ready=tick%11!=0;wire byte_ready=tick%127>=64;
 nes_source_encoder249 dut(.clk(clk),.reset(reset),.abort_source(abort_source),.start(start),.start_ready(start_ready),
 .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),.content_epoch(epoch),.frame_serial(serial),.patch_count(patches),
 .in_valid(in_valid),.in_ready(in_ready),.in_data(in_data),.in_offset(in_offset),
 .raw_query(raw_query),.raw_index(raw_index),.raw_response(raw_response),.raw_hit(1'b1),.raw_data(raw_data),
 .record_valid(record_valid),.record_ready(record_ready),.record_length(length),.record_flush(flush),
 .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(value),
 .ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_generation),.done(done),.fault(fault));
 always @(negedge clk)begin
  tick=tick+1;in_valid=0;
  if(in_ready)begin in_valid=1;in_offset=dut.cursor;in_data=geometry[dut.cursor];end
 end
 always @(posedge clk)begin raw_response<=raw_query;if(raw_query)raw_data<={56'd0,raw[raw_index]};end
 always @(posedge clk)if(!reset)begin
  if(dut.state!=dut.IDLE)begin cycles++;if(!record_valid&&!byte_valid&&dut.state!=dut.SREAD&&dut.state!=dut.WAITACK)prepared++;end
  if(fault&&f<=975)$fatal(1,"unexpected fault f=%0d code=%0d",f,fault);
  if(dut.a_we&&dut.b_we&&dut.a_addr==dut.b_addr)$fatal(1,"write collision");
  if(dut.base_we&&dut.base_addr>=4398)$fatal(1,"base bounds");
  if(hold&&(!byte_valid||held!==value))$fatal(1,"published byte changed");
  hold=byte_valid&&!byte_ready;held=value;
  if(record_valid&&record_ready)begin
   if(length!==expected_length[record_i])$fatal(1,"length f=%0d rec=%0d got=%0d want=%0d",f,record_i,length,expected_length[record_i]);
   if(flush!==(record_i==total_records-1))$fatal(1,"flush boundary");
   record_i++;record_bytes=0;
  end
  if(byte_valid&&byte_ready)begin
   if(value!==expected[seen])$fatal(1,"byte f=%0d at=%0d got=%0h want=%0h state=%0d",f,seen,value,expected[seen],dut.state);
   seen++;record_bytes++;
  end
 end
 initial begin
  fd=$fopen("cycles.csv","w");$fwrite(fd,"frame,total,prepare,payload,records\n");
  repeat(4)@(negedge clk);reset=0;
  for(f=905;f<=975;f++)begin
   path=$sformatf("frame%0d.geometry.hex",f);$readmemh(path,geometry);
   path=$sformatf("frame%0d.raw.hex",f);$readmemh(path,raw);
   path=$sformatf("frame%0d.expected.hex",f);$readmemh(path,expected);
   path=$sformatf("frame%0d.lengths.hex",f);$readmemh(path,expected_length);
   path=$sformatf("frame%0d.meta",f);boundary_fd=$fopen(path,"r");
   if($fscanf(boundary_fd,"%d %d %d",total_expected,total_records,raw_length)!=3)$fatal(1,"meta");$fclose(boundary_fd);
   patches=raw_length/256;seen=0;record_i=0;cycles=0;prepared=0;
   wait(start_ready);@(negedge clk);start=1;@(negedge clk);start=0;
   wait(ack_ready);repeat(20)@(negedge clk);
   if(seen!=total_expected||record_i!=total_records)$fatal(1,"totals");
   for(integer k=0;k<4398;k++)begin
    if(k<4096)begin if(dut.base_lo[k]!==geometry[k])$fatal(1,"base low");end
    else if(dut.base_hi[k-4096]!==geometry[k])$fatal(1,"base high");
   end
   ack_generation=generation;ack_valid=1;@(negedge clk);ack_valid=0;wait(done);
   $fwrite(fd,"%0d,%0d,%0d,%0d,%0d\n",f,cycles,prepared,seen,record_i);
   @(negedge clk);generation++;serial++;
  end
  // Abort invalidates the speculative base. A common reset is mandatory.
  @(negedge clk);abort_source=1;@(negedge clk);abort_source=0;@(negedge clk);
  if(fault!=4||dut.base_valid||start_ready)$fatal(1,"abort base lifetime");
  reset=1;repeat(3)@(negedge clk);reset=0;serial=2;
  @(negedge clk);start=1;@(negedge clk);start=0;@(negedge clk);
  if(fault!=1||dut.base_valid)$fatal(1,"missing cold admission");
  $fclose(fd);$display("PASS SOURCE249 frames=71 abort_and_cold_guards=2");$finish;
 end
 initial begin #2000000000;$fatal(1,"timeout");end
endmodule
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--questa-bin',type=Path);p.add_argument('--map-test',type=Path);p.add_argument('--block',action='store_true');p.add_argument('--directed',action='store_true')
    a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
    def run(exe,args,label):
        with (d/(label+'.log')).open('wb') as log:q=subprocess.run([str(exe),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(label+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
        return text
    module='nes_source_block249' if a.block else 'nes_source_encoder249'
    from nes_block249_rtl import RTL
    from nes_block249 import encode,decode
    source=d/(module+'.sv');source.write_text(RTL if a.block else encoder(),encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/'probe.py')
    for name in ('nes_block249_rtl.py','nes_block249.py'):shutil.copyfile(ROOT/'tools'/name,d/name)
    pins={};probe=BASE/'probes/nes-wholepath247/observer03';previous=bytes(4398)
    if a.map_test:
        test=json.loads((a.map_test/'result.json').read_text());assert test['passed'] and sha(source)==test['encoder_sha256']
        (d/'source.qpf').write_text('PROJECT_REVISION = "source"\n')
        (d/'source.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
            'set_global_assignment -name TOP_LEVEL_ENTITY '+module,'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
            'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name SYSTEMVERILOG_FILE '+source.name])+'\n')
        run('C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe',['source'],'map')
        summary=(d/'output_files/source.map.summary').read_text();report=(d/'output_files/source.map.rpt').read_text()
        result=dict(passed=True,scope='Standalone tested encoder MAP only;no query/projector,validator,wholeboard FIT or STA.',
            encoder_sha256=sha(source),test_sha256=sha(a.map_test/'result.json'),summary=summary,
            ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and ('base_' in l or 'scratch' in l)],
            query_projector_included=False,validator_included=False,fit=False,sta=False)
        print(summary)
    else:
        assert a.questa_bin and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
        total=0
        frame_count=74 if a.directed else 71
        for g,f in enumerate(range(905,905+frame_count),1):
            if f<=975:
                geo=probe/f'frame{f}.geometry';rawfile=probe/f'frame{f}.raw';data=geo.read_bytes();raw=rawfile.read_bytes()
                pins[geo.relative_to(BASE).as_posix()]=sha(geo);pins[rawfile.relative_to(BASE).as_posix()]=sha(rawfile)
                current=data[:3872]+project(data)+data[5664:]
            else:
                current=bytearray(previous);raw=b''
                if f==976:
                    current[:66]=b'\x19\x2a'+previous[:64];current[2046:2112]=previous[2048:2112]+b'\x13\x24';current[-1]^=1
                    raw=bytes(i%64 for i in range(256))
                elif f==977:
                    current[:66]=previous[2:66]+b'\x1a\x2b';current[2112]^=1;current[4352]^=1
                current=bytes(current)
            records=encode(previous,current,raw,g,g) if a.block else variant(previous,current,raw,g,g,'shift')
            if a.block:assert decode(records,previous,g,g)==(current,raw)
            previous=current
            flat=b''.join(records);total+=len(flat)
            for label,b in [('geometry',current),('raw',raw+bytes(2048-len(raw))),('expected',flat+bytes(65536-len(flat))),('lengths',bytes(map(len,records))+bytes(8192-len(records)))]:
                (d/f'frame{f}.{label}.hex').write_text(b.hex(' '),encoding='ascii')
            (d/f'frame{f}.meta').write_text(f'{len(flat)} {len(records)} {len(raw)}\n')
        tb=TB.replace('nes_source_encoder249',module)
        if a.directed:tb=tb.replace('975','978').replace('frames=71','frames=74')
        (d/'source249_tb.sv').write_text(tb,encoding='utf-8',newline='\n')
        run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv',source.name,'source249_tb.sv'],'vlog')
        log=run(a.questa_bin/'vsim.exe',['-c','work.source249_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim')
        assert f'PASS SOURCE249 frames={frame_count} abort_and_cold_guards=2' in log
        result=dict(passed=True,scope=__doc__,frames=frame_count,recorded_frames=71,synthetic_frames=frame_count-71,exact_payload_bytes=total,base_bytes_checked=frame_count*4398,
            encoder_sha256=sha(source),input_hashes=pins,guard_cases=2,stall_window=64,collector_bound=False,
            projection_in_hardware=False,full_arm=False,physical=False,fit=False)
        print(json.dumps({k:v for k,v in result.items() if k!='input_hashes'}))
    result['block_format']=a.block;result['script_sha256']=sha(Path(__file__));(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
