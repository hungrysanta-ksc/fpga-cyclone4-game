"""Derive read-only diagnostic taps from the SHA-pinned MMC639 board inputs."""
import argparse
import shutil
from pathlib import Path

from check_nes_fault641 import digest, evidence
from nes_status495 import once


def prepare(base, out, stream_crc=True, late_witness=True):
    pins = evidence("trial613-package.json")["inputs"] | evidence("export636-verification.json")["board_changes"]
    pins["sink-program.hex"] = evidence("trial639-package.json")["ROM_read"]["program"]
    assert digest(base / "output_files/board.sof") == evidence("trial639-package.json")["board"]["SHA"]["board.sof"]
    out.mkdir(parents=True, exist_ok=False)
    for name, expected in pins.items():
        assert digest(base / name) == expected, name
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / name, dest)

    def edit(name, changes):
        path = out / name
        code = path.read_text()
        for before, after in changes:
            code = once(code, before, after)
        path.write_text(code, newline="\n")

    edit("nes_plan_batch206.sv", [
        ("output wire plan_closed,", "output wire plan_closed, witness_host, witness_reject,"),
        ("assign plan_closed=closed&&!nc;", """assign plan_closed=closed&&!nc;
 assign witness_host=hf;
 // Same edge that sets nf. nf itself can clear upon host cancellation before the next NES edge.
 assign witness_reject=!nr&&!nc&&(
   (retire_ack&&(!retire_word||!closed||state!=WAIT||word_valid||!lease_ok)) ||
   ((state==READY||state==RUN||state==ENDING)&&!lease_ok) ||
   (state==WAIT&&word_valid&&(closed||retire_valid)) ||
   (state==READ&&(offset+{4'd0,at}>=batch_length||remaining==0||remaining>16||(at>=16&&alt_index>=8))) ||
   (state==CHECK&&(!shape_ok||!lease_ok)));""")])
    edit("nes_tile_bulk206.sv", [
        ("output wire fault,output reg end_sealed", "output wire fault,witness_host,witness_reject,output reg end_sealed"),
        ("wire wend=word_data[33]", """assign witness_host=host_failed;
 assign witness_reject=tile_valid&&tile_ready&&(!input_ok||tile_index!=next_index||
     (next_index!=0&&(skind!=(tile_kind==1)||sgen!=tile_generation||sslot!=tile_slot||slength!=tile_length)));
 wire wend=word_data[33]""")])
    edit("nes_live_joint.sv", [
        (".transport_fault(native_spi_fault||ext_sink_fault)",
         ".transport_fault(native_spi_fault||ext_sink_fault),.input_error(native_spi_fault),.sink_error(ext_sink_fault)")])
    edit("nes_direct206.sv", [
        ("reset,transport_fault,", "reset,transport_fault,input_error,sink_error,"),
        ("wire pw,pr,ps,pi,pv", """wire batch_host,bulk_host,batch_reject,bulk_reject;
 wire [6:0] host_events={command_error,consume_error,bulk_host,batch_host,spi_fault,sink_error,input_error};
 reg [6:0] host_first;
 always @(posedge host_clk or posedge hr)
  if(hr)host_first<=0;
  else if(!hc && host_first==0)host_first<=host_events;
 wire [4:0] nes_events={core_fault,tile_fault,lease_fault,bulk_reject,batch_reject};
 reg [4:0] nes_first;
 always @(posedge nes_clk or posedge nr)
  if(nr)nes_first<=0;
  else if(!nc && nes_first==0)nes_first<=nes_events;
 // Preserve stable NES witness bits. Sample the public fault levels separately
 // if a clock halt prevents a following local edge. Never feed either path back.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [7:0] witness_meta,witness_sync;
 reg [2:0] halt_seen;
 always @(posedge host_clk or posedge hr)
  if(hr)begin witness_meta<=0;witness_sync<=0;halt_seen<=0;end
  else begin
   witness_meta<={core_fault,tile_fault,lease_fault,nes_first};
   witness_sync<=witness_meta;
   if(halt_seen==0)halt_seen<=witness_sync[7:5];
  end
 wire pw,pr,ps,pi,pv"""),
        (".source_fault(hc),", ".source_fault(hc),.host_first(host_first),.nes_first({halt_seen,witness_sync[4:0]}),"),
        (".host_idle(pi),", ".witness_host(batch_host),.witness_reject(batch_reject),.host_idle(pi),"),
        (".plan_taken(pv&&tr),", ".witness_host(bulk_host),.witness_reject(bulk_reject),.plan_taken(pv&&tr),")])
    edit("nes_plan_spi200.sv", [
        ("input wire [31:0] chunk_token,", "input wire [6:0] host_first,input wire [7:0] nes_first,\n input wire [31:0] chunk_token,"),
        ("chunk_ready?chunk_token[7:0]:8'd0,chunk_ready?chunk_token[15:8]:8'd0,",
         "(fault||source_fault)?{1'b0,host_first}:chunk_ready?chunk_token[7:0]:8'd0,\n       (fault||source_fault)?nes_first:chunk_ready?chunk_token[15:8]:8'd0,")])
    if stream_crc:
        # The SPI shift-out mux already presents each complete snapshot byte in order.
        # Accumulate on the last rising edge. Byte 19 is available for the next falling edge.
        edit("nes_plan_spi200.sv", [
            ("reg crc_busy;reg [4:0] crc_at;", ""),
            ("count<=19)reply=", "count<19)reply="),
            ("reply=snapshot[(19-count)*8+:8];", "reply=snapshot[(19-count)*8+:8];\n  else if(command==8'he8&&count==19)reply=status_crc;"),
            ("status_crc<=0;crc_busy<=0;crc_at<=0;", "status_crc<=0;"),
            ("""   if(crc_busy)begin
    status_crc<=crc8(status_crc,snapshot[151-crc_at*8-:8]);
    if(crc_at==17)begin snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_at*8-:8]);crc_busy<=0;end
    else crc_at<=crc_at+1'b1;
   end
""", ""),
            ("status_crc<=0;crc_busy<=1;crc_at<=0;", "status_crc<=0;"),
            ("end else if(command==8'hea)begin\n      if(count<=4)", """end else if(command==8'he8)begin
      if(count<=18)status_crc<=crc8(status_crc,reply);
     end else if(command==8'hea)begin
      if(count<=4)""")])
    if late_witness:
        assert stream_crc
        # The local fault may coincide with command decode, before the cause crosses
        # the synchronizer. Bind the two evidence bytes once, before either shifts out.
        edit("nes_plan_spi200.sv", [
            ("(fault||source_fault)?{1'b0,host_first}:chunk_ready?chunk_token[7:0]:8'd0,\n       (fault||source_fault)?nes_first:chunk_ready?chunk_token[15:8]:8'd0,",
             "chunk_ready?chunk_token[7:0]:8'd0,chunk_ready?chunk_token[15:8]:8'd0,"),
            ("if(count<=18)status_crc<=crc8(status_crc,reply);", """if(count<=18)status_crc<=crc8(status_crc,reply);
      if(count==13 && snapshot[135])snapshot[47:32]<={1'b0,host_first,nes_first};""")])
        # Each asynchronous input feeds only the first flop of a two-flop sampler.
        # Constrain its data delay. Keep setup/hold to the second stage timed normally.
        constraints = """
foreach i {0 1 2 3 4 5 6 7} {
 set witness_pin [cdc181_exact [format {nes_live_joint:core|nes_direct206:direct_path|witness_meta[%d]} $i]]
 set_max_delay 11.904 -from [get_clocks nes] -to $witness_pin
 set_false_path -hold -from [get_clocks nes] -to $witness_pin
}
"""
        for name in ("board.sdc", "nominal204.sdc"):
            with (out / name).open("a", newline="\n") as sdc:
                sdc.write(constraints)
    edit("nes_screen_status151.sv", [
        ("reg [15:0] frames;", """reg [15:0] frames;
 reg [1:0] boot_e0;
 reg [6:0] boot_order;
 wire vector_read=!read_n&&write_n&&!romsel_n&&addr_sync==address&&addr_previous==address&&
                  (address==24'h00fffc||address==24'h00fffd);
 // SPI E0 probes bracket ARM reset release on the deferred-preflight path.
 // Physical RESET is owned/sensed by ARM and is not a pin of this FPGA top.
 wire [7:0] status_error=(stage==0 && error_code==0)?{1'b0,boot_order}:error_code;"""),
        ("stage<=0;error_code<=0;flags<=0;frames<=0;", "stage<=0;error_code<=0;flags<=0;frames<=0;boot_e0<=0;boot_order<=0;"),
        ("if(wr_sync[1])seen<=0;", """if(stage==0)begin
    if(!boot_order[0]&&vector_read)boot_order[3:0]<={boot_e0==2,boot_e0!=0,active_sync[1],1'b1};
    if(!boot_order[4]&&qualified&&addr_previous==24'h007000)
      boot_order[6:4]<={boot_order[0],active_sync[1],1'b1};
   end
   if(wr_sync[1])seen<=0;"""),
        ("command<=incoming;snapshot<={8'he6,stage,error_code,", """command<=incoming;
       if(stage==0 && incoming==8'he0 && boot_e0<2)boot_e0<=boot_e0+1'b1;
       snapshot<={8'he6,stage,status_error,""")])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("base", "out"):
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--separate-crc", action="store_true", help="Reproduce first failed fit")
    parser.add_argument("--early-witness", action="store_true", help="Reproduce command-edge capture control")
    args = parser.parse_args()
    prepare(args.base, args.out, not args.separate_crc, not (args.early_witness or args.separate_crc))
