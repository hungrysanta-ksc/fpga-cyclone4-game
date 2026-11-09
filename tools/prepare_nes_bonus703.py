"""Preserve pre-sample sprite mapping and use the existing idle hint for plane1."""
import argparse,json,shutil
from pathlib import Path
from nes_game147 import sha

def prepare(base,out):
    m=json.loads((base/'inputs699.json').read_text());pins={n:m['changed'].get(n,h) for n,h in m['base'].items()}
    out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(base/n)==h;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    p=out/'rtl/ppu.sv';s=p.read_text()
    s=s.replace('output wire sprite_preview699,','output wire sprite_preview699,sprite_high703,')
    a=s.index('// Preview a pending CPU mapper write');b=s.index('// Only predict an upcoming background',a)
    s=s[:a]+'''// Keep the mapper preview through non-consuming read edges. At the
// actual ce/sample edge only the committed mapping is independently checked.
wire sprite_rom703=sprite_load_en && !vram_a[13] &&
    read_2007_delayed==0 && write_2007_delayed==0;
assign sprite_preview699=(rom_ppu_address_valid || (vram_r && !ce)) && sprite_rom703;
// While plane0 remains the live demand, offer plane1 to the existing idle-only
// hint path. Actual CPU/PPU demand retains priority; no extra request queue.
assign sprite_high703=sprite_rom703 && is_rendering_d && vram_r &&
    !ALE && cycle[2:0]==6;
'''+s[b:]
    s=s.replace('assign game147_prefetch_hint=restart160 || overlap155 || normal155;','assign game147_prefetch_hint=restart160 || overlap155 || normal155 || sprite_high703;')
    s=s.replace('assign game147_prefetch_hint=restart160 || overlap155 || normal155 || sprite_high703;', '''// Y/tile/attribute are latched by the start of count3 (dot mod8=4).
// X has no effect on the pattern address. Offer low plane during this dummy
// nametable read, before the following CPU fetch can occupy the reader.
wire sprite_low703=sprite_load_en && is_rendering_d && cycle[2:0]==4 &&
    read_2007_delayed==0 && write_2007_delayed==0;
assign game147_prefetch_hint=restart160 || overlap155 || normal155 || sprite_high703 || sprite_low703;''')
    s=s.replace('assign game148_hint_logic=restart160 ?', '''assign game148_hint_logic=sprite_low703 ?
    {1'b0,sprite_vram_addr[12:4],1'b0,sprite_vram_addr[2:0]} : restart160 ?''')
    p.write_text(s,encoding='utf8',newline='\n')
    p=out/'rtl/nes.v';s=p.read_text()
    s=s.replace('wire sprite_preview699;','wire sprite_preview699,sprite_high703;\nwire [21:0] mapper_preview703;')
    s=s.replace('PPU ppu(.sprite_preview699(sprite_preview699),','PPU ppu(.sprite_preview699(sprite_preview699),.sprite_high703(sprite_high703),')
    s=s.replace('.game148_hint_logic(sprite_preview699 ? chr_addr : game148_hint_logic),.game148_hint_physical(game148_hint_physical),',
                '.game148_hint_logic((sprite_preview699 || sprite_high703) ? chr_addr : game148_hint_logic),.game148_hint_physical(mapper_preview703),')
    s=s.replace('assign ppumem_addr  = sprite_preview699 ? game148_hint_physical : chr_linaddr;',
'''assign ppumem_addr  = sprite_preview699 ? mapper_preview703 : chr_linaddr;
// MMC3 CHR banks are >=1KiB aligned: plane bit3 remains an offset bit.
// The expected consumed address still comes from chr_linaddr, not this hint.
assign game148_hint_physical=sprite_high703 ?
    {mapper_preview703[21:4],1'b1,mapper_preview703[2:0]} : mapper_preview703;''')
    s=s.replace('// Only the non-consuming ALE request sees the write preview. Mapper state,', '// Only non-consuming sprite address/read edges see the preview. Mapper state,')
    p.write_text(s,encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h};assert set(changed)=={'rtl/nes.v','rtl/ppu.sv'}
    (out/'inputs703.json').write_text(json.dumps(dict(stage=703,base=pins,changed=changed,base_directory=str(base),constraints_changed=False,seed_changed=False),indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
