"""One confirmed adjacent map at BG completion, before OBJ scratch/calculation."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,shared=False):
    proof=json.loads(Path('analysis/pair683-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==proof['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    changes={}
    def edit(name,fn):
        p=out/'src'/name;p.write_text(fn(p.read_text()),newline='\n');changes[name]=sha(p)
    edit('nes_resident211.h',lambda s:once(s,'bool (*offer_map)(void *);','bool (*offer_map)(void *,bool); /* true: all BG rows are final */'))
    def planner(s):
        # The two calls have different lifetimes. Preserve each row offer's
        # three-final-row limit; only the post-loop call sees the full map.
        s=once(s,'next_offer=g+3;if(!resident->offer_map(resident->ctx))return fail(p,7);',
               'next_offer=g+3;if(!resident->offer_map(resident->ctx,false))return fail(p,7);')
        return once(s,'if(next_offer==3 && resident->offer_map && !resident->offer_map(resident->ctx))return fail(p,7);',
            '''/* No OBJ/raw operation below writes map. A completed offer may only
  * continue the exact683 map prefix; cold and other heads keep old priority. */
 if(resident->offer_map && !resident->offer_map(resident->ctx,next_offer!=3))return fail(p,7);''')
    edit('nes_planner211.c',planner)
    edit('nes_native_runtime165.c',lambda s:once(s,
        '''static bool offer527(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 return nes_sink527_early(&s->sink,s->video,s->resident);
}''',
        '''static bool offer527(void *ctx,bool final){
 struct nes_native_runtime165 *s=ctx;
 if(final)return map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,2);
 return nes_sink527_early(&s->sink,s->video,s->resident);
}'''))
    edit('nes_native_sink165.h',lambda s:once(s,'uint64_t,bool);','uint64_t,unsigned); /* 0: output, 1: row offer, 2: BG complete */'))
    def sink(s):
        s=once(s,'uint64_t mask,bool early){','uint64_t mask,unsigned early){')
        s=once(s,'bool pair=!early && s->map_pair683','bool pair=early!=1 && s->map_pair683')
        s=once(s,'  if(!packet(s,(early||adjacent)?24:2,2,first*64,p->map+first*64,count*64))return false;',
            '''  /* BG complete is a single adjacent packet, never a map drain. */
  if(early==2 && !adjacent)return true;
  if(!packet(s,(early==1||adjacent)?24:2,2,first*64,p->map+first*64,count*64))return false;''')
        return once(s,'s->map_pair683=count==3;','s->map_pair683=early==1 && count==3;')
    edit('nes_native_sink165.c',sink)
    if shared:
        edit('nes_native_runtime165.c',lambda s:once(s,
            ''' if(final)return map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,2);
 return nes_sink527_early(&s->sink,s->video,s->resident);''',
            ' return nes_sink527_early(&s->sink,s->video,s->resident,final);'))
        edit('nes_native_sink165.h',lambda s:once(s,
            'bool nes_sink527_early(struct nes_native_sink165 *,struct nes_native_video165 *,struct nes_resident211 *);',
            'bool nes_sink527_early(struct nes_native_sink165 *,struct nes_native_video165 *,struct nes_resident211 *,bool);'))
        def offer(s):
            a=s.index('bool nes_sink527_early(');b=s.index('static bool __attribute__((noinline)) same635',a)
            return s[:a]+'''bool nes_sink527_early(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r,bool final){
 if(s->map_next>=64)return true;
 if(!final){
  bool ready;
  if(!nes_plan527_map_credit(s->plan,&ready))return false;
  if(!ready){if(!s->map_next)s->map_next=128;return true;}
 }
 return map527(s,p,r->map_stale[r->target]|p->map_dirty,final?2:1);
}
'''+s[b:]
        edit('nes_native_sink165.c',offer)
    (out/'recipe684.json').write_text(json.dumps(dict(base=proof['firmware'],changed=changes,
        shared_offer=shared,bound='Exactly one adjacent192B after all BG rows, before OAM clear/OBJ scratch. Existing683 final-output fallback remains.'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--shared',action='store_true');a=p.parse_args();prepare(a.base,a.out,a.shared)
