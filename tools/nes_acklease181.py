# SPDX-License-Identifier: MIT
"""Share ACK construction/publication storage, retain coherent SPI snapshot."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_clip178 import replace

def endpoint(s):
    s=replace(s,'reg [95:0] ack_work,ack_held;', 'reg [95:0] ack_work;')
    s=replace(s,'ack_work<=0;ack_held<=0;', 'ack_work<=0;')
    s=replace(s,'else begin ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end',
      '''// A coincident publish observes the old complete work, as before.
    // The real SNES bus emits write/publish as mutually exclusive pulses.
    else if(!ack_publish)begin ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end''')
    s=replace(s,'else begin ack_held<=ack_work;ack_valid<=1;', 'else begin ack_valid<=1;')
    s=replace(s,'for(j=0;j<12;j=j+1)snapshot[103-j*8-:8]<=ack_held[j*8+:8];',
      '''// Flags and ACK use the same pre-edge state. Once captured, neither
      // later writes nor publish may alter this transaction or its CRC.
      // A new sealed packet clears valid before its ACK can be written.
      for(j=0;j<12;j=j+1)snapshot[103-j*8-:8]<=ack_valid?ack_work[j*8+:8]:8'd0;''')
    assert 'ack_held' not in s
    return s

def prepare(prior,out):
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
    p=out/'nes_sink_spi165.sv';p.write_text(endpoint(p.read_text()),encoding='utf8',newline='\n')
    changed=[n for n in pins if sha(out/n)!=pins[n]]
    assert changed==['nes_sink_spi165.sv']
    m.update(baseline_acklease_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,
      ack_invalid_payload='zero; consumed only when ACK valid',adopted=False,hardware=False,
      acklease_generator_sha256=sha(Path(__file__)))
    (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n')
    return m

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=prepare(a.prior,a.out);print(json.dumps(dict(changed=r['changed'],adopted=False)))
