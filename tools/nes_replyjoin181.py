# SPDX-License-Identifier: MIT
"""Integrate the qualified local ROM reply; keep all prior CDC/clock contracts."""
from pathlib import Path
import argparse,json,shutil
from nes_reply181 import BASELINE,transform
from nes_game147 import sha
from nes_cdc181 import READER

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','tested','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert str(a.out).isascii() and not a.out.exists()
    m=json.loads((a.baseline/'preparation.json').read_bytes())
    t=json.loads((a.tested/'result.json').read_bytes());assert t['passed']
    assert sha(a.baseline/'nes_rom_physical.sv')==BASELINE
    a.out.mkdir()
    for n,h in m['sources'].items():
        assert sha(a.baseline/n)==h,n
        f=a.out/n;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,f)
    (a.out/'nes_rom_physical.sv').write_text(transform((a.baseline/'nes_rom_physical.sv').read_text()),encoding='utf8',newline='\n')
    assert sha(a.out/'nes_rom_physical.sv')==t['candidate_sha256']
    # Continuously sampled data is only used after ACK stage2. First possible
    # ACK stage2 is >=one NES period after held-data launch; 9.904ns physical
    # bound is stricter and matches the executed delayed-data join fixture.
    # Hold cuts apply ONLY to these eight asynchronous, unqualified samples.
    extra=['# REPLYJOIN181 eight held-data capture bits; qualified by ACK stage2.']
    selected=[]
    for i in range(8):
        s=READER+f'data_hold[{i}]';d=READER+f'reply_data[{i}]'
        pair=f'-from [cdc181_exact {{{s}}}] -to [cdc181_exact {{{d}}}]'
        extra.extend(['set_max_delay 11.904 '+pair,'set_false_path -hold '+pair])
        selected.append(dict(source=s,destination=d,setup_bound_ns=11.904,data_delay_budget_ns=9.904))
    f=a.out/'cdc181.sdc';f.write_text(f.read_text()+'\n'+'\n'.join(extra)+'\n',encoding='utf8')
    m.update(baseline_cdc_sources=m['sources'],sources={n:sha(a.out/n) for n in m['sources']},
        reply_selected=selected,reply_join_result_sha256=sha(a.tested/'result.json'),
        preparer_sha256=sha(Path(__file__)),rtl_unchanged=False,rom_payload_exceptions=True,
        changed=['nes_rom_physical.sv','cdc181.sdc'],adopted=False,hardware=False)
    (a.out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
    print('Prepared actual board: one RTL change, eight exact capture constraints; no approval')

if __name__=='__main__':main()
