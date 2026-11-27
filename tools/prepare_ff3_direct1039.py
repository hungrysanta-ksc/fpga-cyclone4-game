"""Use paused FF3 palette/MMC3 register write ports for checkpoint restores."""
import re
from pathlib import Path


def direct_state(board: Path):
    path = board / "rtl/ppu.sv"
    source = path.read_text()
    start = source.index("module PaletteRam")
    end = source.index("endmodule  // PaletteRam", start)
    pal = source[start:end]
    pal = pal.replace("input         SaveStateBus_rst,", "input         SaveStateBus_rst, SaveStateBus_load,")
    start_regs = pal.index("localparam SAVESTATE_MODULES")
    pal = pal[:start_regs] + pal[pal.index("reg [5:0] palette", start_regs):]
    start_regs = pal.index("assign SaveStateBus_Dout")
    pal = pal[:start_regs] + pal[pal.index("// If 0x0,4,8,C", start_regs):]
    start_regs = pal.index("assign SS_PAL_BACK")
    pal = pal[:start_regs] + """// The core is paused while the checkpoint engine shifts a palette word.
wire state_write = palette_access && SaveStateBus_load;
wire [4:0] write_address = state_write ? palette_address : addr2;
wire [5:0] write_color = state_write ? palette_data : din;
genvar bank, lane;
generate for (bank=0; bank<4; bank=bank+1) begin : word_group
  localparam [63:0] INITIAL_WORD = bank==0 ? SSREG_DEFAULT_PAL0 :
      bank==1 ? SSREG_DEFAULT_PAL1 : bank==2 ? SSREG_DEFAULT_PAL2 : SSREG_DEFAULT_PAL3;
  for (lane=0; lane<8; lane=lane+1) begin : cell_lane
    localparam [4:0] CELL = 4*lane+bank;
    always @(posedge clk) begin
      if (SaveStateBus_rst || (reset && !SaveStateBus_load))
        palette[CELL] <= INITIAL_WORD[8*lane+:6];
      else if (!palette_access && !SaveStateBus_load && ce && corrupting &&
               {addr2[4],raw_addr[3:0]} == CELL)
        palette[CELL] <= dout;
      else if ((state_write || (!SaveStateBus_load && !palette_access && ce && write)) &&
               write_address == CELL)
        palette[CELL] <= write_color;
    end
  end
end endgenerate
assign SaveStateBus_Dout = 0;
assign palette_read = dout;
always @(posedge clk) if (ce && !reset) old_rendering <= rendering;

""" + pal[pal.index("assign native_palette", start_regs):]
    assert "SaveStateBus_rst, SaveStateBus_load" in pal and "SS_PAL_BACK" not in pal
    source = source[:start] + pal + source[end:]
    pal_ports = ("input wire palette_access, input wire [4:0] palette_address, "
                 "input wire [5:0] palette_data, output wire [5:0] palette_read,")
    assert source.count("output wire [191:0] native_palette,") == 2
    assert source.count("PaletteRam palette_ram(") == 1
    source = source.replace("output wire [191:0] native_palette,", pal_ports+"\noutput wire [191:0] native_palette,")
    source = source.replace("PaletteRam palette_ram(", "PaletteRam palette_ram(.palette_access(palette_access),"
                            ".palette_address(palette_address),.palette_data(palette_data),"
                            ".palette_read(palette_read),.SaveStateBus_load(SaveStateBus_load),")
    assert source.count("assign dout = palette[addr3];") == 1
    path.write_text(source.replace("assign dout = palette[addr3];",
                                   "assign dout = palette[palette_access ? palette_address : addr3];"))
    path = board / "rtl/nes.v"
    source = path.read_text()
    assert source.count("PPU ppu(") == 1 and source.count("assign Savestate_RAMReadData = ") == 1
    source = source.replace("PPU ppu(", "wire [5:0] palette_state_q;\nPPU ppu("
                            ".palette_access(Savestate_RAMType == 6),.palette_address(Savestate_RAMAddr[4:0]),"
                            ".palette_data(Savestate_RAMWriteData[5:0]),.palette_read(palette_state_q),")
    path.write_text(source.replace("assign Savestate_RAMReadData = ",
                                   "assign Savestate_RAMReadData = Savestate_RAMType == 6 ? {2'b00,palette_state_q} : "))

    path = board / "cart_nrom.sv"
    source = path.read_text()
    begin = source.index("end else if (SaveStateBus_load) begin")
    end = source.index("end else begin", begin)
    fields = re.findall(r"^\s*([\w\[\]:]+)\s*<= SS_MAP([123])(\[.*?\]);", source[begin:end], re.M)
    assert len(fields) == 39, fields
    groups = {group: [] for group in "123"}
    for name, group, bits in fields:
        # The upstream loader reads these two fields from MAP1 even though
        # the independent save bus puts them in MAP3. Preserve the file ABI.
        if name in {"chr_bank_0_0", "chr_bank_1_0"}:
            group = "3"
        groups[group].append(f"          {name} <= SaveStateBus_Din{bits};")
    writes = ["end else if (SaveStateBus_load) begin",
              "    if (SaveStateBus_wren && !SaveStateBus_rst) case (SaveStateBus_Adr)"]
    for group, body in groups.items():
        writes += [f"      SSREG_INDEX_MAP{group}: begin", *body, "      end"]
    writes += ["      default: ;", "    endcase"]
    # Restore-only fields must go back to power-up values on an aborted load.
    source = source[:begin] + """    {mapper47_multicart,ram6_enabled,ram6_enable,ram6_protect,
     chr_bank_0_0,chr_bank_1_0} <= 0;
""" + "\n".join(writes) + "\n" + source[end:]
    source = source.replace("wire [63:0] SS_MAP1, SS_MAP2, SS_MAP3;", "")
    assert source.count("module MMC3 (") == source.count("MMC3 mapper(") == 1
    source = source.replace("module MMC3 (", "module MMC3 (input wire [2:0] state_lane,")
    source = source.replace("MMC3 mapper(", "MMC3 mapper(.state_lane(Savestate_MAPRAMAddr[2:0]),")
    for i in (1, 2, 3):
        source, count = re.subn(rf"^eReg_SavestateV #\(SSREG_INDEX_MAP{i},.*$",
            f"assign SaveStateBus_wired_or[{i-1}] = SaveStateBus_Adr == SSREG_INDEX_MAP{i} ? "
            f"{{56'd0,SS_MAP{i}_BACK[8*state_lane+:8]}} : 64'd0;",
            source, flags=re.M)
        assert count == 1
    path.write_text(source)
