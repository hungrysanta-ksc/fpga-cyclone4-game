"""Transfer the payload from the exporter's held_data FFs to the host capture FFs."""
import re
from nes_raw506 import once
from nes_count657 import status


def producer(s):
    s=once(s,"reg [3:0] state;", "localparam FORMAT=5;reg cancel_pending;reg [3:0] state;")
    s=s.replace("query_index<limit&&live;","query_index<limit&&live&&tx_ready&&!cancel_pending;")
    s=once(s,"assign ack_ready=!reset;","assign ack_ready=!reset && tx_ready && !cancel_pending;")
    s=once(s,"   default:tx_valid=0;\n  endcase","   default:tx_valid=0;\n  endcase\n  if(cancel_pending)tx_valid=0;")
    begin=s.index("     if(map_repeat && pack_count>=10)tx_data")
    end=s.index("    else if(query_kind==1",begin)
    s=s[:begin]+"""    end else if(query_kind==0)tx_data[79:64]={3'd0,pack_start};
"""+s[end:]
    s=s.replace("state<=VALUE;","state<=FORMAT;").replace("?VALUE:","?FORMAT:")
    s=once(s,"    VALUE:if(tx_ready)begin","""    FORMAT:begin
     if(query_kind==0)held_data[63]<=query_index==limit;
     if(query_kind==7)begin
      if(map_repeat && pack_count>=10)held_data[63:6]<={49'd0,pack_count};
      else held_data[63:60]<=pack_count[3:0];
     end
     state<=VALUE;
    end
    VALUE:if(tx_ready)begin""")
    s=once(s,"if(reset)begin state<=IDLE;","if(reset)begin cancel_pending<=0;state<=IDLE;")
    s=once(s,"if(state!=IDLE&&state!=ABORT&&state!=DRAIN&&state!=COMMIT&&!live)fail(1);",
           """if(!tx_ready)begin
    // The destination can pause. Release a lost lease once, but do not
    // overwrite the launched bundled data before its acknowledged capture.
    if(!cancel_pending && state!=IDLE && state!=ABORT && state!=DRAIN && state!=COMMIT && !live)begin
     cancel_pending<=1;error<=1;release_frame<=1;
    end
   end else if(cancel_pending)begin
    held_data<={generation,44'd0,error};cancel_pending<=0;state<=ABORT;
   end else if(state!=IDLE&&state!=ABORT&&state!=DRAIN&&state!=COMMIT&&!live)fail(1);""")
    # Retain the offered payload on the same edge that toggles request.
    return s.replace("held_data<=0;state<=ASK;", "state<=ASK;")


def direct_board(out):
    def edit(name,fn):
        p=out/name
        p.write_text(fn(p.read_text()),newline="\n")
    edit("nes_native_export203.sv", producer)
    edit("nes_native_spi165.sv",status)
    def mailbox(s):
        s=once(s,"parameter WIDTH=96","parameter WIDTH=96,parameter EXTERNAL_PAYLOAD=0")
        s=once(s," assign src_ready=", """ wire [WIDTH-1:0] sample;
 generate if(EXTERNAL_PAYLOAD)begin
  assign sample={held[WIDTH-1:64],src_data[63:0]};
 end else assign sample=held;endgenerate
 assign src_ready=""")
        return once(s,"received<=held;","received<=sample;")
    edit("nes_native_mailbox165.sv",mailbox)
    edit("nes_live_joint.sv",lambda s:once(s,".WIDTH(80)) native_records",".WIDTH(80),.EXTERNAL_PAYLOAD(1)) native_records"))
    def constraints(s):
        return re.sub(r"nes_native_mailbox165:native_records\|held\[(\d+)\]",lambda m:
            "nes_native_export203:native_export|held_data["+m[1]+"]" if int(m[1])<64 else m[0],s)
    for p in out.glob("*.sdc"):
        if constraints(p.read_text())!=p.read_text():edit(p.name,constraints)
