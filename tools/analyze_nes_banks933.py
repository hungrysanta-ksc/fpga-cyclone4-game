"""Bind the first six physical tile banks, target blank and byte coverage."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_obj923 import recovery
from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_rows932 import original_dma_jobs
from analyze_nes_window924 import sample
from nes_banks933 import DeeperHead, MODES, ORIGINAL, PageHead, QueuedPages, RetainedRows, image
from nes_return920 import client


def check_invalidation(cls):
    # A booked refill represents an in-flight PSRAM transaction. STOP must
    # clear its future data too and keep the physical slot reserved.
    for stop in range(99,107):
        port = object.__new__(cls)
        port.chr = bytes(range(256))*512
        port.history = {}
        if issubclass(cls, PageHead):
            port.pages = {0:dict(cursor=1,after=90,rows={0:(911,105,0,8)})}
            port.page_key = 0
        port.generation = port.owner = 911
        port.free = 106 if stop >= 100 else 99
        if stop >= 100:
            port.store_reply(6511*16,105)
        port.cancel_supply()
        port.pump(stop)
        assert port.stopped and not port.history and not port.ready_rows and not port.queue
        if issubclass(cls, PageHead):
            assert not port.pages and port.page_key is None
        port.restart_supply()
        assert not port.active and not port.history and port.free == (106 if stop>=100 else 99)


def measure(path, arm, base, ref932, baseline_times, expected):
    row, quality = sample(path,arm)
    assert quality == expected
    joint = read(path/'joint.json')
    assert joint['passed'] and joint['firmware_SHA256']==sha(arm/'link/src/obj-nes-100/firmware.stm')
    assert joint['client_SHA256']==sha(client('first')/'sink165.sfc')
    times = job_times(path)
    assert times.keys() == baseline_times.keys()
    other = [(t-baseline_times[k], k) for k,t in times.items() if k[:2] not in ((912,32),(912,35))]
    banks = jobs(path,tokens=(32,33,34,35,36))
    trace = read_csv(path,'window.csv')
    f912 = [r for r in trace if r['g']=='912']
    prior = next(r for r in trace if r['g']=='911' and r['event']=='reveal')
    target = int(prior['frame'])+1
    estimates = [int(r['clock'])+(262-int(r['line']))*1364 for r in trace
                 if int(r['frame'])==target and 225<=int(r['line'])<=261]
    # Do not invent a horizontal position for a line-only callback.
    upper = min(estimates,default=None)
    lower = max(estimates)-1363 if estimates else None
    assert lower is None or lower<=upper
    seal = int(next(r['clock'] for r in f912 if r['op']=='3' and r['event']=='load'))
    dma = [r for r in f912 if r['event']=='ppu_dma' and int(r['clock'])<seal]
    pre = coverage(row['pre912']).keys()
    original = coverage(base['pre912']).keys()
    assert sum(int(r['value']) for r in dma)==sum(s[2] for s in row['pre912'])
    hist = path/'history933.json'
    hits = read(hist) if hist.exists() else []
    assert all(previous<current and reply<lookup for current,addr,previous,reply,lookup in hits)
    original_jobs = original_dma_jobs(path, base['pre912'], times) if len(original)==496 else []
    page_trace = path/'pages933.json'
    pages = read(page_trace) if page_trace.exists() else dict(grants=[],hits=[])
    assert all(prev<g and reply<t for g,addr,prev,reply,t in pages['hits'])
    stalls = [(end-t,addr//16,addr%16,t,end) for slot,addr,t,end,grants in read(path/'slots930.json')
              if banks[35]['offset']<=slot<banks[35]['offset']+banks[35]['bytes'] and grants]
    continuation = [(addr//16,addr%16,grant) for g,addr,grant,reply in read(path/'ahead911.json')
                    if g==912 and (addr//16 in (3081,6264) or addr//16==6265 and addr%16<3)]
    return dict(first_OBJ=banks[32]['clocks'],OBJ288=banks[35]['clocks'],
                original_jobs=original_jobs, previous_show=int(prior['clock']),target_VBlank=target,local_end_lower=lower,
                local_end_upper=upper,ready_bytes_by_end=sum(j['bytes'] for j in original_jobs if j['ready']<=upper)
                if upper is not None else None,
                returned_bytes_by_end=sum(j['bytes'] for j in original_jobs if j['returned']<=upper)
                if upper is not None else None,
                capture_D2=row['commit_D2'],capture_offset=row['capture_offset'],next_capture_ready=row['ready911'],
                other_later_vs932=sum(dt>0 for dt,k in other),max_other_delta_vs932=max(other),
                largest_288B_physical_lookup=max(stalls,default=None),
                continuation_grants=continuation,
                retained_bytes=len(pre & original),preDMA=row['pre912'],SEAL=seal,
                target_bus=[{k:r[k] for k in ('line','clock','event','op','section','value')}
                            for r in f912 if int(r['frame'])==target and int(r['line'])>=224
                            and r['event'] in ('load','ack','ppu_dma')],
                gaps=row['gaps'],total=row['intervals'],ACK=row['ack912'],
                gain_vs925=base['ack912']-row['ack912'],gain_vs932=ref932['ack912']-row['ack912'],
                history_hits=len(hits),extra_page_grants=len(pages['grants']),page_hits=len(pages['hits']),
                page_hits_by_tag912=dict(Counter(h[1]//16 for h in pages['hits'] if h[0]==912)),
                hits_by_tag912=dict(Counter(h[1]//16 for h in hits if h[0]==912)),
                first_OBJ_row_sources=[h for h in hits if h[0]==912 and h[1]//16==6511])


def report(temp):
    check_invalidation(RetainedRows)
    check_invalidation(DeeperHead)
    check_invalidation(PageHead)
    check_invalidation(QueuedPages)
    result = dict(master_Hz=21477272,history_STOP_cases=32,builds={},cases={})
    for arm in (ORIGINAL,*(image(m) for m in ('oam','pair','palette'))):
        proof = recovery('final',arm,trial=arm)
        result['builds'][arm.name]=dict(bytes=(arm/'link/src/obj-nes-100/firmware.stm').stat().st_size,
                                         proof=proof)
    for phase in (1,2):
        for cache in ('cold','warm'):
            control = directory(temp,phase,'932run',cache)
            ref, expected = sample(control,ORIGINAL)
            base, quality = sample(directory(temp,phase,'925final',cache),ORIGINAL)
            assert quality==expected
            prior_times = job_times(control)
            case = result['cases'][f'{cache}-{phase}'] = {}
            for mode in ('932run',*MODES):
                path = control if mode=='932run' else directory(temp,phase,'933'+mode,cache)
                arm = ORIGINAL if mode=='932run' else image(mode)
                result_row=measure(path,arm,base,ref,prior_times,expected)
                case[mode]=result_row
                if cache=='warm':
                    result_row['same_SPI_as932']=sha(path/'events.json')==sha(control/'events.json')
                    result_row['same_65816_trace_as932']=sha(path/'window.csv')==sha(control/'window.csv')
                else:
                    original=case['932run']
                    end=result_row['local_end_lower']
                    result_row['return32_gain']=original['first_OBJ']['returned']-result_row['first_OBJ']['returned']
                    result_row['ready288_gain']=original['OBJ288']['ready']-result_row['OBJ288']['ready']
                    result_row['joint_pass']=bool(end and result_row['first_OBJ']['returned']<=end and
                        result_row['OBJ288']['ready']<=end and result_row['retained_bytes']==496 and
                        result_row['total']<=15 and result_row['gain_vs925']>0 and
                        result_row['other_later_vs932']==0 and result_row['next_capture_ready']<=ref['ready911'])
    return result


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(report(a.temp),indent=2)+'\n',encoding='utf-8')
