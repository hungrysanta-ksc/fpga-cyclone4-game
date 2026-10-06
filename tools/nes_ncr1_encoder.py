# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,hashlib,os,re,shutil,subprocess
from nes_h1_sampling import frontend,transport
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_packet_memory_producer','nes_ncr1_encoder']
 for n in files:shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
 (out/'nes_snes_frontend.sv').write_text(frontend(),newline='\n');(out/'nes_transport.sv').write_text(transport(),newline='\n')
 from verify_nes_video_workloads import read_case
 from build_nes_chr_residency import encode,decode
 from build_nes_trace_replay import palette,convert
 packets=[];events=[];inputs=[]
 for folder,case in [('top','banks32'),('fine_x','fine_x')]:
  root=ROOT/'analysis/local-video-workloads-021';frames,bg,_,_,chrdata=read_case(root,case)
  for f,info in enumerate(frames,1):
   features=info['features'];assert features['ppu_mask']==10 and features['ppu_ctrl']==136 and not features['active_ppu_writes'] and features['scroll_y']==0 and features['scroll_x']==(case=='fine_x')
   seq=[e for e in bg if e['frame']==info['frame']];assert len(seq)==16388
   packet=encode(f,seq,features,chrdata);old=ROOT/f'analysis/local-chr-residency-025/{folder}/build/packet-{f}.bin'
   assert packet==old.read_bytes() and decode(packet,convert(chrdata).ljust(32768,b'\0'))==old.with_name(f'expected-{f}.idx').read_bytes()
   inputs.append({'packet':old.relative_to(ROOT).as_posix(),'packet_sha256':sha(old),'trace':str((root/case/'capture/trace.tsv').relative_to(ROOT)),'trace_sha256':sha(root/case/'capture/trace.tsv'),'source_frame':info['frame'],'events':len(seq),'first_tick':seq[0]['tick'],'last_tick':seq[-1]['tick'],'release_tick':int.from_bytes(packet[12:16],'little')})
   packets.append(packet)
   for e in seq:events.append((e['tick']<<35)|((e['line']&511)<<26)|(e['dot']<<17)|(e['offset']<<2))
 (out/'events.hex').write_text(''.join(f'{e:020x}\n' for e in events),encoding='ascii')
 data=b''.join(packets);(out/'golden.hex').write_text(''.join(f'{b:02x}\n' for b in data.ljust(16384,b'\xff')),encoding='ascii')
 tb=(ROOT/'tests/nes-functional/ncr1_encoder_tb.sv').read_text().replace('@PALETTE@',f'{int.from_bytes(palette(),"little"):016x}')
 (out/'ncr1_encoder_tb.sv').write_text(tb,newline='\n')
 meta={'candidate':'NES-R2-NCR1-ENCODER-046','sources':{n+'.sv':sha(out/(n+'.sv')) for n in files},'testbench_sha256':sha(out/'ncr1_encoder_tb.sv'),'inputs':inputs,'event_count':len(events),'passed':False,'scope':'Streaming RTL from chronological historical NES BG fetches with actual tick gaps through045 and044. Not a new NES core execution, physical memory/board validation, general game renderer or display-policy approval.'}
 def save():(out/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 save()
 for name,tool,args in [('vlib','vlib',['work']),('compile','vlog',['-sv',*[n+'.sv' for n in files],'ncr1_encoder_tb.sv']),('run','vsim',['-c','ncr1_encoder_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(name+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  assert cp.returncode==0,name
 log=(out/'run.log').read_text(errors='replace');m=re.search(r'PASS NCR1 ENCODER checks=(\d+) bytes=(\d+)',log)
 assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect run.log'
 n,bytes_read=map(int,m.groups());assert (n,bytes_read)==(16,18072),(n,bytes_read)
 observed=bytes(int(v.split()[3]) for v in (out/'encoder-trace.tsv').read_text().splitlines() if v.startswith('B '));assert observed==data+data[:2008]
 meta.update(passed=True,cases=re.findall('PASS CASE (.*)',log),checks=n,exact_bus_bytes=bytes_read);save();print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
