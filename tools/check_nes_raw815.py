"""Inject STOP at the production consumer's cold and certified row boundaries."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from check_nes_progress680_interior import fixture, prepare
from nes_raw506 import sha
from test_nes_idle524_priority import case
from test_nes_seal538_stop import exercise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("trace","client","mesen","out"):
        parser.add_argument("--"+arg,type=Path,required=True)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    cases = [(906,"raw_row489"),(906,"final212")]
    # 907 transfers all three odd rows; 908 and 909 transfer the outer two,
    # on opposite banks. STOP at the omitted middle must also suppress row 2.
    cases.extend((g,f"row624_{i}") for g in (907,908,909) for i in range(3))
    rows = [exercise(args,g,label) for g,label in cases]
    source = args.out/"interior-input"
    prepare(args.trace, source)
    body = (args.client/"body.bin").read_bytes()
    def full_map(script, labels):
        return fixture(script,labels,body).replace("1152","1536")
    receipts = []
    for g in (906,907):
        sub = SimpleNamespace(trace=source,client=args.client,mesen=args.mesen,out=args.out/f"map{g}")
        sub.out.mkdir()
        for name in ("late_stop","cold","bad_manifest"):
            receipts.append(case(sub,g,name,edit_fixture=full_map))
    (args.out/"result.json").write_text(json.dumps(dict(client=sha(args.client/"sink165.sfc"),
                    passed=True, cases=rows, receipts=receipts),indent=2)+"\n")
