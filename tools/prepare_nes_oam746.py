# SPDX-License-Identifier: MIT
"""Stage the reused OAM payload while waiting on the latest map watermark."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_bg745 import prepare as prepare745


def prepare(base, out, *, split=False):
    prepare745(base, out, service=True)
    def source(name):
        return (out/name if (out/name).exists() else base/'src'/name).read_text()
    def write(name, text):
        (out/name).write_text(text, encoding='utf8', newline='\n')
    header='nes_sink_window184.h'
    s=once(source(header),'struct nes_sink_window184 {','''struct nes_oam746 {
 uint8_t payload[116];
 const uint8_t *source;
 uint32_t serial;
};
void nes_oam746_prepare(struct nes_oam746 *);
struct nes_sink_window184 {''')
    write(header,once(s,' uint8_t status_flags,ack_status;',
                       ' uint8_t status_flags,ack_status;\n struct nes_oam746 *pending_oam;'))
    name='nes_sink_window184.c'
    s=once(source(name),'static bool fail(','''void nes_oam746_prepare(struct nes_oam746 *o){
 if(!o->source)return;
 memcpy(o->payload,o->source,112);
 memcpy(o->payload+112,&o->serial,4);
 o->source=NULL;
}
static bool fail(''')
    write(name,once(s,'  if(!wait474(s,s->last[0]==3?2:1,s->retired!=before))',
                    '''  /* status has passed CRC and counter checks; the latest map is
   * still pending. No input transaction, retirement or publication here. */
  if(s->pending_oam && s->last[1]==2 && target==s->sent)
   nes_oam746_prepare(s->pending_oam);
  if(!wait474(s,s->last[0]==3?2:1,s->retired!=before))'''))
    name='nes_native_sink165.c'
    s=once(source(name),' put16(b+12,n);if(n && data)', ''' /* A ready credit (or no window) takes the same synchronous fallback. */
 if(op==9)nes_oam746_prepare((struct nes_oam746 *)data);
 put16(b+12,n);if(n && data)''')
    old=s[s.index(' uint8_t cmd[116];'):s.index('\n}',s.index(' uint8_t cmd[116];'))]
    write(name,once(s,old,''' struct nes_oam746 job;
 job.source=p->oam;job.serial=s->ack635[bank];
 struct nes_sink_window184 *w=s->plan?s->plan->window:NULL;
 if(w)w->pending_oam=&job;
 bool ok=packet_wire(s,9,4,0,job.payload,sizeof job.payload,0);
 if(w)w->pending_oam=NULL;
 return ok;'''))

    if split:
        s=once(source(header),' uint32_t serial;', ' uint32_t serial;\n uint8_t prepared;')
        write(header,s)
        s=once(source(name),'job.source=p->oam;', 'job.prepared=0;job.source=p->oam;')
        write(name,s)
        name='nes_sink_window184.c'
        s=source(name)
        at=s.index('void nes_oam746_prepare(')
        end=s.index('static bool fail(',at)
        s=s[:at]+'''static void oam_chunk746(struct nes_oam746 *o){
 unsigned at=o->prepared;
 memcpy(o->payload+at,o->source+at,56);
 o->prepared=(uint8_t)(at+56);
 if(at){
  memcpy(o->payload+112,&o->serial,4);
  o->source=NULL;
 }
}
void nes_oam746_prepare(struct nes_oam746 *o){
 while(o->source)oam_chunk746(o);
}
'''+s[end:]
        s=once(s,'if(s->pending_oam && s->last[1]==2 && target==s->sent)\n   nes_oam746_prepare(s->pending_oam);',
                '''if(s->pending_oam && s->pending_oam->source && s->last[1]==2 && target==s->sent){
   oam_chunk746(s->pending_oam);
   if(!s->guard(s->ctx))return fail(s,2);
   continue;
  }''')
        write(name,s)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('base','out'):p.add_argument(key,type=Path)
    p.add_argument('--split',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,split=a.split)
