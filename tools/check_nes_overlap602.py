"""Timestamp linked M4 calls on pinned input and bound one-block lookahead on the same two display timelines."""
import argparse
import json
from pathlib import Path

from analyze_nes_wire600 import MASTER, DisplayGate, Receiver, UC_ARM_REG_R1, UC_ARM_REG_R3, display_guards, first_visible_switch, ms
from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_R2, crc
from test_nes_service509_schedule import Calendar
from check_nes_wire600 import GENERATIONS, ROOT, pin, pin_packets, read, sha


class Timed(Receiver):
    def start(self,packets):
        self.tracing=False
        super().start(packets)
        self.marks=[]
        self.origin=self.instructions
        self.return_pc=None
        self.tracing=True

    def hook(self,u,at,size,user):
        if getattr(self,'tracing',False):
            event=None
            n=0
            if at==self.spi:
                event=hex(u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0])
                n=u.reg_read(UC_ARM_REG_R3)
            elif at==self.syms['nes_native165_packet']:
                assert self.return_pc is None
                self.return_pc=u.reg_read(UC_ARM_REG_LR)&~1
                event='decode'
            elif at==self.return_pc:
                self.return_pc=None
                event='decoded'
            if event:
                self.marks.append((event,self.index,self.instructions-self.origin,n))
        if at==self.spi and u.reg_read(UC_ARM_REG_R3)==4:
            tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),4))
            assert tx[0]==210 and tx[3]==crc(tx[:3],8,7,0)
            assert int.from_bytes(tx[1:3],'big')==(self.start_token+self.index)&65535
            self.ops.append(('0xd2',4))
            u.mem_write(u.reg_read(UC_ARM_REG_R2),self.status()[:4])
            if not getattr(self,'drop_credit',False):self.index+=1
            self.spi_calls+=1
            u.reg_write(UC_ARM_REG_R0,1)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,at,size,user)


def profile(marks,counts,phase):
    extra=phase['parameters']['driver_extra_us']
    cpi=phase['parameters']['CPI']
    t=0
    last=0
    blocks=[]
    for event,i,ins,n in marks:
        t+=(ins-last)*cpi/84000
        last=ins
        if event=='0xd1':
            assert len(blocks)==i
            blocks.append(dict(index=i,D1_B=n,D1_start_ms=t))
        if n:
            # Driver excess and bits are both charged. Only call boundaries are timed.
            t+=ms(n)+extra[event]/1000
        if event=='0xd1':
            blocks[i]['D1_return_ms']=t
        elif event=='decode':
            blocks[i]['packet_enter_ms']=t
        elif event=='decoded':
            blocks[i]['packet_return_ms']=t
        elif event=='0xd2':
            blocks[i].update(D2_issue_ms=t-ms(n)-extra[event]/1000,D2_return_ms=t)
        elif event=='0xd0' and i and 'retired_confirm_ms' not in blocks[i-1]:
            blocks[i-1]['retired_confirm_ms']=t
    end=t+(counts['receive_instructions']-last)*cpi/84000
    for b in blocks:
        stamps=[b[key] for key in ('D1_start_ms','D1_return_ms','packet_enter_ms','packet_return_ms',
                                  'D2_issue_ms','D2_return_ms','retired_confirm_ms')]
        assert stamps==sorted(stamps)
    return end,blocks


class ShortDisplay(DisplayGate):
    def input_exchange(self,tx):
        if tx[0]!=210:return super().input_exchange(tx)
        assert len(tx)==4 and tx[3]==crc(tx[:3],8,7,0)
        r=self.old_status()
        self.pop(int.from_bytes(tx[1:3],'big'))
        return r[:4]


def short_guards(src,g,pkts):
    m=Timed(src,bytes(128))
    checked=m.guards(pkts)
    m.start(pkts);m.drop_credit=True
    assert not m.pump() and m.index==0 and m.state_value()==5
    rows=[]
    for mode in ('normal','wrong_final_ACK','STOP_at_EA'):
        rt=ShortDisplay(src,False,400)
        rt.generation=rt.ep.generation=g
        rt.start_token=65520
        rt.packets=pkts
        rt.index=rt.produced=rt.max_ring=0
        rt.prepared=rt.saw_ea=rt.saw_seal=False
        rt.guard_mode=mode
        for _ in range(512):
            ok=rt.call('nes_runtime165_step',[rt.rt])
            if rt.saw_ea or not ok:break
        count=rt.get(rt.rt,'nes_native_runtime165','frames',4)
        assert rt.saw_seal and bool(ok)==(mode=='normal') and rt.max_ring==1
        assert rt.saw_ea==(mode!='wrong_final_ACK') and count==int(mode!='wrong_final_ACK')
        assert rt.state_value()==(0 if ok else 4)
        rows.append(dict(mode=mode,EA=rt.saw_ea,count=count))
    return dict(input=checked+['dropped_POP_rejected_by_post_D0'],display=rows)


