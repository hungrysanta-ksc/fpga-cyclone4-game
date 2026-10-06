# SPDX-License-Identifier: MIT
"""038: derive exit telemetry only; preserve035 MCU SPI and036 FPGA."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
from nes_h1_spi import replace
ROOT=Path(__file__).resolve().parents[1]
def source():
 p=ROOT/'src/nes/firmware/nes_h1_stm32.c'
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='c4fa2e91423c9ff6435210751b5e452d1b85987b575137142aea27a79d0e0e24'
 s=p.read_text()
 helper="""
/* Write only after STOP/GPIO restore and verified base FPGA, with RESET held
 * and USB IRQ still disabled. Local FIL avoids the shared file_handle/buffer.
 * Logging errors must not prevent menu recovery. No game/save file access. */
static void runtime_report(const char *reason,unsigned start_result,unsigned stop_result,
                           unsigned status,uint32_t polls,uint16_t epoch,tick_t elapsed) {
 FIL report;
 char text[384];
 int n=snprintf(text,sizeof(text),
   "candidate=NES-H1-RUNTIME-038\\nexit_reason=%s\\nstart_result=%u\\nstop_result=%u\\n"
   "last_status_hex=%02x\\npolls=%lu\\nepoch=%u\\nelapsed_ticks_10ms=%lu\\nbase_restored=1\\n",
   reason,start_result,stop_result,status,(unsigned long)polls,epoch,(unsigned long)elapsed);
 if(n<=0 || (size_t)n>=sizeof(text))return;
 FRESULT opened=f_open(&report,"/sd2snes/nes-h1-last-038.txt",FA_CREATE_ALWAYS|FA_WRITE);
 if(opened!=FR_OK){printf("H1 report open=%u\\n",(unsigned)opened);return;}
 UINT written=0;
 FRESULT saved=f_write(&report,text,(UINT)n,&written);
 FRESULT closed=f_close(&report);
 printf("H1 report write=%u close=%u bytes=%u/%u\\n",(unsigned)saved,(unsigned)closed,(unsigned)written,(unsigned)n);
}
"""
 s=replace(s,'bool nes_h1_run(void) {',helper+'\nbool nes_h1_run(void) {')
 s=replace(s,' uint16_t epoch=0;', ' uint16_t epoch=0;\n const char *reason="START_ERROR";\n uint8_t last_status=255;\n uint32_t polls=0;\n unsigned stop_result=255;\n tick_t started=getticks();')
 s=replace(s,' printf("H1 start=%u epoch=%u\\n",(unsigned)result,(unsigned)epoch);',' const unsigned start_result=(unsigned)result;\n printf("H1 start=%u epoch=%u\\n",(unsigned)result,(unsigned)epoch);')
 s=replace(s,'   if(get_snes_reset())break;', '   if(get_snes_reset()){reason="RESET_ASSERTED";break;}')
 s=replace(s,'   if(!slow_transaction(0,tx,rx,2) || rx[1]!=3) {', '   polls++;\n   if(!slow_transaction(0,tx,rx,2)){reason="SPI_IO";break;}\n   last_status=rx[1];\n   if(rx[1]!=3) {\n    reason="F2_STATUS";')
 s=replace(s,' snes_reset(1);\n if(gpio_owned)', ' tick_t elapsed=getticks()-started;\n snes_reset(1);\n if(gpio_owned)')
 s=replace(s,'  result=nes_h1_stop(&io);','  result=nes_h1_stop(&io);\n  stop_result=(unsigned)result;')
 s=replace(s,' if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);',' runtime_report(reason,start_result,stop_result,last_status,polls,epoch,elapsed);\n if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);')
 # Bitbang routine is byte-for-byte unchanged at the text level.
 assert s.split('static bool slow_transaction',1)[1].split('static void reset_cpu',1)[0]==p.read_text().split('static bool slow_transaction',1)[1].split('static void reset_cpu',1)[0]
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/prepare_nes_h1_firmware.py'),'--out',str(a.out),'--upstream',str(a.upstream)],check=True)
 (a.out/'src/nes_h1_stm32.c').write_text(source(),newline='\n')
 (a.out/'runtime-preparation.json').write_text(json.dumps({'candidate':'NES-H1-RUNTIME-038','binding_sha256':hashlib.sha256((a.out/'src/nes_h1_stm32.c').read_bytes()).hexdigest(),'FPGA':'unchanged036'},indent=2))
if __name__=='__main__':main()
