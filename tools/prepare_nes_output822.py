"""Issue completed even-length scroll and padding at the existing BG completion callback."""
from pathlib import Path
from prepare_nes_mask820 import WORK, edit
import shutil
import sys
from prepare_nes_trial816 import fit


def board(temp):
    base=temp/"nes-trial816-board820b"
    dst=temp/"nes-trial816-board822"
    dst.mkdir()
    for name in ("rtl","sys"):
        shutil.copytree(base/name,dst/name)
    for path in base.iterdir():
        if path.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".hex",".tcl"):
            shutil.copyfile(path,dst/path.name)
    source=dst/"nes_source_tile192.sv"
    edit(source,".second_plane(bg_word)",".second_plane(bg_word),.physical_word(arb_response)")
    tile=dst/"nes_tile205.sv"
    edit(tile,"input wire [7:0] second_plane","input wire physical_word,input wire [7:0] second_plane")
    edit(tile," wire lease_ok=", """ // Only a checked physical response carries both data lanes. Capture hits
 // deliver one byte and go through the ordinary lookup again for plane 1.
 reg obj_peer;
 always @(posedge clk)begin
  if(reset||stop)obj_peer<=0;
  else if(state==WAIT)obj_peer<=mem_response && physical_word && kind==1 && plan_short;
  else if(state!=EMIT || out_ready)obj_peer<=0;
 end
 wire lease_ok=""")
    edit(tile,"if(pair_bg && !index[0])","if((pair_bg || (EXTERNAL_PLAN!=0 && obj_peer)) && !index[0])")

if __name__=="__main__":
    if sys.argv[1:]==["output-f"]:
        patch=WORK.parent/"nes-output822"/"patch-f"
        patch.mkdir(exist_ok=False)
        sink=patch/"nes_native_sink165.c"
        shutil.copyfile(patch.parent/"patch-d"/sink.name,sink)
        # Limit the extra prefix to an inherited right page. Do not interleave
        # changed rows with OBJ and delay their contiguous map upload.
        edit(sink,"if(!n || n>239","if(!(n&1) && (!(uint32_t)(map>>32) || p->map_dirty))return true;\n if(!n || n>239")
        # The last cached descriptor is valid only for this generation; test
        # the generation-local valid flag and the single-span length together.
        edit(sink,"!s->obj_next ||\n    !s->plan->bulk[1] ||","!s->plan->bulk_valid || !s->plan->bulk[1] ||")
        sys.exit(0)
    if sys.argv[1:]==["output-e"]:
        patch=WORK.parent/"nes-output822"/"patch-e"
        patch.mkdir(exist_ok=False)
        base=WORK/"link820b/src"
        sink=patch/"nes_native_sink165.c"
        shutil.copyfile(base/sink.name,sink)
        edit(sink,'#include "nes_sink_window184.h"','#pragma GCC optimize ("Oz")\n#include "nes_sink_window184.h"')
        edit(sink," if(!map527(s,p,r->map_upload,false))return false;", """ /* OBJ planning is complete. Count starts of dirty OBJ ranges, independent
  * of the E8/credit state; fragmented uploads retain the empty map queue. */
 unsigned starts=0,previous=0;
 for(unsigned slot=0;slot<128;slot++){
  unsigned bit=(r->dirty[128+slot/8]>>(slot%8))&1;
  starts+=bit & !previous;previous=bit;
 }
 unsigned n=p->hdma_size;
 bool prefix=starts==1 && p->patch_count && !p->scroll_issued && !(n&1) &&
             n<=238 && s->plan && s->plan->bank_history==2;
 if(prefix){
  p->hdma[n++]=0;
  if(!packet(s,2,5,0,p->hdma,n)||!packet_wire(s,5,5,n,zero,2,1121-n))return false;
  p->scroll_issued=true;
 }
 if(!map527(s,p,r->map_upload,false))return false;""")
        edit(sink,"if(s->plan && s->plan->window && (((uint32_t)(r->map_upload","if(!prefix && s->plan && s->plan->window && (((uint32_t)(r->map_upload")
        # Size-only code generation on the diagnostic writer; counter contents and format stay identical.
        for name in ("nes_budget210.c","nes_menu_diagnostic.c"):
            path=patch/name
            path.write_bytes(b'#pragma GCC optimize ("Oz")\n'+(base/name).read_bytes())
        sys.exit(0)
    if sys.argv[1:]==["output-d"]:
        patch=WORK.parent/"nes-output822"/"patch-d"
        patch.mkdir(exist_ok=False)
        sink=patch/"nes_native_sink165.c"
        shutil.copyfile(patch.parent/"patch-b"/sink.name,sink)
        edit(sink,"if(!p->scroll_issued && s->plan && s->plan->window &&","""/* A single published OBJ span can share the final upload. Multiple
  * descriptors need the empty head so inactive-bank DMA gets serviced. */
 uint16_t last_length;
 if(s->plan)memcpy(&last_length,s->plan->bulk+2,2);else last_length=0;
 if(s->plan && s->plan->window && (!p->scroll_issued || !s->obj_next ||
    !s->plan->bulk[1] || s->obj_next*32u!=last_length) &&""")
        edit(sink,'#include "nes_sink_window184.h"','#pragma GCC optimize ("Oz")\n#include "nes_sink_window184.h"')
        sys.exit(0)
    if sys.argv[1:]==["output-c"]:
        patch=WORK.parent/"nes-output822"/"patch-c"
        patch.mkdir(exist_ok=False)
        sink=patch/"nes_native_sink165.c"
        shutil.copyfile(patch.parent/"patch-b"/sink.name,sink)
        edit(sink,"if(!n || n>239","if(!(n&1) && (!map || p->map_dirty))return true;\n if(!n || n>239")
        sys.exit(0)
    if sys.argv[1:]==["output-b"]:
        patch=WORK.parent/"nes-output822"/"patch-b"
        patch.mkdir(exist_ok=False)
        sink=patch/"nes_native_sink165.c"
        shutil.copyfile(patch.parent/"patch"/sink.name,sink)
        edit(sink,"s->plan->bank_history!=2 || s->plan->bulk_pending ||\n    (((uint32_t)(map>>32)&0x7ffffu)==0x7ffffu)","s->plan->bank_history!=2")
        edit(sink,"if(s->plan && s->plan->window && (((uint32_t)(r->map_upload","if(!p->scroll_issued && s->plan && s->plan->window && (((uint32_t)(r->map_upload")
        sys.exit(0)
    if len(sys.argv)>1:
        temp=Path(sys.argv[2])
        if sys.argv[1]=="board":board(temp)
        elif sys.argv[1]=="fit":fit(temp,"822",Path("C:/altera_lite/25.1std/quartus/bin64"))
        else:raise ValueError(sys.argv[1])
        sys.exit(0)
    patch=WORK.parent/"nes-output822"/"patch"
    patch.mkdir(parents=True,exist_ok=False)
    sink=patch/"nes_native_sink165.c"
    shutil.copyfile(WORK/"link820b/src"/sink.name,sink)
    edit(sink,"n>240 || !(n&1)","n>239")
    edit(sink," if(!packet(s,24,5,0,p->hdma,n)", """ /* A terminated scroll table owns the following zero padding byte. Include
  * that byte in the prefix so the fixed-word fill always has even length. */
 if(!(n&1))p->hdma[n++]=0;
 if(!packet(s,24,5,0,p->hdma,n)""")
