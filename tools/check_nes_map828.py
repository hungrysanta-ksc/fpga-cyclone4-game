"""Exercise the linked post-session formatters, STOP/base recovery and menu release."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from check_nes_report594 import Reports
from check_nes_menu533 import check as menu
from check_nes_windows518 import run as windows
from prepare_nes_map828 import OUT, PROBES


def main():
    ref=PROBES/"nes-output823/link-826/src"
    base_reports=Reports(ref)
    expected=[base_reports.run(good,826) for good in (False,True)]
    for link in ("link-c","link-right"):
        src=OUT/link/"src"
        dest=OUT/("checks-"+link)
        dest.mkdir(exist_ok=True)
        actual=Reports(src)
        logs=[]
        for good,(baseline,old_cost) in zip((False,True),expected):
            data,new_cost=actual.run(good,826)
            assert data==baseline
            logs.append(dict(persist=good,reference=old_cost,candidate=new_cost,
                             game_B=len(data[0]),budget_B=len(data[2])-1))
        for name,result in (("menu",menu(src,"826")),
                            ("windows",windows(SimpleNamespace(arm=src,layout="demo"))),
                            ("reports",logs)):
            (dest/(name+".json")).write_text(json.dumps(result,indent=2)+"\n")
        script=Path(__file__).with_name("check_nes_transfer512_recovery.py")
        subprocess.run([sys.executable,script,"--arm",src,"--trial","826","--fault","none","--out",dest/"base"],check=True)

if __name__=="__main__":
    main()
