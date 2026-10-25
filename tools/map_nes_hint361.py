# SPDX-License-Identifier: MIT
import map_nes_host359 as previous
from nes_hint361 import apply
from nes_delta231 import once
old_patch=previous.patch
def patch(d):
 old_patch(d);apply(d,board=True)
 p=d/'nes_live_joint.sv';s=p.read_text();s=once(s,'nes_plan_path267 retained_plan267(', 'nes_plan_path267 retained_plan267(.prelease361(native_frame_owned&&native_geometry_valid),.epoch361(captured_epoch204),.serial361(source_serial267),');p.write_text(s,newline='\n')
previous.previous.engine.apply=patch
if __name__=='__main__':previous.previous.engine.main()
