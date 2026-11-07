"""Materialize the whole 657 port board with an in-place CHR layout and a checked SNES aperture."""
import argparse
from pathlib import Path
import shutil
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def board(base,out,window=True,jobs=False,client=None):
    expected=evidence("record657-verification.json")["modes"]["port"]
    assert digest(base/"output_files/board.fit.rpt")==expected["area"]["whole"]["fit_report"]
    out.mkdir(parents=True,exist_ok=False)
    files=set(evidence("trial613-package.json")["inputs"])|{"nes_geometry_sender653.sv"}
    for name in files:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,target)
    def edit(name,fn):
        p=out/name;p.write_text(fn(p.read_text()),newline="\n")
    def loader(s):
        return once(s,"load_address<={2'd0,byte_address[21:2]};chip<=byte_address[1];lane<=byte_address[0];",
          """load_address<={2'd0,byte_address[21:4],loaded_bytes[18]?byte_address[2:1]:byte_address[3:2]};
   chip<=loaded_bytes[18]?byte_address[0]:byte_address[1];
   lane<=loaded_bytes[18]?byte_address[3]:byte_address[0];""")
    edit("nes_rom_loader.sv",loader)
    def reader(s):
        if window:
            s=once(s," output wire rom_ready,"," output reg [15:0] window_word,output wire rom_ready,")
            s=once(s," reg [7:0] data_hold;",""" reg [7:0] data_hold;
 (* preserve *) reg [15:0] window_hold;
 always @(posedge mem_clk)if(capture_low && capture_high)window_hold<=psram_data;
 always @(posedge clk)window_word<=window_hold;""")
            # Keep declarations ahead of the always blocks for Questa.
            block=s[s.index(" always @(posedge mem_clk)if(capture_low"):s.index(" (* altera_attribute",s.index("reg [15:0] window_hold;"))]
            s=s.replace(block,"")
            s=once(s," wire capture_next=",block+" wire capture_next=")
        return s
    edit("nes_rom_physical.sv",reader)
    def logical(s):
        s=once(s," wire raw_check_ready", """ function automatic [21:0] layout(input [21:0] a);
  layout=a[21:17]==5'h10 ? {a[21:4],a[2:0],a[3]}:a;
 endfunction
 function automatic [21:0] native_addr(input [21:0] a);
  native_addr=a[21:17]==5'h10 ? {a[21:4],a[0],a[3:1]}:a;
 endfunction
 wire [21:0] response_pins,check_pins;
 assign rom_response_address=native_addr(response_pins);
 wire raw_check_ready""")
        s=once(s,"wire [21:0] raw_check_address;","wire [21:0] raw_check_address=native_addr(check_pins);")
        return s.replace(".check_address(physical_check_address)",".check_address(layout(physical_check_address))").replace(".check_response_address(raw_check_address)",".check_response_address(check_pins)").replace(".rom_address(rom_address)",".rom_address(layout(rom_address))").replace(".rom_response_address(rom_response_address)",".rom_response_address(response_pins)")
    edit("nes_rom_boot.sv",logical)
    if not window:return
    for n in ("nes_rom_boot.sv","nes_spi_boot.sv"):
        edit(n,lambda s:once(once(s," output wire rom_chr32,"," output wire [15:0] window_word,output wire rom_chr32,") if " output wire rom_chr32," in s else once(s,"module nes_spi_boot(","module nes_spi_boot(output wire [15:0] window_word,"),".rom_data(rom_data),",".rom_data(rom_data),.window_word(window_word),"))
    def live(s):
        s=once(s," assign native_mem_ready=boot_read_ready&&!reset;", """ wire issue659,owned659,select659,fault659;wire [21:0] address659;wire [15:0] word659;wire [7:0] data659;
 wire response659,error659;wire [21:0] reply659;
 assign native_mem_ready=boot_read_ready&&!reset&&!owned659;
 assign native_mem_response=response659&&!owned659;
 assign native_mem_error=error659;assign native_mem_response_address=reply659;
 nes_bg_window659 window659(.clk(clk),.reset(reset),.stop(ext_sink_fault||native_spi_fault||direct_nes_fault204||rom_fault),
  .slot(native_fill_slot),.safe(native_core_safe),.normal_request(native_mem_request||rom_request),
  .mem_ready(boot_read_ready),.mem_response(response659),.mem_error(error659),.mem_response_address(reply659),.mem_word(word659),
  .address(snes_addr),.read_n(read_n),.write_n(write_n),.issue(issue659),.request_address(address659),
  .owned(owned659),.selected(select659),.data(data659),.fault(fault659));""")
        s=once(s,".rom_request(native_mem_request&&!reset),.rom_address(native_mem_address),.rom_ready(boot_read_ready),.rom_response(native_mem_response),.rom_error(native_mem_error),.rom_response_address(native_mem_response_address)",
         ".window_word(word659),.rom_request(!reset&&(issue659 || (!owned659 && native_mem_request))),.rom_address(issue659?address659:native_mem_address),.rom_ready(boot_read_ready),.rom_response(response659),.rom_error(error659),.rom_response_address(reply659)")
        return s.replace("assign out_bus_data=bus_data;","assign out_bus_data=select659?data659:bus_data;").replace("assign out_databus_oe_n=databus_oe_n;","assign out_databus_oe_n=databus_oe_n&&!select659;").replace("assign out_databus_dir=databus_dir;","assign out_databus_dir=databus_dir||select659;").replace("out_native_spi_fault=native_spi_fault||","out_native_spi_fault=fault659||native_spi_fault||")
    edit("nes_live_joint.sv",live)
    if jobs:
        from nes_bg659_jobs import producer
        edit("nes_tile205.sv",producer)
    if client:
        assert jobs
        rom=(client/"sink-program.hex").read_bytes()
        assert len(rom.splitlines())==6144
        (out/"sink-program.hex").write_bytes(rom)
        edit("nes_sink_bus165.sv",lambda s:once(once(once(s,"15'h13c0","15'h17c0"),"[0:5119]","[0:6143]"),"{1'b1,{2{!address_sync[14]}},10'h3ff}","{1'b1,!address_sync[14],1'b1,10'h3ff}"))
        edit("nes_live_joint.sv",lambda s:once(s,".transport_fault(native_spi_fault||ext_sink_fault)",".transport_fault(fault659||native_spi_fault||ext_sink_fault)"))
    shutil.copyfile(Path(__file__).with_name("nes_bg_window659.sv"),out/"nes_bg_window659.sv")
    edit("board.qsf",lambda s:s+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_bg_window659.sv\n')
    edit("board.sdc",lambda s:s+"""
# Held together with the physical read ACK, sampled on the NES clock.
foreach i {0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15} {
 set wsrc [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|window_hold[%d]} $i]]
 set wdst [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|window_word[%d]} $i]]
 set_max_delay 23.808 -from $wsrc -to $wdst
 set_false_path -hold -from $wsrc -to $wdst
}
""")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    p.add_argument("--layout-only",action="store_true");p.add_argument("--jobs",action="store_true");p.add_argument("--client",type=Path);a=p.parse_args();board(a.base,a.out,not a.layout_only,a.jobs,a.client)
