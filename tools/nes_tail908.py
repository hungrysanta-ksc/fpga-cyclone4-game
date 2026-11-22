"""Build and replay three independent changes to the MMC907 post-OBJ schedule."""
import argparse
from pathlib import Path
from collections import Counter
from nes_raw506 import once, sha
from prepare_nes_trial907 import PROBES, WORK as BASE
from replay_nes_peer906 import compare

WORK=PROBES/'nes-tail908'
ACK_WORK=PROBES/'nes-tail908-ack'
FILL_WORK=PROBES/'nes-tail908-fill'
OLD=''' unsigned run=repeat_bytes(b,n);if(run>=64)return run;
 unsigned end=n<240?n:240;
 for(unsigned i=1;i<end&&i+64<=n;i++)if(repeat_bytes(b+i,64)==64)return i;
 return end;'''
NEW=''' unsigned end=n<240?n:240;
 unsigned start=0;
 for(unsigned i=2;i<n && start<end;i++){
  /* A mismatch at i rules out every start through i-2. */
  if(b[i]!=b[i-2])start=i-1;
  else if(i-start==63)return start?start:repeat_bytes(b,n);
 }
 return end;'''


def prepare():
    assert sha(BASE/'link/src/obj-nes-100/firmware.stm')=='dba9d47853d5c470a85b7041019d396bd0abf70939c14ff7751ccf2e3cbcfe74'
    patch=WORK/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    name='nes_native_sink165.c'
    (patch/name).write_text(once((BASE/'link/src'/name).read_text(),OLD,NEW),newline='\n')
    patch=ACK_WORK/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    name='nes_native_runtime165.c'
    src=(BASE/'link/src'/name).read_text()
    src=once(src,' bool input_wait=',' bool first_seal_poll=reason==3;\n bool input_wait=')
    src=once(src,'   if(reason!=2)break;',
             '   /* Return to the checked display status after the first input service. */\n'
             '   if(reason!=2 || first_seal_poll)break;')
    (patch/name).write_text(src,newline='\n')
    patch=FILL_WORK/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    name='nes_native_sink165.c'
    src=(BASE/'link/src'/name).read_text()
    # The independent receiver already supports exact word fills within
    # section 5. Keep the usual two heads when even one 64-byte run differs.
    old='''  if(!packet(s,2,5,offset,joined,201))return false;
  if(!packet(s,2,5,offset+201,joined+201,240))return false;'''
    new='''  unsigned skip=0;
  if(repeat_bytes(joined,64)==64 && repeat_bytes(joined+64,64)==64 &&
     repeat_bytes(joined+128,64)==64){
   for(;skip<192;skip+=64)
    if(!packet(s,2,5,offset+skip,joined+skip,64))return false;
  }
  if(!packet(s,2,5,offset+skip,joined+skip,201-skip))return false;
  if(!packet(s,2,5,offset+201,joined+201,240))return false;'''
    (patch/name).write_text(once(src,old,new),newline='\n')

def early_status_order(trace):
    # Only move one already-recorded, still-pending E0 across independent
    # input traffic. Preserve every byte, the eventual final receipt and EA.
    rows=list(trace)
    seal,=[i for i,(tx,_) in enumerate(rows) if tx.startswith('e103')]
    first=next(i for i in range(seal+1,len(rows)) if rows[i][0].startswith('e0'))
    insert=seal+4
    assert [tx[:2] for tx,_ in rows[seal+1:insert]]==['d1','d2','d0']
    assert all(tx[:2] in ('d0','d1','d2') for tx,_ in rows[insert:first])
    reply=bytes.fromhex(rows[first][1])
    assert reply[2]&1 and reply[3:5]!=reply[5:7] and rows[first]==rows[first+1]
    rows.insert(insert,rows.pop(first))
    assert Counter(map(tuple,rows))==Counter(map(tuple,trace))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('patch')
    guard=sub.add_parser('guards')
    guard.add_argument('variant',choices=('linear','ack','fill'))
    guard.add_argument('rom',type=Path)
    r=sub.add_parser('replay')
    r.add_argument('temp',type=Path)
    r.add_argument('phase',type=int,choices=(1,2))
    r.add_argument('--cold',action='store_true')
    variants=r.add_mutually_exclusive_group()
    variants.add_argument('--ack',action='store_true')
    variants.add_argument('--fill',action='store_true')
    a=p.parse_args()
    if a.action=='patch':prepare()
    elif a.action=='guards':
        from check_nes_supply905_arm import run
        run(a.rom,{'linear':WORK,'ack':ACK_WORK,'fill':FILL_WORK}[a.variant],907,
            order=early_status_order if a.variant=='ack' else None)
    else:
        tag,work=('908-fill',FILL_WORK) if a.fill else ('908-ack',ACK_WORK) if a.ack else ('908-linear',WORK)
        compare(a.temp,a.phase,a.cold,True,edition=907,work_arm=work,run_id=tag)
