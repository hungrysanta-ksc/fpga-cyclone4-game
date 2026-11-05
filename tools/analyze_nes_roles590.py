# SPDX-License-Identifier: MIT
"""590 role/round-trip audit. Reference only: no new target timing or area.

Reads hash-pinned private captures; emits numeric evidence, never ROM bytes.
The proposed wire accounting is explicit and is NOT an implemented ABI.
"""
import argparse
import binascii
import hashlib
import json
import random
import struct
import zipfile
from collections import Counter
from pathlib import Path
from statistics import mean

from check_nes_game478 import encode
from nes_abi582 import canonical, crc
from nes_transfer512 import legacy_packets
from analyze_nes_source588 import io_floor

ROOT = Path(__file__).resolve().parents[1]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rowbytes(row):
    assert len(row) == 33 and all(0 <= v < 32768 for v in row)
    return struct.pack('<33H', *row)


def summary(row, shifted=True, triple=False):
    b = rowbytes(row)
    if not shifted:
        return struct.pack('<I', binascii.crc32(b))
    if triple:
        return struct.pack('<IIIHH', binascii.crc32(b), binascii.crc32(b[:-2]),
                           binascii.crc32(b[2:]), row[0], row[-1])
    return struct.pack('<IHH', binascii.crc32(b), row[0], row[-1])


def decision(old, digest, shifted=True, triple=False):
    if old is None:
        return 'full', None
    b = rowbytes(old)
    if binascii.crc32(b) == struct.unpack_from('<I', digest)[0]:
        return 'same', list(old)
    if shifted:
        if triple:
            _, prefix, suffix, first, last = struct.unpack('<IIIHH', digest)
            if binascii.crc32(b[2:]) == prefix:
                return 'left', list(old[1:]) + [last]
            if binascii.crc32(b[:-2]) == suffix:
                return 'right', [first] + list(old[:-1])
        else:
            expected,first,last=struct.unpack('<IHH',digest)
            assert first<32768 and last<32768
            if binascii.crc32(b[2:]+struct.pack('<H',last))==expected:
                return 'left',list(old[1:])+[last]
            if binascii.crc32(struct.pack('<H',first)+b[:-2])==expected:
                return 'right',[first]+list(old[:-1])
    return 'full', None


def old_nonmap(packets):
    """Keep exact577 nonmap records, excluding old BEGIN/META/END/COMMIT.

    Their code and per-record generation fields are NOT reclaimed in budgets.
    """
    meta, raw = [], []
    removed = Counter()
    for p in packets:
        pos = 0
        while pos < len(p):
            tag = int.from_bytes(p[pos:pos+2], 'big')
            kind, idx = tag >> 13, tag & 8191
            width = 8 if kind == 0 and idx & 4096 else (2,1,7,4,7,1,2,8)[kind]
            q = p[pos:pos+4+width]
            assert len(q) == 4+width
            pos += len(q)
            if kind in (0,6):
                removed['map_B'] += len(q)
            elif kind == 7 and idx in (0,1,3,4):
                removed['control_B'] += len(q)
            elif kind == 7 and 0x1000 <= idx < 0x1700:
                raw.append(q)
            else:
                meta.append(q)
    assert sum(map(len,meta+raw)) + sum(removed.values()) == sum(map(len,packets))
    return meta, raw, removed


def phase_packets(phase, records):
    """2B phase/ordinal per D1 payload, <=254B; no record crosses a seal."""
    packets = []
    buf = bytearray()
    for record in records:
        assert len(record) <= 252
        if len(buf) + len(record) > 252:
            packets.append(bytes([phase,len(packets)]) + bytes(buf))
            buf.clear()
        buf += record
    if buf:
        packets.append(bytes([phase,len(packets)]) + bytes(buf))
    assert all(len(p) <= 254 for p in packets)
    return packets


