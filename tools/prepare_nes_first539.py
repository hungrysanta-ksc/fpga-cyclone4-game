# SPDX-License-Identifier: MIT
"""Move the first BG request forward in the MMC533 planner without changing plan order."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once, sha


def prepare(src, out, cache_fine, final_poll, poll_only):
    root = Path(__file__).resolve().parents[1]
    expected = json.loads((root/'analysis/frontier536-verification.json').read_text())['phases'][0]['base']['firmware']
    assert sha(src/'obj-nes-100/firmware.stm') == expected
    name = 'nes_planner211.c'
    code = (src/name).read_text()
    # The two 33-word slices belong to the same immutable COMMITTED map.
    # Distinct indices may still have equal contents and must be compared.
    compare = 'memcmp(&s->maps[g*33],&s->maps[(s->rows[y-1]>>3)*33],66)!=0'
    code = once(code, compare, '(g!=(s->rows[y-1]>>3)&&'+compare+')')
    if cache_fine:
        code = once(code,'end[32],bank[32];unsigned groups=0;', 'end[32],bank[32];unsigned groups=0,previous_fine=0;')
        code = once(code,'fy!=fine(s,y-1,0,false)+1','fy!=previous_fine+1')
        # On the first normal line after a patch, the previous-line test is
        # suppressed by the original predicate. Only normal lines seed it.
        code = once(code,'  if(split){if(groups==32)', '  previous_fine=fy;\n  if(split){if(groups==32)')
    out.mkdir(parents=True,exist_ok=False)
    if not poll_only:
        (out/name).write_text(code,newline='\n')
    if final_poll:
        name='nes_cost471.c'
        code=once((src/name).read_text(),'while(elapsed<84u*128u);',
                  'while(elapsed<84u*(reason==2?64u:128u));')
        code=once(code,'cost_quiet_budget_us=128\\n','cost_quiet_budget_us=128\\ncost_final_ack_quiet_budget_us=64\\n')
        (out/name).write_text(code,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--cache-fine',action='store_true')
    parser.add_argument('--final-poll',action='store_true')
    parser.add_argument('--poll-only',action='store_true')
    args=parser.parse_args()
    if args.poll_only and (not args.final_poll or args.cache_fine):
        parser.error('--poll-only requires --final-poll alone')
    prepare(args.arm,args.out,args.cache_fine,args.final_poll,args.poll_only)
