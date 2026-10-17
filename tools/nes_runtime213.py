# SPDX-License-Identifier: MIT
"""Bind maintained slots and sparse consumer to the pinned production RUN.
No FPGA change. Output is a build candidate, never a hardware release by itself.
"""
from pathlib import Path
import argparse,json,shutil
from nes_resident211 import ROOT,BASE,sha,once,prepare as planner
from nes_sink212 import prepare as sink
from nes_board181 import copy_pins

def runtime(s):
 s=once(s,' if(!s->result)s->result=(uint8_t)reason;', ' if(!s->result)s->result=(uint8_t)reason;\n if(s->resident)nes_resident211_abort(s->resident);')
 s=once(s,'static bool budget_plan210(void *ctx,const struct nes_plan191 *q){', 'static bool resident_plan213(void *ctx,unsigned bank,const struct nes_plan191 *q){')
 s=once(s,' if(!nes_plan200_emit(&s->plan,q))return false;', ''' if(!s->resident||bank!=s->resident->target||
    (s->resident->displayed&&bank==s->resident->active))return false;
 /* Accepted into the plan queue, not yet written. finish drains every
  * descriptor/END before SEAL can confirm any resident bit. */
 if(!nes_plan200_emit(&s->plan,q))return false;''')
 s=once(s,' void *ctx,uint32_t limit){',' void *ctx,uint32_t limit,struct nes_resident211 *resident,uint32_t epoch,bool immutable){')
 s=once(s,' if(!r||!v||!palette||!fn||!ticks||!service||!limit||limit>=0x80000000u)', ' if(!r||!v||!palette||!fn||!ticks||!service||!limit||limit>=0x80000000u||!resident||!epoch||!immutable)')
 s=once(s,' s->receiver=r;s->video=v;s->palette=palette;', ' s->receiver=r;s->video=v;s->palette=palette;\n s->resident=resident;s->content_epoch=epoch;nes_resident211_reset(resident);')
 s=once(s,'''  if(!guard(s)||!nes_sink165_begin(&s->sink,r->generation)||
     !nes_native_video191_plan(r,s->palette,s->video,s->sink.displayed,budget_plan210,s)||
     !nes_plan200_finish(&s->plan))''', '''  if(!guard(s)||!nes_resident211_begin(s->resident,s->content_epoch,true,r->generation,resident_plan213,s)||
     !nes_sink212_begin(&s->sink,s->resident)||
     !nes_native_video211_plan(r,s->palette,s->video,s->resident)||
     !nes_plan200_finish(&s->plan))''')
 s=once(s,'  if(!nes_sink165_seal(&s->sink,s->video,5000))','  if(!nes_sink212_seal(&s->sink,s->video,s->resident))')
 s=once(s,'  nes_budget210_display(nes_trace166.last_display_tick,s->video);', '''  nes_budget210.bins[nes_budget210.bin][B210_REUSE]+=s->resident->hits;
  nes_budget210_display(nes_trace166.last_display_tick,s->video);''')
 return s

