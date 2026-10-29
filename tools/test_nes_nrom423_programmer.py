# SPDX-License-Identifier: MIT
"""Actual 227 config programmer/FatFS with exact 423 image and modeled pins."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src';host=BASE/'probes/nes-run136/evidence/initial/host04';image=BASE/'probes/nes-nrom423/asm01/fpga_nrom16.bi3';raw=BASE/'probes/nes-nrom423/asm01/board.rbf'
for f in host.glob('*.h'):shutil.copyfile(f,d/f.name)
for n in ('ff.c','ff.h','ffconf.h','diskio.h'):
 assert sha(host/n)==sha(prod/n);shutil.copyfile(prod/n,d/n)
(d/'unicode').mkdir();shutil.copyfile(prod/'ccsbcs.c',d/'unicode/ccsbcs.c')
s=(prod/'fpga.c').read_text();marker='struct nes_diag_input {FIL file;';assert s.count(marker)==1;(d/'programmer.inc').write_text(s[s.index(marker):],newline='\n')
disk=(ROOT/'tests/nes-nrom408/fat_disk.c').read_text();disk+='''\nvoid nrom_fatdisk_set_image(const uint8_t *data,uint32_t len){
 uint8_t *fat=media+512,*dir=media+ROOT_SECTOR*512u+32;unsigned n=(len+511)/512;
 assert(n>0 && 51+n<6144 && DATA_SECTOR+49+n<SECTORS);
 memcpy(dir,"BASE       ",11);dir[11]=0x20;word(dir+26,51);dword(dir+28,len);
 for(unsigned i=0;i<n;i++)word(fat+(51+i)*2u,i+1==n?0xffff:52+i);
 memcpy(media+(DATA_SECTOR+49)*512u,data,len);
}\n''';(d/'fat_disk.c').write_text(disk,newline='\n')
src=(ROOT/'tests/nes-nrom412/programmer_tb.c').read_text();assert src.count('static uint8_t bytes[512]')==1
src=src.replace('static uint8_t bytes[512]','static uint8_t bytes[600000]').replace('++w->polls<400','++w->polls<2097152')
src=src[:src.index('int main(void)')]+r'''
void nrom_fatdisk_set_image(const uint8_t *,uint32_t);
int main(int argc,char **argv){
 assert(argc==3);static uint8_t encoded[600000],expected[600000],rom[24592];FATFS fs;
 FILE *f=fopen(argv[1],"rb");assert(f);size_t en=fread(encoded,1,sizeof(encoded),f);assert(feof(f)&&!ferror(f));fclose(f);
 f=fopen(argv[2],"rb");assert(f);size_t rn=fread(expected,1,sizeof(expected),f);assert(feof(f)&&!ferror(f));fclose(f);
 nrom_fatdisk_prepare(rom,sizeof(rom));nrom_fatdisk_set_image(encoded,(uint32_t)en);assert(f_mount(&fs,"",1)==FR_OK);
 fresh();diag.phase=NES_DIAG_RECOVER;assert(nes_diag_fpga_pgm((const uint8_t *)"base"));
 assert(nbytes==rn && !memcmp(bytes,expected,rn));assert(done&&prog&&!pins_masked&&post==1&&file_res==FR_OK);
 printf("PASS NROM423 actual programmer bytes=%u encoded=%u; modeled pins\n",(unsigned)rn,(unsigned)en);return 0;
}''';(d/'programmer_tb.c').write_text(src,newline='\n')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
cmd=[gcc,'-std=c99','-O2','-I',str(d),'-I',str(prod),str(d/'ff.c'),str(d/'unicode/ccsbcs.c'),str(d/'fat_disk.c'),str(d/'programmer_tb.c'),'-o',str(d/'test.exe')]
for name,command in [('compile',cmd),('test',[str(d/'test.exe'),str(image),str(raw)])]:
 with (d/(name+'.log')).open('wb') as f:r=subprocess.run(command,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-5000:]
assert 'PASS NROM423 actual programmer' in (d/'test.log').read_text()
res={'passed':True,'image_sha256':sha(image),'rbf_sha256':sha(raw),'programmer_sha256':sha(prod/'fpga.c'),'scope':'actual programmer/FatFS with exact diagnostic BI3 and modeled GPIO/DONE; not FPGA hardware'}
(d/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res))
