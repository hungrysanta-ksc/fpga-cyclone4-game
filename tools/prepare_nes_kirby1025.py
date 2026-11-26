"""Sample a completed display in each 400 ms interval independently of map size."""
import shutil

from prepare_nes_kirby1024 import WORK as PREVIOUS
from prepare_nes_trial802 import rename_edition


WORK = PREVIOUS.with_name('nes-kirby1025')


def prepare():
    src = WORK / 'link/src'
    shutil.copytree(PREVIOUS / 'link', src.parent)
    edition = WORK / 'edition'
    rename_edition(PREVIOUS / 'link/src', edition, 1024, 1025)
    for path in edition.iterdir():
        shutil.copy2(path, src / path.name)

    path = src / 'nes_budget210.c'
    code = path.read_text()
    assert code.count('edition=1024;') == 1
    code = code.replace('edition=1024;', 'edition=1025;')
    start = code.index(' || r->obj!=18 || r->dirty!=23')
    end = code.index(' current1012.tick=', start)
    code = code[:start] + ''')return;
 unsigned slot = r->tick >= 5750;
 if(log900p->trace[slot].count)return;
''' + code[end:]
    start = code.index(' unsigned w=', code.index('static void record900'))
    end = code.index(' memset(r,0', start)
    code = code[:start] + ''' if(tick<3000 || tick>=6000 || (mode900==1 && tick>=3500) ||
    (mode900==2 && tick<5500))return;
 struct log900 *log=log900p;
 unsigned used=log->used;
 if(used && log->rows[used-1].tick/40==tick/40)return;
 if(used>=log->capacity){++log->drop[tick>=5500];return;}
 struct row900 *r=&log->rows[log->used++];
 unsigned dirty=__builtin_popcountll(v->map_dirty);
''' + code[end:]
    path.write_bytes(code.encode())


if __name__ == '__main__':
    prepare()
