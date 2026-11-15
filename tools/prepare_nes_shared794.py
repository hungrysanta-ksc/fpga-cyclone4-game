"""Carry the PR160 eGBC loader into the two MMC792/793 ARM build trees."""
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GBC = ROOT / "src/firmware-overlay/src"


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"unexpected source around {old!r}")
    return source.replace(old, new)


def prepare(source, output, previous, current):
    output.mkdir(parents=True, exist_ok=False)
    for name in ("sgb.h", "sgb.c"):
        (output / name).write_bytes((GBC / name).read_bytes())
    start = "static uint8_t gbc_copy_duplex("
    end = "uint32_t load_rom("
    def gbc_section(text):
        return text[text.index(start):text.index(end, text.index(start))]
    memory = (source / "memory.c").read_text()
    merged = replace_once(memory, gbc_section(memory), gbc_section((GBC / "memory.c").read_text()))
    (output / "memory.c").write_text(merged, newline="\n")
    make = (source / "Makefile").read_text()
    (output / "Makefile").write_text(replace_once(make, "CFLAGS += $(GBC_DIAG_CFLAGS)",
        "CFLAGS += $(GBC_DIAG_CFLAGS) -DGBC_RGB774"), newline="\n")
    # Only the optional SD report is omitted when file logging is compiled out.
    name = "gbc_state_report.c"
    report = (source / name).read_text()
    (output / name).write_text(replace_once(report, "if(!gbc_file_logs_enabled)return;",
        "if(!GBC_FILE_LOGS || !gbc_file_logs_enabled)return;"), newline="\n")
    for name in ("nes_menu_diagnostic.c", "nes_checkpoint112.c", "VERSION"):
        old = (source / name).read_bytes()
        if previous.encode() not in old:
            raise ValueError(name)
        (output / name).write_bytes(old.replace(previous.encode(), current.encode()))


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=("794", "795"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    previous = str(int(args.edition) - 2)
    source = ROOT.parent / f"probes/nes-trial792/link{previous}/src"
    prepare(source, args.output, previous, args.edition)
