# SPDX-License-Identifier: MIT
"""Record two half-open gameplay windows at ARM-observed final display completion."""
import argparse
import json
import re
from pathlib import Path
from nes_raw506 import once, sha
from nes_transfer512 import compact_reports

FIELD = 'display_1_40_60'
def patch(src,out):
    assert sha(src/'obj-nes-100/firmware.stm')==json.loads((Path(__file__).resolve().parents[1]/'analysis/window516-package.json').read_text())['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False)
    compact_reports(src,out)
    header=(src/'nes_budget210.h').read_text()
    (out/'nes_budget210.h').write_text(once(header,' uint32_t frame_start,last_display,failed_transfers;',
        ' uint32_t displayed_window[2];\n uint32_t frame_start,last_display,failed_transfers;'),encoding='utf8',newline='\n')
    path=out/'nes_budget210.c'
    s=once(path.read_text(),' b[B210_FRAMES]++;',' if(elapsed>=100 && elapsed<6000)s->displayed_window[elapsed>=4000]++;\n b[B210_FRAMES]++;')
    s=once(s,'open=%u\\ncolumns=',f'open=%u\\n{FIELD}=%lu,%lu\\ncolumns=')
    s=once(s,'nes_budget210.open?1u:0u);','nes_budget210.open?1u:0u,\n  (unsigned long)nes_budget210.displayed_window[0],(unsigned long)nes_budget210.displayed_window[1]);')
    path.write_text(s,encoding='utf8',newline='\n')

def windows(budget,elapsed_ms):
    from analyze_nes_supply485_hardware import fields
    b=fields(budget)
    # Old frame-start bins straddle 1s, and cannot reconstruct completion time.
    if FIELD not in b:return None
    if b.get('tick_ms')!='10':raise ValueError('unexpected tick rate')
    counts=b[FIELD].split(',')
    if len(counts)!=2 or any(not c.isascii() or not c.isdecimal() for c in counts):raise ValueError('invalid display window counts')
    if elapsed_ms<60000:raise ValueError('incomplete 60-second observation')
    return [dict(start_s=start,end_s=end,displays=int(n),fps=int(n)/(end-start)) for n,(start,end) in zip(counts,[(1,40),(40,60)])]

def duration_ms(progress):
    marks = re.findall(r"\bseq=(\d+) stage=(\w+).*?elapsed_ms=(\d+)", progress)
    if not marks or [int(i) for i, _, _ in marks] != list(range(len(marks))):
        raise ValueError("incomplete progress sequence")
    clocks = [int(t) for _, _, t in marks]
    stages = [stage for _, stage, _ in marks]
    if (clocks != sorted(clocks) or stages[-1] != "MENU_PREPARED" or
            any(stages.count(s) != 1 for s in ("DISPLAY_NEXT", "DISPLAY_STOPPED"))):
        raise ValueError("incomplete display or menu recovery")
    return clocks[stages.index("DISPLAY_STOPPED")] - clocks[stages.index("DISPLAY_NEXT")]


def read_run(budget, progress):
    return windows(budget.read_text(encoding="utf-8-sig"),
                   duration_ms(progress.read_text(encoding="utf-8-sig")))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    build = sub.add_parser("prepare")
    for key in ("src", "out"):
        build.add_argument("--" + key, type=Path, required=True)
    report = sub.add_parser("report")
    compare = sub.add_parser("compare")
    for name in ("budget", "progress"):
        report.add_argument("--" + name, type=Path, required=True)
        for run in ("previous", "current"):
            compare.add_argument("--" + run + "-" + name, type=Path, required=True)
    a = p.parse_args()
    if a.action == "prepare":
        patch(a.src, a.out)
    elif a.action == "report":
        print(json.dumps(read_run(a.budget, a.progress)))
    else:
        previous = read_run(a.previous_budget, a.previous_progress)
        current = read_run(a.current_budget, a.current_progress)
        delta = None
        if previous is not None and current is not None:
            delta = [c["fps"] - b["fps"] for b, c in zip(previous, current)]
        print(json.dumps(dict(previous=previous, current=current, fps_delta=delta)))
