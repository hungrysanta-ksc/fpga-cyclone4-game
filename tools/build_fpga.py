"""Build the exported C44 FPGA inputs without relaxing any timing constraint."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);p.add_argument('--rle',type=Path,required=True);a=p.parse_args()
out=a.out.resolve()
if not str(out).isascii():raise SystemExit('Use an ASCII output path for Quartus')
shutil.copytree(ROOT/'src/fpga',out)
exe='.exe' if (a.quartus_bin/'quartus_map.exe').exists() else ''
for phase in ['map','fit','sta','asm']:
 log=out/('quartus_'+phase+'.log')
 with log.open('w') as f:
  result=subprocess.run([str(a.quartus_bin/('quartus_'+phase+exe)),'pin'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
 if result.returncode:raise SystemExit('Quartus failed; inspect '+str(log))
 print('Completed',phase,flush=True)
summary=(out/'output_files/pin.sta.summary').read_text()
slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*([-\d.]+)',summary,re.M)]
if len(slacks)<40 or min(slacks)<0:raise SystemExit('Constrained timing check failed')
maplog=(out/'quartus_map.log').read_text()
if 'BootROMs/cgb_boot_packed.mif' not in maplog or 'setting all initial values to 0' in maplog:raise SystemExit('Boot initialization check failed')
rbf=out/'output_files/pin.rbf';target=out/'fpga_egbc.bi3'
subprocess.run([str(a.rle.resolve()),str(rbf),str(target)],check=True)
data=target.read_bytes();raw=rbf.read_bytes();decoded=bytearray();i=0
while i<len(data):
 value=data[i];i+=1
 if value==0x9b:decoded.append(data[i]);i+=1
 elif value in (0x5b,0x77):
  byte=data[i];count=data[i+1];i+=2
  if value==0x77:count|=data[i]<<8;i+=1
  decoded.extend(bytes([byte])*count)
 else:decoded.append(value)
if decoded[:len(raw)]!=raw or decoded[len(raw):] not in (b'',raw[-1:]):raise SystemExit('RLE round-trip failed')
expected=json.loads((ROOT/'release/c44-artifacts.json').read_text())['files']['fpga_egbc.bi3']['sha256']
actual=hashlib.sha256(data).hexdigest()
result=dict(constrained_timing_pass=True,slack_checks=len(slacks),minimum_slack=min(slacks),rle_roundtrip=True,sha256=actual,identical_to_tested_c43=actual==expected)
(out/'rebuild-verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if actual!=expected:raise SystemExit('New placement is not the tested C44 binary; preserve the release payload and validate separately')
