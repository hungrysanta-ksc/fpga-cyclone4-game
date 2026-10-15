# SPDX-License-Identifier: MIT
"""Materialize queue endpoint and explicit enqueue/barrier runtime candidates.

Not deployable until paired system, stack, timing and physical checks complete.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_board181 import copy_pins

def sink_header(s):
 s=replace(s,' nes_sink165_exchange_fn exchange;void *ctx;',
  ' nes_sink165_exchange_fn exchange;void *ctx;\n bool (*enqueue)(void *,const uint8_t *,unsigned);')
 return s

def sink(s):
 # Queued data deliberately returns WITHOUT synthesizing a SNES ACK.
 # BEGIN and SEAL retain real response verification and are drain barriers.
 anchor=' if(!s->exchange(s->ctx,b,n+16,ack))'
 assert s.count(anchor)==1
 s=s.replace(anchor,''' if(s->enqueue && (b[0]==2||b[0]==4||b[0]==5)){
  if(!s->enqueue(s->ctx,b,n+16)){nes_sink168_capture(b,ack,false,0);return fail(s,2);}
  s->sequence++;s->state=old;return true;
 }
 if(!s->exchange(s->ctx,b,n+16,ack))''')
 return s

def runtime(s):
 return replace(s,''' s->transport=(struct nes_sink_spi165){transfer,s,guard,65536};
 nes_sink165_reset(&s->sink,nes_sink_spi165_exchange,&s->transport);''',
 ''' if(!nes_window184_init(&s->transport,transfer,guard,s,65536))return fail(s,NES_RUNTIME165_DISPLAY);
 nes_sink165_reset(&s->sink,nes_window184_barrier,&s->transport);
 s->sink.enqueue=nes_window184_enqueue;''')

def arm(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='8f5ca30ef93f887b87df505dac459dcca4da44efe8776cc1a11e43562444106a'
 prep=json.loads((prior/'preparation-status183.json').read_bytes());pins=prep['copied']|prep['changed']|prep['added'];copy_pins(prior,out,pins)
 changed={};added={}
 def write(n,s,table=changed):
  (out/n).write_text(s,encoding='utf8',newline='\n');table[n]=sha(out/n)
 for n,fn in [('nes_native_sink165.c',sink),('nes_native_sink165.h',sink_header),('nes_native_runtime165.c',runtime)]:
  write('src/'+n,fn((prior/'src'/n).read_text()))
 n='src/nes_native_runtime165.h';s=(prior/n).read_text()
 s=replace(s,'#include "nes_sink_spi165.h"','#include "nes_sink_spi165.h"\n#include "nes_sink_window184.h"')
 s=replace(s,'struct nes_sink_spi165 transport','struct nes_sink_window184 transport');write(n,s)
 for n in ['nes_sink_window184.c','nes_sink_window184.h']:write('src/'+n,(ROOT/'src/nes/firmware'/n).read_text(),added)
 n='src/Makefile';write(n,replace((prior/n).read_text(),'nes_sink_spi165.c nes_native_runtime165.c','nes_sink_spi165.c nes_sink_window184.c nes_native_runtime165.c'))
 # Source build only. Keep identity183 explicitly until the paired package gate.
 r=dict(copied=pins,changed=changed,added=added,baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),hardware_package=False,identity_not_for_deployment=True,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_window184.py','src/nes/firmware/nes_sink_window184.c','src/nes/firmware/nes_sink_window184.h']})
 for n in ['preparation-window184.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 return r

def board(prior,out):
 assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
 m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
 for n,h in pins.items():
  assert sha(prior/n)==h,n;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,p)
 s=(ROOT/'src/nes/diagnostic/nes_sink_queue184.sv').read_text()
 s=replace(s,'module nes_sink_queue184(','module nes_sink_spi165(')
 (out/'nes_sink_spi165.sv').write_text(s,encoding='utf8',newline='\n')
 changed=[n for n in pins if sha(out/n)!=pins[n]];assert changed==['nes_sink_spi165.sv']
 m.update(baseline_window184_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,adopted=False,hardware=False,
  window184_sources={n:sha(ROOT/n) for n in ['tools/nes_window184.py','src/nes/diagnostic/nes_sink_queue184.sv']})
 (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8');return m

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['arm','board'])
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=globals()[a.kind](a.prior,a.out);print(json.dumps(dict(changed=r['changed'],hardware_package=False)))
