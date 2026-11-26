"""Compare matching 400 ms samples of the two Kirby first-block probes."""
import argparse
import json
from pathlib import Path

from read_nes_ingress1029 import decode


def samples(path,edition):
    out={}
    for row in decode(path.read_bytes(),edition)['rows']:
        if 'timing' not in row or 'ready_to_D1_ms' not in row:
            continue
        block=row['input']
        key=(row['tick']//40,row['BG'],row['OBJ'],row['map'],row['tiles'],row['chunks'],
             block['blocks'],block['payload_bytes'])
        if key in out:
            raise ValueError('duplicate physical sampling window')
        out[key]=row
    return out


def compare(control,prefetch):
    baseline=samples(control,1032)
    candidate=samples(prefetch,1031)
    matched=[]
    for key in sorted(baseline.keys() & candidate.keys()):
        a,b=baseline[key],candidate[key]
        times=[r['ready_to_D1_ms'] for r in (a,b)]
        # Age is measured entirely in the FPGA clock domain. A saturated bin
        # gives a one-sided bound, not an exact latency.
        (lo,hi),(cl,ch)=times
        saved=[None if ch is None else lo-ch,None if hi is None else hi-cl]
        matched.append(dict(seconds=[r['tick']/100 for r in (a,b)],
                            generations=[r['generation'] for r in (a,b)],
                            work=key[1:],ready_to_D1_ms=times,ready_wait_saved_ms=saved,
                            first_D1_from_previous_show_estimate_ms=[
                                [v-r['input']['first_D1_to_last_return_ms']
                                 for v in r['timing']['previous_show_to_input_complete_ms']] for r in (a,b)],
                            previous_show_to_ACK_ms=[r['timing']['previous_show_to_ACK_ms'] for r in (a,b)]))
    return dict(order=['MMC1032 control','MMC1031 prefetch'],valid_samples=[len(baseline),len(candidate)],
                matched=matched)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control',type=Path)
    parser.add_argument('prefetch',type=Path)
    args=parser.parse_args()
    print(json.dumps(compare(args.control,args.prefetch),indent=2))
