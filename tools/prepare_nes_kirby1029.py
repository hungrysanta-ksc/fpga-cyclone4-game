"""Replace late output packet tracing with generation-bound D1/restore/D2 accounting."""
import shutil
import sys

from prepare_nes_kirby1025 import WORK as REFERENCE
from prepare_nes_trial802 import rename_edition


def change(path, old, new):
    data = path.read_bytes()
    assert data.count(old.encode()) == 1, (path.name, old)
    path.write_bytes(data.replace(old.encode(), new.encode()))


def prepare(edition):
    assert edition in (1029, 1030)
    work = REFERENCE.with_name(f'nes-kirby{edition}')
    src = work / 'link/src'
    shutil.copytree(REFERENCE/'link', src.parent)
    rename_edition(REFERENCE/'link/src', work/'edition', 1025, edition)
    for f in (work/'edition').iterdir():
        shutil.copy2(f, src/f.name)

    hdr = src/'nes_frame900.h'
    change(hdr, 'struct log900 {', '''struct ingress1029 {
 uint32_t first, end, d1, restore, retire, bytes;
 uint16_t gen, blocks;
};
_Static_assert(sizeof(struct ingress1029)*83<=sizeof(struct trace1012)*3,"observer scratch");
void block1029(unsigned,unsigned,unsigned,const uint32_t *);
struct log900 {''')
    change(hdr, 'struct trace1012 trace[3];', 'union {struct trace1012 trace[3]; struct ingress1029 ingress[83];};')
    budget = src/'nes_budget210.c'
    change(budget, 'edition=1025;', f'edition={edition};')
    data = budget.read_text()
    data = data[:data.index('#define current1012')] + data[data.index('static struct row900 *pending950;'):]
    data = data.replace('if(match)keep1012(r);', '')
    data = data.replace('active1012=0;pending950', 'pending950')
    budget.write_bytes(data.encode())
    change(budget, 'void input900(uint16_t g){', '''/* Slots 80/81 follow the two input completion marks; 82 is the receiver. */
void block1029(unsigned begin,unsigned gen,unsigned n,const uint32_t *t){
 struct ingress1029 *a=&log900p->ingress[82];
 if(begin)*a=(struct ingress1029){.gen=gen,.first=t[0]};
 else if(!a->blocks || a->gen!=gen)return;
 ++a->blocks; a->bytes+=n; a->end=t[3];
 a->d1+=t[1]-t[0]; a->restore+=t[2]-t[1]; a->retire+=t[3]-t[2];
}
void input900(uint16_t g){''')
    change(budget, 'in900[latest900]=(struct mark900){nes_cost471_now(),g,1};',
           'in900[latest900]=(struct mark900){nes_cost471_now(),g,1};\n log900p->ingress[80+latest900]=log900p->ingress[82];\n log900p->ingress[82].blocks=0;')
    change(budget, 'r->input_age=a;r->valid|=1;', '''r->input_age=a;r->valid|=1;
  struct ingress1029 *m=&log->ingress[80+i];
  if(m->blocks && m->gen==r->gen)log->ingress[used]=*m;''')
    # Remove the replaced output observer at the call sites. Credit checks themselves stay.
    for filename, snippet in [('nes_native_sink165.c','ready1012(b);'),
            ('nes_sink_window184.c','if(delta)credit1012(r);'),('nes_sink_window184.c','issue1012(s->sent);'),
            ('nes_sink_window184.c','sent1012();')]:
        change(src/filename,snippet,'')
    rx = src/'nes_native165.c'
    change(rx,'if(!fn(ctx,tx,rx,n+3))','uint32_t t[4];t[0]=nes_cost471_now();\n if(!fn(ctx,tx,rx,n+3))')
    change(rx,'if(crc_xmodem_block(0xffff,rx+1,n)', 't[1]=nes_cost471_now();\n if(crc_xmodem_block(0xffff,rx+1,n)')
    change(rx,'nes_rom_spi_frame(tx,0xd2,tok,0);','unsigned begin=n>=12 && rx[1]==0xe0 && rx[2]==0;\n t[2]=nes_cost471_now();\n nes_rom_spi_frame(tx,0xd2,tok,0);')
    change(rx,'if(s->state==NES_NATIVE165_COMPLETE)input900', '''t[3]=nes_cost471_now();
 block1029(begin,s->generation,n,t);
 if(s->state==NES_NATIVE165_COMPLETE)input900''')
    # The COMMIT control packet following COMPLETE cannot start a new measurement.


if __name__=='__main__':
    prepare(int(sys.argv[1]))
