"""Run actual cartridge CPUs and independently compare the execution after restore."""
from pathlib import Path
import re
import subprocess
import tempfile
import zlib
from prepare_cart_state1059 import OUT
from prepare_nes_carts1056 import ROOT
from check_ff3_checkpoint_rtl import BIN


def run(m, castle_slot=None):
    board=OUT/f"board-{m}"
    names={5:"Dragon Quest IV (K1.2)",7:"Battletoads v1.0 (K)",21:"WaiwaiWorld 2 (K)"}
    raw=(Path.home()/"Downloads/test"/(names[m]+".nes")).read_bytes()
    assert zlib.crc32(raw)=={5:0x9ac62bb9,7:0xca40be7e,21:0x20f150ff}[m]
    prg_bytes=16384*raw[4]
    words=2785 if m==5 else 2658
    original=(ROOT/"tests/nes-functional/ff3_checkpoint_tb.sv").read_text()
    tb=original[:original.index(" wire [191:0] live_mapper")]+original[original.index(" // File indices"):original.index(" task automatic battery_byte")]
    tb+=original[original.index(" task automatic check_resumed_cpu"):original.index(" reg [5:0] reference_pixels")]
    tb=tb.replace("0:524287",f"0:{prg_bytes-1}").replace("WORDS=2658",f"WORDS={words}").replace("ca[18:0]",f"ca[{prg_bytes.bit_length()-2}:0]")
    if m==21:
        tb=tb.replace("reg [7:0] prg[","reg [7:0] pattern[0:131071]; reg [7:0] prg[").replace(".external_ppu_data(8'hff)",".external_ppu_data(pattern[pa[16:0]])").replace(".DEVICE_CHR(USE_M9K)",".CHR_RAM(0)")
    ex="core.core.multi_mapper.cartridge.exram"
    tb+="""
 initial begin
  fd=$fopen("prg.bin","rb");n=$fread(prg,fd);$fclose(fd);if(n!=$size(prg))$fatal;
  @INIT@
  repeat(8)@(negedge clk);reset=0;wait(init_done);
  repeat(300000)@(negedge clk);
  pause_req=1;wait(paused);@(negedge clk);save_req=1;@(negedge clk);save_req=0;
  wait(sleeping);wait(!sleeping);if(saves!=WORDS || checkpoint[0][63:32]!==2*WORDS)$fatal(1,"size");
  @SAVED@
  @(negedge clk);pause_req=0;wait(!paused);check_resumed_cpu(0);
  @(negedge clk);reset=1;repeat(10)@(negedge clk);reset=0;wait(init_done);
  @CLEAR@
  @(negedge clk);pause_req=1;wait(paused);@(negedge clk);load_req=1;
  @(negedge clk);load_req=0;wait(restored);wait(!sleeping);wait(paused);
  if(loads!=WORDS)$fatal(1,"incomplete restore");
  @SAVED@
  @(negedge clk);pause_req=0;wait(!paused);check_resumed_cpu(1);
  $display("PASS cartridge CPU resume 64 fetches and %0d words",WORDS);$finish;
 end
 initial begin repeat(8000000)@(posedge clk);$fatal(1,"timeout");end
endmodule
"""
    tb=tb.replace("@INIT@",f"for(int i=0;i<1024;i++){ex}[i]=8'(i*19^(i>>8));" if m==5 else 'fd=$fopen("chr.bin","rb");n=$fread(pattern,fd);$fclose(fd);' if m==21 else "")
    tb=tb.replace("@SAVED@",f"for(int i=0;i<1024;i++)if($isunknown({ex}[i]) || {ex}[i]!==checkpoint[97+i/8][8*(i%8)+:8])$fatal(1,\"exram %0d\",i);" if m==5 else "").replace("@CLEAR@",f"for(int i=0;i<1024;i++){ex}[i]=0;" if m==5 else "")
    with tempfile.TemporaryDirectory(prefix="cart-resume-") as tmp:
        tmp=Path(tmp)
        (tmp/"prg.bin").write_bytes(raw[16:16+prg_bytes])
        if m==21:(tmp/"chr.bin").write_bytes(raw[16+prg_bytes:])
        if castle_slot:
            import struct
            from prepare_cart_debug1060 import OUT as output
            raw_slot=castle_slot.read_bytes()
            header=struct.unpack_from('<9I',raw_slot)
            assert header[:6]==(0x5353454e,1,zlib.crc32(raw),prg_bytes,1,8*words)
            assert len(raw_slot)==36+words*8 and header[7:]==(zlib.crc32(raw_slot[36:]),zlib.crc32(raw_slot[:32]))
            (tmp/'physical.hex').write_text(''.join(f'{v:016x}\n' for v, in struct.iter_unpack('<Q',raw_slot[36:])))
            tb=tb.replace(" reg clk=0;", " reg [7:0] inspect_oam=0; reg clk=0;").replace(".native_oam_address(11'd0)", ".native_oam_address(inspect_oam)")
            tb=tb[:tb.index(" initial begin\n  fd=")]+(ROOT/"tests/nes-functional/dq4_castle1060.svh").read_text()+"\nendmodule"
        else: output=OUT
        (tmp/"tb.sv").write_text(tb)
        (tmp/"imports.sv").write_text("import regs_savestates::*;")
        def tool(name,*args):
            p=output/f"resume-{m}-{name}.log"
            with p.open("w") as out:
                result=subprocess.run([BIN/(name+".exe"),*args],cwd=tmp,stdout=out,stderr=subprocess.STDOUT,timeout=900)
            log=p.read_text(errors="replace")
            if result.returncode or "** Error" in log or "** Fatal" in log:raise RuntimeError(log[-1500:])
            return log
        tool("vlib","work")
        qsf=(board/"board.qsf").read_text()
        tool("vcom","-2008",*[board/n for n in re.findall(r"^set_global_assignment -name VHDL_FILE (rtl/\S+)",qsf,re.M)])
        files=re.findall(r"^set_global_assignment -name SYSTEMVERILOG_FILE ((?:rtl|sys)/\S+)",qsf,re.M)
        files += ["cart_nrom.sv","nes_probe.sv","nes_local_memory.sv","nes_native_ciram165.sv","nes_checkpoint_memory.sv"]
        if castle_slot:
            files += ["nes_native_compact181.sv","nes_native_planes165.sv","nes_native_raster181.sv","nes_patch_capture181.sv","nes_patch_rows181.sv","nes_native_frame201.sv"]
        tool("vlog","-mfcu","-sv","+define+FF3_FITTED",board/files[0],"imports.sv",*[board/n for n in files[1:]],"tb.sv")
        expected="# PASS castle" if castle_slot else "# PASS cartridge CPU resume"
        assert expected in tool("vsim","-c","-L","altera_mf_ver","-suppress","3009","ff3_checkpoint_tb",*(["+walk_down"] if castle_slot else []),"-do","onerror {quit -code 1}; run -all; quit -f")


if __name__=="__main__":
    import sys
    for mapper in sys.argv[1:]:run(int(mapper))
