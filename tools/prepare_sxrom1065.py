"""Generate the SXROM memory variant from the fitted 256 KiB MMC1 source."""
from shutil import copytree
from prepare_nes_headers1064 import ROOT, OUT as PREVIOUS

OUT = PREVIOUS.parent / "nes-mmc1-1065"
BOARD = OUT / "board-sxrom"

def replace(file, *changes):
    path = BOARD/file
    data = path.read_text()
    for before,after in changes:
        if data.count(before)!=1:
            raise ValueError((file,before,data.count(before)))
        data=data.replace(before,after)
    path.write_text(data)

def prepare():
    copytree(PREVIOUS/"board-1",BOARD,dirs_exist_ok=True)
    replace("cart_nrom.sv",("assign prg_aout=", """wire [18:0] sx_prg;
wire [14:0] sx_ram;
// Saved state exposes the same live mapper registers used by CHR decode.
nes_sxrom_address1065 pins(mapper_state[4],chr_ain_orig[12],mapper_state[9:5],
 mapper_state[14:10],prg,prg_ain[12:0],sx_prg,sx_ram);
assign prg_aout="""),("25'h3c0000 | prg_ain[12:0]","25'h3c0000 | sx_ram"),("{7'd0,prg}","{6'd0,sx_prg}"))
    for f in ("nes_source_epoch207.sv","nes_rom_loader.sv","nes_rom_boot.sv","nes_rom_service.sv"):
        path=BOARD/f
        data=path.read_text()
        assert "h40000" in data
        path.write_text(data.replace("h40000","h80000"))
    replace("nes_rom_loader.sv",("12'h3ff","12'h7ff"))
    spi=BOARD/"nes_rom_spi.sv"
    text=spi.read_text()
    assert text.count("snapshot<={8'h85")==2
    spi.write_text(text.replace("snapshot<={8'h85","snapshot<={8'h86"))
    replace("nes_probe.sv",("21'h03ffff","21'h07ffff"))
    replace("nes_checkpoint_spi.sv",("[12:0] bat_addr","[14:0] bat_addr"),("WORDS=2658","WORDS=5730"),
      ("{4'd0,stream_addr[12:1]}","{3'd0,stream_addr[13:1]}"),("{3'b0,bat_addr}","{1'b0,bat_addr}"),
      ("index<8192","index<32768"),("bat_addr<=index[12:0]","bat_addr<=index[14:0]"))
    walk=BOARD/"rtl/savestates.vhd"
    data=walk.read_text().replace("unsigned(11 downto 0)","unsigned(12 downto 0)").replace("to_unsigned(1,12)","to_unsigned(1,13)")
    walk.write_text(data)
    replace("rtl/savestates.vhd",("2657);","5729);"),("000014C400000000","00002CC400000000"),
      ("word_index(11 downto 2)=to_unsigned(2,10)","word_index(12 downto 2)=to_unsigned(2,11)"),
      ("to_unsigned(last_word(region),12)","to_unsigned(last_word(region),13)"),
      ("to_unsigned(savestate_address/8192,13)","to_unsigned(savestate_address/16384,12)"),
      ("Save_RAMAddr <= std_logic_vector", """Save_RAMAddr <= std_logic_vector(to_unsigned(16#3c0000#/32768,10)) &
                   std_logic_vector(resize(word_index-to_unsigned(1634,13),12)) & std_logic_vector(subaddr(2 downto 0)) when region=5 else
                   std_logic_vector"""))
    # External SRAM owns battery storage. The freed M9Ks hold the immutable
    # CHR snapshot; the live PPU, generation ledger and read protocol stay intact.
    replace("nes_checkpoint_memory.sv",
      ("input wire clk, reset, paused,", """input wire clk, reset, paused,
 output wire [18:0] sx_addr, output wire sx_oe,sx_we,inout wire [7:0] sx_data,"""),
      ("state_address[24:13]==12'h1e0","state_address[24:15]==10'h078"),
      ("cpumem_addr[24:13]==12'h1e0","cpumem_addr[24:15]==10'h078"),
      (" reg [12:0] scrub;"," wire sx_cleared;\n reg [12:0] scrub;"),
      ("if(&scrub) init_done<=1;","if(&scrub) init_done<=sx_cleared;"),
      ("end else if(i!=CHR) begin: local_ram", """end else if(i==PRG) begin: battery
     wire [14:0] sx_address=paused ? state_address[14:0] : cpumem_addr[14:0];
     wire sx_write=init_done && ((service && state_write) || (!paused && live_sel[PRG] && cpumem_write));
     nes_sxrom_sram1065 ram(clk,reset,sx_write,sx_address,cpu_data,q[i],sx_cleared,sx_addr,sx_oe,sx_we,sx_data);
   end else if(i!=CHR) begin: local_ram"""))
    replace("nes_live_joint.sv",("[12:0] bat_addr","[14:0] bat_addr"),
      ("{12'h1e0,bat_addr}","{10'h078,bat_addr}"),
      ("(bat_read||bat_write)?","(bat_read||bat_write||bat_pending)?"),
      ("local_memory(.chr_scan_address","local_memory(.sx_addr(RAM_ADDR),.sx_oe(RAM_OE),.sx_we(RAM_WE),.sx_data(RAM_DATA),.chr_scan_address"),
      ("assign RAM_DATA=sram_drive?sram_data:8'hzz;", """wire [18:0] snapshot_addr;
 wire snapshot_we;
 wire [7:0] snapshot_q;
 nes_local_memory_ram #(.AW(13)) mirror(clk,!snapshot_we,snapshot_addr[12:0],sram_data,snapshot_q);"""),
      (".ram_addr(RAM_ADDR),.oe_n(RAM_OE),.we_n(RAM_WE)",".ram_addr(snapshot_addr),.oe_n(),.we_n(snapshot_we)"),(".ram_q(RAM_DATA)",".ram_q(snapshot_q)"))
    for src, dest in (("nes_sxrom_address1065.sv","cart_nrom.sv"),("nes_sxrom_sram1065.sv","nes_checkpoint_memory.sv")):
        path=BOARD/dest
        path.write_text(path.read_text()+"\n"+(ROOT/"rtl"/src).read_text())
    return BOARD

if __name__=="__main__": prepare()
