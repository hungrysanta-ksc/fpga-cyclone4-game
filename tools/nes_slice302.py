# SPDX-License-Identifier: MIT
"""Resume OBJ rank scans without restarting or publishing partial records."""
from nes_wait296 import prepare
from nes_delta231 import once


def native(d):
    prepare(d)
    p=d/'nes_planner211.c';s=p.read_text()
    s=once(s,'static struct context286 ctx286;', 'static struct context286 ctx286;\nstatic unsigned obj_init302,obj_rank302,obj_at302;')
    s=once(s,'rows_reused287=rows_full287=0;', 'obj_init302=obj_rank302=obj_at302=0;rows_reused287=rows_full287=0;')
    s=once(s,' ctx286.phase=0;', ' obj_init302=obj_rank302=obj_at302=0;ctx286.phase=0;')
    a=s.index(' memset(p->oam,0,sizeof(p->oam));');z=s.index(' /* CGRAM becomes',a)
    part=s[a:z]
    part=once(part,' memset(p->oam,0,sizeof(p->oam));', ' if(!obj_init302){\n memset(p->oam,0,sizeof(p->oam));')
    part=once(part,'uint8_t *rank_used=(uint8_t *)p->bg_keys,*evaluation=rank_used+224;', 'uint8_t *rank_used=(uint8_t *)p->bg_keys;')
    part=once(part,' memset(rank_used,0,448);', ' memset(rank_used,0,448);obj_init302=1;return 3;\n }\n uint8_t *rank_used=(uint8_t *)p->bg_keys,*evaluation=rank_used+224;')
    part=once(part,' for(unsigned rank=0;rank<8;rank++)for(unsigned i=0;i<s->counts[2];i++){', ''' unsigned scanned302=0;
 while(obj_rank302<8){
  if(obj_at302==s->counts[2]){obj_at302=0;obj_rank302++;continue;}
  if(scanned302++==16)return 3;
  unsigned rank=obj_rank302,i=obj_at302++;''')
    part=once(part,'\n }\n\n', '\n  return 3; /* One complete fragment, never a half-written OAM/plan. */\n }\n\n')
    s=s[:a]+part+s[z:];p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'extern unsigned service296(void);','extern unsigned service296(void),work_pending302(void);')
    s=once(s,' if(p[0]==0xe2&&!prefill_active287){if(!service296()){plan_error267=5;return 0;}plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;}','')
    s=once(s,' wait_armed284=command==0xe2;', ''' /* Inspect actual progress first; a ready DMA returns to its caller.
  * No recursive SPI inside a planner slice. Only unpublished batch state grows. */
 if(command==0xe2&&!prefill_active287&&work_pending302()){
  if(!service296()){plan_error267=5;return 0;}
  plan_bytes267=output_size285>plan_bytes267?output_size285:plan_bytes267;
 }
 wait_armed284=command==0xe2;''')
    p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned status(unsigned full){', '''static unsigned wait_reason302;
unsigned work_pending302(void){
 if(status259[7]&2)return 0;
 unsigned pending=(uint16_t)(state259.sent-state259.retired);
 return wait_reason302==8?pending>=4:wait_reason302==4?pending!=0:
   (wait_reason302!=0&&!(status259[7]&wait_reason302));
}
static unsigned status(unsigned full,unsigned reason){
 wait_reason302=reason;''')
    s=s.replace('status(1)','status(1,0)')
    s=once(s,'if(!status(0))return 0;if(state259.retired', 'if(!status(0,4))return 0;if(state259.retired')
    s=once(s,'if(!status(0))return 0;}return fail(error);', 'if(!status(0,bit))return 0;}return fail(error);')
    s=once(s,'i==65536||!status(0)', 'i==65536||!status(0,8)')
    assert 'status(0)' not in s
    p.write_text(s,newline='\n')
