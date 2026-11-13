"""Bind BG deadline reproductions, selected D, whole cost and unchanged schedules."""
import argparse,difflib,hashlib,json,re,zipfile
from pathlib import Path
from nes_game147 import ROOT,sha
from analyze_nes_status689 import cost
from analyze_nes_output664 import trace

def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);archive={}
    def add(p,n):
        assert p.is_file(),p
        archive[n]=p
    base=a.temp/'nes-bonus703-board02';selected=a.temp/'nes-bg707-board04'
    meta=read(selected/'inputs707.json')
    for n,h in meta['base'].items():
        assert sha(base/n)==h and sha(selected/n)==meta['changed'].get(n,h),n
        add(base/n,'703B/'+n);add(selected/n,'707D/'+n)
    assert set(meta['changed'])=={'rtl/ppu.sv'}
    patch=''.join(difflib.unified_diff((base/'rtl/ppu.sv').read_text().splitlines(True),(selected/'rtl/ppu.sv').read_text().splitlines(True),fromfile='703B/rtl/ppu.sv',tofile='707D/rtl/ppu.sv'))
    (a.out/'production.patch').write_text(patch,encoding='utf8',newline='\n');add(a.out/'production.patch','production.patch')
    paths=[Path(p) for p in read(a.probe/'matrix-d-inputs.json')]
    extras=['boundary01','boundary-old-p0','boundary-old-p2','cpu-old01','cpu-old-p0','cpu-old-p2','readcpu-old03','readcpu-new03','replay03-old']
    paths += [a.temp/('nes-bg707-'+n) for n in extras]
    runs={};candidate_cases=0
    for d in paths:
        m=read(d/'inputs.json');r=read(d/'result.json');log=(d/'simulation.log').read_text()
        assert r['completed'] and r['returncode']==0 and '# Errors: 0,' in log,d
        rows=[]
        for line in re.findall(r'^# CASE\w* ([^\r\n]+)',log,re.M):
            kv=dict(re.findall(r'(\w+)=([^ ]+)',line))
            rows.append({k:v if k in ('context','ppu') else int(v) for k,v in kv.items()})
        assert rows,d
        old='old' in d.name or d.name=='nes-bg707-boundary01'
        if old:
            expected=4 if 'boundary' in d.name else 2
            assert sum(v['failed'] for v in rows)==expected,(d,rows)
        else:
            assert all(v['failed']==v['error']==0 for v in rows),d
            candidate_cases+=len(rows)
        for n,h in m['sources'].items():
            assert sha(d/n)==h,(d,n)
            if n!='game147_tb.sv':assert sha((base if old else selected)/n)==h,(d,n)
        fills=re.findall(r'FILL699 grants=(\d+) replies=(\d+)',log)
        if fills:assert all(int(g)>0 and g==r for g,r in fills),d
        stops=re.findall(r'STOP703 scenario=(\d+) step=(\d+) quiescent=1',log)
        if '-sprite-1-' in d.name:assert len(stops)==12 and {int(s) for _,s in stops}=={49,52,55,58,61,64}
        runs[d.name]=dict(cases=rows,old=old,failures=sum(v['failed'] for v in rows),fills=fills,mid_STOP=stops,log=sha(d/'simulation.log'),inputs=m)
        for n in ('inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log'):add(d/n,d.name+'/'+n)
    target=('e30143c2c221e161','60b9880005858586')
    for n in ('nes-bg707-boundary01','nes-bg707-readcpu-old03','nes-bg707-replay03-old'):
        assert any((r['context'],r['ppu'])==target for r in runs[n]['cases']),n
    fine=a.temp/'nes-bg707-fine01';log=(fine/'simulation.log').read_text()
    assert 'DONE698 FINE707 cases=3072 reference_equivalent=1 preview_render=1' in log and '# Errors: 0,' in log
    for n in ('inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log'):add(fine/n,fine.name+'/'+n)
    boards={}
    for label,d in [('703B',base),*[(chr(64+i),a.temp/f'nes-bg707-board0{i}') for i in range(1,5)]]:
        boards[label]=cost(d)
        for f in (d/'output_files').iterdir():
            if f.suffix in ('.rpt','.summary','.sof'):add(f,label+'/output_files/'+f.name)
        for f in d.iterdir():
            if f.suffix in ('.tsv','.tcl','.json','.rpt'):add(f,label+'/'+f.name)
        if label in ('A','B','C'):add(d/'rtl/ppu.sv',label+'/rtl/ppu.sv')
    b=boards['D'];assert b['SOF'] and not b['LAB_error'] and b['STA'] and min(b['slack_ns'].values())>0
    for k in ('word660.tsv','reader661.tsv','io612.tsv'):
        assert b.get(k) and min(float(r['slack']) for r in b[k])>0,k
    guards={}
    for label in ('status01','plan01','bus01'):
        d=a.temp/f'nes-bonus703-{label}';r=read(d/'result.json');assert r['passed']
        for n,h in r['pins'].items():
            if (selected/n).is_file():assert sha(selected/n)==h,(label,n)
        guards[label]=dict(proof=sha(d/'result.json'),unchanged_selected_D=True,result=r)
        for n in ('result.json',):add(d/n,d.name+'/'+n)
    schedules={};speed={}
    for phase in (1,2):
        d=a.temp/f'nes-bg707-step{phase}';old=a.temp/f'nes-bonus703-step{phase}'
        r=read(d/'joint.json');o=read(old/'joint.json');assert r['passed'] and r['commits']==53
        for k in ('frames','firmware_SHA256','client_SHA256','parameters','wire_B','ARM_instructions','ROM_read_allocations'):assert r[k]==o[k],(phase,k)
        t=trace(d,a.temp/f'nes-front638-both{phase}h');ot=trace(old,a.temp/f'nes-front638-both{phase}h')
        for k in ('intervals','checked'):assert t[k]==ot[k],(phase,k)
        assert t['intervals'][952]['VBlank']==3 and t['intervals'][957]['final_waits']==0
        assert t['details'][951]['marks']['reveal']['line']<=246
        schedules[phase]=dict(frames=53,cycle_identical_to703B=True,intervals=t['intervals'],dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],line951=t['details'][951]['marks']['reveal']['line'],firmware=r['firmware_SHA256'],client=r['client_SHA256'],proof=sha(d/'joint.json'))
        ev=read(d/'events.json');detail=t['details'][951]
        ready=[e for e in ev if e.get('generation')==951 and e['event'] in ('immutable673','bg_map_frozen','prepare_enter','end_enter','output_enter')]
        speed[phase]=dict(frame951=detail,semantic_ready=ready,dense=t['dense'],matched_work={g:v['work'] for g,v in t['frames'].items()})
        for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv'):add(d/n,d.name+'/'+n)
    assert speed[1]['matched_work']==speed[2]['matched_work']
    # The schedule binds the same host/output sources; new NES/PPU is tested
    # separately with actual T65 and physical reader, not substituted as timing.
    a_meta=read((a.temp/'nes-bg707-board01')/'inputs707.json')
    for n in meta['base']:
        if n!='rtl/ppu.sv':assert sha(selected/n)==a_meta['changed'].get(n,a_meta['base'][n])
    boot=a.temp/'nes-bg707-boot02'
    bootlog=(boot/'simulation.log').read_text()
    assert 'PASS GAME147' in bootlog
    for n in ('inputs.json','result.json','game147_tb.sv','simulation.log'):add(boot/n,boot.name+'/'+n)
    result=dict(stage=707,selected='D board04',merged_PR156='4ee65ac300c3b5eca73848bd0b408c1bc63b6800',inputs=meta,
        target=dict(context=target[0],ppu=target[1],address='21e161',line=193,dot=230,error=2,age=2),
        mechanisms=['Render enable before BG low-plane with preceding CPU request','PPUDATA read tail increments fine Y before BG read'],
        production_changed=['rtl/ppu.sv'],runs=runs,candidate_cases=candidate_cases,fine_cases=3072,fine_proof=sha(fine/'simulation.log'),
        boards=boards,guards=guards,schedules=schedules,speed_followup=speed,
        functional_gate=True,FIT_STA_gate=True,new_hardware_test=False,installer_created=False,
        resource_delta=dict(LE=b['LE'][0]-boards['703B']['LE'][0],FF=b['FF'][0]-boards['703B']['FF'][0],RAM_bits=b['RAM_bits'][0]-boards['703B']['RAM_bits'][0],LE_free=15408-b['LE'][0],LAB_free=963-b['LAB'],M9K_free=56-b['M9K'][0],ARM_Flash_B=0,ARM_RAM_B=0,CPU_ROM_B=0),
        inherited_menu_base_proof=sha(ROOT/'analysis/trial704-package.json'),
        scope='Actual T65/private setup and controlled PPU position with native arbiter/PSRAM; separate actual linked ARM/65816 SPI/IRQ/ROM-calendar replay. Not whole placed-board cosimulation or hardware FPS.',
        limitations=['Physical705 preceding CPU history unavailable; two valid exact-context reproductions do not identify a unique physical trigger.','Natural boot20 frames was old703B and direct reader only; not candidate full-game stability.','Repeated graphics and stage0 boot timeout deferred by user; not fixed by performance assumption.','External IO full signoff still open; existing constraints unchanged.','No performance gain claimed707; schedules unchanged.'])
    save(ROOT/'analysis/bg707-verification.json',result)
    add(ROOT/'analysis/bg707-verification.json','analysis/bg707-verification.json')
    for f in (ROOT/'tools').glob('*bg707*.py'):add(f,'tools/'+f.name)
    # Retain failed fixtures and intermediate experiments without ROM bytes.
    for d in a.temp.glob('nes-bg707-*'):
        if d.is_dir():
            for n in ('inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log'):
                if (d/n).is_file():add(d/n,d.name+'/'+n)
    for n in ('matrix-d.ps1','matrix-d-inputs.json','fine.ps1','step.ps1','board04-build.log'):
        add(a.probe/n,'jobs/'+n)
    inv={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(archive.items())}
    save(a.out/'inventory.json',inv)
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(archive.items()):z.write(p,n)
    with zipfile.ZipFile(zpath) as z:
        for n,h in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==h['SHA256']
    save(ROOT/'analysis/bg707-archive.json',dict(stage=707,location='WORKSPACE/probes/nes-bg707/'+a.out.name,SHA256=sha(zpath),files=len(inv),all_verified=True,raw_ROM=False,license=False,inventory_SHA256=sha(a.out/'inventory.json')))
    print(json.dumps(dict(cases=candidate_cases,fine_cases=3072,LE=b['LE'],LAB=b['LAB'],slack=b['slack_ns'],last_ACK=[s['last_ACK'] for s in schedules.values()])))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
