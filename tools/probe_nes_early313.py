# SPDX-License-Identifier: MIT
"""Positive early-manifest stress, same compiled RTL and two storage slots.

Reorders a test producer, not the actual ARM schedule. Never use its timing
as an ARM performance claim.
"""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    source=a.source.resolve();d=a.out.resolve();assert not d.exists()
    original=json.loads((source/'result.json').read_text())
    assert original['passed'] and original['positive_control313']
    shutil.copytree(source,d,ignore=shutil.ignore_patterns('*.log','*.json','*.wlf'))
    blob=bytes(int(x,16) for x in (d/'all905.hex').read_text().split())
    sizes=[int(x,16) for x in (d/'all905.lens').read_text().split()]
    count=sizes[0];at=0;packets=[]
    for n in sizes[1:count+1]:packets.append(bytearray(blob[at:at+n]));at+=n
    assert at==len(blob)
    index=next(i for i,p in enumerate(packets) if p[0]==15);assert index>2
    metadata=packets.pop(index);packets.insert(2,metadata)
    for i,p in enumerate(packets):p[2:4]=i.to_bytes(2,'little')
    (d/'all905-late.hex').write_bytes((d/'all905.hex').read_bytes())
    (d/'all905-late.lens').write_bytes((d/'all905.lens').read_bytes())
    (d/'all905.hex').write_text(''.join(f'{v:02x}\n' for p in packets for v in p),newline='\n')
    sizes[1:count+1]=[len(p) for p in packets]
    (d/'all905.lens').write_text(''.join(f'{v:x}\n' for v in sizes),newline='\n')
    with (d/'early.log').open('wb') as log:
        r=subprocess.run(['C:/altera_standard/25.1std/questa_fse/win64/vsim.exe','-c','-sv_lib','producer263',
            'work.joint266_tb','-gGNEG=0','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],
            cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    raw=(d/'early.log').read_text(errors='replace')
    assert r.returncode==0 and 'PASS JOINT266 frames=1' in raw and '** Fatal:' not in raw,raw[-2000:]
    result=dict(passed=True,manifest_old_index=index,manifest_new_index=2,packets=count,
        scope=__doc__,actual_inputs={p.name:sha(p) for p in d.iterdir() if p.is_file() and p.suffix in ('.sv','.hex','.lens','.desc','.dll')})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='actual_inputs'}))


if __name__=='__main__':main()
