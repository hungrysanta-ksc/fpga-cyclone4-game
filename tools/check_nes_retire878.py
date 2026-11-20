"""Check linked E0/EA ownership and align full-scene clocks to the 874 edge."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline875 import STRIDE, analyze, points
from analyze_nes_credit876 import verified_commits
from analyze_nes_map830 import load, packets, window
from check_nes_game478 import crc
from check_nes_strip869 import digest
from check_nes_table877 import timings, table_packets


def retire_guards(work):
    from guard_nes_progress870 import Machine, crc, offsets
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR
    src=work/'link-credit/src'
    cpu=Machine(src,bytes(128))
    plan,sink,queue=0x20012000,0x20012400,0x20012800
    guard,transfer=0x0807ffc4,0x0807ffc8
    layout={ptr:offsets(src,name) for ptr,name in ((plan,'nes_plan200'),(sink,'nes_native_sink165'),(queue,'nes_sink_window184'))}
    def put(ptr,k,v,n):
        cpu.u.mem_write(ptr+layout[ptr][k],v.to_bytes(n,'little'))
    def reply(u,pc,size,ctx):
        ok=True
        if pc==transfer:
            tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R3)))
            op=tx[0]
            bus.append(op)
            if op==0xe0:
                r=bytearray.fromhex('00f702000100010103')+header[2:]+bytes.fromhex('659a00')
                if case=='old_seal':r[15]^=1
                if case=='queue_live':r[2]=1;r[6]=0
                r[-1]=crc(r[1:-1],8,7,0)^int(case=='bad_E0_CRC')
            elif op==0xea:
                assert tx==ea
                ok=case!='EA_io'
                r=bytes(7)
            else:
                assert op==0xe8
                r=bytearray(20);r[1:4]=bytes((0xd7,4,1))
                if checking_finish:
                    r[3]=3 if case=='bad_finish_flags' else 2
                    r[5]=11-int(case=='bad_finish_count')
                    r[7]=int(case=='bad_finish_empty')
                elif 0xea not in bus:
                    assert case in ('incomplete','incomplete_count')
                    r[3]=2;r[5]=11-int(case=='incomplete_count')
                elif case=='delayed' and bus.count(op)==1:r[3]=6;r[5]=11
                elif case=='old_count':r[5]=11
                elif case=='late_fault':r[3]=0x80
                elif case=='stale_chunk':r[6]=1
                elif case=='reserved':r[18]=1
                r[19]=crc(r[1:19],8,7,0)^int(case==('bad_finish_crc' if checking_finish else 'bad_E8_CRC'))
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(r))
        else:
            ok=not ((case=='STOP_before_EA' and bus==[0xe0]) or
                    (case=='STOP_after_EA' and 0xea in bus))
        u.reg_write(UC_ARM_REG_R0,int(ok))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for pc in (guard,transfer):
        cpu.u.hook_add(UC_HOOK_CODE,reply,begin=pc,end=pc)
    header=bytes.fromhex('0300300021000000b603')
    ea=bytes.fromhex('eab603000b');ea+=bytes((crc(ea,8,7,0),0xa5))
    rows={}
    conditional=work.name.endswith('-overlap')
    cases=('normal','delayed','old_seal','bad_E0_CRC','queue_live','unfinished','previous_generation',
           'STOP_before_EA','EA_io','STOP_after_EA','bad_E8_CRC','late_fault','old_count','stale_chunk','reserved',
           'bad_finish_flags','bad_finish_count','bad_finish_empty','bad_finish_crc')
    for case in cases+(('incomplete','incomplete_count') if conditional else ()):
        for ptr in layout:cpu.u.mem_write(ptr,bytes(512))
        for ptr in (queue,plan):
            for k,v,n in [('guard',guard|1,4),('transfer',transfer|1,4),('poll_limit',3,4)]:
                put(ptr,k,v,n)
        for k,v,n in [('sent',1,2),('ever_sent',1,1),('initialized',1,1)]:put(queue,k,v,n)
        cpu.u.mem_write(queue+layout[queue]['last'],header)
        for k,v,n in [('sink',sink,4),('generation',950,2),('sent',11,2),('started',1,1),('ending',1,1)]:
            put(plan,k,v,n)
        for k,v,n in [('displayed',1,1),('generation',950,2),('last_generation',950-int(case=='previous_generation'),2)]:
            put(sink,k,v,n)
        bus=[]
        checking_finish=True
        put(sink,'state',1,1)
        finished=cpu.call('nes_plan200_progress',[plan,0])
        if case.startswith('bad_finish'):
            assert not finished and bus==[0xe8]
            rows[case]={'FINISH_rejected':True}
            continue
        assert finished and bus==[0xe8]
        checking_finish=False
        bus=[]
        put(sink,'state',0,1)
        if case=='unfinished':put(plan,'finished',0,1)
        ack=cpu.call('nes_window184_drain',[queue,queue+128])
        args=[plan,int(not case.startswith('incomplete'))] if conditional else [plan]
        retired=bool(ack and cpu.call('nes_plan200_retire',args))
        assert retired==(case in ('normal','delayed','incomplete')),(case,bus)
        if case in ('old_seal','bad_E0_CRC','queue_live','unfinished','previous_generation','STOP_before_EA','incomplete_count'):
            assert 0xea not in bus
        if retired:
            assert bus==[0xe0]+[0xe8]*int(case=='incomplete')+[0xea]+[0xe8]*(1+int(case=='delayed'))
        rows[case]={'transactions':[hex(i) for i in bus],'returned_rearmed':retired}
    return {'cases':rows,'ARM':digest(src/'obj-nes-100/firmware.stm')}


def trace(folder,edge,work=None,ph=None):
    r=timings(folder,edge,work,ph)
    shows=[(e['g'],e['frame']) for e in window(folder) if e['event']=='reveal']
    r['intervals']={g:b-a for (_,a),(g,b) in zip(shows[1:],shows[2:])}
    assert len(r['intervals'])==60 and sum(r['intervals'].values())==r['dense60']
    start=r['show950']['clock']
    stages=('display950_ACK','checked_E0_950','old_EA','D3','commit_D2')
    r['from_publish']={k:r[k]-start for k in stages}
    r['from_valid_E0']=r['commit_D2']-r['checked_E0_950']
    r['spi']=[(e['opcode'],round(e['start']-start),round(e['clock']-start))
              for e in load(folder/'events.json') if e.get('opcode') and
              r['checked_E0_950']<=round(e['clock'])<=r['commit_D2']]
    # Charge the six mandatory calls at their measured SPI/driver duration.
    # This bound holds at this E0 with this link/driver and zero code gaps.
    tail=r['spi'][next(i for i,v in enumerate(r['spi']) if v[0]=='0xea'):]
    expected=['0xea','0xe8','0xd3','0xd0','0xd1','0xd2']
    if [e[0] for e in tail]==expected:
        elapsed=sum(end-begin for _,begin,end in tail)
        r['fixed_E0_budget']={'until_edge':edge-r['checked_E0_950'],'six_transfers':elapsed,
                              'left_for_other_work':edge-r['checked_E0_950']-elapsed}
    return r


def verify_retire_order(folder):
    """Match each SEAL's real receipt to EA, its E8 rearm and the next D3."""
    from collections import defaultdict
    bus=load(folder/'events.json')
    transactions=defaultdict(list)
    for e in bus:
        if e.get('opcode'):
            transactions[e['generation']].append(e)
    acks={e['g']:e['clock'] for e in window(folder) if e['event']=='ack' and e['op']==3}
    commits={e['input_generation']:e for e in bus if e.get('opcode')=='0xd3'}
    plan_status=[e for e in bus if e.get('opcode')=='0xe8']
    old_to_new={e['previous_output']:e['generation'] for e in bus if e['event']=='source_begin' and 'previous_output' in e}
    count=0
    for i,b in enumerate(packets(folder),1):
        if b[0]!=3:continue
        g=int.from_bytes(b[8:10],'little')
        expected=bytes((1,3))+b[2:10]+bytes.fromhex('659a')
        rows=transactions[g]
        ea,=[e for e in rows if e['opcode']=='0xea']
        end=next(e for e in rows if e['opcode']=='0xe0' and acks[g]<=e['clock']<ea['start']
                 and bytes.fromhex(e['reply'])[7:19]==expected)
        status=bytes.fromhex(end['reply'])
        assert status[1]==0xf7 and status[2]&2 and status[19]==crc(status[1:19],8,7,0)
        assert int.from_bytes(status[3:5],'big')==int.from_bytes(status[5:7],'big')==i
        rearm=next(e for e in plan_status if ea['clock']<=e['start'] and
                   bytes.fromhex(e['reply'])[1:19]==bytes((0xd7,4,1))+bytes(15))
        data=bytes.fromhex(rearm['reply'])
        assert data[19]==crc(data[1:19],8,7,0)
        if g in old_to_new:assert rearm['clock']<commits[old_to_new[g]]['start']
        count+=1
    assert count==len(acks)==len(commits)
    return count


