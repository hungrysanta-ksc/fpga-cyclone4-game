# SPDX-License-Identifier: MIT
"""Report-only SD initialization appended to pinned080; originals immutable."""
from pathlib import Path
import argparse, hashlib, json, shutil
ROOT = Path(__file__).resolve().parents[1]
PIN = '0db3ed47138d114fc847216b6f1035bd27e4e3c9e4863db5f8cac728b45ba78d'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence080', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); e = a.evidence080.resolve(); out = a.out.resolve()
    assert not out.exists() and not out.is_relative_to(e)
    assert sha(e/'manifest.json') == PIN
    manifest = json.loads((e/'manifest.json').read_bytes())['files']; used = {}
    prefix = 'work/arm-02/source/'
    for k, h in manifest.items():
        if not k.startswith(prefix): continue
        n = Path(k[len(prefix):])
        if any(x.startswith(('obj-', '.dep-')) or x in ['db', 'incremental_db', 'output_files'] for x in n.parts): continue
        if n.suffix.lower() in ['.exe', '.elf', '.stm', '.sof', '.rbf', '.o', '.d', '.lst', '.map']: continue
        assert sha(e/k) == h
        dest = out/n; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(e/k, dest); used[k] = h
    src = out/'src'
    shutil.copy2(ROOT/'src/nes/firmware/nes_report_disk081.c', src/'nes_report_disk081.c')
    f = src/'stm32f4xx/sdnative.c'; original = f.read_bytes()
    # Include beside sdnative.c, so no include-path or legacy source rewrite.
    shutil.copy2(ROOT/'src/nes/firmware/nes_report_init081.inc', f.parent/'nes_report_init081.inc')
    f.write_bytes(original+b'\n#include <string.h>\n#include "nes_report_init081.inc"\n')
    f = src/'nes_report_platform080.c'; s = f.read_text()
    s = s.replace('080', '081')
    old = ' /* main\'s card mount/CIC initialization still precedes this bounded scope.\n  * Never activate the legacy sdn_initialize: active077 intentionally rejects it. */'
    assert old in s
    s = s.replace(old, ' /* Clock/GPIO/timer/CIC setup precedes this scope; SD mount does not. */')
    s = s.replace('#include "nes_report_boot081.h"', '#include "nes_report_boot080.h"\nextern bool sdn_report_initialize081(void);')
    s = s.replace('report_boot081', 'report_boot080').replace('report_line081', 'report_line080')
    needle = ' if(file_res!=FR_OK){'
    assert s.count(needle) == 1
    s = s.replace(needle, ' if(!sdn_report_initialize081())return false;\n file_init();\n if(!nes_return_io_step())return false;\n'+needle)
    (src/'nes_report_platform081.c').write_text(s, encoding='utf-8', newline='\n')
    f = src/'main.c'; s = f.read_text()
    assert s.count('sdreport_run080') == 2 and s.count('  file_init();') == 1
    s = s.replace('sdreport_run080', 'sdreport_run081').replace('  file_init();', '  /* report081 mounts only after checked report-only SD initialization. */')
    start = s.index('  printf("\\n\\n" DEVICE_NAME')
    end = s.index('  /* report081 mounts', start)
    s = s[:start]+'  /* Report-only startup omits legacy UART banner. */\n'+s[end:]
    f.write_text(s, encoding='utf-8', newline='\n')
    f = src/'Makefile'; s = f.read_text(); assert s.count('nes_report_platform080.c') == 1
    f.write_text(s.replace('nes_report_platform080.c', 'nes_report_platform081.c nes_report_disk081.c'), encoding='utf-8', newline='\n')
    f = src/'nes_sd_inventory_log.c'; s = f.read_text(); assert s.count('/HW080') == 1
    f.write_text(s.replace('/HW080', '/HW081'), encoding='utf-8', newline='\n')
    (src/'VERSION').write_bytes(b'RELEASE_VERSION = "SDREPORT081"\r\n')
    record = dict(inputs=used, native_prefix_sha256=hashlib.sha256(original).hexdigest(), installable=False,
                  files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    (out.parent/'preparation081.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print('Prepared081 from pinned080 inputs='+str(len(used)))
if __name__ == '__main__': main()
