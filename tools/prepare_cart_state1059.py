"""Generate the AxROM and ExROM checkpoint and CHR mirror variants."""
from shutil import copytree
import re
from prepare_cart_stage1058 import OUT as BASE
from prepare_nes_kirby1023 import edit

OUT = BASE.parent / "nes-carts1059"


def board(mapper):
    source = BASE if mapper == 7 else BASE.parent / "nes-carts1056"
    dst = OUT / f"board-{mapper}"
    copytree(source / dst.name, dst, dirs_exist_ok=True)
    cart = "cart_nrom.sv"
    # Disk register word 33 uses an eight-lane read and a single word write.
    common = """input wire state_write, input wire [63:0] state_word,
 input wire [2:0] state_lane, output wire [7:0] state_byte,"""
    pins = """.state_write(SaveStateBus_load && SaveStateBus_wren && SaveStateBus_Adr==32),
 .state_word(SaveStateBus_Din),.state_lane(Savestate_MAPRAMAddr[2:0]),.state_byte(mapper_byte),"""
    edit(dst, cart, ("wire [19:0] prg;", """wire [7:0] mapper_byte;
assign SaveStateBus_Dout = SaveStateBus_Adr==32 ? {56'd0,mapper_byte} : 64'd0;
wire [19:0] prg;"""), (" cartridge(", " cartridge("+pins),
         ("diskside,\n SaveStateBus_Dout,Savestate_MAPRAMReadData}","diskside}"))
    if mapper == 7:
        edit(dst, cart, ("input wire clk, reset, ce,", common+"\n input wire clk, reset, ce,"),
             ("reg [4:0] latch;", """reg [4:0] latch;
   assign state_byte=state_lane==0 ? {3'd0,latch} : 8'd0;"""),
             ("if(reset) latch<=0;", "if(reset) latch<=0;\n     else if(state_write) latch<=state_word[4:0];"),
             ("assign chr_dout=", "assign Savestate_MAPRAMReadData=0;\nassign chr_dout="))
        # The copy engine takes five clocks per byte. Do not copy the other
        # half of a 1 KiB page on sparse writes. Receipt ABI stays unchanged.
        edit(dst, "nes_chr_snapshot.sv", ("reg [7:0] dirty;", "reg [15:0] dirty;"),
             ("p<8;", "p<16;"), ("changed_page==p", "changed_group[5:2]==p"),
             ("scan_addr[12:10]", "scan_addr[12:9]"), ("&scan_addr[9:0]", "&scan_addr[8:0]"))
    else:
        edit(dst, cart, ("input wire clk,reset,ce,wr,", common+"""
 input wire state_ram, state_wr, input wire [9:0] state_addr,
 input wire [7:0] state_data, output wire [7:0] state_q,
 input wire clk,reset,ce,wr,"""),
             (".state_word(SaveStateBus_Din)", """.state_ram(Savestate_MAPRAMactive),.state_wr(Savestate_MAPRAMWrEn),
 .state_addr(Savestate_MAPRAMAddr[9:0]),.state_data(Savestate_MAPRAMWriteData),
 .state_q(Savestate_MAPRAMReadData),.state_word(SaveStateBus_Din)"""),
             ("reg [7:0] selected;", """wire [63:0] regs={16'd0,bank7,bank6,bank5,bank4,nt_map,ex_mode,protect2,protect1,mode};
 assign state_byte=regs[8*state_lane +: 8];
 reg [7:0] selected;"""),
             ("ex_data<=exram[cpu[9:0]];", """ex_data<=exram[ex_addr];"""),
             ("if(!reset && ce && wr && ex && ex_mode==2)exram[cpu[9:0]]<=data;",
              """if(!reset && (state_ram ? state_wr : (ce && wr && ex && ex_mode==2)))
     exram[ex_addr]<=state_ram ? state_data : data;"""),
             ("reg [7:0] ex_data;", """wire [9:0] ex_addr=state_ram ? state_addr : cpu[9:0];
 reg [7:0] ex_data;
 assign state_q=ex_data;"""),
             ("end else if(ce && wr) case(cpu)", """end else if(state_write)
     {bank7,bank6,bank5,bank4,nt_map,ex_mode,protect2,protect1,mode}<=state_word[47:0];
   else if(ce && wr) case(cpu)"""))
        edit(dst/"rtl", "savestates.vhd", ("96,97,1121,1377,1633,2657","96,224,1248,1504,1760,2784"),
             ("000014C4","000015C2"), ("to_unsigned(98,10)", "to_unsigned(225,10)"),
             ("(others=>'0') when 1", "resize(word_index(6 downto 0)-to_unsigned(97,7),10) when 1"))
        edit(dst,"nes_checkpoint_spi.sv",("WORDS=2658","WORDS=2785"))


