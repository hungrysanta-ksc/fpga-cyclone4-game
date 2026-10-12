# SPDX-License-Identifier: MIT
"""Factor the common CHECK command inhibit after the loader conflict decoder."""
from pathlib import Path
import argparse,json,re,shutil,difflib
from nes_game147 import ROOT,sha

def loader(s):
    declaration=' input wire load_begin,load_chr32,load_valid,load_end,start,stop,input wire [7:0] load_data,'
    assert s.count(declaration)==1
    s=s.replace(declaration,declaration+'\n input wire commands_blocked,')
    at=s.index(' localparam IDLE=')
    head,body=s[:at],s[at:]
    conflict='(load_begin && (load_end || start || stop || load_valid)) || (load_end && (start || stop || load_valid)) || (start && (stop || load_valid))'
    assert body.count(conflict)==1
    body=body.replace(conflict,'command_conflict')
    for n in ['load_begin','load_valid','load_end','start']:
        body=re.sub(r'\b'+n+r'\b','accepted_'+n,body)
    wires=' wire command_conflict=!commands_blocked && ('+conflict+');\n'
    wires+=''.join(f' wire accepted_{n}={n} && !commands_blocked;\n' for n in ['load_begin','load_valid','load_end','start'])
    return head+wires+body

def boot(s):
    for n in ['load_begin','load_valid','load_end','start']:
        old=f'.{n}({n} && !check_failed)';assert s.count(old)==1
        s=s.replace(old,f'.{n}({n})')
    needle='nes_rom_loader loader(';assert s.count(needle)==1
    return s.replace(needle,needle+'.commands_blocked(check_failed),')

def spi(s):
    start=s.index(' reg [7:0] reply;');end=s.index(' task automatic fail',start)
    s=s[:start]+s[end:]
    old='miso_hold<=reply[7-bit_count];';assert s.count(old)==1
    s=s.replace(old,"miso_hold<=(byte_count>=1 && byte_count<=7)?snapshot[55]:1'b0;")
    old='shift<=incoming;bit_count<=bit_count+1\'b1;';assert s.count(old)==1
    s=s.replace(old,old+"\n    if(byte_count>=1 && byte_count<=7)snapshot<={snapshot[54:0],1'b0};")
    return s

def retire(s):
    # Decode disjoint clear/increment enables directly rather than threading
    # every counter bit through the complete error-code/command priority mux.
    old='check_next<=0;';assert s.count(old)==4
    s=s.replace(old,'')
    start=s.index('        // Bitwise carry prefixes')
    end=s.index('\n       end',start)
    s=s[:start]+s[end:]
    at=s.index(' task automatic fail')
    logic=''' wire retire_ok=!fault && pending && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) &&
  !(check_response && (!check_enable || !check_busy || check_response_address!=check_next)) &&
  pending_header_error==0 && pending_causes==0;
 wire counter_clear=retire_ok && (pending_command==0 || pending_command==4 || pending_command==6);
 wire counter_inc=retire_ok && pending_command==8;
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else begin
'''
    for i in range(19):
        carry="1'b1" if i==0 else f'(&check_next[{i-1}:0])' if i<8 else 'next_carry8' if i==8 else f'(next_carry8 && (&check_next[{i-1}:8]))'
        logic+=f'   check_next[{i}] <= (check_next[{i}] ^ (counter_inc && {carry})) && !counter_clear;\n'
    logic+='  end\n'
    return s[:at]+logic+s[at:]

def prepare(baseline,out,variant='serial'):
    assert not out.exists() and str(out).isascii()
    pub=json.loads((ROOT/'analysis/check165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==pub['raw_result_sha256']['map03']
    meta=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in meta['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    changes=[('nes_rom_loader.sv',loader),('nes_rom_boot.sv',boot)]
    if variant=='serial':changes.append(('nes_rom_spi.sv',spi))
    elif variant=='retire':changes.append(('nes_rom_spi.sv',lambda s:retire(spi(s))))
    else:assert variant=='loader'
    for n,fn in changes:
        p=out/n;before=p.read_text();after=fn(before);p.write_text(after,encoding='utf8')
        (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
    m=dict(variant=variant,baseline=meta['sources'],sources={n:sha(out/n) for n in meta['sources']},public_sources={'tools/nes_retire165.py':sha(Path(__file__))})
    m['changed']=[n for n in m['sources'] if m['sources'][n]!=m['baseline'][n]]
    assert sorted(m['changed'])==sorted(n for n,_ in changes)
    (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--variant',choices=['loader','serial','retire'],default='serial')
    a=p.parse_args();prepare(a.baseline,a.out,a.variant)
