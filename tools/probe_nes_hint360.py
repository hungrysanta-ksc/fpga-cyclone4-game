# SPDX-License-Identifier: MIT
"""Observe committed resident history before each first source block; no new runtime work."""
import probe_nes_host359 as previous
engine=previous.engine
old_call=engine.ARM296.call
def call(self,name,args):
 if name=='block286' and bytes(self.uc.mem_read(args[0],2))==b'N5':
  serial=int.from_bytes(self.uc.mem_read(args[0]+12,4),'little')
  (self.endpoint.d/f'prior360-{serial}.bin').write_bytes(bytes(self.uc.mem_read(0x20000000,0x40000)))
 return old_call(self,name,args)
engine.ARM296.call=call
engine.__file__=__file__
if __name__=='__main__':engine.main()
