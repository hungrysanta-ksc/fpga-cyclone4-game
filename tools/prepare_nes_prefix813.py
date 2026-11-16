"""Keep early section-5 sends from ageing a live bulk receipt beyond its window."""
from package_nes_obj807 import ROOT, digest, read
from prepare_nes_trial802 import PROBES, rename_edition

WORK = PROBES / "nes-prefix813"
PARENTS = {813:(811, "811"), 814:(812, "812c")}


def prepare():
    proof = read(ROOT / "analysis/trial811-package.json")
    for edition, (parent, build) in PARENTS.items():
        src = PROBES / f"nes-trial811/link{build}/src"
        assert digest((src/"obj-nes-100/firmware.stm").read_bytes()) == proof["variants"][str(parent)]["firmware"]
        patch = WORK / f"patch{edition}"
        rename_edition(src, patch, parent, edition)
        name = "nes_native_sink165.c"
        code = (src/name).read_bytes()
        marker = b"!p->patch_count || s->plan->bank_history!=2"
        assert code.count(marker) == 1
        # Both prefix packets bypass plan progress. The ordinary path below
        # still owns these bytes when the producer has a pending bulk receipt.
        (patch/name).write_bytes(code.replace(marker, marker + b" || s->plan->bulk_pending"))


if __name__ == "__main__":
    prepare()
