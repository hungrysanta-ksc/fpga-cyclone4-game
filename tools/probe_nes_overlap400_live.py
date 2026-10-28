# SPDX-License-Identifier: MIT
"""Separate400 ARM receive-ahead + native header DMA on unchanged398 RTL."""
import probe_nes_joint398 as previous
import probe_nes_hint367 as hint
from nes_joint398 import arm
from nes_overlap400 import apply
from nes_delta231 import once

def current_arm(d,cold_quantum=0):arm(d);apply(d)
previous.prior.old.apply_arm=current_arm
previous.prior.old.__file__=__file__
worker_source=previous.prior.old.previous.old_worker_source
def source400():
 s,ns=worker_source()
 s=once(s,'    for f in range(905,last+1):','''    for f in range(905,last+1):
        # EOF policy only: a finite replay has no input after LAST. It does
        # not move capture deadlines or supply bytes before the source FIFO.
        arm.call('source_prefetch_policy400',[int(907<=f<last)])''')
 s=once(s,'rows_reused=word(', 'prefetch_completions400=word("prefetch_completions400"),prefetch_attempts400=word("prefetch_attempts400"),prefetch_yields400=word("prefetch_yields400"),rows_reused=word(')
 s=once(s,'        tr=ep.transfers[start:]','''        tr=ep.transfers[start:]
        (d/f'after-finish400-{f}.json').write_text(json.dumps(dict(transfers=tr),indent=2)+'\\n')''')
 return s,ns
previous.prior.old.previous.old_worker_source=source400
if __name__=='__main__':previous.prior.old.main()
