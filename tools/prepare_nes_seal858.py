"""Build the compact SEAL on 857B, with a full-width fallback for every set bit."""
import argparse
import json
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_raw506 import once
from prepare_nes_trial802 import PROBES

ROOT = PROBES / 'nes-seal858'
BASE = PROBES / 'nes-column854/client-e'
ORIGIN = 0x7e2000


def sender(out, compact_serial=False, variable=False):
    src = PROBES / 'nes-output857/link-b/src/nes_native_sink165.c'
    s = once(src.read_text(), 'static bool fail(struct nes_native_sink165',
             'static __attribute__((cold,noinline)) bool fail(struct nes_native_sink165')
    s = once(s, ''' memcpy(descriptor+24,r->used,144);
 if(!packet(s,3,0,0,descriptor,sizeof descriptor))''',
             ''' /* Bits 256..1023 are implicitly zero in the short SEAL. */
 unsigned end=128;
 while(end>32 && !r->used[end-1])end--;
 unsigned prefix=end==32 ? 32 : 128;
 memcpy(descriptor+24,r->used,prefix);
 memcpy(descriptor+24+prefix,r->used+128,16);
 if(!packet(s,3,0,0,descriptor,40+prefix))''')
    if variable:
        s=once(s,''' unsigned end=128;
 while(end>32 && !r->used[end-1])end--;
 unsigned prefix=end==32 ? 32 : 128;''',''' unsigned prefix=128;
 while(prefix>4){
  uint32_t word;
  memcpy(&word,r->used+prefix-4,sizeof word);
  if(word)break;
  prefix-=4;
 }''')
    if compact_serial:
        s = once(s, "for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));",
                 "memcpy(b+4,&s->serial,4); /* Cortex-M4 is little endian. */")
    out.mkdir(parents=True)
    (out/src.name).write_text(s)


