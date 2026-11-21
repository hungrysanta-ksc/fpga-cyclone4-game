"""Build the final SRAM-query diagnostic firmware from the tested MMC903 source."""
from prepare_nes_supply905 import BASE, WORK, rename_edition, replace
import shutil

def patch_arm():
    src=BASE/'src'
    dst=WORK/'patch'
    rename_edition(src,dst,903,905)
    for n in ('nes_frame900.h','nes_budget210.c','nes_runtime_board165.inc'):
        shutil.copyfile(src/n,dst/n)
    p=dst/'nes_frame900.h'
    replace(p,'wire[26]','wire[16]')
    replace(p,'==54','==44')
    replace(p,'rows[151];','rows[124]; uint16_t selected,score; uint8_t sample[320][8];')
    replace(p,'int read900(uint8_t *);','int page905(uint8_t *,unsigned);')
    p=dst/'nes_runtime_board165.inc'
    s=p.read_text()
    start=s.index('int read900(uint8_t *rx)')
    end=s.index('\n}',start)+2
    p.write_text(s[:start]+"""int page905(uint8_t *rx,unsigned page){
 static uint8_t query[32] __attribute__((section(".data.nes_trace_tx"),aligned(4)))={0x78};
 query[1]=page;
 return nes_native165_bulk(native_io165,query,rx,sizeof query);
}"""+s[end:],newline='\n')
    p=dst/'nes_budget210.c'
    replace(p,' if(mode900!=3 && read900(r->wire))r->valid|=4;',""" uint8_t page[32] __attribute__((aligned(4)));
 if(mode900!=3 && page905(page,0)){
  memcpy(r->wire,page,16);
  if(page[1]==0x95 && (page[2]|page[3]<<8)==r->gen){
   r->valid|=4;
   unsigned age=((page[8]|page[9]<<8)-(page[10]|page[11]<<8))&1023;
   int score=(int)(a>>6)-(int)age;
   if((r->valid&3)==3 && r->descriptor[0]==1 && r->descriptor[1]==1 &&
      page[4]<255 && page[5] && page[5]<63 && score>=(int)log->score && a<65535){
    log->selected=0;
    for(unsigned group=0;group<2;group++){
     unsigned count=r->wire[4+group];
     for(unsigned j=0;j<count;j+=2){
      if(!page905(page,group*128+j/2) || memcmp(page+1,r->wire+1,5) ||
         memcmp(page+12,r->wire+12,4))goto trace_done;
      memcpy(log->sample[group*256+j],page+16,16);
     }
    }
    log->selected=log->used;log->score=score;
   }
  }
 }
trace_done:""")
    replace(p,'memset(log900p,0,16)','memset(log900p,0,sizeof *log900p)')
    replace(p,'edition=903','edition=905')
    replace(p,'capacity=151','capacity=124')
    p=dst/'nes_menu_diagnostic.c'
    replace(p,'16+log900p->used*sizeof(struct row900)','sizeof *log900p')

if __name__=='__main__':
    patch_arm()
