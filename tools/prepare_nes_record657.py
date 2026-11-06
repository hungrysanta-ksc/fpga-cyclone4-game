"""Build a board-bound 80-bit source record transport from the verified 656 ingress."""
import argparse
import re
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def exporter(source, staged):
    # The generation travels in fixed-signature or reserved terminal payload bits.
    source = once(source, "[95:0] tx_data", "[79:0] tx_data")
    source = source.replace("3'd7,generation,", "3'd7,").replace("3'd0,generation,", "3'd0,").replace("query_kind,generation,", "query_kind,")
    source = once(source, "header<={16'h2233,", "header<={frame_generation,")
    source = once(source, "13'd3,64'd0", "13'd3,generation,48'd0")
    source = once(source, "13'd2,60'd0,error", "13'd2,generation,44'd0,error")
    if not staged:
        return source
    # Store the awaited count record in the same register as query responses.
    source = once(source, "reg [63:0] held_data,header;", "reg [63:0] held_data;")
    source = once(source, "generation,records,bytes_count;", "generation,records;")
    source = source.replace("bytes_count<=0;", "").replace("header<=0;", "")
    source = once(source, "header<=", "held_data<=")
    source = once(source, "     if(query_kind==7)bytes_count<=bytes_count+{7'd0,pack_count};\n", "")
    source = once(source, "if(query_kind==5)state<=META_END;else if(query_kind==7)state<=ENDING;", """if(query_kind==5)begin held_data<={32'd0,records,16'd0};state<=META_END;end
     else if(query_kind==7)begin held_data<={32'd0,records,3'd0,query_index};state<=ENDING;end """)
    source = once(source, "if(tx_ready)state<=ASK;", "if(tx_ready)begin held_data<=0;state<=ASK;end")
    start = source.index("  tx_valid=0;tx_data=0;")
    end = source.index(" end\n task fail", start)
    return source[:start] + """  // One payload path for query values, frame header, and accepted counts.
  tx_data[63:0]=held_data;
  tx_data[79:64]={3'd7,13'd0};
  tx_valid=live;
  case(state)
   HEADER:;
   VALUE:begin
    if(query_kind==7)begin
     tx_data[79:64]={3'd7,(13'h1000|pack_start)};
     if(map_repeat && pack_count>=10)tx_data[63:0]={49'd0,pack_count,held_data[5:0]};
     else tx_data[63:60]=pack_count[3:0];
    end else if(query_kind==0)begin tx_data[79:64]={3'd0,pack_start};tx_data[63]=(query_index==limit);end
    else if(query_kind==1 || query_kind==5 || (query_kind==4 && pack_count!=1 && !map_repeat))
     tx_data[79:64]={3'd7,2'b11,query_kind,count_minus_one};
    else if(pack_count!=1)tx_data[79:64]={3'd7,2'b01,query_kind,count_minus_one};
    else tx_data[79:64]={query_kind,pack_start};
   end
   META_END:tx_data[79:64]=16'he004;
   ENDING:tx_data[79:64]=16'he001;
   COMMIT,ABORT:begin tx_valid=!reset;tx_data[79:64]=state==COMMIT?16'he003:16'he002;end
   default:tx_valid=0;
  endcase
""" + source[end:]


def host(source):
    source = once(source, "[95:0] record_data", "[79:0] record_data")
    source = source.replace("record_data[95:93]", "record_data[79:77]")
    source = once(source, "reg terminal;", """wire header_record=record_data[79:64]==16'he000;
 wire abort_record=record_data[79:64]==16'he002;
 wire commit_record=record_data[79:64]==16'he003;
 wire explicit_generation=header_record || abort_record || commit_record;
 reg terminal;""")
    source = once(source,"wire [7:0] pack_byte=held[95:88];","""wire [7:0] pack_byte=position==2?map_generation[15:8]:
                       position==3?map_generation[7:0]:held[79:72];""")
    source = once(source,"reg [95:0] held","reg [79:0] held")
    source = once(source,"    map_generation<=record_data[92:77];\n","")
    source = once(source,"held<={record_data[79:77],record_data[76:64],record_data[92:77],record_data[63:0]};","""if(explicit_generation)map_generation<=record_data[63:48];
     held<={record_data[79:64],header_record?16'h2233:
             (abort_record || commit_record)?16'd0:record_data[63:48],record_data[47:0]};""")
    source = once(source,"group_start[11:0],map_generation,", "group_start[11:0],")
    return once(source,"held<={held[87:0],8'd0};","if(position!=2 && position!=3)held<={held[71:0],8'd0};")


def copy_inputs(base, out):
    pins=evidence("stream656-verification.json")["modes"]["ingress"]
    assert digest(base/"output_files/board.fit.rpt")==pins["fit"]["fit_report"]
    for name,value in pins["rtl"].items():
        assert digest(base/name)==value,name
    out.mkdir(parents=True,exist_ok=False)
    for name in set(evidence("trial613-package.json")["inputs"]) | {"nes_geometry_sender653.sv"}:
        target=out/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/name,target)


def board(base, out, staged, split=False):
    copy_inputs(base,out)
    def revise(name,fn):
        path=out/name
        path.write_text(fn(path.read_text()),newline="\n")
    revise("nes_native_export203.sv",lambda s:exporter(s,staged))
    if staged:
        revise("nes_native_export203.sv",lambda s:once(once(s,"error<=reason;state<=ABORT;","held_data<={generation,44'd0,reason};error<=reason;state<=ABORT;"),"if(ack_accept)state<=COMMIT;","if(ack_accept)begin held_data<={generation,48'd0};state<=COMMIT;end "))
    revise("nes_native_spi165.sv",host)
    revise("nes_live_joint.sv",lambda s:once(once(once(s,"[95:0] native_tx_data","[79:0] native_tx_data"),"[95:0] native_host_data","[79:0] native_host_data"),".WIDTH(96)) native_records",".WIDTH(80)) native_records"))
    if split:
        from nes_split657 import split_source, split_host
        revise("nes_native_export203.sv",split_source)
        revise("nes_native_spi165.sv",split_host)
        revise("nes_live_joint.sv",lambda s:once(once(s.replace("[79:0] native_","[41:0] native_").replace(".WIDTH(80)) native_records",".WIDTH(42)) native_records"),".tx_data(native_tx_data)",".segment(native_tx_data)"),".record_data(native_host_data)",".segment(native_host_data)"))
    # Only retired lanes are removed. The REQ/ACK and all surviving data
    # endpoints keep their original per-bit constraints.
    def constraints(s):
        return "".join(line for line in s.splitlines(keepends=True) if not any(
            int(bit)>=(42 if split else 80) for bit in re.findall(r"native_records\|(?>held|received)\[(\d+)\]",line)))
    for p in out.glob("*.sdc"):
        if constraints(p.read_text())!=p.read_text():revise(p.name,constraints)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--staged",action="store_true")
    mode.add_argument("--split",action="store_true")
    mode.add_argument("--count",action="store_true")
    mode.add_argument("--direct",action="store_true")
    mode.add_argument("--lanes",action="store_true")
    mode.add_argument("--port",action="store_true")
    a=p.parse_args()
    if a.count or a.lanes or a.port:
        from nes_count657 import apply
        apply(a.base,a.out,a.lanes or a.port,a.port)
    else:
        board(a.base,a.out,a.staged or a.direct,a.split)
        if a.direct:
            from nes_hold657 import direct_board
            direct_board(a.out)
