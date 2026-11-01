# SPDX-License-Identifier: MIT
"""Analyze one unaligned hardware run; distinguish tile supply from on-screen enemy counts."""
import argparse
import json
import re
import struct
from pathlib import Path
from analyze_nes_supply485_hardware import fields, sha
from audit_nes499 import capture_evidence
from check_nes_hardware494_termination import SealDeadline

ROOT=Path(__file__).resolve().parents[1]

def begin_probe(src,g):
    """Exercise the linked BEGIN with an empty window and a previously displayed bank."""
    rows=[]
    for expired in (False,True):
        m=SealDeadline(src,'normal')
        count=int(g['native_frames']);serial=count+1;gen=int(g['trace_generation'])
        sent=int(g['sink_window_sent'])
        for kind,addr,values in [
            ('nes_native_sink165',m.s,[('state',0,1),('displayed',1,1),('serial',count,4)]),
            ('nes_resident211',m.resident,[('open',1,1),('prepared',0,1),('displayed',1,1),
                                            ('serial',serial,4),('generation',gen,2),('target',count&1,1)]),
            ('nes_sink_window184',m.w,[('sent',sent,2),('retired',sent,2),('status_flags',2,1),
                                       ('ack_status',1,1),('ever_sent',1,1)]),
            ('nes_native_runtime165',m.rt,[('frames',count,4)])]:
            for name,value,size in values:m.put(addr,kind,name,value,size)
        # The last SEAL's exact sequence is not recorded. Give the mocked
        # prior acknowledged head and its independent status reply the same identity.
        m.last=struct.pack('<BBHIH',3,0,0,count,int(g['native_generation']))
        m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],m.last)
        m.accepted=sent;m.expired=expired;m.calls.clear()
        ok=m.call('nes_sink212_begin',[m.s,m.resident])
        errors=[m.get(m.rt,'nes_native_runtime165','result'),m.get(m.w,'nes_sink_window184','error'),
                m.get(m.s,'nes_native_sink165','error')]
        assert bool(ok)==(not expired) and errors==([1,2,2] if expired else [0,0,0])
        assert m.get(m.rt,'nes_native_runtime165','frames',4)==count
        if expired:
            assert not m.calls
            trace=bytes(m.u.mem_read(m.data_symbols['nes_sink_trace168'],32))
            assert trace[4:20].hex()==g['sink_trace_request_hex'] and trace[20:]==bytes(12)
        rows.append(dict(deadline_injected=expired,begin_accepted=bool(ok),errors=errors,new_E1=sum(s[:2]=='e1' for s in m.calls)))
    return rows

