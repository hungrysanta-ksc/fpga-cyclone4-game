"""Audit curated source hashes, Quartus inputs and packed open boot image."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'source-manifest.json').read_text())
for item in m['files']:
 f=ROOT/item['path']
 if hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:raise SystemExit('Source changed: '+item['path'])
fp=ROOT/'src/fpga'
for name in re.findall(r'-name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP)_FILE\s+(\S+)',(fp/'pin.qsf').read_text()):
 if not (fp/name.strip('"')).is_file():raise SystemExit('Missing Quartus input: '+name)
def mif(path,size):
 data=[0]*size
 for match in re.finditer(r'^([0-9A-Fa-f]+):\s*(.*?);',path.read_text(),re.M):
  for off,value in enumerate(match[2].split()):data[int(match[1],16)+off]=int(value,16)
 return data
full=mif(fp/'BootROMs/cgb_boot.mif',4096);packed=mif(fp/'BootROMs/cgb_boot_packed.mif',2048)
for addr in list(range(256))+list(range(512,2304)):
 target=(addr&255)|((1 if addr&2048 else (addr>>8)&7)<<8)
 if packed[target]!=full[addr]:raise SystemExit('Packed boot image mismatch')
print('PASS:',len(m['files']),'source hashes, Quartus inputs, 2048 reachable boot bytes')
