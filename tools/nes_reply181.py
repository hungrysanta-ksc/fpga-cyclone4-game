# SPDX-License-Identifier: MIT
"""Experimental local RUN reply capture; no FIT/SD approval implied."""
from pathlib import Path
import argparse, hashlib, json

BASELINE = '9b66c32071c7176eec55081c9e73737db1d97615ee0cedb88fcef6932aeffe12'

def transform(source):
    anchor = ' assign rom_data=data_hold;'
    assert source.count(anchor) == 1
    return source.replace(anchor, ''' //181 Receive the held byte locally in parallel with ACK synchronization.
 // Only rom_response qualifies this byte. ACK stage two and this register
 // update on the same source edge; no extra visible reply cycle is added.
 // The data path must settle BEFORE that edge: separately constrain/verify
 // data_hold -> reply_data. Do not expose the unqualified sample to clients.
 (* preserve *) reg [7:0] reply_data;
 always @(posedge clk or posedge sr)
  if(sr)reply_data<=0;else reply_data<=data_hold;
 assign rom_data=reply_data;''')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    raw = (a.baseline/'nes_rom_physical.sv').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASELINE
    assert not a.out.exists()
    a.out.mkdir()
    target = a.out/'nes_rom_physical.sv'
    target.write_text(transform(raw.decode('utf8').replace('\r\n', '\n')), encoding='utf8', newline='\n')
    result = dict(baseline_sha256=BASELINE,
                  candidate_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  experimental=True, fit=False, adopted=False,
                  scope='RUN qualified data only. CHECK/pins/ACK/ready unchanged. Requires downstream/physical CDC verification before integration.')
    (a.out/'preparation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')

if __name__ == '__main__': main()
