# SPDX-License-Identifier: MIT
"""Observe a cartridge that boots directly from the packed 751 image."""
import runpy
from pathlib import Path
from unittest.mock import patch
import subprocess

from nes_raw506 import once


def observer(s):
    return once(s,'(i<tail or n<=160)',
                '(i<tail or n<=160 or ((src&0x7000)==0x4000 and n==288))')


if __name__=='__main__':
    popen=subprocess.Popen.__init__
    def launch(proc,argv,*rest,**kwargs):
        if isinstance(argv,(list,tuple)) and '--testRunner' in argv:
            script=Path(argv[argv.index('--testRunner')+1])
            if script.name=='capture.lua':
                script.write_text(observer(script.read_text(encoding='utf8')),encoding='utf8',newline='\n')
        popen(proc,argv,*rest,**kwargs)
    with patch.object(subprocess.Popen,'__init__',launch):
        runpy.run_module('test_nes_input748',run_name='__main__')
