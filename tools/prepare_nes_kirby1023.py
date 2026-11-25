"""Generate the isolated 14-bit Kirby board and ARM profile from the validated inputs."""
import argparse
from pathlib import Path
import shutil

from prepare_nes_kirby1022_board import FILES, BASE_HASHES, patch
from prepare_nes_trial802 import rename_edition
import hashlib


def edit(folder, name, *pairs):
    path = folder / name
    source = path.read_text()
    for old, new in pairs:
        if old not in source:
            raise ValueError(f"{name}: missing {old!r}")
        source = source.replace(old, new)
    path.write_text(source)


def board(base, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for file in base.iterdir():
        if file.is_file() and file.suffix in {".qpf", ".qsf", ".sdc", ".hex", ".mif", ".sv", ".v", ".vhd", ".tcl", ".qip"}:
            shutil.copy2(file, dest / file.name)
    for name in ("rtl", "sys"):
        shutil.copytree(base/name, dest/name, dirs_exist_ok=True)
    for name, digest in BASE_HASHES.items():
        path = dest / (name+".sv")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        if name in FILES:
            path.write_text(patch(name, path.read_text()))
    for src, target in (("nes_probe_order1022","nes_chr_cache611"),("nes_obj_cross1022","nes_obj_capture611")):
        path = Path(__file__).resolve().parents[1]/"rtl"/(src+".sv")
        (dest/(target+".sv")).write_text(path.read_text().replace(src,target).replace("nes_obj_cross1022 capture","nes_obj_capture611 capture"))
    def sv(name, *pairs):
        edit(dest, name+".sv", *pairs)
    sv("nes_rom_service", ("[17:0]", "[18:0]"), ("[16:0]","[17:0]"), ("[17:3]","[18:3]"),
       ("[14:0] cpu_line_tag","[15:0] cpu_line_tag"), ("3'b000,pending_offset","2'b00,pending_offset"),
       ("3'b000,next_offset","2'b00,next_offset"), ("25'h40000","25'h80000"), ("22'h220000","22'h240000"))
    sv("nes_native_planes165", ("[12:0]","[13:0]"), ("8191","16383"),
       ("physical_address[16:4]","physical_address[17:4]"), ("pair_address[16:4]","pair_address[17:4]"),
       ("physical_address[21:17]==5'h10","physical_address[21:18]==4'h8"),
       ("{11'd0,rank","{physical_address[17],10'd0,rank"),
       ("physical_address[2:0],physical_address[17:4]","physical_address[2:0],physical_address[16:4]"),
       ("{2'd0,1'b1,pair_address","{physical_address[17],pair_address[17],1'b1,pair_address"))
    sv("nes_native_capture201", ("[12:0] query_index","[13:0] query_index"),
       ("nes_native_frame201 frame(", "nes_native_frame201 #(.TILE_QUERY(0)) frame("))
    # The physical exporter enumerates geometry, then jumps from palette (5)
    # to raw (7). The unused debugger read port must return a miss on this board.
    sv("nes_native_frame201", ("[12:0] query_index","[13:0] query_index"),
       ("module nes_native_frame201(", "module nes_native_frame201 #(parameter TILE_QUERY=1)("),
       ("selected==6?fetch_response","selected==6?(TILE_QUERY && fetch_response)"),
       ("selected==6?{62'd0,required_kind}","selected==6?(TILE_QUERY?{62'd0,required_kind}:64'd0)"))
    sv("nes_native_raster181",
       ("display_mask!=8'h18 && display_mask!=8'h1e && display_mask!=8'h0e",
        "(display_mask & 8'hef)!=8'h08 && (display_mask & 8'hef)!=8'h0e"))
    sv("nes_live_joint", ("wire [12:0] native_frame_query_index=native_query_index","wire [13:0] native_frame_query_index={1'b0,native_query_index}"),
       ("[21:17]==5'h10","[21:18]==4'h8"), ("cap_address(ppumem_addr[16:0]","cap_address(ppumem_addr[17:0]"))
    sv("nes_native_compact181", ("[14:0]","[15:0]"), ("[31:0] exceptions","[32:0] exceptions"), ("[31:0] exception_q","[32:0] exception_q"),
       ("49'd0,map_q","48'd0,map_q"), ("32'd0,exception_q","31'd0,exception_q"), ("[37:0]","[38:0]"),
       ("[12:0] tile=event_data[12:0]","[13:0] tile={event_data[63],event_data[12:0]}"),
       ("key={attribute,position,top,tile}","key={tile[13],attribute,position,top,tile[12:0]}"),
       ("15'd0,rank,mask,key","14'd0,key[38],rank,mask,key[37:0]"),
       ("[12:0] low_tile=cross_tile?{event_data[60:57]","[13:0] low_tile=cross_tile?{event_data[62],event_data[60:57]"),
       ("event_data[63:62]!=0","(!cross_tile && event_data[62])"))
    sv("nes_native_export203", ("16'h2233","16'h2234"), ("if(data[63:15]!=0)","if(data[63:16]!=0)"))
    sv("nes_native_spi165", ("3:width=4","3:width=5"), ("[14:0] cell_word","[15:0] cell_word"),
       ("[6:0] cell_upper,cells","[7:0] cell_upper;reg [6:0] cells"), ("{1'b0,cell_upper}","cell_upper"),
       ("record_data[14:8]","record_data[15:8]"), ("held[59:0]<={held[44:0],cell_word}","held[63:0]<={(group_count==1?48'd0:held[47:0]),cell_word}"),
       ("1'b0,group_count,held[59:0]","held[63:0]"))
    sv("nes_geometry_sender653", ("[14:0] cell_word","[15:0] cell_word"), ("{q[6:0],first}","{q,first}"))
    for name in ("nes_plan_batch206","nes_e9_scan914"):
        pairs=[("[12:0]","[13:0]"),("[12:8]<=data[4:0]","[13:8]<=data[5:0]"),("data[7:5]","data[7:6]")]
        if name=="nes_plan_batch206":
            pairs += [("[103:0]","[111:0]"),("{data[4:0],alt_low}","{data[5:0],alt_low}")]
        sv(name,*pairs)
    for name in ("nes_tile205","nes_source_tile192","nes_direct206"):
        pairs=[("[12:0]","[13:0]"),("[103:0]","[111:0]"),("[16:0]","[17:0]")]
        if name=="nes_tile205":
            pairs.append(("*13)","*14)"))
        if name=="nes_source_tile192":
            pairs += [("5'h10,tile_address","4'h8,tile_address"),("[21:17]!=5'h10","[21:18]!=4'h8"),("[9:0] page_base963","[10:0] page_base963")]
        if name=="nes_direct206":
            pairs += [("[25:0] payload","[26:0] payload"),("WIDTH(26)","WIDTH(27)"),("payload_dst963[25:10]","payload_dst963[26:11]"),("payload_dst963[9:0]","payload_dst963[10:0]")]
        sv(name,*pairs)
    sv("nes_plan_spi200", ("[25:0] payload","[26:0] payload"),("received16[7:5]","received16[7:6]"),("length,received16[4:0]","length,received16[5:0]"))
    sv("nes_e9_rows914", ("[12:0]","[13:0]"),("[9:0] page_base963","[10:0] page_base963"),("page_base963[9:1]","page_base963[10:1]"),
       ("[8:0] page952","[9:0] page952"),("[12:4]","[13:4]"),("9'h1ff","10'h3ff"),("WIDTH=30-LOW","WIDTH=31-LOW"),
       ("[16:4+LOW]","[17:4+LOW]"),("[12:LOW]","[13:LOW]"),("5'h10,","4'h8,"))
    for file, signal, prior in (("board.sdc","page_mail963|held",25),
                                ("initial576.sdc","reader|address_hold",17),
                                ("cdc576.sdc","reader|address_hold",17)):
        path=dest/file
        lines=[line for line in path.read_text().splitlines() if f"{signal}[{prior}]" in line]
        assert len(lines)==2 and lines[0].startswith("set_max_delay") and lines[1].startswith("set_false_path -hold")
        with path.open("a") as s:
            for line in lines:
                s.write("\n"+line.replace(f"[{prior}]",f"[{prior+1}]"))
            s.write("\n")


def arm(base, dest):
    shutil.copytree(base, dest, dirs_exist_ok=True)
    src=dest/"src"
    edition=dest.parent/"edition"
    if not edition.exists():
        rename_edition(base/"src", edition, 1022, 1023)
    for path in edition.iterdir():
        shutil.copy2(path, src/path.name)
    edit(src,"nes_budget210.c",("edition=1012","edition=1023"))
    edit(src, "nes_native165.h",
         ("uint16_t tag;uint8_t kind;","uint16_t tag:14,kind:2;"),
         ("uint32_t exceptions[128];","uint32_t exceptions[128];uint8_t exception_hi[16];"),
         ("struct nes_native165 {","static inline unsigned nes_obj_tag1023(uint64_t v){return (v & 8191u) | ((v >> 36) & 8192u);}\nstruct nes_native165 {"))
    edit(src,"nes_native165.c", ("2,1,7,4,7,1,2,8","2,1,7,5,7,1,2,8"), ("15,8,49,32,53,6","16,8,50,33,53,6"),
         ("0x2233","0x2234"), ("t<8192","t<16384"), ("tag=(unsigned)obj&8191","tag=nes_obj_tag1023(obj)"),
         ("(unsigned)v&8191,1","(unsigned)v&16383,1"), ("(unsigned)v&8191,2","nes_obj_tag1023(v),2"),
         ("s->exceptions[index]=(uint32_t)v","s->exceptions[index]=(uint32_t)v;if(v>>32)s->exception_hi[index/8]|=1u<<(index%8)"),("counts[0]-start||v>>15","counts[0]-start||v>>16"),
         ("start=index&0xfff,n=(unsigned)(v>>60);","start=index&0xfff,n=(unsigned)s->counts[0]-start; if(n>4)n=4;"),
         ("uint64_t words=v&UINT64_C(0x0fffffffffffffff);","uint64_t words=v;"), ("(words>>(15*n))","(n<4 && (words>>(16*n)))"),
         ("(unsigned)words&32767","(unsigned)words&65535"),("cell&8191","cell&16383"), ("words>>=15","words>>=16"),
         ("if(v>>15)return fail(s,36);","if(v>>16)return fail(s,36);"), ("v&8191u,1","v&16383u,1"))
    inventory=(Path(__file__).parent/"kirby1023_inventory.c").read_text()
    receiver=src/"nes_native165.c"
    c=receiver.read_text()
    c=c[:c.index("static void require_tile")]+c[c.index("/* Validate capacity"):]
    begin=c.index("  if(s->missing>512)")
    end=c.index("  s->missing=0",begin)
    c=c[:begin]+"  if(!finish_tiles1023(s))return fail(s,34);\n"+c[end:]
    c=c.replace("static bool logical_record",inventory+"\nstatic bool logical_record",1)
    receiver.write_text(c.replace("require_tile(s,nes_obj_tag1023(v),2);",""))
    for name in ("nes_plan191.c","nes_planner211.c"):
        pairs=[("tag>=8192","tag>=16384"),("if(cell>>15)return fail(p,6);",""),("cell&8191","cell&16383"),
               ("(13+f*3)","(14+f*3)"),("cell>>13","cell>>14"),("if(v>>49)return fail(p,8)","if(v>>50)return fail(p,8)"),
               ("tag=(unsigned)v&8191","tag=nes_obj_tag1023(v)"),("masks[e]<<13","masks[e]<<14"),
               ("uint32_t e=s->exceptions[i]","uint32_t e=s->exceptions[i];unsigned low_tag=(e>>19)|((unsigned)(s->exception_hi[i/8]>>(i%8)&1)<<13)"),
               ("&& (e>>19)!=","&& low_tag!="),("tile(s,e>>19,1)","tile(s,low_tag,1)"),
               ("(uint16_t)(e>>19)","(uint16_t)low_tag")]
        if name=="nes_planner211.c":
            pairs += [("s->maps[idx-2])&8191","s->maps[idx-2])&16383"),("0x1fed6c8da4480000","0x3fdad91b48900000"),
                      ("mask==0x0e?0x1e:mask","mask|0x10")]
        edit(src,name,*pairs)
    edit(src,"nes_resident211.c",("tag>=8192","tag>=16384"),("q->mask<<13","q->mask<<14"))
    for name in ("nes_plan_wire196.h","nes_plan_wire199.h"):
        edit(src,name,(">8191",">16383"))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target",choices=("arm","board"))
    ap.add_argument("base",type=Path)
    ap.add_argument("dest",type=Path)
    args=ap.parse_args()
    {"arm":arm,"board":board}[args.target](args.base,args.dest)
