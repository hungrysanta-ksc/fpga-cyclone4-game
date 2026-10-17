# SPDX-License-Identifier: MIT
"""Bind actual227 C/65816 bytes, fault guards, ARM and routed ROM evidence."""
from pathlib import Path
import argparse,json,struct
from nes_repeat227 import ROOT,BASE,sha,sink


def read(p):return json.loads(p.read_bytes())
def packets(folder):return [p.read_bytes() for p in sorted(folder.glob('req-*.bin'))]
def frames(ps):
    result={};gen=None
    for p in ps:
        if p[0]==1:
            gen=int.from_bytes(p[8:10],'little');assert gen not in result
            result[gen]=[]
        assert gen is not None;result[gen].append(p)
    return result


def normalize(p):
    p=bytearray(p);p[2:4]=bytes(2)
    if p[0]==1:p[16:18]=bytes(2)
    if p[0]==3:p[36:38]=bytes(2)
    return p


def oam(ps):
    out=bytearray(544);seen=bytearray(544);encoded=0;count=0;repeat=0
    for p in ps:
        if p[1]!=4:continue
        op,at,n,expanded=p[0],*struct.unpack('<HHH',p[10:16])
        assert len(p)==16+n and op in [2,4,5,8]
        data=p[16:] if op==2 else p[16:]*(expanded//n)
        assert 0<len(data) and at+len(data)<=544
        assert not any(seen[at:at+len(data)])
        out[at:at+len(data)]=data;seen[at:at+len(data)]=bytes([1])*len(data)
        if op==8:
            assert n==4 and 8<=expanded<=512 and not(at%4 or expanded%4) and at+expanded<=512
            repeat+=1
        encoded+=len(p);count+=1
    assert all(seen)
    return bytes(out),dict(packet_bytes=encoded,packets=count,repeat_packets=repeat)


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True)
    d=p.parse_args().archive.resolve();assert not(d/'manifest01.json').exists()
    src=d/'arm01/src';prep=read(d/'arm01/preparation-repeat227.json')
    for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(d/'arm01'/n)==h,n
    for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
    baseline=BASE/'probes/nes-fast226/arm01/src'
    assert (src/'nes_native_sink165.c').read_text()==sink((baseline/'nes_native_sink165.c').read_text())
    for n in ['nes_planner211.c','nes_resident211.c','nes_native165.c','nes_plan_service200.c',
              'nes_runtime_board165.inc','nes_native_runtime165.c','nes_run136.inc']:
        assert sha(src/n)==sha(baseline/n),n
    snes=read(d/'snes04/result.json');faults=read(d/'snes03/result.json')
    runtime=read(d/'runtime02/result.json');arm=read(d/'check02/result.json')
    assembly=read(d/'asm02/result227.json');rom=read(d/'romcheck01/result.json')
    assert all(v['passed'] for v in [snes,faults,runtime,arm,assembly,rom])
    assert {x['mode'] for x in faults['cases']}==set(['normal','repeat_short','repeat_odd',
        'repeat_section','repeat_period','repeat_overflow','wrong_display_ack','bad_bank','bad_epoch','stop_repeat'])
    assert snes['cases'][0]['commits']==30 and len(snes['cases'])==1
    assert 'exact candidate OAM mismatch' in (d/'snes04/candidate-normal/capture.lua').read_text()
    assert 'frames=9 ' in runtime['results']['runtime']
    assert runtime['results']['runtime'].count('PASS METADATA203 fault=')==6
    assert 'maximum_bytes=3521' in runtime['results']['budget']
    for n,h in runtime['source_hashes'].items():
        assert sha(d/'runtime02'/n)==h,n
        if (src/n).exists():assert sha(src/n)==h,n
    for n in ['nes_native_sink165.c','nes_planner211.c','nes_resident211.c','nes_native165.c']:
        assert sha(d/'snes04/candidate'/n)==sha(src/n),n
        assert sha(d/'snes03/candidate'/n)==sha(src/n),n
    olddir=BASE/'probes/nes-scroll225/snes02/candidate-normal'
    before=frames(packets(olddir));after=frames(packets(d/'snes04/candidate-normal'))
    assert set(before)==set(after)==set(range(1,31))
    rows=[]
    for gen in before:
        old,new=before[gen],after[gen]
        # Except sequence numbering/version and OAM representation, every
        # accepted packet remains byte-identical, including plans/maps/seal.
        assert [normalize(x) for x in old if x[1]!=4]==[normalize(x) for x in new if x[1]!=4],gen
        a,am=oam(old);b,bm=oam(new);assert a==b==(d/f'snes04/candidate-normal/oam-{gen}.bin').read_bytes()
        assert bm['packet_bytes']<=am['packet_bytes'],gen
        assert (d/f'snes04/candidate-normal/frame-{gen}.rgb').read_bytes()==(d/f'snes02/reference-normal/frame-{gen}.rgb').read_bytes()
        rows.append(dict(generation=gen,scroll_fixture=gen>=15,before=am,after=bm,
            before_all_bytes=sum(map(len,old)),after_all_bytes=sum(map(len,new))))
    before_total=sum(x['before_all_bytes'] for x in rows);after_total=sum(x['after_all_bytes'] for x in rows)
    assert before_total==104753 and after_total==88733
    assert sha(d/'snes03/client/sink-program.hex')==sha(d/'snes04/client/sink-program.hex')==assembly['client_sha256']==rom['expected_hex_sha256']
    build=read(d/'snes04/client/build.json');assert build['body_bytes']==3712 and build['body_free']==224
    assert arm['remaining_margin']==1800 and arm['ram_static']==28116 and arm['foreground_bound']==35000
    assert arm['firmware_sha256']==sha(src/'obj-nes-100/firmware.stm')
    assert assembly['new_fit']==False and assembly['fpga_sha256']==sha(d/'asm02/fpga_n227.bi3')
    for n,h in assembly['baseline_pins'].items():assert sha(BASE/'probes/nes-counter224/mapfit02'/n)==h,n
    for n,h in assembly['unchanged_routing_and_sources'].items():
        if n=='board.qsf':continue # EDA may add simulator export settings after ASM.
        assert sha(d/'asm02'/n)==h,n
    q0=(BASE/'probes/nes-counter224/mapfit02/board.qsf').read_text().splitlines()
    q1=(d/'asm02/board.qsf').read_text().splitlines()
    q0=[x.replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"',
                   'LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"') for x in q0]
    assert q1==q0+['',
        'set_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"',
        'set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR simulation/modelsim -section_id eda_simulation',
        'set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation']
    for x in rom['checks']:assert x['matched_bytes']==4096 and sha(d/'asm02/simulation/modelsim'/x['file'])==x['netlist_sha256']
    public=['tools/nes_repeat227.py','tools/test_nes_repeat227_snes.py','tools/test_nes_repeat227_runtime.py',
        'tools/check_nes_repeat227_arm.py','tools/assemble_nes_paired227.py','tools/nes_repeat227_evidence.py']
    gates=['arm01/preparation-repeat227.json','snes03/result.json','snes04/result.json',
        'runtime02/result.json','check02/result.json','asm02/result227.json','romcheck01/result.json']
    result=dict(passed=True,trial_gates_pass=True,physical=False,fps60=False,new_fit=False,new_rom=True,
        selected=dict(arm='arm01',normal='snes04',faults='snes03',runtime='runtime02',check='check02',assembly='asm02',rom='romcheck01'),
        exact=dict(frames=30,pixels=1835520,oam_bytes=30*544,unchanged_non_oam_packets=True,
            source='actual227C -> actual65816; exact544B candidateWRAM atSEAL +186 referenceRGB',
            faults=9,frame_rows=rows),
        wire=dict(before_packet_bytes=before_total,after_packet_bytes=after_total,
            change_percent=(after_total/before_total-1)*100,
            scroll_before=sum(x['before_all_bytes'] for x in rows if x['scroll_fixture']),
            scroll_after=sum(x['after_all_bytes'] for x in rows if x['scroll_fixture']),
            repeat_packets=sum(x['after']['repeat_packets'] for x in rows),
            scope='Synthetic matched scenes, not captured SMB3 play or FPS. Packet bytes exclude E0 polling/CRC/audio/ingress/tile aperture.'),
        arm={k:arm[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin','firmware_sha256']},
        snes=dict(version='2271',body_bytes=3712,free=224,program_bytes=4096,extra_persistent_bytes=0,
            maximum_repeat_bytes=512,service_after_repeat=True),
        baseline=dict(merge='f48017ad7912a436401eabf7604fc6fc4f25dcec',fpga_route='nes-counter224/mapfit02'),
        fpga=dict(new_fit=False,rom_only=True,sha256=assembly['fpga_sha256'],
            client_sha256=assembly['client_sha256'],unchanged_files=len(assembly['unchanged_routing_and_sources']),
            conditional_io_caveat_preserved=True),
        gates={n:sha(d/n) for n in gates},public_sources={n:sha(ROOT/n) for n in public},
        limitations=['This targets repeated OAM tails only; unchanged ingress/map/other metadata still prevents60fps.',
            'MVN adds bounded SNES decode work. Byte savings are not measured CPU/latency/FPS savings; physical scroll acceptance pending.',
            'No new frame RAM/saveSRAM. Version2271 rejects mixed old/new consumers at BEGIN.',
            'Same route timing evidence is reused; ROM atom checks are not physical readback or electrical signoff.'],
        prior_failures=['snes01 sandbox MinGW WinError623','snes02 obsolete stop mode was not injected; host assertion, not product fault',
            'runtime01 harness used video instead of output; compiler rejected it',
            'asm01 Lite edition could not open Standard database; asm02 uses matching Standard with no FIT',
            'evidence01 required exact QSF prefix; evidence02 allows only observed LAST_QUARTUS_VERSION and three exact EDA export settings'],
        next='Paired227 firmware+ROM-only FPGA physical first-level scroll,3TXT/video/audio/input/menu; compare SEAL with226. No same226/044 repetition. If no netgain, do not expand repeat codec: prioritize ingress and metadata/finish structural throughput for16.67ms.')
    (d/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    (ROOT/'analysis/repeat227-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ['passed','wire','arm','snes','fpga']}))


if __name__=='__main__':main()
