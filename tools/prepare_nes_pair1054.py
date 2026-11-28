"""Prepare both retail FPGA profiles for the one-pass PSRAM loader."""
from pathlib import Path
import argparse
import shutil
from prepare_nes_kirby1023 import edit

ROOT=Path(__file__).resolve().parents[1]
PROBES=ROOT.parent/'probes'
WORK=PROBES/'nes-pair1054'
def board(kind):
    src=PROBES/('nes-kirby1035/board-times' if kind=='rom' else 'nes-ff3-1051B/board-d')
    out=WORK/('board-'+kind+'-retail')
    shutil.copytree(src,out)
    edit(out,'nes_rom_spi.sv',
         ('(command==8\'h60)?arg!=2', "(command==8'h60)?(arg!=3)"),
         (' || command_finish;', ' || command_finish || (pending && pending_command==2 && load_chr32);'))
    # The retail image rejects diagnostic BEGIN and DATA. In this image
    # arg 3 adopts PSRAM written by the MCU while the menu mapper owned it.
    # Both supported cartridge profiles have fixed geometry.
    edit(out,'nes_rom_loader.sv',
         ('chr32<=load_chr32;', "chr32<=1'b0;"))
    edit(out,'nes_rom_spi.sv',
         ("assign static_causes[0]=command<8'h60", "assign static_causes[0]=cmd61 || command<8'h60"))
    p=out/'nes_rom_loader.sv'
    text=p.read_text()
    a=text.index(' wire count_increment_data=')
    p.write_text(text[:a]+""" // The menu mapper writes physical PSRAM. Only a fully staged image can
 // be adopted. STOP in RUN retains the image for a checked state reload.
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin loaded_bytes<=0;count_complete<=0;end
  else if(active_reset || (!fault && count_stop))begin loaded_bytes<=0;count_complete<=0;end
  else if(!fault && count_begin)begin
   loaded_bytes<=load_chr32 ? total : 0; count_complete<=load_chr32;
  end
 end
endmodule
""")

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part',choices=('rom','ram'))
    board(parser.parse_args().part)
