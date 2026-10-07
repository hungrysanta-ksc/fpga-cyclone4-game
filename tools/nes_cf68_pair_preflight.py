# SPDX-License-Identifier: MIT
"""071 CF68 offline pair preparation and read-only SD backup/rollback planning.

No install or restore operation is provided. A digest supplied independently
of the package pins its manifest; CF68 is not a file identity check.
"""
from pathlib import Path
import argparse, hashlib, json, os
from build_nes_video_workloads import build

FIRMWARE_SHA = '268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499'
RBF_SHA = '45dcb3f3908b427b66f3fe52f14e56c80efae58d422af95b322580bd57f0a572'
MARKERS = ['NES VERIFY 069 80.nh1', 'NES VERIFY 069 96.nh1']
TARGETS = ['sd2snes/firmware.stm', 'sd2snes/fpga_nl8.bi3',
           'sd2snes/nes/fine_x.nes', 'sd2snes/nes/banks32.nes', *MARKERS]
RECOVERY = ['sd2snes/fpga_base.bi3', 'sd2snes/m3nu.bin']
DIAGNOSTIC_SHA = ['3daf26c8e2d0002c288efdf2ff694cdc14f0266b9cb32bb3efda8b9bf5d173df',
                  '22427da4f719a0bce2b4d8417b35a45a347e76dbcab2cbc22427ace29aa1279b']
RAW = 'reference/board.rbf'
BLOCKERS = ['external voltage/PCB/asynchronous SPI/SNES timing and lockedHIGH clock-halt limitation',
            'actual SD base/menu classification and independent backup',
            'physical programming/recovery/visibility and GBC regression']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def record(data):
    return dict(size=len(data), sha256=digest(data))

def read(root, name):
    """Reject links/junctions and traversal even on an untrusted package/SD."""
    root = Path(root).absolute()
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or ':' in name or '\\' in name:
        raise ValueError('Unsafe relative path')
    if root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
        raise ValueError('Linked root refused')
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink() or getattr(cursor, 'is_junction', lambda: False)():
            raise ValueError('Linked path refused: '+name)
    if not cursor.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escaped root')
    return cursor.read_bytes()

def write_new(root, name, data):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def save(root, name, data):
    write_new(root, name, (json.dumps(data, indent=2, ensure_ascii=False)+'\n').encode())

def encode(raw):
    """Existing firmware token format, without legacy EOF seek ambiguity."""
    out = bytearray()
    i = 0
    while i < len(raw):
        end = i+1
        while end < len(raw) and end-i < 65535 and raw[end] == raw[i]:
            end += 1
        n, value = end-i, raw[i]
        if n > 3:
            out.extend((0x5b, value, n) if n < 256 else
                       (0x77, value, n & 255, n >> 8))
        else:
            for _ in range(n):
                if value in (0x9b, 0x5b, 0x77):
                    out.append(0x9b)
                out.append(value)
        i = end
    return bytes(out)

def decode(packed):
    if not 0 < len(packed) <= 1048576:
        raise ValueError('Compressed FPGA size limit')
    out = bytearray()
    i = 0
    while i < len(packed):
        token = packed[i]
        i += 1
        value, count = token, 1
        if token in (0x9b, 0x5b, 0x77):
            needed = 1 if token == 0x9b else 2 if token == 0x5b else 3
            if i+needed > len(packed):
                raise ValueError('Truncated FPGA token')
            value = packed[i]
            i += 1
            if token != 0x9b:
                count = packed[i]
                i += 1
                if token == 0x77:
                    count |= packed[i] << 8
                    i += 1
                if not count:
                    raise ValueError('Zero FPGA run')
        if len(out)+count > 2097152:
            raise ValueError('Expanded FPGA size limit')
        out.extend(bytes([value])*count)
    return bytes(out)

def prepare(firmware, rbf, out):
    fw, raw = firmware.read_bytes(), rbf.read_bytes()
    if digest(fw) != FIRMWARE_SHA:
        raise ValueError('Unreviewed069 firmware')
    if digest(raw) != RBF_SHA:
        raise ValueError('Unreviewed068 RBF')
    if not 0 < len(raw) <= 2097152:
        raise ValueError('Raw FPGA size limit')
    packed = encode(raw)
    if decode(packed) != raw:
        raise ValueError('FPGA roundtrip mismatch')
    out.mkdir(exist_ok=False)
    files = {TARGETS[0]: fw, TARGETS[1]: packed, RAW: raw}
    for index, case in enumerate(['fine_x', 'banks32']):
        generated = out / 'generated' / case
        build(generated, case)
        files[TARGETS[index+2]] = (generated/'mmc3.nes').read_bytes()
        if digest(files[TARGETS[index+2]]) != DIAGNOSTIC_SHA[index]:
            raise ValueError('Diagnostic source changed')
    for marker in MARKERS:
        files[marker] = b''
    for name, data in files.items():
        write_new(out, ('sd-overlay/'+name) if name != RAW else name, data)
    save(out, 'pair-manifest.json', dict(candidate='NES-CF68-PAIR-071',
         firmware_identity='NES-CF68-MCU-069', fpga_identity='CF68/protocol59',
         start_enabled=False, installable=False, hardware_execution=False, clock_halt_safe=False,
         log_path="/sd2snes/nes-verify-last-069.txt", blockers=BLOCKERS,
         targets=TARGETS, recovery=RECOVERY,
         files={n:record(data) for n, data in files.items()}))
    return digest((out/'pair-manifest.json').read_bytes())

