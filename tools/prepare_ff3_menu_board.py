"""Attach the in-game command mailbox to the FF3 board's qualified host bus."""
import argparse
from pathlib import Path
import shutil

from prepare_ff3_display1037 import build
from prepare_nes_kirby1023 import edit


def menu_board(board,client=None):
    build(board)
    root=Path(__file__).resolve().parents[1]
    shutil.copy2(root/'src/nes/nes_menu_reply.sv',board)
    with (board/'board.qsf').open('a') as qsf:
        qsf.write('\nset_global_assignment -name SYSTEMVERILOG_FILE nes_menu_reply.sv\n')
    edit(board,'nes_screen_status151.sv',
         ('module nes_screen_status151(', 'module nes_screen_status151(output wire [7:0] menu_status,'),
         ('reg addr_stable,was_stage,was_error;', 'reg addr_stable,was_stage,was_error,was_menu;'),
         ("address==24'h007001;", "(address==24'h007001 || address==24'h007002);"),
         ('was_stage<=0;was_error<=0;', 'was_stage<=0;was_error<=0;was_menu<=0;'),
         ("was_stage<=addr_sync==24'h007000;", "was_menu<=addr_sync==24'h007002;was_stage<=addr_sync==24'h007000;"),
         (' assign selected=', ''' wire [7:0] menu_request;
 nes_menu_reply menu(.clk(clk),.reset(reset),.cancel(trace_cancel || !active_sync[1]),
  .submit(qualified && !seen && was_menu),.request_data(data_previous),
  .spi_idle(ss_sync[1]),.spi_byte(trace_byte),.selected(command==8'h7a),
  .byte_count(byte_count),.bit_count(bit_count),.incoming(incoming),
  .pending(menu_request),.status(menu_status));
 assign selected='''),
         ("command==8'h73||command==8'h78", "command==8'h73||command==8'h78||command==8'h7a"),
         ("snapshot<={8'he6,stage,status_error,", "snapshot<=incoming==8'h7a ? {menu_request,~menu_request,40'd0} : {8'he6,stage,status_error,"))
    edit(board,'fxpak_nes_screen137_top.sv',
         (' nes_screen_status151 screen_status(', ' wire [7:0] menu_status;\n nes_screen_status151 screen_status(.menu_status(menu_status),'),
         (' nes_sink_bridge165 sink(', ' nes_sink_bridge165 sink(.menu_status(menu_status),'))
    edit(board,'nes_sink_bridge165.sv',
         ('module nes_sink_bridge165(', 'module nes_sink_bridge165(input wire [7:0] menu_status,'),
         (' nes_sink_bus165 bus(', ' nes_sink_bus165 bus(.menu_status(menu_status),'))
    edit(board,'nes_sink_bus165.sv',
         ('module nes_sink_bus165(', 'module nes_sink_bus165(input wire [7:0] menu_status,'),
         ("  16'h6004:control_data=", "  16'h6002:control_data=menu_status;\n  16'h6004:control_data="))
    if client is not None:
        # The loader increments only on accepted write retirement. Cache the
        # all-ones low byte on that same clock enable, including clears, so
        # the 168 MHz upper count and final-byte check avoid a 19-bit carry.
        loader=board/'nes_rom_loader.sv'
        counter=loader.read_text()
        anchor=' always @(posedge mem_clk or posedge reset)begin\n  if(reset)loaded_bytes<=0;'
        assert counter.count(anchor)==1 and "wire [19:0] total=20'h80000" in counter
        counter=counter.replace(anchor,""" reg low_full;
 always @(posedge mem_clk or posedge reset)
  if(reset)low_full<=0;
  else if(count_update)low_full<=count_increment_data && loaded_bytes[7:0]==8'hfe;
"""+anchor)
        for bit in range(8,20):
            old=f'(&loaded_bytes[{bit-1}:0])'
            assert counter.count(old)==1
            upper=f'(low_full && (&loaded_bytes[{bit-1}:8]))' if bit>8 else 'low_full'
            counter=counter.replace(old,upper)
        assert counter.count("loaded_bytes==total-1'b1")==1
        loader.write_text(counter.replace("loaded_bytes==total-1'b1",
                                          "(low_full && loaded_bytes[19:8]==12'h7ff)"))
        from build_ff3_menu_client import program
        program(client)
        shutil.copyfile(client/'sink-program.hex',board/'sink-program.hex')
        edit(board,'nes_sink_bus165.sv',('program_rom[0:5119]','program_rom[0:7167]'),
             ("address[14:0]<15'h13c0", "(address[14:0]<15'h13c0 || "
              "(address[14:0]>=15'h1400 && address[14:0]<15'h1c00))"))
        # The optional SPI78 diagnostic occupies three M9Ks. The playable
        # profile gives two to the menu ROM. Keep the scheduler's exact clock
        # phase and publish no valid diagnostic footer from this image.
        t=board/'nes_display1010.sv'
        text=t.read_text()
        assert 'assign offer_phase=clock_count[14];' in text
        ports=text[:text.index(' (* altera_attribute')].replace('output reg [7:0] reply','output wire [7:0] reply')
        # The diagnostic toggle and its receiver both disappear in this profile.
        # Keep all other source/destination checks strict.
        sdc=board/'board.sdc'
        constraints=sdc.read_text()
        first=constraints.index('set src1010 ')
        last=constraints.index('\n',constraints.index('set_false_path -hold -from $src1010',first))
        diagnostic=constraints[first:last]
        assert len(diagnostic.splitlines())==4 and 'done_sync[0]' in diagnostic
        # Give the placer additional routing margin on the three measured
        # 168 MHz endpoints. All functional STA checks and hold checks remain.
        placement="""
set mem_loader {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader}
foreach source {
 {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|start}
 {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed}
} {
 foreach bit {1 2 4} {
  set_max_delay 4.9 -from [cdc181_exact $source] -to [cdc181_exact [format {%s|remaining[%d]} $mem_loader $bit]]
 }
}
set_max_delay 4.9 -from [cdc181_exact {nes_live_joint:core|nes_diag_clock_guard127:clock_guard|ref_qualified}] -to [cdc181_exact {nes_live_joint:core|nes_diag_clock_guard127:clock_guard|ref_ok_mem[0]}]
"""
        sdc.write_text(constraints[:first]+constraints[last:]+placement)
        t.write_text(ports+''' reg clear_record;
 reg [14:0] phase_clock;
 assign offer_phase=phase_clock[14];
 always @(posedge clk) begin
  clear_record<=reset || !active || cancel;
  phase_clock<=clear_record ? 15'd0 : phase_clock+1'b1;
 end
 assign reply=8'd0;
endmodule
''')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('board',type=Path)
    p.add_argument('--client',type=Path)
    args=p.parse_args()
    menu_board(args.board,args.client)
