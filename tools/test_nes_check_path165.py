# SPDX-License-Identifier: MIT
"""Run existing hardware-timed SPI/read/ACK boundaries on the selected CHECK RTL."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,os
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();a.out.mkdir()
    source=a.out/'inputs';source.mkdir();m=json.loads((a.prepared/'preparation.json').read_bytes())
    names=['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','nes_rom_spi.sv','nes_rom_service.sv']
    for n in names:
        assert sha(a.prepared/n)==m['sources'][n],n
        shutil.copy2(a.prepared/n,source/n)
    (source/'result.json').write_text(json.dumps(dict(sources={n:sha(source/n) for n in names},prefetch=True)))
    #149 expects the historical5F reply ID. The installed164 decoder is6B.
    # Both unchanged164 and this candidate failed precisely that stale check.
    # Preserve the pinned149 driver and materialize only this explicit update.
    driver=(ROOT/'tools/test_nes_game149_spi.py').read_text()
    needle="    tb.write_text(s,encoding='utf8',newline='\\n')"
    assert driver.count(needle)==1
    update='    assert s.count("rx[1]==8\'h5f")==2\n    s=s.replace("rx[1]==8\'h5f","rx[1]==8\'h6b")\n'
    driver=driver.replace(needle,update+needle)
    runner=a.out/'driver.py';runner.write_text(driver)
    env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'))
    with (a.out/'driver.log').open('wb') as f:
        r=subprocess.run([sys.executable,'-X','utf8',str(runner),'--prepared',str(source),'--out',str(a.out/'path'),'--questa-bin',str(a.questa_bin)],env=env,stdout=f,stderr=subprocess.STDOUT)
    assert r.returncode==0,(a.out/'driver.log').read_text(errors='replace')[-3000:]
    v=json.loads((a.out/'path/result.json').read_bytes());assert v['passed']
    v['expected_reply_id']='6B';v['prior_5F_expectation_obsolete']=True
    v['public_sources']={n:sha(ROOT/n) for n in ['tools/test_nes_check_path165.py','tools/test_nes_game149_spi.py','tests/nes-functional/game147_path_tb.sv']}
    (a.out/'result.json').write_text(json.dumps(v,indent=2)+'\n');print(v['summary'])
if __name__=='__main__':main()
