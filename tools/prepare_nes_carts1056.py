"""Generate one cartridge wiring per board, using the 1054 dual-mode loaders."""
from pathlib import Path
import argparse
import shutil

from prepare_nes_kirby1023 import edit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "probes/nes-carts1056"
# mapper: (board identity, PRG KiB, CHR-ROM KiB)
CARTS = {3:(0x81,32,32), 7:(0x82,512,0), 21:(0x83,256,128), 5:(0x84,1024,0)}

def exrom(dest):
    # 20 address bits span the ROM, but the one-past-end count needs 21.
    # The SPI ABI already carries three count bytes.
    for name in ("nes_spi_boot","nes_rom_boot","nes_live_joint","nes_rom_loader",
                 "nes_source_epoch207","nes_rom_spi"):
        f=dest/(name+".sv")
        text=f.read_text()
        for signal in ("loaded_bytes","out_loaded_bytes","check_address","check_response_address",
                       "check_next","check_request_tag","total"):
            text=text.replace("[19:0] "+signal,"[20:0] "+signal)
        text=text.replace("20'h100000","21'h100000")
        f.write_text(text)
    edit(dest,"nes_rom_spi.sv",("4'd0,check_next","3'd0,check_next"),
         ("4'd0,loaded_bytes","3'd0,loaded_bytes"),("loaded_bytes[19:12]","loaded_bytes[20:12]"),
         ("check_next[19]<=", "check_next[20]<=check_next[20] ^ (next_carry8 && (&check_next[19:8]));\n        check_next[19]<="))
    edit(dest,"nes_rom_loader.sv",("loaded_bytes[19]?22'h200000+{3'd0,loaded_bytes[18:0]}:{2'd0,loaded_bytes}","{2'd0,loaded_bytes[19:0]}"),
         ("loaded_bytes[19]?byte_address[2:1]:byte_address[3:2]","byte_address[3:2]"),
         ("loaded_bytes[19]?byte_address[0]:byte_address[1]","byte_address[1]"),
         ("loaded_bytes[19]?byte_address[3]:byte_address[0]","byte_address[0]"),
         ("loaded_bytes[19]<=","loaded_bytes[20]<=loaded_bytes[20] ^ (low_full && (&loaded_bytes[19:8]));\n    loaded_bytes[19]<="),
         ("loaded_bytes[19:8]==12'h7ff","loaded_bytes[19:8]==12'hfff"))
    edit(dest,"nes_rom_boot.sv",("check_address[19] ?\n     {1'b1,2'b0,check_address[18:0]} : {2'b0,check_address}","{1'b0,check_address}"),
         ("{raw_check_address[21],raw_check_address[18:0]}","raw_check_address[20:0]"))
    f=dest/"nes_rom_service.sv"
    f.write_text(f.read_text().replace("[18:0]","[19:0]").replace("[18:3]","[19:3]")
                 .replace("[15:0] cpu_line_tag","[16:0] cpu_line_tag").replace(",2'b00,",",1'b0,")
                 .replace("next_ppu ? {1'b0,","next_ppu ? {2'b00,"))
    edit(dest,"nes_plan_batch206.sv",('ramstyle="M9K, no_rw_check" *) reg [13:0] alternate','ramstyle="logic" *) reg [13:0] alternate'))
    # Bit 19 shares the same held address, req/ack synchronizers and capture
    # edge as bit 18. Constrain it at the exact new endpoints.
    sdc=dest/"cdc576.sdc"
    lines=[s for s in sdc.read_text().splitlines() if "|address_hold[18]}" in s and "|check_response_address[18]}" in s]
    assert len(lines)==2
    with sdc.open("a") as f:
        for line in lines:f.write("\n"+line.replace("[18]","[19]")+"\n")

