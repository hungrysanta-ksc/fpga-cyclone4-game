"""700/701 physical logs and extended699 boundary; do not equate CPU and PPU faults."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
from analyze_nes_supply485_hardware import fields
from analyze_nes_hardware663 import work
from nes_windows518 import windows,duration_ms
from decode_nes_game154 import decode

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
def fault(g):
    c=int(g['fault_context_hi']+g['fault_context_lo'],16)
    d=dict(raw=f'{c:016x}',context_ppu=bool(c>>63),pending_address=(c>>25)&0x3fffff,demand_address=c&0x1ffffff,age=(c>>47)&255)
    d.update({n:bool(c&(1<<(55+i))) for i,n in enumerate(('ppu_valid','cpu_valid','ppu_sample','cpu_sample','rom_response','rom_ready','pending_ppu','busy'))})
    return d

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    previous=read(Path('analysis/hardware697-mmc695-696.json'))['runs'];runs={}
    package=read(Path('analysis/trial700-package.json'))
    for n in (700,701):
        dest=a.out/str(n);dest.mkdir();t={};pins={}
        for k in ('progress','budget','game-last'):
            name=f'nes-{k}-mmc{n}.txt';src=a.downloads/name;dst=dest/name;shutil.copyfile(src,dst)
            assert sha(src)==sha(dst);pins[name]=sha(dst);t[k]=dst.read_text(encoding='utf-8-sig')
        g=fields(t['game-last']);b=fields(t['budget']);elapsed=duration_ms(t['progress']);count=int(g['native_frames'])
        assert g['candidate']==f'NES-MMC{n}'
        assert all(g[k]=='1' for k in ('verified','end_accepted','start_sent','stop_ok','base_restored','safe_to_reload'))
        assert g['menu_state']=='PREPARED_RESET_HELD' and g['loaded_bytes']==g['compared_bytes']=='393216'
        assert all(g[k]=='0' for k in ('verify_error','plan_error','native_receiver_error','native_video_error','trace_aborts','run_stop_error'))
        assert all(b[k]=='0' for k in ('failed_transfers','cost_crc_errors','plan_valid')) and b['boot_reason']=='1'
        assert b['cost_scene_crc32_hex']=='5a04eed7' and b['cost_clock_hz']=='84000000'
        w=windows(t['budget'],elapsed);ref=previous[str(n-5)]
        marks={k:int(v) for k,v in re.findall(r'stage=(\w+).*?elapsed_ms=(\d+)',t['progress'])}
        d=dict(source_SHA256=pins,display=dict(completed=count,seconds=elapsed/1000,fps=count*1000/elapsed),completion_windows=w,
            trimmed_fps=sum(v['displays'] for v in w)/50,
            comparison=dict(reference=n-5,windows=[dict(start_s=c['start_s'],end_s=c['end_s'],previous_fps=o['fps'],current_fps=c['fps'],change_pct=100*(c['fps']/o['fps']-1)) for c,o in zip(w,ref['completion_windows'],strict=True)]),
            terminal={k:g[k] for k in ('run_passed','run_first_error','run_rom_error','native_result','native_generation','native_sink_error','sink_window_error','sink_window_sent','sink_window_retired','plan_sent','plan_end')},
            pending_packets_mod65536=(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535,
            phases={k:((int(b[f'cost_phase_{i:02}'].split(',')[2])<<32)+int(b[f'cost_phase_{i:02}'].split(',')[3]))/84000/count for i,k in enumerate(('receive_ms','plan_supply_ms','output_final_ack_ms'))},
            stop_menu=dict(stop=True,base_restored=True,prepared=True,user_observed_menu=True,stop_to_menu_ms=marks['MENU_PREPARED']-marks['DISPLAY_STOPPED']),
            fault=fault(g),ppu=decode(int(g['ppu_state_hi']+g['ppu_state_lo'],16)))
        if n==700:
            assert g['run_passed']==g['native_result']=='1' and g['run_rom_error']==g['fault_context_valid']=='0'
            assert g['sink_window_error']=='3' and d['pending_packets_mod65536']==1
            _,wr=work(b);d['work_windows']=wr
            d['work_change_vs695']=[dict(start_s=c['start_s'],end_s=c['end_s'],per_frame_pct={k:100*(v/o['per_frame'][k]-1) for k,v in c['per_frame'].items()}) for c,o in zip(wr,ref['work_windows'],strict=True)]
            d.update(classification='60-second deadline; window transfer failed after runtime deadline, not evidence of a mid-play physical SPI fault',
                     visual_issue='User observed one transient shifted/corrupt tile screen. No timestamp/video/frame hash; no sticky ROM/CRC/video fault. Cause unresolved; safety counters do not certify pixels.')
        else:
            assert g['native_result']=='2' and g['run_passed']=='0' and g['run_rom_error']=='1' and g['fault_context_valid']==g['ppu_state_valid']=='1'
            f=d['fault'];assert not f['context_ppu'] and f['cpu_sample'] and not f['cpu_valid'] and not f['pending_ppu'] and f['busy']
            assert f['pending_address']==f['demand_address']==0x3fb34 and f['age']==2
            assert d['ppu']['line']==192 and d['ppu']['dot']==265
            cols=b['columns'].split(',');rows=[dict(zip(cols,[int(x,16) for x in b[f'b{i:02}'].split(',')],strict=True)) for i in range(12)]
            d.update(classification='CPU PRG sample deadline, not prior696 PPU CHR sample deadline. Same user-observed bonus entry; first fault causal arbitration history not logged.',
                     epoch=dict(start_s=int(b['epoch_tick'])/100,frame_starts=sum(x['frames'] for x in rows),bins=rows,first55s_workload_not_retained=True),
                     explicit_user_exit_tested=False,exact_CPU_failure_reproduced=False)
        runs[str(n)]=d
    tests=[]
    for i in range(1,4):
        src=a.temp/f'nes-bonus702-cpu0{i}';m=read(src/'inputs.json');log=(src/'simulation.log').read_text();rows=[]
        assert 'DONE698 actual T65' in log and 'Errors: 0,' in log
        for row in re.findall(r'CASE699CPU ([^\r\n]+)',log):
            kv=dict(re.findall(r'(\w+)=(\S+)',row));rows.append({k:(v if k in ('context','ppu') else int(v)) for k,v in kv.items()})
        assert len(rows)==8 and sum(v['failed'] for v in rows)==2 and all(v['error']==2 for v in rows if v['failed'])
        dst=a.out/f'cpu0{i}';dst.mkdir()
        for name in ('inputs.json','result.json','game147_tb.sv','simulation.log','vlog.log'):shutil.copyfile(src/name,dst/name)
        tests.append(dict(phase_index=i,cases=rows,log_SHA256=sha(src/'simulation.log'),bench_SHA256=sha(src/'game147_tb.sv')))
    sources=a.out/'sources';sources.mkdir();proof=read(Path('analysis/bonus699-verification.json'))['inputs']
    for n in ('nes_rom_service.sv','nes_rom_physical.sv','nes_native_arbiter165.sv','rtl/nes.v','rtl/ppu.sv'):
        src=a.board/n;assert sha(src)==proof['changed'].get(n,proof['base'][n]);dst=sources/n;dst.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(src,dst)
    for n in ('nes_native_runtime165.c','nes_native_runtime165.h','nes_sink_window184.c','nes_native_sink165.c'):
        shutil.copyfile(a.arm/n,sources/n)
    assert sha(a.arm/'obj-nes-100/firmware.stm')==package['variants']['700']['firmware']
    result=dict(stage=702,runs=runs,prior_package='analysis/trial700-package.json',package_SHA256=sha(Path('analysis/trial700-package.json')),
        extended_boundary=dict(cases=24,passed=18,failed=6,error_code=2,PPU_line=192,PPU_dot=264,CHR_address='21fbef',exact701_CPU_fault=False,tests=tests,
            finding='699 stopped at step59/dot263; extending tostep79 found next CHR plane failures. Actual T65/arbiter fixture retained. Does not reproduce physical CPU fault1 atdot265.'),
        decision='Stability fix remains incomplete. Keep699 evidence limited to firstCHR sample, defer output optimization/new installer until CPU+both CHR planes share a verified deadline schedule.',
        source_pins={p.relative_to(sources).as_posix():sha(p) for p in sources.rglob('*') if p.is_file()},
        limitations=['One unsynchronized playthrough per build; work differs; no causal FPS gain.','700 visual corruption has no synchronized pixel trace.','701 final epoch workload cannot explain its early55s completion counts.','No production RTL/firmware changes or FIT/new ZIP; standalone extension not whole-game simulation.'])
    save(a.report,result)
    inventory={p.relative_to(a.out).as_posix():dict(bytes=p.stat().st_size,SHA256=sha(p)) for p in a.out.rglob('*') if p.is_file()}
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
        for name in inventory:z.write(a.out/name,name)
    with zipfile.ZipFile(zpath) as z:
        for n,v in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==v['SHA256']
    save(a.archive_report,dict(stage=702,location='WORKSPACE/probes/nes-hardware702/'+a.out.name,SHA256=sha(zpath),all_bytes_verified=True,inventory=inventory,game_ROM_included=False,license_included=False))
    print(json.dumps({k:dict(display=v['display'],windows=v['completion_windows'],phases=v['phases']) for k,v in runs.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('downloads','temp','board','arm','out','report','archive-report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