def verify(package, expected):
    data = read(package, 'pair-manifest.json')
    if digest(data) != expected:
        raise ValueError('Pair manifest digest mismatch')
    m = json.loads(data)
    if (m.get('candidate') != 'NES-CF68-PAIR-071' or m.get('installable') is not False
            or m.get('start_enabled') is not False or m.get('targets') != TARGETS
            or m.get('firmware_identity') != 'NES-CF68-MCU-069'
            or m.get('fpga_identity') != 'CF68/protocol59'
            or m.get('log_path') != '/sd2snes/nes-verify-last-069.txt'
            or m.get('hardware_execution') is not False or m.get('clock_halt_safe') is not False
            or m.get('recovery') != RECOVERY or m.get('blockers') != BLOCKERS
            or set(m.get('files', {})) != set(TARGETS+[RAW])):
        raise ValueError('Pair contract mismatch')
    contents = {}
    for name, value in m['files'].items():
        contents[name] = read(package, name if name == RAW else 'sd-overlay/'+name)
        if record(contents[name]) != value:
            raise ValueError('Pair file mismatch: '+name)
    if digest(contents[TARGETS[0]]) != FIRMWARE_SHA:
        raise ValueError('Firmware identity mismatch')
    if digest(contents[RAW]) != RBF_SHA:
        raise ValueError('FPGA identity mismatch')
    for i, expected_rom in enumerate(DIAGNOSTIC_SHA):
        if digest(contents[TARGETS[i+2]]) != expected_rom:
            raise ValueError('Diagnostic identity mismatch')
    if any(contents[n] for n in MARKERS):
        raise ValueError('Marker must be empty')
    if decode(contents[TARGETS[1]]) != contents[RAW]:
        raise ValueError('Pair roundtrip mismatch')
    return m

def state(sd, name):
    try:
        data = read(sd, name)
    except FileNotFoundError:
        return None, None
    return record(data), data

def backup(package, expected, sd, out):
    m = verify(package, expected)
    if sd.is_symlink() or getattr(sd, 'is_junction', lambda: False)():
        raise ValueError('Linked SD root refused')
    sd = sd.resolve(strict=True)
    if out.resolve().is_relative_to(sd) or out.resolve().is_relative_to(package.resolve()):
        raise ValueError('Backup must be independent of SD and candidate')
    before = {n:state(sd, n) for n in TARGETS+RECOVERY}
    if any(before[n][0] is None for n in [TARGETS[0], *RECOVERY]):
        raise ValueError('Original firmware/base/menu required')
    # Parseable RLE is preliminary evidence only; actual base compatibility is pending.
    base = decode(before[RECOVERY[0]][1])
    if not base or not 0 < len(before[RECOVERY[1]][1]) <= 0x400200:
        raise ValueError('Recovery file preliminary size/format rejected')
    out.mkdir(exist_ok=False)
    for n, (_, data) in before.items():
        if data is not None:
            write_new(out, 'original/'+n, data)
            if record(read(out, 'original/'+n)) != before[n][0]:
                raise ValueError('Backup readback mismatch; incomplete')
    for n, (old, _) in before.items():
        if state(sd, n)[0] != old:
            raise ValueError('SD changed during backup; backup remains incomplete')
    verify(package, expected)
    save(out, 'backup-manifest.json', dict(candidate=m['candidate'], pair_sha256=expected,
         originals={n:old for n, (old, _) in before.items()}, complete=True,
         physical_install_authorized=False, menu_classification='pending actual smc_id/sgb_id',
         base_expanded=record(base)))
    return digest((out/'backup-manifest.json').read_bytes())

def rollback_plan(package, expected, sd, backup_dir, backup_sha):
    m = verify(package, expected)
    raw = read(backup_dir, 'backup-manifest.json')
    if digest(raw) != backup_sha:
        raise ValueError('Backup manifest digest mismatch')
    b = json.loads(raw)
    if (b.get('pair_sha256') != expected or b.get('complete') is not True
            or set(b.get('originals', {})) != set(TARGETS+RECOVERY)):
        raise ValueError('Backup contract mismatch')
    plan = []
    for n, old in b['originals'].items():
        if old is not None and record(read(backup_dir, 'original/'+n)) != old:
            raise ValueError('Original backup mismatch: '+n)
        current = state(sd, n)[0]
        if current == old:
            continue
        if n not in TARGETS or current != m['files'][n]:
            raise ValueError('Unknown changed SD file; refuse rollback: '+n)
        plan.append(dict(path=n, action='restore' if old is not None else 'remove-created',
                         before=current, after=old))
    return dict(read_only=True, executed=False, pair_sha256=expected,
                backup_sha256=backup_sha, actions=plan, blockers=BLOCKERS)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('prepare')
    q.add_argument('--firmware', type=Path, required=True)
    q.add_argument('--rbf', type=Path, required=True)
    q.add_argument('--out', type=Path, required=True)
    for cmd in ['verify', 'backup', 'rollback-plan']:
        q = sub.add_parser(cmd)
        q.add_argument('--package', type=Path, required=True)
        q.add_argument('--manifest-sha', required=True)
        if cmd != 'verify':
            q.add_argument('--sd-root', type=Path, required=True)
        if cmd == 'backup':
            q.add_argument('--out', type=Path, required=True)
        if cmd == 'rollback-plan':
            q.add_argument('--backup', type=Path, required=True)
            q.add_argument('--backup-sha', required=True)
    a = p.parse_args()
    if a.command == 'prepare':
        print(prepare(a.firmware, a.rbf, a.out))
    elif a.command == 'verify':
        verify(a.package, a.manifest_sha)
        print('PASS071 pair verified; physical installation blocked')
    elif a.command == 'backup':
        print(backup(a.package, a.manifest_sha, a.sd_root, a.out))
    else:
        print(json.dumps(rollback_plan(a.package, a.manifest_sha, a.sd_root,
                                      a.backup, a.backup_sha), indent=2))

if __name__ == '__main__':
    main()
