# SPDX-License-Identifier: MIT
"""Recalculate pinned CF86 external envelope; never upgrades physical approval."""
from pathlib import Path
import argparse,json,shutil
from decimal import Decimal
from nes_spi_boot import ROOT,sha
from nes_diag_io_budget import calculate

def ps(n):return int(Decimal(str(n))*1000)
def envelope(budget):
 limits={n:ps(v) for n,v in budget['remaining_external_budget_ns'].items()}
 extra=5000;minimum=min(limits.values());limiting=min(limits,key=limits.get)
 # Use integer ps and require strictly positive residual; equality is no margin.
 max_leg=(minimum-extra-1)//2
 scenarios=[]
 for leg in [20000,max_leg,max_leg+1,60000]:
  margins={n:v-2*leg-extra for n,v in limits.items()}
  scenarios.append(dict(leg_ps=leg,extra_ps=extra,minimum_ps=min(margins.values()),positive=all(v>0 for v in margins.values())))
 return dict(limiting_condition=limiting,remaining_external_ps=minimum,
  equal_leg_max_strict_positive_ps=max_leg,extra_ps=extra,scenarios=scenarios,
  limits_ps=limits,arithmetic_resolution_ps=1,physical_bound_established=False,
  electrical_signoff=False,installable=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence086',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence086;o=a.out;assert not o.exists()
 meta=json.loads((ROOT/'analysis/clock086-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];names=['io01/io-paths.tsv','io01/budget.json','io01/budget-outside.json']
 for n in names:assert sha(e/n)==pins[n],n
 normal=calculate(e/names[0],20,5);outside=calculate(e/names[0],60,5)
 for current,name in [(normal,names[1]),(outside,names[2])]:
  previous=json.loads((e/name).read_bytes());current['candidate']=previous['candidate'];assert current==previous
 r=envelope(normal);assert r['limiting_condition']=='normal_ce_high_tCPH5' and r['remaining_external_ps']==109565
 assert [(x['minimum_ps'],x['positive']) for x in r['scenarios']]==[(64565,True),(1,True),(-1,False),(-15435,False)]
 # Domain checks are exercised in the original calculator; no new route run.
 rejected=[]
 for leg,extra in [(-1,5),(20,-1),(float('nan'),5),(float('inf'),5)]:
  try:calculate(e/names[0],leg,extra)
  except AssertionError:rejected.append(str((leg,extra)))
  else:raise AssertionError('invalid assumption accepted')
 o.mkdir(parents=True)
 for n in names:shutil.copy2(e/n,o/Path(n).name)
 shutil.copy2(__file__,o/'executed-assess106.py')
 r.update(source_manifest_sha256=meta['manifest_sha256'],path_sha256=sha(e/names[0]),path_rows=normal['path_rows'],normal_and_outside_exact_reproduction=True,invalid_inputs_rejected=rejected,physical=False,new_fit=False,new_arm=False)
 (o/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ['limiting_condition','remaining_external_ps','equal_leg_max_strict_positive_ps','scenarios','physical_bound_established']}))
if __name__=='__main__':main()
