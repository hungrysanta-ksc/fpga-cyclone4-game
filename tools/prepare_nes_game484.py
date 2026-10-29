# SPDX-License-Identifier: MIT
"""Bounded ARM-only planner changes on the physically working482 source.

Skip a pure retained-shape classification after a same-frame exact hit, and
fully assign BG/OBJ plan fields instead of clearing40 bytes then overwriting
them. No ABI/CRC/STOP/commit, transport, FPGA or runtime allocation changes.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
BASE_SOURCES = {
    'nes_planner211.c': 'fe74952f9c40bc6a38333279f64983f6799a2dcd5d89bfff15bf5a65e93009de',
    'nes_resident211.c': 'ad217befb1d9059f6d4790810a1bb46e8a042e3cfe5597fd40cf29d71a22f3a0',
}


def transform(name, s, variant):
    if name == 'nes_planner211.c' and variant in ['init', 'both']:
        old = 'struct nes_plan191 q={0};q.generation=s->generation;q.tag=(uint16_t)(cell&8191);q.mask=255;'
        assert s.count(old) == 1
        s = s.replace(old, '''/*484 All40 ABI bytes are assigned here and in the following row/alt
   * loops. Slot is assigned again by the resident writer before emission. */
  struct nes_plan191 q;q.generation=s->generation;q.slot=0;q.tag=(uint16_t)(cell&8191);q.kind=0;q.mask=255;''')
        old = 'struct nes_plan191 q={0};q.generation=s->generation;q.tag=(uint16_t)tag;q.kind=1;q.mask=masks[e];'
        assert s.count(old) == 1
        s = s.replace(old, 'struct nes_plan191 q;q.generation=s->generation;q.slot=0;q.tag=(uint16_t)tag;q.kind=1;q.mask=masks[e];')
    if name == 'nes_resident211.c' and variant in ['late', 'both']:
        old = ''' bool retain=ordinary(q);
 uint32_t key=q->kind==2?65534u:q->tag|(kind?(uint32_t)q->mask<<13:0);
'''
        assert s.count(old) == 1
        s = s.replace(old, '')
        at = ' if(exact_slot!=stop)return exact_slot;\n'
        assert s.count(at) == 1
        s = s.replace(at, at+''' /*484 ordinary() only classifies retained-key eligibility. Its result
  * was unused on an exact hit; preserve every entry guard and miss check. */
 bool retain=ordinary(q);
 uint32_t key=q->kind==2?65534u:q->tag|(kind?(uint32_t)q->mask<<13:0);
''')
    return s


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', type=Path, required=True)
    p.add_argument('--variant', choices=['init', 'late', 'both'], default='both')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    old = json.loads((ROOT/'analysis/mmc482-verification.json').read_text(encoding='utf8'))
    assert sha(a.arm/'obj-nes-100/firmware.stm') == old['ARM']['firmware_SHA256']
    for n, h in old['ARM_patch'].items():
        assert sha(a.arm/n) == h, n
    for n, h in BASE_SOURCES.items():
        assert sha(a.arm/n) == h, n
    a.out.mkdir(parents=True, exist_ok=False)
    patch = a.out/'patch'
    patch.mkdir()
    base = {}
    for n in ['nes_planner211.c', 'nes_resident211.c']:
        q = a.arm/n
        base[n] = sha(q)
        s = q.read_text(encoding='utf8')
        changed = transform(n, s, a.variant)
        if changed != s:
            (patch/n).write_text(changed, encoding='utf8', newline='\n')
    r = {'scope': __doc__, 'variant': a.variant, 'baseline_firmware_SHA256': old['ARM']['firmware_SHA256'],
         'baseline_sources': base, 'patch_sources': {q.name: sha(q) for q in patch.iterdir()},
         'FPGA_changed': False, 'ABI_changed': False, 'new_allocation_bytes': 0,
         'deployable': False, 'hardware_verified': False}
    (a.out/'preparation.json').write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'prepared': True, 'variant': a.variant, 'patch_files': list(r['patch_sources'])}))
