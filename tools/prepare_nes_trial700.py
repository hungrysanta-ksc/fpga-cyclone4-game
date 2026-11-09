"""Relabel695/696 as700/701; bind699 fix to the normal685 packed ROM."""
import argparse,json,shutil
from pathlib import Path
from package_nes_window516 import LABELS
from nes_raw506 import sha

def run(a):
    old=json.loads(Path('analysis/trial695-package.json').read_text())
    proof=json.loads(Path('analysis/bonus699-verification.json').read_text())
    assert proof['functional_gate'] and proof['FIT_STA_gate'] and proof['schedule_model_no_regression']
    a.out.mkdir(parents=True,exist_ok=False);records={}
    for name,base,before,after in [('normal',a.normal,'695','700'),('long',a.long,'696','701')]:
        assert sha(base/'src/obj-nes-100/firmware.stm')==old['variants'][before]['firmware']
        d=a.out/name;d.mkdir();pins={}
        for n in LABELS:
            p=base/'src'/n;b=p.read_bytes();assert before.encode() in b and after.encode() not in b
            (d/n).write_bytes(b.replace(before.encode(),after.encode()))
            pins[n]=dict(before=sha(p),after=sha(d/n))
        records[after]=dict(base=before,firmware=old['variants'][before]['firmware'],files=pins)
    m=proof['inputs'];pins={n:m['changed'].get(n,h) for n,h in m['base'].items()}
    a.board_out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(a.board/n)==h,n
        dst=a.board_out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.board/n,dst)
    oldboard=json.loads(Path('analysis/status689-verification.json').read_text())
    assert sha(a.client/'sink165.sfc')==oldboard['client']
    assert sha(a.client/'sink-program.hex')==oldboard['inputs']['base']['sink-program.hex'] or sha(a.client/'sink-program.hex')==oldboard['inputs']['changed'].get('sink-program.hex')
    shutil.copyfile(a.client/'sink-program.hex',a.board_out/'sink-program.hex')
    changed={n:sha(a.board_out/n) for n,h in pins.items() if sha(a.board_out/n)!=h}
    assert set(changed)=={'sink-program.hex'}
    (a.board_out/'inputs700.json').write_text(json.dumps(dict(base=pins,changed=changed,CPU=sha(a.client/'sink165.sfc'),
        proof699=sha(Path('analysis/bonus699-verification.json')),constraints_changed=False,seed_changed=False),indent=2)+'\n',newline='\n')
    (a.out/'labels.json').write_text(json.dumps(records,indent=2)+'\n',newline='\n')
    print('Prepared700/701 labels and700 normal-ROM board;699 RTL unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('normal','long','out','board','board-out','client'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
