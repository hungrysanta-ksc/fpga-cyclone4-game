# Original packet transport RTL execution. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
CANDIDATE='NES-R2-HOST-STAGE-029'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();repo=Path(__file__).resolve().parents[1]
    assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER','')),'Use authorized FLOAT wrapper'
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    sources=['src/nes/nes_packet_queue.sv','src/nes/nes_packet_cdc.sv','src/nes/nes_host_stage.sv','tests/nes-functional/host_stage_tb.sv']
    inputs={'split':'local-bank-patch-024','sprite':'local-sprite-replay-023','resident':'local-chr-residency-025'}
    meta=dict(candidate=CANDIDATE,scope='Host-clock full-packet staging connected to028 CDC;normalized strobes,not physicalSNESbus',
              sources={s:sha(repo/s) for s in sources},driver_sha256=sha(__file__),inputs={},phases={})
    for s in sources:shutil.copyfile(repo/s,out/Path(s).name)
    for name,folder in inputs.items():
        source=repo/'analysis'/folder/'top/build/packet-1.bin';data=source.read_bytes()
        (out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data),encoding='ascii')
        meta['inputs'][name]=dict(path=source.relative_to(repo).as_posix(),bytes=len(data),sha256=sha(source))
    def run(tool,args,label):
        with (out/(label+'.log')).open('wb') as log:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=90)
        meta['phases'][label]=r.returncode
        (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        assert r.returncode==0,'Inspect '+str(out/(label+'.log'))
    run('vlib',['work'],'vlib')
    run('vlog',['-sv','nes_packet_queue.sv','nes_packet_cdc.sv','nes_host_stage.sv','host_stage_tb.sv'],'compile')
    meta['runs']={}
    for label,q,h,phase in [('q10_h14',5,7,3),('q14_h10',7,5,1),('q10_h22',5,11,9)]:
        run('vsim',['-c','host_stage_tb',f'+QHALF={q}',f'+HHALF={h}',f'+HPHASE={phase}',
                    f'+TRACE={label}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],label)
        text=(out/(label+'.log')).read_text(errors='replace')
        match=re.search(r'PASS NES HOST STAGE checks=(\d+) readbytes=(\d+)',text)
        passed=bool(match) and not re.search(r'\*\* (?:Fatal|Error):',text)
        entry=dict(passed=passed,queue_period_ns=q*2,host_period_ns=h*2,host_phase_ns=phase,
                   cases=re.findall(r'PASS CASE ([a-z0-9_]+)',text))
        if match:entry['metrics']=dict(zip(('checks','readbytes'),map(int,match.groups())))
        meta['runs'][label]=entry
        (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        assert passed and len(entry['cases'])==10,'Missing clean10-case staging pass: '+label
    meta['passed']=all(e['passed'] for e in meta['runs'].values())
    meta['output_hashes']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('result.json','transcript')}
    (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=CANDIDATE,passed=meta['passed'],runs=meta['runs']),indent=2))
if __name__=='__main__':main()
