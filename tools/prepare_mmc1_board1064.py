"""Bind the 256 KiB MMC1 cartridge to the board's M2, CHR and checkpoint ports."""
from shutil import copytree
from prepare_cart_state1059 import OUT as STATE
from prepare_nes_headers1064 import ROOT, OUT
from prepare_nes_kirby1023 import edit

def prepare():
    board=OUT/"board-1"
    copytree(STATE/"board-7",board,dirs_exist_ok=True)
    path=board/"cart_nrom.sv"
    old=path.read_text()
    begin=old.index("wire [7:0] mapper_byte;")
    end=old.index("assign prg_aout=",begin)
    cart=old[:begin]+"""wire [25:0] mapper_state;
wire [31:0] state_padded={6'b0,mapper_state};
wire [7:0] state_byte=Savestate_MAPRAMAddr[2] ? 8'd0 : state_padded[8*Savestate_MAPRAMAddr[1:0]+:8];
assign SaveStateBus_Dout=SaveStateBus_Adr==32 ? {56'd0,state_byte} : 64'd0;
wire [17:0] prg;
wire [12:0] chr, prediction;
wire work_ram;
assign irq=0;
nes_mmc1_1063 cartridge(
 .clk(clk),.reset(reset),.cpu_ce(ce),.cpu_write(prg_write),.preview_write(game158_preview_write),
 .cpu_address(prg_ain),.cpu_data(prg_din),.ppu_address(chr_ain_orig),.lookahead(game148_hint_logic),
 .restore(SaveStateBus_load && SaveStateBus_wren && SaveStateBus_Adr==32),
 .restored_state(SaveStateBus_Din[25:0]),.saved_state(mapper_state),.prg_address(prg),
 .chr_address(chr),.predicted_chr(prediction),.nt_page(vram_a10),.ram_selected(work_ram));
"""+old[end:old.index("endmodule",end)+len("endmodule")].replace("{5'd0,prg}","{7'd0,prg}")
    path.write_text(cart+"\n"+(ROOT/"rtl/nes_mmc1_1063.sv").read_text())
    edit(board,"nes_probe.sv",("64'h8007","64'h8001"),("21'h07ffff","21'h03ffff"))
    for file in ("nes_rom_spi.sv","nes_source_epoch207.sv","nes_rom_loader.sv","nes_rom_boot.sv","nes_rom_service.sv"):
        if file=="nes_rom_spi.sv": edit(board,file,("snapshot<={8'h82","snapshot<={8'h85"))
        else: edit(board,file,("h80000","h40000"))
    edit(board,"nes_rom_loader.sv",("12'h7ff","12'h3ff"))
    return board

if __name__=="__main__":
    prepare()
