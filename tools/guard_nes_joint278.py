# SPDX-License-Identifier: MIT
"""Ordered ACK/STOP guards on host execution and fixed phase RAM ports."""
import inspect
import guard_nes_joint276 as prior
from nes_joint278 import patch
from probe_nes_refill278 import tb_patch

CASES=dict(prior.CASES)
CASES.update({
45:'STOP while the sole queue header is being decoded',
46:'STOP during a tagged original-payload CRC tap',
47:'STOP during host receipt RAM write',
48:'STOP during host scroll CRC',
49:'STOP before host packet retirement',
50:'STOP with NES clock paused during host CRC',
51:'STOP with host clock paused during host CRC',
52:'STOP with deferred source mask write pending',
})

def adapt(s):
 s=tb_patch(s)
 s=s.replace('always @(posedge clk)if(dut.h_valid&&h_ready)', 'always @(posedge host_clk)if(dut.h_valid&&h_ready)')
 s=s.replace('dut.core.encoder.state==dut.core.encoder.D_CHECK','dut.core.validator.state==dut.core.validator.D_CHECK')
 s=s.replace('dut.core.encoder.rec_i','dut.core.validator.rec_i')
 s=s.replace('wait(dut.core.encoder.cursor>8)','wait(dut.core.validator.cursor>8)')
 s=s.replace('reg clk=0;always #22.727 clk=~clk;',
             'reg pause_nes278=0,pause_host278=0;reg clk=0;always #22.727 if(!pause_nes278)clk=~clk;')
 s=s.replace('forever #5.952 host_clk=~host_clk;', 'forever #5.952 if(!pause_host278)host_clk=~host_clk;')
 s=s.replace(' initial begin : result264',''' initial begin : paused_stop278
  if(GNEG==50||GNEG==51||GNEG==52)begin
   if(GNEG==52)wait(dut.core.encoder.mask_pending278);
   else wait(dut.flow.tap_state278==2&&dut.core.validator.state==dut.core.validator.H_SCROLL);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;injected264=1;
   if(GNEG==50)pause_nes278=1;
   if(GNEG==51)pause_host278=1;
   test_abort=1;
   #2000;
   if(dut.core.ram_a_we||dut.core.ram_b_we||v_sealed||staged||bus_valid)
    $fatal(1,"paused clock STOP left an active writer or output");
   pause_nes278=0;pause_host278=0;
  end
 end
 initial begin : result264''')
 return s

def main():
 ns=dict(prior.__dict__);ns.update(patch=patch,adapt=adapt,CASES=CASES,__file__=__file__,__doc__=__doc__)
 code=inspect.getsource(prior.main)
 code=code.replace(' patch(d)\n', ''' patch(d)
 for name in ['nes_joint278.py','probe_nes_refill278.py','guard_nes_joint278.py']:
  shutil.copyfile(ROOT/'tools'/name,d/name);pins[str(ROOT/'tools'/name)]=sha(ROOT/'tools'/name)
''')
 a=code.index(" s=once(s,' always @(posedge clk)if(dut.h_valid")
 b=code.index(" s=once(s,'      if(!injected264)begin",a)
 code=code[:a]+" s=adapt(s)\n"+code[b:]
 code=code.replace("default='1-49'","default='1-52'")
 code=code.replace('dut.core.encoder.state==dut.core.encoder.P_LOAD&&dut.core.encoder.row_i==3',
                   'dut.flow.state==dut.flow.HCAP&&dut.flow.at==3')
 code=code.replace('dut.core.encoder.state==dut.core.encoder.P_RECV','dut.flow.tap_state278==2')
 code=code.replace('dut.core.encoder.left_row&&dut.core.encoder.state==dut.core.encoder.V_RWRITE',
                   'dut.core.validator.state==dut.core.validator.V_RWRITE')
 code=code.replace('dut.core.encoder.local_event276&&dut.core.encoder.local_kind276==5',
                   'dut.flow.tap_state278==2')
 code=code.replace('dut.core.encoder.state==dut.core.encoder.H_SCROLL',
                   'dut.core.validator.state==dut.core.validator.H_SCROLL')
 code=code.replace('dut.core.encoder.state==dut.core.encoder.P_RETURN','dut.flow.state==dut.flow.ORET')
 code=code.replace('GNEG>=45)begin','(GNEG>=45&&GNEG<=49))begin')
 a=code.index(' always @(posedge clk)if(!reset&&dut.desc_valid276')
 b=code.index(" initial begin : result264''')",a)
 code=code[:a]+code[b:]
 code=code.replace("'DESCRIPTOR276'","'HOST278'").replace('PASS DESCRIPTOR276','PASS HOST278')
 code=code.replace("*r['rtl_hashes'],'joint266_tb.sv'","*r['rtl_hashes'],'nes_validator278.sv','joint266_tb.sv'")
 code=code.replace("for n in r['rtl_hashes']}", "for n in [*r['rtl_hashes'],'nes_validator278.sv']}")
 exec(compile(code,'guard278-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
