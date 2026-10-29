# SPDX-License-Identifier: MIT
"""Assign a trial identity to an isolated NROM firmware source copy."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);p.add_argument('--label',required=True);a=p.parse_args()
assert re.fullmatch(r'nrom[0-9]+',a.label),a.label
menu=a.directory/'nes_menu_diagnostic.c';checkpoint=a.directory/'nes_checkpoint112.c'
s=menu.read_text(encoding='utf8');c=checkpoint.read_text(encoding='utf8')
for old,new in [('nes-game-last-227.txt',f'nes-game-last-{a.label}.txt'),('nes-budget-227.txt',f'nes-budget-{a.label}.txt'),('candidate=NES-GAME-227',f'candidate=NES-{a.label.upper()}'),('board_expected_hex=74','board_expected_hex=78'),('NES GAME 227.nh1',f'NES NROM {a.label[4:]}.nh1')]:
 assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new)
assert c.count('nes-progress-227.txt')==1;c=c.replace('nes-progress-227.txt',f'nes-progress-{a.label}.txt').replace('NES227 seq=',a.label.upper()+' seq=')
menu.write_text(s,encoding='utf8',newline='\n');checkpoint.write_text(c,encoding='utf8',newline='\n')
print(json.dumps({'label':a.label,'log_files':[f'nes-progress-{a.label}.txt',f'nes-game-last-{a.label}.txt',f'nes-budget-{a.label}.txt'],'board_expected_hex':'78'}))
