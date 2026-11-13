# SPDX-License-Identifier: MIT
"""Reuse the physical E1, map-write and RGB oracles for checked section-2 opcode 9."""
import runpy
from unittest.mock import patch

from test_nes_raw506_joint import Runtime
import test_nes_static751
from nes_raw506 import once

if __name__=='__main__':
    import subprocess
    from pathlib import Path
    launch=subprocess.Popen.__init__
    def start(proc, argv, *args, **kwargs):
        if isinstance(argv,(list,tuple)) and '--testRunner' in argv:
            script=Path(argv[argv.index('--testRunner')+1])
            if script.name=='capture.lua':
                original=script.read_text(encoding='utf8')
                script.write_text(once(original,'(pb(0)==2 or pb(0)==4) then',
                                       '(pb(0)==2 or pb(0)==4 or pb(0)==9) then'),encoding='utf8',newline='\n')
        return launch(proc,argv,*args,**kwargs)
    with patch.object(Runtime,'linked_runtime_storage',True,create=True),patch.object(subprocess.Popen,'__init__',start):
        runpy.run_module('test_nes_static751',run_name='__main__')
