"""Sample STOP on the original snapshot edge; apply it at the first CRC rotation."""
from pathlib import Path
import argparse
import shutil
from nes_raw506 import once


def snapshot(text):
    text = once(text, "(progress&&!stop&&idle_receipt)", "(progress&&idle_receipt)")
    anchor = " wire [8:0] expected_length="
    text = once(text, anchor, """ // The first CRC rotation is exactly one host edge after command capture.
 // The same STOP sample qualifies both the stored flag and its independent CRC.
 reg sampled_stop801;
 always @(posedge clk) sampled_stop801<=stop;
 wire mask_progress801=crc_busy && crc_position==0 && sampled_stop801;
 wire [7:0] head801={snapshot[135:132],snapshot[131]&&!mask_progress801,snapshot[130:128]};
""" + anchor)
    assert text.count("snapshot<={snapshot[127:0],snapshot[135:128]}") == 2
    text = text.replace("snapshot<={snapshot[127:0],snapshot[135:128]}", "snapshot<={snapshot[127:0],head801}")
    text = once(text,"crc8(status_crc,snapshot[135:128])","crc8(status_crc,head801)")
    return once(text,"?status_crc:snapshot[135:128]","?status_crc:head801")


def serial_snapshot(text):
    """Freeze data at command acceptance; cover the actual outgoing bits with CRC8."""
    text = once(text, "reg crc_busy;reg [4:0] crc_position;integer j;", "reg stop_at_command;integer j;")
    text = once(text, "(progress&&!stop&&idle_receipt)", "(progress&&idle_receipt)")
    old = "  if(command==8'he0&&byte_count>=1&&byte_count<=19)reply=byte_count==1?8'hf7:byte_count==19?status_crc:snapshot[135:128];"
    rows = ["  if(command==8'he0)begin", "   case(byte_count)", "    1:reply=8'hf7;",
            "    2:reply={snapshot[135:132],snapshot[131]&&!stop_at_command,snapshot[130:128]};"]
    rows += [f"    {n}:reply=snapshot[{151-8*n}:{144-8*n}];" for n in range(3,19)]
    rows += ["    19:reply=status_crc;", "    default:reply=0;", "   endcase",
             "   if(byte_count>=7 && byte_count<=18 && !snapshot[129])reply=0;", "  end"]
    text = once(text, old, "\n".join(rows))
    text = once(text, "crc_busy<=0;crc_position<=0;", "stop_at_command<=0;")
    start = text.index("   // Seventeen changing bytes")
    end = text.index("   if(ack_write", start)
    text = text[:start] + text[end:]
    text = once(text, "    shift<=incoming;bit_count<=bit_count+1'b1;", """    shift<=incoming;bit_count<=bit_count+1'b1;
    // MISO was registered on the preceding falling edge. Include F7 via the
    // initial seed and the following 17 bytes one transmitted bit at a time.
    if(command==8'he0 && byte_count>=2 && byte_count<=18)
     status_crc<={status_crc[6:0],1'b0} ^ ((status_crc[7]^miso_hold)?8'h07:8'h00);""")
    text = once(text, "crc_position<=0;crc_busy<=1;", "stop_at_command<=stop;")
    text = once(text, "ack_valid?ack_work[j*8+:8]:8'd0", "ack_work[j*8+:8]")
    return once(text, """     end else if(command==8'he0)begin
      if(byte_count>=2&&byte_count<=18)snapshot<={snapshot[127:0],snapshot[135:128]};
""", "")


def serial_request(text):
    # E1 is the only command whose request CRC is checked. Its first byte is
    # already known when the command is decoded; stream the remaining bits.
    text = once(text, "request_crc<=crc16(16'hffff,incoming);",
                "request_crc<=crc16(16'hffff,8'he1);")
    text = once(text, "       request_crc<=crc16(request_crc,incoming);", "")
    return once(text, "    shift<=incoming;bit_count<=bit_count+1'b1;", """    shift<=incoming;bit_count<=bit_count+1'b1;
    if(command==8'he1 && byte_count!=0 && (byte_count<=14 || byte_count<=expected_length))
     request_crc<={request_crc[14:0],1'b0} ^ ((request_crc[15]^mosi[1])?16'h1021:16'h0000);""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base",type=Path)
    ap.add_argument("dest",type=Path)
    ap.add_argument("--serial",action="store_true")
    ap.add_argument("--request",action="store_true")
    a=ap.parse_args()
    shutil.copytree(a.base, a.dest, ignore=shutil.ignore_patterns("db","incremental_db","output_files","*.log","*.rpt"))
    p=a.dest/"nes_sink_spi165.sv"
    text=(serial_snapshot if a.serial else snapshot)(p.read_text())
    p.write_text(serial_request(text) if a.request else text, newline="\n")
