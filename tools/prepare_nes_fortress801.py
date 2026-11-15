"""Keep the 800B netlist and tighten only the two failing 168-to-84 MHz setup paths."""
import argparse
import re
import shutil
from pathlib import Path

PAIRS = (
    ("nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed",
     "nes_screen_status151:screen_status|drive_sync[0]"),
    ("nes_live_joint:core|nes_domain_reset124:diagnostic_release|release_reset[1]",
     "nes_sink_bridge165:sink|nes_sink_spi165:endpoint|snapshot[131]"),
)


def loader_locations(backannotated):
    # C shortened the loader-enable hop from 1.989 ns to 0.493 ns.
    # Reuse that small counter/enable cluster, leaving other cells free.
    prefix = PAIRS[0][0].rsplit("|",1)[0] + "|nes_rom_loader:loader|"
    moves = []
    for line in backannotated.splitlines():
        m = re.fullmatch(r'set_location_assignment (?:FF|LCCOMB)_X\d+_Y\d+_N\d+ -to "([^"]+)"', line)
        if not m:
            continue
        name = m[1]
        if name == PAIRS[0][0] or (name.startswith(prefix) and
                name[len(prefix):].startswith(("remaining","phase_step","terminal","to_idle~0"))):
            moves.append(line)
    if len(moves) < 20:
        raise ValueError("missing placed loader counter/enable locations")
    return "\n" + "\n".join(moves) + "\n"


def prepare(base, dest, readback=False, remaining=False, route=False, locations=None, margin=False):
    if dest.exists() or base.resolve() in dest.resolve().parents:
        raise ValueError("use a fresh sibling project directory")
    shutil.copytree(base, dest)
    if route:
        # At full LAB occupancy the failing C path includes a 1.968 ns
        # interconnect hop. Let the router spend longer on the same placement.
        with (dest/"board.qsf").open("a", newline="\n") as out:
            out.write("\nset_global_assignment -name ROUTER_EFFORT_MULTIPLIER 2.0\n")
    if locations:
        with (dest/"board.qsf").open("a", newline="\n") as out:
            out.write(loader_locations(locations.read_text()))
    sdc = dest / "board.sdc"
    with sdc.open("a", newline="\n") as out:
        out.write("\n# 801 fitter budgets for the two measured 5.952 ns transfers.\n")
        if margin:
            # Close the entire pair of affected clock domains together.
            out.write("""set mem801 [get_clocks {core|pll|altpll_component|auto_generated|pll1|clk[1]}]
set host801 [get_clocks {core|pll|altpll_component|auto_generated|pll1|clk[0]}]
foreach dest801 [list $host801 $mem801] {
 if {[get_collection_size $mem801]!=1 || [get_collection_size $dest801]!=1} {error "missing 801 clock"}
 set_clock_uncertainty -add -setup -from $mem801 -to $dest801 0.450
}
""")
        for src, dst in PAIRS:
            out.write("set_max_delay 5.35 -from [cdc181_exact {" + src + "}]"
                      " -to [cdc181_exact {" + dst + "}]\n")
        if readback:
            # 801A moved the critical path to the existing loader readback enable.
            for source in (17, 18):
                for target in (5, 14):
                    src = f"nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|check_next[{source}]"
                    dst = f"nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|check_response_address[{target}]"
                    out.write("set_max_delay 5.25 -from [cdc181_exact {" + src + "}]"
                              " -to [cdc181_exact {" + dst + "}]\n")
        if remaining:
            # B closed both original paths. Three bits of the loader count
            # then missed their original memory-clock edge by 63 ps.
            for bit in (0, 3, 5):
                dst = f"nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|remaining[{bit}]"
                out.write("set_max_delay 5.40 -from [cdc181_exact {" + PAIRS[0][0] + "}]"
                          " -to [cdc181_exact {" + dst + "}]\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--readback", action="store_true")
    ap.add_argument("--remaining", action="store_true")
    ap.add_argument("--route", action="store_true")
    ap.add_argument("--locations", type=Path)
    ap.add_argument("--margin", action="store_true")
    args = ap.parse_args()
    prepare(args.base, args.dest, args.readback, args.remaining, args.route, args.locations, args.margin)
