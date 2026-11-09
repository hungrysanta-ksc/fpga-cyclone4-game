"""Analyze695 control and696 long-session PPU deadline fault without pooling epochs."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
from analyze_nes_supply485_hardware import fields
from analyze_nes_hardware663 import work
from nes_windows518 import windows,duration_ms
from decode_nes_game154 import decode as ppu_decode
from decode_nes_minreject180 import decode as history_decode

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    old=load(Path('analysis/hardware691-mmc690.json'));pack=load(Path('analysis/trial695-package.json'))
    integrated=load(Path('analysis/longrun694-verification.json'))
    assert sha(a.arm/'obj-nes-100/firmware.stm')==pack['variants']['696']['firmware']
    baseline=load(Path('analysis/hardware667-mmc666.json'));runs={};inventory={}
    for trial,suffix in [(695,'-1차60초'),(696,'')]:
        raw=a.out/str(trial);raw.mkdir();texts={};pins={}
        for kind in ('progress','budget','game-last'):
            source=a.downloads/f'nes-{kind}-mmc{trial}{suffix}.txt';dest=raw/f'nes-{kind}-mmc{trial}.txt'
            shutil.copyfile(source,dest);assert sha(dest)==sha(source)
            texts[kind]=dest.read_text(encoding='utf-8-sig');pins[dest.name]=sha(dest)
        g,b=fields(texts['game-last']),fields(texts['budget']);p=texts['progress'];elapsed=duration_ms(p);n=int(g['native_frames'])
        assert g['candidate']==f'NES-MMC{trial}' and all(g[k]=='1' for k in ('verified','end_accepted','start_sent','stop_ok','base_restored','safe_to_reload'))
        assert g['loaded_bytes']==g['compared_bytes']=='393216' and g['verify_error']=='0'
        assert g['menu_state']=='PREPARED_RESET_HELD' and b['boot_reason']=='1'
        assert all(b[k]=='0' for k in ('failed_transfers','cost_crc_errors','plan_valid'))
        assert int(b['cost_transfer_stops'])==int(trial==695)
        assert g['plan_error']==g['native_video_error']==g['trace_aborts']==g['run_stop_error']=='0'
        assert b['cost_clock_hz']=='84000000' and b['cost_scene_crc32_hex']=='5a04eed7'
        split=windows(texts['budget'],elapsed)
        comparisons={}
        for name,ref in [('MMC690',old),('MMC666',baseline)]:
            comparisons[name]={'windows':[dict(start_s=c['start_s'],end_s=c['end_s'],reference_fps=o['fps'],fps=c['fps'],change_pct=100*(c['fps']/o['fps']-1)) for c,o in zip(split,ref['completion_windows'],strict=True)],
                'trimmed_fps':sum(c['displays'] for c in split)/50,'trimmed_change_pct':100*((sum(c['displays'] for c in split)/50)/ref['trimmed_fps']-1)}
        phase={}
        for i,key in enumerate(('receive','plan_supply','output_final_ack')):
            calls,byte,hi,lo,mx=map(int,b[f'cost_phase_{i:02}'].split(','))
            phase[key]={'calls':calls,'ms_per_completed_display':((hi<<32)+lo)/84000/n,'max_ms':mx/84000}
        marks={k:int(t) for k,t in re.findall(r'stage=(\w+).*?elapsed_ms=(\d+)',p)}
        common={'source_SHA256':pins,'display':{'completed':n,'seconds':elapsed/1000,'fps':n*1000/elapsed},'completion_windows':split,'comparison':comparisons,'phases':phase,
            'terminal_fields':{k:g[k] for k in ('run_passed','run_first_error','run_rom_error','native_result','native_generation','native_receiver_error','native_sink_error','native_video_error','sink_window_sent','sink_window_retired','sink_window_error','plan_sent','plan_end')},
            'history':history_decode(texts['game-last']),'stop_and_menu':{'stop_ok':True,'base_restored':True,'user_observed_menu':True,'stop_to_menu_ms':marks['MENU_PREPARED']-marks['DISPLAY_STOPPED']},
            'pending_packets_mod65536':(int(g['sink_window_sent'])-int(g['sink_window_retired']))&65535,
            'transfer_stops':int(b['cost_transfer_stops']),'CRC_errors':int(b['cost_crc_errors']),
            'profile_last_display_s':int(g['profile_last_display_tick'])/100}
        if trial==695:
            assert g['run_passed']==g['native_result']=='1' and g['run_rom_error']==g['fault_context_valid']=='0'
            assert g['native_sink_error']==g['sink_window_error']=='0' and g['native_receiver_error']=='23'
            assert common['pending_packets_mod65536']==0
            rows,wr=work(b);assert sum(r['frames'] for r in rows)==n
            common.update(work_windows=wr,work_change_vs690=[{'start_s':c['start_s'],'end_s':c['end_s'],'per_display_change_pct':{k:100*(v/o['per_frame'][k]-1) for k,v in c['per_frame'].items()}} for c,o in zip(wr,old['work_comparison']['690'],strict=True)],
                classification='60-second deadline completion; receiver23 is terminal input guard rejection, not a mid-run ROM/SPI fault; pending output0',same_code_as_MMC690=True)
        else:
            assert g['run_passed']=='0' and g['native_result']=='2' and g['run_first_error']=='1' and g['run_rom_error']=='2'
            assert g['fault_context_valid']==g['ppu_state_valid']=='1'
            c=int(g['fault_context_hi']+g['fault_context_lo'],16)
            decoded={'raw':f'{c:016x}','context_is_ppu':bool(c>>63),'pending_address':(c>>25)&0x3fffff,'demand_address':c&0x1ffffff,'age_nes_clocks':(c>>47)&255}
            decoded.update({name:bool(c&(1<<(55+i))) for i,name in enumerate(('ppu_valid','cpu_valid','ppu_sample','cpu_sample','rom_response','rom_ready','pending_ppu','busy'))})
            assert decoded['context_is_ppu'] and decoded['pending_address']==decoded['demand_address']==0x21fbe7 and decoded['age_nes_clocks']==1
            assert decoded['busy'] and decoded['pending_ppu'] and decoded['ppu_sample'] and not decoded['ppu_valid'] and not decoded['rom_response']
            ppu=ppu_decode(int(g['ppu_state_hi']+g['ppu_state_lo'],16))
            assert ppu['line']==192 and ppu['dot']==262 and ppu['sprite_fetch']==ppu['rendering']==1
            assert ppu['read_2007_pipeline']==ppu['write_2007_pipeline']==0 and ppu['prefetch_hint']==0
            cols=b['columns'].split(',');bins=[dict(zip(cols,map(lambda x:int(x,16),b[f'b{i:02}'].split(',')),strict=True)) for i in range(12)]
            assert b['budget_schema']=='693' and sum(x['frames'] for x in bins)<n
            request=bytes.fromhex(g['sink_trace_request_hex']);assert request[0]==2
            common.update(classification='Sticky NES PPU ROM sample deadline fault; not USER exit, fixed60s timeout, plan FINISH0x80 or five-second stage0 boot timeout',
                fault=decoded,ppu=ppu,request_hex=request.hex(),request={'op':request[0],'section':request[1],'serial':int.from_bytes(request[4:8],'little'),'generation':int.from_bytes(request[8:10],'little'),'offset':int.from_bytes(request[10:12],'little'),'length':int.from_bytes(request[12:14],'little')},
                epoch={'start_s':int(b['epoch_tick'])/100,'frame_starts':sum(x['frames'] for x in bins),'bins':bins,'first55s_workload_not_retained':True},
                explicit_exit_tested=False,root_cause=None,
                unresolved=['Request first-eligible/grant/response timestamps before the snapshot','Native CPU versus PPU versus tile-plan ownership immediately before fault','Sprite address/ALE/mapper physical tag timing across dots257..264'],
                forbidden_inference=['No proof of a bad PSRAM byte, electrical IO violation or excessive tile count','age1 is request age at sample, not a255-cycle backend timeout','screen_error169 is valid SPC init readbackA9, not a rendering error','Final16 capture episodes are not the final ROM request history','First55s completion counts persist; epoch bins no longer describe first55s workload'])
        runs[str(trial)]=common
    sources=a.out/'sources';sources.mkdir()
    for n in ('nes_rom_service.sv','nes_rom_physical.sv','nes_run_observer134.sv','nes_live_joint.sv','rtl/ppu.sv'):
        src=a.board/n;assert sha(src)==integrated['inputs']['changed'].get(n,integrated['inputs']['base'][n])
        dst=sources/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    for n in ('nes_runtime_board165.inc','nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c','nes_native165.h'):
        src=a.arm/n
        if src.exists():shutil.copyfile(src,sources/n)
    result={'stage':697,'physical':True,'runs':runs,'package':'analysis/trial695-package.json','package_SHA256':sha(Path('analysis/trial695-package.json')),
        'source_pins':{p.relative_to(sources).as_posix():sha(p) for p in sources.rglob('*') if p.is_file()},
        'decision':'695 control passed;696 long play exceeds60s but stage-entry PPU deadline remains unresolved. Prioritize sprite ROM request/grant/response reproduction; preserve STOP/independent sample deadline/menu, defer output optimization until bounded cause audit.',
        'limitations':['One unsynchronized playthrough per variant;695 executable instructions equal690. No causal FPS claim.','696 early completion counters are valid, early workload bins overwritten. Long full-run phases cannot be paired to60s control.','No new simulation/synthesis/installer or physical button-exit proof.']}
    a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    for f in a.out.rglob('*'):
        if f.is_file():inventory[f.relative_to(a.out).as_posix()]={'bytes':f.stat().st_size,'SHA256':sha(f)}
    archive=a.out/'evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n in inventory:z.write(a.out/n,n)
    with zipfile.ZipFile(archive) as z:
        for n,h in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==h['SHA256']
    a.archive_report.write_text(json.dumps({'stage':697,'location':'WORKSPACE/probes/nes-hardware697/'+a.out.name,'SHA256':sha(archive),'bytes':archive.stat().st_size,'all_bytes_verified':True,'inventory':inventory},indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:{'display':v['display'],'windows':v['completion_windows'],'classification':v['classification']} for k,v in runs.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('downloads','board','arm','out','report','archive-report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
