"""Cancel alternating words at both interior service points, then cold restore both banks."""
import argparse
import json
from pathlib import Path

from guard_nes_output852 import run
from nes_raw506 import once


def verify(temp, trial, client):
    results = {}
    for g, prefix in ((949, 64), (950, 128)):
        name = f'word-{g}-{prefix}'

        def inject(lua, labels):
            condition = f'packet and pb(0)==4 and pb(1)==2 and pw(8)=={g} and pw(10)==2240'
            lua = once(lua, f'packet and pb(0)==10 and pw(8)=={g} then',
                       f"{condition} and emu.getState()['cpu.x']==word(0x7a)+{prefix} then")
            lua = once(lua, f"end,emu.callbackType.exec,{labels['column_service']})",
                       f"end,emu.callbackType.exec,{labels['word_service873']})")
            # Poison the inactive destination immediately before its first store.
            hook = f"""
checkedMem527(function()
 if {condition} and emu.getState()['cpu.x']==word(0x7a) then
  assert(pw(12)==2 and pw(14)==192 and pw(16)==0x21b8)
  for i=0,191 do emu.write(0x10000+word(0x7a)+i,0xcd,emu.memType.snesWorkRam) end
 end
end,emu.callbackType.exec,{labels['repeat1814']})
"""
            return once(lua, 'local function loaded()', hook+'local function loaded()')

        result = run(temp, trial, 'stop', column_client=client, column_op=10,
                     edit_seal=lambda b, gen, case: (b, gen == g), adapt_lua=inject, output_name=name)
        saved = trial/f'guard-{name}/canceled.bin'
        memory = saved.read_bytes()
        bank = (g-905) & 1
        at = bank*4096+2240
        assert memory[at:at+192] == bytes.fromhex('b821')*(prefix//2)+b'\xcd'*(192-prefix)
        assert memory[(1-bank)*4096:(2-bank)*4096] == (trial/f'map-{g-1}.bin').read_bytes()
        recovery = run(temp, trial, 'restart', seed=saved, column_client=client,
                       column_op=10, output_name=name+'-restart')
        results[name] = dict(stop=result, cold=recovery, prefix_B=prefix, active_bank_intact=True)
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('temp', 'trial', 'client', 'out'):
        p.add_argument(name, type=lambda s: Path(s).resolve())
    args = p.parse_args()
    args.out.write_text(json.dumps(verify(args.temp, args.trial, args.client), indent=2)+'\n')
