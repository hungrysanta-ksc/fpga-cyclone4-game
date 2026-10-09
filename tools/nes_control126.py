# SPDX-License-Identifier: MIT
"""Explicit bridge synchronizers: reuse mapped124 DB, rerun fitting + timing."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put

def check_archive(path,meta):
 assert sha(path/'manifest.json')==meta['manifest_sha256']
 return json.loads((path/'manifest.json').read_bytes())['files']

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline124','baseline125','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii();o.mkdir()
 e=a.baseline124;f=a.baseline125
 pins=check_archive(e,json.loads((ROOT/'analysis/reset124-verification.json').read_bytes()))
 pins125=check_archive(f,json.loads((ROOT/'analysis/cdc125-verification.json').read_bytes()))
 for n,h in pins.items():
  if n.startswith('fit01/'):assert sha(e/n)==h,n
 baseline=o/'baseline';shutil.copytree(e/'fit01',baseline)
 r=json.loads((f/'sta03/result125.json').read_bytes());assert sha(f/'sta03/result125.json')==pins125['sta03/result125.json']
 first=sorted({v['to'] for v in r['unexcepted_controls']});assert len(first)==6
 chains=[('control','control'+str(i),n,n[:-2]+'1]') for i,n in enumerate(first)]
 release=['nes_domain_reset124:core_release|release_reset','nes_rom_physical:physical|memory_reset','nes_transport:transport|nes_domain_reset124:host_release|release_reset','nes_domain_reset124:init_release|release_reset']
 chains += [('release','release'+str(i),n+'[0]',n+'[1]') for i,n in enumerate(release)]
 put(baseline/'chains126.tcl','set chains126 {\n'+''.join(' {'+k+' '+l+' {'+x+'} {'+y+'}}\n' for k,l,x,y in chains)+'}\n')
 shutil.copy2(ROOT/'tools/nes_control126.tcl',baseline/'control126.tcl')
 shutil.copy2(__file__,o/'executed-control126.py')
 def run(where,tool,args,label,timeout=600):
  with (where/(label+'.log')).open('wb') as log:
   r=subprocess.run([str(a.quartus_bin/(tool+'.exe')),*args],cwd=where,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
  assert r.returncode==0,label
 run(baseline,'quartus_sta',['-t','control126.tcl'],'control126')
 candidate=o/'candidate';shutil.copytree(baseline,candidate)
 settings=[]
 for n in first:
  if 'nes_packet_cdc_ram:bridge|' not in n:continue
  for reg in [n,n[:-2]+'1]']:
   # QSF node names use instance paths, not TimeQuest entity:instance names;
   # QSF's assignment parser retains braces literally instead of Tcl quoting.
   target='|'.join(part.split(':')[-1] for part in reg.split('|'))
   settings.append('set_instance_assignment -name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS -to '+target)
 assert len(settings)==8
 put(candidate/'synchronizers126.qsf','\n'.join(settings)+'\n')
 put(candidate/'live.qsf',(candidate/'live.qsf').read_text()+'\n# Exact four bridge chains; both registers must be marked.\n'+ '\n'.join(settings)+'\n')
 run(candidate,'quartus_fit',['live'],'fit126')
 assert 'Ignored assignment' not in (candidate/'fit126.log').read_text(errors='replace')
 run(candidate,'quartus_sta',['live'],'sta126')
 run(candidate,'quartus_sta',['-t','control126.tcl'],'control126')
 for n in ['inventory125.tcl','bundled125.sdc','pairs125.tcl','constraints125.tcl']:
  src=f/'sta03'/n;assert sha(src)==pins125['sta03/'+n];shutil.copy2(src,candidate/n)
 run(candidate,'quartus_sta',['-t','inventory125.tcl'],'inventory125')
 run(candidate,'quartus_sta',['-t','constraints125.tcl'],'constraints125')
 result=dict(candidate='NES-CONTROL-CDC-126',tool_phases_passed=True,base124_manifest=sha(e/'manifest.json'),base125_manifest=sha(f/'manifest.json'),chains=chains,assignments=settings,rtl_changed=False,map_rerun=False,fit_rerun=True,full_timing_pass=False,mtbf_signoff=False,installable=False)
 put(o/'result126.json',json.dumps(result,indent=2)+'\n');print('PASS126 tool phases; inspect topology/timing/data constraints before acceptance')
if __name__=='__main__':main()
