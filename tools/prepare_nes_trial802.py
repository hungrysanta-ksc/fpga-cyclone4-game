"""Change user-visible edition strings in the two physically booted MMC798/799 sources."""
import re
from pathlib import Path

PROBES = Path(__file__).resolve().parents[2] / "probes"
WORK = PROBES / "nes-trial802"
EDITIONS = ((798, 802), (799, 803))


def patches():
    for parent, edition in EDITIONS:
        base = PROBES / f"nes-control798/link{parent}/src"
        dest = WORK / f"patch{edition}"
        dest.mkdir(parents=True, exist_ok=False)
        for name in ("nes_menu_diagnostic.c", "nes_checkpoint112.c", "VERSION"):
            old = (base / name).read_bytes()
            new = re.sub(rb'"[^"\r\n]*"', lambda m: m[0].replace(str(parent).encode(), str(edition).encode()), old)
            assert old != new and len(old) == len(new)
            (dest / name).write_bytes(new)


if __name__ == "__main__":
    patches()
