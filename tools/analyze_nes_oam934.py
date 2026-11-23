"""Compare OAM submission, checked OBJ return and addressed DMA in the same blank."""
import argparse
import json
from pathlib import Path

from analyze_nes_banks933 import check_invalidation, measure
from analyze_nes_obj923 import recovery
from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_window924 import sample
from nes_banks933 import DeeperHead, ORIGINAL, QueuedPages
from nes_oam934 import arm


def oam_packet(folder):
    packets = [bytes.fromhex(json.loads(line)[2]) for line in (folder/'packets.jsonl').read_text().splitlines()]
    spi = [e for e in read(folder/'events.json') if e.get('opcode')=='0xe1']
    heads = iter(r for r in read_csv(folder,'window.csv') if r['g']=='912' and r['event']=='load')
    for data,event in zip(packets,spi,strict=True):
        if int.from_bytes(data[8:10],'little')!=912:
            continue
        head = next(heads)
        assert (int(head['op']),int(head['section']))==tuple(data[:2])
        if data[1]==4:
            return dict(start=round(event['start']),sent=round(event['clock']),
                        load=int(head['clock']),line=int(head['line']),size=int.from_bytes(data[12:14],'little'))
    raise ValueError(f'Missing generation 912 OAM in {folder}')


def compare(temp,mode,storage,phase,cache):
    baseline = directory(temp,phase,'925final',cache)
    prior = directory(temp,phase,'933'+storage,cache)
    control = mode=='933'
    path = prior if control else directory(temp,phase,'934'+mode+storage,cache)
    firmware = ORIGINAL if control else arm(mode)
    base,expected = sample(baseline,ORIGINAL)
    ref,quality = sample(prior,ORIGINAL)
    assert quality==expected
    data = measure(path,firmware,base,ref,job_times(prior),expected)
    vblank = data['target_VBlank']
    by_addr = coverage([entry for entry in data['preDMA'] if entry[3]==vblank])
    original = coverage(base['pre912'])
    obj = jobs(path,(35,36))
    oam = oam_packet(path)
    # Match both start and last PPU write of every early transfer, including
    # the small final OBJ. A queue receipt alone cannot satisfy this check.
    trace = [r for r in read_csv(path,'window.csv') if r['g']=='912']
    bus = [r for r in trace if r['event'] in ('ppu_dma','ppu_last') and int(r['clock'])<data['SEAL']]
    assert len(bus)==2*len(data['preDMA'])
    dma = []
    for entry,a,b in zip(data['preDMA'],bus[::2],bus[1::2],strict=True):
        assert a['event']=='ppu_dma' and b['event']=='ppu_last' and int(a['value'])==entry[2]
        dma.append(dict(address=entry[1],size=entry[2],start=int(a['clock']),end=int(b['clock']),
                        first_line=int(a['line']),last_line=int(b['line']),vblank=int(a['frame'])))
        assert int(b['frame'])==entry[3]==int(a['frame'])
    same_capture = data['next_capture_ready']==ref['ready911']
    beam = {r['value']:[int(r['frame']),int(r['line']),int(r['clock'])] for r in trace
            if r['event']=='consume920' and r['value'] in ('35','36')}
    for token in obj:
        assert beam[str(token)][2]==obj[token]['clocks']['returned']
    linked=read(path/'joint.json')
    row = dict(firmware=linked['firmware_SHA256'], consumer=linked['client_SHA256'],
               flash=(firmware/'link/src/obj-nes-100/firmware.stm').stat().st_size,
               target_VBlank=vblank,OAM=oam,OBJ288=obj[35]['clocks'],following_OBJ32=obj[36]['clocks'],
               bank_return_beam=beam,issue_after_return=oam['start']-obj[35]['clocks']['returned'],DMA=dma,
               in_target_blank=len(original.keys() & by_addr.keys()),all_pre=data['retained_bytes'],
               capture_D2=data['capture_D2'],capture_offset=data['capture_offset'],
               capture_ready=data['next_capture_ready'],capture_preserved=same_capture,
               other_later=data['other_later_vs932'],worst_other=data['max_other_delta_vs932'],
               gaps=data['gaps'],total=data['total'],ACK=data['ACK'],gain_vs925=data['gain_vs925'],
               gain_vs933=ref['ack912']-data['ACK'],
               SEAL=data['SEAL'],target_bus=data['target_bus'])
    row['cold_pass'] = bool(cache=='cold' and row['in_target_blank']==496 and row['total']<=15
                            and row['gain_vs925']>0 and row['other_later']==0 and same_capture
                            and row['issue_after_return']>=0 and row['flash']<=212992)
    return row


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('pairs',nargs='+',help='mode/storage')
    p.add_argument('--warm',nargs='*',default=[])
    p.add_argument('--proof',nargs='*',default=[])
    args=p.parse_args()
    result=dict(master_Hz=21477272,physical_timing=False,consumer='unchanged MMC925 65816',
                supply='933 recorded shared-ROM calendar and checked CHR row/page models',cases={},proof={})
    for pair in args.pairs:
        mode,storage=pair.split('/')
        result['cases'][pair]={f'{cache}-{phase}':compare(args.temp,mode,storage,phase,cache)
                               for cache in (('cold','warm') if pair in args.warm else ('cold',))
                               for phase in (1,2)}
    for cls in (DeeperHead,QueuedPages):
        check_invalidation(cls)
    result['history_STOP_cases']=16
    for mode in args.proof:
        result['proof'][mode]=recovery('final',arm(mode),trial=arm(mode))
    if 'window/fair' in result['cases']:
        for phase in (1,2):
            normal=directory(args.temp,phase,'934windowfair','cold')
            traced=directory(args.temp,phase,'934windowfairbeam','cold')
            for name in ('events.json','window.csv','producer.jsonl','tile532.csv'):
                assert sha(traced/name)==sha(normal/name), (phase,name)
            row=result['cases']['window/fair'][f'cold-{phase}']
            # Recover the destination from the verified descriptor and the
            # inactive OBJ bank, not from the tile byte count alone.
            destination=0x8000+jobs(normal,(36,))[36]['offset']
            marks=[]
            for line in (traced/'beam934.csv').read_text().splitlines():
                event,*values=line.split(',')
                tick,blank,scan,address,size,latched,a=map(int,values)
                if blank==row['target_VBlank'] and address==destination and size==32:
                    marks.append(dict(event=event,clock=tick,line=scan,address=address,size=size,
                                      saved_line=latched,accumulator=a))
            assert any(r['event']=='defer' for r in marks) and not any(r['event']=='grant' for r in marks)
            row['last32_beam']=marks
    result['both_cold_phases_pass']=[pair for pair,rows in result['cases'].items()
                                     if all(rows[f'cold-{p}']['cold_pass'] for p in (1,2))]
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
