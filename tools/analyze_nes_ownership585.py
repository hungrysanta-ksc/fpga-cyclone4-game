# SPDX-License-Identifier: MIT
"""585 deletion ceilings and buffer/history ownership reference, not firmware."""
import argparse,json,hashlib,math
from pathlib import Path
from check_nes_supply485_arm import ELFFile
from check_nes_hardware494_termination import member_offset
from analyze_nes_body581 import output_decode
from nes_abi582 import input_packets
from nes_row583 import encode_rows,restore_rows
from check_nes_game478 import encode

ROOT=Path(__file__).resolve().parents[1]
CAP={3:512,4:544,5:3418}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))

def inventory(src):
    modules={};structs={}
    for name in ('nes_native165','nes_native_runtime165','nes_plan_service200','nes_sink_window184'):
        p=src/'obj-nes-100'/f'{name}.o'
        with p.open('rb') as f:
            e=ELFFile(f)
            modules[name]={s.name:s['st_size'] for s in e.get_section_by_name('.symtab').iter_symbols()
                           if s['st_info']['type']=='STT_FUNC' and s['st_size']}
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        e=ELFFile(f)
        end=max(s['p_vaddr']+s['p_memsz'] for s in e.iter_segments()
                if s['p_type']=='PT_LOAD' and 0x20000000<=s['p_vaddr']<0x20010000)
        names=('nes_native165','nes_native_video165','nes_resident211','nes_native_runtime165','nes_plan200','nes_sink_window184')
        for cu in e.get_dwarf_info().iter_CUs():
            for d in cu.iter_DIEs():
                a=d.attributes
                if d.tag!='DW_TAG_structure_type' or 'DW_AT_name' not in a or 'DW_AT_byte_size' not in a:continue
                name=a['DW_AT_name'].value.decode()
                if name in names:
                    structs[name]=dict(size_B=a['DW_AT_byte_size'].value,
                        offsets={(c.attributes['DW_AT_name'].value.decode() if 'DW_AT_name' in c.attributes else '__anonymous'):member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'})
    stack={}
    for p in (src/'obj-nes-100').glob('*.su'):
        for line in p.read_text().splitlines():
            loc,n,kind=line.split('\t');fn=loc.rsplit(':',1)[-1]
            if fn in ('native_frames222.isra','native_session165','native_service165','nes_native165_bulk','nes_native_video211_plan','nes_native165_poll','nes_runtime165_step'):
                stack[fn]=int(n)
    return dict(modules=modules,structs=structs,static_end=end,static_B=end-0x20000000,
                stack_frames_B=stack,gap_before_callees_IRQ_B=0x20010000-end-stack['native_frames222.isra'])

def suffix_probe():
    rows=[]
    for cut in range(1,8):
        original=bytearray((i*7+3)&255 for i in range(248));start=4+cut*8;size=(15-cut)*8
        wanted=bytes(original[start:start+size]);real=cut*8+8
        ok={}
        for mode in ('legacy_inplace','naive_padded_inplace','separate_RX'):
            b=original.copy();saved=b[start:start+4]
            b[start:start+4]=bytes(4) # actual E9 trailer occupies the suffix
            if mode!='separate_RX':b[:max(real,52) if mode=='naive_padded_inplace' else real]=bytes(max(real,52) if mode=='naive_padded_inplace' else real)
            b[start:start+4]=saved
            ok[mode]=bytes(b[start:start+size])==wanted
        assert ok['legacy_inplace'] and ok['separate_RX']
        assert ok['naive_padded_inplace']==(cut>=6)
        rows.append(dict(cut=cut,real_transfer_B=real,extra_overwrite_B=max(52-real,0),suffix_preserved=ok))
    return rows

class History:
    """Logical stale-set model; current bytes and bank oracles are test storage.

    This does not detect corruption of retained RAM. Independent expected-bank
    validation remains mandatory; a directed counterexample below demonstrates it.
    """
    def __init__(self):
        self.previous={};self.stale=[set(),set()];self.valid=[False,False]
        self.layout=[None,None];self.previous_layout=None;self.pending=None;self.serial=0;self.epoch=1
    def begin(self,serial,bank,layout,current):
        assert self.pending is None and serial==self.serial+1 and bank in (0,1)
        groups={(k,i//8) for k,i in current}
        dirty={(k,i//8) for (k,i),v in current.items() if self.previous.get((k,i))!=v}
        if layout!=self.previous_layout:dirty|={g for g in groups if g[0]==5}
        for s in self.stale:s.update(dirty)
        self.pending=(serial,bank,layout,groups);self.previous=dict(current);self.previous_layout=layout
    def can_skip(self,k,at,n):
        assert self.pending is not None
        serial,bank,layout,groups=self.pending
        return self.valid[bank] and (k!=5 or self.layout[bank]==layout) and all((k,i//8) not in self.stale[bank] for i in range(at,at+n))
    def ack(self,serial,bank,layout,final,epoch):
        assert epoch==self.epoch and self.pending and self.pending[:3]==(serial,bank,layout) and final
        self.stale[bank].difference_update(self.pending[3]);self.valid[bank]=True;self.layout[bank]=layout
        self.serial=serial;self.pending=None
    def stop(self):
        self.previous={};self.previous_layout=None;self.valid=[False,False];self.pending=None
        self.epoch+=1 # proposed cancel namespace, not an existing hardware claim

def directed():
    h=History();data={(3,i):7 for i in range(16)};rows=[]
    for serial,bank in ((1,0),(2,1),(3,0)):
        h.begin(serial,bank,0,data)
        assert h.can_skip(3,0,16)==(serial==3)
        if serial==3:
            before=(h.serial,h.pending,set(h.stale[bank]))
            for args in ((serial-1,bank,0,True),(serial,1,0,True),(serial,bank,1,True),(serial,bank,0,False)):
                try:h.ack(*args,h.epoch)
                except AssertionError:rows.append('reject_wrong_final_identity_'+str(len(rows)))
                else:raise AssertionError('bad ACK accepted')
                assert before==(h.serial,h.pending,set(h.stale[bank]))
        h.ack(serial,bank,0,True,h.epoch)
    # A partial write/STOP cannot publish stale clear. Same bytes still go cold.
    h.begin(4,1,0,data);h.stop();h.begin(4,1,0,data);assert not h.can_skip(3,0,16)
    rows.append('STOP_partial_cold')
    try:h.ack(4,1,0,True,h.epoch-1)
    except AssertionError:rows.append('reject_late_pre_STOP_ACK')
    else:raise AssertionError('cancelled namespace accepted')
    h.ack(4,1,0,True,h.epoch)
    # Layout is part of section5 identity even if the payload happens to match.
    x={(5,i):7 for i in range(16)}
    h.begin(5,1,1,x);assert not h.can_skip(5,0,16);h.ack(5,1,1,True,h.epoch)
    h.begin(6,1,2,x);assert not h.can_skip(5,0,16);h.ack(6,1,2,True,h.epoch);rows.append('layout_change_full')
    h.begin(7,1,2,x);assert h.can_skip(5,0,16)
    corrupt_bank=dict(x);corrupt_bank[(5,0)]^=1
    assert h.can_skip(5,0,16) and corrupt_bank!=x
    rows.append('counterexample_mask_alone_misses_bank_corruption')
    return rows

def trace_audit(path):
    grouped={}
    for line in path.read_text().splitlines():
        b=bytes.fromhex(json.loads(line)[2]);g=int.from_bytes(b[8:10],'little');grouped.setdefault(g,[]).append(b)
    result={}
    for mode in ('hybrid_full','existing_prefix_only'):
        tracker=History();banks=[{},{}];rows=[]
        for serial,(g,packets) in enumerate(grouped.items(),1):
            bank=int.from_bytes(packets[0][18:20],'little');layout=int.from_bytes(packets[-1][38:40],'little')
            work=[];current={}
            for b in packets:
                k=b[1]
                if b[0] not in (2,4,5,8) or k not in CAP:continue
                at=int.from_bytes(b[10:12],'little');v=output_decode(b);assert at+len(v)<=CAP[k]
                for i,x in enumerate(v):assert (k,at+i) not in current;current[k,at+i]=x
                work.append((k,at,v,len(b)+3))
            tracker.begin(serial,bank,layout,current);saved=exact=0;omitted=[];exact_ranges=[]
            carriers=[];exact_carriers=[]
            for b in packets:
                if b[0] in (2,4,5,8) and b[1] in (2,3,4,5):continue
                carriers.append(len(b)+3);exact_carriers.append(len(b)+3)
            for k,at,v,wire in work:
                same=all(banks[bank].get((k,at+i))==x for i,x in enumerate(v))
                if same and (k!=5 or tracker.layout[bank]==layout):exact+=wire;exact_ranges.append((k,at,len(v)))
                else:exact_carriers.append(wire)
                eligible=mode=='hybrid_full' or k!=5 or at+len(v)<=1121
                skip=eligible and tracker.can_skip(k,at,len(v))
                if skip:
                    assert same,'false omission';saved+=wire;omitted.append((k,at,len(v)))
                else:
                    carriers.append(wire)
                    for i,x in enumerate(v):banks[bank][k,at+i]=x
            assert all(banks[bank].get(key)==value for key,value in current.items())
            # Declaration has the same5827B range/8B context+19B wire cost.
            ranges=[]
            for k,at,n in sorted(omitted):
                if ranges and ranges[-1][0]==k and ranges[-1][1]+ranges[-1][2]==at:
                    a,b,c=ranges.pop();ranges.append((a,b,c+n))
                else:ranges.append((k,at,n))
            declaration=27+7*len(ranges) if ranges else 0
            if declaration:carriers.append(declaration)
            er=[]
            for k,at,n in sorted(exact_ranges):
                if er and er[-1][0]==k and er[-1][1]+er[-1][2]==at:
                    x,y,z=er.pop();er.append((x,y,z+n))
                else:er.append((k,at,n))
            if er:exact_carriers.append(27+7*len(er))
            tracker.ack(serial,bank,layout,True,tracker.epoch)
            rows.append(dict(generation=g,bank=bank,layout=layout,active_B=len(current),
                raw_shadow_used_B=sum(k==5 and i>=1121 for k,i in current),omitted_wire_B=saved,
                exact_two_bank_omitted_wire_B=exact,declaration_wire_B=declaration,net_saved_wire_B=saved-declaration,
                carrier_count=len(carriers),exact_carrier_count=len(exact_carriers),
                padded_carrier_B=sum(max(n,52) for n in carriers),exact_padded_carrier_B=sum(max(n,52) for n in exact_carriers),
                omitted_packets=len(omitted),ranges=len(ranges)))
        assert len(rows)==53
        dense=[r for r in rows if 951<=r['generation']<=955]
        result[mode]=dict(rows=rows,dense={k:sum(r[k] for r in dense)/5 for k in ('omitted_wire_B','declaration_wire_B','net_saved_wire_B','exact_two_bank_omitted_wire_B')},
            max_raw_shadow_used_B=max(r['raw_shadow_used_B'] for r in rows))
    return result

def input_audit(data,traces):
    pinned=read(ROOT/'analysis/body581-verification.json');prior=read(ROOT/'analysis/row583-verification.json')
    previous=None;rows=[]
    for g in range(905,958):
        gp=data/f'frame{g}.geometry';rp=data/f'frame{g}.raw'
        assert sha(gp)==pinned['inputs'][gp.name] and sha(rp)==pinned['inputs'][rp.name]
        _,_,arrays=encode(gp.read_bytes(),rp.read_bytes(),g);arrays+=[list(rp.read_bytes())]
        blocks=encode_rows(arrays,previous);assert restore_rows(blocks,list(map(len,arrays)),previous)==arrays
        # Same582 BEGIN/META_END/END/COMMIT and583 blocks; only the combined
        # transport's hard254B payload ceiling is applied, not an opcode sweep.
        controls=input_packets(arrays,[],g-904,g-905)
        assert list(map(len,controls))==[40,8,8]
        packets=[];pending=bytearray(controls[0][:32])
        for raw in (False,True):
            for b in blocks:
                if (b[0]==6)!=raw:continue
                assert len(b)<=254
                if len(pending)+len(b)>254:packets.append(bytes(pending));pending.clear()
                pending+=b
            tail=controls[1] if raw else controls[0][32:]
            if len(pending)+len(tail)>254:packets.append(bytes(pending));pending.clear()
            pending+=tail;packets.append(bytes(pending));pending.clear()
        packets.append(controls[2]);assert max(map(len,packets))<=254
        old=next(r for r in prior['frames'] if r['generation']==g)
        # Actual58436B head + DD5B overhead; DE replaces the COMMIT head,
        # DF adds36B. Busy and actual queue queries are NOT projected as zero.
        wire=sum(map(len,packets))+41*len(packets)+36
        row=dict(generation=g,packets=len(packets),payload_B=sum(map(len,packets)),max_DD_B=max(map(len,packets))+5,
            input_success_wire_B=wire,old583_variable_success_wire_B=old['input_variable_fetch_wire_B'],phases={})
        for p in ('1','2'):
            h=next(x for x in traces[p]['hybrid_full']['rows'] if x['generation']==g)
            oldcase=old['phases'][p]['cases']['C']['variable_two_transfers_three_queries']
            delta=wire-old['input_variable_fetch_wire_B']+h['padded_carrier_B']-h['exact_padded_carrier_B']
            row['phases'][p]=dict(optimistic_three_query_wire_B=oldcase['wire_B']+delta,
                wire_delta_from583_B=delta,additional_source_calls=2*(len(packets)-old['input_packets']),
                additional_output_calls=h['carrier_count']-h['exact_carrier_count'],
                caveat='3queries and noBUSY sensitivity only; no new schedule/driver/processing time')
        rows.append(row);previous=arrays
    return rows

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    base=inventory(a.base);prototype=inventory(a.prototype)
    assert base['modules']['nes_native165']['nes_native165_packet']==1434
    assert prototype['modules']['nes_plan_service200']['read509']==166
    assert base['modules']['nes_native165']['logical_record']==1112
    old=read(ROOT/'analysis/transport584-verification.json')
    assert sha(a.base/'obj-nes-100/firmware.stm')==old['baseline_firmware_SHA256']
    assert sha(a.prototype/'obj-nes-100/firmware.stm')==old['firmware_SHA256']
    for name,digest in old['patch']['baseline'].items():assert sha(a.base/name)==digest
    for name,digest in old['patch']['patched'].items():assert sha(a.prototype/name)==digest
    ceiling=old['deployment_capacity_B']-old['firmware_B']+1434+166-248
    assert ceiling==992
    groups=sum(math.ceil(n/8) for n in CAP.values());masks=2*math.ceil(groups/8)
    assert groups==560 and masks==140
    # All new buffers aligned individually; this is reservation, not compiler layout.
    aligned=lambda n:(n+3)&~3
    hybrid=aligned(3418-1121)+aligned(masks)+aligned(259)+aligned(8)
    evidence=read(ROOT/'analysis/whole580-verification.json');traces={}
    for i in (1,2):
        p=a.traces/f'nes-close561-run{i}/packets.jsonl'
        assert sha(p)==evidence['phases'][i-1]['evidence']['packets.jsonl']
        traces[str(i)]=dict(SHA256=sha(p),**trace_audit(p))
    prior582=read(ROOT/'analysis/abi582-verification.json')
    for p in ('1','2'):
        for row in traces[p]['hybrid_full']['rows']:
            oldframe=next(x for x in prior582['frames'] if x['generation']==row['generation'])
            assert row['exact_two_bank_omitted_wire_B']==oldframe['reuse'][p]['omitted_wire_B']
    inputs=input_audit(a.data,traces)
    pins=('nes_native165.c','nes_native165.h','nes_native_runtime165.c','nes_runtime_board165.inc','nes_native165_bulk.inc','nes_dma182.inc',
          'nes_sink_window184.c','nes_plan_service200.c','nes_plan_service200.h','nes_planner211.c','nes_native_sink165.c')
    result=dict(stage=585,passed=True,scope=__doc__,R3_selected=False,product_changed=False,
        baseline=base,prototype584=prototype,source_pins={n:sha(a.base/n) for n in pins},tool_SHA256=sha(Path(__file__)),
        evidence_pins={n:sha(ROOT/n) for n in ('analysis/transport584-verification.json','analysis/body581-verification.json',
            'analysis/row583-verification.json','analysis/abi582-verification.json','analysis/whole580-verification.json',
            'tools/nes_row583.py','tools/nes_abi582.py','tools/analyze_nes_body581.py','tools/check_nes_game478.py')},
        binary_pins={label:{n:sha(src/'obj-nes-100'/n) for n in ('firmware.stm','sd2snes.elf','nes_native165.o',
            'nes_plan_service200.o','nes_native_runtime165.o','nes_sink_window184.o','nes_h1_stm32.su')}
            for label,src in [('577',a.base),('584',a.prototype)]},
        input_body_flash_budget=dict(remove_packet_envelope_B=1434,retain_logical_record_B=1112,retain_require_tile_B=68,
          remove_plan_adapter_ceiling_B=166,add_row583_B=248,new_remaining_code_ceiling_B=ceiling,
          caveat='992B is an algebraic ceiling, not measured net deletion; includes new sections/controls/CRC/base/direct consumers/RX changes'),
        storage=dict(full_two_bank_history_B=8948,group_count=groups,two_stale_masks_B=masks,raw_shadow_max_B=2297,
          shared_RX_B=259,chunk_scratch_B=8,hybrid_reserved_aligned_B=hybrid,
          before_callers_IRQ_identity_integrity_B=prototype['gap_before_callees_IRQ_B']-hybrid,
          caveat='No free video history: planner clears it. Prefix must compare final chunks before overwrite; raw union requires separate shadow. Independent integrity/metadata/IRQ not included.'),
        E9_suffix=suffix_probe(),history_reference=traces,directed=directed(),combined_input=inputs,
        no_new_ARM_build=True,no_new_FPGA_FIT=True,new_display_interval_ms=None,
        limits=['stale mask reference is not ARM planner/SNES integration','bank oracle is test-only, not target storage',
          'No retained corruption proof; explicit counterexample requires independent expected integrity',
          'No new IRQ/ROM/VBlank/menu or two-slot RTL tests','Flash992B ceiling and RAM residual are not feasibility signoff'])
    (a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(flash_ceiling_B=ceiling,storage=result['storage'],dense={p:{m:traces[p][m]['dense'] for m in ('hybrid_full','existing_prefix_only')} for p in traces})))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','prototype','traces','data','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
