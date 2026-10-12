# SPDX-License-Identifier: MIT
"""Actual serial RTL transactions -> compiled bounded C receiver, no new boot."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha,VHDL,SV,EXTRA
from nes_native_spi165 import prepare,FILES

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','records','out','questa-bin','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 baseline=json.loads((ROOT/'analysis/native-host165-verification.json').read_bytes())
 assert sha(a.records)==baseline['transport_cases'][0]['stream_sha256']
 # The caller supplies the already-pinned normal host stream, not a fresh ROM run.
 expected=''.join(x+'\n' for x in a.records.read_text().splitlines() if int(x,16)>>93!=7)
 records=a.records.read_text().splitlines();assert len(records)==1717
 shutil.copy2(a.records,a.out/'records.hex')
 tb='tests/nes-functional/native_spi165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 def run(exe,args,label,timeout=180):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 def q(exe,args,label):return run(a.questa_bin/(exe+'.exe'),args,label)
 q('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):q('vcom',['-2008',n],f'vcom-{i}')
 q('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*FILES,'nes_native_ciram165.sv',Path(tb).name],'vlog')
 fw=ROOT/'src/nes/firmware';host=ROOT/'tests/nes-functional/native_receiver165_host.c'
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,host,fw/'nes_native165.c','-o','receiver.exe'],'gcc')
 cases=[]
 for phase in [0,3.5]:
  tag='phase'+str(phase);s=q('vsim',['-c','work.native_spi165_tb',f'-gPHASE={phase}',f'+COUNT={len(records)}','-do','onerror {quit -code 1}; run -all; quit -f'],tag)
  m=re.search(r'PASS SPI165 records=(\d+) blocks=(\d+) wirebytes=(\d+)',s);assert m
  shutil.copy2(a.out/'transactions.txt',a.out/(tag+'.transactions.txt'))
  c=run(a.out/'receiver.exe',['transactions.txt','decoded.hex'],tag+'-receiver')
  assert (a.out/'decoded.hex').read_text()==expected
  cases.append(dict(phase_ns=phase,records=int(m[1]),blocks=int(m[2]),wire_bytes=int(m[3]),c_result=c.strip(),decoded_sha256=sha(a.out/'decoded.hex')))
 # Variable-length engine preserves the original guard/ownership logic exactly.
 original=(ROOT/'tests/nes-functional/game149_spi_host.c').read_text()
 s=original.replace('nes_game149_spi.inc','nes_native165_bulk.inc').replace('sent[8],received[8]','sent[259],received[259]').replace('writes<8','writes<259')
 s=s[:s.index('int main(void)')]+'''int main(void){
 uint8_t tx[259],rx[259];for(unsigned i=0;i<259;i++)tx[i]=(uint8_t)i;
 unsigned sizes[]={1,8,259},cases=0;
 for(unsigned n=0;n<3;n++){
  reset149();assert(nes_native165_bulk(&io,tx,rx,sizes[n]));stopped();
  assert(writes==sizes[n]&&reads==sizes[n]&&memcmp(tx,sent,sizes[n])==0&&memcmp(rx,received,sizes[n])==0);
  unsigned checks=guard_checks;cases++;
  for(unsigned c=1;c<=checks;c++){reset149();inject_check=c;assert(!nes_native165_bulk(&io,tx,rx,sizes[n]));assert(failed);stopped();cases++;}
 }
 for(unsigned b=1;b<=259;b++){reset149();error_byte=b;injected_error=SPI_SR_OVR;assert(!nes_native165_bulk(&io,tx,rx,259));assert(failed&&writes==b);stopped();cases++;}
 for(int mode=1;mode<=3;mode++){reset149();stuck=mode;if(mode==1)spi.SR=0;assert(!nes_native165_bulk(&io,tx,rx,259));assert(failed&&polls<259*6+600);stopped();cases++;}
 reset149();assert(!nes_native165_bulk(&io,tx,rx,0)&&!writes);assert(!nes_native165_bulk(&io,tx,rx,260)&&!writes);
 printf("PASS BULK165 cases=%u maxbytes=259\\n",cases);return 0;
}
'''
 (a.out/'bulk_host.c').write_text(s)
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,'bulk_host.c','-o','bulk.exe'],'gcc-bulk')
 bulk=run(a.out/'bulk.exe',[],'bulk')
 sources=['tools/nes_native_spi165.py','tools/test_nes_native_spi165.py',tb,'tests/nes-functional/native_receiver165_host.c','src/nes/firmware/nes_native165.c','src/nes/firmware/nes_native165.h']+['src/nes/diagnostic/'+n for n in FILES]
 result=dict(passed=True,cases=cases,bulk=bulk.strip(),inputs=inputs,record_input_sha256=sha(a.records),public_sources={n:sha(ROOT/n) for n in sources},generated_joint_sha256=sha(a.out/'nes_live_joint.sv'),bulk_engine_sha256=sha(a.out/'nes_native165_bulk.inc'),scope='Serial RTL + captured-transaction replay by actual C receiver. Register-model bulk driver. Parent joint compile only; no MCU-board/SNES runtime, fit or package.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS native SPI/C receiver/bulk')
if __name__=='__main__':main()
