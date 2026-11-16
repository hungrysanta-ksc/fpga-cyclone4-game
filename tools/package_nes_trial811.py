"""Qualify both final 810I links and package them with their tested MMC807/808 boards."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_order810 import compare, schedule
from package_nes_obj807 import ROOT, digest, read
from prepare_nes_trial802 import PROBES, rename_edition

WORK = PROBES / "nes-trial811"
EDITIONS = ((807, 811), (808, 812))
TIMED_CLIENT = "c79e2b013701fa9cde8a8164da3f0545f2b7c916b8477aa6d74ec405002ebf2e"
LONG_CLIENT = "ba9542fcdbdfdae9437ea8bd65f6f5d29c7fc0d2c9d0895cedbcddbaee054b2a"
POLL_LIMITS = {"811":24, "812b":56, "812c":32}


def patches():
    expected = read(ROOT / "analysis/order810-results.json")["builds"]["order810i"]
    for previous, edition in EDITIONS:
        source = PROBES / f"nes-order810i/link{previous}/src"
        assert digest((source / "obj-nes-100/firmware.stm").read_bytes()) == expected[str(previous)]["firmware"]
        rename_edition(source, WORK / f"patch{edition}", previous, edition)


def long_grant_patch(build):
    source = WORK / "link812/src/nes_native_sink165.c"
    code = source.read_bytes()
    assert code.count(b"poll<24") == 1
    output = WORK / f"patch{build}"
    output.mkdir(exist_ok=False)
    (output / source.name).write_bytes(code.replace(b"poll<24", f"poll<{POLL_LIMITS[build]}".encode()))


def qualify(edition, build, phases, fw):
    checks = WORK / f"check{build}"
    image = digest(fw)
    label = f"mmc{build}"
    source = PROBES / f"nes-order810i/link{edition-4}/src"
    final = WORK / f"link{build}/src"
    for path in source.iterdir():
        if not path.is_file() or (path.suffix not in (".c",".h",".inc",".s",".S") and path.name != "VERSION"):
            continue
        original = path.read_bytes()
        if path.name in ("VERSION","nes_menu_diagnostic.c","nes_checkpoint112.c"):
            expected = (WORK / f"patch{edition}" / path.name).read_bytes()
        elif path.name == "nes_native_sink165.c" and edition == 812:
            assert original.count(b"poll<24") == 1
            expected = original.replace(b"poll<24", f"poll<{POLL_LIMITS[build]}".encode())
        else:
            expected = original
        assert (final / path.name).read_bytes() == expected, path.name
    guard = read(checks / "guards.json")
    assert len(fw) <= 212992 and guard["candidate"] == dict(bytes=len(fw), firmware=image)
    assert guard["linked_crc_inputs"] == 265 and guard["guards"]["ACK"]["corrupt_bits"] == 152
    obj = guard["object_recovery"]
    assert obj["firmware"] == image and obj["runtime_consecutive_skips"] == 2 and obj["service_stop_pending"]
    menu = guard["guards"]["menu"]
    assert menu["firmware"] == image and menu["rows"]["normal"]["released"] == 1
    prefix = read(checks / "prefix.json")
    assert prefix["planar"]["verified_bytes"] == 2048
    stops = {case["case"]:case for case in prefix["map_grant"]}
    assert all(not stops[k]["committed"] for k in ("STOP", "bad_credit", "bad_final", "bad_progress"))
    assert stops["bad_progress"]["drains"] == POLL_LIMITS[build]+1
    mode = read(checks / "mode.json")
    if edition == 811:
        assert mode["firmware_SHA256"] == image and mode["layout"] == "trimmed" and mode["unfinished_excluded"]
        deadline = read(checks / "deadline.json")
        assert deadline["firmware"] == image and deadline["passed"]
        mode["elapsed_guard"] = {r["case"]:r["result"] for r in deadline["cases"]}
    else:
        assert mode["firmware"] == image and mode["passed"] and all(c["passed"] for c in mode["cases"])
    recovered = read(checks / "stopped.json")
    assert recovered == read(PROBES / f"nes-obj807/check{edition-4}/stopped.json")
    report = read(checks / "report.json")
    assert report["context"]["raw"] == recovered["late"]["context"]
    assert report["file"] == f"/sd2snes/nes-game-last-mmc{edition}.txt"
    recovery = {}
    for fault in ("none", "program", "done", "busy", "token"):
        case = read(checks / f"base-{fault}/result.json")
        assert case["passed"] and case["fault"] == fault and case["firmware_sha256"] == image
        assert case["safe_return"] == case["base_restored"] == int(fault == "none")
        recovery[fault] = case["safe_return"]
    names = [f"nes-{kind}-mmc{edition}.txt" for kind in ("progress","budget","game-last")]
    for name in [*names, f"fpga_mmc{edition}.bi3", f"mmc{edition}.nes"]:
        assert name.encode() in fw
    timing = {}
    for phase, rows in phases.items():
        result = rows[label]
        assert result["firmware"] == image and result["restored951"] and result["line951"] <= 246
        assert result["display959"] == 2 and result["vs807_last_ACK_ms"] < 0
        assert result["dense_vblank"] <= rows["base"]["dense_vblank"]
        if edition == 811:
            assert result["target_pass"]
        timing[phase] = {k:result[k] for k in ("start","commits","early951","line951","display959",
                         "reveal959_line","dense_vblank","dense_ms","vs807_dense_ms","last_ACK",
                         "vs807_last_ACK_ms","interval_changes_vs807","hashes")}
    return dict(bytes=len(fw), flash_free=212992-len(fw), firmware=image,
                client=TIMED_CLIENT if edition == 811 else LONG_CLIENT, grant_polls=POLL_LIMITS[build],
                phases=timing, mode=mode, OBJ=obj, bad_ACK_bits=152, verified_crc_inputs=265,
                stopped_context=report["context"]["raw"], menu_and_base=recovery, logs=names)


def package(temp, long_build):
    parent = PROBES / "nes-obj807/MMC807-60SEC-MMC808-LONG.zip"
    old = read(ROOT / "analysis/obj807-results.json")
    assert digest(parent.read_bytes()) == old["ZIP_SHA256"]
    clients = {"mmc811":TIMED_CLIENT, f"mmc{long_build}":LONG_CLIENT}
    phases = compare(temp, list(clients), clients=clients)
    other = "812b" if long_build == "812c" else "812c"
    comparison = {}
    for phase in phases:
        path = temp / f"nes-output809-mmc{other}-p{phase}"
        if (path / "joint.json").is_file():
            row = schedule(path, read(temp / f"nes-output809-base-p{phase}/joint.json"), LONG_CLIENT)
            comparison[phase] = {key:row[key] for key in ("firmware","restored951","line951","display959",
                                                              "dense_vblank","dense_ms","last_ACK","hashes")}
        else:
            comparison[phase] = dict(error=(path / "map-error.txt").read_text().split("capture.lua:")[-1],
                                     trace=digest((path / "window.csv").read_bytes()))
    original = temp / "nes-output809-mmc812-p1"
    first = schedule(original, read(temp / "nes-output809-base-p1/joint.json"), LONG_CLIENT)
    assert not first["restored951"] and first["after_map951_E0"] == 25
    failed = temp / "nes-output809-mmc812-p2"
    error = (failed / "map-error.txt").read_text()
    assert "assertion failed" in error and not (failed / "joint.json").exists()
    beam = read(temp / "nes-trial812-beam960/beam.json")
    assert beam["g"] == 960 and beam["sampled_line"] > 252
    rejected = dict(firmware=first["firmware"], phase1_early951=first["early951"],
                    phase1_E0=first["after_map951_E0"], phase1_trace=first["hashes"],
                    phase2_last_event=(failed / "window.csv").read_text().splitlines()[-1],
                    phase2_oracle_error=error.split("capture.lua:")[-1], phase2_beam=beam,
                    phase2_trace=digest((failed / "window.csv").read_bytes()))
    manual_exit = read(temp / f"nes-trial{long_build}-key/result.json")
    assert manual_exit["passed"] and manual_exit["CPU"] == LONG_CLIENT
    assert {r["mode"] for r in manual_exit["cases"] if r["passed"]} == {"packet","dma"}
    files = {"README-KO.txt":(ROOT / "docs/nes-mmc811-812-trial.ko.md").read_bytes()}
    evidence = {}
    with ZipFile(parent) as prior:
        for previous, edition in EDITIONS:
            build = "811" if edition == 811 else long_build
            fw = (WORK / f"link{build}/src/obj-nes-100/firmware.stm").read_bytes()
            evidence[edition] = qualify(edition, build, phases, fw)
            directory = f"01-MMC{previous}-60SEC-SD-ROOT/" if edition == 811 else f"02-MMC{previous}-LONG-SD-ROOT/"
            members = [name for name in prior.namelist() if name.startswith(directory)]
            assert len(members) == 10
            for name in members:
                data = prior.read(name)
                assert digest(data) == old["files"][name]
                if name.endswith("/firmware.stm"):
                    data = fw
                elif name.endswith("/ROM-NOT-INCLUDED.txt"):
                    data = data.replace(str(previous).encode(), str(edition).encode())
                files[name.replace(str(previous), str(edition))] = data
    assert not any("restore" in name.lower() or name.lower().endswith(".nes") for name in files)
    proof = dict(parent_ZIP_SHA256=old["ZIP_SHA256"], physical_test=False, variants=evidence,
                 rejected_long_24=rejected, comparison=dict(build=other,phases=comparison), manual_exit=manual_exit,
                 files={k:digest(v) for k,v in files.items()})
    files["manifest.json"] = (json.dumps(proof, indent=2) + "\n").encode()
    output = WORK / "MMC811-60SEC-MMC812-LONG.zip"
    with ZipFile(output, "x", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            member = ZipInfo(name)
            member.create_system = 0
            member.external_attr = 0x20
            archive.writestr(member, data, compress_type=ZIP_DEFLATED)
    with ZipFile(output) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(files)
        assert all(archive.read(name) == data for name,data in files.items())
    proof["ZIP_SHA256"] = digest(output.read_bytes())
    (ROOT / "analysis/trial811-package.json").write_text(json.dumps(proof, indent=2) + "\n", newline="\n")
    print(output, proof["ZIP_SHA256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("patch", "long-grant-patch", "package"))
    parser.add_argument("--build", choices=("812b","812c"), default="812c")
    parser.add_argument("--temp", type=Path)
    args = parser.parse_args()
    if args.action == "patch":
        patches()
    elif args.action == "long-grant-patch":
        long_grant_patch(args.build)
    elif args.temp:
        package(args.temp, args.build)
    else:
        parser.error("package requires --temp pointing to the four replay directories")
