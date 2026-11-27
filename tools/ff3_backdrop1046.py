"""Carry a proven uniform sprite-only row through the existing normal map and DMA path."""
from prepare_nes_kirby1023 import edit


def patch_board(board):
    # The settled pixel stream includes both edge pixels and the final sprite mux.
    edit(board, 'nes_patch_capture181.sv',
         (' input wire need_patch,', ' input wire [5:0] backdrop,\n output reg non_backdrop,\n input wire need_patch,'),
         (' wire [8:0] x=', ''' always @(posedge clk)begin
  if(reset || release_frame || (ce_after && visible && dot==1))non_backdrop<=0;
  else if(pixel_valid && color!=backdrop)non_backdrop<=1;
 end
 wire [8:0] x='''))
    edit(board,'nes_native_frame201.sv',
         (' nes_patch_capture181 pixels(', ''' wire non_backdrop;
 nes_patch_capture181 pixels(
  .backdrop(palette[5:0]),.non_backdrop(non_backdrop),'''),
         (' nes_native_raster181 raster(', ' nes_native_raster181 raster(\n  .non_backdrop(non_backdrop),'))
    edit(board,'nes_native_raster181.sv',
         (' input wire row_commit,',' input wire non_backdrop,\n input wire row_commit,'),
         ('assign row_needs_patch=row_bad;', "assign row_needs_patch=row_bad || (!line_mask[3] && non_backdrop);"),
         ("row_bad<=((display_mask", "row_bad<=(display_mask!=8'h10 && ((display_mask"),
         ("display_mask[2]!=display_mask[1])) ||","display_mask[2]!=display_mask[1]))) ||"),
         ("display_mask[1]!=normal_mask[1] ||","(display_mask[3] && normal_mask[3] && display_mask[1]!=normal_mask[1]) ||"),
         ('if(row_bad)errors[3]<=1;', 'if(row_needs_patch)errors[3]<=1;'),
         ("3'b0,line_mask[4],1'b1,", "3'b0,line_mask[4] && line_mask[3],line_mask[3],"))


def patch_arm(src):
    edit(src,'nes_planner211.c',
         ('#include "nes_cost471.h"','#include "nes_cost471.h"\n#include "nes_mmc479.h"'),
         ('static unsigned epoch(','''/* Mask zero is emitted only after checking all 256 settled pixels. */
static bool backdrop1046(const struct nes_native165 *s,unsigned y){
 return (uint8_t)(s->raster[y]>>36)==0 && !patched(s,y);
}
static unsigned epoch('''),
         ('while(first_normal<224&&patched(s,first_normal))','while(first_normal<224&&(patched(s,first_normal)||backdrop1046(s,first_normal)))'),
         ('if(first_normal==224)return fail(p,15);\n p->display_mask=layer_class820(s->raster[first_normal]);',
          'p->display_mask=first_normal==224?0x1e:layer_class820(s->raster[first_normal]);'),
         ('unsigned raw_count=0;', 'unsigned raw_count=0;bool backdrop_used=false;'),
         ('}else if(s->raster[y]>>49', '''}else if(backdrop1046(s,y)){
   if(nes_board_id!=0x7d||(s->rows[y]>>3)>=s->counts[0]/33||epoch(s,y)>=palettes||s->raster[y]>>49)return fail(p,3);
   backdrop_used=true;
  }else if(s->raster[y]>>49'''),
         ('uint8_t first[32],end[32],bank[32];unsigned groups=0;', '''uint8_t first[32],end[32],bank[32];unsigned groups=0;
 /* SNES map row 31, left page. A zero word selects proven transparent tile
  * zero. Clear the inherited row before any map offer can publish it. */
 if(backdrop_used)for(unsigned x=0;x<32;x++)map_word185(p,2*(31*32+x),0);'''),
         ('unsigned g=s->rows[y]>>3,fy=', '''if(backdrop1046(s,y)){
   p->hofs[y]=0;p->vofs[y]=(uint16_t)((31*8-1-(int)(y&~7u))&1023);continue;
  }
  unsigned g=s->rows[y]>>3,fy='''),
         ('bool split=y==0||fy==0||(y&&patched(s,y-1));', 'bool split=y==0||fy==0||patched(s,y-1)||backdrop1046(s,y-1);'),
         ('if(y&&!patched(s,y-1))split=', 'if(!split)split='),
         ('if(groups==32)return fail(p,5);', 'if(groups==32u-backdrop_used)return fail(p,5);'))
