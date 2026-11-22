"""Trace aperture reads and the physical token return on MMC915's 65816."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_credit919 import ARM, OUT, PROBES, LeadingRecord, monitor, once, peer

BASE = OUT/'consumer'
WORK = PROBES/'nes-return920'
ORIGIN = 0x7e2000
MODES = ('reference','copy','mask','issue','joint','first')


def client(mode):
    return BASE if mode in ('reference','issue') else WORK/('mask' if mode in ('joint','first') else mode)


def arm(mode):
    if mode=='first':return WORK/'arm-first'
    return WORK/'arm' if mode in ('issue','joint') else ARM


def prepare_issue(mode):
    root=arm(mode)/'link'
    shutil.copytree(ARM/'link',root)
    src=root/'src/nes_plan_service200.c'
    s=src.read_text()
    pivot='p->sent++;p->bytes=0;p->count=0;p->obj_start=0;return true;'
    if mode=='first':
        s=once(s,pivot,'''p->sent++;p->bytes=0;p->count=0;p->obj_start=0;
   /* A complete first batch can publish slot zero without another plan.
    * Poll once, accepting only the existing CRC/identity-checked descriptor. */
   if(p->bank_history==2 && p->sent==1 && !p->ending)
    return poll(p,&flags,NES_PLAN215_FLUSH);
   return true;''')
        src.write_text(s,newline='\n')
        return
    s=once(s,pivot,'''p->sent++;p->bytes=0;p->count=0;p->obj_start=0;
   /* After the terminal E9 the new batch owns the producer. Retire the first
    * checked BG descriptor, then query the newly visible head once. */
   if(p->ending && p->bulk_pending && !p->bulk[1] && p->bulk[2]==16 && !p->bulk[3] &&
      !p->bulk[4] && !p->bulk[5]){
    if(!complete485(p) || !poll(p,&flags,NES_PLAN215_FINISH))return false;
   }
   return true;''')
    pivot=' if(p->count){\n  /* Recheck tile'
    s=once(s,pivot,''' if(!p->count && mode==NES_ORDINARY553 && p->bulk_pending && p->bulk[1] &&
    p->bulk[2]==64 && !p->bulk[3] && !complete485(p))return false;
'''+pivot)
    src.write_text(s,newline='\n')


def prepare(mode):
    labels=json.loads((BASE/'labels.json').read_bytes())
    body=bytearray((BASE/'body.bin').read_bytes())
    c=Code(ORIGIN+len(body))
    c.labels.update(labels)
    def jump(at,target,n):
        body[at:at+n]=bytes((0x4c,target&255,(target>>8)&255))+bytes([0xea])*(n-3)
    # X was restored after the independent extent, bitmap and command-list checks.
    # $70 is the registered DMA source in WRAM, equal to the copy destination.
    site=body.index(bytes.fromhex('bf74367e186d20106d0a128d8121'),labels['data_size_ok']-ORIGIN)
    assert body[0xa6c:0xa70]==body[0x1674:0x1678]==bytes.fromhex('00000040')
    c.label('select920')
    c.emit(0xe0,4,0)                       # CPX #4 (two tile sections)
    c.branch(0x90,'copy920')
    c.emit(*body[site:site+11])
    c.absolute(0x4c,(ORIGIN+site+11)&65535)
    c.label('copy920')
    c.emit(0xa5,0x70,0x85,0x7a);c.absolute(0x8d,0x2181)
    c.emit(0xe2,0x20,0xa9,1);c.absolute(0x8d,0x2183)
    c.emit(0xa9,0x40);c.absolute(0x8d,0x4304)
    c.emit(0xc2,0x20,0xa9,0,0x80);c.absolute(0x8d,0x4300)
    c.emit(0xa9,0,8);c.absolute(0x8d,0x4302)
    c.absolute(0xad,0x120c);c.absolute(0x8d,0x4305)
    c.emit(0xe2,0x20,0xa9,1);c.absolute(0x8d,0x420b)
    c.emit(0xc2,0x20)
    # Original STOP service then the same two token words and consume strobe.
    check=body.index(bytes.fromhex('201936d024af100040'),labels['ordinary635']-ORIGIN)
    c.absolute(0x4c,(ORIGIN+check)&65535)
    jump(site,c.labels['select920'],11)
    if mode=='mask':
        site=labels['units212']-ORIGIN
        start=body.index(bytes.fromhex('290700a8a90100'),site)
        stop=labels['bit_ready212']-ORIGIN
        # 16-bit load of a one-hot byte plus its neighbour, explicitly masked.
        # Use an in-body table so its run-time address survives cold boot.
        c.label('masks920')
        c.emit(1,2,4,8,16,32,64,128,0)
        mask=c.labels['masks920']
        code=bytes((0x29,7,0,0xaa,0xbf,mask&255,(mask>>8)&255,0x7e,0x29,255,0,0x80,stop-(start+13)))
        assert len(code)<=stop-start
        body[start:stop]=code+bytes([0xea])*(stop-start-len(code))
    body.extend(c.finish())
    build(BASE,client(mode),bytes(body),c.labels)


def trace(source,scene):
    s=monitor(source,scene)
    at='local function loaded()'
    code="""
local function step920(key)
 if packet and pb(0)==7 and pw(8)==908 then sample516(key,pw(16)) end
