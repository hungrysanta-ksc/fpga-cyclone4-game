# SPDX-License-Identifier: MIT
"""036: unchanged035 C waveform replay against legacy/fixed034 FPGA boundary."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
BOUNDARY_SHA="8e2d7b2b0cbb3706db8fa325ffb6cf0e7ca7ad0d9d57c0d5c943a963f045b969"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)
def fixed_boundary():
    p=ROOT/"src/nes/nes_h1_board_bus.sv"
    assert sha(p)==BOUNDARY_SHA
    s=p.read_text()
    s=replace(s," assign spi_miso=reply[7-bit_count];",
        " reg miso_hold=0;\n assign spi_miso=miso_hold;")
    s=replace(s,"   ss_sync<=3;sck_sync<=0;mosi_sync<=0;",
        "   miso_hold<=0;ss_sync<=3;sck_sync<=0;mosi_sync<=0;")
    s=replace(s,"   if(ss_sync[1])begin",
        """   // Mode0: advance MISO on synchronized falling SCK only.
   // The master may sample anywhere in the high half-cycle (035 reads at +2us).
   if(!ss_sync[1] && !sck_sync[1] && sck_previous)
    miso_hold<=reply[7-bit_count];
   if(ss_sync[1])begin
    miso_hold<=0;""")
    return s

def capture_c(out,gcc):
    out.mkdir()
    source=ROOT/"src/nes/firmware/nes_h1_stm32.c"
    s=replace(source.read_text(),"((GPIOB->IDR>>4)&1u)","h1_read_miso()")
    (out/"binding.c").write_text(s)
    for name in ("nes_h1_stm32.h","nes_h1_session.h"):
        shutil.copy2(ROOT/"src/nes/firmware"/name,out/name)
    h=(ROOT/"tests/nes-functional/h1_stm32_mock.h").read_text()
    (out/"h1_stm32_mock.h").write_text(h+"\nunsigned h1_read_miso(void);\n")
    for name in ("config","bits","timer","snes","fpga","fpga_spi","fileops","uart"):
        (out/(name+".h")).write_text('#include "h1_stm32_mock.h"\n')
    s=(ROOT/"tests/nes-functional/h1_stm32_test.c").read_text()
    s=replace(s,'#include "../../src/nes/firmware/nes_h1_stm32.c"','#include "binding.c"')
    s=replace(s,"static FILE *trace;","""static FILE *trace,*wave;
