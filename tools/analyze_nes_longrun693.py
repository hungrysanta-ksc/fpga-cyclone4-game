"""Bind selected long693 CPU, linked ARM, unchanged RTL and recovery evidence."""
import argparse,json
from pathlib import Path
from nes_raw506 import sha

def read(p):return json.loads(p.read_text(encoding='utf8'))
def run(a):
    p=a.probe;arm=p/'arm03/src';client=p/'client02';root=Path(__file__).resolve().parents[1]
    info=read(client/'build.json');rom=(client/'sink165.sfc').read_bytes();body=(client/'body.bin').read_bytes()
    prefix=info['prefix_B'];out=bytearray(rom[288:288+prefix]);pos=288+prefix
    while True:
        t=rom[pos];pos+=1
        if not t:break
        if t<128:out.extend(rom[pos:pos+t]);pos+=t
        else:
            if t>=192:src=len(out)-rom[pos];pos+=1
            else:src=int.from_bytes(rom[pos:pos+2],'little')-0x2000;pos+=2
            assert 0<=src<len(out)
            for _ in range((t&63)+3):out.append(out[src]);src+=1
        assert len(out)<=len(body)
    assert bytes(out)==body and pos==288+prefix+info['encoded_B']
    guards=read(p/'guards08.json');cpu=read(a.cpu/'result.json');rtl=read(a.rtl/'result.json');menu=read(p/'menu03.json')
    fw=sha(arm/'obj-nes-100/firmware.stm');sf=sha(client/'sink165.sfc')
    assert guards['passed'] and len(guards['cases'])==16 and guards['firmware']==fw
    assert cpu['passed'] and len(cpu['cases'])==12 and cpu['client']==sf
    assert rtl['passed'] and menu['firmware']==fw and len(menu['rows'])==5
    recovery={k:read(p/f'base03-{k}/result.json') for k in ('none','program','done','busy','token')}
    for k,v in recovery.items():assert v['passed'] and v['firmware_sha256']==fw and v['safe_return']==v['base_restored']==int(k=='none')
    sources={x.name:sha(x) for x in (p/'patch04').iterdir()}
    assert all(sha(arm/n)==h for n,h in sources.items())
    size=list(map(int,(p/'arm03/size.log').read_text().splitlines()[-1].split()[:3]));flash=(arm/'obj-nes-100/firmware.stm').stat().st_size
    assert flash<=212992 and size[1:]==[10040,19552]
    return dict(stage=693,baseline='MMC690',normal_firmware=read(root/'analysis/trial690-package.json')['firmware_SHA256'],normal_unchanged=True,
        ARM=dict(firmware=fw,ELF=sha(arm/'obj-nes-100/sd2snes.elf'),Flash_B=flash,Flash_free_B=212992-flash,Flash_delta_B=flash-212984,data_B=size[1],BSS_B=size[2],BSS_delta_B=8,compiled_sources=sources,guards=guards),
        CPU=dict(client=sf,body=sha(client/'body.bin'),body_B=len(body),body_delta_B=36,stored_B=5120,stored_free_B=info['physical_free_B'],new_persistent_WRAM_B=0,pack_roundtrip=True,tests=cpu),
        RTL=rtl,menu=menu,recovery=recovery,
        lifecycle=dict(mode='no fixed play or display-idle duration; begin limit=0',watchdog_no_retired_frame_ms=None,stopped_tick_step_limit=4194304,existing_transaction_guards_retained=True,user_exit_buttons='L+R+Start+Select',user_screen_stage=126,runtime_result=8,final_ACK_fabricated=False,
            logs='schema693; bounded ~60second epoch bins; first5-40/40-55 windows retained; cumulative32bit diagnostic counters remain modulo32; physical elapsed uses existing progress checkpoints',normal_names_unchanged=True),
        board=dict(logic_unchanged=True,ROM_initialization_changed=True,new_FIT_STA=False,whole_resource_cost_pending=True),
        open=['actual packed reset loader boot/time and board ROM init integration','whole actual ARM/65816 shared schedule and two start phases','full generation rollover through input/plan/receipt/SNES; CPU user exit during each DMA/SEAL boundary','unique60s/long labels, packaging and physical long play'],
        installer_created=False,physical_longrun=False,
        scope='Actual linked M4 guards/status/queue cancellation/format and native65816 service; same screen RTL bus/SPI simulation and existing linked base/menu fixtures. Tests are linked by interface values, not one shared physical/full-pipeline clock. No new performance or physical-hour claim.',
        tool_pins={n:sha(root/'tools'/n) for n in ('prepare_nes_longrun693.py','check_nes_longrun693.py','check_nes_longrun693_cpu.py','check_nes_longrun693_rtl.py','analyze_nes_longrun693.py')})

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','cpu','rtl','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();j=run(a);a.out.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print('PASS693:16 ARM,12 CPU,RTL,5 menu,5 base; Flash free',j['ARM']['Flash_free_B'],'B; pack roundtrip')
