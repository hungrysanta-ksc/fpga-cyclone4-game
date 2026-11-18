"""Index consecutive no-input source frames and their observed PPU buses. Keep game data local."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path
from statistics import mean

from analyze_nes_scroll229 import FETCH, WRITE
from capture_nes_mask820 import capture
from prepare_nes_geometry230 import NT, ROW
from prepare_nes_opening818 import ADVENTURE_SHA


# The first two source frames in each clip warm both output banks.
CLIPS = {"opening": 700, "transition": 1527, "demo": 2560}
STREAMS = {"nametable.bin": (NT, 0), "rows.bin": (ROW, 0),
           "ppu-fetch.bin": (FETCH, 0), "writes.bin": (WRITE, 1)}


def ids():
    return [f for start in CLIPS.values() for f in range(start - 2, start + 60)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def index(folder, dest, out):
    meta = json.loads((folder / "capture.json").read_text())
    assert meta["sampled"] == ids() and meta["rom"] == ADVENTURE_SHA and meta["exit_code"] == 0
    clocks = {}
    for line in (folder / "frames.tsv").read_text().splitlines():
        f, clock, *buttons = map(int, line.split())
        assert f == len(clocks) + 1 and len(buttons) == 4 and not any(buttons)
        clocks[f] = clock
    assert len(clocks) == 3600
    dest.mkdir(parents=True, exist_ok=False)
    for f in ids():
        d = dest / str(f)
        d.mkdir()
        (d / "capture.json").write_text(json.dumps(dict(exit_code=0, capture_first=f, capture_last=f)))
        (d / "frames.tsv").write_bytes((folder / "frames.tsv").read_bytes())
        (d / f"frame-{f:04d}.rgb").write_bytes((folder / f"frame-{f:04d}.rgb").read_bytes())
    # Separate the observation files once. Geometry230 can now validate one frame
    # at a time without scanning the other 185 captures or using their row state.
    selected = set(ids())
    outside = {}
    for name, (codec, frame_offset) in STREAMS.items():
        outside[name] = {}
        with (folder / name).open("rb") as src:
            last = None
            chunk = bytearray()
            while block := src.read(codec.size * 8192):
                assert len(block) % codec.size == 0
                for pos in range(0, len(block), codec.size):
                    frame, = struct.unpack_from("<I", block, pos + frame_offset)
                    if frame not in selected:
                        # Writes following endFrame can already carry the next source ID.
                        assert frame - 1 in selected, (name, frame)
                        outside[name][frame] = outside[name].get(frame, 0) + 1
                        continue
                    if frame != last:
                        if last is not None:
                            (dest / str(last) / name).write_bytes(chunk)
                            assert frame > last
                        chunk.clear()
                        last = frame
                    chunk.extend(block[pos:pos + codec.size])
            if last is not None:
                (dest / str(last) / name).write_bytes(chunk)
    clips = {}
    for label, start in CLIPS.items():
        frames = []
        for f in range(start - 2, start + 60):
            d = dest / str(f)
            rgb = (d / f"frame-{f:04d}.rgb").read_bytes()
            state = (folder / f"state-{f:04d}.bin").read_bytes()
            assert len(rgb) == 256*240*3 and len(state) == 2048 + 256 + 32 + 48
            counts = {}
            for name, (codec, _) in STREAMS.items():
                path = d / name
                path.touch(exist_ok=True)
                counts[name] = path.stat().st_size // codec.size
            frames.append(dict(source=f, clock=clocks[f], rgb=digest(rgb), state=digest(state),
                               records=counts, warmup=f < start))
        measured = frames[2:]
        gaps = [b["clock"] - a["clock"] for a, b in zip(frames[1:], measured)]
        assert min(gaps) > 0
        clips[label] = dict(frames=frames, mean_source_period_clocks=mean(gaps),
                           changed_RGB=sum(a["rgb"] != b["rgb"] for a, b in zip(frames[1:], measured)),
                           distinct_RGB=len({f["rgb"] for f in measured}))
    out.write_text(json.dumps(dict(rom=meta["rom"], core=meta["core"], clips=clips, outside=outside),
                              indent=2) + "\n", encoding="utf8")


def check_rgb(index_path, normal_frames):
    from PIL import Image
    report = json.loads(index_path.read_bytes())
    expected = {r["source"]:r["rgb"] for clip in report["clips"].values() for r in clip["frames"]}
    with normal_frames.open("rb") as stream:
        for frame in range(1,3601):
            size, = struct.unpack("<I", stream.read(4))
            data = stream.read(size)
            assert len(data) == size
            if frame in expected:
                with Image.open(io.BytesIO(data)) as im:
                    assert digest(im.convert("RGB").tobytes()) == expected[frame], frame
        assert not stream.read(1)
    report["independent_normal_RGB"] = dict(matched=len(expected), archive=digest(normal_frames.read_bytes()))
    index_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for cmd, names in (("capture", ("rom", "mesen", "out")), ("index", ("folder", "dest", "out")),
                       ("check-rgb", ("index_path", "normal_frames"))):
        parser = sub.add_parser(cmd)
        for name in names:
            parser.add_argument(name, type=Path)
    a = p.parse_args()
    if a.action == "capture":
        capture(a.rom.resolve(), a.mesen.resolve(), a.out.resolve(), ids())
    elif a.action == "index":
        index(a.folder, a.dest, a.out)
    else:
        check_rgb(a.index_path, a.normal_frames)