def extra_requests(base, count, driver_us):
    # Each accepted 24B command has an additional 8B D0 confirmation.
    # New command driver is only a sensitivity using old D3 measured mean.
    r = dict(base)
    r['request_roundtrips'] = count
    r['request_wire_B'] = 32*count
    r['calls'] += 2*count
    r['wire_B'] += 32*count
    r['wire_ms'] += 32*count*8/2625000*1000
    r['driver_ms'] += count*(driver_us + EXTRA['0xd0'])/1000
    r['serial_IO_ms'] = r['wire_ms'] + r['driver_ms']
    return r


def trial(arrays, old, meta, raw, g, shifted=True, one_request_per_row=False,
          force_full=False,triple=False):
    n = len(arrays[0])//33
    assert len(arrays[0]) == 33*n and n <= 32
    cold = old is None
    modes, restored, requests, summaries = [], [], [], []
    for i in range(n):
        row = arrays[0][i*33:(i+1)*33]
        prior = old[i*33:(i+1)*33] if old is not None and len(old) >= (i+1)*33 else None
        s = summary(row,shifted,triple)
        mode, result = decision(prior,s,shifted,triple)
        if cold or force_full:
            mode, result = 'full', None
        if mode == 'full':
            requests.append(i)
            result = row
        modes.append(mode)
        restored.extend(result)
        if not cold:
            summaries.append(s)
    assert restored == arrays[0]
    assert crc(canonical([restored])) == crc(canonical([arrays[0]]))
    assert crc(canonical([restored]+arrays[1:])) == crc(canonical(arrays))
    # Exact field sizes for BEGIN/map seal/response seal are documented in590.
    begin = bytes(32)
    map_seal = struct.pack('<HHHH',0x5900,n,crc(canonical([arrays[0]])),g)
    packets = phase_packets(0,[begin]+summaries+[map_seal])
    responses = [struct.pack('<BBHH',0,0,i*33,33)+rowbytes(arrays[0][i*33:(i+1)*33]) for i in requests]
    if one_request_per_row and not cold:
        # Serial ownership prohibits packing replies from different requests.
        for record in responses:
            packets += phase_packets(1,[record,bytes(8)])
        if not responses:
            packets += phase_packets(1,[bytes(8)])
    else:
        packets += phase_packets(1,responses+[bytes(8)])
    packets += phase_packets(2,meta+[bytes(8)])
    packets += phase_packets(3,raw+[bytes(8)])
    packets += phase_packets(4,[bytes(8)])
    # One HELLO every frame, then one REQUEST (including empty bitmap) per warm
    # frame. Cold HELLO requests full rows directly; no warm summary exchange.
    turns = 1 + (max(1,len(requests)) if one_request_per_row else 1) * int(not cold)
    cost = extra_requests(io_floor(packets,EXTRA),turns,EXTRA['0xd3'])
    cost.update(rows=n,full_rows=len(requests),modes=dict(Counter(modes)),
                summary_B=sum(map(len,summaries)),map_reply_B=sum(map(len,responses)),
                phase_packet_counts=dict(Counter(p[0] for p in packets)),
                # Upper bound if all three fingerprints are evaluated, excluding
                # new canonicalCRC16, semantics, reconstruction and driver work.
                ARM_previous_row_CRC32_B=0 if cold else sum(66 if m=='same' or not shifted else (130 if triple else 132) if m=='left' else (194 if triple else 198) for m in modes),
                ARM_previous_row_CRC32_upper_B=0 if cold else n*((194 if triple else 198) if shifted else 66),
                FPGA_summary_CRC32_B=0 if cold else n*(194 if triple else 66),
                FPGA_canonical_CRC16_B=len(canonical(arrays)),
                FPGA_requested_map_requery_values=33*len(requests),
                restored_sha256=sha(canonical([restored])))
    # Repair uses one extra request and full rows under the SAME immutable lease.
    repair = phase_packets(1,[struct.pack('<BBHH',0,0,i*33,33)+rowbytes(arrays[0][i*33:(i+1)*33]) for i in range(n)]+[bytes(8)])
    nr=len(repair);wire=sum(map(len,repair))+19*nr+32
    cost['one_repair_extra_IO_ms']=wire*8/2625000*1000+(nr*sum(EXTRA[k] for k in ('0xd0','0xd1','0xd2'))+EXTRA['0xd3']+EXTRA['0xd0'])/1000
    return cost


