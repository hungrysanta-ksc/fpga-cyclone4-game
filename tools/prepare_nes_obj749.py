# SPDX-License-Identifier: MIT
"""Service a ready tile after the completed warm map run, before ordinary traffic."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_input748 import prepare as layout_control


def prepare(base, out, policy):
    layout_control(base, out, control=True)
    path = out / 'nes_native_sink165.c'
    text = path.read_text()
    failure = '{\n     return fail(s,5);\n    }' if policy == 'notice' else '\n     return fail(s,5);'
    service = '''/* E8 verifies the producer descriptor. poll retains the prior bulk
     * receipt and validates the last map before submitting a new token. */
    if(s->plan->bulk_valid && s->plan->bulk[1]==0 && s->plan->bulk[2]==48 &&
       s->plan->bulk[3]==0 && !nes_plan200_progress(s->plan,NES_ORDINARY553))''' + failure
    if policy == 'page':
        # The ordinary map service can publish a BG while holding the next
        # page's first map on its call stack. Retire that BG, then perform one
        # normal producer progress pass before sending any map from this page.
        old = ' /* The original span still owns packet boundaries'
        new = """ if(op==2 && section==2 && !(at%2048) && n==192 && s->plan &&
    s->plan->ending && s->plan->bank_history==2 && s->plan->bulk_valid &&
    s->plan->window && s->plan->window->last[0]==7 && s->plan->window->last[1]==0 &&
    s->plan->bulk[2]==48 && !s->plan->bulk[3]){
  if(!nes_plan749_after_bg(s->plan))return fail(s,5);
 }
"""
        text = once(text, old, new+old)
        for name,anchor,addition in (
            ('nes_plan_service200.c', 'bool nes_plan200_retire(', """bool nes_plan749_after_bg(struct nes_plan200 *p){
 return complete485(p) && nes_plan200_progress(p,NES_ORDINARY553);
}
"""),
            ('nes_plan_service200.h', 'bool nes_plan200_progress(', 'bool nes_plan749_after_bg(struct nes_plan200 *);\n')):
            original = (base/'src'/name).read_text()
            (out/name).write_text(once(original,anchor,addition+anchor),newline='\n')
    elif policy == 'notice':
        text = once(text, '    if((w->status_flags&8) || !w->wait)break;',
                    '    if(w->status_flags&8){\n    '+service+'\n     break;\n    }\n    if(!w->wait)break;')
    else:
        text = once(text, '   unsigned left=w->poll_limit;',
                    '   '+service+'\n   unsigned left=w->poll_limit;')
    path.write_text(text, encoding='utf8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--policy',choices=('early','notice','page'),default='early')
    args = parser.parse_args()
    prepare(args.base,args.out,args.policy)
