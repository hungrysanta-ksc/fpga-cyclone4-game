# SPDX-License-Identifier: MIT
"""Run unchanged STOP-aware65816 code on the actual split ARM packets."""
import inspect
import probe_nes_ordinary269 as old
from nes_delta231 import once

def main():
 ns=dict(old.old.__dict__)
 ns.update(rom=old.rom,
  LUA=once(old.old.LUA,"if a==0x6000 then return","if a==0x6001 then return event(0,a,0) elseif a==0x6000 then return"),
  __file__=__file__,__doc__=__doc__)
 s=inspect.getsource(old.old.main)
 s=once(s,"probes/nes-joint264/arm01/frame","probes/nes-joint274/arm01/frame")
 exec(compile(s,'ordinary274-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
