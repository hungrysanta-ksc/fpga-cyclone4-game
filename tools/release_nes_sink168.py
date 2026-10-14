# SPDX-License-Identifier: MIT
"""Package MCU-only168 with byte-identical deployed167 FPGA and164 restore."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','arm-check','test','report','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert sha(a.prior)=='99f9cf595766146d8d86c254d607d2f717eea8a4a0b491ae41cc6117584b709b'
 ar=json.loads((a.arm_check/'result.json').read_bytes());t=json.loads((a.test/'result.json').read_bytes());report=json.loads((a.report/'result.json').read_bytes())
 assert ar['passed'] and ar['remaining_margin']>=1024 and ar['trace_bytes']==32 and t['passed'] and report['passed']
 assert sha(a.arm/'src/nes_menu_diagnostic.c')==report['source_sha256']
 for v in [ar,t]:
  for n,h in v['public_sources'].items():assert sha(ROOT/n)==h,n
 prep=json.loads((a.arm/'preparation-sink168.json').read_bytes())
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(a.arm/n)==h,n
 source_comparison={}
 for n in ['nes_native_sink165.c','nes_native165.c','nes_sink_trace168.c']:
  # Windows host fixture writes CRLF; ARM materializer writes LF.
  # Preserve both executed byte hashes; accept only newline normalization.
  arm_bytes=(a.arm/'src'/n).read_bytes();test_bytes=(a.test/n).read_bytes()
  assert arm_bytes.replace(b'\r\n',b'\n')==test_bytes.replace(b'\r\n',b'\n'),n
  source_comparison[n]=dict(arm=sha(a.arm/'src'/n),host=sha(a.test/n),newline_only=True)
 fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
 digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
 with zipfile.ZipFile(a.prior) as z:
  prior=json.loads(z.read('manifest.json'))
  for n,item in prior['files'].items():
   b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
   if n.startswith(('01-GAME167-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
    dst=n.replace('167','168') if n.startswith('01-') else n;blobs[dst]=b
    if dst!='01-GAME168-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
 blobs['01-GAME168-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
 fpga=blobs['01-GAME168-SD-ROOT/sd2snes/fpga_n168.bi3'];assert digest(fpga)=='d1e8278212164ecce5ec1161ca9f469ad710debc4e7ffe2c2c9d0450bd356bf2'
 blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game168-ready.ko.md').read_bytes()
 decision=dict(trial_ready=True,physical=False,video_fix_claimed=False,fpga_identical_to167=True,trace_bytes=32,trace_report_bytes=169,run_ticks=6000,run_sd_writes=False,save_sram_used=False,stack_margin=ar['remaining_margin'],next='Inspect first failed packet and12B ACK; no blind retry, validation removal or budget increase.')
 blobs['decision168.json']=(json.dumps(decision,indent=2)+'\n').encode()
 manifest=dict(package='NES168-SMB3-SINK-RESPONSE',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
 blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
 archive=a.out/'NES168-SMB3-SINK-RESPONSE.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in blobs.items():
   info=zipfile.ZipInfo(n,(2026,10,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(blobs)
  for n,b in blobs.items():assert z.read(n)==b,n
 for n,h in preserved.items():assert digest(blobs[n])==h,n
 for n in ['START-HERE.ko.md','manifest.json','decision168.json']:(a.out/n).write_bytes(blobs[n])
 result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(fpga),preserved=preserved,source_comparison=source_comparison,public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_sink168.py','docs/nes-game168-ready.ko.md']},physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='preserved'}))
if __name__=='__main__':main()
