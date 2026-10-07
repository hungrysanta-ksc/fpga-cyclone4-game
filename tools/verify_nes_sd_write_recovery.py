# SPDX-License-Identifier: MIT
"""Frozen073 retry audit; actual hardware success is still pending."""
from pathlib import Path
import argparse,hashlib,json,re,zlib,zipfile
from check_nes_sd_inventory073 import check
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def audit(e):
    meta=load(ROOT/'analysis/sd-write-recovery-verification.json');assert sha(e/'manifest.json')==meta['manifest_sha256'];m=load(e/'manifest.json')
    assert len(m['files'])==meta['archived_files']
    for n,h in m['files'].items():
        p=(e/n).resolve();assert p.is_relative_to(e.resolve()) and sha(p)==h,n
    for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h and sha(e/'public-source'/n)==h,n
    host=load(e/'host/result.json');assert [host[n] for n in ['collector_checks','writer_checks','platform_sessions','report_checks']]==[52,23,6,29] and not host['physical_SD']
    check((e/'host/SYNTHETIC-NOT-HARDWARE.TXT').read_bytes())
    normal=load(e/'integration/result.json');assert normal['checks']==40 and normal['exit']==0 and not normal['physical_SD']
    log=(e/'integration/integration.log').read_text();assert all('REPRO072 FAT'+n+' result=4 writes=0' in log for n in ['16','32'])
    mutation=load(e/'mutation/result.json');assert mutation['mutation'] and mutation['exit']!=0
    assert 'sdinv_write_report(data,sizeof(data),path,sizeof(path))==0' in (e/'mutation/integration.log').read_text()
    pins=load(ROOT/'analysis/sd-write-recovery-inputs.json');assert pins==normal['inputs']
    for n,h in pins.items():assert sha(e/'arm/source/src'/n)==h,n
    for n,h in load(e/'arm/build-inputs.json').items():assert sha(e/'arm/source'/n)==h,n
    fw=(e/'arm/firmware.stm').read_bytes();assert len(fw)==133184 and sha(e/'arm/firmware.stm')=='cd7eea7ae61cca3be60a8c5f876a09dbd29e0c6669ccba53462c035b654de5e7'
    assert fw[:4]==b'STM3' and int.from_bytes(fw[8:12],'little')==len(fw)-512 and int.from_bytes(fw[12:16],'little')==zlib.crc32(fw[512:]) and b'SDINFO073-BASE069' in fw
    writer=(e/'arm/writer-disassembly.txt').read_text();assert writer.count('<nes_return_log_allow>')==2 and '<nes_diag_active>' in writer
    main=(e/'arm/main-disassembly.txt').read_text();calls=re.findall(r'\bbl(?:\.w)?\s+\w+\s+<([^>]+)>',main);assert calls[-1]=='sdinv_run'
    run=(e/'arm/run-disassembly.txt').read_text();assert run.rfind('<snes_bootprint_center>')<run.rfind('<nes_return_failed>')<run.index('<nes_diag_leave>')
    kit=load(e/'kit/manifest.json');assert kit['payload_paths']==['sd2snes/firmware.stm'] and not kit['physical_execution'] and not kit['nes_pair_installable']
    with zipfile.ZipFile(e/'kit/FXPAK-SDINFO073-SD.zip') as z:assert hashlib.sha256(z.read('sd2snes/firmware.stm')).hexdigest()==kit['firmware']['sha256'] and json.loads(z.read('manifest.json'))==kit
    observed=load(e/'observed/user-observation.json');assert observed['identity']=='SDINFO072-BASE069' and observed['save_code']==4 and observed['TXT_created_reported'] is False and observed['hardware073_success'] is False
    print('PASS073 frozen='+str(len(m['files']))+' FatFS40/window mutation1/52+23+6+29/ARM; 072 hardware failure observed,073 retry pending')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);audit(p.parse_args().evidence)
