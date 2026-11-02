# SPDX-License-Identifier: MIT
"""Issue the first warm BG batch within one or three geometry rows."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(arm, out, rows, keep_run=False):
    assert rows in (1,3)
    assert sha(arm/'obj-nes-100/firmware.stm') == '89815cf842071ab3194beb09e13c4d6241480943673b294c3b6756787e2dba6a'
    out.mkdir(parents=True, exist_ok=False)
    def patch(name, changes):
        s = (arm/name).read_text()
        for old, new in changes:
            s = once(s, old, new)
        (out/name).write_text(s, newline='\n')
    callback = 'bool (*finish_bg_row)(void *);\n bool (*offer_map)'
    arm_row = 'if(q->kind==0)s->resident->finish_bg_row=(ok&&!s->plan.early)?finish_bg549:NULL;'
    row_exit = ' if(resident->finish_bg_row&&!resident->finish_bg_row(resident->ctx))return fail(p,7);'
    planner_edits = []
    if rows==3:
        callback = 'uint8_t first_bg_rows;\n ' + callback
        arm_row = """if(q->kind==0){
   if(!s->resident->finish_bg_row)s->resident->first_bg_rows=3;
   s->resident->finish_bg_row=(ok&&!s->plan.early)?finish_bg549:NULL;
 }"""
        planner_edits.append(('nes_cost474_reused++;continue;', 'nes_cost474_reused++;goto row549_done;'))
        row_exit = """row549_done:
 if(resident->finish_bg_row&&(--resident->first_bg_rows==0||g+1==groups)&&!resident->finish_bg_row(resident->ctx))return fail(p,7);"""
    patch('nes_resident211.h', [('bool (*offer_map)',callback)])
    patch('nes_plan_service200.h', [('bool early,ending;', 'bool defer_first,early,ending;'),
        ('bool nes_plan200_emit', 'bool nes_plan549_first(struct nes_plan200 *);\nbool nes_plan200_emit')])
    plan_edits = [('bool nes_plan200_emit', '''bool nes_plan549_first(struct nes_plan200 *p){
 if(!flush(p))return false;
 p->early=true;return true;
}
bool nes_plan200_emit'''), ('if(!p->early&&q->kind==0){p->early=true;return flush(p);}',
        'if(!p->early&&q->kind==0&&(!p->defer_first||p->count>=4))return nes_plan549_first(p);')]
    if keep_run:
        assert rows==3
        plan_edits.append(('return p->count<15||flush(p);', '''if(p->count<15)return true;
 /* Only compact OBJ records have this fixed stride and sorted slot field.
  * Preserve a long adjacent suffix for the following plan or END. */
 if(p->obj_start==0 && p->bytes==15*8){
  uint8_t *records=p->buffer+4;
  unsigned cut=14;
  while(cut && records[cut*8+3]==records[(cut-1)*8+3]+1)cut--;
  if(cut && cut<=7){
   unsigned keep=15-cut;
   uint8_t saved[4];
   /* The in-place E9 trailer/reply overlaps four bytes of the suffix. */
   memcpy(saved,records+cut*8,sizeof saved);
   p->count=cut;p->bytes=cut*8;
   if(!flush(p))return false;
   memcpy(records+cut*8,saved,sizeof saved);
   memmove(records,records+cut*8,keep*8);
   p->count=keep;p->bytes=keep*8;return true;
  }
 }
 return flush(p);'''))
    patch('nes_plan_service200.c',plan_edits)
    patch('nes_native_runtime165.c', [('static bool resident_plan213', '''static bool finish_bg549(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 s->resident->finish_bg_row=NULL;
 return nes_plan549_first(&s->plan);
}
static bool resident_plan213'''), ('bool ok=nes_plan200_emit(&s->plan,q);', '''s->plan.defer_first=s->resident->displayed;
 bool ok=nes_plan200_emit(&s->plan,q);
 '''+arm_row)])
    planner_edits.append((' } /* compact groups */',row_exit+'\n } /* compact groups */'))
    patch('nes_planner211.c',planner_edits)
    # Reset transient callbacks at the start of every attempted generation.
    patch('nes_resident211.c', [('s->open=true;', 's->finish_bg_row=NULL;s->open=true;')])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--rows',type=int,choices=(1,3),required=True)
    p.add_argument('--keep-run',action='store_true')
    a=p.parse_args()
    prepare(a.arm,a.out,a.rows,a.keep_run)
