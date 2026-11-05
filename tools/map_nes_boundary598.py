"""Map the actual compact collector and source together at one diagnostic boundary."""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from budget_nes_region597 import build
from check_nes_map598 import CORE,TAP,ROOT,checked_board,collector,sha

TOP = '''module boundary598(input wire clk,host_clk,reset,enable,frame_owned,geometry_valid,
 input wire begin_scene,end_scene,source_fault_in,event_valid,row_commit,row_patched,
 input wire [7:0] committed_row,input wire [63:0] event_data,
 input wire [15:0] generation,input wire [31:0] epoch,input wire [5:0] palettes,input wire [2:0] patches,
 input wire ext_response,ext_hit,input wire [63:0] ext_data,input wire SPI_SS,SPI_SCK,SPI_MOSI,
 output wire release_frame,selected,miso,host_fault,packet_fault,needs_patch,output wire [3:0] source_fault,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,output wire [15:0] query_generation,
 output wire [7:0] errors);
 wire co,cv,cr,ch,summary_hit,read_summary;wire [63:0] cd,summary;wire [15:0] map_crc;
 wire [5:0] groups;wire [7:0] objects,exceptions,rows;wire [4:0] read_group;
 wire owned=co&&frame_owned,good=cv&&geometry_valid;
 reg local_read;
 always @(posedge clk)if(query)local_read<=query_kind<4;
 nes_native_compact181 collector(.clk(clk),.reset(reset),.release_scene(release_frame),
  .begin_scene(begin_scene),.end_scene(end_scene),.source_fault(source_fault_in),.event_valid(event_valid),
  .event_data(event_data),.row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),
  .row_needs_patch(needs_patch),.owned(co),.valid(cv),.errors(errors),.object_count(objects),.exception_count(exceptions),
  .row_count(rows),.group_count(groups),.query(query && owned && good && query_generation==generation && query_kind<4 && query_index<2048),
  .query_kind(query_kind[1:0]),.query_address(query_index[10:0]),.response(cr),.hit(ch),.data(cd),
  .read_summary(read_summary),.read_group(read_group),.summary(summary),.summary_hit(summary_hit),.map_crc(map_crc));
 SOURCE source(.clk(clk),.host_clk(host_clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(good),
  .generation(generation),.epoch(epoch),.groups(groups),.palettes(palettes),.objects(objects),.exceptions(exceptions),
  .rows(rows),.patches(patches),.query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),
  .response(local_read?cr:ext_response),.hit(local_read?ch:ext_hit),.data(local_read?cd:ext_data),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(selected),.miso(miso),
  .release_frame(release_frame),.source_fault(source_fault),.host_fault(host_fault),.packet_fault(packet_fault) EXTRA);
endmodule
'''


def cached(s):
    s=s.replace('module nes_region595(','''module nes_region595(input wire summary_hit,input wire [63:0] summary_data,
 input wire [15:0] captured_crc,output wire read_summary,output wire [4:0] read_group,''')
    s=s.replace(' assign query_generation=gen;', ''' assign query_generation=gen;
 assign read_group=row[4:0];
 assign read_summary=(state==SCAN || state==25 || state==SUMMARY) && warm && row<row_total && live;''')
    old='records<=0;bytes_count<=0;map_crc<=16\'hffff;'
    assert old in s
    s=s.replace(old,'records<=groups*33;bytes_count<=groups*66;map_crc<=captured_crc;')
    start=s.index('    SCAN:if(')
    end=s.index('    ASK:',start)
    s=s[:start]+'''    SCAN:if(!warm || row==row_total)begin pos<=0;state<=MAP_END;end else state<=25;
    25:if(!summary_hit)bad(4);else begin pos<=0;state<=SUMMARY;end
'''+s[end:]
    start=s.index('   SUMMARY:begin case')
    end=s.index('   MAP_END,',start)
    # The synchronous summary port follows read_group, which remains stable through SUMMARY.
    s=s[:start]+'''   SUMMARY:write_byte=summary_data[pos[2:0]*8+:8];
'''+s[end:]
    # Hold the read request while bytes are being drained, not just during SCAN.
    start=s.index('else if(phase==0 && warm)')
    end=s.index('else begin row<=',start)
    s=s[:start]+s[end:]
    return s


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--only',choices=('original','rescan597','cached598'))
    a=p.parse_args()
    checked_board(a.board)
    archive=ROOT.parent/'probes/nes-source589/analysis02/evidence.private.zip'
    assert sha(archive)==json.loads((ROOT/'analysis/source589-archive.json').read_bytes())['sha256']
    a.out.mkdir(parents=True,exist_ok=False)
    result={}
    for name in ((a.only,) if a.only else ('original','rescan597','cached598')):
        with tempfile.TemporaryDirectory(prefix='nes598bound-') as tmp:
            d=Path(tmp); extra=''
            if name=='original':
                src='nes_region589'
                with zipfile.ZipFile(archive) as z:
                    for f in ('nes_region589','nes_native_mailbox165','nes_native_export203','nes_native_spi165'):
                        data=z.read('map/reference/'+f+'.sv')
                        if f!='nes_region589':assert data==(a.board/(f+'.sv')).read_bytes() or data.replace(b'\r\n',b'\n')==(a.board/(f+'.sv')).read_bytes().replace(b'\r\n',b'\n')
                        (d/(f+'.sv')).write_bytes(data)
            else:
                build('joint')(d);src='nes_region595'
                if name=='cached598':
                    f=d/(src+'.sv');f.write_bytes(cached(f.read_text()).encode())
                    extra=',.read_summary(read_summary),.read_group(read_group),.summary_hit(summary_hit),.summary_data(summary),.captured_crc(map_crc)'
            (d/(CORE+'.sv')).write_bytes(collector(a.board,name=='cached598').encode())
            shutil.copy(ROOT/'rtl'/TAP,d/TAP)
            top=TOP.replace('SOURCE source',src+' source').replace(' EXTRA',extra)
            if not extra:top=top.replace(' reg local_read;', " assign read_group=0;assign read_summary=0;\n reg local_read;")
            (d/'boundary598.sv').write_bytes(top.encode())
            (d/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
            files=sorted(d.glob('*.sv'))
            (d/'region.qsf').write_text('set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY boundary598\nset_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files\n'+''.join('set_global_assignment -name SYSTEMVERILOG_FILE '+f.name+'\n' for f in files))
            with (a.out/(name+'.log')).open('wb') as log:
                subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','region'],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
            report=d/'output_files/region.map.rpt';summary=(d/'output_files/region.map.summary').read_text()
            assert 'Successful' in summary and 'Lite Edition' in summary
            shutil.copy(report,a.out/(name+'.map.rpt'))
            result[name]={k:int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
                          for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('bits','Total memory bits')]}
            result[name].update(report=sha(report),pins={f.name:sha(f) for f in files})
            print(name,result[name]['LE'],flush=True)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
