#include "config.h"
#include "gbc_log_policy.h"
#include <stdio.h>
#include "ff.h"
#include "fileops.h"
#include "gbc_state_report.h"
#include "gbc_state_transfer.h"
#include "gbc_memio.h"
/* Completed-operation report: no extra FPGA access and no reset required. */
void gbc_state_report(const gbc_state_identity *id,unsigned command,int result){
 if(!gbc_file_logs_enabled)return;
 uint32_t d[4];char path[48],text[512];FIL f;UINT got=0;FRESULT r=FR_EXIST;
 gbc_state_diagnostic(d);
 if(check_or_create_folder("/sd2snes/gbcdiag/")!=FR_OK)return;
 for(unsigned i=0;i<1000;i++){
  snprintf(path,sizeof(path),"/sd2snes/gbcdiag/state%03u.txt",i);
  r=f_open(&f,(const TCHAR*)path,FA_WRITE|FA_CREATE_NEW);if(r!=FR_EXIST)break;
 }
 if(r!=FR_OK)return;
 int n=snprintf(text,sizeof(text),"G13C36 STATE REPORT\ncommand=%02x slot=%u result=%d fatal=%d\nrom_bytes=%lu rom_crc=%08lx ram_bytes=%lu\nstep=%lu address=%06lx control=%02lx io=%02lx timeout_address=%08lx\n",command,(unsigned)id->slot+1,result,gbc_state_faulted(),(unsigned long)id->rom_bytes,(unsigned long)id->rom_crc,(unsigned long)id->ram_bytes,(unsigned long)d[0],(unsigned long)d[1],(unsigned long)d[2],(unsigned long)d[3],(unsigned long)gbc_memio_error_address());
 if(n>0&&(unsigned)n<sizeof(text)&&f_write(&f,text,n,&got)==FR_OK&&got==(UINT)n)f_sync(&f);
 f_close(&f);
}
