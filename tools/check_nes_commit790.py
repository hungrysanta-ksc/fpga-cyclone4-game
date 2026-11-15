# SPDX-License-Identifier: MIT
"""Exercise source CRC, STOP, display and menu ownership on the linked ARM."""
import argparse
import json
from pathlib import Path
from check_nes_capture785 import exercise, retirement
from check_nes_supply781 import check


def verify(src, rearm, *, batch_empty_status=False, trial="763"):
    proof = check(src, extra=True, owner=True, batch_empty_status=batch_empty_status, trial=trial)
    proof["commit"] = [exercise(src, case) for case in
                       ("cached", "uncached", "bad_token", "bad_crc", "stop_commit")]
    if rearm:
        proof["retire"] = [retirement(src, case) for case in
                           ("normal", "busy", "no_finish", "no_ACK", "stop_after_EA",
                            "count", "descriptor", "fault", "crc")]
    if src.parent.name in ("link-owned","link-owned_ready"):
        for complete in (False,True):
            proof["handoff_"+str(complete)]=[retirement(src,case,complete) for case in
                ("normal","busy","no_finish","no_ACK","stop_after_EA","count","descriptor","fault","crc")]
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--rearm", action="store_true")
    args = parser.parse_args()
    args.out.write_text(json.dumps(verify(args.src,args.rearm),indent=2)+"\n",newline="\n")
