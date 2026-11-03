# SPDX-License-Identifier: MIT
"""Derive END illegality from the existing DATA legality and live write phases."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_mailbox567 import prepare as mailbox567


def prepare(base, out, phase_only=False, late_select=False):
    mailbox567(base, out, local_ports=True)
    path = out/'nes_rom_loader.sv'
    if late_select:
        # Keep the existing registered result and its consumers. Decode both
        # choices before the CHECK failure selection; never delay STOP or fault.
        source=once(path.read_text(), ' // State-only legality advances', """ wire quiet_cmd=!(load_begin || load_end || start);
 wire timed_end_state=phase[SETUP] || (phase[RELEASE] && (stop || !terminal));
 wire resident_end_state=from_ir || phase[RUN];
 wire end_blocked=resident_end_state || timed_end_state || (phase[RECEIVE] && stop);
 wire end_command=(resident_end_state && quiet_cmd && (stop || !load_valid)) ||
     (phase[READY] && start && !load_begin && !load_end && !stop && !load_valid) ||
     (phase[RECEIVE] && !load_begin && !start &&
       ((stop && !load_end) || (!stop && ((load_end && !load_valid && count_complete) ||
                                         (!load_end && load_valid && !count_complete))))) ||
     (timed_end_state && quiet_cmd);
 // WRITE and HOLD always preserve the END rejection while draining,
 // including on the first edge of a STOP or sticky fault.
 wire reject_end_next=phase[WRITE] || phase[HOLD] ||
     (!fault && (commands_blocked ? end_blocked : end_command));
 // State-only legality advances""")
        source=once(source,'reject_state[2]<=to_idle || to_ready || to_run || to_setup || to_write || to_hold || to_release;',
                    'reject_state[2]<=reject_end_next;')
        path.write_text(source,newline='\n')
        return
    s = once(path.read_text(), 'reg [3:0] reject_state;', '''reg [1:0] reject_state;
 (* preserve, dont_merge *) reg reject_data_state;
 // DATA is rejected in IDLE, READY or RUN. END also rejects all timed phases.
 wire timed_phase=(phase[SETUP] || phase[WRITE] || phase[HOLD] || phase[RELEASE]);''')
    s = once(s, ' wire timed_phase=(phase[SETUP] || phase[WRITE] || phase[HOLD] || phase[RELEASE]);\n wire phase_step=', ' wire phase_step=')
    s = once(s, 'reject_state[2] || (phase[RECEIVE]', 'reject_data_state || timed_phase || (phase[RECEIVE]')
    s = once(s, 'reject_state[3] || (phase[RECEIVE]', 'reject_data_state || (phase[RECEIVE]')
    for predicate in ('if(reset)', 'else if(active_reset)'):
        s = once(s, predicate+"reject_state<=4'b1110;", predicate+"{reject_data_state,reject_state}<=3'b110;")
    s = once(s, '   reject_state[2]<=to_idle || to_ready || to_run || to_setup || to_write || to_hold || to_release;\n', '')
    s = once(s, 'reject_state[3]<=to_idle', 'reject_data_state<=to_idle')
    if phase_only:
        # All four saved predicates duplicate groups of current phase bits.
        # Keep the explicit groups so unused encodings retain their old behavior.
        first=s.index(' // Bits0..3 reject')
        end=s.index(' wire illegal_begin',first)
        s=s[:first]+''' wire timed_phase=phase[SETUP] || phase[WRITE] || phase[HOLD] || phase[RELEASE];
 wire reject_data_state=phase[IDLE] || phase[READY] || phase[RUN];
 wire reject_begin=phase[RECEIVE] || phase[RUN] || timed_phase;
 wire reject_start=phase[IDLE] || reject_begin;
'''+s[end:]
        s=once(s,'load_begin && reject_state[0]','load_begin && reject_begin')
        s=once(s,'start && reject_state[1]','start && reject_start')
        first=s.index(' // State-only legality advances')
        s=s[:first]+s[s.index(' wire count_stop=',first):]
    path.write_text(s, newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument('--'+k,type=Path,required=True)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--phase-only',action='store_true')
    group.add_argument('--late-select',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.phase_only,a.late_select)
