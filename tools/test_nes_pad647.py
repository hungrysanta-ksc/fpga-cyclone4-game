"""Clock the actual padding handler without inserting instructions in the 65816."""
import json
import runpy
from unittest.mock import patch
from nes_raw506 import once
import test_nes_tile532 as tile


def instrument(s, a):
    labels=json.loads((a.client/"labels.json").read_text())
    body=(a.client/"body.bin").read_bytes()
    start=labels["zero_chunk516"]
    assert body[start-0x7e2000]==0x20
    tail=body.index(bytes.fromhex("8d0b42c220"),start-0x7e2000,labels["word16_516"]-0x7e2000)
    sites={k:labels[k] for k in ("header","data","data_size_ok","generic548","accepted","reply","fill_receipt548")}
    sites.update(post_service=start+3,post_dma=0x7e2000+tail+3)
    if "hit647" in labels:
        sites["hit"]=labels["hit647"]
        s=once(s,"assert(fillBytes545==pw(14) and fillServiced545,'fill ACK before completion/service')",
               """local hit=fillBytes545==0 and pb(0)==5 and pb(1)==5 and pw(16)==0 and pw(10)+pw(14)==1121
   assert((fillBytes545==pw(14) or hit) and fillServiced545,'fill ACK before completion/service')
   if hit then sample516('reuse647',pw(14)) end""")
        s=once(s,"for j=0,fillBytes545-1 do assert(rd(address+j)==pb(16)",
               "for j=0,pw(14)-1 do assert(rd(address+j)==pb(16)")
    hooks=[]
    for k,pc in sites.items():
        hooks.append(f"""emu.addMemoryCallback(function()
 if packet and pb(0)==5 and pb(1)==5 and (pw(8)==954 or pw(8)==955) and pw(14)==1100 then sample516('pad_{k}')end
end,emu.callbackType.exec,{pc})""")
    return once(s,"local function loaded()","\n".join(hooks)+"\nlocal function loaded()")


if __name__=="__main__":
    original=tile.run_schedule
    def run(a, observe, link, frames):
        return original(a,lambda s,args:instrument(observe(s,args),args),link,frames)
    with patch.object(tile,"run_schedule",run):
        runpy.run_module("test_nes_export636",run_name="__main__")
