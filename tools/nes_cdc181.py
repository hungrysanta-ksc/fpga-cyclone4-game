# SPDX-License-Identifier: MIT
"""Exact, fail-closed CDC constraints for held mailboxes, pad and audio only.

No clock groups, reset exceptions, ROM data exceptions or RTL changes. Standard
25.1 has no datapath_only: setup bounds include clock latency, and post-route
data_delay must separately pass the smaller physical budget. Hold-only cuts are
justified by ACK ownership, not by an assumed phase of independent clocks.
"""
from pathlib import Path
import argparse,csv,json,re,shutil
from collections import Counter
from nes_game147 import ROOT,sha

CORE='nes_live_joint:core|'
RECORDS=CORE+'nes_native_mailbox165:native_records|'
PREPARED=CORE+'nes_native_mailbox165:native_prepared|'
PAD='nes_game_pad150:pad|'
AUDIO='nes_dac162:audio|'
READER=CORE+'nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|'
GUARD=CORE+'nes_diag_clock_guard127:clock_guard|'
BUDGETS={'records':(11.904,9.904),'prepared':(45.454,43.454),
         'pad':(45.454,43.454),'audio':(11.904,9.904)}
CONTROLS={
 **{p+n+'[0]':p+n+'[1]' for p in (RECORDS,PREPARED) for n in ('req_sync','ack_sync','up_src','up_dst')},
 PAD+'request_meta':PAD+'request_sync',PAD+'ack_meta':PAD+'ack_sync',
 **{AUDIO+n+'[0]':AUDIO+n+'[1]' for n in ('request_sync','ack_sync')},
 **{READER+n+'[0]':READER+n+'[1]' for n in ('request_sync','ack_sync')},
 **{GUARD+n+'[0]':GUARD+n+'[1]' for n in ('mem_sync','ref_sync')},
 'sink_rom_fault[0]':'sink_rom_fault[1]'}

def classify(s,d):
    for p,src,dst,g in [(RECORDS,'held','received','records'),(PREPARED,'held','received','prepared'),
                        (PAD,'held_buttons','current_buttons','pad'),(AUDIO,'held_sample','dac_sample','audio')]:
        m=re.fullmatch(re.escape(p+src)+r'\[(\d+)\]',s)
        if m and d==p+dst+'['+m[1]+']':return g
    if d in CONTROLS:return 'first_stage'
    return 'unmodified'

EXACT='''proc cdc181_exact {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "CDC181 missing/ambiguous register: $name"}
 foreach_in_collection n $r {if {[get_node_info -name $n] ne $name} {error "CDC181 name mismatch: $name"}}
 return $r
}
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','inventory','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    sources=json.loads((ROOT/'analysis/rank181-verification.json').read_bytes())['verification']['sources']
    inv=json.loads((a.inventory/'inventory-inputs.json').read_bytes())
    assert inv['sources']==sources
    assert inv['script_sha256']==sha(ROOT/'tools/nes_cdc181_inventory.tcl')
    assert int((a.inventory/'inventory.exitcode').read_text(encoding='utf-8-sig'))==0
    xs=list(csv.DictReader((a.inventory/'inventory181.tsv').open(),delimiter='\t'))
    pairs=sorted({(x['from'],x['to']) for x in xs if x['kind']=='setup'})
    selected=[dict(group=classify(s,d),source=s,destination=d) for s,d in pairs if classify(s,d)!='unmodified']
    counts=Counter(x['group'] for x in selected)
    # Fresh synthesis includes record bit60; failed-fit DB post-map can prune it.
    # Never generate final constraints from that incomplete failed-fit inventory.
    assert counts==dict(records=87,prepared=17,pad=8,audio=16,first_stage=17),counts
    assert {x['destination'] for x in selected if x['group']=='first_stage'}==set(CONTROLS)
    for x in selected:
        matches=[v for v in xs if v['kind']=='setup' and (v['from'],v['to'])==(x['source'],x['destination'])]
        assert all((v['from_clock']=='nes') != (v['to_clock']=='nes') for v in matches)
        assert all('board8' not in (v['from_clock'],v['to_clock']) for v in matches)
    a.out.mkdir()
    for n,h in sources.items():
        assert sha(a.baseline/n)==h,n
        f=a.out/n;f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,f)
    sdc=['# CDC181 exact source/destination pairs. No reset or whole-domain waiver.',EXACT]
    for x in selected:
        s,d,g=x['source'],x['destination'],x['group']
        pair=f'-from [cdc181_exact {{{s}}}] -to [cdc181_exact {{{d}}}]'
        if g=='first_stage':
            sdc.append('set_false_path '+pair)
            x['second_stage']=CONTROLS[d]
        else:
            mx,physical=BUDGETS[g]
            sdc.extend([f'set_max_delay {mx} '+pair,'set_false_path -hold '+pair])
            x.update(setup_bound_ns=mx,data_delay_budget_ns=physical)
    (a.out/'cdc181.sdc').write_text('\n'.join(sdc)+'\n',encoding='utf8')
    f=a.out/'board.sdc';f.write_text(f.read_text()+'\nsource cdc181.sdc\n',encoding='utf8')
    (a.out/'preparation.json').write_text(json.dumps(dict(
        sources={n:sha(a.out/n) for n in [*sources,'cdc181.sdc']},baseline_sources=sources,
        changed=['board.sdc'],added=['cdc181.sdc'],rtl_unchanged=True,
        preparer_sha256=sha(Path(__file__)),inventory_sha256=sha(a.inventory/'inventory181.tsv'),
        inventory_rows=len(xs),setup_pairs=len(pairs),selected=selected,groups=counts,
        reset_exceptions=False,rom_payload_exceptions=False,whole_domain_exceptions=False,
        hardware=False,adopted=False),indent=2)+'\n',encoding='utf8')
    print('Prepared CDC181',dict(counts),'RTL unchanged; post-route gate mandatory')

if __name__=='__main__':main()
