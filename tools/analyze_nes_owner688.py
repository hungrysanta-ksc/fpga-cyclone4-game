"""Reuse the exact687 time/pixel/DMA gates, with actual query-owner evidence."""
import argparse,inspect
from pathlib import Path
import analyze_nes_pair687 as prior
from nes_raw506 import once

def implementation():
    s=inspect.getsource(prior.run).replace("'687'","'688'").replace("'686'","'687'")
    s=s.replace('nes-seal686-arm','nes-pair687-pending').replace('delta686','delta687')
    s=s.replace('../probes/nes-seal686/arm01/src','../probes/nes-pair687/arm04/src')
    s=s.replace('analysis/seal686-verification.json','analysis/pair687-verification.json')
    s=s.replace("changed==['nes_native_sink165.c']","changed==['nes_native_sink165.c','nes_plan_service200.c']")
    s=s.replace('stage=687','stage=688').replace("glob('*687*.py')","glob('*688*.py')").replace('Actual linked687','Actual linked688')
    s=s.replace('for g in (955,956,957):','for g in (951,955,956,957):')
    s=s.replace("BG=preparation(f,g)['BG']", "BG=preparation(f,g)['BG'] if g!=951 else []")
    s=once(s,"a.out.write_text(json.dumps(report,indent=2)","report['shared_analyzer_SHA256']=sha(Path('tools/analyze_nes_pair687.py'))\n    a.out.write_text(json.dumps(report,indent=2)")
    s=once(s,"new_RTL=False,new_CPU=False,new_FIT=False,new_STA=False", "new_RTL=False,new_CPU=False,new_FIT=True,new_STA=False,whole_board_evidence='analysis/owner688-board.json',deployment_gate=False")
    s=once(s,"over_budget_first_build=dict(Flash_B=213000,replayed=False,reason='Second next cursor duplicated existing gap scan; removed in arm02.'),",
        "failed_first_build=dict(Flash_B=212980,replayed=False,reason='Credit error could leave transient query grant set; arm02 clears it on failed packet send.'),")
    begin=s.index("        c['map_owner_samples']=")
    end=s.index("        c['BG_window_comparison']=",begin)
    s=s[:begin]+'''        owner=[v for v in ev if v['event']=='owner688_return']
        assert owner,'actual runpy owner observer was not connected'
        for v in owner:
            if not v['grant']:continue
            assert v['result']==1 and not v['bulk_pending']
            queries=[q for q in ev if q['event']=='SPI' and q['opcode']=='0xe8' and v['begin']['clock']<=q['start']<=q['clock']<=v['clock']]
            assert queries,'grant without an actual producer query'
            q=bytes.fromhex(queries[-1]['reply']);assert len(q)==20 and q[6]==0 and not(q[3]&2)
        c['query_owner']=dict(returns=len(owner),empty_grants=sum(bool(v['grant']) for v in owner),samples=owner)
''' +s[end:]
    ns=dict(vars(prior));exec(s,ns);return ns['run']

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','arm','client','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--guards',type=Path);p.add_argument('--replay',type=Path)
    p.add_argument('--run-prefix',default='nes-owner688-arm')
    implementation()(p.parse_args())
