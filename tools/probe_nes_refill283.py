# SPDX-License-Identifier: MIT
"""Actual ARM nibble CRC plus joint receipt range/RAM progression."""
import inspect,shutil
import probe_nes_refill282 as prior
from nes_delta231 import ROOT,sha,once
from nes_joint283 import apply


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' integer ordinary263=0,', ''' always @(posedge host_clk)if(!reset&&dut.flow.ordinary_range)
  $fwrite(events261,"range283,%0d,%0d,%0d,%0t\\n",f,dut.flow.ordinary_first,dut.flow.ordinary_count,$time);
 integer ordinary263=0,''')
    p.write_text(s,encoding='utf-8',newline='\n')
    for n in ('nes_joint283.py','nes_crc283.h','probe_nes_refill283.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
    return src,pins


def build_rom(d):
    # Keep the actual 282 serializer/refill, modify only the CRC implementation.
    # Compile once with the existing flags, rather than patching ELF bytes.
    source=inspect.getsource(prior.build_rom)
    source=once(source,"    p.write_text(s,encoding='utf-8',newline='\\n')",'''    s=once(s,'static unsigned crc8(unsigned c,unsigned b){c^=b;for(unsigned i=0;i<8;i++)c=(c&128)?(c<<1)^7:c<<1;return c&255;}',
        '#include "nes_crc283.h"\\nstatic unsigned crc8(unsigned c,unsigned b){return crc_byte283(c,b);}')
    shutil.copyfile(ROOT/'tools/nes_crc283.h',d/'nes_crc283.h')
    p.write_text(s,encoding='utf-8',newline='\\n')''')
    marker="    p=d/'stubs.s';"
    source=once(source,marker,'''    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'static unsigned crc8(const uint8_t *p,unsigned n){unsigned c=0;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c&128)?(c<<1)^7:c<<1;c&=255;}return c;}',
        '#include "nes_crc283.h"\\nstatic unsigned crc8(const uint8_t *p,unsigned n){unsigned c=0;while(n--)c=crc_byte283(c,*p++);return c;}')
    p.write_text(s,encoding='utf-8',newline='\\n')
'''+marker)
    ns=dict(prior.__dict__);exec(compile(source,'build283','exec'),ns);ns['build_rom'](d)


def main():
    old=prior.old
    ns=dict(old.__dict__);ns.update(prepare=prepare,build=prior.prior.prior.build,build_rom=build_rom,
        worker=prior.prior.prior.worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill283-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
