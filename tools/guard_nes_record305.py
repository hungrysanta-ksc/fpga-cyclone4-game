# SPDX-License-Identifier: MIT
"""Run retained independent receipt/STOP/final ACK cases on replacement control."""
import inspect,json,sys,shutil
from pathlib import Path
import guard_nes_joint287 as old
from nes_close295 import apply
from nes_joint298 import apply as joint298,observe
from nes_delta231 import once,ROOT,sha
from nes_arch300 import apply as arch300,observe as observe300
from nes_record305 import apply as record305,observe as observe305

def main():
    # Legacy STOP points used the removed ORET relay. Bind them to the shared
    # execution wait; the injected STOP remains before receipt/manifest retire.
    engine_guard=old.old.old.old
    source_main=inspect.getsource(engine_guard.main)
    source_main=once(source_main," exec(compile(code,'guard278-main','exec'),ns);ns['main']()",
                    " code=code.replace('dut.flow.ORET','dut.flow.XWAIT298')\n code=code.replace('dut.flow.ordinary_mode&&dut.flow.state==dut.flow.PREAD','dut.exec_busy298&&dut.core.validator.state==dut.core.validator.E_READ298')\n exec(compile(code,'guard278-main','exec'),ns);ns['main']()")
    # The inherited runner installs patch/adapt after this point; retain its
    # live globals rather than freezing the older RTL patch in a copied dict.
    guard_ns=engine_guard.__dict__
    exec(compile(source_main,'guard298-main','exec'),guard_ns)
    engine_guard.main=guard_ns['main']
    original=old.apply
    source=inspect.getsource(apply)
    a=source.index("    p=d/'nes_tile_producer260.sv'");b=source.index("    for name in ('nes_plan_rom267.sv'",a)
    ns=dict(once=once);exec('def control(d):\n'+source[a:b],ns)
    def patch(d):original(d);ns['control'](d);joint298(d);arch300(d);record305(d)
    old.apply=patch
    before=old.old.old.tb
    def tb(s):
        s=observe305(observe300(observe(before(s)))).replace('.end_valid(ev),.end_ready(er),',".end_valid(ev),.end_partial295(1'b0),.end_ready(er),")
        s=s.replace('dut.flow.state==dut.flow.OSETUP&&dut.flow.header[0]==15','dut.flow.state==dut.flow.XBEGIN298&&dut.flow.header[0]==15')
        s=s.replace('dut.flow.ordinary_mode&&dut.flow.state==dut.flow.PREAD',
                    'dut.exec_busy298&&dut.core.validator.state==dut.core.validator.E_READ298')
        return once(s,' initial begin : result264','''
 always @(posedge host_clk)if(!reset&&dut.exec_busy298&&dut.flow.header[0]!=12&&!dut.flow.qr)
  $fatal(1,"common executor lost immutable queue head");
 always @(posedge host_clk)if(!reset&&dut.core.validator.state==dut.core.validator.V_CLEARFRAME&&dut.core.ram_b_we&&dut.core.ram_b_addr>=680&&dut.core.ram_b_addr<=715)
  $fatal(1,"frame clear destroyed H2 context");
 initial begin : admission300
  if(GNEG==68||GNEG==69)begin
   wait(dut.flow.ordinary_range&&dut.core.validator.v_ready);
   @(negedge host_clk);injected264=1;
   if(GNEG==68)force dut.core.validator.v_count=0;
   else force dut.core.validator.v_count=4095;
   wait(source_fault);
   if(dut.core.validator.fault!=2)$fatal(1,"exclusive end admission wrong fault");
  end
 end
 initial begin : execution298
  if(GNEG==64||GNEG==65)begin
   wait(dut.core.validator.state==dut.core.validator.E_READ298&&dut.flow.header[0]==10);
   @(negedge host_clk);injected264=1;
   if(GNEG==64)force dut.core.validator.packet_at298=9'd256;
   else force dut.core.validator.cursor=10'd422;
   wait(source_fault);
   if(dut.core.validator.fault!=3)$fatal(1,"common decode bound wrong fault");
  end
  if(GNEG==66||GNEG==67)begin
   if(GNEG==66)wait(dut.core.validator.state==dut.core.validator.E_NEXT298&&dut.flow.header[0]==10);
   else wait(dut.core.validator.state==dut.core.validator.E_SEAL298);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;injected264=1;test_abort=1;
   #2000;
   if(dut.exec_busy298||dut.exec_done298||dut.core.ram_b_we||v_sealed||bus_valid)
    $fatal(1,"STOP left shared execution or completion active");
  end
 end
 initial begin : result264''')
    old.old.old.tb=tb
    engine_guard.CASES.update({68:'descriptor exclusive end below first',69:'descriptor exclusive end outside independent domain',64:'shared packet cursor outside queue length',65:'shared manifest expanded bound',
                              66:'STOP inside shared manifest return',67:'STOP before shared seal/final ACK'})
    old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]);r=json.loads((d/'result.json').read_text())
    for name in ('nes_joint298.py','guard_nes_joint298.py','nes_arch300.py','guard_nes_arch300.py','nes_record305.py','guard_nes_record305.py'):
        shutil.copyfile(ROOT/'tools'/name,d/name);r['entry_hashes'][name]=sha(d/name)
    r['scope298']='38 retained guards plus 4 shared executor bounds/STOP cases; legacy ORET STOP points rebound to XWAIT298.'
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')

if __name__=='__main__':main()
