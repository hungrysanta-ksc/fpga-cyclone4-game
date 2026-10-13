# SPDX-License-Identifier: MIT
"""Local reset release for the native video mailbox and host SPI endpoint."""
from pathlib import Path
import argparse,difflib,json,shutil
from nes_game147 import ROOT,sha

def mailbox(s):
    old=' (* async_reg="true" *) reg [1:0] sr,dr,req_sync,ack_sync,up_src,up_dst;'
    assert s.count(old)==1
    s=s.replace(old,''' (* async_reg="true" *) reg [1:0] sr,dr,req_sync,ack_sync,up_src,up_dst;
 // Only these two release chains see asynchronous deassertion. Payload and
 // protocol state use their own clock's release; common assertion is immediate.
 always @(posedge src_clk or posedge reset)
  if(reset)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge dst_clk or posedge reset)
  if(reset)dr<=0;else dr<={dr[0],1'b1};
 wire src_reset=!sr[1],dst_reset=!dr[1];''')
    s=s.replace('always @(posedge src_clk or posedge reset)begin','always @(posedge src_clk or posedge src_reset)begin')
    s=s.replace('if(reset)begin sr<=0;up_src<=0;', 'if(src_reset)begin up_src<=0;')
    s=s.replace("sr<={sr[0],1'b1};up_src",'up_src')
    s=s.replace('always @(posedge dst_clk or posedge reset)begin','always @(posedge dst_clk or posedge dst_reset)begin')
    s=s.replace('if(reset)begin dr<=0;up_dst<=0;', 'if(dst_reset)begin up_dst<=0;')
    s=s.replace("dr<={dr[0],1'b1};up_dst",'up_dst')
    assert s.count('sr<=0')==1 and s.count('dr<=0')==1
    return s

def joint(s):
    old='nes_native_spi165 native_spi(.clk(host_clk),.reset(reset),'
    assert s.count(old)==1
    return s.replace(old,'''wire native_spi_reset;
nes_domain_reset124 native_spi_release(.clk(host_clk),.raw_reset(reset),.reset(native_spi_reset));
nes_native_spi165 native_spi(.clk(host_clk),.reset(native_spi_reset),''')

def prepare(baseline,out):
    assert not out.exists() and str(out).isascii()
    pub=json.loads((ROOT/'analysis/directstate165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==pub['raw_result_sha256']['map01']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    changes={'nes_native_mailbox165.sv':mailbox,'nes_live_joint.sv':joint}
    for n,fn in changes.items():
        old=(baseline/n).read_text();new=fn(old);(out/n).write_text(new)
        (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
    result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],changed=list(changes),
        baseline_result_sha256=sha(baseline/'result.json'),public_sources={'tools/nes_boundary165.py':sha(Path(__file__))})
    assert {n for n,h in result['sources'].items() if h!=m['sources'][n]}==set(changes)
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
