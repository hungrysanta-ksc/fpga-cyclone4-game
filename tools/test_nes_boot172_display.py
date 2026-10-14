# SPDX-License-Identifier: MIT
"""One banked display sequence after172 startup; reuse the169 pixel oracle."""
import inspect
import test_nes_banked169 as prior
from nes_boot172 import build
source=inspect.getsource(prior.main)
source=source.replace('a=p.parse_args()',"p.add_argument('--reference',type=Path,required=True)\n a=p.parse_args()")
source=source.replace("results=[]", "shutil.copytree(a.reference,a.out/'budget-reference')\n results=[]")
source=source.replace("([('stop',False)] if a.stop_only else [('overflow',True),('budget',True),('overflow',False),('budget',False),('stop',False)])", "[('budget',False)]")
source=source.replace("sources=['tools/nes_banked169.py'", "sources=['tools/nes_boot172.py','tools/test_nes_boot172_display.py','tools/nes_banked169.py'")
source=source.replace("result=dict(passed=True", "result=dict(reference_reused={f.name:sha(f) for f in a.reference.glob('frame-*.rgb')},passed=True")
namespace=dict(prior.__dict__);namespace['build']=build
exec(compile(source,'boot172_display','exec'),namespace)
if __name__=='__main__':namespace['main']()
