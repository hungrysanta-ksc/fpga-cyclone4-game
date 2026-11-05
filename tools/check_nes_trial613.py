"""Check the relabeled whole ARM link and actual failure/return paths."""
import argparse,json,struct,subprocess,sys,zlib
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
from nes_schedule492 import funcs
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    old=a.base/'obj-nes-100';new=a.arm/'obj-nes-100'
    assert sha(old/'firmware.stm')==read(ROOT/'analysis/oe612-verification.json')['ARM_SHA']
    before=(old/'firmware.stm').read_bytes();fw=(new/'firmware.stm').read_bytes()
    assert before[32:].replace(b'577',b'613')==fw[32:]
    fn=funcs(new/'sd2snes.elf');assert fn==funcs(old/'sd2snes.elf')
    n,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==n+512==212992 and zlib.crc32(fw[512:])==crc and crc^inv==0xffffffff
    def run(name,script,args):
        with (a.out/(name+'.log')).open('wb') as f:
            subprocess.run([sys.executable,str(ROOT/'tools'/script),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
    for name,script,extra in [('windows','check_nes_windows518.py',['--layout','trimmed']),
        ('menu','check_nes_menu533.py',['--trial','613']),('offer','guard_nes_offer610.py',['--obj-only']),
        ('prelude','check_nes_prelude554.py',['--cutoff'])]:
        run(name,script,['--arm',a.arm,'--out',a.out/(name+'.json'),*extra])
    for fault in ('none','program','done','busy','token'):
        run('base-'+fault,'check_nes_transfer512_recovery.py',['--arm',a.arm,'--fault',fault,'--trial','613','--out',a.out/('base-'+fault)])
    result=dict(firmware=sha(new/'firmware.stm'),ELF=sha(new/'sd2snes.elf'),identical_functions=len(fn),Flash_B=len(fw),Flash_free_B=0,
        checks={n:read(a.out/(n+'.json')) for n in ('windows','menu','offer','prelude')},
        recovery={n:read(a.out/('base-'+n)/'result.json') for n in ('none','program','done','busy','token')})
    for n,v in result['recovery'].items():
        assert v['passed'] and v['safe_return']==v['base_restored']==int(n=='none')
        assert v['config_paths']==['/sd2snes/fpga_mmc613.bi3','/sd2snes/fpga_base.bi3']
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
