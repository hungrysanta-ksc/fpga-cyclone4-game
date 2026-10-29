# SPDX-License-Identifier: MIT
"""Encode RBF for the 227 programmer with exact bounded runs."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
raw=a.input.read_bytes();assert raw and not a.out.exists();out=bytearray();i=0
while i<len(raw):
 v=raw[i];j=i+1
 while j<len(raw) and raw[j]==v and j-i<65535:j+=1
 n=j-i
 if n>=4:
  if n<256:out.extend((0x5b,v,n))
  else:out.extend((0x77,v,n&255,n>>8))
 else:
  for _ in range(n):
   if v in (0x5b,0x77,0x9b):out.append(0x9b)
   out.append(v)
 i=j
a.out.write_bytes(out);print('encoded',len(raw),'bytes into',len(out))
