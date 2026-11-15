"""Resolve constrained register names through this board's exact MAP merge chains."""
import argparse
import re
from pathlib import Path


def bind(sdc, report):
    edges = dict(re.findall(r"^; ([^;\n]+?)\s*; Merged with ([^;\n]+?)\s*;", report, re.M))
    names = ("nes_dac162:audio|nes_release",
             "nes_live_joint:core|nes_native_mailbox165:native_prepared|dr",
             "nes_live_joint:core|nes_native_mailbox165:native_records|sr")
    def survivor(name):
        seen = set()
        while name in edges:
            if name in seen:
                raise ValueError(f"cyclic MAP merge: {name}")
            seen.add(name)
            name = edges[name]
        return name

    for bit in (0, 1):
        expected = survivor(f"{names[0]}[{bit}]")
        known = {f"{root}[{bit}]" for root in names}
        known.add(f"nes_live_joint:core|nes_direct206:direct_path|nes_domain_reset124:nrelease|release_reset[{bit}]")
        if expected not in known:
            raise ValueError(f"unexpected reset representative {expected}")
        for root in names:
            name = f"{root}[{bit}]"
            if survivor(name) != expected:
                raise ValueError(f"unexpected reset merge for {name}")
    # Some constraints use a Tcl loop to assemble the name. Include all exact
    # MAP edges; only lookups already made by the original SDC can use them.
    # Prefer a current MAP edge to a historical alias and retain strict
    # cardinality/name checks for the resolved endpoint.
    entries = ["{" + n + "} {" + survivor(n) + "}" for n in sorted(edges)
               if not any(c in n + survivor(n) for c in "{}\r\n")]
    anchor = " set r [get_registers -nowarn $name]"
    if sdc.count(anchor) != 1:
        raise ValueError("unexpected exact-register resolver")
    # Define the table once, outside the per-endpoint procedure.
    sdc = "array set ::merges800 {\n" + "\n".join(entries) + "\n}\n" + sdc
    lookup = " if {[get_collection_size $r]==0 && [info exists aliases659($name)]} {"
    if sdc.count(lookup) != 1:
        raise ValueError("unexpected alias fallback")
    direct = """ if {[get_collection_size $r]==0 && [info exists ::merges800($name)]} {
  set name $::merges800($name)
  set r [get_registers -nowarn $name]
 }"""
    sdc = sdc.replace(lookup, direct + "\n" + lookup)
    fallback = "  set name $aliases659($name)"
    return sdc.replace(fallback, fallback + "\n  if {[info exists ::merges800($name)]} {set name $::merges800($name)}")


def strip_constant_pairs(sdc, report):
    prefix = "nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|"
    for reg in ("address_hold", "check_response_address"):
        pattern = re.escape(prefix + reg + "[18..20]") + r"\s*; Stuck at GND due to stuck port data_in"
        if not re.search(pattern, report):
            raise ValueError(f"missing MAP constant evidence for {reg}")
    kept = []
    for line in sdc.splitlines(keepends=True):
        for bit in (18, 19, 20):
            pair = (" -from [cdc181_exact {" + prefix + f"address_hold[{bit}]" + "}]"
                    " -to [cdc181_exact {" + prefix + f"check_response_address[{bit}]" + "}]")
            if line.strip() in ("set_max_delay 11.904" + pair, "set_false_path -hold" + pair):
                break
        else:
            kept.append(line)
    return "".join(kept)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ("sdc", "map_report", "out"):
        ap.add_argument(arg, type=Path)
    a = ap.parse_args()
    report = a.map_report.read_text(errors="replace")
    for name in ("cdc576.sdc", "initial576.sdc"):
        source = a.sdc.with_name(name).read_text()
        a.out.with_name(name).write_text(strip_constant_pairs(source, report), newline="\n")
    a.out.write_text(bind(a.sdc.read_text(), report), newline="\n")
