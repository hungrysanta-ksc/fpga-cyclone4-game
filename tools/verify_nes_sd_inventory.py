# SPDX-License-Identifier: MIT
"""Read-only audit of private072 evidence, not hardware/install approval."""
from pathlib import Path
import argparse,hashlib,json,re,zlib,zipfile
from check_nes_sd_inventory import check
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def audit(e):
    meta=load(ROOT/'analysis/sd-inspection-verification.json');raw=(e/'manifest.json').read_bytes();assert sha(raw)==meta['manifest_sha256']
    m=json.loads(raw);assert m['candidate']==meta['candidate'] and len(m['files'])==meta['archived_files']
    for n,h in m['files'].items():
        p=(e/n).resolve();assert p.is_relative_to(e.resolve()) and sha(p.read_bytes())==h,n
    for n,h in meta['public_sources'].items():assert sha((ROOT/n).read_bytes())==h and sha((e/'public-source'/n).read_bytes())==h,n
    host=load(e/'tests/result.json');assert [host[k] for k in ['collector_checks','writer_checks','platform_sessions','report_checks']]==[52,23,6,29] and not host['physical_SD']
    for n,h in host['sources'].items():assert sha((e/'public-source'/n).read_bytes())==h,n
    report=check((e/'tests/SYNTHETIC-NOT-HARDWARE.TXT').read_bytes());assert not report['actual_menu_classification'] and not report['nes_pair_installable']
    mut=load(e/'mutation/result.json');assert set(mut)=={'ignore-readback','early-leave'}
    for n,v in mut.items():assert v['exit']!=0 and v['production_unchanged'] and v['assertion'] in (e/'mutation'/n/'run.log').read_text(errors='replace')
    fw=(e/'arm/firmware.stm').read_bytes();assert len(fw)==meta['firmware']['size'] and sha(fw)==meta['firmware']['sha256']
    assert fw[:4]==b'STM3' and int.from_bytes(fw[8:12],'little')==len(fw)-512 and int.from_bytes(fw[12:16],'little')==zlib.crc32(fw[512:])
    assert b'SDINFO072-BASE069' in fw
    main=(e/'arm/main-disassembly.txt').read_text();calls=re.findall(r'\bbl(?:\.w)?\s+\w+\s+<([^>]+)>',main)
    assert calls[-1]=='sdinv_run' and not set(calls)&{'load_rom','cfg_save','nes_rom_verified_start','nes_menu_run'}
    run=(e/'arm/run-disassembly.txt').read_text();assert run.count('<nes_diag_leave>')==1 and run.count('<sdinv_write_report>')==1
    assert run.index('<sdinv_collect>')<run.index('<sdinv_format>')<run.index('<sdinv_write_report>')<run.index('<nes_diag_leave>')
    assert run.rfind('<snes_bootprint_center>')<run.rfind('<nes_return_failed>')<run.index('<nes_diag_leave>')<run.rfind('<snes_reset>')
    assert load(e/'arm/reproduction.json')['changed_inputs_match'] and load(e/'arm/reproduction.json')['pinned069_inputs']==275
    for n,h in load(e/'arm/build-inputs.json').items():assert sha((e/'arm/source'/n).read_bytes())==h,n
    kit=load(e/'kit/manifest.json');assert kit['candidate']==meta['candidate'] and kit['payload_paths']==['sd2snes/firmware.stm'] and not kit['physical_execution'] and not kit['nes_pair_installable']
    with zipfile.ZipFile(e/'kit/FXPAK-SDINFO072-SD.zip') as z:
        assert sha(z.read('sd2snes/firmware.stm'))==meta['firmware']['sha256'];assert json.loads(z.read('manifest.json'))==kit
        assert set(z.namelist())=={'sd2snes/firmware.stm','manifest.json','README.ko.md','LICENSE.txt'}
    print('PASS072 frozen='+str(len(m['files']))+' collector52/writer23/platform6/report29/mutations2; ARM linked, no physical SD')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);audit(p.parse_args().evidence)
