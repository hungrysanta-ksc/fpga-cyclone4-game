"""Build the sealed-E9 shared-port candidate from the fitted 906/907 board."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once
from prepare_nes_frame900 import fit, QUARTUS

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / 'tests/nes-functional'


def compact_spi(s):
    # One signed distance serves all comparisons, including invalid lengths.
    delta = """ wire signed [10:0] tail_distance=$signed({1'b0,count})-$signed({1'b0,length[9:0]});
 wire before_end=(|length[15:10])||tail_distance[10];
 wire past_end=!before_end;
"""
    s = once(s, ' always @*begin\n  reply=0;', delta+' always @*begin\n  reply=0;')
    for n in (3,5):
        s=once(s,f'count<=length+{n}',f"(before_end||tail_distance<=11'sd{n})")
    for n in (4,5,6,7):
        s=once(s,f'count==length+{n}',f"(past_end&&tail_distance==11'sd{n})")
    s=once(s,'count!=length+8',"(before_end||tail_distance!=11'sd8)")
    # Qualify optional descriptor bytes using the ready bit sampled at E8.
    # The first-fault overlay at output octets 14/15 takes precedence.
    for field in ('{7\'d0,chunk_kind}', 'chunk_length[7:0]',"{4'd0,chunk_length[11:8]}",
                  'offset[7:0]','offset[15:8]','chunk_generation[7:0]','chunk_generation[15:8]',
                  *(f'chunk_token[{i+7}:{i}]' for i in range(0,32,8))):
        s=once(s,"chunk_ready?"+field+":8'd0",field)
    s=once(s,'reply=snapshot[(19-count)*8+:8];',"""begin
   case(count[4:0])
