"""Preserve an early IRQ poll across a taken page-cross branch. SPDX-License-Identifier: MIT."""
from pathlib import Path
import difflib,json,sys
import nes_branch as branch
original_fix=branch.fix_branch

def fix(path):
 prior_diff=original_fix(path);original=path.read_text()
 old="          IRQ_n_o <= IRQ_n;"
 new="""          -- Local mode00 branch fix: retain either eligible IRQ poll.
          -- IRQ_n_o is active low; do not discard the early poll on page cross.
          if Mode_r = "00" and IR(4 downto 0) = "10000" and
             MCycle = Cycle_2 and PCAdder(8) = '1' then
            IRQ_n_o <= IRQ_n_o and IRQ_n;
          else
            IRQ_n_o <= IRQ_n;
          end if;"""
 assert original.count(old)==1;updated=original.replace(old,new);path.write_text(updated,encoding='utf-8',newline='\n')
 out=path.parents[2];(out/'irq-sampling-fix.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='branch-011/rtl/t65/T65.vhd',tofile='irq-012/rtl/t65/T65.vhd')),encoding='utf-8',newline='\n')
 return prior_diff

def main():
 out=Path(sys.argv[sys.argv.index('--out')+1]);branch.fix_branch=fix
 try:branch.main()
 finally:
  p=out/'build.json'
  if p.exists():
   m=json.loads(p.read_text());m['candidate']='NES-P2-BRANCH-IRQ-012';m['irq_driver_sha256']=branch.base.sha(Path(__file__));m['irq_fix_diff_sha256']=branch.base.sha(out/'irq-sampling-fix.diff');m['scope']='Local branch IRQ poll retention correction; directed ideal-memory scenarios only, not full CPU or hardware validation.';p.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
