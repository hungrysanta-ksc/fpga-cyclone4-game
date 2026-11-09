"""Exercise the new nonempty-map drain with one row, no legacy silence policy."""
import argparse
import inspect
import json
from pathlib import Path
import check_nes_dma637 as old
from nes_raw506 import once


def run(arm):
    source=inspect.getsource(old.run)
    source=once(source,"('map_upload',0x7ffff<<32,8)","('map_upload',1,8)")
    # Both injected drain failure and STOP at that boundary must prevent SEAL.
    source=once(source,"m.bad_drain=(1 if after_map or receive else 2) if case=='bad_credit' else 0",
                "m.bad_drain=1 if case in ('bad_credit','interrupted') else 0")
    source=once(source,'limit = 40 if late or after_map else 30','limit = 0')
    source=once(source,"'interrupted':m.stop_at","'interrupted':0")
    source=once(source,"assert m.samples==", "assert m.drains==1\n        assert m.samples==")
    ns=dict(old.__dict__)
    exec(compile(source,'one_map_drain668','exec'),ns)
    result=ns['run'](arm)
    result['scope']='Linked ARM SEAL builder; checked-drain result injected. One map row triggers drain without the legacy 19-row/40-service policy. Bad drain/STOP and bad final ACK never commit history.'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(run(a.arm),indent=2)+'\n')
