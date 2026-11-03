# SPDX-License-Identifier: MIT
"""Pinned single-block input budget/port ownership reference, not RTL timing.

No new codec: reproduce586 packets using a bounded source-side row/base model.
Only hashes/counts are emitted; captures are read directly from the private ZIP.
"""
import argparse, hashlib, json, math, struct, zipfile
from collections import Counter
from pathlib import Path
from check_nes_game478 import encode
from check_nes_combined586 import packets as reference586
from nes_abi582 import WIDTH, canonical, input_blocks, input_packets
from nes_row583 import restore_rows
from nes_transfer512 import legacy_packets
from analyze_nes_ownership585 import inventory

ROOT = Path(__file__).resolve().parents[1]

def sha(b): return hashlib.sha256(b).hexdigest()

class Source:
    """Proposed NES-owned RAM: base0..2335, shared scratch2336..2559.

    RAM accounting is serialized logical byte accesses. No grant, latency or
    two-clock overlap is assumed. Nonmap run selection uses the frozen reference
    and is explicitly not cycle implemented here.
    """
    def __init__(self):
        self.mem = bytearray(3072); self.valid = False; self.base_count = 0
        self.epoch = 1; self.serial = 0; self.pending = None; self.ops = Counter()
    def read(self, at):
        assert 0 <= at < 2560
        self.ops['read_byte'] += 1
        return self.mem[at]
    def write(self, at, v):
        assert 0 <= at < 2560 and 0 <= v < 256
        self.ops['write_byte'] += 1; self.mem[at] = v
    def word(self, at): return self.read(at) | self.read(at+1) << 8
    def row(self, at, values):
        assert len(values) == 33 and at % 33 == 0
        for i, v in enumerate(values):
            assert v < 32768
            self.write(2336 + 2*i, v & 255); self.write(2337 + 2*i, v >> 8)
        choices = [(72, 0, None)]
        if self.valid and at + 33 <= self.base_count:
            for shift in (0, -1, 1):
                mask = 0
                for i in range(33):
                    v = self.word(2336 + 2*i); j = i + shift
                    old = self.word(2*(at+j)) if 0 <= j < 33 else None
                    mask |= (v != old) << i
                    self.ops['compare_value'] += 1
                choices.append((11 + bool(shift) + 2*mask.bit_count(), shift, mask))
        _, shift, mask = min(choices, key=lambda x:x[0])
        block = bytearray(struct.pack('<BBHH', 0, 0 if mask is None else 4 if shift else 3, at, 33))
        if mask is not None:
            if shift: block += bytes([shift & 255])
            block += mask.to_bytes(5, 'little')
        # All old-row comparisons finish before any in-place base overwrite.
        for i in range(33):
            v = self.word(2336 + 2*i)
            if mask is None or mask >> i & 1: block += v.to_bytes(2, 'little')
            self.write(2*(at+i), v & 255); self.write(2*(at+i)+1, v >> 8)
        return bytes(block)
    def begin(self, serial):
        assert self.pending is None and serial == self.serial + 1
        self.pending = serial; self.ops.clear()
    def make(self, arrays):
        blocks = [self.row(at, arrays[0][at:at+33]) for at in range(0,len(arrays[0]),33)]
        # Rows have a separate fixed base region; source/ARM base identities are
        # still provisional. Tail uses existing582 run/literal selection.
        for at in range(0, len(arrays[1]), 32):
            values = arrays[1][at:at+32]; n = len(values)
            mask = 0
            for i,v in enumerate(values):
                self.write(2336+i,v)
                if self.valid:
                    mask |= (v != self.read(2112+at+i)) << i
                    self.ops['compare_value'] += 1
            delta_size = 6 + (n+7)//8 + mask.bit_count()
            delta = self.valid and delta_size < 6+n
            b = bytearray(struct.pack('<BBHH',1,3 if delta else 0,at,n))
            if delta: b += mask.to_bytes((n+7)//8,'little')
            for i in range(n):
                v=self.read(2336+i)
                if not delta or mask >> i & 1:b.append(v)
                self.write(2112+at+i,v)
            blocks.append(bytes(b))
        blocks += [b for b in input_blocks(arrays,None) if b[0] > 1]
        self.ops['canonical_crc_bytes'] = len(canonical(arrays))
        self.ops['logical_query_values'] = sum(map(len,arrays))
        return blocks
    def commit(self, epoch, serial, count, prepared, commit_queued):
        assert epoch == self.epoch and self.pending == serial and prepared and commit_queued
        self.serial=serial;self.base_count=count;self.valid=True;self.pending=None
    def stop(self):
        # No late completion may publish a partially overwritten source base.
        self.pending=None;self.valid=False;self.base_count=0;self.epoch+=1;self.serial=0

def pack254(arrays,blocks,serial,base):
    controls=input_packets(arrays,[],serial,base)
    p=bytearray(controls[0][:32]);out=[]
    for raw in (False,True):
        for b in blocks:
            if (b[0]==6)!=raw:continue
            if len(p)+len(b)>254:out.append(bytes(p));p.clear()
            p+=b
        tail=controls[1] if raw else controls[0][32:]
        if len(p)+8>254:out.append(bytes(p));p.clear()
        p+=tail;out.append(bytes(p));p.clear()
    out.append(controls[2]);return out

def single_block(packets):
    """One immutable sealed block, one held <=8B mailbox beat; no ready queue.

    Directed finite stalls check byte/retire ownership only, not clock timing.
    A dedicated end-of-packet beat flag is necessary; old record tag sealing is
    removed. Full block retention is tested before read and before POP.
    """
    out=[];max_used=0;stall_checks=0
    for packet in packets:
        block=bytearray();sealed=False
        for at in range(0,len(packet),8):
            beat=packet[at:at+8]
            assert not sealed and len(block)+len(beat)<=256
            for _ in range((at//8)%3):assert bytes(beat)==packet[at:at+8]
            block+=beat;max_used=max(max_used,len(block))
            sealed=at+8>=len(packet)
        snapshot=bytes(block);assert sealed
        for _ in range(5):assert sealed and bytes(block)==snapshot;stall_checks+=1
        read=snapshot
        for _ in range(7):assert sealed and bytes(block)==read;stall_checks+=1
        out.append(read);block.clear();sealed=False
    assert out==packets
    return dict(packets=len(packets),max_used_B=max_used,stall_checks=stall_checks,
                mailbox_beats=sum(math.ceil(len(p)/8) for p in packets))

def io_floor(packets,extra):
    n=len(packets);payload=sum(map(len,packets))
    # One initialD0, D1/D2/confirmD0 per block, D0/D3/D0 PREPARE,
    # and a new D0 after PREPARE. Positive confirm metadata may be reused only
    # while RECEIVING; no BUSY retries or CPU source/CRC work is free evidence.
    wire=payload+19*n+40
    driver=(n*(extra['0xd0']+extra['0xd1']+extra['0xd2'])+4*extra['0xd0']+extra['0xd3'])/1000
    return dict(payload_B=payload,packets=n,calls=3*n+5,wire_B=wire,
                wire_ms=wire*8/2625000*1000,driver_ms=driver,
                serial_IO_ms=wire*8/2625000*1000+driver)

def guards():
    results=[]
    for cut in (0,1,16,32):
        s=Source();s.mem[:66]=bytes(range(66));s.valid=True;s.base_count=33;s.serial=1
        s.begin(2)
        for i in range(cut):s.write(2*i,255)
        s.stop()
        try:s.commit(1,2,33,True,True)
        except AssertionError:pass
        else:raise AssertionError('late commit accepted')
        s.begin(1);b=s.row(0,list(range(33)));assert b[1]==0
        results.append(dict(partial_words=cut,late_commit_rejected=True,next_row_full=True))
    for prepared,queued in ((False,False),(True,False),(False,True)):
        s=Source();s.begin(1)
        try:s.commit(1,1,33,prepared,queued)
        except AssertionError:pass
        else:raise AssertionError('early base publication')
        results.append(dict(prepared=prepared,commit_queued=queued,early_commit_rejected=True))
    # Source may publish after PREPARE+queuedCOMMIT; ARM must still wait for
    # validated COMMIT and confirmed D2. STOP invalidates both namespaces.
    s=Source();s.begin(1);s.commit(1,1,33,True,True)
    assert s.valid
    s.stop();s.begin(1)
    try:s.commit(1,1,33,True,True)
    except AssertionError:pass
    else:raise AssertionError('old epoch after restart')
    assert not s.valid
    results.append(dict(stop_after_source_publish=True,old_epoch_after_restart_rejected=True))
    return results

def fit_inventory(board):
    p=board/'output_files/board.fit.rpt';names=('native_export','native_records','native_spi');rows={}
    for line in p.read_text().splitlines():
        if not line.startswith(';'):continue
        cols=[x.strip() for x in line.split(';')[1:-1]]
        if not cols:continue
        for name in names:
            if cols[0].endswith(':'+name+'|'):
                assert name not in rows
                rows[name]=dict(LE=int(cols[1].split()[0]),FF=int(cols[2].split()[0]),
                                memory_bits=int(cols[4]),M9K=int(cols[5]))
    assert len(rows)==3
    return dict(peers=rows,sum_LE=sum(v['LE'] for v in rows.values()),
                same_boundary_ceiling_LE=sum(v['LE'] for v in rows.values())+148,
                report_sha256=sha(p.read_bytes()),net_reclaim_LE=None)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','arm','board','out'):ap.add_argument('--'+n,required=True,type=Path)
    a=ap.parse_args();body=json.loads((ROOT/'analysis/body581-verification.json').read_text())
    whole=json.loads((ROOT/'analysis/whole580-verification.json').read_text())
    manifest=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())
    assert sha((a.arm/'obj-nes-100/sd2snes.elf').read_bytes())==manifest['artifacts']['ELF']
    assert sha((a.board/'output_files/board.sof').read_bytes())==manifest['artifacts']['SOF']
    for name in ('board.qsf','board.sdc','nes_live_joint.sv','nes_native_export203.sv','nes_native_spi165.sv','nes_native_mailbox165.sv'):
        assert sha((a.board/name).read_bytes())==manifest['FPGA_inputs'][name]['sha256'],name
    s=Source();prior=None;rows=[]
    with zipfile.ZipFile(a.archive) as z:
        for g in range(905,958):
            rawfiles=[z.read('data/frame'+str(g)+ext) for ext in ('.geometry','.raw')]
            for ext,b in zip(('geometry','raw'),rawfiles):assert sha(b)==body['inputs'][f'frame{g}.{ext}']
            geometry,raw=rawfiles;arrays=encode(geometry,raw,g)[2]+[list(raw)]
            s.begin(g-904);blocks=s.make(arrays)
            restored=restore_rows(blocks,list(map(len,arrays)),prior)
            assert canonical(restored)==canonical(arrays)
            new=pack254(arrays,blocks,g-904,g-905 if prior is not None else 0)
            ref=reference586(geometry,raw,g,g-904,prior)
            assert blocks==ref[4] and new==ref[0]
            old=legacy_packets(geometry,raw,g)[0]
            assert len(old)==body['frames'][str(g)]['input']['packet_count']
            assert sum(map(len,old))==body['frames'][str(g)]['input']['body_B']
            row=dict(generation=g,ports=dict(s.ops),single_block=single_block(new),
                     old=io_floor(old,whole['phases'][0]['parameters']['driver_extra_us']),
                     candidate=io_floor(new,whole['phases'][0]['parameters']['driver_extra_us']))
            row['wire_driver_only_saving_ms']=row['old']['serial_IO_ms']-row['candidate']['serial_IO_ms']
            row['ports']['partial_serialized_byte_service_cycle_allocation']=(
                2*s.ops['read_byte']+s.ops['write_byte']+s.ops['canonical_crc_bytes'])
            rows.append(row);s.commit(1,g-904,len(arrays[0]),True,True);prior=arrays
    inv=inventory(a.arm);oldcode=inv['modules']['nes_native165']
    assert oldcode['logical_record']==1112 and oldcode['nes_native165_packet']==1434
    groups={}
    for name,selected in [('warm',[r for r in rows if r['generation']>=907]),('dense',[r for r in rows if 951<=r['generation']<=955])]:
        groups[name]={'frames':len(selected)}
        for side in ('old','candidate'):
            groups[name][side]={key:sum(r[side][key] for r in selected)/len(selected) for key in selected[0][side]}
        groups[name]['wire_driver_only_saving_ms']=sum(r['wire_driver_only_saving_ms'] for r in selected)/len(selected)
        groups[name]['max_serial_RAM_byte_accesses']=max(r['ports']['read_byte']+r['ports']['write_byte'] for r in selected)
        groups[name]['max_partial_serialized_byte_service_cycle_allocation']=max(r['ports']['partial_serialized_byte_service_cycle_allocation'] for r in selected)
        groups[name]['max_canonical_crc_bytes']=max(r['ports']['canonical_crc_bytes'] for r in selected)
        groups[name]['max_logical_queries']=max(r['ports']['logical_query_values'] for r in selected)
    residual=[]
    for p in whole['phases']:
        for name in ('both_banks_initialized','dense_regression'):
            d=p['groups'][name];residual.append(dict(phase=p['phase'],group=name,
                old_noninput_sum_ms=d['ACK']['mean']-d['mean_terms']['source_to_planner_ms'],
                scope='frozen old terms, not retimed lower bound; input-only does not establish60Hz'))
    report=dict(stage=588,passed=True,frames=rows,groups=groups,guards=guards(),fit=fit_inventory(a.board),
        arm=dict(old_packet_and_logical_B=2546,headroom_B=84,replacement_ceiling_B=2630,
                 retained_poll_prepare_B=oldcode['nes_native165_poll']+oldcode['nes_native165_prepare'],
                 direct_executor_actual_B=None,precaller_IRQ_RAM_gap_B=inv['gap_before_callees_IRQ_B']),
        source_RAM=dict(base_B=2336,shared_scratch_B=224,nonmap_lookahead_B=14,used_B=2574,reserved_B=3072,
                        new_M9K_assumption=3,board_M9K_remaining_if_realized=2,
                        mapping='proposed3x1024x8 in one NES clock; inference and ports not synthesized'),
        residual=residual,pins=dict(tool=sha(Path(__file__).read_bytes()),archive=sha(a.archive.read_bytes()),
            arm_elf=sha((a.arm/'obj-nes-100/sd2snes.elf').read_bytes()),
            baseline_manifest=sha((ROOT/'analysis/whole580-manifest.json').read_bytes()),
            helpers={n:sha((ROOT/'tools'/n).read_bytes()) for n in ('nes_row583.py','nes_abi582.py','check_nes_combined586.py','nes_transfer512.py','nes_raw506.py','check_nes_game478.py','analyze_nes_ownership585.py')}),
        limitations=['row/base logical byte-port reference only; nonmap selection uses frozen oracle',
            'CRC bytes/queries/access counts are not cycles; RAM latency, source grant, two clocks, CPU, BUSY polls and IRQ not retimed',
            'Source base after PREPARE+queuedCOMMIT; ARM base after validatedCOMMIT+confirmedD2. Common cancellation/epoch binding not yet RTL implemented',
            'No direct ARM executor, no new RTL/MAP/FIT/STA or product timing; hard budgets are not measured net savings'],
        product_changed=False,R3_selected=False)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps(dict(passed=True,groups=groups,region_LE=report['fit']['sum_LE'],ARM_ceiling_B=2630),indent=2))

if __name__=='__main__':main()
