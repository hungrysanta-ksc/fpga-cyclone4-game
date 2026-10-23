# SPDX-License-Identifier: MIT
import json,sys
from pathlib import Path
import guard_nes_spi314 as old
from nes_test315 import reader
old.old.TB=reader(old.old.TB,'rec314','rv314','ra314','rb314','qr','parser_retire','reset||stop')
if __name__=='__main__':
    old.old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]);assert 'PASS SPI314' in (d/'vsim.log').read_text()
    r=json.loads((d/'result.json').read_text());r.update(checks=15,shared_seal_lifetime=True,EA_reuse=True)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
