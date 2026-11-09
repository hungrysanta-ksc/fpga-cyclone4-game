"""Skip unused E1 snapshots without publishing unvalidated status or credit.

Raw retired bytes are only a skip hint. E0 and every used E1 response retain
the complete CRC8/counter/identity checks; final ACK remains mandatory.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha
from prepare_nes_credit709 import arm as previous_arm,board as previous_board

def arm(base,out):
    previous_arm(base,out,needed=True)
    p=out/'nes_sink_window184.c';s=p.read_text()
    s=once(s,'(uint16_t)(s->sent-s->retired)>=2 && !response709(s,tx)',
        '(uint16_t)(s->sent-s->retired)>=2 && (uint16_t)((tx[5]<<8)|tx[6])!=s->retired && !response709(s,tx)')
    publication=' s->status_flags=rx[2];s->ack_status=(rx[2]&2)?rx[7]:0;'
    assert s.count(publication)==1
    s=s.replace(publication,'')
    s=once(s,' s->retired=r;return true;',publication+'\n s->retired=r;return true;')
    p.write_text(s,encoding='utf8',newline='\n')
    (out.parent/(out.name+'-recipe.json')).write_text(json.dumps(dict(stage=710,
        base=sha(base/'nes_sink_window184.c'),changed=sha(p),scope=__doc__),indent=2)+'\n',encoding='utf8')

def board(base,out):
    previous_board(base,out,rotation=True)
    p=out/'nes_sink_spi165.sv';s=p.read_text()
    # Snapshot is never observable until a complete command captures every
    # byte. Reset keeps command/count/MISO invalid. Remove the 136-bit reset
    # tree, not STOP gating or the immutable transaction snapshot itself.
    s=once(s,'received_crc<=0;snapshot<=0;status_crc<=0;', 'received_crc<=0;status_crc<=0;')
    rotate='''   if(crc_busy || (!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&ours&&byte_count>=2&&byte_count<=18))
    snapshot<={snapshot[127:0],snapshot[135:128]};
'''
    s=once(s,rotate,'')
    capture='''      snapshot[135:128]<=flags;
      snapshot[127:112]<=accepted;snapshot[111:96]<=retired;
'''
    s=once(s,capture,'')
    ack="      for(j=0;j<12;j=j+1)snapshot[95-j*8-:8]<=ack_valid?ack_work[j*8+:8]:8'd0;\n"
    s=once(s,ack,'')
    s=once(s,' always @(posedge clk or posedge reset)begin', ''' // Contents need no reset: reply/command/count are reset and command
 // capture dominates rotation before any snapshot byte can be exposed.
 always @(posedge clk)begin
  if(!reset)begin
   if(!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&byte_count==0)begin
      snapshot[135:128]<=flags;
      snapshot[127:112]<=accepted;snapshot[111:96]<=retired;
      for(j=0;j<12;j=j+1)snapshot[95-j*8-:8]<=ack_valid?ack_work[j*8+:8]:8'd0;
   end else if(crc_busy || (!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&ours&&byte_count>=2&&byte_count<=18))
    snapshot<={snapshot[127:0],snapshot[135:128]};
  end
 end
 always @(posedge clk or posedge reset)begin''')
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs709.json').read_text());m.update(stage=710,scope=__doc__,snapshot_reset_removed=True)
    m['changed']={n:sha(out/n) for n,h in m['base'].items() if sha(out/n)!=h}
    (out/'inputs710.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['arm','board'])
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();(arm if a.kind=='arm' else board)(a.base,a.out)
