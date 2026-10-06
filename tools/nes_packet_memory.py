# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from nes_h1_sampling import frontend,transport
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_packet_memory_producer']
 for name in files:shutil.copy2(ROOT/'src/nes'/(name+'.sv'),out/(name+'.sv'))
 (out/'nes_snes_frontend.sv').write_text(frontend(),newline='\n');(out/'nes_transport.sv').write_text(transport(),newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/packet_memory_tb.sv',out/'packet_memory_tb.sv')
 # Reconstruct each historical packet from the original NES reference fetch trace.
 # This is input provenance, not a new NES execution or a live encoder.
 from verify_nes_video_workloads import read_case
 from build_nes_chr_residency import encode,decode
 from build_nes_trace_replay import convert
 parts=[];inputs=[]
 for folder,case in [('top','banks32'),('fine_x','fine_x')]:
  workload=ROOT/'analysis/local-video-workloads-021';frames,bg,_,_,chrdata=read_case(workload,case)
  atlas=convert(chrdata).ljust(32768,bytes([0]))
  for i,info in enumerate(frames,1):
   source=ROOT/f'analysis/local-chr-residency-025/{folder}/build/packet-{i}.bin'
   packet=encode(i,[e for e in bg if e['frame']==info['frame']],info['features'],chrdata)
   assert packet==source.read_bytes()
   assert decode(packet,atlas)==source.with_name(f'expected-{i}.idx').read_bytes()
   inputs.append({'path':source.relative_to(ROOT).as_posix(),'sha256':sha(source),'bytes':len(packet),'source_frame':info['frame'],'release_tick':int.from_bytes(packet[12:16],'little'),'memory_offset':sum(map(len,parts))})
   parts.append(packet)
 data=b''.join(parts);assert len(data)==16064
 (out/'packets.hex').write_text(''.join(f'{b:02x}\n' for b in data.ljust(16384,b'\xff')),encoding='ascii')
 meta={'candidate':'NES-R2-MEMORY-PRODUCER-045','sources':{name+'.sv':sha(out/(name+'.sv')) for name in files},'testbench_sha256':sha(out/'packet_memory_tb.sv'),'inputs':inputs,'input_bytes':len(data),'runs':{},'passed':False,'scope':'Original memory reader + unchanged044 transport, synthetic variable-latency memory and pin transactions. Historical NES trace-derived packets; no live encoder, physical memory, SNES CPU/PPU execution, hardware image or timing signoff.'}
 def run(label,tool,args):
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert cp.returncode==0,label
 def save(): (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 save();run('vlib','vlib',['work']);run('compile','vlog',['-sv',*[n+'.sv' for n in files],'packet_memory_tb.sv'])
 for label,q,h,phase in [('q46_h12',23.280423,5.952381,1.1),('q20_h10',10,5,2.3),('q46_h20',23.280423,10,4.7)]:
  run(label,'vsim',['-c','packet_memory_tb',f'+QHALF={q}',f'+HHALF={h}',f'+HPHASE={phase}','-do','onerror {quit -code 1}; run -all; quit -f'])
  log=(out/(label+'.log')).read_text(errors='replace');m=re.search(r'PASS MEMORY PRODUCER checks=(\d+) bytes=(\d+)',log)
  if (out/'memory-trace.tsv').exists():shutil.copy2(out/'memory-trace.tsv',out/(label+'.tsv'))
  assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect '+label+'.log'
  checks,n=map(int,m.groups());assert (checks,n)==(17,19153),(checks,n)
  observed=bytes(int(s.split()[3]) for s in (out/(label+'.tsv')).read_text().splitlines() if s.startswith('B '))
  assert observed==data+data[2008:2016]+data[:8]+data[:3072]+b'\xff'
  meta['runs'][label]={'checks':checks,'bytes':n,'cases':re.findall('PASS CASE (.*)',log),'queue_period_ns':q*2,'host_period_ns':h*2,'host_phase_ns':phase,'exact_bytes_verified':True};save()
 meta['passed']=True;save();print(json.dumps(meta['runs'],indent=2))
if __name__=='__main__':main()
