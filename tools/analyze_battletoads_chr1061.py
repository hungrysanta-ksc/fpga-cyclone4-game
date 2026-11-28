"""Compare CHR copy/invalidation granularities on the same reference-game write/read trace."""
from collections import Counter
import json
import re
from prepare_dq4_movement1061 import OUT


def analyze(stage, pattern):
    frames = {}
    for line in stage.read_text().splitlines():
        if line.startswith("FRAME "):
            frame = int(line.split()[1])
            groups = frames.setdefault(frame, set())
        elif match := re.match(r"CHR group=(\d+)", line):
            groups.add(int(match[1]))
    # Mapper 7 has unbanked 8 KiB CHR RAM. The reference probe collected
    # the pattern reads only at frame 2100, and CPU CHR writes at frame%60==0.
    reads = Counter(int(line.split()[0],16)//16 for line in pattern.read_text().splitlines())
    groups = frames[2100]
    assert reads and groups and max(reads) < 512 and max(groups) < 64
    touched_pages = {g//8 for g in groups}
    precise = {t for t in reads if t//8 in groups}
    coarse = {t for t in reads if t//64 in touched_pages}
    assert precise <= coarse
    def cost(groups):
        return 512*len({g//4 for g in groups}),128*len(groups)
    samples = [cost(g) for f,g in frames.items() if 1800 <= f <= 6000 and g]
    return dict(reference_frame=2100, write_groups=sorted(groups), read_tags=len(reads),
                demand_tags_in_1KiB_dirty_pages=len(coarse), demand_tags_in_128B_dirty_groups=len(precise),
                avoidable_candidate_tags=len(coarse-precise), snapshot_bytes_at_2100=cost(groups),
                sampled_nonempty_frames=len(samples), snapshot_bytes_across_samples=[sum(v) for v in zip(*samples)])


if __name__ == "__main__":
    src=OUT.parent / "nes-carts1057"
    result=analyze(src/"stage-7.txt",src/"pattern-7.txt")
    (OUT/"battle-chr.json").write_text(json.dumps(result,indent=2))
    print(result)
