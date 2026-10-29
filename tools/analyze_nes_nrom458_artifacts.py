# SPDX-License-Identifier: MIT
"""Pin 457 diagnostic artifacts and cross-check their existing test evidence."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--fit',required=True,type=Path);a=p.parse_args();fit=a.fit.resolve();art=BASE/'probes/nes-nrom458/asm01';program=BASE/'probes/nes-nrom458/program01';romcheck=BASE/'probes/nes-nrom458/romcheck01';live=BASE/'probes/nes-nrom457/live01';fw=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100/firmware.stm';rom=BASE/'probes/nes-nrom428/fixture01/nrom16.nes'
assert sha(fw)=='596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c';assert sha(rom)=='61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c'
assert sha(art/'board.sof')==sha(fit/'output_files/board.sof') and sha(art/'board.rbf')==sha(fit/'board.rbf') and sha(art/'fpga_nrom16.bi3')==sha(fit/'fpga_nrom16.bi3')
pr=json.loads((program/'result.json').read_text());rc=json.loads((romcheck/'result.json').read_text());lr=json.loads((live/'result.json').read_text());assert pr['passed'] and pr['image_sha256']==sha(art/'fpga_nrom16.bi3') and pr['rbf_sha256']==sha(art/'board.rbf');assert rc['passed'] and len(rc['checks'])==1 and rc['checks'][0]['matched_bytes']==4096 and rc['expected_hex_sha256']==sha(art/'sink-program.hex');assert lr['passed'] and lr['rom_sha256']==sha(rom) and lr['consumer']['acks']==33
q=(fit/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);assert len(names)==66
pins={}
for n in names:
 f=fit/n;g=live/n;assert f.is_file() and g.is_file(),n;assert sha(f)==sha(g),n;pins[n]=sha(f)
result={'passed':True,'diagnostic_only':True,'firmware_stm_sha256':sha(fw),'rom_sha256':sha(rom),'sof_sha256':sha(art/'board.sof'),'rbf_sha256':sha(art/'board.rbf'),'bi3_sha256':sha(art/'fpga_nrom16.bi3'),'sink_hex_sha256':sha(art/'sink-program.hex'),'programmer_result_sha256':sha(program/'result.json'),'postfit_result_sha256':sha(romcheck/'result.json'),'live_result_sha256':sha(live/'result.json'),'qsf_source_count':len(pins),'qsf_sources':pins,'scope':'diagnostic 457 Lite fit artifact and host-modeled programmer/65816 evidence, no physical FPGA configuration, SD identity, menu recovery, ARM machine execution or 60fps approval'};(ROOT/'analysis/nrom458-artifacts.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='qsf_sources'}))