def main(a):
    old=read(ROOT/'analysis/wire600-verification.json')
    inputs=read(ROOT/'analysis/body581-verification.json')['inputs']
    calendar=Calendar(a.calendar)
    whole=read(ROOT/'analysis/whole580-verification.json')
    source={'legacy':a.arm/'src','shared':a.probe/'ARM/src','short':a.short/'src'}
    out=dict(stage=602,profiles=[],phases=[],guards={},pin_evidence={},physical=False,
             candidate_end_to_end_ACK_ms=None)
    for name,src in source.items():
        fw=src/'obj-nes-100/firmware.stm'
        if name!='short':pin(fw,old['ARM'][name]['firmware_sha256'])
        out.setdefault('firmware',{})[name]=dict(bytes=fw.stat().st_size,sha256=sha(fw))
        m=Timed(src,bytes(128))
        for g in GENERATIONS:
            variant='shared' if name=='short' else name
            ref=old['receiver'][str(g)][variant]
            d=a.probe/variant
            pin(d/f'transactions-{g}.txt',ref['pins_sha256'])
            pkts=pin_packets(d,g)
            tag_offset=3 if variant=='shared' else 0
            assert pkts[-1][tag_offset:tag_offset+2]==bytes.fromhex('e003')
            end_tag=pkts[-2][-12:-10] if variant=='legacy' else pkts[-2][3:5]
            assert end_tag==bytes.fromhex('e001')
            files=[a.data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
            for f in files:pin(f,inputs[f.name])
            counts=m.receive(pkts,*(f.read_bytes() for f in files),g)
            m.tracing=False
            if name!='short':assert all(counts[k]==ref[k] for k in counts)
            else:
                assert counts['calls']==ref['calls'] and counts['wire']==dict(ref['wire'],**{'0xd2':4*len(pkts)})
            for phase in whole['phases']:
                i=phase['phase']
                end,blocks=profile(m.marks,counts,phase)
                assert all(at['retired_confirm_ms']<=nxt['D1_start_ms'] for at,nxt in zip(blocks,blocks[1:]))
                # Give an independent, already-sealed second slot and autonomous SPI for free.
                # END -> COMMIT still requires PREPARED. Only next D1 wire overlaps semantic restore.
                overlap=sum(min(b['packet_return_ms']-b['packet_enter_ms'],ms(nxt['D1_B']))
                            for b,nxt in zip(blocks[:-2],blocks[1:-1]))
                out['profiles'].append(dict(variant=name,phase=i,generation=g,input_ms=end,blocks=blocks,
                    packet_ms=sum(b['packet_return_ms']-b['packet_enter_ms'] for b in blocks),
                    crc_and_dispatch_ms=sum(b['packet_enter_ms']-b['D1_return_ms'] for b in blocks),
                    max_paired_overlap_ms=overlap))
                if name=='legacy':
                    f=a.traces/f'nes-close561-run{i}'/'events.json'
                    pin(f,phase['evidence']['events.json'])
                    ev=[e for e in read(f) if e.get('generation')==g]
                    origin=next(e['clock'] for e in ev if e['event']=='source_begin')
                    io=[e for e in ev if e.get('opcode') in ('0xd0','0xd1','0xd2','0xd3')]
                    cursor=0
                    for block in blocks:
                        while io[cursor]['opcode']!='0xd1':cursor+=1
                        d1,d2,d0=io[cursor:cursor+3]
                        assert (d2['opcode'],d0['opcode'],d1['bytes'])==('0xd2','0xd0',block['D1_B'])
                        cursor+=3
                        assert d1['clock']<=d2['clock']<=d0['start']<=d0['clock']
                        block['joint_ms']={k:(v-origin)*1000/MASTER for k,v in
                            [('D1_end',d1['clock']),('D2_issue',d2['start']),('D2_end',d2['clock']),('D0_confirm',d0['clock'])]}
                        if d2['start']>d2['clock']:
                            # Historic terminal event has a stale start stamp. Its end and D0 remain ordered.
                            assert block is blocks[-1]
                            block['joint_ms']['D2_issue']=None
                        else:assert d1['clock']<=d2['start']
                if name!='short':continue
                q=next(r for r in old['phases'] if (r['phase'],r['generation'])==(i,g))
                cal=q['relaxed_calendar'];bus=cal['pre_display_bus_end'];prev=cal['previous_reveal']
                control=next(r for r in out['profiles'] if (r['variant'],r['phase'],r['generation'])==('shared',i,g))
                assert abs(control['input_ms']-cal['receiver_ready_ms'])<1e-8
                saved=4*len(blocks)
                # A broader ceiling erases all CPU and all driver costs everywhere in the input.
                # Post-input wire is unchanged; ROM, poll, DMA and VBlank costs are zero before bus end.
                ceiling=control['input_ms']-ms(sum(counts['wire'].values()))
                short_gain=control['input_ms']-end
                reduction=overlap+short_gain
                def interval(t):return (t-prev)*1000/MASTER
                assert phase['parameters']['ROM_calendar']==calendar.summary
                shift=phase['parameters']['ROM_phase']
                def last_rom(release):
                    for _ in range(cal['ROM_reads_due']):
                        release=calendar.select(release-shift)[1]+shift
                    return release
                assert last_rom(cal['ROM_release'])==cal['ROM_last_response']
                advance_ticks=reduction*MASTER/1000
                last=last_rom(cal['ROM_release']-advance_ticks)
                with_rom=first_visible_switch(max(last,bus-advance_ticks))
                out['phases'].append(dict(phase=i,generation=g,wire_before_B=q['wire_floor_B'],
                    short_saved_B=saved,wire_after_B=q['wire_floor_B']-saved,
                    required_saved_B=q['floor_shortfall_B'],short_serial_advance_ms=short_gain,paired_plus_short_advance_ms=reduction,
                    paired_visible_with_ROM_ms=interval(with_rom),before_bus_ms=interval(bus),optimistic_paired_bus_ms=interval(bus)-reduction,
                    optimistic_paired_visible_ms=interval(first_visible_switch(bus-reduction*MASTER/1000)),
                    input_all_overhead_erased_advance_ms=ceiling,wire_only_bus_ms=interval(bus)-ceiling))
            if name=='shared':
                out['guards'][f'{name}-{g}']=dict(input=Receiver(src,bytes(128)).guards(pkts),display=display_guards(src,g,pkts))
            elif name=='short':
                out['guards'][f'{name}-{g}']=short_guards(src,g,pkts)
    for variant in ('legacy','shared','short'):
        d=a.pins/variant
        res=read(d/'result.json')
        assert res['passed']
        out['pin_evidence'][variant]=dict(rtl=sha(d/'nes_native_spi165.sv'),bench=sha(d/'tb.sv'),frames=res['frames'])
        for g in GENERATIONS:
            pin(d/f'transactions-{g}.txt',next(r['wire_SHA256'] for r in res['frames'] if r['generation']==g))
            assert pin_packets(d,g)==pin_packets(a.probe/('legacy' if variant=='legacy' else 'shared'),g)
            def ops(path):
                return [(bytes.fromhex(tx)[0],int(n)) for n,tx,rx in (l.split() for l in path.read_text().splitlines())]
            trace=ops(d/f'transactions-{g}.txt')
            if variant=='short':
                baseline=ops(a.pins/'shared'/f'transactions-{g}.txt')
                assert [op for op,n in trace]==[op for op,n in baseline]
                assert all(n==(4 if op==210 else old_n) for (op,n),(_,old_n) in zip(trace,baseline))
                saved=sum(n-b for (_,n),(_,b) in zip(baseline,trace))
                assert all(r['short_saved_B']==saved for r in out['phases'] if r['generation']==g)
    a.out.write_bytes((json.dumps(out,indent=2)+'\n').encode())
    print(out['phases'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('arm','probe','data','pins','out','short','traces','calendar'):
        p.add_argument('--'+arg,type=Path,required=True)
    main(p.parse_args())
