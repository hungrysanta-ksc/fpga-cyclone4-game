"""Build the FF3 display profile with grayscale palette capture and immutable-CHR receipts."""
from pathlib import Path
import argparse
from prepare_ff3_1046 import board as board1046, arm as arm1046
from prepare_nes_kirby1023 import edit


def board(out,client):
    board1046(out,client)
    edit(out,'nes_native_raster181.sv',
        ('reg [4:0] copy_offset;', 'reg copy_gray;reg [4:0] copy_offset;'),
        ('line_palette!=held_palette;', 'line_palette!=held_palette || copy_gray!=line_mask[0];'),
        ("8'he9","8'he8"),
        ('palette[5:0]!=held_palette[5:0]',
         "(palette[5:0] & (display_mask[0]?6'h30:6'h3f))!=(held_palette[5:0] & (copy_gray?6'h30:6'h3f))"),
        ('copy_offset<=0;copy_bank<=0;', 'copy_gray<=0;copy_offset<=0;copy_bank<=0;'),
        ("{2'b0,copy_color}","{2'b0,copy_color[5:4],copy_gray?4'd0:copy_color[3:0]}"),
        ('held_palette<=line_palette;copy_bank<=', 'copy_gray<=line_mask[0];held_palette<=line_palette;copy_bank<='))
    edit(out,'nes_chr_snapshot.sv',
        ('output wire can_start,','output reg frame_unchanged, output wire can_start,'),
        (' reg [12:0] bus_addr;',""" // Only retirement of this snapshot can retire earlier writes. Writes after
 // its capture, including the retirement edge, belong to the next image.
 reg modified,after_capture;
 always @(posedge clk)begin
  if(reset)begin modified<=1;after_capture<=1;frame_unchanged<=0;end
  else begin
   if(changed)modified<=1;
   else if(held && retire && retire_gen==owner && !discard)modified<=after_capture;
   if(start && can_start)begin frame_unchanged<=!modified;after_capture<=0;end
   else if(changed)after_capture<=1;
  end
 end
 reg [12:0] bus_addr;"""))
    edit(out,'nes_live_joint.sv',
        (' nes_chr_snapshot snapshot(', ' wire chr_unchanged;\n nes_chr_snapshot snapshot(.frame_unchanged(chr_unchanged),'),
        (' native_export(\n',' native_export(\n .chr_unchanged(chr_unchanged),'))
    edit(out,'nes_native_export203.sv',
        (' input wire [2:0] patch_count,',' input wire chr_unchanged,input wire [2:0] patch_count,'),
        ("exceptions,9'd0,patches","exceptions,8'd0,chr_unchanged,patches"))


def arm(out):
    arm1046(out)
    src=out/'src'
    edit(src,'nes_native165.h',('bool token_valid;', 'bool chr_unchanged,token_valid;'))
    edit(src,'nes_native165.c',
         ('#include "nes_frame900.h"', '#include "nes_frame900.h"\n#include "nes_mmc479.h"'),
         ('(v&4088)', '(v&(nes_board_id==0x7d?4080:4088))'),
         ('s->patch_count=(uint8_t)(v&7);','s->chr_unchanged=(v&8)!=0;s->patch_count=(uint8_t)(v&7);'))
    # The commit path sets resident bits only for completed destination tiles.
    # A write can affect both alternating banks, even if one was not displayed.
    edit(src,'nes_resident211.c',('if(nes_board_id==0x7d) memset(s->resident[s->target],0,sizeof s->resident[s->target]);','if(content==2)memset(s->resident,0,sizeof s->resident);'),
         ('bool immutable,','unsigned content,'),('if(!immutable||','if(!content||'))
    edit(src,'nes_resident211.h',('struct nes_resident211 *,uint32_t,bool,uint16_t,','struct nes_resident211 *,uint32_t,unsigned,uint16_t,'))
    edit(src,'nes_native_runtime165.c',('#include "nes_frame900.h"','#include "nes_frame900.h"\n#include "nes_mmc479.h"'),
         ('s->content_epoch,true,r->generation','s->content_epoch,(nes_board_id==0x7d&&!r->chr_unchanged)?2u:1u,r->generation'),
         # Only CHR residency changes. Preserve 1046's CHR-RAM ordering rather
         # than enabling the CHR-ROM bulk prefetch and early output policies.
         ('1+(s->resident->resident[s->resident->target][0]&1)',
          '1+(nes_board_id!=0x7d && (s->resident->resident[s->resident->target][0]&1))'))
    for name in ('nes_checkpoint112.c','nes_menu_diagnostic.c'):
        p=src/name
        s=p.read_text()
        assert 'ff31046' in s
        p.write_text(s.replace('ff31046','ff31047'))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out',type=Path);ap.add_argument('--client',type=Path)
    a=ap.parse_args()
    if a.client:board(a.out,a.client)
    else:arm(a.out)
