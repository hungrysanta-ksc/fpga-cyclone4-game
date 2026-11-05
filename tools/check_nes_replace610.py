"""Replace the selected source cache and compare identical source-region ports."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from check_nes_wire600 import ROOT, pin, read, sha
from nes_raw506 import once

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    manifest=read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs']
    for name in ('nes_source_tile192.sv','nes_tile205.sv','nes_native_arbiter165.sv','nes_chr_cache192.sv'):
        pin(a.board/name,manifest[name]['sha256']);shutil.copy(a.board/name,a.out)
    source=a.out/'nes_source_tile192.sv'
    s=source.read_text()
    s=once(s,' input wire clk,reset,stop,frame_owned,geometry_valid,',''' input wire cap_start,cap_seal,cap_release,cap_sample,
 input wire [15:0] cap_generation,cap_release_generation,
 input wire [16:0] cap_address,input wire [7:0] cap_data,
 output wire cap_ready,cap_sample_ready,
 input wire clk,reset,stop,frame_owned,geometry_valid,''')
    if a.variant=='reference':
        s=once(s,' wire immutable='," assign cap_ready=1'b0;assign cap_sample_ready=1'b0;\n wire immutable=")
    else:
        old='nes_chr_cache192 cache(.clk(clk),.reset(reset),.flush(tile_cancel||denied||!immutable),.content_epoch(live_epoch),'
        s=once(s,old,'''nes_chr_cache610 cache(.clk(clk),.reset(reset),.stop(tile_cancel||denied),.immutable(immutable),
   .start(cap_start),.seal(cap_seal),.release_bank(cap_release),
   .capture_gen(cap_generation),.release_gen(cap_release_generation),
   .sample(cap_sample),.sample_address(cap_address),.sample_data(cap_data),
   .start_ready(cap_ready),.sample_ready(cap_sample_ready),.request_obj(out_kind==1),''')
        for name in ('nes_chr_cache610.sv','nes_obj_capture609.sv'):shutil.copy(ROOT/'rtl'/name,a.out)
    source.write_text(s)
    files=['nes_source_tile192.sv','nes_tile205.sv','nes_native_arbiter165.sv']
    files+=['nes_chr_cache192.sv'] if a.variant=='reference' else ['nes_chr_cache610.sv','nes_obj_capture609.sv']
    (a.out/'inputs.json').write_text(json.dumps({n:sha(a.out/n) for n in files},indent=2)+'\n')
    return files

def run(a):
    files=prepare(a)
    def execute(args,name):
        with (a.out/(name+'.log')).open('wb') as log:
            subprocess.run(args,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
    if a.mode=='map':
        (a.out/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
        qsf='set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY nes_source_tile192\n'
        qsf+='set_parameter -name EXTERNAL_PLAN 1\n'
        qsf+=''.join('set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n' for n in files)
        (a.out/'region.qsf').write_text(qsf)
        execute([a.bin/'quartus_map.exe','region'],'map')
        summary=(a.out/'region.map.summary').read_text()
        assert 'Successful' in summary and 'Lite Edition' in summary
        result={key:int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
                for key,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                                  ('FF','Dedicated logic registers'),('bits','Total memory bits')]}
        result['report']=sha(a.out/'region.map.rpt')
    else:
        tb=ROOT/'tools/nes_source_replace610_tb.sv'
        shutil.copy(tb,a.out)
        execute([a.bin/'vlib.exe','work'],'lib')
        execute([a.bin/'vlog.exe','-sv',*files,tb.name],'compile')
        execute([a.bin/'vsim.exe','-c','nes_source_replace610_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'],'sim')
        assert 'PASS610' in (a.out/'sim.log').read_text()
        result=dict(testbench=sha(tb),log=sha(a.out/'sim.log'))
    result.update(variant=a.variant,inputs=read(a.out/'inputs.json'))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['map','sim'])
    p.add_argument('--variant',choices=['reference','replace'],required=True)
    for n in ('board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
