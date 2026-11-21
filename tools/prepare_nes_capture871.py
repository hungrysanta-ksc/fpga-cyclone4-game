"""Reuse a validated capture status across the END/prepare/COMMIT boundary."""
import argparse
import hashlib
from pathlib import Path

from nes_raw506 import once


def prepare(base, out, variant):
    warm_banks=variant=='banks'
    if warm_banks:
        variant='ready_frame'
    shared_frame=variant.endswith('_frame')
    if shared_frame:
        variant=variant[:-6]
    firmware = base/'obj-nes-100/firmware.stm'
    assert hashlib.sha256(firmware.read_bytes()).hexdigest() == '63a308da4cdca7d0069e6754cc9a5642d16db35f464b13052a78bd3511c2a149'
    name = 'nes_native165.c'
    src = (base/name).read_text()
    if variant in ('warm','warm_clean','warm_dual'):
        # Keep the cold handshake and the general block-poll loop unchanged.
        # Only the runtime knows whether a checked display has already committed.
        src=once(src,'frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,28);',
                 '''frame(tx,0xd0,0,0);
 if(!fn(ctx,tx,s->status183,8)||!status(s->status183))return fail(s,28);
 s->ready183=s->status183[2]&1;''')
        if variant=='warm':
            src=once(src,'static bool obj_overflow807(','static bool __attribute__((noinline)) obj_overflow807(')
        else:
            src=once(src,'static bool fail(','static bool __attribute__((noinline)) fail(')
        if variant=='warm_dual':
            src=once(src,'if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){',
                     'if((s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) ||\n'
                     '    (s->state==NES_NATIVE165_COMPLETE && (rx[2]&2))){')
            src=once(src,''' s->ready183=false;
 uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);''',
                     ''' uint8_t tx[8],rx[8];
 if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}
 else {frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}
 if(!status(rx)||!(rx[2]&2))return fail(s,25);''')
        runtime='nes_native_runtime165.c'
        body=once((base/runtime).read_text(),
                  'if(!nes_native165_prepare(r,true,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);',
                  '''if(!nes_native165_prepare(r,true,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  r->ready183 &= s->sink.displayed;''')
        if variant=='warm_dual':
            body=once(body,'if(!nes_native165_prepare(r,true,transfer,s))',
                      'r->ready183 &= s->sink.displayed;\n  if(!nes_native165_prepare(r,true,transfer,s))')
        out.mkdir(parents=True,exist_ok=False)
        (out/runtime).write_text(body,newline='\n')
        (out/name).write_text(src,newline='\n')
        return
    src = once(src, ' s->state=skip?NES_NATIVE807_WAIT_ABORT:', ''' /* D3 is confirmed by this D0. Only positive, sealed head metadata
  * survives the call. D1 payload, token, and D2 retirement stay checked. */
 if(accept && !skip && (rx[2]&1)){
  memcpy(s->status183,rx,8);s->ready183=true;
 }
 s->state=skip?NES_NATIVE807_WAIT_ABORT:''')
    if variant=='ready_both':
        src = once(src, 'if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){',
                   'if((s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) ||\n'
                   '    (s->state==NES_NATIVE165_COMPLETE && (rx[2]&2))){')
        src = once(src, ''' s->ready183=false;
 uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);''',
                   ''' uint8_t tx[8],rx[8];
 /* The D0 that confirmed the final data POP can also confirm END.
  * An absent END still requires a fresh status. */
 if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}
 else {frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}
 if(!status(rx)||!(rx[2]&2))return fail(s,25);''')
    if shared_frame:
        src=once(src,'uint8_t tx[8],rx[8];','uint8_t tx[8],*rx=s->status183;')
        src=once(src,'''if(accept && !skip && (rx[2]&1)){
  memcpy(s->status183,rx,8);s->ready183=true;
 }''','s->ready183=rx[2]&1; /* WAIT_ABORT still checks its exact record; FAILED cannot poll. */')
        if variant.endswith('_both'):
            src=once(src,'if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}\n else {frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}',
                     'if(!s->ready183){frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,25);}\n s->ready183=false;')
    from check_nes_game478 import crc
    check=crc(bytes.fromhex('d000000000ff'),8,7,0)
    src=once(src,'static bool status(',f'static const uint8_t query871[8]={{0xd0,0,0,0,0,0xff,0x{check:02x},0xa5}};\nstatic bool status(')
    old='frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)'
    assert src.count(old)==4
    src=src.replace(old,'if(!fn(ctx,query871,rx,8)')
    if shared_frame:
        src=once(src,'static void frame(','static void __attribute__((noinline)) frame(')
    out.mkdir(parents=True,exist_ok=False)
    (out/name).write_text(src,newline='\n')
    if warm_banks:
        runtime='nes_native_runtime165.c'
        body=once((base/runtime).read_text(),
                  'if(!nes_native165_prepare(r,true,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);',
                  '''if(!nes_native165_prepare(r,true,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  if(s->plan.bank_history!=2)r->ready183=false;''')
        (out/runtime).write_text(body,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('variant',choices=('wire','ready_frame','ready_both_frame','warm','banks','warm_clean','warm_dual'))
    prepare(**vars(parser.parse_args()))
