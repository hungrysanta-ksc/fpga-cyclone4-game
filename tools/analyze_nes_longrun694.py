"""Compare the long-mode shared schedule with pinned689/MMC690 and MMC666."""
import argparse,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_bg674 import tile_image
from analyze_nes_frontier536 import contents
from analyze_nes_pair687 import receive_batch

def run(a):
    phases={}
    for phase in (1,2):
        folders={k:a.traces/v for k,v in [('MMC690',f'nes-status689-arm{phase}'),('MMC666',f'nes-ready673-b{phase}'),('long',f'nes-longrun694-{a.prefix}{phase}')]}
        ts={k:trace(f,a.traces/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};c=ts['long'];base=ts['MMC690'];f=folders['long']
        assert js['long']['parameters']==js['MMC690']['parameters']
        assert js['long']['firmware_SHA256']==sha(a.arm/'obj-nes-100/firmware.stm')
        assert js['long']['client_SHA256']==sha(a.client/'sink165.sfc')
        assert tile_image(f)==tile_image(folders['MMC690']) and contents(f)[1]==contents(folders['MMC690'])[1]
        assert {g:v['work'] for g,v in c['frames'].items()}=={g:v['work'] for g,v in base['frames'].items()}
        cpu=csv_groups(f/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            reveal951=c['details'][951]['marks']['reveal']['line']<=246,
            interval952=c['intervals'][952]['VBlank']==3,final_wait957=c['intervals'][957]['final_waits']==0)
        r=receive_batch(f);margin=ms(r['previous_ACK']-r['rows'][6]['returned'])
        comparisons={}
        for name,b in ts.items():
            if name=='long':continue
            comparisons[name]=dict(dense_delta_ms=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms'],
                last_ACK_delta_ms=ms(c['checked']['last_ACK']-b['checked']['last_ACK']),
                VBlank_regressions=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']],
                new_final_waits=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']])
        phases[phase]=dict(functional_pass=True,work_equal=True,protected=protected,input7_before956_ACK_ms=margin,
            intervals=c['intervals'],dense_mean_ms=c['checked']['dense_mean_ms'],last_ACK=c['checked']['last_ACK'],comparisons=comparisons,
            wire_B=js['long']['wire_B'],ARM_instructions=js['long']['ARM_instructions'],observed_stack_low=js['long']['observed_stack_low'],workspace_end=js['long']['workspace_end'],
            pins={n:sha(f/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json')})
        print('694',phase,'protected',protected,'delta690',comparisons['MMC690'],'input7 margin',margin,flush=True)
    report=dict(stage=694,variant=a.prefix,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),CPU=sha(a.client/'sink165.sfc'),phases=phases,
        physical=False,whole_FPGA_simulation=False,scope='Actual linked M4/native65816, modeled SPI/IRQ boundaries and replayed ROM calendar; fixed start clocks and same work. MMC690 uses689 record with proven identical688 functions/685CPU. No new physical FPS claim.')
    a.out.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('traces','arm','client','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--prefix',default='packed');run(p.parse_args())
