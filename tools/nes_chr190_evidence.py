# SPDX-License-Identifier: MIT
"""Bounded190 evidence and payload-only budget; no FPS or physical approval."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    selected=BASE/'probes/nes-chr190/test02'
    r=json.loads((selected/'result.json').read_bytes());assert r['passed']
    for n,h in r['source_pins'].items():
        if n.startswith(('repository-nes-milestone/','probes/')):assert sha(BASE/n)==h,n
    prior=[]
    for name in ('nes-paired186','nes-game186-hardware01','nes-video-arch187','nes-bulk188','nes-source189'):
        folder=BASE/'probes'/name;manifest=folder/'manifest01.json'
        entries=json.loads(manifest.read_bytes())
        for n,h in entries.items():assert sha(folder/n)==h,(name,n)
        prior.append(dict(name=name,files=len(entries),manifest_sha256=sha(manifest)))
    video=BASE/'probes/nes-paired186/arm01/src/nes_native_video165.c'
    code=video.read_text()
    # Existing conversion is more than a plane reorder. Pin the exact reference.
    for key in ('mapping[dest*2]','lo[e&7]','obj_slot(p,','p->hdma[at++]','p->patch.chr['):assert key in code
    budget=[]
    master=21477272  # Existing187 reference; payload-only eight-master-cycle model.
    for c in r['cases']:
        budget.append(dict(name=c['name'],old_bytes=c['old_bytes'],bytes=c['bytes'],
            reduction_percent=100*(1-c['bytes']/c['old_bytes']),
            payload_only_cart_ms=c['bytes']*8/master*1000))
    report=dict(passed=True,selected='test02',cases=r['cases'],negative_cases=r['negative_cases'],
        result_sha256=sha(selected/'result.json'),source_pins=r['source_pins'],
        current_converter_sha256=sha(video),payload_only_model=budget,
        model_exclusions=['source capture/fill','mailbox waits','DMA setup/control','conversion/slot allocation',
                          'WRAM-to-VRAM transfer and VBlank','audio/input service','display ACK'],
        decision='Batch CHR in FPGA host domain; preserve native planes and metadata. Do not migrate full geometry/row/OBJ/palette/raw conversion to65816. Evaluate metadata-plan plus FPGA tile materialization before physical integration.',
        scratch_bytes=16,aperture_bytes_reused=4096,physical_fit=False,actual_game=False,
        actual_snes_dma=False,production_decoder=False,physical_fps=False,new_package=False,
        prior_archives=prior)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(passed=True,payload_only_model=budget,prior_files=[x['files'] for x in prior]),indent=2))
if __name__=='__main__':main()
