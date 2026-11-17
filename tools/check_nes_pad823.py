"""Compare the old and compact pad log writers, including bounded buffers."""
import argparse
import os
from pathlib import Path
import subprocess


def formatter(src,name):
    text=(src/"nes_menu_diagnostic.c").read_text()
    return text[text.index("static int pad165_format"):text.index("extern int nes_hexline512")].replace("pad165_format",name)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("base","candidate","out","gcc"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.mkdir()
    report=(a.candidate/"nes_budget210.c").read_text().split("#include <stdarg.h>")[-1]
    harness='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
static struct { unsigned screen_error,screen_valid,pad_valid,pad_total,pad_count,pad_flags,pad_buttons[1],pad_ticks[1]; } nes_run136;
'''+report+formatter(a.base,"old_pad")+formatter(a.candidate,"new_pad")+'''
int main(void){
 char old[1024],current[1024];
 nes_run136.pad_valid=1;nes_run136.pad_count=1;nes_run136.pad_ticks[0]=42;
 for(unsigned mask=0;mask<256;mask++){
  nes_run136.pad_buttons[0]=mask;
  for(unsigned n=1;n<=sizeof old;n++){
   memset(old,0,sizeof old);memset(current,0,sizeof current);
   int a=old_pad(old,n,1),b=new_pad(current,n,1);
   if(a!=b||memcmp(old,current,sizeof old))return 1;
  }
 }
 puts("PASS 256 pad masks x 1024 buffer sizes");
 return 0;
}
'''
    src=a.out/"pad.c"
    exe=a.out/"pad.exe"
    src.write_text(harness)
    env=dict(os.environ,PATH=str(a.gcc.parent)+os.pathsep+os.environ["PATH"])
    subprocess.run([a.gcc,"-Os",src,"-o",exe],env=env,check=True)
    subprocess.run([exe.resolve()],env=env,check=True)
