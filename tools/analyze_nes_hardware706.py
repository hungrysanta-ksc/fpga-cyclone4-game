"""Separate four704/705 physical runs: startup, BG deadline, successful play and pixels."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
from analyze_nes_supply485_hardware import fields
from analyze_nes_hardware663 import work
from analyze_nes_hardware702 import fault
from decode_nes_game154 import decode
from decode_nes_minreject180 import decode as history
from nes_windows518 import duration_ms,windows

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    package=read(ROOT/'analysis/trial704-package.json');previous=read(ROOT/'analysis/hardware702-mmc700-701.json')['runs'];runs={}
    for n in ('704','705'):
        for attempt,suffix in [(1,'1차_실패'),(2,'2차_성공')]:
            key=f'{n}-{attempt}';d=a.out/key;d.mkdir();t={};pins={}
            for kind in ('progress','budget','game-last'):
                name=f'nes-{kind}-mmc{n}_{suffix}.txt';src=a.downloads/name;dst=d/name
                shutil.copyfile(src,dst);assert sha(src)==sha(dst)
                pins[name]=sha(dst);t[kind]=dst.read_text(encoding='utf-8-sig')
            g=fields(t['game-last']);b=fields(t['budget']);elapsed=duration_ms(t['progress']);count=int(g['native_frames'])
            assert g['candidate']==f'NES-MMC{n}' and g['loaded_bytes']==g['compared_bytes']=='393216'
            assert all(g[k]=='1' for k in ('verified','end_accepted','start_sent','stop_ok','base_restored','safe_to_reload'))
            assert g['menu_state']=='PREPARED_RESET_HELD'
            assert all(g[k]=='0' for k in ('verify_error','run_stop_error','native_receiver_error','plan_error','trace_aborts'))
            marks={k:int(v) for k,v in re.findall(r'stage=(\w+).*?elapsed_ms=(\d+)',t['progress'])}
            cols=b['columns'].split(',');rows=[dict(zip(cols,(int(x,16) for x in b[f'b{i:02}'].split(',')),strict=True)) for i in range(12)]
            item=dict(source_SHA256=pins,display=dict(completed=count,seconds=elapsed/1000,fps=count*1000/elapsed),
                terminal={k:g[k] for k in ('run_passed','run_error','run_first_error','run_rom_error','native_result','native_generation','native_sink_error','native_video_error','sink_window_error','sink_window_sent','sink_window_retired','trace_commits')},
                boot={k:v for k,v in b.items() if k.startswith(('boot_','startup_'))},
                stop_menu=dict(stop=True,base_restored=True,prepared=True,stop_to_menu_ms=marks['MENU_PREPARED']-marks['DISPLAY_STOPPED']),
                pending_packets_mod65536=(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535,
                history=history(t['game-last']),completion_windows=None)
            if attempt==1:
                assert count==0 and b['cost_sampled']=='0' and g['native_transactions']=='0'
                if n=='704':
                    assert b['boot_reason']=='5' and b['boot_ticks']=='500' and b['boot_last_hex']=='01580500'
                    assert g['run_first_error']=='6' and g['run_rom_error']==g['fault_context_valid']=='0'
                    item['classification']='stage0 preparation timeout; same terminal01400500->01580500 signature asMMC690, not703 CPU/CHR fault;05 is invalid SPC telemetry'
                else:
                    assert b['boot_reason']=='2' and b['boot_ticks']=='20' and g['run_rom_error']=='2'
                    f=fault(g);ppu=decode(int(g['ppu_state_hi']+g['ppu_state_lo'],16))
                    assert f['raw']=='e30143c2c221e161' and f['pending_address']==f['demand_address']==0x21e161 and f['age']==2
                    assert f['context_ppu'] and f['ppu_sample'] and f['pending_ppu'] and f['busy'] and not f['ppu_valid'] and not f['rom_response']
                    assert ppu['line']==193 and ppu['dot']==230 and ppu['sprite_fetch']==0
                    item.update(fault=f,ppu=ppu,classification='BG CHR low-plane sample deadline before first display; separate from701 CPU at192:265 and696 sprite at192:262. Causal preceding requests unknown.',exact_reproduction=False)
            else:
                assert b['boot_reason']=='1' and g['run_passed']=='1' and g['run_rom_error']==g['fault_context_valid']=='0'
                assert all(b[k]=='0' for k in ('failed_transfers','cost_crc_errors','cost_transfer_stops'))
                assert b['cost_clock_hz']=='84000000' and b['cost_scene_crc32_hex']=='5a04eed7'
                w=windows(t['budget'],elapsed);ref=previous[str(int(n)-4)]
                item.update(completion_windows=w,trimmed_fps=sum(x['displays'] for x in w)/50,
                    comparison=dict(reference=int(n)-4,windows=[dict(start_s=c['start_s'],end_s=c['end_s'],previous_fps=o['fps'],current_fps=c['fps'],delta_pct=100*(c['fps']/o['fps']-1)) for c,o in zip(w,ref['completion_windows'],strict=True)]))
                phases={}
                for i,k in enumerate(('receive_ms','plan_supply_ms','output_final_ack_ms')):
                    calls,_,hi,lo,maximum=map(int,b[f'cost_phase_{i:02}'].split(','))
                    phases[k]=dict(calls=calls,mean_per_display=((hi<<32)+lo)/84000/count,max_call_ms=maximum/84000)
                item['phases']=phases
                epoch=int(b.get('epoch_tick','0'))/100
                item['retained_bins']=[dict(start_s=epoch+i*5,end_s=epoch+(i+1)*5,raw=x,max_gap_ms=x['maxgap']*10,
                    output_ms_per_completed_in_start_bin=x['seal']*10/x['frames'] if x['frames'] else None) for i,x in enumerate(rows)]
                item['bin_scope']='Frame-start ownership; completed count and phases may straddle boundary; final bin partial; maxgap is measured completion gap, not a scene timestamp or minimum instantaneous FPS.'
                if n=='704':
                    assert g['native_result']=='1' and g['native_video_error']=='7' and g['sink_window_error']=='3'
                    _,wr=work(b);item['work_windows']=wr
                    item['work_change_vs700']=[dict(start_s=c['start_s'],end_s=c['end_s'],per_frame_pct={k:100*(v/o['per_frame'][k]-1) for k,v in c['per_frame'].items()}) for c,o in zip(wr,ref['work_windows'],strict=True)]
                    item['classification']='Normal60s runtime deadline; video7 also represents map-offer callback failure, sink3 transfer callback rejection. First result1 and zero failed SPI/CRC do not prove a mid-play allocation/visual fault; no caller PC to select video7 branch.'
                else:
                    assert g['native_result']=='8' and g['native_video_error']=='0' and g['sink_window_error']=='2'
                    item.update(classification='Explicit693 user-exit path, not ROM/plan fault; pendingSEAL cancelled without finalACK',user_exit_confirmed_by_code=True,
                        bonus_cleared_user_observation=True,first55s_workload_not_retained=True,epoch_start_s=epoch)
                item['visual_scope']='User confirms shifted/corrupt tiles repeated across multiple scenes; recovery duration unspecified. No synchronized screen/VRAM/PPU state at artifact. No sticky ROM/CRC fault is not pixel correctness. Capture reject/recovery has no absolute timestamp.'
            runs[key]=item
    src=a.out/'sources';src.mkdir();sourcepins={}
    for n in ('704','705'):
        root=a.normal if n=='704' else a.long
        assert sha(root/'obj-nes-100/firmware.stm')==package['variants'][n]['firmware']
        for name in ('nes_native_runtime165.c','nes_native_runtime165.h','nes_runtime_board165.inc','nes_sink_window184.c','nes_planner211.c','nes_budget210.c','nes_boot214.h'):
            dst=src/(n+'-'+name);shutil.copyfile(root/name,dst);sourcepins[dst.name]=sha(dst)
    proof=read(ROOT/'analysis/bonus703-verification.json')['inputs']
    for name in ('nes_rom_service.sv','rtl/nes.v','rtl/ppu.sv'):
        p=a.board/name;assert sha(p)==proof['changed'].get(name,proof['base'][name]);dst=src/Path(name).name;shutil.copyfile(p,dst);sourcepins[dst.name]=sha(dst)
    result=dict(stage=706,physical=True,runs=runs,package='analysis/trial704-package.json',package_SHA256=sha(ROOT/'analysis/trial704-package.json'),source_pins=sourcepins,
        decision='703B bonus boundary has one physical successful traversal; not all-startup/graphics signoff. Reproduce705 boot BG deadline, separately trace704 stage0 timeout, then pixel/capture/VRAM consistency before performance tuning. No product change/newFIT/newZIP.',
        limitations=['Four selected attempts are not an estimated population failure rate.','No synchronized identical work or scene timestamp; cannot infer implementation speed regression/gain fromFPS.','Longrun epoch retains240.13s onward work only; first5-55s completion counters persist.','No proof that lowFPS caused tile corruption; independent transfer checks do not validate the source pixels.'])
    save(a.report,result)
    shutil.copyfile(Path(__file__),a.out/Path(__file__).name);shutil.copyfile(a.report,a.out/a.report.name)
    inv={p.relative_to(a.out).as_posix():dict(bytes=p.stat().st_size,SHA256=sha(p)) for p in a.out.rglob('*') if p.is_file()}
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
        for n in inv:z.write(a.out/n,n)
    with zipfile.ZipFile(zpath) as z:
        for n,v in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==v['SHA256']
    save(a.archive_report,dict(stage=706,location='WORKSPACE/probes/nes-hardware706/'+a.out.name,SHA256=sha(zpath),inventory=inv,all_bytes_verified=True,raw_logs=12,game_ROM_included=False,license_included=False))
    print(json.dumps({k:dict(display=v['display'],windows=v['completion_windows'],classification=v['classification']) for k,v in runs.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('downloads','normal','long','board','out','report','archive-report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