def board(mapper):
    identity, prg, chr_rom = CARTS[mapper]
    kind = "rom" if chr_rom else "ram"
    base = OUT.parent / "nes-pair1054" / ("board-" + kind)
    dest = OUT / f"board-{mapper}"
    shutil.copytree(base,dest,dirs_exist_ok=True)
    prg_bytes = prg * 1024
    total = (prg + chr_rom) * 1024
    length = f"20'h{total:05x}"
    old_length = "20'hc0000" if chr_rom else "20'h80000"
    cart = (dest/"cart_nrom.sv").read_text().split("wire [18:0] game148_chr_offset;")[0]
    assert cart.rstrip().endswith(");")
    vrc = mapper == 21
    cart += f"""
wire [19:0] prg;
wire [17:0] chr, prediction;
nes_cart1056 #(.MAPPER({mapper})) cartridge(
 .clk(clk),.reset(reset),.ce(ce),.write_cpu(prg_write),.preview_write(game158_preview_write),
 .cpu(prg_ain),.data(prg_din),.ppu(chr_ain_orig),.lookahead(game148_hint_logic),
 .prg(prg),.chr(chr),.predicted_chr(prediction),.nt_page(vram_a10),.irq(irq));
wire work_ram=1'b{int(vrc)} && prg_ain[15:13]==3'b011;
assign prg_aout=prg_ain<16'h2000 ? (25'h380000 | prg_ain[10:0]) :
                work_ram ? (25'h3c0000 | prg_ain[12:0]) :
                prg_ain[15] ? {{5'd0,prg}} : 25'h3fffff;
assign prg_allow=prg_ain<16'h2000 || work_ram || (prg_ain[15] && !prg_write);
assign vram_ce=chr_ain_orig[13];
assign chr_aout=vram_ce ? {{11'h740,vram_a10,chr_ain_orig[9:0]}} : (22'h200000 | chr);
assign game148_hint_physical=22'h200000 | prediction;
assign chr_allow=1'b{int(not chr_rom)};
assign prg_dout=prg_ain[15:8];
assign chr_dout=8'hff;
assign audio=audio_in;
assign {{prg_bus_write,prg_conflict,has_savestate,prg_conflict_d0,has_flashsaves,
 has_chr_dout,mapper_addr,mapper_data_out,mapper_prg_write,mapper_ovr,diskside,
 SaveStateBus_Dout,Savestate_MAPRAMReadData}}='0;
endmodule
"""
    module="nes_cart1056"
    if mapper==5:
        a=cart.index("nes_cart1056 #")
        b=cart.index("assign prg_aout",a)
        cart=cart[:a]+"""wire work_ram,ram_writable;
nes_exrom1056 cartridge(.clk(clk),.reset(reset),.ce(ce),.wr(prg_write),
 .cpu(prg_ain),.data(prg_din),.ppu(chr_ain_orig),.prg(prg),.ram_selected(work_ram),
 .ram_writable(ram_writable),.nt_page(vram_a10),.mapper_data(prg_dout));
assign chr={5'd0,chr_ain_orig[12:0]};
assign prediction={5'd0,game148_hint_logic[12:0]};
assign irq=0;
"""+cart[b:]
        cart=cart.replace("assign prg_dout=prg_ain[15:8];","assign prg_bus_write=prg_ain[15:10]==6'h17 || prg_ain==16'h5204;").replace("{prg_bus_write,prg_conflict","{prg_conflict").replace("|| work_ram ||","|| (work_ram && (!prg_write || ram_writable)) ||").replace("(prg_ain[15] && !prg_write)","(prg_ain[15] && !work_ram && !prg_write)")
        module="nes_exrom1056"
    (dest/"cart_nrom.sv").write_text(cart+(ROOT/("rtl/"+module+".sv")).read_text())
    edit(dest,"nes_probe.sv",("64'd4" if chr_rom else "64'h8004",f"64'h{mapper|(0 if chr_rom else 0x8000):04x}"),
         ("21'h07ffff",f"21'h{prg_bytes-1:06x}"))
    change={3:"prg_addr[15]",7:"prg_addr[15]",21:"(prg_addr[15:12]==9 || (prg_addr[15:12]>=11 && prg_addr[15:12]<=14))",5:"prg_addr==16'h5105"}[mapper]
    edit(dest/"rtl","nes.v",("(prg_addr[15:13]==3'b100 || prg_addr[15:13]==3'b101)",change))
    edit(dest,"nes_rom_spi.sv",("8'h7c" if chr_rom else "8'h7d",f"8'h{identity:02x}"),
         ("response_address[18:9]==check_request_tag[18:9]","response_address[19:9]==check_request_tag[19:9]"))
    edit(dest,"nes_source_epoch207.sv",(old_length,length))
    edit(dest,"nes_rom_service.sv",("cpumem_addr<25'h80000",f"cpumem_addr<25'h{prg_bytes:x}"))
    edit(dest,"nes_rom_loader.sv",(old_length,length))
    edit(dest,"nes_rom_boot.sv",(old_length,length))
    if chr_rom:
        cut=prg_bytes.bit_length()-1
        edit(dest,"nes_rom_loader.sv",("loaded_bytes[19]?",f"loaded_bytes[{cut}]?"),
             ("{3'd0,loaded_bytes[18:0]}",f"{{{22-cut}'d0,loaded_bytes[{cut-1}:0]}}"))
        edit(dest,"nes_rom_boot.sv",("check_address[19] ?",f"check_address[{cut}] ?"),
             ("{1'b1,2'b0,check_address[18:0]}",f"(22'h200000 | check_address[{cut-1}:0])"),
             ("{raw_check_address[21],raw_check_address[18:0]}",
              f"(raw_check_address[21] ? 20'h{prg_bytes:x} : 20'd0) | raw_check_address[{cut-1}:0]"))
    if mapper==5:
        exrom(dest)
    if mapper==21:
        # The optional SPI 78 witness is specific to the 15-tile Kirby run.
        # Zero footer means no diagnostic sample. Keep the scheduler's phase
        # clock, all live status, consumer checks and actual display ACK.
        f=dest/"nes_display1010.sv"
        old=f.read_text()
        f.write_text(old[:old.index(" (* altera_attribute")]+"""
 reg [14:0] count;
 reg clear;
 always @(posedge clk) begin
   clear<=reset || !active || cancel;
   count<=clear ? 15'd0 : count+1'b1;
   reply<=8'd0;
 end
 assign offer_phase=count[14];
endmodule
""")
        sdc=dest/"board.sdc"
        lines=sdc.read_text().splitlines(keepends=True)
        assert sum("src1010" in s or "dst1010" in s for s in lines)==4
        sdc.write_text("".join(s for s in lines if "src1010" not in s and "dst1010" not in s))
    return dest

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mapper",type=int,choices=CARTS)
    board(p.parse_args().mapper)
