# SPDX-License-Identifier: MIT
"""479 MMC3 live source/tile ROM -> selected ARM C -> RTL -> actual65816.

Host C and transaction RPC are functional adapters, not an M4/IRQ timing model.
ROM and verified loader state are seeded; no physical FPGA/full-loader proof.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from nes_delta231 import ROOT, BASE, sha


def once(s, old, new):
    assert s.count(old) == 1, old[:100]
    return s.replace(old, new)


p = argparse.ArgumentParser(description=__doc__)
for n in ['board', 'arm', 'rom', 'core', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
p.add_argument('--prepare-only', action='store_true')
a = p.parse_args()
assert sha(a.rom) == 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
s = (ROOT/'tools/test_nes_nrom447_run136.py').read_text()
s = once(s, "prod=BASE/'probes/nes-repeat227/arm01/src'", 'prod=Path('+repr(str(a.arm.resolve()))+')')
s = once(s, "cand=prior/'candidate'", 'cand=prod')
s = once(s, 'raw[16:16400]', 'raw[16:0x40010]')
s = once(s, 'raw[16400:]', 'raw[0x40010:]')
s = once(s, "shutil.copyfile(BASE/'probes/nes-nrom407/build04/nes_rom_verify.c',d/'nes_rom_verify.c')", "shutil.copyfile(prod/'nes_rom_verify.c',d/'nes_rom_verify.c')")
s = once(s, "t=(BASE/'probes/nes-nrom407/build04/nes_run136.inc').read_text()", "t=(prod/'nes_run136.inc').read_text()")
s = once(s, "'-Wno-unused-function','host.c'", "'-Wno-unused-function','-DNES_COST471_HOST','host.c','nes_cost471.c'")
s = s.replace("<500,'first packet timeout'", "<1200,'first packet timeout'").replace('child.wait(timeout=600)', 'child.wait(timeout=1200)')
# All protocol/cost-selected includes come from the current ARM tree. The old
# native fixture replaces startup GPIO/program bus orchestration only.
injection = r'''
h=d/'host.c';text=h.read_text()
text=text.replace('qack[12],chr[160]','qack[12]')
text=text.replace('assert(cmd>=0xd0&&cmd<=0xd3);rpc(1,0,tx,n,rx,n);','assert(cmd>=0xd0&&cmd<=0xd3);rpc(1,0,tx,n,rx,n);if(cmd==0xd0&&!(rx[2]&1))rpc(10,0,NULL,0,NULL,0);')
old='assert(argc==3);FILE *f=fopen(argv[2],"rb");assert(f&&fseek(f,16400,SEEK_SET)==0&&fread(chr,1,160,f)==160);fclose(f);'
assert text.count(old)==1;text=text.replace(old,'assert(argc==3);(void)argv;FILE *f;')
assert text.count('rx[1]!=0x78')==1;text=text.replace('rx[1]!=0x78','rx[1]!=0x79')
h.write_text(text)
f=d/'native_fixture.inc';text=f.read_text()
old='uint8_t image[162]={4,0};memcpy(image+2,chr,160);rpc(4,0,image,162,NULL,0);'
assert text.count(old)==1;f.write_text(text.replace(old,'rpc(4,0,NULL,0,NULL,0);'))
model=d/'rom_boot_model.sv';text=model.read_text().replace('65535','262143').replace('32767','131071').replace("24'h10000","24'h40000").replace("24'h208000","24'h220000").replace('a[15:0]','a[17:0]').replace('a[14:0]','a[16:0]').replace('assign #25','assign #70');model.write_text(text)
t=d/'join208_tb.sv';text=t.read_text().replace('ram.prg,0,16383','ram.prg,0,262143').replace('ram.chr,0,8191','ram.chr,0,131071').replace('if(n!=162||','if(n!=0||').replace('#300000000;','#600000000;')
needle='default:$fatal(1,"bridge timeout/command %0d",op);';assert text.count(needle)==1
text=text.replace(needle,'10:begin repeat(65536)@(negedge dut.host_clk);join208_reply(0);end\n    '+needle)
golden=r"""
 // Test-only observation of settled actual NES PPU colors, before conversion.
 // Not consumed by ARM/FPGA/65816 and never changes source state or ACKs.
 reg [5:0] golden[0:57343];reg golden_saved=0;integer golden_file,golden_at;
 always @(posedge dut.core.clk)if(!dut.core_reset)begin
  if(dut.core.native_frame.frame.pixels.pixel_valid)begin
   golden_at=(int'(dut.pixel_line)-8)*256+int'(dut.pixel_cycle)-2;
   if(golden_at<0||golden_at>=57344||$isunknown(dut.pixel_color))$fatal(1,"unknown golden NES pixel");
   golden[golden_at]=dut.pixel_color;
  end
  if(dut.core.native_frame_owned&&dut.core.native_geometry_valid&&!golden_saved)begin
   golden_file=$fopen("NES-first-colors.hex","w");
   for(integer i=0;i<57344;i++)$fwrite(golden_file,"%02x\n",golden[i]);
   $fclose(golden_file);golden_saved=1;
   $display("MMC480 golden generation=%0d",dut.core.native_generation);
  end
 end
"""
text=text.replace('endmodule',golden+'\nendmodule');t.write_text(text)
exe=prior/'client/sink165.sfc' '''
s = once(s, "exe=prior/'client/sink165.sfc'", injection)
# Keep all existing consumer CRC/coverage, actual DMA, VBlank and final ACK
# assertions. Replace the NROM checkerboard-only pixel check after the run.
start = s.index('for y in range(16,224):')
end = s.index("result={'passed':True", start)
s = s[:start] + "assert (d/'NES-first-colors.hex').is_file()\n" + s[end:]
s = once(s, "'geometry_sha256':sha(a.rtl/'nrom429-blocks.txt'),", "'reference_geometry_file_unused_by_live_host':True,'golden_NES_colors_SHA256':sha(d/'NES-first-colors.hex'),")
old_scope = 'actual 227 verified START and run136 orchestration with live board/NES core RTL and 65816 emulator via transaction RPC; native board session setup modeled; seeded PSRAM/verified loader, modeled clocks and no common physical timeline, ARM CPU, or hardware'
s = once(s, repr(old_scope), repr(__doc__))
sys.argv = ['test_nes_nrom447_run136.py', '--board', str(a.board), '--rtl', str(a.core), '--rom', str(a.rom), '--out', str(a.out)]
runner = a.out.parent/(a.out.name+'-runner.py')
assert not runner.exists(), runner
runner.write_text(s, encoding='utf8', newline='\n')
compiled = compile(s, str(runner), 'exec')
if a.prepare_only:
    print('Prepared and syntax checked live runner without starting simulator')
    raise SystemExit(0)
exec(compiled, {'__name__':'__main__', '__file__':str(ROOT/'tools/test_nes_nrom447_run136.py')})
