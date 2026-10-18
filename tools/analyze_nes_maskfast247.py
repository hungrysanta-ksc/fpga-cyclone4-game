# SPDX-License-Identifier: MIT
"""Same independent packet/map/command oracle for the expanded fast receiver.

The frozen analyzer accepts the unchanged2471 packet contract. Storage input
must describe the newly synthesized receiver, not the prior4398-byte image.
"""
import inspect
import analyze_nes_maskrun247 as base
from nes_delta231 import once


def main():
    s=inspect.getsource(base.main)
    s=once(s,"('test','host','client','fault','storage','rtl','model','out')", "('test','host','client','fault','storage','rtl','model','lanes','masks','baseline','out')")
    s=once(s,'5KiB RAM geometry','6KiB RAM geometry')
    s=once(s," assert all(r['passed']", " assert storage['client_sha256']==sha(pin(a.client/'sink-program.hex'))\n assert rtl['map_sha256']==sha(a.storage/'result.json')\n assert all(r['passed']")
    s=once(s," raw=a.out/'result.json';", ''' lanes=read(a.lanes/'result.json');masks=read(a.masks/'result.json');before=read(a.baseline/'result.json')
 assert lanes['passed'] and len(lanes['cases'])==24 and masks['passed'] and masks['masks']==255
 for item in (fault,lanes,masks):
  assert item['client_sha256']==sha(pin(a.client/'sink165.sfc'))
  assert item['normal_sha256']==sha(a.test/'result.json')
 for folder in (a.fault,a.lanes,a.masks):
  pin(folder/'test.py')
  for pattern in ('**/mesen.log','**/capture.lua','**/fault-result.json','**/allmask-result.json','**/allmask-map.bin','**/allmask-receipt.bin'):
   for f in sorted(folder.glob(pattern)):pin(f)
 oldrows=list(csv.DictReader(pin(a.baseline/'frames.csv').open()));assert len(oldrows)==71
 regress=[];comparison={}
 for old,new in zip(oldrows,rows):
  assert int(old['frame'])==new['frame']
  for key in ('map_words','map_records','map_packets','commands','dma_bytes','vblanks','wire_ready4','charge'):assert int(old[key])==new[key],(key,new['frame'])
  if new['frame']>=907 and new['mask_clocks']>int(old['mask_clocks']):regress.append(new['frame'])
 for key in ('mask_ms','manifest_ms','coverage_ms','map_and_validation_ms','conditional_wire_plus_measured_ms'):
  old=before['warm'][key];new=result['warm'][key]
  comparison[key]=dict(old_max=old['maximum'],new_max=new['maximum'],old_total=old['total'],new_total=new['total'],total_reduction_percent=100*(1-new['total']/old['total']))
 result.update(lane_fault_cases=lanes['cases'],all_masks=masks,comparison=comparison,mask_regression_frames=regress,baseline_sha256=sha(a.baseline/'result.json'))
 raw=a.out/'result.json';''')
    ns=dict(base.__dict__);ns.update(__file__=__file__,__doc__=__doc__)
    exec(compile(s,'maskfast247-analysis','exec'),ns);ns['main']()


if __name__=='__main__':main()
