# SPDX-License-Identifier: MIT
"""Retained325 RTL faults under the new ARM early-manifest schedule."""
import inspect
import guard_nes_expand325 as base

def main():
    base.old.CASES[11]='STOP during early expected storage on325 RTL'
    s=inspect.getsource(base.main).replace('probe_nes_expand325.py','probe_nes_joint328.py')
    marker=' ns=dict(old.__dict__);'
    assert s.count(marker)==1
    s=s.replace(marker,''' s=s.replace('  else $fatal(1,"unknown guard319");','  else if(NEG319==11)wait(dut.flow.canonical_write313&&dut.flow.header[0]==15&&dut.flow.manifest_byte313==8);\\n  else $fatal(1,"unknown guard319");')
 s=s.replace('if(NEG319<=4||NEG319==7||NEG319==8)begin','if(NEG319<=4||NEG319==7||NEG319==8||NEG319==11)begin')
 ns=dict(old.__dict__);''')
    ns=dict(base.__dict__);exec(compile(s,'guard_arm328','exec'),ns);ns['main']()

if __name__=='__main__':main()
