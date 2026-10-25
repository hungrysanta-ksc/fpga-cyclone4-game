# SPDX-License-Identifier: MIT
import inspect
import subprocess,sys
import guard_nes_expand325 as base


def main():
    base.old.CASES.update({11:'STOP during early expected storage',12:'STOP during independent expected RAM scan',13:'STOP during final certificate RAM scan',14:'independent display expectation corruption',15:'map expected cursor overflow before RAM write',16:'requirements expected cursor overflow before RAM write'})
    s=inspect.getsource(base.main).replace('probe_nes_expand325.py','probe_nes_execute332.py')
    marker=' ns=dict(old.__dict__);'
    assert s.count(marker)==1
    s=s.replace(marker,''' s=s.replace('dut.flow.state==dut.flow.MISSUE313&&dut.flow.header[0]==3&&dut.flow.manifest_byte313==190', 'dut.core.validator.state==dut.core.validator.V_CHECKREAD&&dut.core.validator.map_phase305&&dut.core.validator.cursor==0')
 s=s.replace('else force dut.flow.held=0;', "else if(NEG319==15)begin corrupt325=dut.flow.queue.buffer[0];force dut.flow.manifest_byte313=9'd256;#1;if(dut.flow.canonical_write313)$fatal(1,\\\"overflow map write332\\\");end else if(NEG319==16)begin corrupt325=dut.flow.queue.buffer[422];force dut.flow.manifest_byte313=9'd166;#1;if(dut.flow.canonical_write313)$fatal(1,\\\"overflow requirement write332\\\");end else if(NEG319==14)force dut.core.validator.v_value=8'hff;else force dut.core.validator.v_value=0;")
 s=s.replace('  else $fatal(1,"unknown guard319");', '  else if(NEG319==11)wait(dut.flow.canonical_write313&&dut.flow.header[0]==15&&dut.flow.manifest_byte313==8);\\n  else if(NEG319==12)wait(dut.core.validator.state==dut.core.validator.E_CAPTURE332&&dut.core.validator.cursor==100);\\n  else if(NEG319==13)wait(dut.core.validator.state==dut.core.validator.H_CERT&&dut.core.validator.h_count==23);\\n  else if(NEG319==14)wait(dut.core.validator.state==dut.core.validator.D_READ&&dut.core.validator.rec_i==0);\\n  else if(NEG319==15)wait(dut.flow.canonical_write313&&dut.flow.header[0]!=15);\\n  else if(NEG319==16)wait(dut.flow.canonical_write313&&dut.flow.header[0]==15&&!dut.flow.display_byte313);\\n  else $fatal(1,"unknown guard319");')
 s=s.replace('if(NEG319<=4||NEG319==7||NEG319==8)begin','if(NEG319<=4||NEG319==7||NEG319==8||NEG319==11||NEG319==12||NEG319==13)begin')
 s=s.replace('  repeat(8)@(negedge host_clk);','  repeat(8)@(negedge host_clk);\\n  if(NEG319==15&&dut.flow.queue.buffer[0]!==corrupt325)$fatal(1,"overflow alias changed332");\\n  if(NEG319==16&&dut.flow.queue.buffer[422]!==corrupt325)$fatal(1,"overflow gap changed332");')
 ns=dict(old.__dict__);''')
    ns=dict(base.__dict__);exec(compile(s,'guards332','exec'),ns);ns['main']()
    reference=sys.argv[sys.argv.index('--reference')+1]
    out=base.old.Path(sys.argv[sys.argv.index('--out')+1])/'final-raw0'
    subprocess.run([sys.executable,str(base.old.ROOT/'tools/check_nes_final332.py'),'--source',reference,'--out',str(out)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)


if __name__=='__main__':main()
