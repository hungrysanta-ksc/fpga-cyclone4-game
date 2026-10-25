# SPDX-License-Identifier: MIT
import os,shutil,inspect
import probe_nes_expand325 as old
from nes_joint327 import native
from nes_joint328 import apply
from nes_delta231 import ROOT,sha,once
engine=old.old.engine
previous_init=engine.ARM296.__init__
def observed_init(self,*args,**kwargs):
    previous_init(self,*args,**kwargs)
    if 'issue_map327' in self.symbols:self.watch317[self.symbols['issue_map327']&~1]='issue_map327'
engine.ARM296.__init__=observed_init
previous=engine.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0]
    joint=os.environ.get('NES328_ARM_ONLY')!='1'
    if joint:apply(d)
    # Retain the same observation-only ROM and direct-scan assertions as327.
    # Extract the literal rather than importing its engine-mutating runner.
    import ast
    tree=ast.parse((ROOT/'tools/probe_nes_joint327.py').read_text())
    observation=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'integer seen_frame327' in n.value)
    if not joint:observation=observation[:observation.index(' integer expected_count327')]+ ' task clear_output;'
    p=d/'joint266_tb.sv';s=p.read_text();s=once(s,' task clear_output;',observation)
    p.write_text(s,newline='\n')
    for n in ('nes_joint328.py','probe_nes_joint328.py','nes_joint327.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
