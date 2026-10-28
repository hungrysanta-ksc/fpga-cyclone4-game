# SPDX-License-Identifier: MIT
"""Bind the unit-tested 404 staging experiment to the 402 funded image.

This is a partial integration: it does not replace the host VM or raster/lease.
"""
import argparse
import json
import shutil
from pathlib import Path

from nes_delta231 import BASE, sha

p = argparse.ArgumentParser()
p.add_argument('--rtl', required=True, type=Path)
p.add_argument('--candidate', required=True, type=Path)
a = p.parse_args()
d = a.rtl.resolve()
stage = d / 'nes_stage396.sv'
assert sha(stage) == sha(BASE / 'probes/nes-joint402/build07/nes_stage396.sv')
assert sha(a.candidate) == sha(BASE / 'probes/nes-stage404/test04/nes_stage396.sv')
shutil.copyfile(a.candidate, stage)
p = d / 'manifest402.json'
m = json.loads(p.read_text())
assert 'nes_stage396.sv' in m['RTL']
m['RTL']['nes_stage396.sv'] = sha(stage)
m.update(stage404_shared_stamp=True, host_VM_replaced=False,
         raster_lease_replaced=False, whole_path_improvement_claimed=False)
p.write_text(json.dumps(m, indent=2) + '\n', newline='\n')
print(json.dumps({'stage': sha(stage), 'ARM': m['ARM'], 'sources': len(m['RTL'])}))
