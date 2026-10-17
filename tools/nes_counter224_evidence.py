# SPDX-License-Identifier: MIT
"""Use unchanged223 whole-board gates with the new same-edge counter evidence."""
import inspect,re
import nes_ingress223_evidence as prior
from nes_counter224 import ROOT,BASE,sha,replace

s=inspect.getsource(prior.main)
s=s.replace("d/'source01/preparation-ingress223.json'","d/'source01/preparation224.json'")
s=replace(s,"    test=read(d/'test01/result.json');arm=read(d/'check01/result.json')",'''    old=BASE/'probes/nes-ingress223'
    oldmanifest=read(old/'manifest01.json')
    for n in ['test01/result.json','check01/result.json','analysis.json','source01/preparation-ingress223.json']:
        assert sha(old/n)==oldmanifest[n],n
    counter=read(d/'test02/result.json');assert counter['passed'] and counter['same_edge']
    assert counter['source_sha256']==sha(d/'source01/nes_rom_spi.sv')
    assert counter['reference_sha256']==sha(old/'source01/nes_rom_spi.sv')
    for n,h in counter['public_sources'].items():assert sha(ROOT/n)==h,n
    for n,h in counter['sources'].items():assert sha(d/'test02'/n)==h,n
    test=read(old/'test01/result.json');arm=read(old/'check01/result.json')''')
for name in ['test01','arm01','check01']:
 s=re.sub(r"\bd/'"+name+r"(?=/|')", "old/'"+name, s)
s=s.replace("sha(d/'source01/preparation-ingress223.json')","sha(d/'source01/preparation224.json')")
s=replace(s,"                next='Close exact check_response_address[5]->commit_clear strict residual without changing acceptance edge/response ownership/STOP priority. Prefer proven local qualification sharing; no clock/SDC waiver or seed loop. Then full paired board/SNES212 ROM checks and real first-level trial. Keep compact geometry and scroll-map joint16.67ms budget; packing alone not60fps.',", "                next='If whole-board gates pass, pair existing223 ARM/wire2231 with current SNES212 ROM, verify routed ROM and package for first-level scrolling. If a gate fails, analyze the exact path without seed/clock/SDC waiver. No additional frame pipeline or SRAM.',")
s=s.replace("'Nominal passes but implementation stricter gate fails; no installable image.'", "'This evidence alone is not paired ROM/ASM or release approval.'")
start=s.index("    files=['nes_ingress223.py'")
end=s.index("    text=json.dumps(result",start)
s=s[:start]+'''    result['counter']=counter
    result['arm_reused_from']='nes-ingress223/check01'
    result['ingress_reused_from']='nes-ingress223/test01'
    result['public_sources']={n:sha(ROOT/n) for n in [
        'tools/nes_counter224.py','tools/test_nes_counter224.py','tools/nes_counter224_evidence.py',
        'tools/nes_ingress223_evidence.py','tools/check_nes_boundary165.py']}
'''+s[end:]
s=s.replace("analysis/ingress223-verification.json","analysis/counter224-verification.json")
s=s.replace("timing=timing,cdc=result['cdc'],io=io,", "timing=timing,cdc=result['cdc'],conditional_io_pass=io['conditional_data_bounds_pass'],")
ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(s,'counter224-evidence','exec'),ns)
if __name__=='__main__':ns['main']()
