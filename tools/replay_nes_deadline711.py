"""Unchanged65816 acceptance-deadline sensitivity, not an ARM implementation.

Immutable707D packet bytes/work and all independent pixel/DMA/ACK oracles are
retained. Earlier availability is a hypothetical budget; SPI E1 service,
FIFO order, four credits, two bulk owners and prior display ACK are retained.
ARM/ROM/source readiness debt is reported separately, never treated as free.
"""
import argparse,csv,json,os,shutil,subprocess
from pathlib import Path
from analyze_nes_output615 import read,sha,csv_groups,one,packets,ms
from nes_raw506 import once
from trace_nes_tail522 import CLOCKED_INPUT

def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    j=read(a.trace/'joint.json');assert j['passed'] and j['commits']==53
    assert sha(a.client/'sink165.sfc')==sha(a.trace/'client.sfc')==j['client_SHA256']
    shutil.copyfile(a.trace/'client.sfc',a.out/'client.sfc')
    for pattern in ('map-*.bin','expected-*.bin','colors636-*.bin'):
        for p in a.trace.glob(pattern):shutil.copyfile(p,a.out/p.name)
    events=read(a.trace/'events.json');spi=[e for e in events if e.get('opcode')=='0xe1']
    ps=[json.loads(s) for s in (a.trace/'packets.jsonl').read_text().splitlines()]
    assert len(ps)==len(spi)
    last_tile={}
    for i,(_,t,h,b) in enumerate(ps):
        h=bytes.fromhex(h);g=int.from_bytes(h[8:10],'little')
        if h[0]==7:last_tile[g]=i
    advance=round(a.advance_us*21.477272);rows=[];ledger=[];previous=0
    tail_gap=getattr(a,'tail_gap_us',0)
    if tail_gap and (a.mode!='all' or a.generation!=a.through or tail_gap>a.advance_us or tail_gap<0):
        raise ValueError('A tail gap requires one full generation and must fit within the requested advance')
    for i,((_,t,h,b),e) in enumerate(zip(ps,spi,strict=True)):
        h=bytes.fromhex(h);g=int.from_bytes(h[8:10],'little');assert abs(t-e['clock'])<=1
        selected=a.generation<=g<=a.through and (a.mode=='all' or a.mode=='seal' and h[0]==3 or a.mode=='tail' and i>last_tile[g])
        desired=t-advance if selected else t
        if selected and i>last_tile[g] and h[1]!=2 and tail_gap:
            desired+=round(tail_gap*21.477272)
        # Retain each E1 wire+driver duration, including headers/request CRC.
        duration=e['clock']-e['start']
        offer=max(desired,round(previous+duration)) if selected else t
        assert offer>=previous,(g,i)
        rows.append(f'{offer}\t{h.hex()}\t{b}')
        if selected:ledger.append(dict(index=i+1,generation=g,op=h[0],section=h[1],offset=int.from_bytes(h[10:12],'little'),
            baseline_push=t,offer=offer,advance_ms=ms(t-offer),wire_B=e['bytes'],retained_SPI_ms=ms(duration)))
        previous=offer
    (a.out/'arrivals.tsv').write_text('\n'.join(rows+[f'{previous+1}\tFINISH\t'])+'\n',encoding='ascii',newline='\n')
    s=(a.trace/'capture.lua').read_text(encoding='utf8')
    s=once(s,'local ROOT='+json.dumps(a.trace.resolve().as_posix()),'local ROOT='+json.dumps(a.out.as_posix()))
    start=s.index('local sequence=0;');end=s.index('local progressLog=',start)
    releases='\n'.join(f"sourceRelease[{g['generation']}]={g['release_masterclock']}" for g in j['frames'])
    clocked=CLOCKED_INPUT.replace("  assert(sent-retired<4,'queue overflow')",'''  if sent-retired>=4 then return end
  local incoming711=unhex(b522);local g711=incoming711:byte(9)+256*incoming711:byte(10)
  if g711>905 and not retiredAt[sealIndex[g711-906]]then return end
  if incoming711:byte(1)==7 and bulkOwned711>=2 then return end''')
    clocked=once(clocked,'  frames[sent]=g-905;', '''  if requests[sent]:byte(1)==7 then bulkOwned711=bulkOwned711+1 end
  assert(bulkOwned711<=2 and sent-retired<=4)
  admission711:write(string.format('%d,%d,%d,%d,%d,%d\\n',sent,g,target522,now,sent-retired,bulkOwned711));admission711:flush()
  frames[sent]=g-905;''')
    pre="local bulkOwned711=0\nlocal admission711=assert(io.open(ROOT..'/admission711.csv','w'));admission711:write('index,g,offer,admit,depth,bulk\\n')\n"
    s=s[:start]+releases+"\nlocal function unhex(b)return (b:gsub('..',function(c)return string.char(tonumber(c,16))end))end\n"+pre+clocked+s[end:]
    # Poll and DMA callbacks observe immutable arrivals exactly as the prior
    # no-pipe527 replay. Avoid an expensive Lua callback on every instruction;
    # require a clock-identical control before trusting changed schedules.
    s=once(s,'checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    a0=s.index('checkedEvent527(function()\n if sequence==1');a1=s.index('end,emu.eventType.endFrame)',a0)+len('end,emu.eventType.endFrame)')
    s=s[:a0]+s[a1:]
    s=once(s,'  consumed[#consumed+1]=','  assert(bulkOwned711>0);bulkOwned711=bulkOwned711-1\n  consumed[#consumed+1]=')
    (a.out/'capture.lua').write_text(s,encoding='utf8',newline='\n')
    with (a.out/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'client.sfc'),'--timeout=600',
            '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
            cwd=a.out,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
            stdout=log,stderr=subprocess.STDOUT,timeout=650,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    r=read(a.out/'result.json');assert r['passed'] and r['commits']==53
    before=csv_groups(a.trace/'window.csv');after=csv_groups(a.out/'window.csv')
    if a.mode=='control':assert before==after,'control differs from original coupled execution'
    else:
        assert all(before[g]==after[g] for g in before if g<a.generation),'prefix differs'
    for g in range(905,958):assert sha(a.out/f'frame-{g}.rgb')==sha(a.trace/f'frame-{g}.rgb'),g
    metrics={}
    for g in range(951,958):
        seal=[e for e in after[g] if e['op']==3];old=[e for e in before[g] if e['op']==3]
        prev=one([e for e in after[g-1] if e['op']==3],'reveal');show=one(seal,'reveal')
        metrics[g]=dict(load=one(seal,'load'),show=show,ACK=one(seal,'ack')['clock'],
            interval_VBlank=show['frame']-prev['frame'],interval_ms=ms(show['clock']-prev['clock']),
            show_frame_delta=show['frame']-one(old,'reveal')['frame'],show_delta_ms=ms(show['clock']-one(old,'reveal')['clock']),
            final_waits=sum(e['event']=='wait169' and e['clock']>=one(seal,'final212')['clock'] for e in seal),
            seal_load_advance_ms=ms(one(old,'load')['clock']-one(seal,'load')['clock']))
    out=dict(passed=True,scope=__doc__,mode=a.mode,generation=a.generation,through=a.through,advance_us=a.advance_us,
        metrics=metrics,tail_gap_us=getattr(a,'tail_gap_us',0),offers=ledger,same_pixels=True,full_CRC_coverage_ACK=True,client_SHA256=sha(a.out/'client.sfc'),
        dense_mean_ms=sum(metrics[g]['interval_ms'] for g in range(951,956))/5,
        last_ACK=metrics[957]['ACK'],prefix_exact=True,new_ARM=False,new_FPGA=False,
        pins={n:sha(a.out/n) for n in ('capture.lua','arrivals.tsv','window.csv','admission711.csv','result.json','seal528.csv','budget685.csv')})
    (a.out/'audit711.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:out[k] for k in ('mode','generation','through','advance_us','dense_mean_ms','last_ACK')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('trace','client','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',choices=['control','seal','tail','all'],required=True)
    p.add_argument('--generation',type=int,default=951);p.add_argument('--through',type=int,default=957)
    p.add_argument('--advance-us',type=int,default=0)
    p.add_argument('--tail-gap-us',type=int,default=0,help='Extra time before ordinary/SEAL following the last tile and map (sensitivity only)')
    run(p.parse_args())
