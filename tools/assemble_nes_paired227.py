# SPDX-License-Identifier: MIT
"""Update only the4KiB SNES ROM in qualified224 route, no MAP/FIT."""
import assemble_nes_paired220 as prior
from nes_runtime213 import once,BASE,sha
import json
s=prior.s.replace('preparation220.json','preparation224.json')
for a,b in [('mif220','mif227'),('asm220','asm227'),('cpf220','cpf227'),('eda220','eda227'),
 ('result220.json','result227.json'),('fpga_n220.bi3','fpga_n227.bi3'),
 ('assemble_nes_paired220.py','assemble_nes_paired227.py'),('PASS220','PASS227')]:s=s.replace(a,b)
s=once(s," a=p.parse_args();assert",""" a=p.parse_args()
 evidence=json.loads((BASE/'probes/nes-counter224/analysis02.json').read_bytes())
 assert evidence['functional_pass'] and evidence['related_timing_pass']
 assert evidence['conditional_io']['conditional_data_bounds_pass'] and evidence['conditional_io']['native_payload_reset_pass']
 assert a.baseline.resolve()==(BASE/'probes/nes-counter224/mapfit02').resolve()
 assert json.loads((a.client/'build.json').read_bytes())['sink_version']=='2271'
 assert""")
ns=dict(prior.ns);ns.update(BASE=BASE);ns['__file__']=__file__;exec(compile(s,'assemble227','exec'),ns)
if __name__=='__main__':ns['main']()
