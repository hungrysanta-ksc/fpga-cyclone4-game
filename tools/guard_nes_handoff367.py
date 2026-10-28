# SPDX-License-Identifier: MIT
"""Final local store releases raw0/1/2 before a deliberately blocked wire tail."""
import guard_nes_handoff366 as old
from nes_delta231 import ROOT
if __name__=='__main__':
 old.TB=old.TB.replace('reg released=0;','')
 old.TB=old.TB.replace('reg response=0;', 'reg released=0;integer drain367=0;wire sink367=!released||drain367>=256;\n reg response=0;')
 old.TB=old.TB.replace('aq<=memory[aa];', 'if(released)begin drain367<=drain367+1;data<=64\'hdeaddeaddeaddead;end\n  aq<=memory[aa];')
 old.TB=old.TB.replace('seals++;released<=1;', 'if(dut.state!=dut.BLOCKEND||dut.cursor!=4398+RAW*256)$fatal(1,"not final committed store");\n   seals++;released<=1;')
 old.TB=old.TB.replace('if(byte_valid)begin', 'if(byte_valid&&sink367)begin')
 old.TB=old.TB.replace('if(seals!=1||!released)', 'if(drain367<256||seals!=1||!released)')
 s=(ROOT/'tools/guard_nes_handoff366.py').read_text()
 a=s.index('def main():');s=s[a:]
 s=s.replace("record_ready=\"1'b1\",byte_ready=\"1'b1\"", "record_ready='sink367',byte_ready='sink367'")
 env=dict(old.__dict__);env['TB']=old.TB
 exec(compile(s,'guard_handoff367','exec'),env);env['main']()
