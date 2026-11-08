"""Bind the first full680/685 board gate to exact inputs and failed FIT evidence."""
import argparse,json,re
from pathlib import Path
from analyze_nes_progress680 import mapping
from analyze_nes_output615 import sha

def report_text(p):
    raw=p.read_bytes()
    try:return raw.decode('utf-8')
    except UnicodeDecodeError:return raw.decode('cp949')

def budget(board):
    p=board/'output_files';summary=report_text(p/'board.fit.summary');rpt=report_text(p/'board.fit.rpt')
    def use(label,text):
        m=re.search(label+r'\s*[:;]\s*([\d,]+)\s*/\s*([\d,]+)',text)
        return [int(v.replace(',','')) for v in m.groups()]
    labs=re.search(r'Fitter requires (\d+) LABs.*contains only (\d+) LABs',rpt)
    return dict(LE=use('Total logic elements',summary),comb=use('Total combinational functions',summary),
        FF=use('Dedicated logic registers',summary),M9K=use('M9Ks',rpt),RAM_bits=use('Total memory bits',summary),
        LAB_error=[int(v) for v in labs.groups()] if labs else None,fit=summary.splitlines()[0],
        SOF=(p/'board.sof').exists(),STA=(p/'board.sta.rpt').exists(),fit_report=sha(p/'board.fit.rpt'))

def run(a):
    inputs=json.loads((a.board/'inputs680.json').read_text())
    for name,old in inputs['base'].items():
        assert sha(a.base/name)==old,name
        assert sha(a.board/name)==inputs['changed'].get(name,old),name
    assert set(inputs['changed'])=={'sink-program.hex','nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv'}
    assert sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
    costs={k:budget(p) for k,p in [('MMC666',a.base),('688',a.board)]}
    c=costs['688'];assert c['LAB_error']==[969,963] and not c['SOF'] and not c['STA']
    b=costs['MMC666'];assert b['SOF'] and b['STA']
    rpt=report_text(a.base/'output_files/board.fit.rpt')
    b['LAB']=int(re.search(r'Total LABs: *partially or completely used\s*;\s*(\d+)',rpt)[1])
    result=dict(stage=688,functional_evidence=sha(Path('analysis/owner688-verification.json')),
        costs=costs,mapping={k:mapping(p) for k,p in [('MMC666',a.base),('688',a.board)]},
        same_pin_clock_constraints=True,inputs=inputs,fit_passed=False,STA_executed=False,
        LAB_shortage=6,LE_arithmetic_free=15408-c['LE'][0],M9K_free=0,
        new_constraints=False,new_seed=False,installer_created=False,
        reports={n:sha(a.board/n) for n in ('compile.log','inputs680.json','output_files/board.map.rpt','output_files/board.map.summary','output_files/board.fit.rpt','output_files/board.fit.summary')},
        scope='First whole680 progress RTL plus685 ROM gate. Fitter failed before placement/STA; LE arithmetic is not usable placement margin. No attribution of all LAB cost to a single progress bit.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('costs','LAB_shortage','fit_passed','STA_executed')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','client','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
