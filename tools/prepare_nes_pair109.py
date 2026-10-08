# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT
from nes_pair109 import manifest,verify,digest,require,MARKERS,REPORT

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence105','evidence108','integration','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;require(not o.exists(),'output already exists')
 def archive(path,meta):
  require(digest((path/'manifest.json').read_bytes())==json.loads((ROOT/f'analysis/{meta}-verification.json').read_bytes())['manifest_sha256'],'archive differs')
  pins=json.loads((path/'manifest.json').read_bytes())['files']
  def read(n):
   b=(path/n).read_bytes();require(digest(b)==pins[n],'input differs: '+n);return b
  return read
 old=archive(a.evidence105,'pair105');new=archive(a.evidence108,'css108')
 integration={}
 for name,count in [('normal02',20),('fat32-96-01',3),('fault03',15)]+[('negative-'+x+'-01',1) for x in ['begin','end','nconfig','sticky']]:
  r=a.integration/name/'result.json';m=json.loads(r.read_bytes());require(len(m['cases'])==count,'integration count differs')
  for n,h in m['production_sources'].items():require(digest(new('arm02/src/'+n))==h,'integration source differs')
  for index,case in enumerate(m['cases']):
   log=a.integration/name/f'case-{index}.log';require(digest(log.read_bytes())==case['log_sha256'],'integration log differs')
   require((case['exit']!=0) if m['mutation'] else (case['exit']==0),'integration failed')
  integration[name]=digest(r.read_bytes())
 blobs={n:old('review02/files/'+n) for n in manifest()['files'] if n!='arm108.stm'}
 blobs['arm108.stm']=new('arm02/src/obj-nes-100/firmware.stm')
 source=new('arm02/src/nes_menu_diagnostic.c').decode();fw=blobs['arm108.stm']
 tokens=[*MARKERS,REPORT,'/sd2snes/fpga_n86.bi3','/sd2snes/nes/fine_x.nes','/sd2snes/nes/banks32.nes','PREPARED_RESET_HELD','RETURN_READY_RESET_RELEASED']
 for t in tokens:require(t in source and t.encode() in fw,'missing token: '+t)
 require('save_report("PREPARED_RESET_HELD",true)' in source and 'save_report("RETURN_READY_RESET_RELEASED",false)' in source,'persistence boundary differs')
 require(b'CF86-CSS108' in fw,'version missing')
 o.mkdir(parents=True);(o/'files').mkdir()
 for n,b in blobs.items():(o/'files'/n).write_bytes(b)
 (o/'manifest.json').write_text(json.dumps(manifest(),indent=2)+'\n',encoding='utf-8')
 mh=digest((o/'manifest.json').read_bytes());result=verify(o,mh)
 result.update(manifest_sha256=mh,integration=integration,source_binary_tokens=len(tokens),new_arm=False,new_asm=False,physical=False)
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 shutil.copy2(__file__,o/'executed-prepare109.py');print(json.dumps(result))
if __name__=='__main__':main()
