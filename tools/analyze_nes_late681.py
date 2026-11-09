"""Four same-work replays; separate tile beam eligibility from BG issuance."""
import argparse,hashlib,json
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_output664 import trace
from analyze_nes_bg674 import tile_image
from analyze_nes_frontier536 import contents
from analyze_nes_progress680 import grants
from analyze_nes_idle676 import end_timing
from analyze_nes_handoff678 import input_credit
from analyze_nes_progress679 import unpack
from nes_rom636 import pack


def credit_frontier(folder,g,packets):
    events=[e for e in read(folder/'events.json') if e.get('generation')==g]
    rows=[]
    for p in packets:
        if not ((p['op']==7 and p['section']==0) or (p['section']==2 and p['offset']>=3000) or (p['section']==5 and p['expanded_B']==1100)):continue
        e0=[e for e in events if e.get('opcode')=='0xe0' and e['clock']<=p['start']]
        e8=[e for e in events if e.get('opcode')=='0xe8' and e['clock']<=p['start']]
        q=None
        if e0:
            e=e0[-1];r=bytes.fromhex(e['reply']);accepted=int.from_bytes(r[3:5],'big');retired=int.from_bytes(r[5:7],'big')
            q=dict(clock=e['clock'],flags=r[2],accepted=accepted,retired=retired,used=(accepted-retired)&65535,
                   to_next_issue_ms=ms(p['start']-e['clock']))
        rows.append(dict(packet=p,last_credit=q,last_plan_status=e8[-1] if e8 else None))
    return rows


def plan_frontier(plan):
    return dict(boundaries561=plan['boundaries561'],banks557=[dict(count=x['count'],first=x['first'],
        decoded_SHA256=hashlib.sha256(json.dumps(x['decoded'],sort_keys=True,separators=(',',':')).encode()).hexdigest()) for x in plan['banks557']])


