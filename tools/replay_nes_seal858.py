"""Boot the paired links independently for each dot-zero phase and scene."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from pathlib import Path

from prepare_nes_seal858 import ROOT


def run(args,clip,phase):
    tag=args.tag
    with (ROOT/f'{tag}-{clip}-{phase}.log').open('w') as log:
        subprocess.run([sys.executable, str(Path(__file__).with_name('replay_nes_column853.py')),
            str(args.temp),clip,str(phase),'on',tag+'-on','--arm',str(args.arm),
            '--client',str(args.client),'--budget',str(args.budget)],
            stdout=log,stderr=subprocess.STDOUT,check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    p.add_argument('clips',nargs='+',choices=('opening','demo','transition'))
    p.add_argument('--arm',type=Path,default=ROOT/'link-c/src')
    p.add_argument('--client',type=Path,default=ROOT/'client')
    p.add_argument('--budget',type=Path,default=Path.home()/'Downloads/nes-budget-mmc855.txt')
    args=p.parse_args()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(run,args,clip,phase) for clip in args.clips for phase in (1,2)]
        for f in futures:f.result()
