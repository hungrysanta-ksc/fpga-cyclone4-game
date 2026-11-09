"""Package695 normal60s and696 long play, with separate install roots and logs."""
import argparse,hashlib,json,struct,subprocess,sys,zipfile,zlib
from pathlib import Path
from nes_raw506 import sha
from nes_schedule492 import funcs
from nes_cf68_pair_preflight import decode,encode

def read(p):return json.loads(p.read_text(encoding='utf8'))
def digest(b):return hashlib.sha256(b).hexdigest()
def run(a):
    old=read(Path('analysis/trial690-package.json'));proof=read(Path('analysis/longrun694-verification.json'))
    assert proof['functional_gate'] and proof['whole_FIT_STA_no_regression'] and proof['protected_VBlank_and_last_ACK_gate']
    assert sha(a.prior)==old['ZIP_SHA256']
    assert sha(a.board/'output_files/board.sof')==proof['boards']['694']['reports']['board.sof']
    assert sha(a.image/'board.sof')==proof['boards']['694']['reports']['board.sof']
    raw=(a.image/'board.rbf').read_bytes();packed=(a.image/'fpga_mmc696.bi3').read_bytes()
    assert encode(raw)==packed and decode(packed)==raw
    programmer=read(a.programmer/'result.json')
    assert programmer['passed'] and programmer['image_sha256']==digest(packed) and programmer['rbf_sha256']==digest(raw)
    a.checks.mkdir(parents=True,exist_ok=False);files={};variants={}
    def check(label,script,args):
        with (a.checks/(label+'.log')).open('wb') as log:
            subprocess.run([sys.executable,'tools/'+script,*map(str,args)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    with zipfile.ZipFile(a.prior) as z:
        basefiles={n:z.read('01-MMC690-SD-ROOT/'+n) for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin','sd2snes/fpga_mmc690.bi3')}
    for n,b in basefiles.items():assert digest(b)==old['files']['01-MMC690-SD-ROOT/'+n]
    for number,src,base in [('695',a.normal,a.normalbase),('696',a.long,a.longbase)]:
        obj=src/'obj-nes-100';before=base/'obj-nes-100';firmware=(obj/'firmware.stm').read_bytes()
        expected=old['firmware_SHA256'] if number=='695' else proof['schedule']['firmware']
        assert sha(before/'firmware.stm')==expected
        assert (before/'firmware.stm').read_bytes()[32:].replace(b'690',number.encode())==firmware[32:]
        fn=funcs(obj/'sd2snes.elf');assert fn and fn==funcs(before/'sd2snes.elf')
        size,crc,inverse=struct.unpack_from('<III',firmware,8)
        assert firmware[:4]==b'STM3' and size+512==len(firmware)<=212992
        assert zlib.crc32(firmware[512:])==crc and crc^inverse==0xffffffff
        marker=f'NES MMC3 {number}.nh1';image=f'sd2snes/fpga_mmc{number}.bi3';rom=f'sd2snes/nes/mmc{number}.nes'
        logs=[f'sd2snes/nes-{k}-mmc{number}.txt' for k in ('progress','budget','game-last')]
        for name in [marker,*('/'+n for n in [image,rom,*logs])]:
            assert name.encode()+b'\0' in firmware
            assert name.replace(number,'690').encode()+b'\0' not in firmware
        menu=a.checks/f'menu{number}.json'
        check('menu'+number,'check_nes_menu533.py',['--arm',src,'--trial',number,'--out',menu])
        mr=read(menu);assert mr['firmware']==sha(obj/'firmware.stm') and mr['marker_cases']==4
        for k,v in mr['rows'].items():assert v['prepared']==v['released']==int(k=='normal')
        recovery={}
        for fault in ('none','program','done','busy','token'):
            d=a.checks/f'base{number}-{fault}'
            check(d.name,'check_nes_transfer512_recovery.py',['--arm',src,'--trial',number,'--fault',fault,'--out',d])
            r=read(d/'result.json');assert r['passed'] and r['firmware_sha256']==sha(obj/'firmware.stm')
            assert r['safe_return']==r['base_restored']==int(fault=='none')
            assert r['config_paths']==['/'+image,'/sd2snes/fpga_base.bi3'];recovery[fault]=r
        gp=a.checks/f'guards{number}.json'
        if number=='696':
            check('guards'+number,'check_nes_longrun693.py',['--arm',src,'--out',gp]);g=read(gp)
            assert g['passed'] and g['firmware']==sha(obj/'firmware.stm')
        else:
            check('guards'+number,'check_nes_windows518.py',['--arm',src,'--layout','trimmed','--out',gp]);g=read(gp)
            assert g['firmware_SHA256']==sha(obj/'firmware.stm')
            assert [(w['start_s'],w['end_s']) for w in g['accepted']]==[(5,40),(40,55)]
        prefix=f'{"01" if number=="695" else "02"}-MMC{number}-{"60SEC" if number=="695" else "LONG"}-SD-ROOT/'
        files[prefix+marker]=b'';files[prefix+image]=basefiles['sd2snes/fpga_mmc690.bi3'] if number=='695' else packed
        files[prefix+'sd2snes/firmware.stm']=firmware
        for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):files[prefix+n]=basefiles[n]
        files[prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=(f'Copy your existing mmc690.nes as mmc{number}.nes. Same SMB3(J), CRC32 5a04eed7. Do not rename an unrelated game.\n').encode()
        variants[number]={'mode':'60-second comparison' if number=='695' else 'no fixed time limit; L+R+Start+Select exit','firmware':sha(obj/'firmware.stm'),'ELF':sha(obj/'sd2snes.elf'),
            'identical_functions':len(fn),'Flash_B':len(firmware),'Flash_free_B':212992-len(firmware),'logs':logs,'ROM':rom,'marker':marker,'menu':mr,'recovery':recovery,'guards':g}
    files['README-KO.txt']=Path('docs/nes-mmc695-696-trial.ko.md').read_bytes()
    assert not any('RESTORE' in n.upper() or n.lower().endswith(('.nes','.sav','.srm','.rtc')) for n in files)
    report={'stage':695,'variants':variants,'baseline':'MMC690; MMC666 retained','ROM_included':False,'RESTORE_included':False,'physical_verified':False,
        'proof694':sha(Path('analysis/longrun694-verification.json')),'normal_inherited_proof':sha(Path('analysis/trial690-package.json')),'long_programmer':programmer,
        'comparison_windows_s':[[5,40],[40,55]],'strict_all_time_no_regression':False,
        'timing_caveat':proof['decision'],'long_board':proof['boards']['694'],
        'files':{n:digest(b) for n,b in files.items()}}
    files['manifest.json']=(json.dumps(report,indent=2)+'\n').encode()
    a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC695-60SEC-MMC696-LONG.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(n)==b for n,b in files.items())
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print('PASS695/696 dual package:',archive.resolve(),report['ZIP_SHA256'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('normal','long','normalbase','longbase','prior','board','image','programmer','checks','out','report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
