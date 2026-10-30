# SPDX-License-Identifier: MIT
"""Pack the source-pinned489 full RBF after FIT and related timing gates."""
import argparse,csv,json
from pathlib import Path
from nes_cf68_pair_preflight import encode,decode
from check_nes_game478 import sha
p=argparse.ArgumentParser(description=__doc__)
for n in ['board','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();pins=json.loads((a.board/'source-pins.json').read_text())
for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
assert 'Successful'in(a.board/'output_files/board.fit.summary').read_text()
for view in ['implementation','nominal']:
 rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'))
 assert all(float(x['slack'])>=0 for x in rows if((x['from_clock']=='nes')==(x['to_clock']=='nes')))
raw=(a.board/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
a.out.mkdir(parents=True,exist_ok=False);(a.out/'fpga_mmc489.bi3').write_bytes(packed)
r={'passed':True,'scope':__doc__,'source_inputs':pins['board_inputs'],'RBF_SHA256':sha(a.board/'output_files/board.rbf'),'BI3_SHA256':sha(a.out/'fpga_mmc489.bi3'),'BI3_bytes':len(packed),'fit_report_SHA256':sha(a.board/'output_files/board.fit.rpt'),'physical':False}
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'passed':True,'BI3_bytes':len(packed)}))
