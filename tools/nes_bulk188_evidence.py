# SPDX-License-Identifier: MIT
"""Inventory available real-game evidence without relabeling intro as scrolling."""
from pathlib import Path
import argparse, hashlib, json, math

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    base=ROOT.parent; pins={}
    def read(p):
        data=p.read_bytes();pins[p.relative_to(base).as_posix()]=hashlib.sha256(data).hexdigest();return data
    source=base/'probes/nes-native-video165/video03'
    scenes={}
    raw={}
    for gen in (12,15):
        d=source/f'frame{gen}'
        sections={n:read(d/(n+'.bin')) for n in ('bg','obj','map','cgram','oam','hdma')}
        records=[int(x,16) for x in read(d/'records.hex').decode('ascii').split()]
        assert all(((x>>77)&0xffff)==gen for x in records)
        raw[gen]=sections
        scenes[gen]=dict(section_bytes={n:len(v) for n,v in sections.items()},
                         total_section_bytes=sum(map(len,sections.values())),
                         historical_165_record_count=len(records),
                         historical_165_record_bytes=len(records)*12)
    comparison={}
    for section,size in [('bg',16),('obj',32)]:
        old,new=raw[12][section],raw[15][section]
        assert len(old)%size==len(new)%size==0
        previous=[old[i:i+size] for i in range(0,len(old),size)]
        current=[new[i:i+size] for i in range(0,len(new),size)]
        comparison[section]=dict(pattern_bytes=size,old_slots=len(previous),new_slots=len(current),
            exact_same_slot=sum(i<len(previous) and p==previous[i] for i,p in enumerate(current)),
            exact_content_found_in_prior=sum(p in previous for p in current),
            scope='Byte equality only. Not mapper identity/CHR-RAM generation safety, new cache, or scrolling hit rate.')
    old,new=raw[12]['map'],raw[15]['map']
    assert len(old)==len(new)==4096
    comparison['map']=dict(same64B=sum(old[i:i+64]==new[i:i+64] for i in range(0,4096,64)),total64B=64)
    reference=json.loads(read(base/'probes/nes-level179/evidence/reference05/result.json'))
    r=json.loads(read(base/'probes/nes-bulk188/test02/result.json'))
    assert r['passed']
    record=dict(kind='bulk188_evidence_inventory',sources=pins,real_intro=scenes,
        intro_comparison=comparison,
        missing='No paired current-production ingress/egress for consecutive first-level scrolling in these selected archives. Do not infer it from two intro frames or synthetic7 packet fixtures.',
        level_reference=dict(frames=reference['frames'],scope=reference['scope'],
                             available='Mesen scene images and PPU register writes; not production compact/raw/CHR packet stream'),
        user_scroll_recipe=dict(level_entry='World map: move to tile marked 1, press A',
                                scroll='Hold RIGHT and B continuously; repeatedly press and release A',
                                capture_state='Not executed this turn; do not assume a fixed intro/menu timing'),
        prototype=dict(streams=r['streams'],bytes=sum(r['streams'].values()),
                       chunks=sum(math.ceil(n/2048) for n in r['streams'].values()),
                       tests=r['cases'],payload_bytes=4096,
                       resource_estimate=dict(m9k_added=4,current186_m9k=42,total_estimate=46,
                                              spare_estimate=10,scope='Arithmetic only; no synthesis/LAB/STA/port packing approval'),
                       limitations=['Host-clock local producer only; game/mapper capture and CDC not connected',
                                    'Raw SNES pin reads plus unchanged bus decoder, not actual CPU/DMA',
                                    'Consumer release frees transport chunk; final visible ACK still required',
                                    'No permanent pattern cache or measured FPS improvement']),
        next='Implement source-side immutable compact/CHR view and stable pattern/content generations with host-domain ownership. Use actual SNES client bulk reads and final display boundary. Obtain paired first-level scrolling with user RIGHT+B/A recipe; do not run a long unmodified core replay. Resource/16.7ms service budget before FIT and hardware package.',
        new_firmware=False,new_package=False,fps60=False)
    (a.out/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('sources','next')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