class Ownership:
    """Reference invariant model; not RTL/ARM/65816 verification."""
    def __init__(self):
        self.epoch=1;self.serial=0;self.active=None;self.base_valid=False
        self.display_history=7;self.display_pending=None;self.repaired=False;self.needs_EA=False
    def begin(self,serial):
        assert self.active is None and not self.needs_EA and serial == self.serial+1
        self.active=(self.epoch,serial);self.repaired=False
    def request(self,identity,bitmap,n=29):
        assert identity==self.active and bitmap>>n==0 and bitmap>=0
    def repair(self):
        assert self.active and not self.repaired
        self.repaired=True
    def commit(self,identity,crc_ok,coverage_ok,prepared,d2_confirmed):
        assert identity==self.active and crc_ok and coverage_ok and prepared and d2_confirmed
        self.serial=identity[1];self.base_valid=True;self.active=None
        self.display_pending=identity;self.needs_EA=True
    def final_ack(self,identity,coverage,vblank):
        assert identity==self.display_pending and coverage and vblank
        self.display_history=identity;self.display_pending=None
    def ea(self,identity):
        assert self.needs_EA and self.display_pending is None and self.display_history==identity
        self.needs_EA=False
    def stop(self):
        self.epoch+=1;self.serial=0;self.active=None;self.base_valid=False
        self.display_pending=None;self.needs_EA=False


def rejected(fn):
    try:
        fn()
    except AssertionError:
        return True
    raise AssertionError('invalid transition accepted')


def guards():
    results=[]
    for field in range(4):
        s=Ownership();s.begin(1);args=[True]*4;args[field]=False
        assert rejected(lambda:s.commit((1,1),*args)) and not s.base_valid
        results.append('commit prerequisite '+str(field))
    for ident,bitmap in [((2,1),0),((1,0),0),((1,1),1<<29)]:
        s=Ownership();s.begin(1);assert rejected(lambda:s.request(ident,bitmap))
        results.append('request identity/bounds '+str((ident,bitmap)))
    for cut in (0,1,16,32):
        old=list(range(33));partial=[99]*cut+old[cut:]
        s=Ownership();s.begin(1);s.stop()
        assert rejected(lambda:s.commit((1,1),True,True,True,True))
        s.begin(1);mode,value=decision(None,summary(partial))
        assert not s.base_valid and mode=='full' and value is None
        results.append('STOP partial row '+str(cut))
    s=Ownership();s.begin(1);s.repair();assert rejected(s.repair)
    results.append('one repair maximum')
    s=Ownership();s.begin(1);s.commit((1,1),True,True,True,True)
    assert s.base_valid and s.display_history==7
    assert rejected(lambda:s.ea((1,1))) and rejected(lambda:s.begin(2))
    assert rejected(lambda:s.final_ack((1,1),True,False))
    assert rejected(lambda:s.final_ack((1,2),True,True))
    s.final_ack((1,1),True,True);assert s.display_history==(1,1)
    assert rejected(lambda:s.begin(2));s.ea((1,1));s.begin(2)
    results.append('source COMMIT distinct from VBlank final ACK')
    original=list(range(33));bad=list(original);bad[5]^=1
    assert decision(bad,summary(original))[0]=='full'
    results.append('digest recomputed from actual retained RAM')
    # A malicious/stale summary matching old RAM is not a geometry certificate.
    # Fresh canonicalCRC must catch this case BEFORE required-tag publication.
    mode,provisional=decision(original,summary(original))
    assert mode=='same' and crc(rowbytes(provisional))!=crc(rowbytes(bad))
    repaired=list(bad);assert crc(rowbytes(repaired))==crc(rowbytes(bad))
    results.append('false summary fails fresh map CRC; full row repair')
    invalid=struct.pack('<IHH',0,0x8000,0)
    assert rejected(lambda:decision(original,invalid))
    results.append('summary edge 15bit semantic rejection')
    # Right-shift is absent in these captures, so exercise it synthetically.
    for new,mode in [(original,'same'),(original[1:]+[99],'left'),([99]+original[:-1],'right'),([99]*33,'full')]:
        m,v=decision(original,summary(new));assert m==mode and (v==new or m=='full')
        results.append('synthetic decision '+mode)
    return results


