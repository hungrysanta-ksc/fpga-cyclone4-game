"""Build the MMC813 map-grant control or its independent warm raw-row consumer."""
import argparse
import json
from pathlib import Path

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from nes_rom636 import build

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"
ORIGIN = 0x7e2000


def arm(out):
    source = PROBES / "nes-prefix813/link813/src"
    reference = json.loads((ROOT / "analysis/prefix813-results.json").read_bytes())
    assert sha(source / "obj-nes-100/firmware.stm") == reference["builds"]["813"]["firmware"]
    name = "nes_native_sink165.c"
    out.mkdir(parents=True, exist_ok=False)
    (out / name).write_bytes(once((source / name).read_text(), "poll<24", "poll<32").encode())


def client(out):
    parent = PROBES / "nes-complete685/client01"
    info = json.loads((parent / "build.json").read_bytes())
    labels = json.loads((parent / "labels.json").read_bytes())
    body = bytearray((parent / "body.bin").read_bytes())
    assert sha(parent / "sink165.sfc") == "c79e2b013701fa9cde8a8164da3f0545f2b7c916b8477aa6d74ec405002ebf2e"
    # CPY sets both C and Z; branch below $15 to generic and dispatch the
    # remaining masks at pairs624. A still holds the checked destination.
    offset = labels["raw_dma489"] - ORIGIN
    assert body[offset:offset + 7] == bytes.fromhex("a4 78 c0 15 00 d0 03")
    body[offset + 5] = 0x90
    c = Code(labels["pairs624"])
    c.labels.update({k:v for k,v in labels.items() if not k.startswith("row624_")})
    c.branch(0xf0, "warm815")
    c.emit(0xc0, 0x1d, 0)
    c.branch(0xf0, "warm815")
    c.jump("generic624")
    c.label("warm815")
    c.emit(0x4a, 0x85, 0x76)  # word destination, $2800 or $4800
    for reg, value in ((0x4300, 0x1801), (0x4304, 0x007f)):
        c.emit(0xa9); c.word(value); c.absolute(0x8d, reg)
    c.emit(0xe2, 0x20); c.store(0x2115, 0x81); c.emit(0xc2, 0x20)
    c.emit(0xa2, 64, 0)  # service preserves X/Y; caller restores descriptor X.
    for pair in range(3):
        c.label(f"row624_{pair}")
        call(c, "service")
        c.branch(0xd0, "stop815")
        if pair == 1:
            c.emit(0xc0, 0x1d, 0)
            c.branch(0xf0, "row624_2")
        # The WRAM bank offset is $0000 or $8000. Neither base overlaps
        # the row's offset bits. Keep every remaining 64B MDMA separate.
        for source, dest, mask in ((0x1020,0x4302,0x69a1+128*pair),
                                   (0x76,0x2116,1+8*pair)):
            if source == 0x76:
                c.emit(0xa5, source)
            else:
                c.absolute(0xad, source)
            c.emit(0x09); c.word(mask); c.absolute(0x8d, dest)
        c.absolute(0x8e, 0x4305)
        c.emit(0xe2, 0x20); c.store(0x420b, 1); c.emit(0xc2, 0x20)
    c.emit(0x64, 0x78); c.jump("raw_return489")
    c.label("stop815"); c.jump("raw_stop489")
    replacement = c.finish()
    start, end = (labels[k]-ORIGIN for k in ("pairs624", "raw_boot489"))
    assert len(replacement) <= end-start
    body[start:end] = replacement.ljust(end-start, b"\xea")
    # The original packed loader still verifies every expanded WRAM byte.
    base = PROBES / "nes-reuse635/client04"
    build(base, out, edit_body=lambda _body,_labels: bytes(body), allow_extension=True)
    packed = json.loads((out / "build.json").read_bytes())
    info.update({k:packed[k] for k in ("physical_ROM_B","body_bytes","program_bytes","loader_B",
                        "prefix_B","encoded_B","physical_free_B","verify_entry","boot_error")})
    info.update(candidate="raw815", warm_row_masks=[0x15, 0x1d])
    (out / "build.json").write_text(json.dumps(info,indent=2)+"\n")
    (out / "labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("arm","client"))
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    (arm if args.mode == "arm" else client)(args.out)
