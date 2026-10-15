# SPDX-License-Identifier: MIT
"""Actual service/arbiter/fill/reader join, bounded 70ns pin-model schedules."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess
from nes_reply181 import BASELINE, transform

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']: p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    root=Path(__file__).resolve().parents[1]
    assert sha(a.baseline/'nes_rom_physical.sv')==BASELINE
    old=(a.baseline/'nes_rom_physical.sv').read_text()
    new=(a.prepared/'nes_rom_physical.sv').read_text();assert new==transform(old)
    a.out.mkdir(exist_ok=False)
    names=['nes_rom_service.sv','nes_native_arbiter165.sv','nes_native_fill165.sv']
    for n in names:shutil.copyfile(a.baseline/n,a.out/n)
    for n in ['rom_physical_model.sv','reply181_join_tb.sv']:
        shutil.copyfile(root/'tests/nes-functional'/n,a.out/n);names.append(n)
    def run(exe,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=(a.out/(label+'.log')).read_text(errors='replace')
        if not negative:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),(label,s[-2500:])
        return s
    run('vlib',['work'],'vlib')
    delayed=new.replace(' (* preserve *) reg [7:0] reply_data;', ' wire [7:0] delayed_reply;\n assign #9.904 delayed_reply=data_hold;\n (* preserve *) reg [7:0] reply_data;').replace('else reply_data<=data_hold;','else reply_data<=delayed_reply;')
    wrong=new.replace('else reply_data<=data_hold;','else if(rom_response)reply_data<=data_hold;')
    results={}
    for label,source,negative in [('baseline',old,False),('candidate',new,False),('delay9',delayed,False),('wrong_capture',wrong,True)]:
        (a.out/(label+'.sv')).write_text('`timescale 1ns/1ps\n'+source,encoding='utf8')
        run('vlog',['-sv',label+'.sv',*names],label+'-compile')
        s=run('vsim',['-c','work.reply181_join_tb','-do','onerror {quit -code 1}; run -all; quit -f'],label,negative)
        if negative:
            assert '** Fatal:' in s and 'qualified byte' in s and 'PASS REPLYJOIN181' not in s
            results[label]={'rejected':True}
        else:
            rows=sorted(re.findall(r'PASS REPLYJOIN181 phase=[^\r\n]+',s));assert len(rows)==16 and 'PASS REPLYJOIN181 all16' in s
            results[label]=rows
            if label!='baseline':assert rows==results['baseline'],label
        print(label+' PASS',flush=True)
    result=dict(passed=True,runs=results,candidate_sha256=sha(a.prepared/'nes_rom_physical.sv'),
        executed_sources={p.name:sha(p) for p in a.out.glob('*.sv')},runner_sha256=sha(Path(__file__)),
        scope='Actual ROM service + arbiter + FIFO fill + READ16 reader. CPU/PPU and slots are modeled; address-dependent 70ns PSRAM model, 16 clock phases, exact transcript equivalence. No whole core/game, metastability, physical fit or FPS approval.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