def analyze(a):
    result={}
    for phase in (1,2):
        folders={k:a.traces/v for k,v in [('MMC666',f'nes-ready673-b{phase}'),('680',f'nes-progress680-neighbor{phase}'),
                    ('client',f'nes-late681-client{phase}'),('joint',f'nes-late681-joint{phase}')]}
        if a.zero_arm:folders['zero']=a.traces/f'nes-late681-zero{phase}'
        if a.mapfirst_client:folders['mapfirst']=a.traces/f'nes-late681-mapfirst{phase}'
        ts={k:trace(f,a.traces/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};base=ts['MMC666'];old=ts['680'];rows={}
        for k,f in folders.items():
            c=ts[k]
            assert js[k]['parameters']==js['MMC666']['parameters']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:d['work'] for g,d in c['frames'].items()}=={g:d['work'] for g,d in base['frames'].items()}
            if k in ('client','joint','zero','mapfirst'):
                expected=a.zero_arm if k in ('zero','mapfirst') else a.arm if k=='joint' else a.base_arm
                assert js[k]['firmware_SHA256']==sha(expected/'obj-nes-100/firmware.stm')
                assert js[k]['client_SHA256']==sha((a.mapfirst_client if k=='mapfirst' else a.client)/'sink165.sfc')
            plan=read(f/'obj-phases.json');oldplan=read(folders['680']/'obj-phases.json')
            if k!='MMC666':
                for g,p in oldplan.items():
                    assert [(x['count'],x['first'],x['decoded']) for x in p['banks557']]==[(x['count'],x['first'],x['decoded']) for x in plan[g]['banks557']]
            cpu=csv_groups(f/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
            protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=c['details'][951]['marks']['reveal']['line']<=246,
                interval952=c['intervals'][952]['VBlank']==3,final_wait957=c['intervals'][957]['final_waits']==0)
            delta=c['checked']['dense_mean_ms']-base['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-base['checked']['last_ACK'])
            regress=[g for g in base['intervals'] if c['intervals'][g]['VBlank']>base['intervals'][g]['VBlank']]
            waits=[g for g in base['intervals'] if c['intervals'][g]['final_waits']>base['intervals'][g]['final_waits']]
            rows[k]=dict(protected=protected,dense_mean_ms=c['checked']['dense_mean_ms'],dense_VBlank=c['checked']['dense_VB'],
                last_ACK=c['checked']['last_ACK'],dense_delta_MMC666_ms=delta,last_ACK_delta_MMC666_ms=ack,
                dense_delta_680_ms=c['checked']['dense_mean_ms']-old['checked']['dense_mean_ms'],
                last_ACK_delta_680_ms=ms(c['checked']['last_ACK']-old['checked']['last_ACK']),
                timing_gate=all(protected.values()) and delta<0 and ack<0 and not regress and not waits,
                regressions=regress,new_final_waits=waits,intervals=c['intervals'],wire_B=js[k]['wire_B'],
                first_poll=js[k]['first_packet_poll_masterclock'],input_credit=input_credit(f),
                deadline911={k:one(s911,k) for k in ('load','upload165_entry')},
                details={g:dict(marks=c['details'][g]['marks'],previous_reveal=c['details'][g]['previous_reveal'],
                    packets=c['details'][g]['packets'],early_DMA_B=c['early_DMA_B'][g],
                    idle_grants=grants(f,g,c['details'][g]['packets']),END=end_timing(f,g),plan=plan_frontier(plan[str(g)]),
                    credit_frontier=credit_frontier(f,g,c['details'][g]['packets'])) for g in (956,957)},
                pins={n:sha(f/n) for n in ('joint.json','packets.jsonl','window.csv','events.json','obj-phases.json')})
        result[phase]=rows
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size;info=read(a.client/'build.json');body=(a.client/'body.bin').read_bytes()
    assert flash<=212992 and len(body)<=5984 and info['physical_free_B']>=0
    decoded,_=unpack(body[:info['prefix_B']],pack(body,info['prefix_B']));assert decoded==body
    guards={p.parent.name+'/'+p.name:dict(SHA256=sha(p),result=read(p)) for p in a.guards}
    assert len(guards)==len(a.guards)
    known_arms={sha(p/'obj-nes-100/firmware.stm') for p in (a.arm,a.base_arm,a.zero_arm) if p}
    known_clients={sha(p/'sink165.sfc') for p in (a.client,a.mapfirst_client) if p}
    for entry in guards.values():
        g=entry['result']
        if 'firmware' in g:assert g['firmware'] in known_arms
        for key in ('client','client_SHA256'):
            if key in g:assert g[key] in known_clients
    report=dict(stage=681,phases=result,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),client=sha(a.client/'sink165.sfc'),
        timing_gate={k:all(r[k]['timing_gate'] for r in result.values()) for k in result[1] if k not in ('MMC666','680')},
        Flash_B=flash,Flash_free_B=212992-flash,ARM_data_B=10040,ARM_BSS_B=19544,client_build=info,guards=guards,
        selected_physical='MMC666',new_FIT=False,new_STA=False,
        scope='Actual linked M4/65816 with fixed shared SPI/ROM calendar and instruction allocation, exact same work and pixels. Not live wholeboard/physical FPS. RTL progress endpoint is unchanged680; no FIT/STA inferred.')
    if a.zero_arm:
        image=a.zero_arm/'obj-nes-100/firmware.stm';n=image.stat().st_size;assert n<=212992
        report['zero_ARM']=dict(firmware=sha(image),Flash_B=n,Flash_free_B=212992-n,data_B=10040,BSS_B=19544)
    if a.mapfirst_client:
        info=read(a.mapfirst_client/'build.json');body=(a.mapfirst_client/'body.bin').read_bytes()
        decoded,_=unpack(body[:info['prefix_B']],pack(body,info['prefix_B']));assert decoded==body
        assert info['physical_ROM_B']==5120 and info['physical_free_B']>=0 and len(body)<=5984
        report['mapfirst_client']=dict(client=sha(a.mapfirst_client/'sink165.sfc'),build=info)
    if a.board:
        manifest=read(a.board/'inputs680.json');old=read(Path('analysis/progress680-verification.json'))['board_inputs']
        assert manifest['base']==old['base']
        for n,h in manifest['base'].items():assert sha(a.board/n)==manifest['changed'].get(n,h)
        assert sha(a.board/'sink-program.hex')==sha(a.mapfirst_client/'sink-program.hex')
        for n,h in manifest['changed'].items():
            if n!='sink-program.hex':assert h==old['changed'][n]
        report['board_inputs']=manifest
        if (a.board/'output_files/board.fit.summary').exists():
            from analyze_nes_sender652 import budget
            from analyze_nes_word660 import board_reports
            from analyze_nes_reader661 import inventory
            import re
            b=budget(a.board)
            labs=re.search(r'Total LABs:\s+partially or completely used\s+;\s*(\d+)',(a.board/'output_files/board.fit.rpt').read_text())
            b['LAB']=int(labs[1]) if labs else None
            report.update(new_FIT=True,board=b)
            if (a.board/'output_files/board.sta.summary').exists():
                b['timing']=board_reports(a.board);b['unconstrained']=inventory(a.board);report['new_STA']=True
    report['source_pins']={p.name:sha(p) for p in Path('tools').glob('*681.py')}
    a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps({p:{k:{n:r[n] for n in ('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','dense_delta_680_ms','last_ACK_delta_680_ms','timing_gate','regressions','new_final_waits')} for k,r in rows.items() if k not in ('MMC666','680')} for p,rows in result.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','arm','base-arm','client','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--guards',type=Path,nargs='*',default=[]);p.add_argument('--zero-arm',type=Path);p.add_argument('--mapfirst-client',type=Path);p.add_argument('--board',type=Path);analyze(p.parse_args())
