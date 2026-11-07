"""Implement a 96-bit record with source count/format and status ownership changes."""
from nes_raw506 import once


def counted(s):
    # 32*33 + 224 + 128 + 128 + 224 + 64 + 7*256 = 3616 records.
    s=once(s,"reg [15:0] generation,records,bytes_count;", "reg [15:0] generation;reg [11:0] records;")
    s=once(s,"reg [63:0] held_data,header;","reg [63:0] held_data;")
    s=s.replace("header<=0;","").replace("bytes_count<=0;","")
    s=once(s,"header<={16'h2233,group_count,palette_count,row_count,object_count,exception_count,9'd0,patch_count};","")
    s=once(s,"reg [31:0] cycles;", "reg [$clog2(MAX_CYCLES+1)-1:0] cycles;")
    s=once(s,"records<=records+{7'd0,pack_count};","")
    s=once(s,"     if(query_kind==7)bytes_count<=bytes_count+{7'd0,pack_count};\n","")
    # One increment for each accepted source value. A mismatch that flushes
    # the previous run re-queries the same index and must not count twice.
    s=s.replace("query_index<=query_index+1'b1;", "records<=records+1'b1;query_index<=query_index+1'b1;")
    start=s.index("  tx_valid=0;tx_data=0;")
    end=s.index(" end\n task fail",start)
    return s[:start]+"""  tx_valid=live && (state==HEADER || state==VALUE || state==META_END || state==ENDING)
       || (!reset && (state==COMMIT || state==ABORT));
  tx_data[92:77]=generation;
  tx_data[95:93]=3'd7;
  tx_data[76:64]=0;
  tx_data[63:0]=0;
  case(state)
   HEADER:tx_data[63:0]={16'h2233,groups,palettes,8'd224,objects,exceptions,9'd0,patches};
   VALUE:begin
    tx_data[63:0]=held_data;
    if(query_kind==7)begin
     tx_data[76:64]=13'h1000|pack_start;
     if(map_repeat && pack_count>=10)tx_data[63:6]={49'd0,pack_count};
     else tx_data[63:60]=pack_count[3:0];
    end
    else if(query_kind==0)begin
     tx_data[95:93]=0;tx_data[76:64]=pack_start;tx_data[63]=query_index==limit;
    end
    else if(query_kind==1 || query_kind==5 || (query_kind==4 && pack_count!=1 && !map_repeat))
     tx_data[76:64]={2'b11,query_kind,count_minus_one};
    else if(pack_count!=1)tx_data[76:64]={2'b01,query_kind,count_minus_one};
    else begin tx_data[95:93]=query_kind;tx_data[76:64]=pack_start;end
   end
   META_END,ENDING:begin
    tx_data[76:64]=state==META_END?4:1;
    tx_data[27:16]=records;
    if(state==ENDING)tx_data[10:8]=patches;
   end
   COMMIT:tx_data[76:64]=3;
   ABORT:begin tx_data[76:64]=2;tx_data[3:0]=error;end
   default:;
  endcase
"""+s[end:]


def status(s):
    # Token only advances at SS release after a complete validated D2.
    # Snapshot all mutable status fields on command reception, even when busy.
    s=once(s,"reg [47:0] snapshot;", "reg [8:0] status_size;reg [2:0] status_flags;")
    s=once(s,"end else reply=byte_count==7?status_crc:snapshot[47:40];","""end else case(byte_count)
   1:reply=8'hd6;
   2:reply={status_flags[2],5'd0,status_flags[1:0]};
   3:reply=token[15:8];4:reply=token[7:0];
   5:reply={7'd0,status_size[8]};6:reply=status_size[7:0];
   7:reply=status_crc;default:reply=0;
  endcase""")
    s=once(s,"snapshot<=0;","status_size<=0;status_flags<=0;")
    s=once(s,"     if(byte_count>=1 && byte_count<=6)snapshot<={snapshot[39:0],8'd0};\n","")
    return once(s,"snapshot<={8'hd6,flags,token,7'd0,public_size};","status_flags<={fault,!ack_valid,available};status_size<=public_size;")


def lanes(s):
    # Eight byte lanes serve both 8x8 raster/palette and 10x6 raw literals.
    # Only the oldest two sextets require additional storage.
    s=once(s,"reg [63:0] held_data;", """reg [63:0] held_data;reg [11:0] older;
 wire [59:0] sextets={older,held_data[61:56],held_data[53:48],held_data[45:40],
                     held_data[37:32],held_data[29:24],held_data[21:16],
                     held_data[13:8],held_data[5:0]};""")
    s=once(s,"else tx_data[63:60]=pack_count[3:0];","else tx_data[63:0]={pack_count[3:0],sextets};")
    s=once(s,"held_data<=data;pack_count<=1;map_repeat<=1;", "older<=0;held_data<=data;pack_count<=1;map_repeat<=1;")
    s=once(s,"held_data<={4'd0,held_data[53:0],data[5:0]};",
           "older<={older[5:0],held_data[61:56]};held_data<={held_data[55:0],data[7:0]};")
    # Every ordinary run or patch starts by loading a full value. Each raster
    # or palette record shifts exactly eight bytes before it can be published.
    return s.replace("held_data<=0;","")


def ram_port(s):
    start=s.index(" always @(posedge clk)begin\n  read_byte<=buffer")
    end=s.index(" reg [7:0] shift,command",start)
    return s[:start]+""" wire cell_write=take_cell || cell_tail;
 wire wire_write=active && wen652;
 wire port_write=!reset && (cell_write || write_serial || wire_write);
 reg [8:0] port_address;
 reg [7:0] port_data;
 always @* begin
  port_address=active?addr652:{1'b0,spi_index};
  port_data=wd652;
  if(cell_write)begin
   port_address={1'b1,cells,cell_tail};
   port_data=cell_tail?{1'b0,cell_upper}:record_data[7:0];
  end else if(write_serial)begin
   port_address={1'b0,used[7:0]};port_data=pack_byte;
  end else if(wire_write)port_address={1'b0,wa652};
 end
 always @(posedge clk)begin
  if(port_write)buffer[port_address]<=port_data;
  else read_byte<=buffer[port_address];
 end
"""+s[end:]


def apply(base,out,use_lanes=False,single_port=False):
    from prepare_nes_record657 import copy_inputs
    copy_inputs(base,out)
    for name,change in (("nes_native_export203.sv",counted),("nes_native_spi165.sv",status)):
        path=out/name
        source=change(path.read_text())
        if use_lanes and name=="nes_native_export203.sv":source=lanes(source)
        if single_port and name=="nes_native_spi165.sv":source=ram_port(source)
        path.write_text(source,newline="\n")
