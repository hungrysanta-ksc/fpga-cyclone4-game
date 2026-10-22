# SPDX-License-Identifier: MIT
"""Same whole278 boundary, raw MASK and common request context, Quartus Lite."""
import inspect
import map_nes_joint272 as prior
from nes_joint280 import patch


def main():
    ns=dict(prior.__dict__);ns.update(patch=patch,__file__=__file__,__doc__=__doc__)
    code=inspect.getsource(prior.main)
    code=code.replace('patch(d,shared=a.shared_context)','patch(d)')
    code=code.replace('nes_parser272.sv','nes_validator278.sv')
    code=code.replace("['nes_joint272.py','map_nes_joint272.py']",
        "['nes_joint278.py','nes_joint280.py','nes_exchange280.inc','nes_source_exchange280.inc','map_nes_joint280.py']")
    exec(compile(code,'map280-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
