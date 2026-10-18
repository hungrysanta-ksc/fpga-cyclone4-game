# SPDX-License-Identifier: MIT
"""Same replacement boundary MAP: old exporter/records/ACK/SPI vs235 endpoints.

New encoder stays external input/output ports. This is NOT an encoder fit,
equivalence proof, whole-board fit, or timing approval.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha

HEADER='''module source_path236(
 input wire src_clk,host_clk,reset,enable,abort_source,start,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [2:0] patch_count,input wire [7:0] row_count,object_count,exception_count,
 input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output wire release_frame,busy,output wire [3:0] error,observe,
 output wire out_valid,input wire out_ready,output wire [7:0] out_data,
 output wire [12:0] out_offset,output wire done,start_ready,
 input wire record_valid,output wire record_ready,input wire [7:0] record_length,
 input wire record_flush,byte_valid,output wire byte_ready,input wire [7:0] byte_data,
 output wire ack_valid,input wire ack_ready,output wire ack_accept,output wire [15:0] ack_generation,
 output wire source_fault,host_fault
);
'''
QUERY='''.frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(frame_generation),
 .patch_count(patch_count),.row_count(row_count),.object_count(object_count),.exception_count(exception_count),
 .group_count(group_count),.palette_count(palette_count),.query(query),.query_kind(query_kind),
 .query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data)'''
OLD='''
 wire tx_valid,tx_ready,host_valid,host_ready,host_ack_valid,host_ack_ready,host_ack_accept,old_ack_valid,old_ack_ready;
 wire [95:0] tx_data,host_data;wire [15:0] host_generation;wire [16:0] old_ack_data;wire spi_reset;
 nes_native_export203 #(.MAX_CYCLES(33554432)) exporter(.clk(src_clk),.reset(reset),.enable(enable),
 QUERY,
 .release_frame(release_frame),.busy(busy),.error(error),.observe_state177(observe),
 .tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),.ack_valid(old_ack_valid),.ack_ready(old_ack_ready),
 .ack_accept(old_ack_data[16]),.ack_generation(old_ack_data[15:0]));
 nes_native_mailbox165 #(.WIDTH(96)) records(src_clk,host_clk,reset,tx_valid,tx_ready,tx_data,host_valid,host_ready,host_data);
 nes_native_mailbox165 #(.WIDTH(17)) prepared(host_clk,src_clk,reset,host_ack_valid,host_ack_ready,{host_ack_accept,host_generation},old_ack_valid,old_ack_ready,old_ack_data);
 nes_domain_reset124 spi_release(.clk(host_clk),.raw_reset(reset),.reset(spi_reset));
 nes_native_spi165 spi(.clk(host_clk),.reset(spi_reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .selected(selected),.miso(miso),.fault(host_fault),.record_valid(host_valid),.record_ready(host_ready),.record_data(host_data),
 .ack_valid(host_ack_valid),.ack_ready(host_ack_ready),.ack_accept(host_ack_accept),.ack_generation(host_generation));
 assign source_fault=|error;
 assign out_valid=0;assign out_data=0;assign out_offset=0;assign done=0;assign start_ready=0;
 assign record_ready=0;assign byte_ready=0;assign ack_valid=0;assign ack_accept=0;assign ack_generation=0;
'''.replace('QUERY',QUERY)
NEW='''
 nes_source_query235 reader(.clk(src_clk),.reset(reset),.abort_source(abort_source),.start(start),.start_ready(start_ready),
 QUERY,
 .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_offset(out_offset),.done(done),.fault(error));
 nes_source_spi235 spi(.src_clk(src_clk),.host_clk(host_clk),.reset(reset),.abort_source(abort_source),
 .record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),
 .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .selected(selected),.miso(miso),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_generation),
 .source_fault(source_fault),.host_fault(host_fault));
 assign release_frame=0;assign busy=0;assign observe=0;
'''.replace('QUERY',QUERY)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    board=BASE/'probes/nes-counter224/mapfit02';result=dict(scope=__doc__,projects={},new_fit=False,new_sta=False)
    for name,body in (('old',OLD),('new',NEW)):
        d=out/name;d.mkdir()
        files=[board/(s+'.sv') for s in ('nes_native_export203','nes_native_mailbox165','nes_native_spi165','nes_domain_reset124')] if name=='old' else [ROOT/'src/nes/rtl'/('nes_source_'+s+'235.sv') for s in ('query','spi')]+[board/'nes_native_mailbox206.sv']
        (d/'source_path236.sv').write_text(HEADER+body+'endmodule\n',newline='\n')
        qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
             'set_global_assignment -name TOP_LEVEL_ENTITY source_path236','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
             'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name SYSTEMVERILOG_FILE source_path236.sv']
        for f in files:shutil.copyfile(f,d/f.name);qsf.append('set_global_assignment -name SYSTEMVERILOG_FILE '+f.name)
        (d/'path.qpf').write_text('PROJECT_REVISION = "path"\n');(d/'path.qsf').write_text('\n'.join(qsf)+'\n')
        with (d/'map.log').open('wb') as log:
            cp=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','path'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        assert cp.returncode==0,(d/'map.log').read_text(errors='replace')[-4000:]
        summary=(d/'output_files/path.map.summary').read_text();report=(d/'output_files/path.map.rpt').read_text()
        result['projects'][name]=dict(le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',summary)[1].replace(',','')),
            ff=int(re.search(r'Total registers\s*:\s*([\d,]+)',summary)[1].replace(',','')),summary=summary,
            ram_rows=[s.strip() for s in report.splitlines() if '; M9K ' in s],
            pins={str(f.relative_to(BASE)).replace('\\','/'):sha(f) for f in files},wrapper_sha256=sha(d/'source_path236.sv'))
        print(name+'\n'+summary)
    result['passed']=True;result['endpoint_only_difference_le']=result['projects']['old']['le']-result['projects']['new']['le']
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('Endpoint-only MAP difference:',result['endpoint_only_difference_le'])
if __name__=='__main__':main()
