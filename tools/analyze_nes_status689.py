"""Tie unchanged688 CPU schedules, actual689 interface proofs and complete FIT/STA."""
import argparse,csv,json,re
from pathlib import Path
from types import SimpleNamespace
from analyze_nes_owner688 import implementation
from analyze_nes_owner688_board import budget,report_text
from analyze_nes_progress680 import mapping
from analyze_nes_output615 import sha

def load(p):return json.loads(p.read_text())
def cost(p):
    c=budget(p);c['mapping']=mapping(p)
    if c['SOF']:
        c['LAB']=int(re.search(r'Total LABs: *partially or completely used\s*;\s*(\d+)',report_text(p/'output_files/board.fit.rpt'))[1])
    if c['STA']:
        s=(p/'output_files/board.sta.summary').read_text()
        c['slack_ns']={k:min(map(float,re.findall(r'Model '+k+r' [^\n]+\nSlack : ([-\d.]+)',s))) for k in ('Setup','Hold','Recovery','Removal','Minimum Pulse Width')}
        rpt=report_text(p/'output_files/board.sta.rpt')
        c['unconstrained']={name.strip():[int(a),int(b)] for name,a,b in re.findall(r'^; ((?:Illegal Clocks|Unconstrained [\w ]+?)\s*);\s*(\d+)\s*;\s*(\d+)\s*;',rpt,re.M)}
        c['reports']={n:sha(p/'output_files'/n) for n in ('board.sof','board.fit.rpt','board.sta.rpt','board.sta.summary')}
    for filename in ('paths612.tsv','word660.tsv','reader661.tsv','io612.tsv'):
        if (p/filename).exists():
            with (p/filename).open() as f:c[filename]=list(csv.DictReader(f,delimiter='\t'))
    return c

def run(a):
    # Same full independent pixel/byte/credit/beam oracle; no surrogate time.
    validation=a.probe/'schedule-verified.json'
    implementation()(SimpleNamespace(traces=a.traces,arm=a.arm,client=a.client,out=validation,guards=a.arm.parent,replay=a.probe/'replay.ps1',run_prefix='nes-status689-arm'))
    r=load(validation);old=load(Path('analysis/owner688-verification.json'));assert r['firmware']==old['firmware'] and r['client']==old['client']
    phases={}
    for phase,rows in r['phases'].items():
        c=rows['688'];b=old['phases'][phase]['688']
        for k in ('intervals','last_ACK','dense_mean_ms','protected','map955_boundary','checked_input_margin_ms'):
            assert c[k]==b[k],(phase,k)
        phases[phase]=dict(candidate=c,cycle_identical_to688=True)
    boards={name:cost(p) for name,p in [('MMC666',a.traces/'nes-entry665-board01'),('688',a.traces/'nes-owner688-board01'),('689A',a.traces/'nes-status689-board01'),('689B',a.traces/'nes-status689-board02'),('689C',a.traces/'nes-status689-board03'),('689D',a.traces/'nes-status689-board04')]}
    b=a.traces/'nes-status689-board04';inputs=load(b/'inputs689.json')
    for name,h in inputs['base'].items():assert sha(b/name)==inputs['changed'].get(name,h)
    assert sha(b/'sink-program.hex')==sha(a.client/'sink-program.hex')
    guardpaths=[a.traces/f'nes-status689-{n}/result.json' for n in ('diff04','owner01')]
    guards={}
    for p in guardpaths:
        g=load(p);assert g['passed']
        for name,h in g['pins'].items():
            target=p.parent/name if name.endswith('_tb.sv') else b/name
            assert sha(target)==h,(p,name)
        guards[p.parent.name]=dict(SHA256=sha(p),result=g)
    c=boards['689D'];fit=c['SOF'] and not c['LAB_error'];sta=c['STA'] and min(c.get('slack_ns',{'absent':-1}).values())>=0
    if c['STA']:
        for k in ('Illegal Clocks','Unconstrained Clocks','Unconstrained Input Ports','Unconstrained Output Ports'):
            assert c['unconstrained'][k]==boards['MMC666']['unconstrained'][k]
        for k in ('word660.tsv','reader661.tsv','io612.tsv'):
            assert k in c and min(float(row['slack']) for row in c[k])>0,k
    report=dict(stage=689,firmware=r['firmware'],client=r['client'],Flash_B=r['Flash_B'],Flash_free_B=r['Flash_free_B'],
        ARM_unchanged=True,CPU_unchanged=True,new_ARM_RAM_B=0,phases=phases,boards=boards,inputs=inputs,guards=guards,
        inherited_ARM_guards=r['guards'],inherited_CPU_guards=r['inherited_CPU_guards'],schedule_proof=sha(validation),
        functional_gate=r['request_gate'],fit_gate=fit,STA_gate=sta,request_gate=r['request_gate'] and fit and sta,
        selected_physical='MMC666',selected_candidate='689D',new_hardware_test=False,installer_created=False,
        timing_scope='Existing unchanged board constraints. External IO signoff remains open; input path count661->664 and output3005/3008->2991/2994 are recorded, not waived.',
        replay_binding='Replay ran against separately checked689A interface.689D/688 sampled boundary equality and unchanged ARM/CPU hashes establish the same model interface; no new placed FPGA latency is substituted.',
        source_pins={p.name:sha(p) for p in Path('tools').glob('*689*.py')},
        scope='Actual serial RTL boundary proofs plus separate linked M4/65816 replay; SPI/IRQ/ROM calendar model, not full placed FPGA/CPU cosimulation or physical FPS.')
    a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps({k:report[k] for k in ('functional_gate','fit_gate','STA_gate','request_gate','Flash_free_B')}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','probe','arm','client','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
