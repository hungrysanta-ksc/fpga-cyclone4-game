"""Replay a checked packed-input decoder and SEAL-wait scheduler on the 921 link."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_palette921 import image
from nes_return920 import PROBES, LeadingRecord, client, guards, once, peer, trace

WORK = PROBES/'nes-deadline922'
MODES = ('rows','words','receive','poll','combined','oam','idle','batch','quantum','finish','group','suffix','firstrow')


def prepare(mode):
    link=WORK/mode/'link'
    shutil.copytree(image('compact')/'link',link)
    source=link/'src/nes_native165.c'
    s=source.read_text()
    grouped=mode in ('rows','receive','combined','group','suffix','firstrow')
    if grouped:
        s=once(s,'  for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(end-n)[i]))return false;',
'''  /* The complete group is bounded by this record and the section extent.
   * Resolve order once, validate every byte, then publish the entire group. */
  while(s->next_kind<6 && s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;
  if(s->next_kind!=k)return fail(s,9);
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  const uint8_t *group=end-n;
  for(unsigned i=0;i<n;i++)if(group[i]>=limit)return fail(s,k==1?10:9);
  memcpy((k==1?s->rows:s->palette)+start,group,n);
  s->at[k]+=n;s->records+=n;''')
    if mode in ('words','receive','combined'):
        s=once(s,'uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];',
'''uint64_t value=0;
  if(width==8){
   uint32_t high,low;
   memcpy(&high,p+pos,4);memcpy(&low,p+pos+4,4);pos+=8;
   value=((uint64_t)__builtin_bswap32(high)<<32)|__builtin_bswap32(low);
  }else for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];''')
    if mode in ('words','receive','combined','suffix'):
        s=once(s,'for(unsigned i=0;i<n;i++)s->raw_pixels[start+i]=(uint8_t)(colors>>(6*(n-1-i)))&63;',
'''for(unsigned i=n;i;i--){
    s->raw_pixels[start+i-1]=(uint8_t)colors&63;
    colors>>=6;
   }''')
    if mode=='group':
        s=once(s,'''  for(unsigned i=0;i<n;i++)if(group[i]>=limit)return fail(s,k==1?10:9);
  memcpy((k==1?s->rows:s->palette)+start,group,n);''','''  uint8_t *dest=(k==1?s->rows:s->palette)+start;
  for(unsigned i=0;i<n;i++){
   if(group[i]>=limit)return fail(s,k==1?10:9);
   dest[i]=group[i];
  }''')
    if mode=='firstrow':
        lo=s.index('  /* The complete group')
        hi=s.index('s->records+=n;',lo)+len('s->records+=n;')
        s=s[:lo]+'''  const uint8_t *group=end-n;
  if(!logical_record(s,k,gen,start,group[0]))return false;
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  for(unsigned i=1;i<n;i++)if(group[i]>=limit)return fail(s,k==1?10:9);
  memcpy((k==1?s->rows:s->palette)+start,group,n);
  s->at[k]+=n-1;s->records+=n-1;'''+s[hi:]
    if grouped or mode=='words':
        source.write_text(s,newline='\n')
    if mode in ('oam','idle','batch','finish'):
        source=link/'src/nes_native_sink165.c'
        old='return packet_wire(s,8,4,first,b+first,4,length)&&packet(s,2,4,512,b+512,32);'
        # Only a checked, short OBJ after an already substantial tile set
        # warrants opening the queue. Never release a bank on this observation.
        early='''if(s->plan && s->plan->bulk_pending && s->plan->bulk[1] &&
    s->plan->bulk[2]==32 && !s->plan->bulk[3] && s->obj_next>=16){
  struct nes_sink_window184 *w=s->plan->window;
  uint8_t ack[12];
  if(!nes_window184_drain(w,ack))return fail(s,5);
'''
        if mode=='finish':
            early=early.split('  struct nes_sink_window184')[0]+'''  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
'''
        elif mode!='oam':
            early+='''  if(!nes_cost474_pause(w->ctx,w->guard,1,false,84u*512u))return fail(s,5);
'''
        early+=' }\n '
        first='if(!packet_wire(s,8,4,first,b+first,4,length))return false;\n '
        tail='return packet(s,2,4,512,b+512,32);'
        replacement=(early+first if mode=='batch' else first+early)+tail
        s=once(source.read_text(),old,replacement)
        if mode!='oam' and '#include "nes_cost471.h"' not in s:
            s='#include "nes_cost471.h"\n'+s
        source.write_text(s,newline='\n')
    if mode=='quantum':
        source=link/'src/nes_native_runtime165.c'
        s=once(source.read_text(),'if(reason!=2)break;','if(reason!=2 || (s->prefetch_left&3u)==0)break;')
        source.write_text(s,newline='\n')
    if mode in ('poll','combined'):
        source=link/'src/nes_native_runtime165.c'
        s=once(source.read_text(),'84u*96u : 84u*128u','0u : 84u*128u')
        source.write_text(s,newline='\n')


def replay(temp,mode,phase,cold):
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',client('first')),patch.object(peer,'monitor',trace):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=WORK/mode,run_id='922'+mode)


def check_groups(work):
    """Exercise the real linked packet entry, including a bad last byte."""
    from check_nes_game478 import Machine
    import struct
    m=Machine(work/'link/src',bytes(128))
    offset=m.layout['nes_native165']
    tested=0
    for section,limit,field in ((1,16,'rows'),(5,64,'palette')):
        for length in (1,7,8):
            for case in ('valid','last_byte','generation','order','size','token','truncated'):
                m.call('nes_native165_reset',[m.state])
                def put(name,value):
                    m.u.mem_write(m.state+offset[name],value)
                counts=[66,0,0,0,0,0]
                counts[section]=length
                put('counts',struct.pack('<6H',*counts))
                put('at',struct.pack('<6H',65 if case=='order' else 66,0,0,0,0,0))
                put('state',bytes([1]))
                put('generation',struct.pack('<H',908))
                put('token_valid',bytes([1]))
                put('next_token',struct.pack('<H',99))
                n=length+(case=='size')
                tag=0xf800|(section<<8)|(n-1)
                data=bytes(range(length-1))+bytes([limit if case=='last_byte' else limit-1])
                packet=struct.pack('>HH',tag,908+(case=='generation'))+data.rjust(8,b'\x00')
                m.u.mem_write(m.lut,packet)
                accepted=m.call('nes_native165_packet',[m.state,99+(case=='token'),m.lut,len(packet)-(case=='truncated')])
                assert accepted==(case=='valid'),(field,length,case)
                if accepted:
                    assert bytes(m.u.mem_read(m.state+offset[field],length))==data
                    assert int.from_bytes(m.u.mem_read(m.state+offset['next_token'],2),'little')==100
                else:
                    assert m.state_value()==5
                    assert int.from_bytes(m.u.mem_read(m.state+offset['next_token'],2),'little')==99
                    assert not m.call('nes_native165_packet',[m.state,99,m.lut,len(packet)])
                tested+=1
    return tested


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards','proof','groups'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,nargs='?')
    p.add_argument('--cold',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,a.mode,a.phase,a.cold)
    elif a.action=='guards':
        guards(a.temp,'first',tag='922'+a.mode,destination=WORK/(a.mode+'-guards.json'))
    elif a.action=='groups':
        print('checked packet cases, reference and candidate:',check_groups(image('compact')),check_groups(WORK/a.mode))
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',WORK/a.mode,915)