static unsigned long long previous_ns;
static unsigned samples;
static void record(int expect) {
 unsigned long long ns=(unsigned long long)now_us*1000;
 fprintf(wave,"%llu %u %u %u %d\\n",ns-previous_ns,
   (port_a.ODR>>4)&1u,(port_b.ODR>>3)&1u,(port_b.ODR>>5)&1u,expect);
 previous_ns=ns;
}
unsigned h1_read_miso(void) {
 unsigned bit=(port_b.IDR>>4)&1u;
 record(bits<=8 || command_byte==0xe8 || command_byte==0xe9 ? -2:(int)bit);
 samples++;return bit;
}""")
    s=replace(s," if(before==high)return;"," record(-1);\n if(before==high)return;")
    s=replace(s," assert(argc==2);trace=fopen(argv[1],\"w\");assert(trace);",
        ' assert(argc==3);trace=fopen(argv[1],"w");assert(trace);wave=fopen(argv[2],"w");assert(wave);')
    cut=' setup();assert(nes_h1_run());assert(arms==1 && stops==1);puts("PASS re-entry");'
    assert s.count(cut)==1
    s=s.split(cut)[0]+' printf("PASS C waveform samples=%u\\n",samples);fclose(trace);fclose(wave);return 0;\n}\n'
    (out/"capture.c").write_text(s)
    cmd=[str(gcc),"-std=c11","-D__USE_MINGW_ANSI_STDIO=1","-Wall","-Wextra","-Werror",
         "-O2","-I"+str(out),str(out/"capture.c"),
         str(ROOT/"src/nes/firmware/nes_h1_session.c"),"-o",str(out/"capture.exe")]
    for label,args in [("compile",cmd),("capture",[str(out/"capture.exe"),str(out/"transactions.tsv"),str(out/"waveform.txt")])]:
        cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/(label+".log")).write_bytes(cp.stdout);assert cp.returncode==0,label
    assert "PASS C waveform samples=224" in (out/"capture.log").read_text()
    return {"binding_sha256":sha(source),"session_sha256":sha(ROOT/"src/nes/firmware/nes_h1_session.c"),
        "sample_instrumentation":"Replace only IDR read expression with logging callback; delay/control code unchanged",
        "samples":224,"waveform_sha256":sha(out/"waveform.txt")}

def main():
    p=argparse.ArgumentParser()
    for n in ("out","build","questa-bin","gcc"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    assert re.fullmatch(r"18000@(?:localhost|127\.0\.0\.1)",os.environ.get("SALT_LICENSE_SERVER",""))
    assert str(out).isascii() and not out.exists();out.mkdir()
    m={"candidate":"NES-H1-SPI-036","c_waveform":capture_c(out/"c-wave",a.gcc),"runs":{}}
    files=["nes_packet_queue_ram","nes_packet_cdc_ram","nes_host_stage","nes_snes_frontend",
           "nes_transport","nes_h1_pattern_producer","nes_h1_pattern","nes_h1_board_bus"]
    for version in ("legacy","fixed"):
        folder=out/version;folder.mkdir()
        for name in files:shutil.copy2(ROOT/"src/nes"/(name+".sv"),folder/(name+".sv"))
        if version=="fixed":(folder/"nes_h1_board_bus.sv").write_text(fixed_boundary())
        for name in ("h1-pattern.hex","h1-program.hex","program-full.hex"):
            shutil.copy2(a.build/name,folder/name)
        shutil.copy2(out/"c-wave/waveform.txt",folder/"waveform.txt")
        shutil.copy2(ROOT/"tests/nes-functional/h1_spi_wave_tb.sv",folder/"h1_spi_wave_tb.sv")
        tb=(ROOT/"tests/nes-functional/h1_board_tb.sv").read_text()
        tb=replace(tb,"   rx[b]=spi_miso;#2000;SPI_SCK=0;",
           "   #2000;rx[b]=spi_miso;SPI_SCK=0;")
        (folder/"h1_board_tb.sv").write_text(tb)
        def run(tool,args,label):
            with (folder/(label+".log")).open("wb") as log:
                cp=subprocess.run([str(a.questa_bin/(tool+".exe")),*args],cwd=folder,
                    stdout=log,stderr=subprocess.STDOUT,timeout=180)
            return cp.returncode
        assert run("vlib",["work"],"vlib")==0
        assert run("vlog",["-sv",*[n+".sv" for n in files],"h1_spi_wave_tb.sv","h1_board_tb.sv"],"compile")==0
        records={}
        for top,label in [("h1_spi_wave_tb","wave"),("h1_board_tb","board")]:
            code=run("vsim",["-c",top,"-do","onerror {quit -code 1}; run -all; quit -f"],label)
            text=(folder/(label+".log")).read_text(errors="replace")
            failed=bool(re.search(r"\*\* (?:Fatal|Error):",text))
            if version=="legacy":
                assert failed and ("SPI sample mismatch" in text if label=="wave" else "SPI queryf0 got4b expecteda5" in text),text
                records[label]={"expected_failure":True,"exit_code":code}
            else:
                marker="PASS C SPI WAVE samples=224" if label=="wave" else "PASS NES H1 BOARD checks=6 rombytes=65536 payloadbytes=8192"
                assert code==0 and not failed and marker in text,text
                records[label]={"passed":True,"exit_code":code}
        if version=="fixed":
            rows=[list(map(int,line.split())) for line in (folder/"board-bytes.tsv").read_text().splitlines()]
            rom=bytes(int(s,16) for s in (a.build/"program-full.hex").read_text().split())
            pattern=bytes(int(s,16) for s in (a.build/"h1-pattern.hex").read_text().split())
            assert bytes(v for k,addr,v in rows if k==1)==rom
            assert bytes(v for k,addr,v in rows if k==2)==pattern+pattern[:2048]
        m["runs"][version]=records
        (out/"result.json").write_text(json.dumps(m,indent=2)+"\n")
    m["fixed_boundary_sha256"]=sha(out/"fixed/nes_h1_board_bus.sv")
    m["passed"]=True;(out/"result.json").write_text(json.dumps(m,indent=2)+"\n")
    print(json.dumps(m,indent=2))
if __name__=="__main__":main()
