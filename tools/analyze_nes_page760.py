# SPDX-License-Identifier: MIT
"""Compare the 759 fixed-order lower-bound budget and isolated 760 replay."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_owner739 import ms, read, sha


def analyze(temp, ledger):
    result = dict(selected='753', scope='receiver replay; 753 releases and calibrated E1 cost', phases={})
    for phase, rows in read(ledger)['phases'].items():
        ref = rows['753']
        budget = ref['same_prefix_budget']
        original = ref['page']
        old_cost = ref['page_SPI_ms']
        assert len(original)==8 and all(p['B']==211 for p in original)
        overhead = old_cost/8 - 211*8/2625
        variants = {}
        for mode, tag in [('bitmap','credit'),('indexed','index')]:
            folder = temp/f'nes-page760-{tag}{phase}'
            cost = read(folder/'cost760.json')
            assert cost['original_B']==1688 and cost['changes']==34
            assert read(folder/'audit.json')['frames']==read(folder/'result.json')['commits']==53
            phases = {k:ms(cost[k+'_clocks']) for k in ('entry','restore','check_and_reply','service')}
            assert abs(sum(phases[k] for k in ('entry','restore','check_and_reply'))-phases['service'])<1e-8
            new_spi = cost['wire_B']*8/2625 + overhead
            saved = old_cost-new_spi
            # A whole immutable E1 must finish before this one checked head can
            # start. Only the eighth original service was charged in 759.
            ceiling = saved + budget['last_service_ms'] - budget['driver_plus_last_service_short_ms']
            # Also grant the contender all eight old service intervals in full,
            # although those previously overlapped SPI. Even this fails here.
            favorable = saved + ref['page_head_to_ACK_ms'] - phases['service']
            with (folder/'window.csv').open() as f:
                frames = [r for r in csv.DictReader(f) if r['event']=='reveal']
            assert len(frames)==53 and frames[-1]['g']=='957'
            delta_frames = int(frames[-1]['frame'])-int(frames[-2]['frame'])
            final = read(folder/'result.json')['frames'][-1]['ACK_masterclock']
            variants[mode] = dict(**cost, ms=phases, spi_ms=new_spi, saved_spi_ms=saved,
                fixed_order_net_saving_ms=saved+budget['last_service_ms']-phases['service'],
                fixed_order_max_service_ms=ceiling,
                short_of_first248_ms=phases['service']-ceiling, all_eight_credit_net_ms=favorable,
                replay_last_map_late_ms=ms(cost['ack_clock']-ref['first248'][1]),
                replay_957_VBlank=delta_frames, replay_final_ACK_delta_ms=ms(final-ref['ACK']),
                RGB_frames_verified=len(frames),
                pins={s:sha(folder/s) for s in ('arrivals.tsv','handler.bin','capture.lua','window.csv','result.json')})
        result['phases'][phase]=dict(required_ms=budget['driver_plus_last_service_short_ms'],
            baseline_spi_ms=old_cost, baseline_last_service_ms=budget['last_service_ms'],
            baseline_service_sum_ms=ref['page_head_to_ACK_ms'], variants=variants)
    result['faults']={name:read(temp/f'nes-page760-{name}1/cost760.json') for name in ('retained','partial')}
    result['baseline_ledger_SHA256']=sha(ledger)
    result['eligible']=[mode for mode in variants if all(v['variants'][mode]['short_of_first248_ms']<=0 for v in result['phases'].values())]
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--temp',type=Path,required=True)
    p.add_argument('--ledger',type=Path,default=Path('analysis/pipe759-verification.json'))
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.ledger),indent=2)+'\n',encoding='utf8',newline='\n')
