# SPDX-License-Identifier: MIT
"""Keep 749's boot and E8. Execute the selected WRAM path with live ARM feedback."""
import argparse
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch

from replay_nes_bg750 import install_hook


if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--client',type=Path,required=True)
    args,_=p.parse_known_args()
    popen=subprocess.Popen.__init__
    def launch(proc,argv,*rest,**kwargs):
        if isinstance(argv,(list,tuple)) and '--testRunner' in argv:
            path=Path(argv[argv.index('--testRunner')+1])
            if path.name=='capture.lua':
                path.write_text(install_hook(path.read_text(encoding='utf8'),args.client,'tail'),encoding='utf8',newline='\n')
        popen(proc,argv,*rest,**kwargs)
    with patch.object(subprocess.Popen,'__init__',launch):
        runpy.run_module('test_nes_input748',run_name='__main__')
