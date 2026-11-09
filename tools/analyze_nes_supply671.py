"""Price measured kernels and explicit dual-reader ownership models, not RTL."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from probe_nes_supply671 import read,sha
from analyze_nes_supply670 import ms
from nes_schedule492 import funcs

class Owner:
    def __init__(self):self.valid=False;self.epoch=0;self.expected=0;self.reads=0;self.arm=False;self.copied=False;self.checked=False
    def seal(self,g,n):
        assert not self.valid
        self.valid=True;self.g=g;self.expected=n;self.reads=0;self.arm=False;self.copied=False;self.checked=False
        self.identity=(self.epoch,g);return self.identity
    def d2(self,identity):
        assert self.valid and self.identity==identity;self.arm=True
    def beat(self,identity,index):
        assert self.valid and self.identity==identity and index==self.reads and self.reads<self.expected
        self.reads+=1
    def copy_ack(self,identity):
        assert self.valid and self.identity==identity and self.reads==self.expected
        self.copied=True
    def release(self):
        assert self.valid and self.arm and self.copied
        self.valid=False
    def stop(self):self.valid=False;self.epoch+=1;self.checked=False

def guards():
    total=0
    def reject(fn):
        nonlocal total
        try:fn()
        except AssertionError:total+=1
        else:raise AssertionError('owner accepted invalid event')
    for first in ('ARM','SNES'):
        for n in (1,64,168):
            o=Owner();token=o.seal(955,n)
            reject(lambda:o.release());reject(lambda:o.copy_ack(token));reject(lambda:o.seal(956,n))
            if first=='ARM':o.d2(token)
            for i in range(n):o.beat(token,i)
            reject(lambda:o.beat(token,n));o.copy_ack(token)
            if first=='SNES':reject(lambda:o.release());o.d2(token)
            o.release();assert not o.checked # storage credit is NOT validation/display ACK
            o.seal(956,n);o.stop();new=o.seal(955,n)
            reject(lambda:o.d2(token));reject(lambda:o.copy_ack(token));reject(lambda:o.beat(token,0))
            assert new!=token
    return total

def main(a):
    k=read(a.kernel/'result.json');assert k['passed'];budget=read(Path('analysis/supply670-budget.json'))
    for g,pins in k['pins']['input'].items():
        assert pins['geometry']==budget['pins']['fixture'][f'frame{g}.geometry']
        assert pins['raw']==budget['pins']['fixture'][f'frame{g}.raw']
        assert pins['map']==budget['phases']['1']['frames'][g]['map_SHA256']
    assert sha(a.traces/'nes-reader661-sender/sender.json')==budget['pins']['sender']
    # Conventional probes layout; the selected product is never rewritten.
    base=Path(__file__).resolve().parents[2]/'probes/nes-trial666/arm01'
    assert sha(base/'src/obj-nes-100/firmware.stm')==budget['pins']['firmware']
    unchanged=[p for p in (base/'src').rglob('*') if p.is_file() and p.suffix in ('.c','.h','.S') and not any(part.startswith(('obj-','.dep-')) for part in p.parts)]
    assert all(sha(p)==sha(a.arm/'src'/p.relative_to(base/'src')) for p in unchanged)
    cpu=list(csv.DictReader((a.kernel/'cpu.csv').read_text().splitlines()))
    marks=list(csv.DictReader((a.kernel/'components.csv').read_text().splitlines()))
    beats=list(csv.DictReader((a.kernel/'source-reads.csv').read_text().splitlines()))
    phases={};frames={r['generation']:r for r in k['frames']}
    for r in frames.values():
        g=r['generation'];components={}
        for kind,mark in [('source','crc'),('row','row_crc')]:
            total=sum(int(t['clocks']) for t in cpu if t['case']==f'{g}-{kind}')
            prefix=sum(int(t['clock']) for t in marks if t['case']==f'{g}-{kind}' and t['mark']==mark)
            components[kind+'_before_check_ms']=ms(prefix)
            components[kind+'_check_and_return_ms']=ms(total-prefix)
        r['components']=components
    # Competing port requests are a specified arbiter model. Actual encoded
    # block is sealed; no codec writes may occur until storage release.
    # Each SPI byte can request one source read every256 host84MHz clocks;
    # SNES beats come from actual native DMA, not an assumed constant stride.
    arbitration={}
    for g in frames:
        groups=[];block=[]
        for b in beats:
            if b['case']!=f'{g}-source':continue
            if int(b['index'])==0:
                if block:groups.append(block)
                block=[]
            block.append(int(b['clock']))
        if block:groups.append(block)
        collisions=[];min_gap=10**9
        for offset in range(256):
            count=0
            for block in groups:
                ticks=[math.floor(t*84e6/21477272) for t in block]
                count+=sum(t%256==offset for t in ticks)
                min_gap=min(min_gap,min(b-a for a,b in zip(ticks,ticks[1:])))
            collisions.append(count)
        arbitration[g]=dict(model=True,source_read_count=sum(map(len,groups)),SNES_min_beat_gap_host_ticks=min_gap,
            scanned_relative_SPI_offsets=256,max_single_tick_SPI_stalls=max(collisions),
            max_added_SPI_us=max(collisions)/84,extra_codec_writes_allowed_while_sealed=False)
    for phase in (1,2):
        events=read(a.traces/f'nes-entry665-a{phase}/events.json');out={}
        for g,r in frames.items():
            transactions=[e for e in events if e['event']=='SPI' and e.get('input_generation',e['generation'])==g]
            d1=[e for e in transactions if e['opcode']=='0xd1'][:12]
            d2=[e for e in transactions if e['opcode']=='0xd2'][:12]
            costs=[int(t['clocks']) for t in cpu if t['case']==f'{g}-source'];assert len(costs)==len(d1)==len(d2)==12
            assert all(x['clock']<=y['clock'] for x,y in zip(d1,d2))
            # This optional conservative policy keeps the SINGLE source buffer
            # until mirror CRC completes. Times are counterfactual, not replay.
            done=0;holding=[]
            for x,y,cost in zip(d1,d2,costs):
                start=max(done,x['start']);done=max(start+cost,y['clock'])
                holding.append(ms(done-y['clock']))
            old=budget['phases'][str(phase)]['frames'][str(g)]
            out[g]=dict(
                    current_map_consume_ms=old['current_map_consumer_ms'],
                    conservative_keep_until_CRC_last_map_credit_delay_ms=holding[-1],
                    measured_SNES_service_ms=r['SNES_ms']['source']+r['SNES_ms']['row']+r['SNES_ms']['warm-clear'],
                    gross_wire_saving_ms=r['wire_saving_ms'])
        phases[phase]=out
    fw=a.arm/'src/obj-nes-100/firmware.stm';elf=a.arm/'src/obj-nes-100/sd2snes.elf'
    symbols=funcs(elf);recipe=next((addr,size) for name,addr,size in symbols if name=='recipe671')
    result=dict(stage=671,selected='MMC666',candidate_selected=False,budget_passed=False,
        reason='Measured SNES reconstruction/check service exceeds both wire savings and baseline map consume; producer-only full link fits, integrated port/ROM budget not passed',
        kernels=k,components_by_frame={g:r['components'] for g,r in frames.items()},phases=phases,
        source_port_model=arbitration,dual_consumer_model_guard_rejections=guards(),
        ownership=dict(actual_RTL=False,CRC_wait_policy='modeled conservative stalls; not required by two-reader ownership',
            preferred_storage_release='ARM D2 and complete ordered SNES copy+identity ACK; destination WRAM immutable through deferred CRC/use',
            pending_validation='CRC/coverage/actual DMA and final display ACK remain separate; copying does not certify display',
            extra_WRAM_for_overlap='two2112B source buffers if next input arrives before previous source use retires',
            STOP='model epoch cancellation blocks late reads/ACK; actual kernel invalidates recipe use until cold',
            cycle='ARM must return pending status and service old output; waiting synchronously for SNES while SNES awaits SEAL is forbidden'),
        full_ARM_resource_link=dict(firmware_B=fw.stat().st_size,Flash_free_B=212992-fw.stat().st_size,
            firmware_SHA256=sha(fw),ELF_SHA256=sha(elf),recipe_address=recipe[0],recipe_B=recipe[1],
            original_functions_retained=True,production_callback_connected=False,
            static_data_B=10040,static_BSS_B=19544,new_context_not_allocated_B=128+140+32,
            observed_recipe_stack_B=k['ARM_stack_observed_B']),
        unchanged_selected_source_files=len(unchanged),selected_firmware_SHA256=budget['pins']['firmware'],
        SNES=dict(new_kernel_B=k['SNES_kernel_ROM_B'],CRC_table_B=512,
            append_compression_sensitivity_B=k['SNES_append_storage_min_B'],physical_capacity_B=5056,
            append_is_not_integrated_net_cost=True,minimum_two_source_WRAM_B=4224,
            tag_LUT_B=16384,prior_keys_B=2048,descriptor_B=140,WRAM_product_allocation_verified=False),
        unchanged_guards='MMC666 production artifacts unchanged; no new end-to-end final ACK/menu/RTL proof',
        new_FIT=False,new_whole_schedule=False,new_delivery=False,
        pins=dict(kernel_result=sha(a.kernel/'result.json'),components=sha(a.kernel/'components.csv'),
            source_reads=sha(a.kernel/'source-reads.csv'),script=sha(Path(__file__))))
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(Flash=result['full_ARM_resource_link'],guards=result['dual_consumer_model_guard_rejections'],
        frames={g:{'parts':r['components'],'wire_ms':r['wire_saving_ms'],'source_ms':r['SNES_ms']['source'],
            'row_ms':r['SNES_ms']['row']} for g,r in frames.items()},phases=phases),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel','arm','traces','out'):p.add_argument('--'+name,type=Path,required=True)
    main(p.parse_args())
