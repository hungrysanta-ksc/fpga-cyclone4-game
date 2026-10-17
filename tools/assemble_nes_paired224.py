# SPDX-License-Identifier: MIT
"""Pair qualified224 route with SNES212; retain223 firmware/file identity."""
import assemble_nes_paired220 as prior
from nes_counter224 import BASE,sha,replace
import json
s=prior.s.replace('preparation220.json','preparation224.json').replace('mif220','mif224').replace('asm220','asm224').replace('cpf220','cpf224').replace('eda220','eda224').replace('result220.json','result224.json').replace('fpga_n220.bi3','fpga_n223.bi3').replace('assemble_nes_paired220.py','assemble_nes_paired224.py').replace('PASS220','PASS224')
s=replace(s," a=p.parse_args();assert", """ a=p.parse_args()
 evidence=json.loads((BASE/'probes/nes-counter224/analysis02.json').read_bytes())
 assert evidence['functional_pass'] and evidence['related_timing_pass'] and evidence['arm_pass']
 assert evidence['conditional_io']['conditional_data_bounds_pass'] and evidence['conditional_io']['native_payload_reset_pass']
 assert a.baseline.resolve()==(BASE/'probes/nes-counter224/mapfit02').resolve()
 assert sha(a.client/'sink-program.hex')==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
 assert""")
ns=dict(prior.ns);ns.update(BASE=BASE);ns['__file__']=__file__;exec(compile(s,'assemble224','exec'),ns)
if __name__=='__main__':ns['main']()
