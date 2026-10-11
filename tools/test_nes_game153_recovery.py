# SPDX-License-Identifier: MIT
"""Actual153 MCU/FatFS/menu, modeled GPIO/card/FPGA and bitbang transport shim.

The unchanged SPI149 register engine is covered by149; this test exercises the
new typed fault through real STOP, base reload, FAT report and menu release.
The private user ROM is never copied to public source/evidence metadata.
"""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','arm','rom','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();o=a.out;e=a.baseline/'nes-display146/evidence';s=a.arm/'src'
    assert str(o).isascii() and not o.exists() and sha(a.rom)==ROM_SHA
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/screen146-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir(parents=True)
    for n,h in pins.items():
        if not n.startswith('host/') or Path(n).suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
        src=e/n;assert sha(src)==h;n=n[5:];d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,d)
    def edit(n,before,after):
        q=o/n;t=q.read_text(encoding='utf8');assert before in t,(n,before);q.write_text(t.replace(before,after),encoding='utf8',newline='\n')
    # Hardware transport adapter only; actual153 MCU source files stay exact.
    old=(o/'nes_rom_spi.c').read_text();start=old.index('bool nes_rom_spi_transfer(');end=old.index('bool nes_rom_spi_query(',start)
    shim=old[start:end].replace('nes_rom_spi_transfer','nes_game149_transfer')
    exact=['ff.c','ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c',
      'nes_cf86_session094.c','nes_cf86_session094.h','nes_h1_stm32.c','nes_h1_session.c',
      'nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','nes_checkpoint112.c','nes_run136.inc','nes_run136.h']
    for n in exact:
        (o/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s/n,o/n)
    (o/'unicode').mkdir(exist_ok=True);shutil.copy2(s/'ccsbcs.c',o/'unicode/ccsbcs.c')
    (o/'nes_game149_spi.inc').write_text('#include "nes_cf86_session094.h"\n'+shim,encoding='utf8',newline='\n')
    for n in ['host109.c','card.c','config097_card.inc']:
        for before,after in [('NES SCREEN 146','NES GAME 153'),('NES-SCREEN-146','NES-GAME-153'),
          ('NES146','NES153'),('nes-progress-146','nes-progress-153'),('nes-screen-last-146','nes-game-last-153'),
          ('screen146.nes','game153.nes'),('fpga_n146.bi3','fpga_n153.bi3')]:
            if before in (o/n).read_text():edit(n,before,after)
    edit('platform.c','rom[98320],loaded[98304]','rom[393232],loaded[393216]')
    edit('platform.c','total=tx[4]?98304:81920','assert(tx[4]==2);total=393216')
    edit('platform.c','0xd9','0xdc');edit('platform.c','0x5e','0x62')
    # Tagged PPU demand, error2. Synthetic addresses are distinguishable.
    edit('platform.c','(1ull<<62)|(1ull<<61)|(1ull<<58)|(7ull<<47)|(0x200456ull<<25)|0x8123ull','0xe200c2f430217a19ull')
    edit('platform.c','reply[6]=run_case136==18?2:1','reply[6]=run_case136==18?1:2')
    edit('platform.c','reply[2]|=2;reply[3]=1','reply[2]|=2;reply[3]=2')
    edit('host109.c','assert((ctx&0x1ffffff)==0x8123&&((ctx>>25)&0x3fffff)==0x200456&&((ctx>>47)&255)==7&&((ctx>>55)&255)==0xc8);','assert(ctx==0xe200c2f430217a19ull);')
    edit('host109.c','assert(run_case136==1||','assert(OLD153||run_case136==1||')
    edit('host109.c','printf("PASS136 terminal','assert(!OLD153 || (run_case136==3 && !stop_count && !nes_run136.context_valid));\n  printf("PASS136 terminal')
    # No unrelated legacy-load helper changes: the actual menu path is tested.
    sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']
    sources += ['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
    result={}
    for name,old_control in [('fixed153',False),('released152_condition',True)]:
        source=(s/'nes_run136.inc').read_text()
        if old_control:source=source.replace('lo[6]!=nes_run136.rom_error','(hi[3]&0x80u) || lo[6]!=nes_run136.rom_error')
        (o/'nes_run136.inc').write_text(source,encoding='utf8',newline='\n')
        exe=o/(name+'.exe')
        cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format',
          '-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.',
          '-DGBC_SAVE_G12','-DGBC_DUMP_G12','-DOLD153='+str(int(old_control)),*sources,'-Wl,--gc-sections','-o',str(exe)]
        b=subprocess.run(cmd,cwd=o,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(o/(name+'-build.log')).write_bytes(b.stdout)
        assert b.returncode==0,b.stdout.decode(errors='replace')
        cmd=[str(exe),'3','0',str(a.rom.resolve()),*[str(o/n) for n in ['diag.packed','diag.raw','base.packed','base.raw','menu.bin']]]
        r=subprocess.run(cmd,cwd=o,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240);(o/(name+'.log')).write_bytes(r.stdout)
        assert r.returncode==0,r.stdout.decode(errors='replace')[-5000:]
        records=(o/'checkpoint-sectors.txt').read_text();(o/(name+'-progress.txt')).write_text(records)
        if old_control:
            assert 'DISPLAY_STOPPED' not in records and 'BASE_DONE' not in records and 'MENU_PREPARED' not in records
            assert b'PASS136 terminal' in r.stdout
        else:
            assert all(n in records for n in ['DISPLAY_NEXT','DISPLAY_STOPPED','BASE_DONE','MENU_PREPARED'])
            assert b'PASS109' in r.stdout and b'release=1 blocked=0' in r.stdout
            report=(o/'saved-report146.txt').read_text()
            for line in ['candidate=NES-GAME-153','loaded_bytes=393216','compared_bytes=393216','stop_ok=1','base_restored=1',
              'safe_to_reload=1','run_passed=0','run_rom_error=2','fault_context_valid=1','fault_context_hi=e200c2f4','fault_context_lo=30217a19']:
                assert line+'\n' in report,line
            (o/'saved-report153.txt').write_text(report)
        result[name]=dict(passed=True,source_sha256=sha(o/'nes_run136.inc'))
    shutil.copy2(s/'nes_run136.inc',o/'nes_run136.inc')
    for n in exact:assert sha(o/n)==sha(s/n),n
    result.update(passed=True,actual_sources={n:sha(s/n) for n in exact},physical=False,
      scope='Actual MCU/FatFS/menu C; modeled SD/GPIO/SPI peer and old bitbang transport adapter. Synthetic tagged error2, not physical152 cause.')
    (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
