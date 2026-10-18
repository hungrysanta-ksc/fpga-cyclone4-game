# SPDX-License-Identifier: MIT
"""Actual negative checks for every unrolled manifest/coverage lane.

Each case replays a real displayed frame and rejects the changed second one.
No WRAM or ACK injection. Frozen12-case protocol/STOP suite runs separately.
"""
import inspect
import test_nes_maskfault247 as base
from nes_delta231 import once

CASES=tuple(f'manifest_lane{i}' for i in range(16))+tuple(f'coverage_lane{i}' for i in range(8))


def main():
    s=inspect.getsource(base.main)
    s=once(s,'  for n,b in packets.items():', '''  if case.startswith('manifest_lane'):
   lane=int(case.removeprefix('manifest_lane'))
   packets[manifests[lane%2]][16+lane]^=128
  elif case.startswith('coverage_lane'):
   lane=int(case.removeprefix('coverage_lane'));valid=set()
   for name in second:
    q=originals[name]
    if q[0]==7 and q[1]<2:
     unit=16 if q[1]==0 else32;base_slot=0 if q[1]==0 else1024
     at=int.from_bytes(q[10:12],'little');n=int.from_bytes(q[14:16],'little')
     valid.update(range(base_slot+at//unit,base_slot+(at+n)//unit))
   missing=next(slot for slot in range(1152) if slot not in valid and (slot//16)%8==lane)
   q=packets[seal];q[40+missing//8]|=1<<(missing%8)
  for n,b in packets.items():'''.replace('else32','else 32').replace('else1024','else 1024'))
    ns=dict(base.__dict__);ns.update(CASES=CASES,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'fastlanes247','exec'),ns);ns['main']()


if __name__=='__main__':main()
