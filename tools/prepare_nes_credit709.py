"""Share existing status snapshot on E1; validate only the pre-send identity.

No current-E1 acceptance or final display completion is inferred from it.
Original E0 remains for short packets, full credit and receipt/final barriers.
"""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def arm(base,out,needed=False):
    assert sha(base/'obj-nes-100/firmware.stm')=='b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600'
    s=(base/'nes_sink_window184.c').read_text()
    s=once(s,'''static bool status(struct nes_sink_window184 *s,uint8_t ack[12]){
 uint8_t tx[20]={0xe0},rx[20];if(!io(s,tx,rx,20))return false;''',
        '''static bool response709(struct nes_sink_window184 *s,const uint8_t rx[20]){''')
    s=once(s,''' s->retired=r;memcpy(ack,rx+7,12);
 return true;
}
bool nes_window532_room''',''' // Common identity check before updating credit, for both E0 and E1.
 // E1 snapshot predates this packet: sent/last still describe the old tail.
 if(s->ever_sent && r==s->sent && (rx[7]!=(s->last[0]==3?1:0) ||
    rx[8]!=s->last[0] || memcmp(rx+9,s->last+2,8) || rx[17]!=0x65 || rx[18]!=0x9a))return fail(s,8);
 s->retired=r;return true;
}
static bool status(struct nes_sink_window184 *s,uint8_t ack[12]){
 uint8_t tx[20]={0xe0},rx[20];
 if(!io(s,tx,rx,20)||!response709(s,rx))return false;
 memcpy(ack,rx+7,12);return true;
}
bool nes_window532_room''')
    s=once(s,'''  if(s->retired==s->sent && (ack[0]!=0 || ack[1]!=s->last[0] ||
     memcmp(ack+2,s->last+2,8) || ack[10]!=0x65 || ack[11]!=0x9a))return fail(s,8);
''','')
    s=once(s,'''  if(s->retired==s->sent){
   if(s->ever_sent&&(ack[0]!=(s->last[0]==3?1:0)||ack[1]!=s->last[0]||memcmp(ack+2,s->last+2,8)||ack[10]!=0x65||ack[11]!=0x9a))return fail(s,8);
  }
''','')
    s=once(s,''' if(!io(s,tx,tx,n+3))return false;
 s->sent++;''',''' if(!io(s,tx,tx,n+3))return false;
 // A minimum19B transaction has no CRC8 byte: keep conservative old credit.
 if(n>16 && !response709(s,tx))return false;
 s->sent++;''')
    if needed:
        s=once(s,'if(n>16 && !response709(s,tx))',
            'if(n>16 && (uint16_t)(s->sent-s->retired)>=2 && !response709(s,tx))')
    out.mkdir(parents=True,exist_ok=False)
    (out/'nes_sink_window184.c').write_text(s,encoding='utf8',newline='\n')
    (out.parent/(out.name+'-recipe.json')).write_text(json.dumps(dict(stage=709,needed=needed,base=sha(base/'nes_sink_window184.c'),changed=sha(out/'nes_sink_window184.c'),scope=__doc__),indent=2)+'\n',encoding='utf8')

def board(base,out,qualified=False,rotation=False):
    m=json.loads((base/'inputs707.json').read_text());pins={n:m['changed'].get(n,h) for n,h in m['base'].items()}
    out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(base/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    p=out/'nes_sink_spi165.sv';s=p.read_text()
    s=once(s,"if(command==8'he0&&byte_count>=1&&byte_count<=19)","if(ours&&byte_count>=1&&byte_count<=19)")
    s=once(s,"   end else if(sck[1]&&!prev_sck)begin", "   end else if(sck[1]&&!prev_sck)begin")
    # Rotation must run alongside E1 input CRC/RAM writes, not in its else chain.
    s=once(s,"     end else if(command==8'he0)begin\n      if(byte_count>=2&&byte_count<=18)snapshot<={snapshot[127:0],snapshot[135:128]};\n     end else if(command==8'he1)begin", "     end else if(command==8'he1)begin")
    s=once(s,"     if(byte_count!=511)byte_count<=byte_count+1'b1;", "     if(byte_count!=511)byte_count<=byte_count+1'b1;\n     if(ours&&byte_count>=2&&byte_count<=18)snapshot<={snapshot[127:0],snapshot[135:128]};")
    if qualified:
        # Progress can be set only on the checked empty receipt. Every new
        # E1/ACK write/publish clears it. Keep raw STOP/enable/fault masking;
        # do not repeat the retired/accepted and ACK state comparators here.
        s=once(s,'(progress&&!stop&&idle_receipt)', '(progress&&!stop&&enable&&!fault)')
    if rotation:
        # One update enable for the same 17-byte rotation. Initial capture
        # below retains priority. CRC and serial paths no longer carry two
        # independently nested assignments to the entire snapshot register.
        s=once(s,'   if(crc_busy)begin\n    snapshot<={snapshot[127:0],snapshot[135:128]};',
            '''   if(crc_busy || (!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&ours&&byte_count>=2&&byte_count<=18))
    snapshot<={snapshot[127:0],snapshot[135:128]};
   if(crc_busy)begin''')
        s=once(s,"     if(ours&&byte_count>=2&&byte_count<=18)snapshot<={snapshot[127:0],snapshot[135:128]};\n",'')
    p.write_text(s,encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h};assert set(changed)=={'nes_sink_spi165.sv'}
    (out/'inputs709.json').write_text(json.dumps(dict(stage=709,base=pins,changed=changed,qualified=qualified,rotation=rotation,scope=__doc__,constraints_changed=False,seed_changed=False),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['arm','board'])
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--qualified',action='store_true')
    p.add_argument('--needed',action='store_true')
    p.add_argument('--rotation',action='store_true')
    a=p.parse_args()
    if a.kind=='arm':assert not(a.qualified or a.rotation);arm(a.base,a.out,a.needed)
    else:assert not a.needed;board(a.base,a.out,a.qualified,a.rotation)
