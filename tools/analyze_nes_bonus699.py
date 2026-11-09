"""Bind minimal preview fix, real T65/arbiter proof, replay and whole Lite cost."""
from pathlib import Path
import argparse,difflib,hashlib,json,re,zipfile
from nes_game147 import ROOT,sha,ROM_SHA
from analyze_nes_status689 import cost
from analyze_nes_output664 import trace

def read(p):return json.loads(p.read_text(encoding='utf8'))

def main():
    p=argparse.ArgumentParser()
    for n in ('temp','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    b=a.temp/'nes-bonus699-board01';old=a.temp/'nes-longrun694-board01'
    m=read(b/'inputs699.json');private=[]
    for n,h in m['base'].items():
        assert sha(old/n)==h and sha(b/n)==m['changed'].get(n,h),n
        private.extend([(old/n,'baseline/'+n),(b/n,'candidate/'+n)])
    assert set(m['changed'])=={'rtl/nes.v','rtl/ppu.sv'}
    patches=''.join(''.join(difflib.unified_diff((old/n).read_text().splitlines(True),(b/n).read_text().splitlines(True),fromfile='694/'+n,tofile='699/'+n)) for n in sorted(m['changed']))
    (a.out/'production.patch').write_text(patches,encoding='utf8',newline='\n')
    private.extend([(a.out/'production.patch','production.patch'),(b/'inputs699.json','candidate/inputs699.json')])
    runs={}
    def sim(name,cpu=False,expected_fail=()):
        d=a.temp/name;meta=read(d/'inputs.json');r=read(d/'result.json');log=(d/'simulation.log').read_text()
        assert r['completed'] and r['returncode']==0 and not re.search(r'\*\* (Fatal|Error):',log),name
        assert '# Errors: 0,' in log and 'DONE698' in log
        for n,h in meta['sources'].items():
            assert sha(d/n)==h,(name,n)
            if n!='game147_tb.sv':assert sha(Path(meta['board'])/n)==h,(name,n)
        if cpu:
            pattern=r'CASE699CPU scenario=(\d+) failed=(\d+) error=(\d+) raw=(\d+) commit=(\d+) checked=(\d+) old=(\d+) new=(\d+) context=(\w+) ppu=(\w+)'
        else:pattern=r'CASE698 scenario=(\d+) failed=(\d+) error=(\d+) context=(\w+) ppu=(\w+) reads=(\d+) checked=(\d+)'
        rows=re.findall(pattern,log);assert len(rows)==8,name
        results=[]
        for row in rows:
            n,f,e=map(int,row[:3]);assert bool(f)==(n in expected_fail),(name,row)
            if f:
                assert e==2 and 'e200c3f7ce21fbe7' in row and '604198007f9f9f9c' in row,(name,row)
            else:assert e==0,(name,row)
            if cpu:
                raw,commit,checked,older,newer=map(int,row[3:8])
                assert commit==48+n%4 and commit-raw==9 and newer==1,(name,row)
                assert older==f and checked==1-f,(name,row)
                results.append(dict(case=n,failed=bool(f),error=e,raw=raw,commit=commit,independent_bytes=checked,old_requests=older,new_requests=newer))
            else:
                checked=int(row[-1]);assert checked==int(not f and '-stop-' not in name),(name,row)
                results.append(dict(case=n,failed=bool(f),error=e,independent_bytes=checked))
        fills=re.findall(r'FILL699 grants=(\d+) replies=(\d+)',log)
        if 'arb-final' in name:assert len(fills)==8 and all(int(g)>=1 and g==r for g,r in fills)
        stops=re.findall(r'STOP699 scenario=(\d+) step=(\d+) quiescent=1',log)
        if '-stop-' in name:assert len(stops)==8 and {int(s) for _,s in stops}=={47,49,51,53}
        for n in ['inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log']:
            private.append((d/n,name+'/'+n))
        runs[name]=dict(memory_phase_ns=meta['memory_phase_ns'],cases=results,fill_receipts=fills,mid_read_STOP=stops,log_sha256=sha(d/'simulation.log'))
    for phase in ('0','3.5','5.5'):
        sim(f'nes-bonus699-old-width-{phase}',expected_fail=range(2,7))
        sim(f'nes-bonus699-new-pulse-{phase}',expected_fail=range(3,6))
        sim(f'nes-bonus699-new-width-{phase}')
        sim(f'nes-bonus699-cpu-old-{phase}',cpu=True,expected_fail=range(8))
        sim(f'nes-bonus699-cpu-new-{phase}',cpu=True)
        sim(f'nes-bonus699-arb-final-{phase}',cpu=True)
        sim(f'nes-bonus699-stop-{phase}')
    guards={}
    for name in ('status01','plan01','bus01'):
        d=a.temp/f'nes-bonus699-{name}';r=read(d/'result.json');assert r['passed']
        guards[name]=dict(result=r,SHA256=sha(d/'result.json'))
        for n in d.iterdir():
            if n.is_file() and n.suffix in ('.json','.sv','.log','.hex'):private.append((n,d.name+'/'+n.name))
    c=cost(b);o=read(ROOT/'analysis/longrun694-verification.json')['boards']['694']
    assert c['SOF'] and c['STA'] and not c['LAB_error'] and min(c['slack_ns'].values())>0
    assert c['LE'][0]<=c['LE'][1] and c['LAB']<=963 and c['M9K'][0]<=56
    assert c['unconstrained']==o['unconstrained']
    for n in ('word660.tsv','reader661.tsv','io612.tsv'):
        assert c[n] and min(float(r['slack']) for r in c[n])>0,n
        private.append((b/n,'candidate/'+n))
    for n in ('report_nes_word660.tcl','reader661-report-executed699.tcl','report_nes_oe612.tcl'):
        private.append((b/n,'executed-reports/'+n))
    for n in (b/'output_files').iterdir():
        if n.is_file() and n.suffix in ('.sof','.rpt','.summary'):private.append((n,'candidate/output_files/'+n.name))
    schedules={}
    for phase in (1,2):
        d=a.temp/f'nes-bonus699-step{phase}';base=a.temp/f'nes-longrun694-step{phase}'
        r=read(d/'joint.json');prior=read(base/'joint.json');assert r['passed'] and r['commits']==53
        for k in ('frames','firmware_SHA256','client_SHA256','parameters','wire_B','ARM_instructions','ROM_read_allocations'):
            assert r[k]==prior[k],(phase,k)
        t=trace(d,a.temp/f'nes-front638-both{phase}h');ot=trace(base,a.temp/f'nes-front638-both{phase}h')
        for k in ('intervals','checked'):assert t[k]==ot[k],(phase,k)
        assert t['intervals'][952]['VBlank']==3 and t['intervals'][957]['final_waits']==0
        assert t['details'][951]['marks']['reveal']['line']<=246
        schedules[phase]=dict(frames=53,cycle_identical_to694=True,interval952=t['intervals'][952],final957=t['intervals'][957],
            dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
            firmware=r['firmware_SHA256'],client=r['client_SHA256'],physical_timing=False,full_ROM_RTL=False,
            proof=sha(d/'joint.json'))
        for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json'):
            private.append((d/n,d.name+'/'+n))
    inherited=read(ROOT/'analysis/longrun694-verification.json')
    report=dict(stage=699,selected='board01; unchanged694 ARM/client',rom_sha256=ROM_SHA,
        modification='Sprite ALE request uses existing raw-write physical preview; read/sample retains committed mapper physical tag. Only two RTL files; no new state, changed mapper commits, reader latency or clock.',
        inputs=m,runs=runs,guards=guards,boards={'694':o,'699':c},LE_delta=c['LE'][0]-o['LE'][0],
        LAB_delta=c['LAB']-o['LAB'],register_delta=c['FF'][0]-o['FF'][0],new_RAM_bits=c['RAM_bits'][0]-o['RAM_bits'][0],
        schedules=schedules,independent_CPU_24_pass=True,actual_arbiter_24_pass=True,mid_read_STOP_24_pass=True,
        original_pulse_sensitivity=dict(total=24,healthy=15,late_correct_faults=9,
          explanation='Three one-master-clock writes first appear AFTER the old request is accepted; unlike actual T65 raw-write lead9. Keep them rejected; no deadline masking.'),
        inherited_menu_base=dict(proof='analysis/longrun694-verification.json',SHA256=sha(ROOT/'analysis/longrun694-verification.json'),
          firmware=inherited['schedule']['firmware'],client=inherited['schedule']['CPU'],source_unchanged=True,
          boundary_hashes={n:v['SHA256'] for n,v in inherited['boundaries'].items()},new_hardware=False),
        Flash_B=inherited['Flash_B'],Flash_delta_B=0,ARM_RAM_delta_B=0,CPU_ROM_delta_B=0,
        functional_gate=True,FIT_STA_gate=True,schedule_model_no_regression=True,physical_tested=False,installer_created=False,
        limits=['T65 executes actual FB29..FB34 and F794 bytes; reset vector/RAM setup and PPU/OAM phase are fixtures, not full851s replay.',
                'Actual native arbiter gets continuous fill requests and real qualified VBlank grants; source/ARM packet producer is separate.',
                'Two-phase M4/65816 uses the unchanged recorded ROM calendar; it does not execute modified NES RTL concurrently. Boundary proof and scheduler proof are separate.',
                'Existing external IO constraints/signoff limitations remain. Recovery/removal margins slightly decrease but stay positive.',
                'No new physical STOP/menu/bonus-stage success claim. Package and real long play remain next gate.'])
    (ROOT/'analysis/bonus699-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    private.append((ROOT/'analysis/bonus699-verification.json','verification.json'))
    for n in ROOT.joinpath('tools').glob('*bonus699*.py'):private.append((n,'tools/'+n.name))
    for n in (ROOT.parent/'probes/nes-bonus699').iterdir():
        if n.is_file() and not n.name.endswith('.local.log') and not n.name.startswith('analysis') and n.suffix in ('.ps1','.log','.json'):private.append((n,'jobs/'+n.name))
    # Keep failed harness attempts without any license/server transcript.
    for folder in ('nes-bonus699-arb01','nes-bonus699-cpu-new01','nes-bonus699-arb02'):
        d=a.temp/folder
        for n in ('inputs.json','result.json','game147_tb.sv','vlog.log','simulation.log'):
            if (d/n).exists():private.append((d/n,'prior/'+folder+'/'+n))
    manifest={name:sha(src) for src,name in private};assert len(manifest)==len(private)
    with zipfile.ZipFile(a.out/'evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for src,name in private:z.write(src,name)
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(a.out/'evidence.zip') as z:
        for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    archive=dict(stage=699,path=str(a.out/'evidence.zip'),sha256=sha(a.out/'evidence.zip'),files=len(manifest),verified_all=True,
      private_ROM_not_in_Git=True,raw_game_ROM_not_in_archive=True)
    (ROOT/'analysis/bonus699-archive.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(passed=True,LE=c['LE'],slack_ns=c['slack_ns'],phases=schedules,archive=archive)))

if __name__=='__main__':main()
