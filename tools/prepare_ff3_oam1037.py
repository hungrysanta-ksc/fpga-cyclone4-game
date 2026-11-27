"""Share OAM write ports with the paused checkpoint engine on the FF3 board."""
from pathlib import Path


def share_oam(board: Path, compact=True):
    path = board / "rtl/ppu.sv"
    s = path.read_text()
    a = s.index("// Original048 structural mapping")
    b = s.index("assign native_oam_write=", a)
    template = s[s.index('altsyncram #', a):s.index('genvar rb_main;', a)]
    unit = template[template.rindex("altsyncram #"):]
    assert "primary_run_main_word1" in unit
    parts = ["""// Checkpoint writes occur only after pause + display drain.
wire [63:0] primary_main,primary_copy,primary_extra,primary_repeat,primary_native;
wire [7:0] run_mask=oam_copy_write ? 8'hff :
                       oam_cpu_write ? (8'd1 << oam_read_addr[2:0]) : 8'd0;
wire [7:0] write_mask=Savestate_OAMWrEn ? (8'd1 << Savestate_OAMAddr[2:0]) : run_mask;
wire [4:0] write_row=Savestate_OAMWrEn ? Savestate_OAMAddr[7:3] : oam_write_row;
wire [63:0] write_data=Savestate_OAMWrEn ? {8{Savestate_OAMWriteData}} :
                       oam_copy_write ? primary_copy : {8{is_attr_byte ? (oam_din & 8'he3) : oam_din}};
wire [7:0] native_or_state_addr=Savestate_OAMRdEn ? Savestate_OAMAddr : native_oam_address;
`ifndef SYNTHESIS
always @(posedge clk) if(Savestate_OAMWrEn && |run_mask)
    $fatal(1,"checkpoint collided with active OAM write");
`endif
"""]
    # The PPU fetches the primary OAM byte on even evaluation dots. The
    # repeat check reads its three bytes on odd evaluation dots. Outside
    # rendering the CPU-visible byte always uses oam_read_addr.
    ports = [("main","oam_read_addr[7:3]"), ("copy","oam_row_last"),
             ("extra","oam_addr_ex[5:1]"), ("repeat","oam_addr[7:3]"),
             ("native","native_or_state_addr[7:3]")]
    if compact:
        parts.append("wire [4:0] primary_row=(rendering && secondary_write) ? oam_addr[7:3] : oam_read_addr[7:3];\n"
                     "assign primary_repeat=primary_main;\n")
        ports[0]=("main","primary_row")
        ports.remove(("repeat","oam_addr[7:3]"))
        # The extra sprite address is a PPU register. Sample its 32-bit
        # record on idle master clocks, before the next PPU enable can
        # change it. Rendering-rise copies use the full row at the enable.
        ports.remove(("extra","oam_addr_ex[5:1]"))
        ports[1]=("copy","(ce ? oam_row_last : oam_addr_ex[5:1])")
        parts.append("""reg [31:0] extra_sprite;
always @(posedge clk) if(!ce) extra_sprite<=primary_copy[oam_addr_ex[0]*32+:32];
assign primary_extra={extra_sprite,extra_sprite};
""")

    for name,row in ports:
        for half in range(2):
            parts.append(unit.replace("primary_run_main_word1",f"shared_{name}_{half}")
                         .replace("primary_run_mask","write_mask").replace("oam_write_row","write_row")
                         .replace("primary_run_data","write_data").replace("primary_run_q_main",f"primary_{name}")
                         .replace("oam_read_addr[7:3]",row).replace("32+:32",f"{32*half}+:32")
                         .replace("4+:4",f"{4*half}+:4"))
    parts.append("assign native_oam_data=primary_native[native_oam_address[2:0]*8+:8];\n")
    s = s[:a] + "".join(parts) + s[b:]
    assert s.count("primary_state[Savestate_OAMAddr")==1
    s = s.replace("primary_state[Savestate_OAMAddr", "primary_native[Savestate_OAMAddr")
    if not compact:
        path.write_text(s)
        return
    low_ram = (Path(__file__).resolve().parents[1]/"src/nes/ff3_secondary1042.sv").read_text()
    marker = "wire [7:0] temp_copy_data ="
    assert s.count(marker)==1
    s = s.replace("reg [63:0] temp_valid;", "wire [7:0] secondary_q,copy_q;\nreg [63:0] temp_valid;")
    insert = s.index("genvar temp_index;",s.index(marker))
    s = s[:insert] + low_ram + "\n" + s[insert:]
    s = s.replace("temp_storage[oam_secondary_addr]", "secondary_q")
    s = s.replace("temp_storage[oam_row_last]", "copy_q")
    writes = "  if(load_byte)temp_storage[temp_index]<=oam_dbus;\n  else if(copy_byte)temp_storage[temp_index]<=temp_copy_data;"
    assert s.count(writes)==1
    s=s.replace(writes,"")
    # Keep only the 32 high entries with their original simultaneous extra writes.
    s=s.replace("reg [7:0] temp_storage[0:63]", "reg [7:0] temp_storage[32:63]")
    first=s.index("wire [7:0] oam_temp[0:63];")
    end=s.index("end endgenerate",first)+len("end endgenerate")
    assert s.count("oam_temp[") == 3  # declaration, old observation and reset comment
    path.write_text(s[:first]+s[end:])
