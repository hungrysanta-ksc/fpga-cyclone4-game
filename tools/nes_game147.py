# SPDX-License-Identifier: MIT
"""Run the user's exact SMB3(J) through the selected CPU/PPU/MMC3/70ns reader.

This is a core integration run, not an SD package or SNES display proof.
ROM content and rendered frames stay in the caller's private output directory.
"""
from pathlib import Path
import argparse, difflib, json, os, re, shutil, subprocess
from nes_functional import VHDL, SV, sha

ROOT = Path(__file__).resolve().parents[1]
ROM_SHA = 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
EXTRA = ['cart_nrom.sv', 'nes_probe.sv', 'nes_local_memory.sv',
         'nes_rom_service.sv', 'nes_rom_physical.sv', 'nes_domain_reset124.sv']
ROM_PATH = ['nes_rom_loader.sv', 'nes_rom_boot.sv', 'nes_rom_spi.sv', 'nes_spi_boot.sv']

def prepare(baseline, rom, out, prefetch=False):
    assert not out.exists() and str(out).isascii()
    image = rom.read_bytes()
    assert sha(rom) == ROM_SHA, 'Wrong target ROM; no filename-only identification'
    assert len(image) == 16 + 0x40000 + 0x20000
    assert image[:4] == b'NES\x1a' and image[4:6] == bytes([16, 16])
    assert ((image[6] >> 4) | (image[7] & 0xf0)) == 4 and not (image[6] & 4)
    e = baseline / 'nes-display146/evidence'
    assert sha(e/'manifest.json') == json.loads((ROOT/'analysis/screen146-verification.json').read_bytes())['manifest_sha256']
    pins = json.loads((e/'manifest.json').read_bytes())['files']
    out.mkdir(parents=True)
    inputs = {}
    for n in VHDL + SV + EXTRA + ROM_PATH:
        assert sha(e/'fit'/n) == pins['fit/'+n], n
        dest = out/n; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(e/'fit'/n, dest); inputs[n] = sha(dest)
    patches = []
    def edit(name, replacements):
        p = out/name; old = p.read_text(); new = old
        for a,b,count in replacements:
            assert new.count(a) == count, (name,a,new.count(a),count)
            new = new.replace(a,b)
        p.write_text(new, encoding='utf8', newline='\n')
        patches.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='146/'+name,tofile='147/'+name))
    edit('nes_probe.sv', [("21'h00ffff", "21'h03ffff", 1),
                          ("chr_32k?20'h07fff:20'h03fff", "20'h1ffff", 1)])
    # Physical tags MUST retain the newly enabled bank bits; changing only the
    # range comparators would silently reuse another bank's cached bytes.
    edit('nes_rom_service.sv', [
        ('64KiB PRG + up to32KiB CHR', '256KiB PRG +128KiB CHR (fixed SMB3 target)', 1),
        ("25'h10000", "25'h40000", 1), ("22'h208000", "22'h220000", 1),
        ('[14:0]', '[16:0]', 6), ('[12:0] cpu_line_tag', '[14:0] cpu_line_tag', 1),
        ('[15:0] cpu_tag', '[17:0] cpu_tag', 1),
        ('[15:3]', '[17:3]', 2), ('pending_address[15:0]', 'pending_address[17:0]', 1)])
    edit('nes_rom_loader.sv', [
        ('diagnostic64KiB PRG +16/32KiB CHR', 'SMB3 fixed256KiB PRG +128KiB CHR', 1),
        ('[16:0] loaded_bytes', '[18:0] loaded_bytes', 1),
        ("wire [16:0] total=chr32?17'h18000:17'h14000;", "wire [18:0] total=19'h60000;", 1),
        ("loaded_bytes[16]?22'h200000+{6'd0,loaded_bytes[15:0]}:{6'd0,loaded_bytes[15:0]}",
         "loaded_bytes[18]?22'h200000+{4'd0,loaded_bytes[17:0]}:{3'd0,loaded_bytes}", 1)])
    edit('nes_rom_boot.sv', [
        ('[16:0]', '[18:0]', 3),
        ("(rom_chr32 ? 17'h18000 : 17'h14000)", "19'h60000", 1),
        ("check_address[16] ?\n     {1'b1,5'b0,check_address[15:0]} : {6'b0,check_address[15:0]}",
         "check_address[18] ?\n     {1'b1,3'b0,check_address[17:0]} : {3'b0,check_address}", 1),
        ('{raw_check_address[21],raw_check_address[15:0]}', '{raw_check_address[21],raw_check_address[17:0]}', 1)])
    edit('nes_rom_spi.sv', [
        ('[16:0]', '[18:0]', 4), ('[16:8]', '[18:8]', 2),
        ("7'd0,", "5'd0,", 5),
        ('(command==8\'h60)?arg>1:arg!=0', '(command==8\'h60)?arg!=2:arg!=0', 1),
        ("8'h5e", "8'h5f", 2), ('a17-bit increment', 'a19-bit increment', 1)])
    edit('nes_spi_boot.sv', [('[16:0]', '[18:0]', 2)])
    for name,data in [('prg',image[16:16+0x40000]),('chr',image[16+0x40000:])]:
        (out/(name+'.hex')).write_text(''.join(f'{v:02x}\n' for v in data),encoding='ascii')
    shutil.copy2(ROOT/'tests/nes-functional/game147_tb.sv', out/'game147_tb.sv')
    if prefetch:
        # A CPU PPUDATA read may overlap rendering ALE one dot later. The PPU
        # then latches its prior bus data as address low bits. Speculate only
        # with already validated current data; actual addresses still own tags.
        edit('rtl/ppu.sv', [
            ('output wire rom_ppu_address_valid,', 'output wire rom_ppu_address_valid,game147_prefetch_hint,', 1),
            ('assign rom_ppu_address_valid=ALE && !vram_w;',
             'assign rom_ppu_address_valid=ALE && !vram_w;\nassign game147_prefetch_hint=read_2007_delayed[3] && vram_r && !ALE;', 1)])
        for n in ['rtl/nes.v','nes_probe.sv']:
            edit(n, [
                ('output wire rom_cpu_address_valid,rom_ppu_address_valid,',
                 'output wire rom_cpu_address_valid,rom_ppu_address_valid,game147_prefetch_hint,', 1),
                ('.rom_ppu_address_valid(rom_ppu_address_valid),',
                 '.rom_ppu_address_valid(rom_ppu_address_valid),.game147_prefetch_hint(game147_prefetch_hint),', 1)])
        edit('nes_rom_service.sv', [
            ('input wire clk,reset,', 'input wire clk,reset,\n input wire ppu_prefetch_valid,input wire [21:0] ppu_prefetch_address,', 1),
            ('// Never steal or abort a read already accepted by the backend.', '''//147 Idle-slot speculation. A misprediction can only fill an immutable
 // physical-address-tagged cache entry. Actual demand wins; no read abort,
 // relaxed sampling deadline or CPU/PPU clock stretching is introduced.
 wire prefetch_hit=(ppu_cached && ppu_tag==ppu_prefetch_address[16:0]) ||
                   (ppu_previous_cached && ppu_previous_tag==ppu_prefetch_address[16:0]);
 wire prefetch_need=ppu_prefetch_valid && ppu_prefetch_address>=22'h200000 &&
   ppu_prefetch_address<22'h220000 && !prefetch_hit;
 wire use_prefetch=!ppu_need && !cpu_need && prefetch_need;
 // Never steal or abort a read already accepted by the backend.''', 1),
            ('(ppu_need || cpu_need);', '(ppu_need || cpu_need || use_prefetch);', 1),
            ('(choose_ppu?ppumem_addr:cpumem_addr[21:0])',
             '(use_prefetch?ppu_prefetch_address:(choose_ppu?ppumem_addr:cpumem_addr[21:0]))', 1),
            ('pending_ppu<=choose_ppu;', 'pending_ppu<=choose_ppu || use_prefetch;', 1)])
        edit('game147_tb.sv', [
            ('wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;',
             'wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint;', 1),
            ('.clk(clk),.reset(reset),.cpu_address_valid',
             '.ppu_prefetch_valid(game147_prefetch_hint && rom_ppu_valid),.ppu_prefetch_address({ppumem_addr[21:8],external_ppu_data}),\n .clk(clk),.reset(reset),.cpu_address_valid', 1)])
    (out/'geometry.diff').write_text(''.join(patches), encoding='utf8')
    meta = dict(candidate='NES-GAME-147', rom_sha256=ROM_SHA, mapper=4,
                prg_bytes=0x40000, chr_bytes=0x20000, inputs=inputs,
                sources={n:sha(out/n) for n in VHDL+SV+EXTRA+ROM_PATH+['game147_tb.sv']},
                passed=False, prefetch=prefetch, physical_test=False, sd_package=False,
                scope='Actual target ROM CPU/PPU/MMC3/local RAM and READ16/168MHz at modeled70ns. Memory preloaded in testbench. No MCU loader, SNES display, pad wiring, audio output, placement or physical timing claim.')
    (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--frames',type=int,default=120)
    p.add_argument('--prefetch',action='store_true')
    a=p.parse_args(); assert 2 <= a.frames <= 1200
    assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
    meta=prepare(a.baseline,a.rom,a.out,a.prefetch)
    def run(exe,args,log):
        with (a.out/log).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
        s=(a.out/log).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2500:])
        return s
    run('vlib',['work'],'vlib.log')
    for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}.log')
    run('vlog',['-sv','-mfcu',*SV,*EXTRA,'game147_tb.sv'],'vlog.log')
    s=run('vsim',['-c','work.game147_tb',f'+FRAMES={a.frames}','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation.log')
    assert 'PASS GAME147' in s
    meta.update(passed=True,frames=a.frames,simulation_log_sha256=sha(a.out/'simulation.log'))
    (a.out/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(s[-3000:],flush=True)

if __name__=='__main__':main()
