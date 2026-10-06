# SPDX-License-Identifier: MIT
"""Audit054 immutable raw evidence supplied explicitly; not a new simulation."""
from pathlib import Path
import argparse,json,re,hashlib

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();raw=a.evidence
 meta=read(ROOT/'analysis/spi-boot-verification.json')
 for name in ['unit','wave','resource']:
  folder=raw/name;result=read(folder/'result.json')
  for n,h in result['sources'].items():assert sha(folder/n)==h,(name,n)
  for n in ['nes_rom_spi','nes_spi_boot','nes_rom_loader','nes_rom_boot','nes_rom_physical']:
   assert sha(folder/(n+'.sv'))==sha(ROOT/'src/nes'/(n+'.sv')),(name,n)
 for n,h in read(raw/'wave/result.json')['firmware_sources'].items():
  assert sha(raw/'wave'/n)==h
  path=ROOT/('tests/nes-functional' if n=='rom_spi_capture.c' else 'src/nes/firmware')/n
  assert sha(path)==h,n
 for name,marker in [('unit','PASS SPI BOOT checks=163894 reads=81921 negative_cases=14 pin_bytes=81920'),
                     ('wave','PASS SPI MCU WAVE samples=8896 checked=7784 pin_bytes=64 legacy_queries=4 pll_loss=1')]:
  log=(raw/name/'vsim.log').read_text(errors='replace')
  assert marker in log and not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  assert sha(raw/name/'vsim.log')==meta['logs'][name]
 assert not (raw/'wave/arm_compile.log').read_text().strip()
 assert sha(raw/'wave/nes_rom_spi.o')==meta['arm_object_sha256']
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace')
 summary=(raw/'resource/output_files/live.fit.summary').read_text(errors='replace')
 assert 'Fitter Status : Successful' in summary
 lab=int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1])
 le=int(re.search(r'Total logic elements : ([0-9,]+)',summary)[1].replace(',',''))
 m9k=int(re.search(r'; M9Ks\s*; (\d+) /',report)[1]);assert (le,lab,m9k)==(13866,948,26)
 log=(raw/'resource/map.log').read_text(errors='replace')
 assert not re.search(r'Warning \((?:10036|10240)\)',log)
 assert not any('Warning' in line and ('nes_rom_spi.sv' in line or 'nes_spi_boot.sv' in line) for line in log.splitlines())
 for e in read(ROOT/'source-manifest.json')['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
 for e in read(ROOT/'cores/nes/publication-sources.json')['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
 for e in read(raw/'manifest.json')['files']:assert sha(raw/e['path'])==e['sha256'],e['path']
 print(json.dumps(dict(candidate=meta['candidate'],checks=163894,read_bytes=81921,negative_cases=14,
  C_samples=8896,consumed_bits=7784,LE=le,LAB=lab,LAB_remaining=963-lab,M9K=m9k,
  protected_GBC=152,original_public_sources=334,hardware_baseline='044 unchanged',new_SD_image=False),indent=2))

if __name__=='__main__':main()
