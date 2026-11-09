"""Separate long-session lifecycle from unchanged MMC690 comparison firmware."""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha
from build_nes_trace_replay import Code
from nes_rom636 import build

def arm(base,out):
    assert sha(base/'obj-nes-100/firmware.stm')=='71e4f00670d26599872c2c294e2f5f8c793a4b2b5aacc2b22e53425e44f7ea5d'
    out.mkdir(parents=True,exist_ok=False)
    edits={}
    s=(base/'nes_native_runtime165.h').read_text()
    s=once(s,'NES_RUNTIME165_LIMIT, NES_RUNTIME165_ARGUMENT };','NES_RUNTIME165_LIMIT, NES_RUNTIME165_ARGUMENT, NES_RUNTIME693_USER };')
    s=once(s,'uint32_t started,limit,steps,frames,transactions,wire_bytes;','uint32_t started,limit,steps,frames,transactions,wire_bytes; /* limit holds the last observed tick in long693. */')
    s=once(s,'* ticks is monotonic modulo32; limit <2^31 ticks. service runs only between', '* Long693 begin requires limit=0. No session/display-idle deadline.\n * Existing transaction limits and stopped-tick backstop remain. service runs only between')
    edits['nes_native_runtime165.h']=s
    s=(base/'nes_native_runtime165.c').read_text()
    s=once(s,'if((uint32_t)(s->ticks(s->ctx)-s->started)>=s->limit)\n  return fail(s,NES_RUNTIME165_DEADLINE);', '''uint32_t now=s->ticks(s->ctx);
 /* Timer progress renews the stopped-tick backstop. Valid empty captures
  * have no display-idle deadline. Per-transaction and clock-fault guards
  * remain responsible for stalled operations. */
 if(now!=s->limit){s->limit=now;s->steps=0;}''')
    s=once(s,'||!service||!limit||limit>=0x80000000u||','||!service||limit||')
    s=once(s,'s->started=ticks(ctx);','s->started=s->limit=ticks(ctx);')
    edits['nes_native_runtime165.c']=s
    s=(base/'nes_runtime_board165.inc').read_text()
    s=once(s,'if(!screen146(native_io165))return nes_cf86_fail094();\n return true;', '''if(!screen146(native_io165))return nes_cf86_fail094();
 if(nes_run136.screen_stage==0x7e){
  native_runtime165.result=NES_RUNTIME693_USER;return false;
 }
 return true;''')
    s=once(s,'native_service165,NULL,6000,','native_service165,NULL,0,')
    s=once(s,'native_runtime165.result!=NES_RUNTIME165_DEADLINE','native_runtime165.result!=NES_RUNTIME693_USER')
    s=once(s,' if(!native_runtime165.frames&&!nes_run136.first_error)nes_run136.first_error=5;',
        ' /* A deliberate user cancellation may occur before the first display. */')
    edits['nes_runtime_board165.inc']=s
    s=(base/'nes_budget210.h').read_text()
    s=once(s,'uint16_t serial;uint8_t bin;bool open;', 'uint16_t serial;uint8_t bin;bool open;\n uint32_t epoch693;bool comparison_closed693;')
    edits['nes_budget210.h']=s
    s=(base/'nes_budget210.c').read_text()
    s=once(s,'s->frame_start=elapsed;s->bin=(uint8_t)(elapsed/500<12?elapsed/500:11);s->open=true;', '''if((uint32_t)(elapsed-s->epoch693)>=6000u){
  s->epoch693=elapsed;memset(s->bins,0,sizeof s->bins);
 }
 s->frame_start=elapsed;s->bin=(uint32_t)(elapsed-s->epoch693)/500;s->open=true;''')
    s=once(s,'if(elapsed>=500 && elapsed<5500)s->displayed_window[elapsed>=4000]++;', '''if(elapsed>=5500)s->comparison_closed693=true;
 if(!s->comparison_closed693&&elapsed>=500)s->displayed_window[elapsed>=4000]++;''')
    s=once(s,r'budget_schema=226\ntick_ms=10\nbin_ticks=500\nbin_basis=FRAME_START_NOT_SCENE\nmodel=ACTUAL_BANK_RESIDENT_SLOTS_211\nsource_reads_snes_vblank=UNMEASURED\n',
        r'budget_schema=693\nepoch_tick=%lu\ntick_ms=10\nbin_ticks=500\n')
    s=once(s,'(unsigned long)nes_budget210.failed_transfers,nes_budget210.open?', '(unsigned long)nes_budget210.epoch693,(unsigned long)nes_budget210.failed_transfers,nes_budget210.open?')
    edits['nes_budget210.c']=s
    for n,s in edits.items():(out/n).write_text(s,newline='\n')
    (out.parent/f'prepare-arm-{out.name}.json').write_text(json.dumps(dict(baseline={n:sha(base/n) for n in edits},patch={n:sha(out/n) for n in edits},mode='long_only',normal_patch_required=False),indent=2)+'\n')

def client(base,raw635,out):
    assert sha(base/'sink165.sfc')=='c79e2b013701fa9cde8a8164da3f0545f2b7c916b8477aa6d74ec405002ebf2e'
    body=bytearray((base/'body.bin').read_bytes());labels=json.loads((base/'labels.json').read_text())
    # Replace just the accepted full joypad commit. All sample-validity,
    # VBlank and hardware STOP checks stay at their original addresses.
    old=bytes.fromhex('688d0260e220a9018d3812')
    assert body.count(old)==1;at=body.index(old)
    c=Code(0x7e2000+len(body));c.labels.update(labels)
    c.label('joy693');c.emit(0x68);c.absolute(0x8d,0x6002)
    c.emit(0x29,0x30,0x30,0xc9,0x30,0x30);c.branch(0xd0,'joy_return693')
    c.absolute(0xad,0x1236);c.branch(0xd0,'joy_return693')
    # Never manufacture receipt/final ACK. The CPU parks until ARM has read
    # the held stage and asserts its existing STOP/reset/menu sequence.
    c.emit(0xe2,0x20);c.store(0x7000,0x7e);c.label('exit_wait693');c.branch(0x80,'exit_wait693')
    c.label('joy_return693');c.emit(0xe2,0x20);c.store(0x1238,1);c.jump('joy_resume693')
    c.labels['joy_resume693']=0x7e2000+at+len(old)
    body[at:at+len(old)]=bytes([0x4c])+(c.labels['joy693']&65535).to_bytes(2,'little')+bytes([0xea])*(len(old)-3)
    body.extend(c.finish());assert 0x2000+len(body)<0x3900
    build(raw635,out,edit_body=lambda b,l:bytes(body),allow_extension=True)
    labels.update(c.labels);(out/'labels.json').write_text(json.dumps(labels,indent=2)+'\n')
    info=json.loads((out/'build.json').read_text());info.update(candidate='longrun693',user_exit_buttons='L+R+Start+Select',user_stage=126,body_capacity=0x1900,body_free=0x1900-len(body),copy_verified_bytes=len(body),new_persistent_WRAM_B=0,baseline_client=sha(base/'sink165.sfc'))
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n');print('CPU693',len(body),info['physical_free_B'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path);p.add_argument('--client',type=Path);p.add_argument('--raw635',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.arm:arm(a.arm,a.out)
    else:client(a.client,a.raw635,a.out)