def collision():
    rng=random.Random(590);seen={}
    for attempt in range(1,65538):
        row=[rng.randrange(32768) for _ in range(33)];b=rowbytes(row);c=crc(b)
        if c in seen and seen[c]!=b:
            a=seen[c]
            prefix=b'identity590';suffix=b'nonmap590'
            assert crc(prefix+a+suffix)==crc(prefix+b+suffix)
            assert binascii.crc32(a)!=binascii.crc32(b)
            return dict(attempts=attempt,row_A_sha256=sha(a),row_B_sha256=sha(b),
                        same_row_CRC16=True,same_full_stream_CRC16=True,
                        distinct_CRC32=True,CRC32_not_collision_free=True)
        seen[c]=b
    raise AssertionError('collision not found')


def deployed_crc(elf):
    """Execute the ALREADY linked577 CRC32 function, not a new ARM candidate.

    Only the update function is counted. Caller loop/BL and memory wait/IRQ
    cycles are not measured. Shared table is present in the selected image.
    """
    from check_nes_game478 import (ELFFile,Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,
        UC_HOOK_CODE,UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,
        UC_ARM_REG_R1,UC_ARM_REG_XPSR)
    manifest=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())
    assert sha(elf.read_bytes())==manifest['artifacts']['ELF']
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000)
    with elf.open('rb') as f:
        e=ELFFile(f)
        for s in e.iter_segments():
            if s['p_type']=='PT_LOAD' and s['p_filesz']:
                u.mem_write(s['p_vaddr'],s.data())
        syms=e.get_section_by_name('.symtab')
        update=syms.get_symbol_by_name('crc32_update')[0]
        table=syms.get_symbol_by_name('crc32_table')[0]
        entry=update['st_value'];code_B=update['st_size'];table_B=table['st_size']
    end=0x08000000;counts=[];state=0xffffffff;stream=bytearray();count=[0]
    def hook(uc,at,size,ctx):
        if at==end:uc.emu_stop()
        else:count[0]+=1
    u.hook_add(UC_HOOK_CODE,hook)
    for value in range(256):
        count[0]=0
        for reg,v in [(UC_ARM_REG_R0,state),(UC_ARM_REG_R1,value),(UC_ARM_REG_SP,0x2001e000),
                      (UC_ARM_REG_LR,end|1),(UC_ARM_REG_XPSR,0x01000000)]:
            u.reg_write(reg,v)
        u.emu_start(entry|1,end+2,count=1000)
        assert u.reg_read(UC_ARM_REG_PC)==end
        state=u.reg_read(UC_ARM_REG_R0);stream.append(value)
        assert state^0xffffffff==binascii.crc32(stream)
        counts.append(count[0])
    return dict(ELF_sha256=sha(elf.read_bytes()),existing_function_B=code_B,
                existing_table_B=table_B,cases=256,instructions_per_update=sorted(set(counts)),
                new_table_B=0,new_firmware=False,caller_and_cycles_measured=False)


