# SPDX-License-Identifier: MIT
"""Run retained semantic/preflight/wrap guards on the integrated inline ELF."""
import inspect
import guard_nes_arm264 as old
import guard_nes_split274 as split
from probe_nes_inline275 import Endpoint
from probe_nes_split274 import verify

def main():
 ns=dict(old.__dict__);ns.update(Endpoint=Endpoint,verify=verify,__doc__=__doc__)
 body=inspect.getsource(old.BadStatus.transfer).replace('super().transfer(tx)','Endpoint.transfer(self,tx)')
 exec('class BadStatus(Endpoint):\n def __init__(self,case):super().__init__();self.case=case\n'+body,ns)
 exec(compile(inspect.getsource(old.main),'arm275-base','exec'),ns);ns['main']()
 ns=dict(split.__dict__);ns.update(Endpoint=Endpoint,__file__=__file__,__doc__=__doc__)
 code=inspect.getsource(split.main)
 a=code.index(' saved=');b=code.index(' ap=argparse',a)
 code=code[:a]+code[b:]
 exec(compile(code,'arm275-split','exec'),ns);ns['main']()

if __name__=='__main__':main()
