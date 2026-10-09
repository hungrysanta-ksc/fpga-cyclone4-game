# SPDX-License-Identifier: MIT
"""Pinned127 integration, staged decoder and local diagnostic reset release."""
from pathlib import Path
import json,shutil
from nes_loader127 import ROOT,sha,put,replace
def materialize(o,baseline,full=False):
 e=baseline/'nes-loader127/evidence';m=json.loads((ROOT/'analysis/loader127-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='fit02/'
 names=[n[len(prefix):] for n in pins if n.startswith(prefix) and n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf'))]
 if not full:names=[n for n in names if '/' not in n and n.endswith('.sv')]
 inputs={}
 for n in names:
  src=e/prefix/n;assert sha(src)==pins[prefix+n];dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_rom_spi128.sv',o/'nes_rom_spi.sv')
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_rom_loader128.sv',o/'nes_rom_loader.sv')
 p=o/'nes_rom_boot.sv';s=p.read_text()
 # The reader emits CHECK response only from its registered RELEASE state.
 # Leaving CHECK with no RUN asynchronously resets that register; RUN can only
 # start after FINISH has left CHECK. Do not add loader RUN to the response path.
 s=replace(s,'assign check_response=check_active && raw_check_response;',
  'assign check_response=raw_check_response; //128 registered response, canceled by reader_reset')
 # CHECK can only own an already loaded READY image. Illegal commands latch
 # check_failed on that edge: START cannot export RUN, BEGIN cannot write, and
 # DATA/END are illegal in READY. The sticky latch blocks all later commands.
 # Retain this latch gate, avoiding the redundant combinational CHECK gate.
 assert s.count(' && !check_enable && !check_failed')==4
 s=s.replace(' && !check_enable && !check_failed',' && !check_failed')
 put(p,s)
 if full:
  p=o/'nes_live_joint.sv';s=p.read_text()
  s=replace(s,'nes_spi_boot loader_boot(.clk(clk),.mem_clk(mem_clk),.reset(!external_memory_ready)',
   'wire diagnostic_reset;\n nes_domain_reset124 diagnostic_release(.clk(mem_clk),.raw_reset(!external_memory_ready),.reset(diagnostic_reset));\n nes_spi_boot loader_boot(.clk(clk),.mem_clk(mem_clk),.reset(diagnostic_reset)')
  put(p,s)
 put(o/'materialization128.json',json.dumps(dict(inputs=inputs,outputs={p.relative_to(o).as_posix():sha(p) for p in o.rglob('*') if p.is_file()}),indent=2)+'\n')
