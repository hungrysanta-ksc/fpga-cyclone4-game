# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_h1_sampling import source,session
from nes_h1_spi import replace,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ('out','gcc'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir()
 binding=replace(source(),'((GPIOB->IDR>>4)&1u)','h1_read_miso()')
 (out/'binding.c').write_text(binding)
 for n in ('nes_h1_stm32.h','nes_h1_session.h'):shutil.copy2(ROOT/'src/nes/firmware'/n,out/n)
 h=(ROOT/'tests/nes-functional/h1_stm32_mock.h').read_text()
 extra='\ntypedef unsigned tick_t;\ntypedef struct {unsigned opened;} FIL;\ntypedef unsigned FRESULT;\ntypedef unsigned UINT;\n#define FA_CREATE_ALWAYS 8\n#define FA_WRITE 2\ntick_t getticks(void);\nFRESULT f_open(FIL*,const char*,unsigned);\nFRESULT f_write(FIL*,const void*,UINT,UINT*);\nFRESULT f_close(FIL*);\nunsigned h1_read_miso(void);\n'
 (out/'h1_stm32_mock.h').write_text(h.replace('#endif',extra+'\n#endif'))
 for n in ('config','bits','timer','snes','fpga','fpga_spi','fileops','uart'):(out/(n+'.h')).write_text('#include "h1_stm32_mock.h"\n')
 t=(ROOT/'tests/nes-functional/h1_stm32_test.c').read_text()
 t=replace(t,'case 0xf1:return wrong_id?0x35:0x34;','case 0xf1:return wrong_id?0x35:0x44;')
 t=replace(t,'status_fault && polls>=1?6:3','status_fault && polls>=1?7:3')
 t=replace(t,'default:return 0;', 'default:if(c>=0xd0 && c<=0xdf && active && status_fault)return c-0xd0+1;if(c>=0xf5 && c<=0xff && active && status_fault){const unsigned snapshot[]={0x87,5,0x10,0,0x60,0,0x64,0,0,0,2};return snapshot[c-0xf5];}return 0;')
 t=replace(t,'#include "../../src/nes/firmware/nes_h1_stm32.c"','#include "binding.c"')
 t=replace(t,'static FILE *trace;',"""static FILE *trace,*wave;
static unsigned long long previous_ns;
static unsigned samples,log_mode,opens,writes,closes;
static char last_report[512];
tick_t getticks(void){return (tick_t)(now_us/10000);}
FRESULT f_open(FIL *f,const char *name,unsigned flags){
 assert(held && !gpio_owned && !usb_enabled && checks==1);
 assert(strcmp(name,"/sd2snes/nes-h1-last-044.txt")==0 && flags==(FA_CREATE_ALWAYS|FA_WRITE));
 opens++;f->opened=log_mode!=1;return log_mode==1?1:FR_OK;
}
FRESULT f_write(FIL *f,const void *data,UINT size,UINT *written){
 assert(f->opened && size<sizeof(last_report));writes++;
 memcpy(last_report,data,size);last_report[size]=0;*written=log_mode==2?0:log_mode==3?size-1:size;
 return log_mode==2?1:FR_OK;
}
FRESULT f_close(FIL *f){assert(f->opened);f->opened=0;closes++;return log_mode==4?1:FR_OK;}
static void record(int expect){
 if(!wave)return;
 unsigned long long ns=(unsigned long long)now_us*1000;
 fprintf(wave,"%llu %u %u %u %d\\n",ns-previous_ns,(port_a.ODR>>4)&1u,(port_b.ODR>>3)&1u,(port_b.ODR>>5)&1u,expect);previous_ns=ns;
}
unsigned h1_read_miso(void){unsigned b=(port_b.IDR>>4)&1u;record(bits<=8 || command_byte==0xe8 || command_byte==0xe9?-2:(int)b);if(wave)samples++;return b;}
""")
 t=replace(t,' if(before==high)return;',' record(-1);\n if(before==high)return;')
 t=replace(t,' assert(argc==2);trace=fopen(argv[1],"w");assert(trace);',' assert(argc==3);trace=fopen(argv[1],"w");assert(trace);wave=fopen(argv[2],"w");assert(wave);')
 t=replace(t,' fpga_config=FPGA_BASE;file_res=0;usb_enabled=true;expected_mode=original_mode;', ' fpga_config=FPGA_BASE;file_res=0;usb_enabled=true;expected_mode=original_mode;log_mode=opens=writes=closes=0;last_report[0]=0;')
 needle=' printf("PASS normal RESET/menu restoration, %u timed SCK edges\\n",edge_count);'
 t=replace(t,needle,needle+'\n assert(opens==1 && writes==1 && closes==1 && strstr(last_report,"exit_reason=RESET_ASSERTED") && strstr(last_report,"last_status_hex=03") && strstr(last_report,"polls=2"));\n printf("PASS C waveform samples=%u\\n",samples);fclose(wave);wave=NULL;\n')
 t=replace(t,' puts("PASS running status fault stops and restores");',' assert(strstr(last_report,"exit_reason=F2_STATUS") && strstr(last_report,"last_status_hex=07"));\n puts("PASS running status fault stops and restores");')
 t=replace(t,' puts("PASS running status fault stops and restores");', ' assert(strstr(last_report,"detail_ok=1") && strstr(last_report,"detail_hex=a5440787051000600064000000020102030405060708090a0b0c0d0e0f10"));\n puts("PASS running status fault stops and restores");')
 t=replace(t,' fclose(trace);return 0;','\n for(unsigned mode=1;mode<=4;mode++){\n  setup();log_mode=mode;assert(nes_h1_run());assert(held && usb_enabled && checks==1 && opens==1);\n  assert(writes==(mode==1?0:1) && closes==(mode==1?0:1));\n  printf("PASS logging failure mode=%u preserves recovery\\n",mode);\n }\n fclose(trace);return 0;\n')
 (out/'test.c').write_text(t)
 (out/'session.c').write_text(session())
 cmd=[str(a.gcc),'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-I'+str(out),str(out/'test.c'),str(out/'session.c'),'-o',str(out/'test.exe')]
 for name,args in [('compile',cmd),('test',[str(out/'test.exe'),str(out/'transactions.tsv'),str(out/'waveform.txt')])]:
  cp=subprocess.run(args,capture_output=True);(out/(name+'.log')).write_bytes(cp.stdout+cp.stderr)
  assert cp.returncode==0,(cp.stdout+cp.stderr).decode(errors='replace')
 log=(out/'test.log').read_text();assert 'PASS C waveform samples=704' in log
 cases=[s for s in log.splitlines() if s.startswith('PASS ') and not s.startswith('PASS C waveform')];assert len(cases)==15,cases
 (out/'result.json').write_text(json.dumps({'candidate':'NES-H1-SAMPLING-044','cases':cases,'samples':704,'source_sha256':sha(out/'binding.c'),'scope':'Production-derived C, one read instrumentation; GPIO/FAT mocks, no physical MCU/SD'},indent=2))
 print('PASS host15 cases +704-sample production timing waveform')
if __name__=='__main__':main()
