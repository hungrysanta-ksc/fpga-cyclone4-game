# SPDX-License-Identifier: MIT
"""Retain38 STOP/semantic guards plus4 parser/metadata handoff cancellations."""
from pathlib import Path
import inspect,json,sys
import guard_nes_joint270 as prior
from nes_joint272 import patch
from nes_delta231 import once,sha
from probe_nes_joint261 import run


def prepare(d,last):
    src,pins,stats=prior.prepare(d,last);patch(d,src,pins,shared=True)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'endmodule', '''
 // These four directed stops interrupt actual metadata, read request,
 // locally generated receipt/hash events, and completion response.
 initial begin : cancel272
  if(GNEG>=39&&GNEG<=42)begin
   case(GNEG)
    39:wait(dut.flow.state==dut.flow.OMETA&&dut.flow.at==3);
    40:wait(dut.flow.parser272.state==dut.flow.parser272.RECV);
    41:wait(dut.flow.parser272.event_valid);
    42:wait(dut.flow.parser272.state==dut.flow.parser272.RETURN);
   endcase
   @(negedge clk);disable bus263;bus_read=1;bus_write=1;test_abort=1;
  end
 end
 always @(posedge clk)if(!reset&&dut.cfg_valid272&&dut.cfg_ready272)begin
  if(!dut.core.output_phase||dut.core.encoder.q_pending||source_fault)
   $fatal(1,"source/context ownership collision");
 end
endmodule''')
    p.write_text(s,encoding='utf-8',newline='\n')
    return src,pins,stats


def main():
    # Exact prior269->266->265 guard composition, substituting only prepare.
    ns=dict(prior.old.__dict__);ns.update(prepare=prepare,__file__=__file__)
    exec(compile(inspect.getsource(prior.old.main),'guard272-main','exec'),ns)
    ns['main']()
    d=Path(sys.argv[sys.argv.index('--out')+1]).resolve()
    qb=Path(sys.argv[sys.argv.index('--questa-bin')+1])
    r=json.loads((d/'result.json').read_text())
    for i in range(39,43):
        log=run(qb/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'-gGNEG={i}','+LAST=905',
                   '-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',120)
        assert f'PASS DIRECT266 GNEG={i}' in log
        r['guards'].append(i)
    r.update(scope=__doc__,script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(passed=True,guards=r['guards'])))


if __name__=='__main__':main()
