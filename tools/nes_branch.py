"""Local T65 branch bus correction; pinned upstream remains unchanged. SPDX-License-Identifier: MIT."""
from pathlib import Path
import difflib,json,sys
import nes_functional as base

PIN_T65='52395e881ade8e7d99717d5082cdb5131a0711aaa2dea1fcf042014f6758d01b'
original_adapter=base.generate_adapter

def fix_branch(path):
 original=path.read_text();assert base.sha(path)=='db702503c364af3124bb97488d639ecaab72c467a7f41a5ea0c0b2b44b97f9a8'
 decl='  signal PCAdder            : unsigned(8 downto 0);'
 assert original.count(decl)==1
 text=original.replace(decl,decl+'\n  signal BranchBusPC        : std_logic_vector(15 downto 0);')
 anchor='  with Set_Addr_To_r select'
 bus="""  -- Local NES branch bus fix: preserve sequential read before page correction.
  -- Combinational only; PC updates, cycle count and saved state are unchanged.
  BranchBusPC <= std_logic_vector(PC)
    when Mode_r = "00" and IR(4 downto 0) = "10000" and MCycle = Cycle_2 else
    std_logic_vector(PC(15 downto 8) - 1) & std_logic_vector(PC(7 downto 0))
    when Mode_r = "00" and IR(4 downto 0) = "10000" and MCycle = Cycle_3 and DL(7) = '0' else
    std_logic_vector(PC(15 downto 8) + 1) & std_logic_vector(PC(7 downto 0))
    when Mode_r = "00" and IR(4 downto 0) = "10000" and MCycle = Cycle_3 and DL(7) = '1' else
    std_logic_vector(PC(15 downto 8)) & std_logic_vector(PCAdder(7 downto 0));

"""
 assert text.count(anchor)==1;text=text.replace(anchor,bus+anchor)
 old='PBR & std_logic_vector(PC(15 downto 8)) & std_logic_vector(PCAdder(7 downto 0)) when Set_Addr_To_PBR;'
 assert text.count(old)==1;text=text.replace(old,'PBR & BranchBusPC when Set_Addr_To_PBR;')
 path.write_text(text,encoding='utf-8',newline='\n')
 return ''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='upstream/rtl/t65/T65.vhd',tofile='local/rtl/t65/T65.vhd'))

def main():
 assert base.sha(Path(base.__file__))=='28524fbf36ee98aae0675c070bf42883afb4489ed1ae499c0f3e4ef5c6a56d1e'
 mapper4='--mapper4' in sys.argv
 if mapper4:
  sys.argv.remove('--mapper4');import nes_mmc3_integrated as mmc3
  assert base.sha(Path(mmc3.__file__))=='94baeb9a26fe0138357f63f391fcef63bc0ab1918c8cb0a21a0861772631f081'
  generate=mmc3.adapter
 else:generate=original_adapter
 out=Path(sys.argv[sys.argv.index('--out')+1])
 def adapter(u,d):
  assert base.sha(u/'rtl/t65/T65.vhd')==PIN_T65
  generate(u,d);diff=fix_branch(d/'rtl/t65/T65.vhd');(d/'branch-bus-fix.diff').write_text(diff,encoding='utf-8',newline='\n')
 base.generate_adapter=adapter
 try:base.main()
 finally:
  p=out/'build.json'
  if p.exists():
   result=json.loads(p.read_text());result['infrastructure_candidate']=result['candidate'];result['candidate']='NES-P2-BRANCH-011';result['branch_driver_sha256']=base.sha(Path(__file__));result['mapper']=4 if mapper4 else 0
   for item in result['sources']:
    if item['path']=='rtl/t65/T65.vhd':item['compiled_sha256']=base.sha(out/item['path']);item['changed']=True
   result['branch_fix_diff_sha256']=base.sha(out/'branch-bus-fix.diff');result['scope']='Local branch bus correction, original ROM diagnostics only; full CPU/IRQ conformance and hardware unverified.';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
