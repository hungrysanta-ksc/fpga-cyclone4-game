"""Check completed WRAM uploads, preserved screens and STOP edges on the 959 replay."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_chr951 import directory, logtext, read, sha
from analyze_nes_ready958 import board_case
from guard_nes_output852 import run as fault_run
from nes_blank959 import ROM, OUT, WORK, edits
from pack_nes_column854 import encode
from test_nes_banks557 import MASTER


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def summary(folder, control):
    joint = read(folder/'joint.json')
    assert joint['passed'] and joint['commits'] == 8
    for g in range(905,913):
        assert sha(folder/f'frame-{g}.rgb') == sha(control/f'frame-{g}.rgb')
    assert joint['vram_DMA_B'] == read(control/'joint.json')['vram_DMA_B']
    window = rows(folder/'window.csv')
    sealed = [r for r in window if r['g']=='906' and r['op']=='3']
    mark = lambda r:[int(r[k]) for k in ('frame','line','clock')]
    show = [int(r['frame']) for r in window if r['event']=='reveal']
    assert len(show)==8
    # Before the first reveal the screen is forced blank and the PPU monitor
    # deliberately does not emit visible-port last-byte events.
    all_checked = [r for r in window if r['op']=='3' and int(r['g'])>905]
    starts = [r for r in all_checked if r['event']=='ppu_dma']
    ends = [r for r in all_checked if r['event']=='ppu_last']
    jobs = []
    for a,b in zip(starts,ends,strict=True):
        assert (a['g'],a['index'],a['frame'])==(b['g'],b['index'],b['frame'])
        assert 225 <= int(a['line']) <= int(b['line']) <= 261
        if a['g']=='906':
            jobs.append([int(a['value']),*mark(a),*mark(b)[1:]])
    def only(event):
        r, = [r for r in sealed if r['event']==event]
        return mark(r)
    maps = [r for r in rows(folder/'seal528.csv') if r['g']=='906' and r['event']=='dma'
            and int(r['bytes'])==1920 and int(r['port'])==24]
    assert len(maps)<=1
    if maps:
        assert int(maps[0]['bank'])==1 and int(maps[0]['dst'])==0xa780
    events = read(folder/'events.json')
    inputs = [e for e in events if e.get('input_generation')==912 and e.get('event')=='SPI']
    plans = [e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe9']
    reveal911, = [r for r in window if r['g']=='911' and r['event']=='reveal']
    seal911, = [r for r in window if r['g']=='911' and r['event']=='load' and r['op']=='3']
    d2_before_reveal=sum(e['opcode']=='0xd2' and e['clock']<int(reveal911['clock']) for e in inputs)
    last_obj = max(r['producer'] for r in map(json.loads,(folder/'producer.jsonl').read_text().splitlines())
                   if r['generation']==912 and r['kind']==1)
    seal912, = [r for r in window if r['g']=='912' and r['op']=='3' and r['event']=='load']
    timing912=dict(first_D1=round(min(e['start'] for e in inputs if e['opcode']=='0xd1')),
                   last_D2=round(max(e['clock'] for e in inputs if e['opcode']=='0xd2')),
                   first_E9=round(plans[0]['start']),last_OBJ=last_obj,SEAL=mark(seal912))
    return dict(reveals=show, six=show[-1]-show[1], seal=only('load'),
                reveal=only('reveal'), ACK906=only('ack'),
                ACK912=joint['frames'][-1]['ACK_masterclock'],
                checked_PPU_DMA=len(starts), sealed906_DMA=jobs,
                map1920_start=[int(maps[0][k]) for k in ('clock','line','h')] if maps else None,
                SEAL911=mark(seal911), reveal911=mark(reveal911),D2_before_911_reveal=d2_before_reveal,
                timing912=timing912, RGB=8, VRAM_B=joint['vram_DMA_B'])


def guard(temp, phase, case, retry=False):
    trial=directory(temp,phase,'959retryseal' if retry else '959orderedseal','cold')
    select=lambda b,g: g==906 and b[0]==3
    if case=='identity':
        def damage(b,g,kind):
            if g!=906:
                return b,False
            b[8]^=1
            return b,True
        return fault_run(temp,trial,'bad-seal',column_client=ROM,edit_seal=damage)
    def adapt(script,labels):
        hook='if not injected852 then'
        assert script.count(hook)==1
        if case=='before':
            script=script.replace(hook,"if not injected852 and packet and pw(8)==906 and pb(0)==3 and word(0x4004+emu.getState()['cpu.x'])==1920 then")
            old=f"end,emu.callbackType.exec,{labels['column_service']})"
            assert script.count(old)==1
            site=labels['sample618']
            if retry:
                body=bytearray((ROM/'body.bin').read_bytes())
                for at,original,value in edits('retry'):
                    assert body[at]==original
                    body[at]=value
                site=0x7e2000+body.index(bytes.fromhex('201936f0034c'),labels['group_wait912']-0x7e2000)
            script=script.replace(old,f"end,emu.callbackType.exec,{site})")
        else:
            script=script.replace(hook,'if false and not injected852 then')
            needle='if dmaRemaining==1 then sample516("ppu_last") end'
            assert script.count(needle)==1
            script=script.replace(needle,needle+"""
   if dmaRemaining==1 and dmaLength==1920 and packet and pb(0)==3 and pw(8)==906 then
     assert(not injected852);injected852=true;stop852=true
   end""")
        check='  assert(captured==commits)'
        return script.replace(check,'  assert(injected852);assert(captured==commits)')
    out=fault_run(temp,trial,'stop',column_client=ROM,select_packet=select,adapt_lua=adapt,
                  output_name='edge959-'+case)
    trace=rows(trial/('guard-edge959-'+case)/'window.csv')
    started=[int(r['value']) for r in trace if r['g']=='906' and r['op']=='3' and r['event']=='ppu_dma']
    assert started == ([] if case=='before' else [1920]),started
    assert not any(r['g']=='906' and r['event']=='reveal' for r in trace)
    return dict(**out, completed_before_cancel=started)


def analyze(temp):
    phases={}
    for phase in (1,2):
        folder=lambda tag: directory(temp,phase,tag,'cold')
        results={}
        for tag,base in [('958closed','958closed'),('959seal','958closed'),('959retryseal','958closed'),
                         ('959orderedseal','958closed'),('958control','958control'),
                         ('959static','958control'),('959orderedstatic','958control'),
                         ('959orderedclosed','958closed')]:
            one=summary(folder(tag),folder(base))
            if tag.endswith('seal'):
                base_window=rows(folder(base)/'window.csv')
                cand_window=rows(folder(tag)/'window.csv')
                clock=one['seal'][2]
                assert [r for r in base_window if int(r['clock'])<=clock]==[r for r in cand_window if int(r['clock'])<=clock]
                assert one['seal']==results[base]['seal']
            one['ACK912_delta_ms']=round((one['ACK912']-results.get(base,one)['ACK912'])*1000/MASTER,6)
            results[tag]=one
        for tag in ('959orderedstatic','959orderedclosed'):
            board=board_case(folder(tag))
            assert board['checked_batch']==7 and board['body_B']==75
            if tag.endswith('closed'):
                assert board['polls'][1]==0
                wire=[e for e in read(folder(tag)/'events.json')
                      if e.get('generation')==906 and e.get('opcode')=='0xe9']
                assert len(wire)==7 and abs(wire[-1]['clock']-board['checked_seal'])<=2
            results[tag]['RTL906_polls_mismatches']=board['polls']
            results[tag]['RTL906_E9_accept_clock']=board['checked_seal']
            # The earlier generation's baseline is reported separately.
            line=next(s for s in logtext(folder(tag)/'gen905/timing958.log').splitlines()
                      if 'E8914 compared=' in s)
            results[tag]['RTL905_E8']=line.strip()
        phases[phase]=results
    baseline=read(ROM/'build.json')
    body=bytearray((ROM/'body.bin').read_bytes())
    for off,old,val in edits('retry'):
        assert body[off]==old
        body[off]=val
    guards={}
    for phase in (1,2):
        for variant in ('ordered','retry'):
            d=directory(temp,phase,'959'+variant+'seal','cold')
            outcomes={}
            for name in ('edge959-before','edge959-after','bad-seal'):
                folder=d/('guard-'+name)
                r=read(folder/'result.json')
                assert r['passed'] and r['commits']==1 and r['last_status']==(224 if name=='bad-seal' else 228)
                assert sha(folder/'retained.rgb')==sha(d/'frame-905.rgb')
                outcomes[name]=dict(status=r['last_status'],retained=905)
            guards[f'{variant}{phase}']=outcomes
    base=read(OUT.parent/'base/result.json')
    assert base['firmware_sha256']==sha(WORK/'link/src/obj-nes-100/firmware.stm')
    assert base['passed'] and base['base_restored'] and base['safe_return']
    return dict(master_Hz=MASTER, physical_reference='MMC955', phases=phases,guards=guards,
                base_restore=base['config_paths'],ARM_SHA256=base['firmware_sha256'],
                ordered_ROM_SHA256=sha(OUT.with_name('ordered')/'sink165.sfc'),
                free_ROM_B={k:read(p/'build.json')['physical_free_B'] for k,p in
                            [('MMC955',ROM),('early',OUT),('ordered',OUT.with_name('ordered'))]},
                retry_ROM_deficit_B=len(encode(bytes(body),0,2))+baseline['loader_B']-5056)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--guard', choices=('before','after','identity'))
    p.add_argument('--phase',type=int,choices=(1,2))
    p.add_argument('--retry',action='store_true')
    a=p.parse_args()
    if a.guard:
        print(json.dumps(guard(a.temp,a.phase,a.guard,a.retry)))
    else:
        print(json.dumps(analyze(a.temp),indent=2))
