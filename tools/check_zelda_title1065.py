"""Compare rank fragments in the reference opening and replay captured geometry on both final links."""
import json

from check_ff3_backdrop1046 import captured, check
from package_nes_headers1064 import checked_sim
from prepare_sxrom1065 import OUT


def title_fragments():
    lines = (OUT / "zelda2-opening.txt").read_text().splitlines()
    assert "FRAME 60 COLORS 11" in lines
    oam = bytes(int(line.split()[-1], 16) for line in lines if line.startswith("60 ") and " CPU 2004 " in line)
    pattern = bytes(int(line.split()[-1], 16) for line in lines if line.startswith("PATTERN "))
    assert len(oam) == 256 and len(pattern) == 8192
    counts = []
    for transparent_rows in (True, False):
        previous = [None] * 8
        fragments = 0
        for y in range(8, 232):
            rank = 0
            for i in range(0, len(oam), 4):
                top, tile, attr, x = oam[i:i + 4]
                row = y - top - 1
                if not 0 <= row < 16:
                    continue
                slot = rank
                rank += 1
                if slot == 8:
                    break
                if attr & 128:
                    row = 15 - row
                tag = (tile & 1) * 256 + (tile & 254) + row // 8
                address = tag * 16 + row % 8
                if not transparent_rows and not (pattern[address] | pattern[address + 8]):
                    continue
                key = (tag, x, attr, y - (7 - row % 8 if attr & 128 else row % 8))
                if key != previous[slot]:
                    previous[slot] = key
                    fragments += 1
        counts.append(fragments)
    assert counts == [138, 85], counts
    return counts


def main():
    counts = title_fragments()
    log = OUT / "title-fix/resume-1-vsim.log"
    checked_sim(log, "PASS opening capture trace")
    frames = list(captured(log))
    assert [f for f, data in frames] == list(range(19, 24))
    plans = {}
    for mode in ("debug", "release"):
        plans[mode] = check(OUT / mode / "link/src", [], frames, fold_backdrop=True, board=0x85)
        assert all(v["objects"] == 85 and v["raw_lines"] == 1 for v in plans[mode].values()), plans[mode]
    result = dict(plans=plans, reference_frame=60, reference_colors=11, rank_fragments=counts,
                  validated_capture_fields=[f for f, data in frames], arm_links=["debug", "release"])
    (OUT / "title-planner.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
