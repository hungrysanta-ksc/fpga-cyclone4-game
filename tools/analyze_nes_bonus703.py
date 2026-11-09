"""Bind exact701 reproduction, continuous sprite/CPU checks, whole cost and display model."""
import argparse,difflib,json,re,zipfile
from pathlib import Path
from nes_game147 import ROOT,sha
from analyze_nes_status689 import cost
from analyze_nes_output664 import trace

def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);private={};runs={}
    def add(p,n):private[n]=p
    baseline=a.temp/'nes-bonus699-board01';selected=a.temp/'nes-bonus703-board02'
    meta=read(selected/'inputs703.json')
    for n,h in meta['base'].items():
        assert sha(baseline/n)==h and sha(selected/n)==meta['changed'].get(n,h),n
        add(baseline/n,'699/'+n);add(selected/n,'703B/'+n)
    assert set(meta['changed'])=={'rtl/nes.v','rtl/ppu.sv'}
    patches=''.join(''.join(difflib.unified_diff((baseline/n).read_text().splitlines(True),(selected/n).read_text().splitlines(True),fromfile='699/'+n,tofile='703B/'+n)) for n in sorted(meta['changed']))
    (a.out/'production.patch').write_text(patches,encoding='utf8',newline='\n');add(a.out/'production.patch','production.patch')
    for mode in ('old','new','b','bstop'):
        allrows=[];tests=[]
        for i in range(2,5):
            d=a.temp/f'nes-bonus703-{mode}0{i}';m=read(d/'inputs.json');log=(d/'simulation.log').read_text();rows=[]
            assert 'DONE698 actual T65' in log and '# Errors: 0,' in log
            for n,h in m['sources'].items():
                assert sha(d/n)==h,(d,n)
                if n!='game147_tb.sv':assert sha(Path(m['board'])/n)==h,(d,n)
            for s in re.findall(r'CASE699CPU ([^\r\n]+)',log):
                kv=dict(re.findall(r'(\w+)=(\S+)',s));rows.append({k:v if k in ('context','ppu') else int(v) for k,v in kv.items()})
            assert len(rows)==12
            if mode=='old':
                assert sum(v['failed'] for v in rows)==6
                assert all(v['context']=='440107f66803fb34' and v['ppu']=='60425c008c03bc01' and v['error']==1 for v in rows if v['scenario']%6==5)
            elif mode=='new':assert sum(v['failed'] for v in rows)==4
            else:assert all(v['failed']==v['error']==0 and v['old']==0 for v in rows)
            if mode=='b':assert all(v['checked']==4 for v in rows)
            fills=re.findall(r'FILL699 grants=(\d+) replies=(\d+)',log)
            assert len(fills)==12 and all(int(g)>0 and g==r for g,r in fills)
            stops=re.findall(r'STOP703 scenario=(\d+) step=(\d+) quiescent=1',log)
            if mode=='bstop':assert len(stops)==12 and {int(s) for _,s in stops}=={49,52,55,58,61,64}
            tests.append(dict(memory_phase=m['memory_phase_ns'],cases=rows,fills=fills,stops=stops,log=sha(d/'simulation.log')));allrows+=rows
            for n in ('inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log'):add(d/n,d.name+'/'+n)
        runs[mode]=dict(cases=len(allrows),failures=sum(v['failed'] for v in allrows),tests=tests)
    guards={}
    for label in ('status01','plan01','bus01'):
        d=a.temp/f'nes-bonus703-{label}';r=read(d/'result.json');assert r['passed']
        # Only NES/PPU changed fromA toB; every module in these execution checks
        # is byte-identical to selectedB. Do not rerun unchanged tests as new proof.
        for n,h in r['pins'].items():
            if (selected/n).is_file():assert sha(selected/n)==h,(label,n)
        guards[label]=dict(result=r,selectedB_binding=True)
        for f in d.iterdir():
            if f.is_file() and f.suffix in ('.json','.sv','.log','.hex'):add(f,d.name+'/'+f.name)
    boards={}
    for n,d in [('699',baseline),('A',a.temp/'nes-bonus703-board01'),('B',selected)]:
        c=cost(d);boards[n]=c
        for f in (d/'output_files').iterdir():
            if f.suffix in ('.rpt','.summary','.sof'):add(f,n+'/output_files/'+f.name)
        for f in d.iterdir():
            if f.suffix in ('.tsv','.tcl','.json'):add(f,n+'/'+f.name)
        if n=='A':
            for rel in ('rtl/nes.v','rtl/ppu.sv'):add(d/rel,'A/'+rel)
    b=boards['B'];assert b['SOF'] and b['STA'] and not b['LAB_error']
    schedules={}
    for phase in (1,2):
        d=a.temp/f'nes-bonus703-step{phase}';old=a.temp/f'nes-bonus699-step{phase}'
        r=read(d/'joint.json');o=read(old/'joint.json');assert r['passed'] and r['commits']==53
        for k in ('frames','firmware_SHA256','client_SHA256','parameters','wire_B','ARM_instructions','ROM_read_allocations'):assert r[k]==o[k],(phase,k)
        t=trace(d,a.temp/f'nes-front638-both{phase}h');ot=trace(old,a.temp/f'nes-front638-both{phase}h')
        for k in ('intervals','checked'):assert t[k]==ot[k],(phase,k)
        assert t['intervals'][952]['VBlank']==3 and t['intervals'][957]['final_waits']==0
        assert t['details'][951]['marks']['reveal']['line']<=246
        schedules[phase]=dict(frames=53,cycle_identical_to699=True,dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
            interval952=t['intervals'][952],final957=t['intervals'][957],firmware=r['firmware_SHA256'],client=r['client_SHA256'],proof=sha(d/'joint.json'),
            scope='Actual linked ARM/65816 with existing SPI/IRQ/ROM calendar, independently bound unchanged host interface; not simultaneous complete NES/PSRAM RTL. SameA andB host pins.')
        for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json'):add(d/n,d.name+'/'+n)
    # Retain a small exact request/reply timeline, separately from final counts.
    timeline={}
    for mode in ('old','new','b'):
        log=(a.temp/f'nes-bonus703-{mode}03/simulation.log').read_text()
        timeline[mode]=[s for s in log.splitlines() if re.search(r'(CPU699|MEM703) scenario=(3|5) step=',s)]
    inherited=read(ROOT/'analysis/trial700-package.json')
    assert inherited['variants']['701']['ROM_read']['client']==schedules[1]['client']
    special=all(b.get(n) and min(float(r['slack']) for r in b[n])>0 for n in ('word660.tsv','reader661.tsv','io612.tsv'))
    result=dict(stage=703,selected='B board02',inputs=meta,production_changed=['rtl/nes.v','rtl/ppu.sv'],
        exact701_reproduction=dict(conditions=6,context='440107f66803fb34',ppu='60425c008c03bc01',native_error=1,physical_address='03fb34',age=2,CPU_executed=True,whole_game=False),
        runs=runs,guards=guards,boards=boards,schedules=schedules,timeline=timeline,
        functional_gate=True,FIT_STA_gate=min(b['slack_ns'].values())>0 and special,
        menu_recovery=dict(inherited_trial700=sha(ROOT/'analysis/trial700-package.json'),unchanged_ARM_and_65816=True,physical_fix_verified=False),
        budget_delta=dict(LE=b['LE'][0]-boards['699']['LE'][0],FF=b['FF'][0]-boards['699']['FF'][0],RAM_bits=b['RAM_bits'][0]-boards['699']['RAM_bits'][0],LE_free=15408-b['LE'][0],LAB_free=963-b['LAB'],M9K_free=56-b['M9K'][0]),
        limitations=['PPU position/OAM fixture, private reset stub; original ROM code/data with actual T65 andPSRAM model. Not whole263s history.',
        'FirstA fixed CPU fault but failed12/36 next-sprite cases and setup-.021ns; retained, not selected.',
        'Unconstrained external IO still not full signoff;700 transient tile issue remains separate. No new installer.'])
    save(ROOT/'analysis/bonus703-verification.json',result)
    for f in ROOT.glob('tools/*bonus703.py'):add(f,'tools/'+f.name)
    add(ROOT/'analysis/bonus703-verification.json','analysis/bonus703-verification.json')
    for f in a.probe.iterdir():
        if f.is_file() and f.suffix in ('.ps1','.log') and not any(x in f.name.lower() for x in ('wrapper','private','license')):add(f,'jobs/'+f.name)
    inv={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(private.items())};save(a.out/'inventory.json',inv)
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(private.items()):z.write(p,n)
    with zipfile.ZipFile(zpath) as z:
        import hashlib
        for n,h in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==h['SHA256']
    save(ROOT/'analysis/bonus703-archive.json',dict(stage=703,location='WORKSPACE/probes/nes-bonus703/'+a.out.name,SHA256=sha(zpath),files=len(inv),all_verified=True,raw_ROM=False,license=False))
    print(json.dumps(dict(functional=True,FIT_STA=result['FIT_STA_gate'],LE=b['LE'],LAB=b['LAB'],slack=b['slack_ns'],schedules=schedules),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
