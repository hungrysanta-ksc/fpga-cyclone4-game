"""699 CHR fix: separately fitted normal-ROM700 and unchanged long-ROM701."""
import argparse,hashlib,json,shutil,struct,subprocess,sys,zipfile,zlib
from pathlib import Path
from nes_raw506 import sha
from nes_schedule492 import funcs
from nes_cf68_pair_preflight import encode,decode
from analyze_nes_status689 import cost

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def digest(b):return hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
def checked(script,args,log):
    with log.open('wb') as f:subprocess.run([sys.executable,str(ROOT/'tools'/script),*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=240)

def image(a):
    assert str(a.out.resolve()).isascii();a.out.mkdir(parents=True,exist_ok=False)
    sof=a.board/'output_files/board.sof';shutil.copyfile(sof,a.out/'board.sof')
    with (a.out/'cpf.log').open('wb') as f:
        subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c','board.sof','board.rbf'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
    raw=(a.out/'board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
    bi=a.out/f'fpga_mmc{a.number}.bi3';bi.write_bytes(packed)
    checked('test_nes_nrom458_programmer.py',['--image',bi,'--rbf',a.out/'board.rbf','--out',a.out/'programmer'],a.out/'programmer.log')
    p=read(a.out/'programmer/result.json');assert p['passed'] and p['image_sha256']==sha(bi) and p['rbf_sha256']==digest(raw)
    save(a.out/'image.json',dict(number=a.number,SOF=sha(sof),RBF=digest(raw),BI3=sha(bi),programmer=p,physical=False))
    print('IMAGE',a.number,'encode/decode and actual programmer bytes PASS',sha(bi))

def pack(a):
    old=read(ROOT/'analysis/trial695-package.json');fix=read(ROOT/'analysis/bonus699-verification.json')
    assert fix['functional_gate'] and fix['FIT_STA_gate'] and fix['schedule_model_no_regression']
    assert sha(a.prior)==old['ZIP_SHA256']
    m=read(a.normal_board/'inputs700.json');f=fix['inputs']
    assert set(m['changed'])=={'sink-program.hex'}
    for n,h in m['base'].items():
        assert sha(a.normal_board/n)==m['changed'].get(n,h)
        assert sha(a.long_board/n)==h==f['changed'].get(n,f['base'][n]),n
    costs={}
    for number,b in [('700',a.normal_board),('701',a.long_board)]:
        c=cost(b);assert c['SOF'] and c['STA'] and not c['LAB_error'] and min(c['slack_ns'].values())>0
        assert c['LE'][0]<=15408 and c['LAB']<=963 and c['M9K'][0]<=56
        assert c['unconstrained']==fix['boards']['699']['unconstrained']
        for n in ('word660.tsv','reader661.tsv','io612.tsv'):assert c[n] and min(float(r['slack']) for r in c[n])>0,n
        costs[number]={k:c[k] for k in ('LE','FF','RAM_bits','M9K','LAB','slack_ns','unconstrained','reports','word660.tsv','reader661.tsv','io612.tsv')}
    assert costs['701']['reports']==fix['boards']['699']['reports']
    a.checks.mkdir(parents=True,exist_ok=False);files={};variants={}
    with zipfile.ZipFile(a.prior) as z:
        assert z.testzip() is None
        basefiles={n:z.read('01-MMC695-60SEC-SD-ROOT/'+n) for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin')}
    for n,b in basefiles.items():assert digest(b)==old['files']['01-MMC695-60SEC-SD-ROOT/'+n]
    for number,prior,src,base,b,img in [('700','695',a.normal,a.normalbase,a.normal_board,a.normal_image),('701','696',a.long,a.longbase,a.long_board,a.long_image)]:
        obj=src/'obj-nes-100';before=base/'obj-nes-100';fw=(obj/'firmware.stm').read_bytes()
        assert sha(before/'firmware.stm')==old['variants'][prior]['firmware']
        assert (before/'firmware.stm').read_bytes()[32:].replace(prior.encode(),number.encode())==fw[32:]
        fn=funcs(obj/'sd2snes.elf');assert len(fn)>700 and fn==funcs(before/'sd2snes.elf')
        size,crc,inverse=struct.unpack_from('<III',fw,8)
        assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
        im=read(img/'image.json');assert im['number']==number and im['SOF']==sha(b/'output_files/board.sof')
        bi=img/f'fpga_mmc{number}.bi3';packed=bi.read_bytes();assert sha(bi)==im['BI3'] and digest(decode(packed))==im['RBF']
        p=read(img/'programmer/result.json');assert p['passed'] and p['image_sha256']==sha(bi)
        marker=f'NES MMC3 {number}.nh1';imagepath=f'sd2snes/fpga_mmc{number}.bi3';rom=f'sd2snes/nes/mmc{number}.nes'
        logs=[f'sd2snes/nes-{k}-mmc{number}.txt' for k in ('progress','budget','game-last')]
        for name in [marker,*('/'+n for n in [imagepath,rom,*logs])]:
            assert name.encode()+b'\0' in fw and name.replace(number,prior).encode()+b'\0' not in fw,name
        menu=a.checks/f'menu{number}.json'
        checked('check_nes_menu533.py',['--arm',src,'--trial',number,'--out',menu],a.checks/f'menu{number}.log')
        mr=read(menu);assert mr['firmware']==sha(obj/'firmware.stm') and mr['marker_cases']==4
        for k,v in mr['rows'].items():assert v['prepared']==v['released']==int(k=='normal')
        recovery={}
        for fault in ('none','program','done','busy','token'):
            d=a.checks/f'base{number}-{fault}'
            checked('check_nes_transfer512_recovery.py',['--arm',src,'--trial',number,'--fault',fault,'--out',d],a.checks/(d.name+'.log'))
            r=read(d/'result.json');assert r['passed'] and r['firmware_sha256']==sha(obj/'firmware.stm')
            assert r['safe_return']==r['base_restored']==int(fault=='none')
            assert r['config_paths']==['/'+imagepath,'/sd2snes/fpga_base.bi3'];recovery[fault]=r
        gp=a.checks/f'guards{number}.json'
        if number=='701':
            checked('check_nes_longrun693.py',['--arm',src,'--out',gp],a.checks/f'guards{number}.log');g=read(gp)
            assert g['passed'] and g['firmware']==sha(obj/'firmware.stm')
        else:
            checked('check_nes_windows518.py',['--arm',src,'--layout','trimmed','--out',gp],a.checks/f'guards{number}.log');g=read(gp)
            assert g['firmware_SHA256']==sha(obj/'firmware.stm') and [(w['start_s'],w['end_s']) for w in g['accepted']]==[(5,40),(40,55)]
        bus=read(a.rom_checks/f'rom{number}/result.json')
        assert bus['bytes']==5120 and bus['program']==sha(b/'sink-program.hex') and bus['bus']==sha(b/'nes_sink_bus165.sv')
        client_sha=read(ROOT/'analysis/status689-verification.json')['client'] if number=='700' else fix['schedules']['1']['client']
        assert bus['client']==client_sha
        prefix=f'{"01" if number=="700" else "02"}-MMC{number}-{"60SEC" if number=="700" else "LONG"}-SD-ROOT/'
        files[prefix+marker]=b'';files[prefix+imagepath]=packed;files[prefix+'sd2snes/firmware.stm']=fw
        for n,bv in basefiles.items():files[prefix+n]=bv
        files[prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=(f'Copy your existing SMB3(J) ROM unchanged as mmc{number}.nes. Same bytes as mmc695.nes/mmc696.nes. Payload CRC32 5a04eed7.\n').encode()
        variants[number]=dict(mode='60-second comparison' if number=='700' else 'long play; L+R+Start+Select exit',firmware=sha(obj/'firmware.stm'),ELF=sha(obj/'sd2snes.elf'),
            base_firmware=old['variants'][prior]['firmware'],identical_functions=len(fn),Flash_B=len(fw),Flash_free_B=212992-len(fw),
            ROM=rom,marker=marker,logs=logs,board=costs[number],image=im,menu=mr,recovery=recovery,guards=g,ROM_read=bus)
    files['README-KO.txt']=(ROOT/'docs/nes-mmc700-701-trial.ko.md').read_bytes()
    assert not any('RESTORE' in n.upper() or n.lower().endswith(('.nes','.sav','.srm','.rtc')) for n in files)
    report=dict(stage=700,variants=variants,proof699=sha(ROOT/'analysis/bonus699-verification.json'),
        normal_board_inputs=m,baseline='MMC695 normal/MMC696 long;699 fix in both',ROM_included=False,RESTORE_included=False,physical_verified=False,
        comparison_windows_s=[[5,40],[40,55]],cheat_or_shortcut_included=False,
        scope='Two linked ARM builds with only labels changed; exact699 RTL plus separately fitted normal packed ROM; actual programmer/FatFS and ARM/menu/ROM bus tests with modeled hardware. No new physical install or FPS claim.',
        files={n:digest(b) for n,b in files.items()})
    files['manifest.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'MMC700-60SEC-MMC701-LONG.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        for n,b in files.items():assert z.read(n)==b,n
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    save(a.report,report);print('PASS700/701 package',archive.resolve(),report['ZIP_SHA256'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('image','pack'));p.add_argument('--number')
    for n in ('board','quartus','out','normal','long','normalbase','longbase','normal-board','long-board','normal-image','long-image','rom-checks','prior','checks','report'):
        p.add_argument('--'+n,type=Path)
    a=p.parse_args();image(a) if a.mode=='image' else pack(a)
