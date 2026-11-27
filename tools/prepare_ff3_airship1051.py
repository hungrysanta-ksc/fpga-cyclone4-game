"""Keep the page receipt for scattered CHR writes; qualify a single 128-byte range."""
from pathlib import Path
import argparse
import shutil

from prepare_ff3_1050 import prepare
from prepare_nes_kirby1023 import edit


def build(work):
    prepare(work)
    src=work/'link/src'
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        edit(src,name,('ff31050','ff31051'))
    edit(src,'nes_native165.h',('uint8_t clean_pages;bool token_valid;', 'bool token_valid;uint16_t dirty_chr;'))
    edit(src,'nes_native165.c',
        ('if(s->state!=NES_NATIVE165_IDLE||(v>>48)!=0x2234||(nes_board_id!=0x7d && (v&4088)))return fail(s,2);',
         '''unsigned version=(unsigned)(v>>48)-0x2234, flags=((unsigned)v>>3)&511, dirty=0;
  if(s->state!=NES_NATIVE165_IDLE)return fail(s,2);
  if(nes_board_id==0x7d){
   if(version>1 || (version && (flags&385)))return fail(s,2);
   dirty=version ? 256+(flags>>1) : (flags&1)?0:(255^(flags>>1));
  }else if(version || flags)return fail(s,2);'''),
        ('s->clean_pages=(v&8)?255:(uint8_t)(v>>4);',
         's->dirty_chr=dirty;'))
    edit(src,'nes_native_runtime165.c',
        ('nes_board_id==0x7d ? 1u+((uint8_t)~r->clean_pages) : 1u','1u+r->dirty_chr'))
    # CHR-ROM headers carry zero flags. Their tiles remain immutable.
    edit(src,'nes_resident211.c',
         ('if(changed & (1u<<((key>>6)&7u)))',
          'if(changed>=256 ? ((key>>3)&63u)==changed-256 : (changed & (1u<<((key>>6)&7u))))'))
    board=work/'board'
    shutil.copytree(work.parent/'nes-ff3-1048/board-io',board)
    shutil.copyfile(work/'client/sink-program.hex',board/'sink-program.hex')
    edit(board,'nes_checkpoint_memory.sv',('output wire [2:0] changed_page,','output wire [5:0] changed_group,'),
         ('assign changed_page=ppu_address[12:10];','assign changed_group=ppu_address[12:7];'))
    edit(board,'nes_live_joint.sv',('wire [2:0] changed_page;', 'wire [5:0] changed_group;'),
         ('.changed_page(changed_page)', '.changed_group(changed_group)'),
         ('wire [7:0] clean_pages;', 'wire fine_receipt;wire [7:0] clean_pages;'),
         ('.clean_pages(clean_pages)', '.fine_receipt(fine_receipt),.clean_pages(clean_pages)'))
    edit(board,'nes_chr_snapshot.sv',
         ('input wire [2:0] changed_page,','input wire [5:0] changed_group,output reg fine_receipt,'),
         (' reg [7:0] dirty;', ' wire [2:0] changed_page=changed_group[5:3];\n reg [7:0] dirty;'),
         (' assign frame_unchanged=&clean_pages;', ''' reg [5:0] group_id;
 reg seen,mixed;
 wire narrow=seen && !mixed;
 assign frame_unchanged=&clean_pages;
 // A successful capture starts the next interval. Discard makes its origin
 // uncertain until the next successful capture; the page ledger stays valid.
 always @(posedge clk)begin
  if(reset || discard)begin mixed<=1;seen<=0;end
  else if(start && can_start)begin mixed<=0;seen<=0;end
  else if(changed)begin
   if(seen && group_id!=changed_group)mixed<=1;
   group_id<=changed_group;seen<=1;
  end
 end'''),
         ('after_capture<=0;clean_pages<=0;', 'after_capture<=0;clean_pages<=0;fine_receipt<=0;'),
         ('clean_pages<=~modified;after_capture<=0;', "clean_pages<=narrow?{2'b0,group_id}:~modified;fine_receipt<=narrow;after_capture<=0;"))
    edit(board,'nes_native_export203.sv',('input wire [7:0] clean_pages,','input wire fine_receipt,input wire [7:0] clean_pages,'),
         ("{16'h2234,groups,palettes","{15'h111a,fine_receipt,groups,palettes"))
    pin_clock_guard(board)
    timer_enable(board)


def timer_enable(board):
    # The command checker affects only the timer enable. Keep its path out of
    # the decrement/reload data multiplexer, including sticky fault write drain.
    edit(board,'nes_rom_loader.sv',
         ('reg [CW-1:0] remaining;', '(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION ON; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [CW-1:0] remaining;'),
         ('reg terminal;\n always', '''reg terminal;
 wire timer_enable=active_reset || !timed_phase || phase_step;
 always'''),
         ('else if(active_reset)begin remaining<=0;terminal<=0;end',
          'else if(timer_enable) begin\n  if(active_reset)begin remaining<=0;terminal<=0;end'),
         ('else if(phase_step)begin\n   if(!terminal)', 'else begin\n   if(!terminal)'),
         ('endcase\n  end\n end\n task automatic advance_phase',
          'endcase\n  end\n  end\n end\n task automatic advance_phase'))


def pin_clock_guard(board):
    # Preserve the timing-closed 1048 placement of the permit and its synchronizer.
    prefix='nes_live_joint:core|nes_diag_clock_guard127:clock_guard|'
    with (board/'board.qsf').open('a') as qsf:
        for signal, n in (('ref_qualified',23),('ref_ok_mem[0]',31),('ref_ok_mem[1]',19)):
            qsf.write(f'\nset_location_assignment FF_X3_Y7_N{n} -to {prefix}{signal}\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('work',type=Path)
    build(ap.parse_args().work)