end
"""
    labels=json.loads((BASE/'labels.json').read_bytes())
    for name in ('header','bulk194','data_size_ok','mark212','append212','service'):
        code+=f"checkedMem527(function()step920('{name}920')end,emu.callbackType.exec,{labels[name]})\n"
    s=once(s,at,code+at)
    s=once(s,'reads=reads+1;return tile:byte(i+1)',"""if i==0 then step920('first_read920') end
 if i==#tile-1 then step920('last_read920') end
 reads=reads+1;return tile:byte(i+1)""")
    return once(s,'consumed[#consumed+1]=','step920("consume920");consumed[#consumed+1]=')


def replay(temp,phase,cold,mode,edges=False):
    def instrument(s,scene):
        s=trace(s,scene)
        if not edges:return s
        rom=client(mode)
        labels=json.loads((rom/'labels.json').read_bytes())
        b=(rom/'body.bin').read_bytes()
        at=b.index(bytes.fromhex('8d0b42c220'),labels.get('copy920',labels['literal_length227'])-ORIGIN)+ORIGIN
        hooks=''.join(f"checkedMem527(function()step920('{event}')end,emu.callbackType.exec,{pc})\n"
                      for pc,event in [(at,'DMA_instruction920'),(at+3,'DMA_resumed920')])
        return once(s,'local function loaded()',hooks+'local function loaded()')
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',client(mode)),patch.object(peer,'monitor',instrument):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=arm(mode),run_id='920'+mode+('edges' if edges else ''))


def guards(temp,mode,*,tag=None,destination=None):
    from guard_nes_output852 import run
    from check_nes_prefetch912 import stop_test
    tag=tag or '920'+mode
    trial=temp/f'nes-tile821-obj-jointmirror-p1-{tag}-warm-pair'
    rom=client(mode)
    results={}
    for case in ('stop-copy','descriptor','duplicate'):
        def adapt(s,labels):
            if case=='stop-copy':
                s=once(s,'if not injected852 then','if false and not injected852 then')
                s=once(s,'local i=a-0x400800;',"""local i=a-0x400800;
 if pw(8)==908 and pb(1)==0 and i==15 then injected852=true;stop852=true end;""")
                hit='injected852'
            else:
                hook="local hit920=false\n"
                if case=='duplicate':
                    hook+=f"""checkedMem527(function()
 if packet and pw(8)==908 and pb(0)==7 and pb(1)==0 then
 hit920=true;emu.write(0x1280,rd(0x1280)|1,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{labels['bulk194']})\n"""
                else:
                    s=once(s,'return d[a-0x6040+1]',"""if pw(8)==908 and pb(1)==0 and a==0x6048 then
 hit920=true;return d[9]~1 end;return d[a-0x6040+1]""")
                s=once(s,'local function loaded()',hook+'local function loaded()')
                hit='hit920'
            expected='lastStatus==228 and reads==16' if case=='stop-copy' else 'lastStatus==224 and reads==0'
            original="if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end"
            s=once(s,original,f"if {hit} then assert({expected}) else {original} end")
            s=once(s,'consumed[#consumed+1]=',f"assert(not {hit},'faulted tile returned');consumed[#consumed+1]=")
            return once(s,'  assert(captured==commits)',f'  assert({hit});assert(captured==commits)')
        results[case]=run(temp,trial,'stop' if case=='stop-copy' else case,column_client=rom,
                          select_packet=lambda b,g:g==908 and b[:2]==bytes((7,0)),adapt_lua=adapt,output_name=case)
    def bad_seal(b,g,case):
        if g!=909:return b,False
        b[8]^=1
        return b,True
    results['seal']=run(temp,trial,'bad-seal',column_client=rom,edit_seal=bad_seal)
    results['display_stop']=stop_test(temp,tag,rom)
    (destination or WORK/f'{mode}-guards.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')


def bus_test(temp,phase,mode):
    from guard_nes_output852 import run
    trial=temp/f'nes-tile821-obj-jointmirror-p{phase}-920{mode}edges-warm-pair'
    def observe(s,labels):
        start=labels.get('copy920',labels['literal_length227'])-ORIGIN
        b=(client(mode)/'body.bin').read_bytes()
        at=b.index(bytes.fromhex('8d0b42c220'),start)+ORIGIN
        hooks=f"""checkedMem527(function()step920('after_dma920')end,emu.callbackType.exec,{at+5})
checkedMem527(function(a,v)
 if packet and pw(8)==908 and pb(0)==7 then
  assert(reads>0 and v==tile:byte(reads),'WRAM port data')
  if reads==1 then step920('first_write920') end
  if reads==#tile then step920('last_write920') end
 end
end,emu.callbackType.write,0x2180)
"""
        return once(s,'local function loaded()',hooks+'local function loaded()')
    def stop_at_909(b,g,case):
        if g!=909:return b,False
        b[8]^=1
        return b,True
    run(temp,trial,'bad-seal',column_client=client(mode),edit_seal=stop_at_909,adapt_lua=observe,output_name='bus920')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards','bus'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',nargs='?',type=Path)
    p.add_argument('phase',nargs='?',choices=(1,2),type=int)
    p.add_argument('--cold',action='store_true')
    p.add_argument('--edges',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        if a.mode in ('issue','first'):
            prepare_issue(a.mode)
        elif a.mode in ('copy','mask'):
            prepare(a.mode)
        else:
            p.error('reference uses MMC915 directly; joint uses the mask ROM and issue ARM')
    elif a.action=='replay':
        replay(a.temp,a.phase,a.cold,a.mode,a.edges)
    elif a.action=='bus':
        bus_test(a.temp,a.phase,a.mode)
    else:
        guards(a.temp,a.mode)
