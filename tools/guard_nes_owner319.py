# SPDX-License-Identifier: MIT
"""Fault injection in the actual M4/ROM/2-slot candidate, not a mock owner."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from nes_delta231 import ROOT,sha,once
from probe_nes_refill267 import run

CASES={1:'STOP source record in flight',2:'STOP NES plan RAM read',3:'STOP E1 partial ingress',
       4:'STOP E9 partial ingress',5:'premature final display ACK',6:'independent expected/receipt mismatch',
       7:'STOP during physical ROM request'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cases',default='1,2,3,4,5,6,7');a=ap.parse_args();selected=[int(x) for x in a.cases.split(',')]
    assert selected and len(set(selected))==len(selected) and all(x in CASES for x in selected)
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    ref=json.loads((a.reference/'result.json').read_text());assert ref['passed']
    for p in a.reference.iterdir():
        if p.is_file() and p.suffix in ('.sv','.v','.hex','.bin','.elf','.dll','.cfg','.palette','.expected'):
            shutil.copyfile(p,d/p.name)
    p=d/'joint266_tb.sv';s=once(p.read_text(),'module joint266_tb;', 'module joint266_tb;\n reg injected319=0;')
    s=once(s,'if(source_fault&&GUARD==0&&!NEG&&!PRENEG)', 'if(source_fault&&!injected319&&GUARD==0&&!NEG&&!PRENEG)')
    s=once(s,'if(romfault267)$fatal', 'if(romfault267&&!injected319)$fatal')
    s=once(s,'if((flow_fault||lease_fault)&&!NEG&&!PRENEG)', 'if((flow_fault||lease_fault)&&!injected319&&!NEG&&!PRENEG)')
    s=once(s,'endmodule', '''
 parameter integer NEG319=0;
 initial begin : guards319
  reg [7:0] frozen319[0:1023];reg [7:0] queue319[0:1023];
  if(NEG319==1)wait(dut.core.encoder.state==dut.core.encoder.SBYTE&&dut.core.encoder.rec_i==3);
  else if(NEG319==2)wait(planrom.transport.state==planrom.transport.READ);
  else if(NEG319==3)wait(spi_front270.command==8'he1&&spi_front270.count==10);
  else if(NEG319==4)wait(spi_front270.command==8'he9&&spi_front270.count==7);
  else if(NEG319==5)wait(dut.flow.state==dut.flow.DMA&&dut.flow.data_command278);
  else if(NEG319==6)wait(dut.flow.state==dut.flow.MISSUE313&&dut.flow.header[0]==3&&dut.flow.manifest_byte313==190);
  else if(NEG319==7)wait(planrom.source.cache_path.cache.pending);
  else $fatal(1,"unknown guard319");
  @(negedge host_clk);injected319=1;
  if(NEG319<=4||NEG319==7)begin disable bus263;bus_read=1;bus_write=1;test_abort=1;end
  else if(NEG319==5)begin disable bus263;bus_read=1;bus_write=1;token261(dut.flow.chunk_token);wr261(24'h006058,8'h5a);end
  else force dut.flow.held=0;
  fork
   begin wait(source_fault);end
   begin #100000;$fatal(1,"missing expected fault319");end
  join_any
  disable fork;
  repeat(8)@(negedge host_clk);
  for(integer j=0;j<1024;j++)begin frozen319[j]=dut.core.memory[j];queue319[j]=dut.flow.queue.buffer[j];end
  repeat(256)@(negedge host_clk);
  for(integer j=0;j<1024;j++)begin
   if(frozen319[j]!==dut.core.memory[j]||queue319[j]!==dut.flow.queue.buffer[j])$fatal(1,"post-fault write319");
  end
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"completion after fault319");
  if(NEG319==7&&!planrom.drained)$fatal(1,"ROM not drained319");
  $display("PASS OWNER319 GUARD=%0d fault=%0d",NEG319,source_fault);$finish;
 end
endmodule''');p.write_text(s,newline='\n')
    q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    run(q/'vlib.exe',['work'],d,'vlib')
    run(q/'vlog.exe',['-sv',*ref['rtl_hashes'],'joint266_tb.sv'],d,'vlog')
    results=[]
    for case in selected:
        label=CASES[case]
        # Each run has a fresh rendezvous directory and independent ARM state.
        target=d/f'case{case}';target.mkdir()
        shutil.copytree(d/'work',target/'work')
        for f in d.iterdir():
            if f.is_file():shutil.copyfile(f,target/f.name)
        with (target/'arm-worker.log').open('wb') as log:
            worker=subprocess.Popen([sys.executable,str(ROOT/'tools/probe_nes_owner319.py'),'--worker','--out',str(target),'--last','905','--irq','--plans',str(target)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                raw=run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'-gNEG319={case}','-gROM_WINDOW=1','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],target,'vsim',600)
                assert f'PASS OWNER319 GUARD={case}' in raw
                results.append(dict(case=case,label=label,passed=True,log_sha256=sha(target/'vsim.log')))
            finally:
                if worker.poll() is None:worker.kill();worker.wait()
    actual={n:sha(d/n) for n in ref['rtl_hashes']};assert actual==ref['rtl_hashes']
    result=dict(passed=True,cases=results,rtl_hashes=actual,tb_sha256=sha(p),ELF_sha256=sha(d/'output.elf'))
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
