"""Generate a cycle-equivalent 660 reader and SPI D1 response for whole-board timing."""
import argparse
import re
from pathlib import Path
from nes_raw506 import once
from prepare_nes_owner660 import build as owner


def board(base, out, timing):
    owner(base, out)
    if timing in ("decode", "stream"):
        loader = out / "nes_rom_loader.sv"
        src = loader.read_text()
        first = src.index(" (* preserve, dont_merge *) reg [1:0] reject_state;")
        end = src.index(" wire illegal_begin=", first)
        timed = src[src.index(" wire timed_phase=", first):].splitlines()[0]
        src = src[:first] + timed + """
 wire reject_begin=phase[RECEIVE] || phase[RUN] || timed_phase;
 wire [1:0] reject_state={phase[IDLE] || reject_begin,reject_begin};
 wire reject_data_state=phase[IDLE] || phase[READY] || phase[RUN];
""" + src[end:]
        first = src.index(" // State-only legality advances")
        end = src.index(" end\n", src.index("reject_data_state<=to_idle", first)) + len(" end\n")
        if src[end:].startswith(" end\n"):
            end += len(" end\n")
        loader.write_text(src[:first] + src[end:], newline="\n")
    spi = out / "nes_native_spi165.sv"
    s = spi.read_text()
    # At command acceptance, reading and status_size snapshot the same sealed
    # block. A D1 cannot retire it. Use that size up to and including SS rise.
    for old in ("byte_count<=public_size", "byte_count==public_size+1",
                "byte_count==public_size+2", "byte_count==public_size+3"):
        s = once(s, old, old.replace("public_size", "status_size"))
    if timing in ("tail", "stream", "index", "launch", "mux", "pack"):
        # Count the two CRC bytes at byte boundaries. A fourth state accepts
        # only the exact SS retirement edge; a surplus byte invalidates it.
        s = once(s, " reg [7:0] status_crc;", """ reg [7:0] status_crc;
 localparam PAYLOAD=0,CRC_HIGH=1,CRC_LOW=2,EXACT=3,EXTRA=4;
 reg [2:0] tail;
 always @(posedge clk or posedge reset)begin
  if(reset)tail<=PAYLOAD;
  else if(ss[1])tail<=PAYLOAD;
  else if(sck[1] && !prev_sck && bit_count==7)begin
   if(byte_count==0)tail<=(public_size==0)?CRC_HIGH:PAYLOAD;
   else case(tail)
    PAYLOAD:if(byte_count==status_size)tail<=CRC_HIGH;
    CRC_HIGH:tail<=CRC_LOW;
    CRC_LOW:tail<=EXACT;
    default:tail<=EXTRA;
   endcase
  end
 end""")
        s = once(s, "if(byte_count>=1&&byte_count<=status_size)reply=read_byte;", "if(tail==PAYLOAD)reply=read_byte;")
        s = once(s, "if(byte_count==status_size+1)", "if(tail==CRC_HIGH)")
        s = once(s, "if(byte_count==status_size+2)", "if(tail==CRC_LOW)")
        s = once(s, "byte_count==status_size+3", "tail==EXACT")
    if timing in ("index", "launch", "mux"):
        # Store the actual RAM address. 511 denotes the command byte and
        # 510 saturates oversized transactions just like byte_count==511.
        s = once(s, "reg [8:0] byte_count;", "reg [8:0] cursor;")
        s = once(s, "byte_count[7:0]-1'b1", "cursor[7:0]")
        s = s.replace("byte_count<=0", "cursor<=9'd511").replace("byte_count==0", "cursor==511")
        s = once(s, "byte_count!=0", "cursor!=511")
        s = once(s, "byte_count!=8", "cursor!=7")
        s = once(s, "byte_count<6", "(cursor==511 || cursor<5)")
        s = once(s, "byte_count>=1 && byte_count<=6", "cursor<6")
        s = once(s, "if(byte_count!=511)byte_count<=byte_count+1'b1;", "if(cursor!=510)cursor<=cursor+1'b1;")
        s = once(s, "if(byte_count==status_size)", "if(cursor[7:0]==status_size[7:0]-8'd1)")
        # Rewrite both case tables, including lines with multiple labels.
        def case(m):
            body = re.sub(r"(^[ \t]*|;)([0-7]):", lambda n: n[1]+str((int(n[2])-1) % 512)+":", m[1], flags=re.M)
            return "case(cursor)" + body + "endcase"
        s = re.sub(r"case\(byte_count\)(.*?)endcase", case, s, flags=re.S)
        assert "byte_count" not in s
    if timing == "pack":
        # A raw-load modifies only the lower 60 bits, and raw-emit only the
        # top 36. Ordinary input is impossible while encoding or transforming.
        # Expose those mutually exclusive enables to the fitter.
        s = once(s, "sealed<=0;encoding<=0;held<=0;", "sealed<=0;encoding<=0;")
        s = once(s, "     held<={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};", "")
        s = once(s, "   end else if(raw_load)held[59:0]<={held[44:0],cell_word};", "   end")
        s = once(s, "    held<={4'h1,group_start[11:0],map_generation,1'b0,group_count,held[59:0]};", "")
        s = once(s, "    held<={held[87:0],8'd0};position", "    position")
        anchor = " reg [7:0] shift,command,request_crc;"
        s = once(s, anchor, """ wire ordinary=record_valid && record_ready && !map_cell;
 wire [95:0] ordinary_word={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};
 always @(posedge clk or posedge reset)
  if(reset)held<=0;
  else begin
   if(ordinary || encoding || raw_load)
    held[59:0]<=({60{ordinary}} & ordinary_word[59:0]) |
                ({60{encoding}} & {held[51:0],8'b0}) |
                ({60{raw_load}} & {held[44:0],cell_word});
   if(ordinary || encoding || raw_emit)
    held[95:60]<=({36{ordinary}} & ordinary_word[95:60]) |
                 ({36{encoding}} & held[87:52]) |
                 ({36{raw_emit}} & {4'h1,group_start[11:0],map_generation,1'b0,group_count});
  end
""" + anchor)
    spi.write_text(s, newline="\n")
    p = out / "nes_rom_physical.sv"
    s = p.read_text()
    # Split admission from timed strobes. CHECK is locally qualified by
    # idle/owner_valid/owner_check, so do not feed check_ready back into request.
    boot = out / "nes_rom_boot.sv"
    boot.write_text(once(boot.read_text(), "check_request && raw_check_ready && address_valid && !check_failed",
                         "check_request && address_valid && !check_failed"), newline="\n")
    if timing in ("launch", "mux"):
        # The selected owner is immutable until asynchronous release. Register
        # the two mutually exclusive enables at that boundary instead of
        # decoding valid + owner in series with the IDLE transition.
        s = once(s, "reg owner_valid,owner_check;", "reg owner_valid,owner_check,owner_run;")
        s = once(s, "owner_valid<=0;owner_check<=0;", "owner_valid<=0;owner_check<=0;owner_run<=0;")
        s = once(s, "owner_check<=check_mode;", "owner_check<=check_mode;owner_run<=!check_mode;")
        s = once(s, "owner_valid && (owner_check ? check_request : request_sync[1]!=ack_toggle)",
                 "(owner_check && check_request) || (owner_run && request_sync[1]!=ack_toggle)")
        s = once(s,"owner_valid && owner_check && state==IDLE","owner_check && state==IDLE")
        if timing == "launch":
            p.write_text(s, newline="\n")
            return
    if timing == "counter":
        phases = """ reg in_active;
 localparam CW=$clog2(READ_CYCLES+1);
 reg [CW-1:0] remaining;
 wire terminal=in_active && remaining==1;
 wire sample_next=(READ_CYCLES==1 && setup_phase) || (in_active && remaining==2);
 always @(posedge mem_clk or posedge mr)
  if(mr) begin remaining<=0;in_active<=0;end
  else begin
   if(setup_phase)begin remaining<=CW'(READ_CYCLES);in_active<=1;end
   else if(in_active)begin remaining<=remaining-1'b1;if(terminal)in_active<=0;end
  end
"""
    else:
        phases = """ reg [READ_CYCLES-1:0] read_pipe;
 always @(posedge mem_clk or posedge mr)
  if(mr)read_pipe<=0;else read_pipe<=(read_pipe<<1)|setup_phase;
 wire terminal=read_pipe[READ_CYCLES-1];
 wire sample_next;
 generate if(READ_CYCLES==1)assign sample_next=setup_phase;
 else assign sample_next=read_pipe[READ_CYCLES-2];endgenerate
"""
    s = s[:s.index(" localparam CW=")] + " reg idle,setup_phase,hold_phase,release_phase;\n" + phases + s[s.index(" reg chip,lane;"):]
    s = s[:s.index(" wire capture_next=")] + s[s.index(" always @(posedge mem_clk or posedge mr)", s.index(" wire capture_next=")):]
    s = s.replace("<=capture_next", "<=sample_next").replace("state==IDLE", "idle")
    s = s.replace("state==SETUP", "setup_phase").replace("state==HOLD || state>RELEASE", "hold_phase")
    start = s.index(" always @(posedge mem_clk or posedge mr)begin", s.index("assign psram_ble="))
    s = s[:start] + """ wire admit=idle && pending;
 always @(posedge mem_clk or posedge mr)begin
  if(mr)begin
   idle<=1;setup_phase<=0;hold_phase<=0;release_phase<=0;reading_active<=0;
   ack_toggle<=0;check_response<=0;psram_address<=0;chip<=0;lane<=0;
  end else begin
   setup_phase<=admit;hold_phase<=terminal;release_phase<=hold_phase;
   idle<=(idle && !pending) || release_phase;
   if(admit)begin
    psram_address<={2'b0,selected_address[21:2]};chip<=selected_address[1];lane<=selected_address[0];
   end
   if(setup_phase)reading_active<=1;
   else if(hold_phase)reading_active<=0;
   if(terminal && !owner_check)ack_toggle<=request_sync[1];
   check_response<=release_phase && owner_check;
  end
 end
endmodule
"""
    p.write_text(s, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("timing", choices=("counter", "pipe", "decode", "tail", "stream", "index", "launch", "mux", "pack"))
    args = parser.parse_args()
    board(args.base, args.out, args.timing)
