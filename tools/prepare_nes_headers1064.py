"""Use one size decoder for SD selection and for DEBUG/RELEASE loader revalidation."""
from shutil import copytree, copyfile
from prepare_nes_compat1062 import OUT as BASE, ROOT

OUT = BASE.parent / "nes-headers1064"

def prepare(mode):
    link = OUT / mode / "link"
    copytree(BASE/mode/"link",link,dirs_exist_ok=True)
    src = link/"src"
    copyfile(ROOT/"src/nes/nes_cartridge_header.h",src/"nes_cartridge_header.h")
    menu = src/"nes_menu_diagnostic.c"
    body = menu.read_text()
    start = body.index("unsigned nes_image_id(")
    end = body.index("/* Directory scanning",start)
    body = body[:start]+'''#include "nes_cartridge_header.h"
static unsigned read_cart_profile(const uint8_t h[16],uint32_t size,uint32_t *prg){
 struct nes_cartridge c;
 if(!nes_decode_cart(h,size,&c))return 0;
 *prg=c.prg_size;
 return nes_cart_profile(&c);
}
unsigned nes_image_id(const uint8_t h[16],uint32_t size){
 uint32_t prg;
 return read_cart_profile(h,size,&prg);
}

'''+body[end:]
    old="id=nes_image_id(header,f_size(&file));\n   nes_prg_bytes=header[4]*16384u;"
    assert body.count(old)==1
    menu.write_text(body.replace(old,"id=read_cart_profile(header,f_size(&file),&nes_prg_bytes);"))

if __name__=="__main__":
    for mode in ("debug","release"):
        prepare(mode)
