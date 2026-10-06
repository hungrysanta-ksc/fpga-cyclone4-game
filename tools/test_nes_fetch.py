"""Verify corruption/truncation is rejected using derived capture copies. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse
import json
import shutil
from run_nes_fetch import analyze

p=argparse.ArgumentParser()
for name in ('probe','capture','out'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
original=json.loads((a.capture/'result.json').read_text())
assert original['passed']
first=original['frames'][0]['frame'];count=original['capture_frames']
results={}
for fault,key in [('missing_fetch','bg_fetch_cadence'),('wrong_chr_byte','chr_value'),('pixel_corruption','rgb_pixels'),('missing_frame','frame_sequence')]:
    case=a.out/fault;case.mkdir()
    for file in ['trace.tsv','frames.tsv']+[f'frame-{f["frame"]:03}.rgb' for f in original['frames']]:
        shutil.copy2(a.capture/file,case/file)
    rows=(case/'trace.tsv').read_text().splitlines()
    index=next(i for i,row in enumerate(rows) if row.startswith(f'read\t{first}\t0\t5\t'))
    if fault=='missing_fetch': rows.pop(index)
    elif fault=='wrong_chr_byte':
        values=rows[index].split('\t');values[7]=str(int(values[7])^1);rows[index]='\t'.join(values)
    elif fault=='pixel_corruption':
        file=case/f'frame-{first:03}.rgb';data=bytearray(file.read_bytes());data[0]^=1;file.write_bytes(data)
    elif fault=='missing_frame':
        file=case/'frames.tsv';file.write_text('\n'.join(file.read_text().splitlines()[:-1])+'\n',encoding='utf-8',newline='\n')
    (case/'trace.tsv').write_text('\n'.join(rows)+'\n',encoding='utf-8',newline='\n')
    result=analyze(a.probe,case,first,count,0)
    result['derived_fault']=fault
    (case/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    assert not result['passed'] and result['errors'].get(key), (fault,result['errors'])
    results[fault]=dict(rejected=True,errors=result['errors'])
(a.out/'negative-tests.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(results,indent=2))
