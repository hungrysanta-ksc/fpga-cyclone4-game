"""Run an isolated, local-only MMC3 RTL contract test. SPDX-License-Identifier: MIT."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,difflib,hashlib,json,os,re,shutil,subprocess
from nes_functional import normalize,PIN

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,indent=2)+'\n',encoding='utf-8',newline='\n')
def audit(text):
    regs=[0]*8;select=0;mode=0;mirror=0;ram=0;errors=Counter();counts=Counter();tags=Counter();phases=defaultdict(set)
    for row in text.splitlines():
        v=row.split();kind=v[0];counts[kind]+=1
        if kind=='W':
            _,tick,a,d=v;a,d=int(a),int(d)
            if a==0x8000:select=d&7;mode=d
            elif a==0x8001:regs[select]=d
            elif a==0xa000:mirror=d&1
            elif a==0xa001:ram=d
        elif kind=='P':
            tick,a,writing,physical,allow=map(int,v[1:])
            expected_allow=(a>=0x8000 and not writing) or (0x6000<=a<0x8000 and (ram&128)!=0 and not (writing and ram&64))
            if bool(allow)!=bool(expected_allow):errors['prg_access']+=1
            if a>=0x8000:
                banks=[regs[6]&63,regs[7]&63,62,63]
                if mode&64:banks[0],banks[2]=banks[2],banks[0]
                expected=banks[(a-0x8000)//8192]*8192+(a&8191)
            elif expected_allow:expected=0x3c0000+(a&8191)
            else:expected=physical # Denied cycles have no memory transaction.
            if physical!=expected:errors['prg_mapping']+=1
        elif kind=='C':
            tick,a,physical,allow,a10,vram=map(int,v[1:])
            if allow!=0:errors['chr_rom_write']+=1
            if vram!=int(a>=0x2000):errors['ciram_select']+=1
            if a>=0x2000:
                if a10!=((a>>(11 if mirror else 10))&1):errors['mirroring']+=1
            else:
                banks=[regs[0]&254,regs[0]|1,regs[1]&254,regs[1]|1,*regs[2:6]]
                if mode&128:banks=banks[4:]+banks[:4]
                if physical!=0x200000+banks[a//1024]*1024+(a&1023):errors['chr_mapping']+=1
        elif kind=='I':
            tick,tag,actual,expected,counter=v[1:];tags[tag]+=1;phases[tag].add(int(tick)%12)
            if int(actual)!=int(expected):errors['irq']+=1
        else:raise ValueError('Unknown trace record '+kind)
    expected_tags=('reload_one held_high_no_reclock short_one_rejected short_two_rejected third_sample_accepted irq_latched enable_not_ack disable_ack disabled_no_irq reload_three count_two reload_deferred reload_midcount after_reload_two after_reload_one after_reload_zero zero_latch_irq zero_latch_repeats reset_clears_irq').split()
    if counts['W']!=8378 or counts['P']!=4112 or counts['C']!=8200 or counts['I']!=228:errors['coverage_count']+=1
    if tags!=Counter({tag:12 for tag in expected_tags}):errors['irq_coverage']+=1
    phase_tags=['reload_one','short_one_rejected','short_two_rejected','third_sample_accepted','after_reload_zero']
    for tag in phase_tags:
        if phases[tag]!=set(range(12)):errors['a12_phase_coverage']+=1
    return dict(passed=not errors,errors=dict(errors),counts=dict(counts),irq_cases=dict(tags),a12_master_phases={tag:sorted(phases[tag]) for tag in phase_tags})

def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--testbench',type=Path,required=True);a=p.parse_args()
    if not re.fullmatch(r'\d+@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER','')):p.error('Use the existing FLOAT wrapper; inherited uncounted licenses are not accepted.')
    u=a.upstream.resolve();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
    rev=subprocess.check_output(['git','-c','safe.directory='+u.as_posix(),'-C',str(u),'rev-parse','HEAD'],text=True).strip();assert rev==PIN
    paths=['rtl/mappers/MMC3.sv','rtl/regs_savestates.sv','rtl/bus_savestates.vhd','COPYING'];inventory=[]
    for name in paths:
        dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(u/name,dst);inventory.append(dict(path=name,sha256=sha(dst)))
    assert sha(u/paths[0])=='a85f0324d941c7cf0bf3022b2b94a63e82ba989f882156090585d0d7cac04165'
    original=(u/paths[0]).read_text();match=re.search(r'(?ms)^module MMC3\s*\(.*?^endmodule',original);assert match
    source=match[0];compiled='import regs_savestates::*;\n'+normalize(source)+'\n'
    (out/'mmc3_unit.sv').write_text(compiled,encoding='utf-8',newline='\n')
    (out/'simulation-only.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),compiled.splitlines(True),fromfile='upstream/MMC3-module',tofile='simulation/mmc3_unit.sv')),encoding='utf-8',newline='\n')
    shutil.copy2(a.testbench,out/'mmc3_tb.sv')
    result=dict(candidate='NES-P2-MMC3-UNIT-008',upstream_commit=rev,sources=inventory,runner_sha256=sha(__file__),normalizer_sha256=sha(Path(__file__).with_name('nes_functional.py')),testbench_sha256=sha(a.testbench),compiled_module_sha256=sha(out/'mmc3_unit.sv'),license_route='existing local FLOAT',license_status='MMC3.sv and savestate helpers remain hold-before-vendoring; repository COPYING retained, local experiment only',phases={})
    def run(exe,args,name):
        with (out/(name+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        result['phases'][name]=r.returncode;dump(out/'result.json',result)
        if r.returncode:raise SystemExit('Failed '+name+'; inspect raw log')
    run('vlib',['work'],'vlib');run('vcom',['-2008','rtl/bus_savestates.vhd'],'vcom')
    run('vlog',['-sv','-mfcu','rtl/regs_savestates.sv','mmc3_unit.sv','mmc3_tb.sv'],'vlog')
    (out/'run.do').write_text('onerror {quit -code 1}\nrun -all\nquit -f\n',encoding='ascii')
    run('vsim',['-c','mmc3_tb','-do','do run.do'],'simulation')
    log=(out/'simulation.log').read_text(errors='replace');trace=(out/'mapper-trace.txt').read_text()
    result['audit']=audit(trace);result['rtl_pass']='PASS MMC3 UNIT' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
    # Mutate actual records, then invoke the same full audit used for success.
    lines=trace.splitlines();neg={}
    for kind,field,label in [('P',4,'prg_address'),('P',5,'prg_permission'),('C',3,'chr_address'),('I',3,'irq_level')]:
        modified=lines.copy();idx=next(i for i,s in enumerate(lines) if s.startswith(kind+' '));v=modified[idx].split();v[field]=str(int(v[field])^1);modified[idx]=' '.join(v);neg[label+'_rejected']=not audit('\n'.join(modified))['passed']
    neg['truncated_trace_rejected']=not audit('\n'.join(lines[:-1]))['passed'];result['negative_tests']=neg
    result['passed']=result['rtl_pass'] and result['audit']['passed'] and all(neg.values());result['trace_sha256']=sha(out/'mapper-trace.txt')
    result['scope']='Standard Mapper4 submapper0 standalone RTL. Synthetic CE/M2/A12 bus stimuli; not CPU/PPU-integrated ROM execution, Mesen runtime comparison, all MMC3 revisions, cache, fit/STA, SMB3 or hardware.'
    dump(out/'result.json',result);print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