def receiver(out, direct_budget=False, table_check=False, variable=False):
    labels = json.loads((BASE/'labels.json').read_bytes())
    body = bytearray((BASE/'body.bin').read_bytes())
    # Allow exactly 72 and 168 bytes. Both share the original header, sizes
    # and section fields. The existing header loader checks the payload count.
    i = body.index(bytes.fromhex('c9 a8 00 f0 03'), labels['seal']-ORIGIN)
    c = Code(labels['coverage212'])
    c.labels.update(labels)
    c.absolute(0xac,0x1254)
    c.emit(0xa2,0,0)
    c.label('word858')
    for offset in range(0,4,2):
        c.long(0xbf,0x400028+offset)
        c.branch(0xf0,f'next858_{offset}')
        c.emit(0x49,255,255)
        c.absolute(0x19,0x1320+offset)
        c.emit(0x1a)
        c.branch(0xd0,'missing858')
        c.label(f'next858_{offset}')
    for transfer,restore in ((0x98,0xa8),(0x8a,0xaa)):
        c.emit(transfer,0x18,0x69,4,0,restore)
    # X indexes transmitted words, Y indexes valid bits in the target bank.
    if variable:
        c.emit(0x8a,0x18,0x69,40,0)
        c.absolute(0xcd,0x120c)
        c.branch(0xd0,'end858')
        c.absolute(0xad,0x1254)
        c.emit(0x18,0x69,128,0,0xa8)
    else:
        c.emit(0xe0,32,0)
        c.branch(0xd0,'end858')
        c.absolute(0xad,0x120c)
        c.emit(0xc9,72,0)
        c.branch(0xd0,'word858')
        c.emit(0x98,0x18,0x69,96,0,0xa8)
    c.label('end858')
    c.emit(0x8a,0x18,0x69,24,0)
    c.absolute(0xcd,0x120c)
    c.branch(0xd0,'word858')
    c.emit(0xa2,144,0)
    c.jump('covered619')
    c.label('missing858')
    c.jump('mark_bad212')
    c.label('width858')
    if variable:
        c.emit(0xc9,44,0)
        c.branch(0x90,'invalid_width858')
        c.emit(0xc9,169,0)
        c.branch(0xb0,'invalid_width858')
        c.emit(0x89,3,0)
        c.branch(0xd0,'invalid_width858')
    else:
        c.emit(0xc9,72,0)
        c.branch(0xf0,'valid_width858')
        c.emit(0xc9,168,0)
        c.branch(0xd0,'invalid_width858')
    c.label('valid_width858')
    c.absolute(0x4c,ORIGIN+i+8 & 65535)
    c.label('invalid_width858')
    c.jump('bad_packet')
    code = c.finish()
    start, end = (labels[k]-ORIGIN for k in ('coverage212','covered619'))
    assert len(code)<=end-start
    body[start:end] = code.ljust(end-start,b'\0')
    body[i:i+8] = bytes([0x4c])+ (c.labels['width858'] & 65535).to_bytes(2,'little')+bytes(5)
    if table_check:
        from nes_seal831 import checked_tables
        lo,hi=(labels[k]-ORIGIN for k in ('table181','table_end181'))
        q=Code(ORIGIN+lo)
        q.labels.update(labels)
        checked_tables(q)
        replacement=q.finish()
        assert len(replacement)<=hi-lo
        body[lo:hi]=replacement.ljust(hi-lo,b'\0')
        c.labels.update({k:v for k,v in q.labels.items() if k not in labels})
    if direct_budget:
        at=labels['budget538']-ORIGIN
        tail=body.index(bytes.fromhex('8a 18 69 08 00 aa'),at)
        assert body[at:tail].hex()=='bf04407e186960008574ad561238e574900e8d5612'
        # Leave the previous remaining budget intact if either subtraction
        # borrows. A descriptor is admitted only if its length plus 96 fits.
        q=Code(ORIGIN+at)
        q.labels.update(labels)
        q.absolute(0xad,0x1256)
        q.emit(0x38)
        q.long(0xff,0x7e4004)
        q.branch(0x90,'group_ready538')
        q.emit(0xe9,96,0)
        q.branch(0x90,'group_ready538')
        q.absolute(0x8d,0x1256)
        tail_end=labels['group_ready538']-ORIGIN
        q.emit(0x8a,0x18,0x69,8,0,0xaa)
        q.absolute(0xec,0x1250)
        q.branch(0x90,'budget538')
        q.jump('group_ready538')
        body[at:tail_end]=q.finish().ljust(tail_end-at,b'\0')
        assert len(body)==len((BASE/'body.bin').read_bytes())
    build(BASE,out,bytes(body),c.labels,True)
    describe_receiver(out,direct_budget,table_check,variable)


def describe_receiver(out,direct_budget,table_check,variable):
    path=out/'build.json'
    info=json.loads(path.read_bytes())
    info.update(candidate='seal858', SEAL_payload_B=list(range(44,169,4)) if variable else [72,168],
                direct_DMA_budget=direct_budget, bank_local_table_check=table_check)
    path.write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part',choices=('sender','sender-b','sender-c','sender-f','receiver','receiver-d','receiver-e','receiver-f'))
    opts=parser.parse_args()
    if opts.part=='sender':
        sender(ROOT/'patch')
    elif opts.part=='sender-b':
        sender(ROOT/'patch-b',True)
    elif opts.part in ('sender-c','sender-f'):
        out=ROOT/('patch-'+opts.part[-1])
        sender(out,variable=opts.part=='sender-f')
        src=PROBES/'nes-output857/link-b/src/nes_plan_service200.c'
        s=once(src.read_text(),'static bool fail(struct nes_plan200',
               'static __attribute__((noinline)) bool fail(struct nes_plan200')
        (out/src.name).write_text(once(s,'static uint32_t token485(',
                                 'static inline __attribute__((always_inline)) uint32_t token485('))
    elif opts.part=='receiver-f':
        receiver(ROOT/'client-f',True,True,True)
    elif opts.part=='receiver-e':
        receiver(ROOT/'client-e',True,True)
    elif opts.part=='receiver-d':
        receiver(ROOT/'client-d',True)
    else:
        receiver(ROOT/'client')
