# SPDX-License-Identifier: MIT
"""Keep first-fault telemetry consistency separate from SDF sensitivity results."""
from pathlib import Path
import argparse,collections,hashlib,json,re
from decode_nes_h1_edge import decode

def hardware(text):
 d=decode(text);c=d.get('frontend_capture',{});a=d.get('snapshot',{})
 if not d.get('frontend_capture_valid'):return {'decoded':d,'causal_consistency':'unavailable'}
 mask=int(c['cause_mask_hex'],16)
 projected=(bool(mask&15)*1)|(bool(mask&32)*2)|(bool(mask&16)*4)|(bool(mask&64)*8)
 aggregate=a.get('frontend_mask',0)
 consistent=(aggregate&projected)==projected
 return {'decoded':d,'cause_implied_frontend_mask':projected,'aggregate_first_frontend_mask':aggregate,
  'causal_consistency':'matching_error_bits' if consistent else 'aggregate_first_not_frontend' if aggregate==0 else 'different_first_error_bits',
  'interpretation':'Different first error classes: do not diagnose payload order from the causal byte alone. Ideal RTL schedules the implied sticky bit from the same predicate; physical input timing and capture ordering remain under investigation.' if not consistent else 'Error classes match; this alone does not prove physical cause.',
  'hardware_root_cause_proven':False}

def gate(folder):
 p=folder/'gate.log';s=p.read_text(errors='replace');groups=collections.Counter()
 for line in s.splitlines():
  if 'Process:' in line:
   if 'frontend_error' in line:label='frontend_sticky_error'
   elif 'frontend_snapshot' in line:label='frontend_capture'
   elif 'rd_sync[0]' in line or 'wr_sync[0]' in line:label='control_first_stage'
   elif 'addr_meta' in line or 'data_meta' in line:label='bundle_first_stage'
   elif 'low_count' in line or 'high_count' in line or 'sampled_read_n' in line:label='unsynchronized_strobe_counters'
   elif 'rom_address' in line or 'program_rom' in line:label='ROM_address_sampling'
   else:label='other'
   groups[label]+=1
 return {'gate_log_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'SDF_applied':'SDF Backannotation Successfully Completed' in s,'timing_violations':len(re.findall(r'\*\* Error: \$(?:hold|setup|setuphold|recovery|removal|width)',s)),'timing_process_groups':dict(groups),'fatal':bool(re.search(r'\*\* Fatal:',s)),'result_lines':[x.removeprefix('# ') for x in s.splitlines() if 'GATE MISMATCH' in x or 'GATE RAW' in x or 'GATE STATUS' in x or 'PASS GATE' in x],'limitation':'Vendor timing notifiers remain enabled. First-stage asynchronous sampling violations and X propagation are not proof of the same hardware failure. Fitted internal snapshot vector aliases can have optimized-away undriven Z bits, even in the passing control; do not decode those aliases as hardware telemetry. No timing-check suppression or hardware signoff.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--hardware-log',type=Path,required=True);p.add_argument('--gate',type=Path,action='append',default=[]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result={'hardware':hardware(a.hardware_log.read_text(encoding='utf-8-sig')),'gate_runs':{str(f):gate(f) for f in a.gate}}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
