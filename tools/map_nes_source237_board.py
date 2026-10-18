# SPDX-License-Identifier: MIT
"""Actual-board resource gate, replacing the complete old source boundary.

One MAP and optional single FIT. No STA or production runtime/CDC approval.
MAP estimated LE alone is not physical packing: old18850 MAP became15249 FIT.
Stop at the resource gate; do not run seed loops or relax clocks.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha

GLUE='''// Source237 resource candidate: source base has its own serial; the
// exported capture lease still survives until the existing final retire.
wire source_start_ready237;
reg source_started237;reg [31:0] source_serial237;
always @(posedge clk)begin
 if(reset)begin source_started237<=0;source_serial237<=1;end
 else begin
  if(!export_permitted204)source_started237<=0;
  else if(source_start_ready237&&!source_started237)source_started237<=1;
  if(export_release204)source_serial237<=source_serial237+1'b1;
 end
end
nes_source237 native_source237(.clk(clk),.host_clk(host_clk),.reset(reset),
 .abort_source(direct_nes_fault204),
 .start(export_permitted204&&!direct_nes_fault204&&!source_started237),.start_ready(source_start_ready237),
 .frame_owned(native_frame_owned),.geometry_valid(native_geometry_valid&&!rom_fault),.frame_generation(native_generation),
 .content_epoch(captured_epoch204),.frame_serial(source_serial237),.patch_count(native_patch_count181),
 .row_count(native_row_count),.object_count(native_object_count),.exception_count(native_exception_count),
 .group_count(native_group_count),.palette_count(native_palette_count),
 .query(native_query),.query_kind(native_query_kind),.query_index(native_query_index),.query_generation(native_query_generation),
 .response(native_response),.hit(native_hit),.data(native_data),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
 .selected(native_spi_selected),.miso(native_spi_miso),.done(export_release204),.fault(native_export_error));
assign native_spi_fault=|native_export_error;
'''

def main():
    p=argparse.ArgumentParser()
    for n in ('out','joint','guards'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--fit',action='store_true')
    p.add_argument('--retire-source-sdc',action='store_true')
    a=p.parse_args();out=a.out.resolve();assert str(out).isascii() and not out.exists()
    joint=json.loads((a.joint/'result.json').read_text());guards=json.loads((a.guards/'result.json').read_text())
    assert joint['passed'] and joint['frames']==71 and joint['exact_c_files']==355 and guards['passed']
    for k,h in guards['pins'].items():assert sha(ROOT/k)==h
    for n in ('nes_source_encoder237','nes_source237'):
        f=ROOT/'src/nes/rtl'/(n+'.sv');assert sha(f)==joint['source_pins'][str(f.relative_to(BASE)).replace('\\','/')]
    board=BASE/'probes/nes-counter224/mapfit02';out.mkdir(parents=True);pins={}
    for f in board.rglob('*'):
        rel=f.relative_to(board)
        if any(x in ('db','incremental_db','output_files') for x in rel.parts):continue
        if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);pins[str(f.relative_to(BASE)).replace('\\','/')]=sha(f)
    f=out/'nes_live_joint.sv';s=f.read_text();begin=s.index('wire [3:0] native_export_state177;');end=s.index('wire spi_collision204=',begin)
    s=s[:begin]+GLUE+'\n'+s[end:];begin=s.index('wire native_spi_reset;');s=s[:begin]+'endmodule\n';f.write_text(s,newline='\n')
    qsf=(out/'board.qsf').read_text()
    qsf='\n'.join(l for l in qsf.splitlines() if not ('DONT_MERGE_REGISTER' in l and ('native_records|' in l or 'native_prepared|' in l)))+'\n'
    for n in ('nes_source_query235','nes_source_spi235','nes_source_encoder237','nes_source237'):
        f=ROOT/'src/nes/rtl'/(n+'.sv');shutil.copyfile(f,out/f.name);pins[str(f.relative_to(BASE)).replace('\\','/')]=sha(f)
        qsf+='set_global_assignment -name SYSTEMVERILOG_FILE '+f.name+'\n'
    (out/'board.qsf').write_text(qsf,newline='\n')
    removed=[]
    if a.retire_source_sdc:
        cdc=out/'cdc181.sdc';lines=cdc.read_text().splitlines()
        retired=('nes_native_mailbox165:native_records|','nes_native_mailbox165:native_prepared|',
            'nes_native_spi165:native_spi|','nes_domain_reset124:native_spi_release|','nes_native_export203:native_export|')
        removed=[l for l in lines if any(n in l for n in retired)]
        assert len(removed)==216 and all(l.startswith('set_') for l in removed)
        # Only constraints touching the physically removed source instances.
        # No new false paths, larger bounds or blanket clock-group exceptions.
        cdc.write_text('\n'.join(l for l in lines if l not in removed)+'\n',newline='\n')
    with (out/'map237.log').open('wb') as log:
        cp=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    report=(out/'output_files/board.map.rpt').read_text(encoding='latin-1') if (out/'output_files/board.map.rpt').exists() else ''
    log=(out/'map237.log').read_text(encoding='latin-1')
    summary=(out/'output_files/board.map.summary').read_text(encoding='latin-1') if (out/'output_files/board.map.summary').exists() else ''
    def number(label):
        m=re.search(label+r'\s*:\s*([\d,]+)',summary);return int(m[1].replace(',','')) if m else None
    result=dict(scope=__doc__,map_returncode=cp.returncode,map_completed=cp.returncode==0,summary=summary,
        le=number('Total logic elements'),ff=number('Total registers'),memory_bits=number('Total memory bits'),
        combinational=number('Total combinational functions'),baseline_map_le=18850,baseline_map_combinational=13951,baseline_fit_le=15249,
        ram_rows=[l.strip() for l in report.splitlines() if '; M9K ' in l],
        source_rows=[l.strip() for l in report.splitlines() if 'native_source237' in l and ';' in l],
        warnings=[l.strip() for l in log.splitlines() if 'Warning' in l or 'Error' in l],
        source_pins=pins,wrapper_sha256=sha(out/'nes_live_joint.sv'),qsf_sha256=sha(out/'board.qsf'),
        retired_sdc_rows=removed,cdc_sha256=sha(out/'cdc181.sdc'),
        joint_result_sha256=sha(a.joint/'result.json'),guards_result_sha256=sha(a.guards/'result.json'),
        new_fit=False,new_sta=False,production_glue_approved=False,physical=False)
    result['resource_capacity_pass']=False
    if a.fit and cp.returncode==0:
        with (out/'fit237.log').open('wb') as log_file:
            fit=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_fit.exe','board'],cwd=out,stdout=log_file,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
        fs=(out/'output_files/board.fit.summary').read_text(encoding='latin-1') if (out/'output_files/board.fit.summary').exists() else ''
        fl=(out/'fit237.log').read_text(encoding='latin-1')
        result.update(new_fit=True,fit_returncode=fit.returncode,fit_summary=fs,
            fit_messages=[l.strip() for l in fl.splitlines() if 'Error' in l or 'Warning' in l],resource_capacity_pass=fit.returncode==0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(summary or log[-4000:]);print(json.dumps({k:result[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits')}))
if __name__=='__main__':main()
