"""Materialize an exact, preceding-input map-block reference on the MMC849 receive path."""
import argparse
from pathlib import Path

from nes_raw506 import once


def arm(src, out):
    name = 'nes_native165.c'
    s = (src/name).read_text()
    s = once(s, 's->state=NES_NATIVE165_IDLE;return true;}',
             's->counts[0]=0;s->state=NES_NATIVE165_IDLE;return true;}')
    s = once(s, 'nes_native165_reset(s);s->next_token=tok;', '''
  unsigned history=(uint16_t)(s->generation+1)==gen?s->counts[0]:0;
  /* At IDLE the preceding input is consumed. Reset all frame state except
   * the map prefix, which is verified in-place before a reference can use it. */
  memset((uint8_t *)s+sizeof(s->maps),0,sizeof(*s)-sizeof(s->maps));
  s->next_token=tok;''')
    s = once(s,'s->last_tile=65535;', 's->last_tile=history;')
    s = once(s,'const uint8_t *b,unsigned n){\n static const uint8_t distance',
             'const uint8_t *b,unsigned n,bool reuse){\n static const uint8_t distance')
    s = once(s, 'unsigned at=0,i=6;', '''unsigned at=0,i=6;
 if(reuse){
  if(n!=6 || start+count>s->last_tile)return fail(s,36);
  while(at<count){require_tile(s,dst[at]&8191,1);at++;}
 }''')
    s = once(s, 'if(tag==65535){','if(tag>=65534){')
    s = once(s,'restore650(s,gen,p+pos,n-pos)', 'restore650(s,gen,p+pos,n-pos,tag==65534)')
    out.mkdir(parents=True,exist_ok=True)
    (out/name).write_bytes(s.encode())


def board(src, out):
    out.mkdir(parents=True,exist_ok=True)
    name='nes_native_spi165.sv'
    s=(src/name).read_text()
    s=once(s,' wire [15:0] crc_arg;', '''
 // One registered old-data read on each accepted cell. Update the same
 // address on its high-byte cycle, which cannot accept another cell.
 (* ramstyle="M9K" *) reg [14:0] previous_cells[0:1055];
 reg [14:0] previous_cell,incoming_cell;
 reg [10:0] incoming_index,previous_count;
 reg [15:0] previous_gen;
 reg history_valid,following,block_match;
 wire [10:0] cell_index=record_data[74:64];
 always @(posedge clk)begin
  if(take_cell)begin
   previous_cell<=previous_cells[cell_index];
   incoming_index<=cell_index;
   incoming_cell<=record_data[14:0];
  end else if(cell_tail)previous_cells[incoming_index]<=incoming_cell;
 end
 always @(posedge clk)begin
  if(reset || fault)begin history_valid<=0;following<=0;block_match<=0;end
  else begin
   if(record_valid && record_ready && record_data[95:93]==7)begin
    case(record_data[76:64])
     0:begin following<=history_valid && record_data[92:77]==previous_gen+16'd1;history_valid<=0;end
     2:begin following<=0;history_valid<=0;end
     3:begin previous_count<=incoming_index+1'b1;previous_gen<=record_data[92:77];history_valid<=1;end
     default:;
    endcase
   end
   if(cell_tail)block_match<=(cells==0 || block_match) && following &&
                           incoming_index<previous_count && previous_cell==incoming_cell;
  end
 end
 wire [15:0] crc_arg;''')
    s=once(s,'.run(transform),','.run(transform),.reuse(block_match),')
    (out/name).write_bytes(s.encode())
    name='nes_geometry_sender653.sv'
    s=(src/name).read_text()
    s=once(s,'clk,reset,run,has_header','clk,reset,run,has_header,reuse')
    s=once(s,"0,1:write_data=8'hff;","0:write_data=8'hff;1:write_data=reuse?8'hfe:8'hff;")
    s=once(s,'if(index==9)begin index<=0;state<=STEP;end', '''if(index==9)begin
      index<=0;
      if(reuse)begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end else state<=STEP;
     end''')
    (out/name).write_bytes(s.encode())
    for n in ('nes_native_export203.sv','nes_native_mailbox165.sv'):
        (out/n).write_bytes((src/n).read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=('arm','board'))
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    (arm if a.target=='arm' else board)(a.src,a.out)
