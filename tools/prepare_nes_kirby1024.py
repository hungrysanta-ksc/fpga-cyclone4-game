"""Extend the bounded SD progress journal for the 768 KiB loader."""
from pathlib import Path
import shutil
from check_nes_kirby1023_release import WORK as PREVIOUS
from prepare_nes_trial802 import rename_edition

WORK=PREVIOUS.with_name("nes-kirby1024")
def prepare():
    src=WORK/"link/src"
    shutil.copytree(PREVIOUS/"link",src.parent)
    edition=WORK/"edition"
    rename_edition(PREVIOUS/"link/src",edition,1023,1024)
    for path in edition.iterdir():
        shutil.copy2(path,src/path.name)
    for name,old,new in [
        ("nes_checkpoint112.c","sequence>=128","sequence>=256"),
        ("nes_budget210.c","edition=1023","edition=1024")]:
        path=src/name
        data=path.read_bytes()
        assert data.count(old.encode())==1
        path.write_bytes(data.replace(old.encode(),new.encode()))

if __name__=="__main__":
    prepare()