"""+''.join(f"    5'd{i}:reply=snapshot[{(19-i)*8}+:8];\n" for i in range(1,19))+"""    default:reply=0;
   endcase
   if(count>=7&&count<=17&&!snapshot[104]&&!(snapshot[135]&&(count==14||count==15)))reply=0;
  end""")
    return s


def serial_crc(s):
    # MISO is latched on the falling edge. The following rising edge consumes
    # exactly the corresponding response bit. E9 and EA consume MOSI instead.
    for line in ('      request8<=crc8(0,incoming);', '      status_crc<=0;',
                 '      if(count<=18)status_crc<=crc8(status_crc,reply);',
                 '      if(count<=4)request8<=crc8(request8,incoming);',
                 "      if((before_end||tail_distance<=11'sd5)||count<=3)request8<=crc8(request8,incoming);"):
        s=once(s,line+'\n','')
    s=once(s,'status_crc,reply','reply')
    s=once(s,'snapshot<=0;status_crc<=0;', 'snapshot<=0;')
    s=once(s,'reply=status_crc;', 'reply=request8;')
    return once(s,"    shift<=incoming;bits<=bits+1'b1;","""
    if(count==0&&bits==7&&incoming==8'he8)request8<=0;
    else if(count==0||(command==8'he8&&count<=18)||(command==8'hea&&count<=4)||
            (command==8'he9&&(count<=3||before_end||tail_distance<=11'sd5)))
     request8<={request8[6:0],1'b0}^
       ((request8[7]^((count!=0&&command==8'he8)?miso_hold:mosi[1]))?8'h07:8'h00);
    shift<=incoming;bits<=bits+1'b1;""")


def prepare(temp, revision):
    src = temp / 'nes-trial816-board906'
    # Each successive candidate retains the preceding structural changes.
    parent = '' if revision=='A' else 'nes-port914'+revision
    dst = temp / parent / 'nes-trial816-board914'
    dst.mkdir(parents=True, exist_ok=True)
    for sub in ('rtl', 'sys'):
        shutil.copytree(src / sub, dst / sub, dirs_exist_ok=True)
    for f in src.iterdir():
        if f.suffix in ('.sv', '.v', '.vhd', '.qsf', '.qpf', '.sdc', '.tcl', '.hex'):
            shutil.copyfile(f, dst / f.name)
    shutil.copyfile(ROOT.parent / 'probes/nes-prefetch912/consumer/sink-program.hex',
                    dst / 'sink-program.hex')
    for name in ('nes_e9_rows914', 'nes_e9_scan914'):
        shutil.copyfile(RTL / (name + '.sv'), dst / (name + '.sv'))
        with (dst / 'board.qsf').open('a') as out:
            out.write(f'\nset_global_assignment -name SYSTEMVERILOG_FILE {name}.sv\n')

    ports = ('output wire hint,output wire [12:0] hint_tag,output wire [7:0] hint_mask,'
             'input wire hint_ready,')
    con = '.hint(hint),.hint_tag(hint_tag),.hint_mask(hint_mask),.hint_ready(hint_ready),'
    batch = dst / 'nes_plan_batch206.sv'
    s = once(batch.read_text(), ' output wire plan_closed', ' '+ports+'\n output wire plan_closed')
    s = once(s, " always @(posedge nes_clk)data<=payload[{reader,9'(offset+{4'd0,at})}];", """
 wire spec_read;wire [8:0] spec_offset;
 nes_e9_scan914 scan(.clk(nes_clk),.cancel(nr||nc||!lease_valid),
  .owned(word_valid&&!word_ready),.port_free(state!=READ),.length(word[14:5]),
  .generation(lease_generation),.data(data),.read_req(spec_read),.address(spec_offset),
  .hint(hint),.tag(hint_tag),.mask(hint_mask),.hint_ready(hint_ready));
 always @(posedge nes_clk)data<=payload[spec_read?{word[15],spec_offset}:{reader,9'(offset+{4'd0,at})}];""")
    if revision>='E':
        s=once(s,' output wire [103:0] plan_alt_tags,',' input wire [2:0] next_alt_row,output wire [103:0] plan_alt_tags,')
        start=s.index('reg [12:0] alt[0:7];')
        end=s.index(' function automatic [3:0] popcount',start)
        s=s[:start]+'''// The tile reads a single alternate row. Prefetch that address on the previous
 // NES edge. The independently decoded mask excludes untouched RAM entries.
 (* ramstyle="M9K, no_rw_check" *) reg [12:0] alternate[0:7];
 reg [7:0] alt_low;reg [12:0] alt_q;
 always @(posedge nes_clk)begin
  alt_q<=alternate[next_alt_row];
  if(!nc&&state==CAPTURE&&at>=16)begin
   if(!at[0])alt_low<=data;
   else alternate[alt_index[2:0]]<={data[4:0],alt_low};
  end
 end
 assign plan_alt_tags={8{alt_q}};
'''+s[end:]
        assert s.count('for(i=0;i<8;i=i+1)alt[i]<=0;')==2
        s=s.replace('for(i=0;i<8;i=i+1)alt[i]<=0;','')
        s=once(s,"default:if(!at[0])alt[alt_index][7:0]<=data;",'default:if(at[0])begin')
        s=once(s,"else begin alt[alt_index][12:8]<=data[4:0];",'')
    if revision>='F':
        s=once(s,' wire spec_read;', ''' // Capture the bundled word only after the mailbox request has synchronized.
 (* preserve, dont_merge *) reg [10:0] spec_key;
 reg key_valid;
 always @(posedge nes_clk)begin
  if(nr||nc||!word_valid||word_ready)key_valid<=0;
  else if(!key_valid)begin key_valid<=1;spec_key<=word[15:5];end
 end
 wire spec_read;''')
        s=once(s,'.owned(word_valid&&!word_ready)', '.owned(key_valid&&word_valid&&!word_ready)')
        s=once(s,'.length(word[14:5])','.length(spec_key[9:0])')
        s=once(s,'{word[15],spec_offset}','{spec_key[10],spec_offset}')
        path='nes_live_joint:core|nes_direct206:direct_path|nes_plan_batch206:transport|'
        with (dst/'cdc576.sdc').open('a') as out:
            out.write('\n# E9 bundled key: held before synchronized request until consumer ACK.\n')
            for bit in range(11):
                source=f'[cdc181_exact {{{path}nes_native_mailbox206:control|held[{bit+5}]}}]'
                target=f'[cdc181_exact {{{path}spec_key[{bit}]}}]'
                out.write(f'set_max_delay 20.0 -from {source} -to {target}\n')
                out.write(f'set_false_path -hold -from {source} -to {target}\n')
    batch.write_text(s, newline='\n')
    direct = dst / 'nes_direct206.sv'
    s = once(direct.read_text(), ' wire short_bg660;', ' wire short_bg660,hint,hint_ready;wire [12:0] hint_tag;wire [7:0] hint_mask;')
    for mark in ('nes_plan_batch206 transport(', 'source(.evt905'):
        replacement = mark + con if mark.endswith('(') else 'source(' + con + '.evt905'
        s = once(s, mark, replacement)
    if revision>='E':
        s=once(s,' nes_plan_batch206 transport(',''' wire [3:0] next_tile_index=tv&&otready?ti[3:0]+1'b1:ti[3:0];
 nes_plan_batch206 transport(.next_alt_row(next_tile_index[3:1]),''')
    direct.write_text(s, newline='\n')
    source = dst / 'nes_source_tile192.sv'
    s = once(source.read_text(), ' output reg [2:0] evt905,', ' '+ports.replace('output wire','input wire').replace('input wire hint_ready','output wire hint_ready')+'\n output reg [2:0] evt905,')
    s = once(s,'.second_plane(bg_word)', '.second_plane(pair_hi)')
    s = once(s,'{done,arb_request&&arb_ready,arb_request}',
             '{done,shared_req&&shared_ready,shared_req}')
    s = once(s,' wire tile_fault,arbiter_fault;', ' wire tile_fault,arbiter_fault,shared_req,shared_ready;wire [7:0] pair_hi;')
    s = once(s,' nes_native_arbiter165 #(.SOURCE_HOLDS_KEY(USE_CACHE)) arbiter(', '''
 wire shared_reply;wire [21:0] shared_address,actual_address;
 wire [15:0] actual_generation;wire [7:0] actual_lo;
 wire invalidate=arb_abort||!lease||cap_release||fault;
 nes_e9_rows914 ahead(.clk(clk),.reset(reset),.invalidate(invalidate),
  .hint(hint),.tag(hint_tag),.mask(hint_mask),.hint_ready(hint_ready),
  .demand(arb_request),.pair(plan_short&&out_kind==1),.address(arb_address),
  .ready(arb_ready),.response(arb_response),.lo(arb_data),.hi(pair_hi),
  .request(shared_req),.physical_address(shared_address),.grant_ready(shared_ready),
  .reply(shared_reply),.physical_done(mem_response),.physical_error(arb_error),
  .reply_address(actual_address),.physical_lo(actual_lo),.physical_hi(bg_word));
 assign arb_reply_address=shared_reply?actual_address:arb_address;
 assign arb_reply_generation=shared_reply?actual_generation:arb_generation;
 nes_native_arbiter165 #(.SOURCE_HOLDS_KEY(0)) arbiter(''')
    for a,b in [('fill_request(arb_request)','fill_request(shared_req)'),
                ('fill_abort(arb_abort)','fill_abort(invalidate)'),('fill_address(arb_address)','fill_address(shared_address)'),
                ('fill_ready(arb_ready)','fill_ready(shared_ready)'),('fill_response(arb_response)','fill_response(shared_reply)'),
                ('fill_response_address(arb_reply_address)','fill_response_address(actual_address)'),
                ('fill_response_generation(arb_reply_generation)','fill_response_generation(actual_generation)'),
                ('fill_data(arb_data)','fill_data(actual_lo)')]:
        s = once(s, a, b)
    if revision>='D':
        s=once(s,'nes_e9_rows914 ahead(', 'nes_e9_rows914 #(.COMPACT(1)) ahead(')
    if revision>='G':
        s=once(s,'.COMPACT(1)', '.COMPACT(1),.CHECK_HINT(1)')
    if revision>='H':
        s=once(s,'.CHECK_HINT(1)', '.CHECK_HINT(1),.SINGLE_READ(1)')
    if revision>='I':
        s=once(s,'.SINGLE_READ(1)', '.SINGLE_READ(1),.COMPLETE_ROW_SET(1)')
    source.write_text(s, newline='\n')
    if revision>='B':
        spi=dst/'nes_plan_spi200.sv'
        body=compact_spi(spi.read_text())
        spi.write_text(serial_crc(body) if revision>='C' else body,newline='\n')
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp', type=Path)
    ap.add_argument('--fit', action='store_true')
    ap.add_argument('--revision', choices=tuple('ABCDEFGHI'), default='I')
    args = ap.parse_args()
    board=prepare(args.temp,args.revision)
    if args.fit:
        fit(board.parent, 914, QUARTUS)