def arm(edition,vrc=False):
    prior = BASE if edition=="debug" else BASE.parent/"nes-carts1057"
    link = (OUT/"vrc" if vrc else OUT)/edition/"link"
    copytree(prior/edition/"link", link, dirs_exist_ok=True)
    src=link/"src"
    edit(src,"nes_checkpoint_gpio.inc", ("(nes_board_id==0x7d || nes_board_id==0x84)", "NES_PATTERN_RAM"),
         ("(nes_board_id!=0x7d && (slot || nes_board_id!=0x84))","(!NES_PATTERN_RAM || (!slot && nes_board_id==0x82))"),
         ("    if(nes_board_id==0x82)return nes_menu_state_resume();\n",""),
         ("    int result=nes_menu_state_io(0,true);","    if(nes_board_id==0x82)return nes_menu_state_resume();\n    int result=nes_menu_state_io(0,true);"),
         ("available(id,21264)", "available(id,nes_state_bytes(id))"))
    edit(src,"nes_menu_play.inc",("nes_board_id!=0x7d && ((req>=0x10 && req<=0x23) || (req==2 && nes_board_id!=0x84))",
                                  "req==2 && nes_board_id==0x82"))
    edit(src,"nes_savefile.h",("int nes_savefile_available", """static inline unsigned nes_state_bytes(struct nes_save_id id){
    return id.rom_bytes==0x100000u ? 22280u : 21264u;
}
int nes_savefile_available"""))
    edit(src,"nes_savefile.c",("(!id.slot && id.rom_bytes==0x100000u)","id.rom_bytes==0x100000u"),
         ("bytes==21264","bytes==nes_state_bytes(id)"),("id.slot?21264:8192","id.slot?nes_state_bytes(id):8192"))
    edit(src,"nes_checkpoint_host.c",("bool load,state;", "bool load,state; unsigned bytes;"),
         ("static const uint8_t header_word[8]={0,0,0,0,0xc4,0x14,0,0};",""),
         ("struct transfer *t=ctx;", """struct transfer *t=ctx;
    const uint32_t header_word[2]={0,t->bytes/4};"""),
         ("header_word+4","header_word+1"),("offset+size==8*STATE_WORDS","offset+size==t->bytes"),
         ("exchange,load,id.slot!=0}", "exchange,load,id.slot!=0,nes_state_bytes(id)}"),
         ("id.slot?8*STATE_WORDS:BAT_BYTES","id.slot?nes_state_bytes(id):BAT_BYTES"))
    # The six profiles occupy nine adjacent IDs. A bounded sparse table eliminates
    # six padded ID/pointer pairs and the search loop on every launch.
    ui=src/"nes_menu_diagnostic.c"
    text=ui.read_text()
    begin=text.index("static const struct {uint8_t id;const char *file;} boards[]=")
    end=text.index("static const char *nes_board_file;",begin)
    paths=re.findall(r'\{ (0x[0-9a-f]+), ("[^"]+") \}',text[begin:end])
    assert len(paths)==6
    table="static const char *const boards[]={\n"+"".join(
        f" [{ident}-0x7c]={path},\n" for ident,path in paths)+"};\n"
    ui.write_text(text[:begin]+table+text[end:])
    edit(src,ui.name,("""nes_board_file=NULL;
   for(unsigned i=0;i<sizeof boards/sizeof *boards;i++)
    if(boards[i].id==id)nes_board_file=boards[i].file;""",
        "nes_board_file=(unsigned)(id-0x7c)<sizeof boards/sizeof *boards ? boards[id-0x7c] : NULL;"))
    if edition=="debug":
        for name in ("nes_checkpoint112.c","nes_menu_diagnostic.c"):
            edit(src,name,("debug1058","debug1059"))
        edit(src,"nes_budget210.c",("edition=1058","edition=1059"))
    if vrc:
        edit(src,"nes_mmc479.h",("#define NES_PATTERN_RAM", "#define NES_CHECKPOINT_BOARD (NES_PATTERN_RAM || nes_board_id==0x83)\n#define NES_PATTERN_RAM"))
        edit(src,"nes_run136.inc",("!NES_PATTERN_RAM || nes_restore","!NES_CHECKPOINT_BOARD || nes_restore"))
        edit(src,"nes_checkpoint_gpio.inc",("NES_PATTERN_RAM","NES_CHECKPOINT_BOARD"))
        edit(src,"nes_runtime_board165.inc",("NES_PATTERN_RAM && !ff3_play_step","NES_CHECKPOINT_BOARD && !ff3_play_step"))
        edit(src,"nes_savefile.c",("id.rom_bytes==0x80000u ||","id.rom_bytes==0x60000u || id.rom_bytes==0x80000u ||"))
        if edition=="debug":
            # Compile the cold settings parser with the existing size-LTO group.
            with (src/"Makefile").open("a") as make:
                make.write("\n$(OBJDIR)/yaml.o : CFLAGS += -flto -Oz\n")
            (src/"yaml.c").touch()
    # .inc files are included by this unit; do not rely on copied dependency files.
    (src/"nes_h1_stm32.c").touch()


if __name__=="__main__":
    import sys
    for item in sys.argv[1:]:
        if item.isdecimal(): board(int(item))
        else: arm(item.removeprefix("vrc-"),item.startswith("vrc-"))
