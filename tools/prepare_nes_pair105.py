# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile,shutil
from nes_spi_boot import ROOT
from nes_pair105 import manifest,verify,digest,require,MARKERS,REPORT

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence104','restore091','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence104;o=a.out;require(not o.exists(),'output already exists')
 meta=json.loads((ROOT/'analysis/timer104-verification.json').read_bytes())
 require(digest((e/'manifest.json').read_bytes())==meta['manifest_sha256'],'104 manifest differs')
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 def pinned(n):
  b=(e/n).read_bytes();require(digest(b)==pins[n],'104 input differs: '+n);return b
 blobs={'arm104.stm':pinned('arm01/src/obj-nes-100/firmware.stm')}
 for dst,src in [('cf86.packed','diag.packed'),('cf86.raw','diag.raw'),('base.packed','base.packed'),('base.raw','base.raw'),('menu.bin','menu.bin'),('fixture80.nes','fixture.nes')]:blobs[dst]=pinned('main02/'+src)
 blobs['fixture96.nes']=pinned('fat32-96-02/fixture.nes')
 require(digest(a.restore091.read_bytes())=='99bfc70a2fd468945d163d4388db4f5d65d1f440d98fd6a3c6684faf285c24e2','091 archive differs')
 with zipfile.ZipFile(a.restore091) as z:blobs['restore044.stm']=z.read('restore/sd2snes/firmware.stm')
 for i in range(2):blobs[f'marker{i}.empty']=b''
 source=pinned('arm01/src/nes_menu_diagnostic.c').decode();fw=blobs['arm104.stm']
 tokens=[*MARKERS,REPORT,'/sd2snes/fpga_n86.bi3','/sd2snes/nes/fine_x.nes','/sd2snes/nes/banks32.nes','PREPARED_RESET_HELD','RETURN_READY_RESET_RELEASED']
 for t in tokens:require(t in source and t.encode() in fw,'missing source/binary token: '+t)
 require('save_report("PREPARED_RESET_HELD",true)' in source and 'save_report("RETURN_READY_RESET_RELEASED",false)' in source,'report persistence boundary differs')
 require(b'CF86-IRQ104' in fw,'firmware version missing')
 o.mkdir(parents=True);(o/'files').mkdir()
 for n,b in blobs.items():(o/'files'/n).write_bytes(b)
 (o/'manifest.json').write_text(json.dumps(manifest(),indent=2)+'\n',encoding='utf-8')
 mh=digest((o/'manifest.json').read_bytes());result=verify(o,mh)
 result.update(manifest_sha256=mh,source_binary_tokens=len(tokens),source_sha256=digest(source.encode()),source_evidence_manifest=meta['manifest_sha256'],new_arm=False,new_asm=False,physical=False)
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 (o/'report-source.c').write_text(source,encoding='utf-8');shutil.copy2(__file__,o/'executed-prepare105.py')
 print(json.dumps(result))
if __name__=='__main__':main()
