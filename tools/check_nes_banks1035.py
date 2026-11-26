"""Exercise the observer and actual producer on a 15-tile/four-bank workload analogue."""
import json
import re
import shutil
from tempfile import TemporaryDirectory
from pathlib import Path
from check_nes_kirby1035 import ROOT,OUT,command


def run(tmp):
    board=OUT/'board-times'
    fixture=ROOT/'tests/nes-functional'
    names='nes_display1010 nes_domain_reset124 nes_native_mailbox206 nes_bulk_aperture188 nes_tile_bulk206 nes_chr_cache611 nes_obj_capture611 nes_e9_rows914 nes_tile205 nes_native_arbiter165 nes_source_tile192'.split()
    for f in names:shutil.copy(board/(f+'.sv'),tmp)
    shutil.copy(fixture/'tb_nes_kirby1034.sv',tmp)
    tb=(fixture/'tb_nes_kirby1026.sv').read_text()
    # Exact number of tiles, chunks, last length and slot. The original
    # BIN contains no per-tile tags or intermediate chunk lengths.
    for a,b in [('SEED+6','SEED+3'),('index_tile>=19','index_tile>=1'),('index_tile==21','index_tile==14'),
                ("[0:6]='{1,3,1,2,7,5,3}","[0:3]='{1,5,6,3}"),("[0:6]='{0,654,0,2,5,19,12}","[0:3]='{0,0,6,13}"),
                ('g<7','g<4'),('nreturn!=7','nreturn!=4'),('nreturn>=2','nreturn>=1'),('g==0?2:(g==1?0:1)','g==0?2:1'),
                ('!=640','!=464'),('scenario==4 && token==LAST && (!visible || hcycle-visible<hold_cycles)',
                                   'scenario==4 && token==SEED+1 && hcycle-pub2<hold_cycles')]:
        assert a in tb
        tb=tb.replace(a,b)
    tb=tb.replace(' wire defer_poll=', ' integer pub2=0,ret1=0,ret2=0;\n wire defer_poll=')
    tb=tb.replace('  if(bulk.state==bulk.SEAL && bulk.token==LAST)',
                  '  if(bulk.state==bulk.SEAL && bulk.token==SEED+1) pub2=hcycle;\n  if(bulk.state==bulk.SEAL && bulk.token==LAST)')
    tb=tb.replace('   nreturn++;','   if(nreturn==0)ret1=hcycle; if(nreturn==1)ret2=hcycle;\n   nreturn++;')
    tb=tb.replace('  $display("PASS1026','  $display("BANK1035 %0d %0d %0d",ret1,pub2,ret2);\n  $display("PASS1026')
    (tmp/'banks.sv').write_text(tb)
    command(tmp,'banks-lib','vlib','work')
    command(tmp,'banks-compile','vlog','-sv','+define+PUBLISH1035',*[f+'.sv' for f in names],'tb_nes_kirby1034.sv','banks.sv')
    sim=['-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0']
    log=command(tmp,'publication','vsim','-c','work.tb_nes_kirby1034',*sim)
    assert 'PASS1034' in log
    (sample,)=re.findall(r'^# HEADER1034 (\w+)',log,re.M)
    result={}
    for case in (0,1,4):
        log=command(tmp,f'banks-{case}','vsim','-c','work.tb_nes_kirby1026',f'+CASE={case}',*sim)
        assert 'PASS1026' in log
        r,w,t=map(int,re.search(r'BANK1035 (\d+) (\d+) (\d+)',log).groups())
        boundary=max(r,w)
        result[case]=dict(first_return=r,second_publish=w,second_return=t,
                          waiting_for_publish=boundary-r,published_to_return=t-boundary)
    assert result[1]['waiting_for_publish']>result[0]['waiting_for_publish']
    assert result[4]['published_to_return']>result[0]['published_to_return']
    (OUT/'banks.json').write_text(json.dumps(dict(header=sample,host_cycles=result),indent=2)+'\n')


if __name__=='__main__':
    with TemporaryDirectory(prefix='banks1035-') as d:run(Path(d))
