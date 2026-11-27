"""Materialize the 1047 playable board and firmware with page-level CHR receipts."""
import argparse
from pathlib import Path
from prepare_ff3_battle1047 import arm as arm1047, board as board1047
from prepare_nes_kirby1023 import edit

def board(out, client):
    board1047(out, client)
    edit(out, 'nes_chr_snapshot.sv',
         ('output reg frame_unchanged,','output wire frame_unchanged,output reg [7:0] clean_pages,'),
         ('reg modified,after_capture;', '''reg [7:0] modified,after_capture;
 wire [7:0] write_mask=changed ? 8'b1<<changed_page : 8'd0;
 assign frame_unchanged=&clean_pages;'''),
         ('modified<=1;after_capture<=1;frame_unchanged<=0;', "modified<=8'hff;after_capture<=0;clean_pages<=0;"),
         ('if(changed)modified<=1;\n   else if(held && retire && retire_gen==owner && !discard)modified<=after_capture;',
          'if(held && retire && retire_gen==owner && !discard)modified<=after_capture|write_mask;\n   else modified<=modified|write_mask;'),
         ('frame_unchanged<=!modified;', 'clean_pages<=~modified;'),
         ('else if(changed)after_capture<=1;', 'else after_capture<=after_capture|write_mask;'))
    edit(out,'nes_live_joint.sv',
         ('wire chr_unchanged;', 'wire [7:0] clean_pages;wire chr_unchanged;'),
         ('snapshot(.frame_unchanged','snapshot(.clean_pages(clean_pages),.frame_unchanged'),
         ('.chr_unchanged(chr_unchanged), .patch_count','.clean_pages(clean_pages),.chr_unchanged(chr_unchanged), .patch_count'))
    edit(out,'nes_native_export203.sv',
         ('input wire chr_unchanged,','input wire [7:0] clean_pages,input wire chr_unchanged,'),
         ("exceptions,8'd0,chr_unchanged,patches","exceptions,clean_pages,chr_unchanged,patches"))
    # Address and data-in delays share the same external PSRAM access budget.
    # Guide placement of address drivers as well as the existing OE drivers.
    with (out/'board.sdc').open('a') as f:
        f.write('\nset_max_delay 19.5 -from [all_registers] -to [get_ports {ROM_ADDR*}]\n')

def arm(out):
    arm1047(out)
    src=out/'src'
    edit(src,'nes_native165.h',('bool chr_unchanged,token_valid;', 'uint8_t clean_pages;bool token_valid;'))
    edit(src,'nes_native165.c',
         ('(v&(nes_board_id==0x7d?4080:4088))','(nes_board_id!=0x7d && (v&4088))'),
         ('s->chr_unchanged=(v&8)!=0;', 's->clean_pages=(v&8)?255:(uint8_t)(v>>4);'))
    edit(src,'nes_native_runtime165.c',
         ('(nes_board_id==0x7d&&!r->chr_unchanged)?2u:1u',
          'nes_board_id==0x7d ? 1u+((uint8_t)~r->clean_pages) : 1u'))
    edit(src,'nes_resident211.c',
         ('static void rebuild221(struct nes_resident211 *s){','''static void invalidate_page(struct nes_resident211 *s,unsigned id,unsigned key,unsigned changed){
 if(changed & (1u<<((key>>6)&7u))){clear(s->resident[0],id);clear(s->resident[1],id);}
}
static void rebuild221(struct nes_resident211 *s,unsigned changed){'''),
         ('if(s->bg[i]!=UINT16_MAX)insert221(s,i,s->bg[i],false);',
          'if(s->bg[i]!=UINT16_MAX){invalidate_page(s,i,s->bg[i],changed);insert221(s,i,s->bg[i],false);}'),
         ('if(s->obj[i]!=UINT32_MAX)insert221(s,1024+i,s->obj[i],false);',
          'if(s->obj[i]!=UINT32_MAX){invalidate_page(s,1024+i,s->obj[i],changed);insert221(s,1024+i,s->obj[i],false);}'),
         ('if(content==2)memset(s->resident,0,sizeof s->resident);',''),
         ('rebuild221(s);','rebuild221(s,content-1);'))
    edit(src,'nes_planner211.c',
         ('memset(p,0,offsetof(struct nes_native_video165,map));',
          '/* The per-frame used bitmap guards reads of exact keys; each raw output initializes its own storage. */'),
         (' memset(p->oam,0,sizeof(p->oam));',''),
         (' memset(p->cgram,0,sizeof(p->cgram));\n put16(p->cgram,lut[s->palette[0]]);',''),
         ('unsigned next_offer=3;', 'uint32_t bg_lookup[64]={0};\n unsigned next_offer=3;'),
         ('unsigned previous_slot=0,older_slot=0;', ''),
         ('if(x>=2 && !exceptional && ((cell^s->maps[idx-2])&16383)==0){\n   slot=older_slot;',
          '''unsigned tag=cell&16383, cached=bg_lookup[tag&63];
  if(!((exceptional>>x)&1) && (cached>>16)==tag+1){
   slot=(uint16_t)cached;'''),
         ('if(slot>=1024)return fail(p,7);', 'if(slot>=1024)return fail(p,7);\n  if(!((exceptional>>x)&1))bg_lookup[tag&63]=((tag+1)<<16)|slot;'),
         ('older_slot=previous_slot;previous_slot=slot;', ''))
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        file=src/name
        content=file.read_text()
        assert 'ff31047' in content
        file.write_text(content.replace('ff31047','ff31048'))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out',type=Path)
    ap.add_argument('--client',type=Path)
    args=ap.parse_args()
    if args.client:board(args.out,args.client)
    else:arm(args.out)
