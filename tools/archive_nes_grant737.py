"""Archive the six 737 firmware links, joint traces and partial STOP fixtures."""
from argparse import ArgumentParser
from pathlib import Path
from archive_nes_prefix736 import archive

if __name__=='__main__':
    p=ArgumentParser()
    for name in ('probe','temp','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    archive(a.probe,a.temp,a.out,stage=737,name='grant737',
            builds=('normal01','arm01','normal02','arm02','normal03','arm03'),
            tags=('a','b','c'),stops=('stop',),frame_count=318)
