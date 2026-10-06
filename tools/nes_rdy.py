"""Retain NMI edges while mode00 RDY blocks a read. SPDX-License-Identifier: MIT."""
from pathlib import Path
import difflib,json,sys
import nes_branch_irq as irq
original_fix=irq.fix

def fix(path):
 prior_diff=original_fix(path);assert irq.branch.base.sha(path)=='c7c8647f6293f6ea7a949892f8e666341ba23426167ae6c3d0d83a55ca00d065'
 original=path.read_text();old='if IR(4 downto 0)/="10000" or Jump/="01" then -- delay interrupts during branches'
 new='if IR(4 downto 0)/="10000" or Jump/="01" or (Mode_r = "00" and really_rdy = \'0\') then -- delay interrupts during branches'
 assert original.count(old)==1;text=original.replace(old,new)
 old='if NMI_n_o = \'1\' and (NMI_n = \'0\' and (IR(4 downto 0)/="10000" or Jump/="01")) then'
 new='if NMI_n_o = \'1\' and (NMI_n = \'0\' and (IR(4 downto 0)/="10000" or Jump/="01" or (Mode_r = "00" and really_rdy = \'0\'))) then'
 assert text.count(old)==1;text=text.replace(old,new);path.write_text(text,encoding='utf-8',newline='\n')
 (path.parents[2]/'rdy-nmi-fix.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='irq-012/rtl/t65/T65.vhd',tofile='rdy-014/rtl/t65/T65.vhd')),encoding='utf-8',newline='\n');return prior_diff

def main():
 out=Path(sys.argv[sys.argv.index('--out')+1]);irq.fix=fix
 try:irq.main()
 finally:
  p=out/'build.json'
  if p.exists():
   m=json.loads(p.read_text());m['candidate']='NES-P2-RDY-014';m['rdy_driver_sha256']=irq.branch.base.sha(Path(__file__));m['rdy_fix_diff_sha256']=irq.branch.base.sha(out/'rdy-nmi-fix.diff');m['scope']='Local mode00 RDY read-stall NMI edge retention; no general DMA/MMIO/hardware claim.';p.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
