"""Materialize the two 1055 ARM builds from their paired 1054 sources."""
import shutil
from pathlib import Path
from prepare_nes_kirby1023 import edit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'probes/nes-pair1055'

def stair_rows(src):
    name='nes_planner211.c'
    edit(src,name,
         ('static unsigned epoch(', '''static unsigned raw1055(const struct nes_native165 *s,unsigned y,const uint8_t slots[7]){
 return patched(s,y)?slots[(s->raster[y]>>50)&7]:255;
}
static unsigned epoch('''),
         ('unsigned raw_count=0;', 'uint8_t slots[7];unsigned raw_count=0;'),
         ('for(unsigned x=0;x<256;x++)if(pixels[x]>=64)return fail(p,15);',
          '''unsigned different=0;
   for(unsigned x=0;x<256;x++){
    if(pixels[x]>=64)return fail(p,15);
    different|=pixels[x]^s->palette[0];
   }
   slots[raw_count-1]=different!=0;'''),
         ('if(raw_count!=s->patch_count)return fail(p,15);', '''if(raw_count!=s->patch_count)return fail(p,15);
 /* A visible backdrop band already reserves blank map row 31. Its palette
  * and tile zero are valid for both banks. Only fold a composed line if
  * every pixel, including any sprite crossing the wipe, matches CGRAM 0. */
 p->patch_count=0;
 for(unsigned i=0;i<raw_count;i++)
  slots[i]=(!backdrop_used||slots[i])?p->patch_count++:255;'''),
         ('if(patched(s,y)){\n   prior_fine=8;', 'unsigned slot=raw1055(s,y,slots);\n  if(slot!=255){\n   prior_fine=8;'),
         ('(((s->raster[y]>>50)&7)-y-1)', '(slot-y-1)'),
         ('if(backdrop1046(s,y)){\n   prior_fine', 'if(patched(s,y)||backdrop1046(s,y)){\n   prior_fine'),
         ('for(unsigned slot=0;slot<p->patch_count;slot++){\n   const uint8_t *pixels=nes_native181_pixels(s,slot);',
          '''for(unsigned i=0;i<raw_count;i++){
   unsigned slot=slots[i];if(slot==255)continue;
   const uint8_t *pixels=nes_native181_pixels(s,i);'''),
         ('bool raw=patched(s,y);','bool raw=raw1055(s,y,slots)!=255;'),
         ('&&patched(s,n)==raw','&&(raw1055(s,n,slots)!=255)==raw'))

def wait_budget(src):
    edit(src,'nes_checkpoint_host.c',
         ('enum { STATE_WORDS=2658, BAT_BYTES=8192 };','''/* 12,288 x 104 SPI clocks at 2.625 MHz gives a stalled endpoint at
 * least the former GPIO poll window, even without any software delay. */
enum { STATE_WORDS=2658, BAT_BYTES=8192, CHECKPOINT_POLLS=12288 };'''),
         ('i<2048','i<CHECKPOINT_POLLS'))

def retail_reset(src):
    edit(src,'nes_cf86_session094.c',
         ('snes_reset(1);phase094=ARMED094;return nes_cf86_check094();', '''snes_reset(1);phase094=RELEASING146;
 /* As on release, tolerate only the RESET sense transition. STOP must
  * wait for physical assertion; the other ownership checks stay live. */
 for(unsigned ms=0;ms<20;ms++){
  if(!nes_cf86_check094())return false;
  if(get_snes_reset()){phase094=ARMED094;return nes_cf86_check094();}
  if(!nes_return_delay(1,true))break;
 }
 return nes_cf86_fail094();'''))

def prepare(profile):
    prior = 'nes-pair1054r2' if profile == 'release' else 'nes-pair1054'
    link = OUT / profile / 'link'
    shutil.copytree(OUT.parent / prior / profile / 'link', link)
    src = link / 'src'
    stair_rows(src)
    wait_budget(src)
    gpio = 'nes_checkpoint_gpio.inc'
    original = (src / gpio).read_text()
    start = original.index('static bool checkpoint_exchange')
    end = original.index('static bool ff3_writing_save;', start)
    edit(src, gpio, (original[start:end], '''static bool __attribute__((noinline,noclone)) checkpoint_exchange(const uint8_t tx[13],uint8_t rx[13])
{
    /* Boot battery restore precedes native_session165, so native_io165 is
     * not yet owned. Use the same immutable GPIO callbacks at both entries. */
    static const struct nes_rom_spi_io io={0,load_select,load_clock,load_mosi,load_miso,wait_us};
    return nes_native165_bulk_inner471(&io,tx,rx,13);
}

'''))
    host = 'nes_checkpoint_host.c'
    old = (src / host).read_text()
    edit(src, host, (old[old.index('static uint8_t checksum'):old.index('static bool command')],
                     'extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);\n\n'),
         ('checksum(tx)', 'nes_wire_crc807(tx,12)'), ('checksum(rx)', 'nes_wire_crc807(rx,12)'),
         ('Each real GPIO exchange takes at least 208 us.', 'A status transfer always clocks 104 bits.'))
    if profile == 'debug':
        for file in ('nes_menu_diagnostic.c','nes_checkpoint112.c','nes_frame900.c'):
            p=src/file
            if p.exists():p.write_text(p.read_text().replace('debug1054','debug1055'))
        return
    retail_reset(src)
    edit(src,'nes_menu_diagnostic.c',
         (' nes_return_log_allow(true);save_report("PREPARED_RESET_HELD",true);nes_return_log_allow(false);',''))
    # When the mini overwrites the old menu, every copied byte must reach
    # PSRAM before we start readback. Keep the independent compare and CRC.
    edit(src,'nes_retail_preload1054.inc', ('static __attribute__((noinline,noclone)) bool retail_write_page1054','__attribute__((noinline,noclone)) bool retail_write_page1054'))
    edit(src,'nes_menu_return.c', ('uint32_t nes_return_copy_menu(', 'extern bool retail_write_page1054(uint8_t *,uint32_t,unsigned);\nuint32_t nes_return_copy_menu('),
         ('sram_writeblock(data,address+copied,(uint16_t)n)!=n','!retail_write_page1054(data,address+copied,n)'))
    edit(src,'nes_h1_stm32.c',
         ('uint8_t token=fpga_test();','''/* DONE can precede the first valid base command response. Probe
    * only the read-only identity, with RESET held throughout. */
   uint8_t token=0;
   for(unsigned i=0;i<20;i++){
    if(!nes_return_spi_ready())break;
    token=fpga_test();
    if(token==FPGA_TEST_TOKEN || nes_return_failed())break;
    delay_ms(1);
   }'''))


if __name__=='__main__':
    for profile in ('debug','release'):
        prepare(profile)