def prepare(out):
 prior=BASE/'probes/nes-budget210/arm03'
 p=json.loads((prior/'preparation-budget210.json').read_bytes());pins=p['copied']|p['changed']|p['added']
 copy_pins(prior,out,pins);src=out/'src'
 planner(out/'planner211');sink(out/'sink212')
 for n in ['nes_planner211.c','nes_resident211.c','nes_resident211.h']:
  shutil.copyfile(out/'planner211'/n,src/n)
 for n in ['nes_native_sink165.c','nes_native_sink165.h','nes_sink_bulk195.inc']:
  shutil.copyfile(out/'sink212'/n,src/n)
 # Queued admission does not assert physical write completion. The runtime
 # joins all admitted plans at finish before the final displayed ACK/commit.
 h=src/'nes_resident211.h';s=h.read_text();s=once(s,' * the write completed; commit requires a separate final visible display ACK.', ' * the write was accepted; caller MUST drain all queued writes before SEAL,\n * and commit requires a separate final visible display ACK.')
 h.write_text(s,encoding='utf8',newline='\n')
 f=src/'nes_native_runtime165.c';f.write_text(runtime(f.read_text()),encoding='utf8',newline='\n')
 f=src/'nes_native_runtime165.h';s=f.read_text();s=once(s,'#include "nes_plan_service200.h"','#include "nes_plan_service200.h"\n#include "nes_resident211.h"')
 s=once(s,' struct nes_plan200 plan;',' struct nes_plan200 plan;\n struct nes_resident211 *resident;uint32_t content_epoch;')
 s=once(s,' void *,uint32_t limit_ticks);', ' void *,uint32_t limit_ticks,struct nes_resident211 *,uint32_t content_epoch,bool immutable);')
 s=once(s,' * The caller owns STOP, reset, logging and menu recovery after any terminal.', ''' * content_epoch is a caller-qualified immutable ROM SESSION identity, not
 * the independent FPGA loader epoch. Never change content within this session.
 * Caller must reset BOTH physical consumer and producer before begin; even an
 * equal identity on a subsequent load starts with empty banks.
 * The caller owns STOP, reset, logging and menu recovery after any terminal.''')
 f.write_text(s,encoding='utf8',newline='\n')
 f=src/'nes_runtime_board165.inc';s=f.read_text()
 s=s.replace('native_session165(const struct nes_rom_spi_io *io)', 'native_session165(const struct nes_rom_spi_io *io,uint32_t content_epoch)')
 s=once(s,'struct nes_budget210_cache budget;', 'struct nes_resident211 resident;')
 s=once(s,'NULL,6000);','NULL,6000,&work.resident,content_epoch,true);')
 s=once(s,' nes_budget210_attach(&work.budget);\n','');s=once(s,' nes_budget210_detach();\n','')
 s=once(s,' native_runtime165.receiver=NULL;', ' native_runtime165.resident=NULL;\n native_runtime165.receiver=NULL;')
 f.write_text(s,encoding='utf8',newline='\n')
 f=src/'nes_run136.inc';s=f.read_text();s=once(s,'uint32_t total,struct nes_mcu_load_report *r) {','uint32_t total,struct nes_mcu_load_report *r,uint32_t content_epoch) {')
 s=once(s,' native_session165(io);',' native_session165(io,content_epoch);');f.write_text(s,encoding='utf8',newline='\n')
 f=src/'nes_h1_stm32.c';s=f.read_text();s=once(s,'if(!run136(&io,total,r))', '''/* Qualified only here: exact SMB3 CHR-ROM header, three file CRC passes,
  * complete physical comparison/FINISH, then checked START. FPGA reconfigured
  * on every session; no loader writes or state loads are allowed during RUN.
  * CRC is session identity, not a substitute for board201's loader lease. */
 if(!run136(&io,total,r,expected_crc))''');f.write_text(s,encoding='utf8',newline='\n')
 f=src/'Makefile';s=f.read_text();s=once(s,'nes_plan191.c nes_plan_service200.c','nes_planner211.c nes_resident211.c nes_plan_service200.c');f.write_text(s,encoding='utf8',newline='\n')
 # Keep useful phase/wire bins; remove passive hypothetical cache and its work.
 f=src/'nes_budget210.c';s=f.read_text();a=s.index('void nes_budget210_plan(');b=s.index('void nes_budget210_display(',a)
 s=s[:a]+'''void nes_budget210_plan(const struct nes_plan191 *q){
 uint32_t *b=nes_budget210.bins[nes_budget210.bin];
 b[B210_PLANS]++;b[B210_OUTPUT]+=q->kind==1?32:16;
}
'''+s[b:]
 s=s.replace('budget_schema=210','budget_schema=213').replace('model=ROM_SESSION_EXACT256_DIRECT_NO_SLOT_PROOF','model=ACTUAL_BANK_RESIDENT_SLOTS_211').replace('reuse,reuseplan,complex','slot_hits,reserved0,reserved1')
 f.write_text(s,encoding='utf8',newline='\n')
 for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  f=src/name;s=f.read_text()
  for a,b in [('NES-GAME-210','NES-GAME-213'),('GAME 210','GAME 213'),('game210.nes','game213.nes'),('fpga_n210.bi3','fpga_n213.bi3'),('last-210.txt','last-213.txt'),('NES210','NES213'),('nes-progress-210.txt','nes-progress-213.txt'),('nes-budget-210.txt','nes-budget-213.txt'),('NES-GAME210-DEV','NES-GAME213-DEV')]:s=s.replace(a,b)
  f.write_text(s,encoding='utf8',newline='\n')
 changed={n:sha(out/n) for n in pins if sha(out/n)!=pins[n]}
 added={'src/'+n:sha(src/n) for n in ['nes_planner211.c','nes_resident211.c','nes_resident211.h']}
 public=['tools/nes_runtime213.py','tools/nes_resident211.py','tools/nes_sink212.py','src/nes/firmware/nes_resident211.c','src/nes/firmware/nes_resident211.h']
 r=dict(copied=pins,changed=changed,added=added,public_sources={n:sha(ROOT/n) for n in public},hardware_package=False,new_fpga=False,
        content_identity='verified SMB3 CRC within freshly reset immutable ROM session; FPGA201 loader epoch/lease remains independent')
 (out/'preparation-runtime213.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.out)
 print(json.dumps(dict(changed=list(r['changed']),added=list(r['added']))))
