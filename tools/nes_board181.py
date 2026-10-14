# SPDX-License-Identifier: MIT
"""Isolated board/MCU integration of the already verified paired181 sources.

This prepares compile candidates, never an installable firmware package.
The180 pins are checked before copying and all other input bytes are retained.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace
from nes_client181 import build

RTL=['nes_patch_rows181.sv','nes_patch_capture181.sv','nes_native_compact181.sv',
     'nes_native_raster181.sv','nes_native_frame181.sv','nes_native_export181.sv']
MCU=['nes_native181.c','nes_native181.h','nes_native_video181.c',
     'nes_native_video181.h','nes_native_sink181.c']

def copy_pins(prior,out,pins):
    assert not out.exists(),out
    out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((prior/n).read_bytes())

def board(prior,out,client,shared_previous=False):
    assert str(out).isascii(), 'Quartus input directory must be ASCII'
    pins=json.loads((ROOT/'analysis/minreject180-verification.json').read_bytes())['verification']['sources']
    copy_pins(prior,out,pins)
    p=out/'nes_live_joint.sv';s=p.read_text()
    s=replace(s,'nes_native_frame165 native_frame(',
        'wire [2:0] native_patch_count181;\nnes_native_frame181 native_frame(')
    s=replace(s,'.scanline(scanline),.dot(cycle),.bg_low(native_bg_low)',
        '.color(color),.emphasis(emphasis),.patch_count(native_patch_count181),.patch_errors(),\n .scanline(scanline),.dot(cycle),.bg_low(native_bg_low)')
    s=replace(s,'nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(',
        'nes_native_export181 #(.MAX_CYCLES(33554432)) native_export(\n .patch_count(native_patch_count181),')
    p.write_text(s,encoding='utf8',newline='\n')
    # Leave the fill/core arbitration/query mux/CDC/mailbox and clocks intact.
    q=out/'board.qsf';s=q.read_text()
    for old in ['nes_native_frame165.sv','nes_native_export165.sv']:
        s=replace(s,'set_global_assignment -name SYSTEMVERILOG_FILE '+old+'\n','')
    for n in RTL:
        (out/n).write_bytes((ROOT/'src/nes/video'/n).read_bytes())
        s+='set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n'
    if shared_previous:
        from nes_board181_area import compact
        p=out/'nes_native_compact181.sv'
        p.write_text(compact(p.read_text()),encoding='utf8',newline='\n')
    q.write_text(s,encoding='utf8',newline='\n')
    b=build(client)
    assert (client/'body.bin').stat().st_size==3768
    (out/'sink-program.hex').write_bytes((client/'sink-program.hex').read_bytes())
    names=list(pins)+RTL
    changed=[n for n in pins if sha(out/n)!=pins[n]]
    assert sorted(changed)==['board.qsf','nes_live_joint.sv','sink-program.hex']
    r=dict(baseline=pins,sources={n:sha(out/n) for n in names},changed=changed,
        added=RTL,client=b,wire_version='1811',sink_version='1812',hardware_package=False,
        shared_previous=shared_previous,patch_errors_observed=False,scope='Full board source integration; no synthesis, timing or physical approval yet.',
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_board181.py','tools/nes_client181.py']+['src/nes/video/'+n for n in RTL]})
    if shared_previous:r['public_sources']['tools/nes_board181_area.py']=sha(ROOT/'tools/nes_board181_area.py')
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

def mcu(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='f9a6d342e59cdc8be358f8f69afd3d7318fd6263f980b84e42573e3f54a8fbcc'
    m=json.loads((prior/'preparation-minreject180.json').read_bytes())
    pins=m['copied']|m['changed']|m['added'];copy_pins(prior,out,pins)
    changed={}
    for n in MCU:
        dest='src/'+n.replace('181','165')
        assert dest in pins
        (out/dest).write_bytes((ROOT/'src/nes/firmware'/n).read_bytes());changed[dest]=sha(out/dest)
    labels={
        'src/nes_menu_diagnostic.c':[('NES-GAME-180','NES-GAME-181'),('NES GAME 180.nh1','NES GAME 181.nh1'),
            ('nes-game-last-180.txt','nes-game-last-181.txt'),('game180.nes','game181.nes'),('fpga_n180.bi3','fpga_n181.bi3')],
        'src/nes_checkpoint112.c':[('nes-progress-180.txt','nes-progress-181.txt'),('NES180 seq=','NES181 seq=')],
        'src/VERSION':[('NES-GAME180-DEV','NES-GAME181-DEV')]}
    for n,pairs in labels.items():
        p=out/n;s=p.read_text()
        for a,b in pairs:
            assert a in s,(n,a);s=s.replace(a,b)
        p.write_text(s,encoding='utf8',newline='\n');changed[n]=sha(p)
    r=dict(copied=pins,changed=changed,added={},wire_version='1811',sink_version='1812',hardware_package=False,
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_board181.py']+['src/nes/firmware/'+n for n in MCU]})
    for n in ['preparation-board181.json','preparation-runlease165.json']:
        (out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['board','mcu'])
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--client',type=Path);p.add_argument('--shared-previous',action='store_true');a=p.parse_args()
    r=board(a.prior,a.out,a.client,a.shared_previous) if a.kind=='board' else mcu(a.prior,a.out)
    print(json.dumps(dict(kind=a.kind,changed=r['changed'],hardware_package=False)))
