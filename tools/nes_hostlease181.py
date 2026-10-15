# SPDX-License-Identifier: MIT
"""Local host admission, immediate RUN loss cancellation; paired1813/1815 board."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_packed181 import exporter,spi


def bridge(s):
    s=replace(s,' wire reset;nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw_reset),.reset(reset));', ''' // RUN loss starts a new transport lifetime, even with a stopped host clock.
 wire raw_cancel=raw_reset||!active;
 wire reset;nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw_cancel),.reset(reset));
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] idle_ss,idle_write;
 reg host_ready;
 always @(posedge clk or posedge raw_cancel)begin
  if(raw_cancel)begin idle_ss<=0;idle_write<=0;host_ready<=0;end
  else begin
   idle_ss<={idle_ss[0],SPI_SS};idle_write<={idle_write[0],write_n};
   // Do not join the middle of an old SPI transaction or SNES write.
   // Once admitted, normal activity does not revoke ownership.
   if(!reset&&idle_ss[1]&&idle_write[1])host_ready<=1;
  end
 end
 wire session_reset=reset||!host_ready;''')
    s=replace(s,'endpoint(.clk(clk),.reset(reset),.enable(active)',
                   'endpoint(.clk(clk),.reset(session_reset),.enable(host_ready)')
    s=replace(s,'bus(.clk(clk),.reset(reset),.active(active)',
                   'bus(.clk(clk),.reset(session_reset),.active(host_ready)')
    s=replace(s,'assign oe_n=raw_reset?', 'assign oe_n=raw_cancel?')
    s=replace(s,'assign dir=!raw_reset&&bus_dir;', 'assign dir=!raw_cancel&&bus_dir;')
    return s


def prepare(prior,client,out):
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
    for n,h in pins.items():
        assert sha(prior/n)==h,n;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
    for name,fn in [('nes_sink_bridge165.sv',bridge),('nes_native_export181.sv',exporter),('nes_native_spi165.sv',spi)]:
        p=out/name;p.write_text(fn(p.read_text()),encoding='utf8',newline='\n')
    expected=json.loads((ROOT/'analysis/stream181-verification.json').read_bytes())
    # The selected client has already passed actual65816/WRAM/PPU checks.
    assert (client/'program.bin').stat().st_size==4096 if (client/'program.bin').exists() else True
    assert sha(client/'body.bin')=='ddd8fc4aa884fd24b01e8b1e27dd0ce444b79df467c3c605beff6c33e6228792'
    shutil.copy2(client/'sink-program.hex',out/'sink-program.hex')
    changed=[n for n in pins if sha(out/n)!=pins[n]]
    assert set(changed)=={'nes_sink_bridge165.sv','nes_native_export181.sv','nes_native_spi165.sv','sink-program.hex'}
    m.update(baseline_hostlease_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,
             ingress_version='1813',sink_version='1815',client_body_sha256=sha(client/'body.bin'),
             source_pins={n:sha(ROOT/n) for n in ['tools/nes_hostlease181.py','tools/nes_packed181.py']},
             prior_stream_analysis_sha256=sha(ROOT/'analysis/stream181-verification.json'),adopted=False,hardware=False)
    (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n')
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','client','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=prepare(a.prior,a.client,a.out);print(json.dumps(dict(changed=r['changed'],adopted=False)))