def analyse(a):
    base=json.loads((ROOT/'analysis/hardware510-mmc509.json').read_text())['runs'][0]
    package=json.loads((ROOT/'analysis/window516-package.json').read_text())
    files={k:a.raw/f'nes-{k}-mmc516.txt' for k in ('budget','progress','game-last')}
    g,b=(fields(files[k].read_text(encoding='utf-8-sig')) for k in ('game-last','budget'))
    for k,v in dict(candidate='NES-MMC516',board_seen='1',board_expected_hex='7b',board_observed_hex='7b',
                    verified='1',verify_error='0',loaded_bytes='393216',compared_bytes='393216',start_sent='1',run_passed='1',
                    run_error='0',run_rom_error='0',stop_ok='1',base_restored='1',safe_to_reload='1',native_receiver_error='0',
                    native_video_error='0',plan_error='0',fault_context_valid='0').items():assert g[k]==v,(k,g[k])
    assert b['bin_basis']=='FRAME_START_NOT_SCENE' and b['cost_scene_crc32_hex']==package['required_ROM']['CRC32']
    assert b['cost_counter_available']=='1' and b['cost_clock_hz']=='84000000' and b['bin_ticks']=='500' and b['tick_ms']=='10'
    assert all(int(b[k])==0 for k in ('failed_transfers','cost_transfer_stops','cost_crc_errors'))
    pp=files['progress'].read_text(encoding='utf-8-sig')
    marks=re.findall(r'MMC516 seq=(\d+) stage=(\w+).*?elapsed_ms=(\d+)',pp)
    assert [int(seq) for seq,_,_ in marks]==list(range(len(marks)))
    assert [int(t) for _,_,t in marks]==sorted(int(t) for _,_,t in marks)
    stages={k:int(v) for _,k,v in marks};assert marks[-1][1]=='MENU_PREPARED'
    elapsed=(stages['DISPLAY_STOPPED']-stages['DISPLAY_NEXT'])/1000
    n=int(g['native_frames']);bins=[]
    for i in range(12):
        cols=b['columns'].split(',');vals=[int(x,16) for x in b[f'b{i:02}'].split(',')]
        assert len(vals)==len(cols)
        r=dict(zip(cols,vals));f=r['frames']
        # Each accepted plan produces either 32 OBJ bytes or 16 other bytes.
        obj,remainder=divmod(r['out']-16*r['plans'],16)
        assert not remainder and 0<=obj<=r['plans'] and f>0
        bins.append(dict(index=i,frame_start_s=i*5,frames=f,nominal_fps=f/5,
                         max_gap_ms=10*r['maxgap'],ticks_ms_per_display={k:10*r[k]/f for k in ('recv','plan','finish_ticks','seal')},
                         OBJ_jobs=obj,other_jobs=r['plans']-obj,OBJ_jobs_per_display=obj/f,plan_bytes_per_display=r['out']/f,
                         map_dirty_rows_per_display=r['mapdirty']/f,raw=r))
    assert sum(r['frames'] for r in bins)==n
    e8_calls,e8_bytes,*_=map(int,b['cost_op_06'].split(','))
    assert e8_bytes==20*e8_calls==sum(w['raw']['e8'] for w in bins)
    for w in bins:
        assert w['raw']['e8']%20==0
        w['E8_polls_per_display']=w['raw']['e8']/20/w['frames']
    previous_obj=sum((r['out']-16*r['plans'])//16 for r in base['bins'])/base['display']['completed']
    phases={}
    for i,key in enumerate(('receive','plan_supply','seal_final_ACK')):
        calls,_,hi,lo,peak=map(int,b[f'cost_phase_{i:02}'].split(','))
        phases[key]=dict(calls=calls,ms=((hi<<32)|lo)/84000/n,previous_ms=base['DWT_phases_nested'][key]['ms_per_completed_display'])
    assert int(g['trace_commits'])==int(g['trace_begins'])==int(g['trace_ends'])==n+1 and int(g['trace_aborts'])==0
    assert sha(a.arm/'obj-nes-100/firmware.stm')==package['firmware_SHA256']
    assert 60<=elapsed<60.2 and g['native_result']=='1' and g['sink_window_error']==g['native_sink_error']=='2'
    assert g['sink_window_sent']==g['sink_window_retired'] and int(g['sink_window_sent'])==int(b['cost_op_05'].split(',')[0])%65536
    assert g['sink_window_flags']=='2' and g['sink_window_ack']=='1' and g['sink_trace_ack_valid']=='0' and g['sink_trace_ack_hex']=='0'*24
    previous=base['display']
    return dict(trial=516,trial_family='MMC',hardware_run_passed=True,physical=True,scope='Single unaligned play session. Five-second bins use ARM frame start; no enemy count, game-state advancement, video or scene timestamps.',
                user_observation='Normal execution and menu return, perceived improvement; slowdown reported in busy enemy scenes.',
                source_SHA256={f.name:sha(f) for f in files.values()},package_firmware_SHA256=package['firmware_SHA256'],
                firmware_hash_from_hardware=False,display=dict(completed=n,seconds=elapsed,fps=n/elapsed,mean_ms=elapsed*1000/n),
                OBJ_jobs_per_display=sum(w['OBJ_jobs'] for w in bins)/n,previous_OBJ_jobs_per_display=previous_obj,
                baseline509=previous,whole_run_fps_delta_percent=(n/elapsed/previous['fps']-1)*100,phases=phases,bins=bins,
                capture=capture_evidence(files['game-last'].read_text()),terminal=dict(commits=int(g['trace_commits']),last_display_s=int(g['profile_last_display_tick'])*.01,
                request=g['sink_trace_request_hex'],sent=int(g['sink_window_sent']),retired=int(g['sink_window_retired']),flags=int(g['sink_window_flags']),
                model_BEGIN_cases=begin_probe(a.arm,g),physical_final_instant_replayed=False),
                decision='MMC516 is hardware-functional. Preserve MMC509 as comparison baseline. Prioritize dense OBJ supply/END and output measurements using matched gameplay.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('raw','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=analyse(a);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(r['display'],r['phases'],r['terminal'])
