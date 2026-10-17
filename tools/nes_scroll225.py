# SPDX-License-Identifier: MIT
"""Rotate each compact BG row inside the existing64-column SNES map.

Physical fetch tags/row mapping/slots remain authoritative. Raster coarse X
chooses placement only; simultaneous map rotation and HOFS preserve pixels
for arbitrary coarse values, split rows and wrap. No new buffer/protocol/RTL.
"""
from pathlib import Path
import argparse,json
from nes_resident211 import ROOT,BASE,sha,once
from nes_board181 import copy_pins

def planner(s):
    s=once(s,'static bool fail(','''/* The captured line_v coarseX/NT-X select a placement, not CHR identity.
 * One placement per compact group: all its rows share the same33 words.
 * Even mid-group raster changes cannot change mapping beneath another row. */
static unsigned column225(uint64_t raster){
 return (unsigned)(raster&31u)|((unsigned)(raster>>5)&32u);
}
static bool fail(''')
    s=once(s,'p->hofs[y]=(uint16_t)((s->raster[y]>>30)&7);',
        'p->hofs[y]=(uint16_t)(column225(s->raster[first[groups-1]])*8+((s->raster[y]>>30)&7));')
    start=s.index(' /* Explicitly clear cells omitted by this generation, including shrink. */')
    end=s.index(' /* Slot0 is explicitly zero',start)
    s=s[:start]+''' /* Cold map is fully zero-initialized above. Warm offscreen cells are
  * retained, never fetched by the33-column visible window. If they become
  * visible later they are overwritten before SEAL, even after slot eviction.
  * Dirty union still updates both alternating destinations before display. */
'''+s[end:]
    s=once(s,'  unsigned at=((x/32)*1024+g*32+x%32)*2;',
        '  unsigned column=(column225(s->raster[first[g]])+x)&63u;\n  unsigned at=((column/32)*1024+g*32+column%32)*2;')
    return s

def prepare(out):
    prior=BASE/'probes/nes-ingress223/arm01'
    p=json.loads((prior/'preparation-ingress223.json').read_bytes())
    pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins)
    f=out/'src/nes_planner211.c';f.write_text(planner(f.read_text()),encoding='utf8',newline='\n')
    for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        f=out/'src'/n;f.write_text(f.read_text().replace('223','225'),encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    assert set(changed)=={'src/'+n for n in ['nes_planner211.c','nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']}
    report=dict(copied=pins,changed=changed,added={},public_sources={'tools/nes_scroll225.py':sha(Path(__file__))},
        new_fpga=False,new_snes_rom=False,new_data_state_bytes=0,physical=False)
    (out/'preparation-scroll225.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().out)['changed']))