def main():
    global EXTRA
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--arm-elf',type=Path,required=True)
    args=ap.parse_args()
    whole=json.loads((ROOT/'analysis/whole580-verification.json').read_text())
    EXTRA=whole['phases'][0]['parameters']['driver_extra_us']
    body=json.loads((ROOT/'analysis/body581-verification.json').read_text())
    rows=[];old=None
    with zipfile.ZipFile(args.archive) as z:
        for g in range(905,958):
            geom,raw=[z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw')]
            for ext,b in [('geometry',geom),('raw',raw)]:
                assert sha(b)==body['inputs'][f'frame{g}.{ext}']
            arrays=encode(geom,raw,g)[2]+[list(raw)]
            legacy,_,_=legacy_packets(geom,raw,g)
            meta,rawrec,removed=old_nonmap(legacy)
            result=dict(generation=g,baseline=io_floor(legacy,EXTRA),removed_records=dict(removed),retained_nonmap_B=sum(map(len,meta+rawrec)))
            result['fixed_full']=trial(arrays,None,meta,rawrec,g)
            result['same_only']=trial(arrays,old,meta,rawrec,g,shifted=False)
            result['batched_shift']=trial(arrays,old,meta,rawrec,g)
            result['triple_shift']=trial(arrays,old,meta,rawrec,g,triple=True)
            result['per_row_shift']=trial(arrays,old,meta,rawrec,g,one_request_per_row=True)
            result['all_requests']=trial(arrays,old,meta,rawrec,g,force_full=True)
            rows.append(result);old=list(arrays[0])
    groups={}
    for name,selected in [('cold905',rows[:1]),('warm907_957',rows[2:]),('dense951_955',[r for r in rows if 951<=r['generation']<=955])]:
        groups[name]={}
        for variant in ('baseline','fixed_full','same_only','batched_shift','triple_shift','per_row_shift','all_requests'):
            keys=[k for k,v in selected[0][variant].items() if isinstance(v,(float,int))]
            groups[name][variant]={k:mean(r[variant][k] for r in selected) for k in keys}
            groups[name][variant]['saving_IO_ms']=groups[name]['baseline']['serial_IO_ms']-groups[name][variant]['serial_IO_ms']
    c=collision();checks=guards();arm_crc=deployed_crc(args.arm_elf)
    # Keep one copy of per-frame restoration hash and compact variant metrics;
    # detailed cost terms are in group summaries, not repeated 371 times.
    compact=[]
    for row in rows:
        item={k:v for k,v in row.items() if k in ('generation','removed_records','retained_nonmap_B')}
        item['map_sha256']=row['batched_shift']['restored_sha256']
        for variant in ('baseline','fixed_full','same_only','batched_shift','triple_shift','per_row_shift','all_requests'):
            item[variant]={k:v for k,v in row[variant].items() if k in ('payload_B','packets','serial_IO_ms','full_rows','modes')}
        compact.append(item)
    report=dict(stage=590,baseline='MMC577',passed=True,scope='53 hash-pinned reference frames; no target ABI, synthesis or retimed timeline',
                product_changed=False,new_RTL=False,new_ARM=False,new_FIT=False,R3_selected=False,
                frames=compact,groups=groups,reference_guards=checks,CRC16_counterexample=c,existing_ARM_CRC32=arm_crc,
                request_driver_sensitivity_us=EXTRA['0xd3'],
                resources=dict(FPGA_base_removed_vs589_B=2336,FPGA_scratch_candidate_B=66,
                  summary_accumulators_bits=32,canonical_CRC16_bits=16,request_bitmap_bits=32,
                  cached_ARM_fingerprints_B=0,ARM_existing_map_B=2112,ARM_row_scratch_B=66,
                  proposed_ARM_state_ceiling_B=160,ARM_Flash_free_B=84,whole_LE_free=148,
                  guaranteed_net_LE_reclaim=None,ARM_link_cost_B=None,FPGA_new_MAP_LE=None),
                pins=dict(archive_sha256=sha(args.archive.read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),
                          input_manifest_sha256=sha((ROOT/'analysis/body581-verification.json').read_bytes())),
                limitations=['Request driver uses old D3 mean, not measured new opcode; BUSY/IRQ/CRC/semantics/ROM/source waits omitted.',
                'Both old ROM phases have identical input bytes here; no new two-phase scheduling/ACK/display result.',
                'Cold all-row recovery is explicit; repeated integrity failure STOPs. Lost source lease requires a NEW cold capture.',
                'ARM source history must survive BEGIN without resetting old maps and remain separate from display-bank history.',
                'Nonmap577 parser is retained, so old logical1112B cannot be credited as deleted.',
                'CRC32/CRC16 are non-cryptographic error detection, not collision-free independent correctness proofs.'])
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(dict(groups=groups,guards=len(checks),collision=c),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
