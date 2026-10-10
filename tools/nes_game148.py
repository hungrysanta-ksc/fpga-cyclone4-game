# SPDX-License-Identifier: MIT
"""Mapper-aware PPUDATA speculation for the actual SMB3 deadline failure.

Keeps147 frozen sources intact. Uses the current bus byte with the NEXT
background pattern address and the existing MMC3 bank registers. No future
ROM data, second mapper state, IRQ input change, or relaxed sample deadline.
"""
import difflib, json
import nes_game147 as previous
from nes_game147 import sha

prepare147 = previous.prepare

def prepare(baseline, rom, out, prefetch=False):
    assert prefetch, '148 requires --prefetch; use147 for the original control'
    meta = prepare147(baseline, rom, out, True)
    patches = []
    def edit(name, replacements):
        p = out/name
        old = new = p.read_text()
        for before, after, count in replacements:
            assert new.count(before) == count, (name, before, new.count(before))
            new = new.replace(before, after)
        p.write_text(new, encoding='utf8', newline='\n')
        patches.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                       fromfile='147/'+name, tofile='148/'+name))
    edit('rtl/ppu.sv', [
        ('output wire rom_ppu_address_valid,game147_prefetch_hint,',
         'output wire [13:0] game148_hint_logic,\noutput wire rom_ppu_address_valid,game147_prefetch_hint,', 1),
        ('assign game147_prefetch_hint=read_2007_delayed[3] && vram_r && !ALE;',
         '''// Only predict an upcoming background pattern phase. The overlap
// causes the captured current bus data to become the next address low byte.
assign game147_prefetch_hint=read_2007_delayed[3] && vram_r && !ALE &&
    is_rendering_d && !sprite_load_en && cycle<336 &&
    (cycle[2:0]==4 || cycle[2:0]==6);
assign game148_hint_logic={1'b0,bg_patt1,bg_name_table[7:4],vram_din};''', 1)])
    for n in ['rtl/nes.v', 'nes_probe.sv']:
        edit(n, [('output wire rom_cpu_address_valid,rom_ppu_address_valid,game147_prefetch_hint,',
                  'output wire [21:0] game148_hint_physical,\noutput wire rom_cpu_address_valid,rom_ppu_address_valid,game147_prefetch_hint,', 1)])
    edit('nes_probe.sv', [('.game147_prefetch_hint(game147_prefetch_hint),',
                          '.game147_prefetch_hint(game147_prefetch_hint),.game148_hint_physical(game148_hint_physical),', 1)])
    edit('rtl/nes.v', [
        ('PPU ppu(', 'wire [13:0] game148_hint_logic;\nPPU ppu(', 1),
        ('.game147_prefetch_hint(game147_prefetch_hint),',
         '.game147_prefetch_hint(game147_prefetch_hint),.game148_hint_logic(game148_hint_logic),', 1),
        ('cart_top multi_mapper (',
         'cart_top multi_mapper (\n .game148_hint_logic(game148_hint_logic),.game148_hint_physical(game148_hint_physical),', 1)])
    edit('cart_nrom.sv', [
        ('module cart_top(', 'module cart_top(\n input [13:0] game148_hint_logic,\n output [21:0] game148_hint_physical,', 1),
        ('wire [21:0] mp,mc;', 'wire [18:0] game148_chr_offset;\nassign game148_hint_physical=22\'h200000 | ({3\'d0,game148_chr_offset} & {2\'d0,chr_mask});\nwire [21:0] mp,mc;', 1),
        ('MMC3 mapper(', 'MMC3 mapper(.game148_hint_logic(game148_hint_logic),.game148_chr_offset(game148_chr_offset),', 1),
        ('module MMC3 (', 'module MMC3 (\n input [13:0] game148_hint_logic,\n output [18:0] game148_chr_offset,', 1),
        ('assign use_chr_ain_12 =', '''// Pure mapper4 lookup using the SAME bank registers as normal accesses.
// This port never drives chr_ain/chr_read, so it cannot clock the IRQ filter.
reg [8:0] game148_bank;
always @* begin
 case ({game148_hint_logic[12] ^ chr_a12_invert,game148_hint_logic[11:10]})
  3'b000,3'b001:game148_bank={chr_bank_0,game148_hint_logic[10]};
  3'b010,3'b011:game148_bank={chr_bank_1,game148_hint_logic[10]};
  3'b100:game148_bank={1'b0,chr_bank_2};
  3'b101:game148_bank={1'b0,chr_bank_3};
  3'b110:game148_bank={1'b0,chr_bank_4};
  3'b111:game148_bank={1'b0,chr_bank_5};
 endcase
end
assign game148_chr_offset={game148_bank,game148_hint_logic[9:0]};
assign use_chr_ain_12 =''', 1)])
    edit('game147_tb.sv', [
        ('wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint;',
         'wire [21:0] game148_hint_physical;\nwire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint;', 1),
        ('.ppu_prefetch_valid(game147_prefetch_hint && rom_ppu_valid),.ppu_prefetch_address({ppumem_addr[21:8],external_ppu_data}),',
         ".ppu_prefetch_valid(game147_prefetch_hint && (rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),", 1)])
    (out/'prefetch148.diff').write_text(''.join(patches), encoding='utf8', newline='\n')
    meta.update(candidate='NES-GAME-148', mapper_aware_hint=True,
                sources={n:sha(out/n) for n in meta['sources']})
    (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8',newline='\n')
    return meta

if __name__ == '__main__':
    previous.prepare = prepare
    previous.main()
