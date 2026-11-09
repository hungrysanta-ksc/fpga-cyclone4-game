"""Bind selected long-mode machine code, same-work schedule and full board gates."""
import argparse,json
from pathlib import Path
from analyze_nes_status689 import cost
from nes_raw506 import sha

def read(p):return json.loads(p.read_text(encoding='utf8'))
def run(a):
    s=read(a.probe/'schedule-step.json');board=a.traces/'nes-longrun694-board01'
    pins=read(board/'inputs694.json')
    for n,h in pins['base'].items():assert sha(board/n)==pins['changed'].get(n,h),n
    assert set(pins['changed'])=={'sink-program.hex'}
    b=cost(board);old=read(Path('analysis/status689-verification.json'))['boards']['689D']
    assert b['SOF'] and b['STA'] and not b['LAB_error']
    for k in ('LE','LAB','M9K','slack_ns','unconstrained'):assert b[k]==old[k],k
    for k in ('word660.tsv','reader661.tsv','io612.tsv'):
        assert b[k] and min(float(r['slack']) for r in b[k])>0,k
    proofs={}
    for name in ('boot02','bus01','plan01','exit02','stop01'):
        f=a.traces/f'nes-longrun694-{name}/result.json';r=read(f);assert r['passed']
        proofs[name]={'SHA256':sha(f),'result':r}
    w=a.traces/'nes-longrun694-wrap03';r=read(w/'joint.json')
    assert r['passed'] and r['commits']==3 and r['last_status']==1
    assert r['firmware_SHA256']==s['firmware'] and r['client_SHA256']==s['CPU']
    generations=[]
    for line in (w/'packets.jsonl').read_text().splitlines():
        packet=bytes.fromhex(json.loads(line)[2]);g=int.from_bytes(packet[8:10],'little')
        if not generations or g!=generations[-1]:generations.append(g)
    assert generations==[65534,65535,0],generations
    proofs['wrap03']={'SHA256':sha(w/'joint.json'),'wire_generations':generations,'commits':3,'scope':r['scope']}
    guard=read(a.probe/'guards01.json');menu=read(a.probe/'menu01.json')
    assert guard['passed'] and guard['firmware']==menu['firmware']==s['firmware']
    bases={}
    for name in ('none','program','done','busy','token'):
        f=a.probe/f'base01-{name}/result.json';r=read(f)
        assert r['passed'] and r['firmware_sha256']==s['firmware']
        assert r['base_restored']==r['safe_return']==int(name=='none')
        bases[name]={'SHA256':sha(f),'result':r}
    for p in s['phases'].values():
        assert p['functional_pass'] and p['work_equal'] and all(p['protected'].values())
        assert p['input7_before956_ACK_ms']>0
        for name in ('MMC690','MMC666'):
            assert not p['comparisons'][name]['VBlank_regressions']
            assert p['comparisons'][name]['last_ACK_delta_ms']<=0
    strict=all(p['comparisons']['MMC690']['dense_delta_ms']<=0 and not p['comparisons']['MMC690']['new_final_waits'] for p in s['phases'].values())
    report={'stage':694,'selected':'arm01 + client01 + board01','schedule':s,'boards':{'694':b,'689D':old},'inputs':pins,
        'boundaries':proofs,'ARM_guards':guard,'menu':menu,'base':bases,
        'Flash_B':guard['Flash_B'],'Flash_free_B':212992-guard['Flash_B'],'BSS_delta690_B':8,
        'CPU':read(a.probe/'client01/build.json'),'functional_gate':True,'whole_FIT_STA_no_regression':True,
        'protected_VBlank_and_last_ACK_gate':True,'strict_all_time_no_regression':strict,
        'performance_candidate_selected':False,'physical_tested':False,'installer_created':False,
        'decision':'Long-mode feature candidate only. Keep MMC690 normal unchanged. Phase1 dense +10.728us and added906 final wait are explicit overhead; no display interval VBlank loss or final957 ACK regression. This is not a clean performance improvement.',
        'scope':'Boundary RTL and separate actual M4/native65816 schedule with modeled SPI/IRQ and ROM calendar; not whole FPGA co-simulation or physical long play. Existing IO constraints only; unconstrained external IO remains open.',
        'source_pins':{p.name:sha(p) for p in Path('tools').glob('*longrun694*.py')}}
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS694 functional/full FIT/STA/protected intervals; strict timing no-regression:',strict)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','traces','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
