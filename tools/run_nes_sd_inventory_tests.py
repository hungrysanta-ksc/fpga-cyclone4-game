# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--gcc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    mock=a.out/'mock';mock.mkdir()
    (mock/'config.h').write_text('#include "sd_inventory_mock_hw.h"\n')
    (mock/'snes.h').write_text('#include "sd_inventory_mock_hw.h"\n')
    (mock/'diskio.h').write_text('/* platform mock: no disk_status call */\n')
    (mock/'ff.h').write_text('#include "sd_inventory_ff_mock.h"\n#define FR_NO_FILE 4\n#define FR_NO_PATH 5\n#define fptr pos\nFRESULT f_lseek(FIL *,uint32_t);\n')
    source=ROOT/'src/nes/firmware';tests=ROOT/'tests/nes-functional'
    jobs=[('collector',['sd_inventory_host.c'],['nes_sd_inventory.c'],[],['SYNTHETIC-NOT-HARDWARE.TXT'],'checks=52'),('writer',['sd_inventory_log_host.c'],['nes_sd_inventory_log.c'],['-DSDINFO_HOST_TEST'],[],'checks=23'),('platform',['sd_inventory_platform_host.c'],['nes_sd_inventory_platform.c','nes_diag_runtime.c'],[],[],'sessions=6')]
    hashes={}
    def run(name,cmd,marker=None):
        with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        s=(a.out/(name+'.log')).read_text(errors='replace')
        if r.returncode or (marker and marker not in s):raise RuntimeError('Inspect raw '+str(a.out/(name+'.log')))
    for name,t,c,flags,args,marker in jobs:
        files=[*(tests/n for n in t),*(source/n for n in c)]
        for f in files:hashes[f.relative_to(ROOT).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
        binary=a.out/(name+'.exe')
        run(name+'-compile',[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,'-I',str(mock),'-I',str(source),'-I',str(tests),*(str(f) for f in files),'-o',str(binary)])
        run(name,[str(binary.resolve()),*(str((a.out/n).resolve()) for n in args)],marker)
    import sys
    run('report',[sys.executable,'-B',str(tests/'sd_inventory_report_test.py'),str(a.out/'SYNTHETIC-NOT-HARDWARE.TXT')],'checks=29')
    (a.out/'result.json').write_text(json.dumps(dict(candidate='NES-SD-INSPECTION-072',collector_checks=52,writer_checks=23,platform_sessions=6,report_checks=29,physical_SD=False,sources=hashes),indent=2)+'\n')
    print('PASS072 collector52 writer23 platform6 report29; host models only')
if __name__=='__main__':main()
