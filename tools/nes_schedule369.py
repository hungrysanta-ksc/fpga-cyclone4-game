# SPDX-License-Identifier: MIT
"""Classify a descriptor only when exact-key reuse did not already resolve it."""
from nes_delta231 import once

def apply(d):
 p=d/'nes_resident211.c';s=p.read_text()
 old=''' bool retain=ordinary(q);
 uint32_t key=q->kind==2?65534u:q->tag|(kind?(uint32_t)q->mask<<13:0);
'''
 s=once(s,old,'')
 needle=' if(exact_slot!=stop)return exact_slot;\n'
 # The existing exact-hit branch never consulted retain/key. Keep every
 # admission check and complete-key collision comparison before that return.
 s=once(s,needle,needle+old)
 p.write_text(s,newline='\n')