def report(temp):
    root=Path(__file__).resolve().parents[2]
    result={'reference':{},'candidates':{},'fixed_prefix':{}}
    rtl=temp/'nes-trial816-board872/nes_plan_spi200.sv'
    log=(temp/'nes-retire878-endpoint/run.log').read_text(errors='replace')
    assert 'PASS retire878 9 conditions' in log and 'Errors: 0' in log
    result['endpoint']={'SHA256':digest(rtl),'tested_conditions':9}
    for ph in (1,2):
        prefix=f'nes-tile821-demo-jointmirror-p{ph}-'
        edge=points(temp/(prefix+'874-drain'))['previous_capture_edge']
        result['reference'][ph]={tag:trace(temp/(prefix+tag),edge) for tag in ('872-final','874-drain','877-stable')}
        ref,tr=temp/(prefix+'877-stable'),temp/(prefix+'878-once')
        control=result['reference'][ph]['877-stable']
        variant=trace(tr,edge)
        for key in ('show950','map950','gap950','display950_ACK','checked_E0_950'):
            assert control[key]==variant[key],key
        boundary=control['checked_E0_950']
        def before(folder):
            return [e for e in load(folder/'events.json') if e.get('opcode') and round(e['clock'])<=boundary]
        assert before(ref)==before(tr)
        assert table_packets(tr)==table_packets(ref)
        joint=load(tr/'joint.json')
        assert joint['passed'] and verified_commits(tr)==joint['commits']
        assert load(tr/'ack861.json')['loads']==load(ref/'ack861.json')['loads']
        for fr in joint['frames']:
            g=fr['generation']
            assert (tr/f'map-{g}.bin').read_bytes()==(ref/f'map-{g}.bin').read_bytes()
            assert (tr/f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]==(ref/f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]
        result['fixed_prefix'][ph]=variant
    for mode in ('finish','ready','overlap'):
        tag='878-'+mode
        work=root/'probes'/('nes-retire878-'+mode)
        r=analyze(temp,root,work,tag)
        r['retire_guard']=load(work/'retire-guards.json')
        assert r['retire_guard']['ARM']==r['ARM'] and r['guards']['source_tag']==tag
        r['dense']={}
        for clip in ('opening','transition','demo'):
            for ph in (1,2):
                prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
                f=temp/(prefix+tag)
                assert verified_commits(f)==load(f/'joint.json')['commits']
                r.setdefault('verified_releases',{})[clip+'-'+str(ph)]=verify_retire_order(f)
                assert table_packets(f)==table_packets(temp/(prefix+'877-stable'))
                if clip!='demo':continue
                refs=result['reference'][ph]
                old=refs['874-drain']
                t=trace(f,old['commit_D2']-old['commit_minus_874_edge'],work,ph)
                r['dense'][ph]=t
                r['gates'][f'publish950_p{ph}']=t['show950']['clock']<=refs['877-stable']['show950']['clock']
                r['gates'][f'capture_p{ph}']=t['commit_minus_874_edge']<0
                r['gates'][f'chain_p{ph}']=t['from_valid_E0']<refs['877-stable']['from_valid_E0']
        r['passed']=all(r['gates'].values());result['candidates'][mode]=r
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('guard','report'))
    p.add_argument('directory',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    data=retire_guards(a.directory) if a.mode=='guard' else report(a.directory)
    a.out.write_text(json.dumps(data,indent=2)+'\n')
