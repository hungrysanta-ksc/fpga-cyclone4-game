"""Check both SEAL layouts, corrupted required bits, cancellation and cold restart."""
import argparse
import json
from pathlib import Path
from analyze_nes_column853 import verify_partial_stop
from guard_nes_output852 import arm_guard,run
from nes_raw506 import once
from prepare_nes_seal858 import ROOT
from replay_nes_column853 import run as replay


def coverage(temp,folder,client,case):
    pos=64 if case=='full-middle' else 128 if case=='short-obj' else 0
    def edit(packet,g,kind):
        n=int.from_bytes(packet[12:14],'little')
        assert 44<=n<=168 and not n%4 and len(packet)==16+n
        prefix=n-40
        # Accept the full fallback for generation 905 before testing a broken
        # certificate in generation 906, with the same captured map and pixels.
        full=g==905 or kind=='full-middle'
        if full:
            packet[40+prefix:40+prefix]=bytes(128-prefix)
            packet[12:14]=(168).to_bytes(2,'little')
        assert g in (905,906)
        if g==906:
            if kind=='bad-width':
                packet.pop()
                packet[12:14]=(n-1).to_bytes(2,'little')
            elif kind!='table-entry':
                packet[40+(pos if full or pos<prefix else prefix+pos-128)] |= 1
        return packet,g==906
    def corrupt(lua,labels):
        if case=='bad-width':
            return lua
        if case=='table-entry':
            site=labels['table181']
            hook=f"checkedMem527(function() if packet and pw(8)==906 then emu.write(0x10000+word(0x70)+81,255,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{site})\n"
            return once(lua,'local function loaded()',hook+'local function loaded()')
        pc=labels['coverage212']
        inject=f"""checkedMem527(function()
 if packet and pw(8)==906 and pb(0)==3 then
  local a=0x1320+word(0x1254)+{pos}
  emu.write(a,rd(a)&254,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{pc})
"""
        return once(lua,'local function loaded()',inject+'local function loaded()')
    return run(temp,folder,case,column_client=client,edit_seal=edit,adapt_lua=corrupt)


def check(temp,tag,client,arm,case):
    folder=temp/f'nes-tile821-demo-jointmirror-p1-{tag}-on'
    if case=='coverage':
        result={k:coverage(temp,folder,client,k) for k in ('short-bg','short-obj','full-middle','bad-width')}
    elif case=='table':
        result=coverage(temp,folder,client,'table-entry')
    elif case=='consumer':
        result={k:run(temp,folder,k,column_client=client) for k in ('damage','stop','late-stop')}
        result['partial']=verify_partial_stop(folder)
        result['restart']=run(temp,folder,'restart',folder/'guard-stop/canceled.bin',client)
    else:
        def selected(temp,clip,phase,policy,name,dma):
            replay(temp,clip,phase,True,name,arm=arm,client=client,
                   budget=Path.home()/'Downloads/nes-budget-mmc855.txt')
        result=arm_guard(temp,case,selected,'column_serial',tag)
    (ROOT/f'{tag}-{case}.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    cases=('coverage','consumer','identity','stop','table')
    p.add_argument('case',choices=(*cases,'all'))
    p.add_argument('--client',type=Path,default=ROOT/'client-d')
    p.add_argument('--arm',type=Path,default=ROOT/'link-c/src')
    a=p.parse_args()
    for case in cases if a.case=='all' else (a.case,):
        check(a.temp,a.tag,a.client,a.arm,case)
