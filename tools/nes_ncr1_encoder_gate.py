# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,hashlib,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin','rtl-run','netlist'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();assert str(out).isascii() and not out.exists()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''));out.mkdir()
 names=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_packet_memory_producer']
 for n in names:shutil.copy2(a.rtl_run/(n+'.sv'),out/(n+'.sv'))
 for n in ('events.hex','golden.hex'):shutil.copy2(a.rtl_run/n,out/n)
 shutil.copy2(a.netlist,out/'encoder.vo');assert '$sdf_annotate' not in (out/'encoder.vo').read_text()
 s=(a.rtl_run/'ncr1_encoder_tb.sv').read_text();prefix=s.split(' initial begin\n  fd=',1)[0]
 initial=''' initial begin
  fd=$fopen("encoder-trace.tsv","w");$readmemh("events.hex",events);$readmemh("golden.hex",golden);
  for(integer k=0;k<3;k++)begin
   automatic integer f=k==2?4:k;
   restart();
   fork stream_frame(f,0);begin while(published!=1 && !encoder_fault)@(negedge queue_clk);consume(1,f*2008,2008);end join
   if(encoder_fault || producer_fault)$fatal(1,"mapped pipeline fault");
   pass("mapped_header_tiles_palette_exact");
  end
  if(bytes_read!=6024)$fatal(1,"mapped byte count");
  $display("PASS MAPPED NCR1 checks=%0d bytes=%0d",checks,bytes_read);$fclose(fd);$finish;
 end
 initial begin #20000000;$fatal(1,"mapped watchdog");end
endmodule
'''
 (out/'mapped_tb.sv').write_text(prefix+initial,newline='\n')
 lib=a.questa_bin.parent/'intel/verilog/cycloneive'
 for label,tool,args in [('vlib','vlib',['work']),('compile','vlog',['-sv',*[n+'.sv' for n in names],'encoder.vo','mapped_tb.sv']),('gate','vsim',['-c','-t','1ps','-L',str(lib),'-L',str(lib.parent/'altera'),'ncr1_encoder_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  assert cp.returncode==0,label
 log=(out/'gate.log').read_text(errors='replace');assert 'PASS MAPPED NCR1 checks=3 bytes=6024' in log and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect gate.log'
 data=bytes(int(v,16) for v in (out/'golden.hex').read_text().split())
 actual=bytes(int(v.split()[3]) for v in (out/'encoder-trace.tsv').read_text().splitlines() if v.startswith('B '));assert actual==data[:4016]+data[8032:10040]
 result={'candidate':'NES-R2-NCR1-ENCODER-046','passed':True,'cases':3,'exact_bus_bytes':6024,'netlist_sha256':sha(out/'encoder.vo'),'scope':'Functional netlist exported from final fitted encoder;045/044 behavioral RTL. Three compressed-arrival frames, including window0/1 and fineX1. No SDF, external IO timing, physical memory or live NES core proof.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
