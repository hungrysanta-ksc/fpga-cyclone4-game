# SPDX-License-Identifier: MIT
"""Direct host checks, actual ARM progress snapshots and bounded plan refill."""
import inspect,shutil
from pathlib import Path
import probe_nes_refill280 as prior
import probe_nes_refill267 as old
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint282 import apply


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];apply(d)
    for n in ('nes_joint282.py','nes_progress282.c.inc','nes_refill282.c','probe_nes_refill282.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
    return src,pins


def build_rom(d):
    p=d/'nes_output264.c';s=p.read_text()
    marker='static unsigned status(unsigned full){'
    s=once(s,marker,(ROOT/'tools/nes_progress282.c.inc').read_text()+'\n'+marker)
    s=once(s,'static unsigned drain(void){for', 'static unsigned drain(void){if(state259.retired==state259.sent)return !state259.error;for')
    s=once(s,' state259.sent++;state259.sequence++;return 1;', ' state259.sent++;state259.sequence++;status259[7]=0;return 1;')
    s=once(s,' batch_bytes260=0;\n state259.sent=', ' batch_bytes260=0;plan_cache282=0;\n state259.sent=')
    p.write_text(s,encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'tools/nes_refill282.c',d/'nes_refill267.c')
    p=d/'stubs.s';p.write_text(p.read_text().replace('io259','physical267'))
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    old.run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_output264.c','nes_refill267.c','stubs.s','-o','output.elf'],d,'build-rom')
    old.run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size-rom')
    old.run(arm/'arm-none-eabi-objdump.exe',['-dr','output.elf'],d,'disassembly-rom')


def main():
    ns=dict(old.__dict__);ns.update(prepare=prepare,build=prior.prior.build,build_rom=build_rom,worker=prior.prior.worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill282-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
