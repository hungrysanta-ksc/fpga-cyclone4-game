"""Pin694 inputs, preview only sprite ALE requests; committed sample tags remain.

No mapper register, clock, IRQ, reader latency, STOP or ACK modification.
"""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import sha

def prepare(base,out):
    m=json.loads((base/'inputs694.json').read_text())
    pins={n:m['changed'].get(n,h) for n,h in m['base'].items()}
    out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(base/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    p=out/'rtl/ppu.sv';s=p.read_text()
    assert s.count('output wire rom_ppu_address_valid')==1
    s=s.replace('output wire rom_ppu_address_valid','output wire sprite_preview699,\noutput wire rom_ppu_address_valid')
    s=s.replace('assign rom_ppu_address_valid=ALE && !vram_w;', '''assign rom_ppu_address_valid=ALE && !vram_w;
// Preview a pending CPU mapper write only while the sprite address is being
// offered. The later read/sample still uses the committed physical tag.
assign sprite_preview699=rom_ppu_address_valid && sprite_load_en &&
    !vram_a[13] && read_2007_delayed==0 && write_2007_delayed==0;''')
    p.write_text(s,encoding='utf8',newline='\n')
    p=out/'rtl/nes.v';s=p.read_text()
    s=s.replace('wire [13:0] game148_hint_logic;', 'wire [13:0] game148_hint_logic;\nwire sprite_preview699;')
    s=s.replace('PPU ppu(', 'PPU ppu(.sprite_preview699(sprite_preview699),')
    old='.game148_hint_logic(game148_hint_logic),.game148_hint_physical(game148_hint_physical),'
    assert s.count(old)==1
    s=s.replace(old,'.game148_hint_logic(sprite_preview699 ? chr_addr : game148_hint_logic),.game148_hint_physical(game148_hint_physical),')
    s=s.replace('assign ppumem_addr  = chr_linaddr;', '''// Only the non-consuming ALE request sees the write preview. Mapper state,
// A12 IRQ inputs and all consuming read phases keep their original timing.
assign ppumem_addr  = sprite_preview699 ? game148_hint_physical : chr_linaddr;''')
    p.write_text(s,encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    assert set(changed)=={'rtl/ppu.sv','rtl/nes.v'}
    result=dict(stage=699,base=pins,changed=changed,base_directory=str(base),
                constraints_changed=False,seed_changed=False,scope=__doc__)
    (out/'inputs699.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['changed']))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
