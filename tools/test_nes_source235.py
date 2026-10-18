# SPDX-License-Identifier: MIT
"""frame201 query and two-bank SPI235 on the SAME234 scrolling fixtures.

Delta encoder remains a host fixture between these two tested RTL endpoints.
Actual SPI blocks feed actual C234/planner231; not whole-board/game/FPS.
"""
from pathlib import Path
import argparse,json,os,re,shutil,struct,subprocess
from nes_delta231 import ROOT,BASE,sha,once


def read_records(path):
    b=path.read_bytes();out=[];at=0
    while at<len(b):
        n=struct.unpack_from('<H',b,at)[0];at+=2;assert 0<n<=243 and at+n<=len(b)
        out.append(b[at:at+n]);at+=n
    return out


def query_tb():
    s=(ROOT/'tests/nes-functional/geometry230_tb.sv').read_text().replace('module geometry230_tb;','module source_query235_tb;')
    a=s.index(' reg enable=0;');b=s.index(' reg [106:0] stimulus',a)
    s=s[:a]+''' reg enable=0;wire start_ready,out_valid;reg out_ready=1;wire [7:0] out_data;wire [12:0] out_offset;
 wire query_done;wire [3:0] query_fault;integer seen=0,queries=0,cycle=0;reg [7:0] expected[0:5740];
 assign exporter_release=0;
 nes_source_query235 reader(.clk(clk),.reset(reset),.abort_source(1'b0),.start(enable),.start_ready(start_ready),
 .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),.patch_count(patch_count),
 .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),
 .query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
 .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_offset(out_offset),.done(query_done),.fault(query_fault));
 always @(negedge clk)begin cycle++;out_ready=cycle%7!=0&&cycle%13!=0;end
 always @(posedge clk)if(!reset)begin
  if(query_fault)$fatal(1,"query fault frame%0d code%0d",f,query_fault);
  if(query)queries++;
  if(out_valid&&out_ready)begin
   if(out_offset!=seen||out_data!==expected[seen])$fatal(1,"canonical mismatch frame%0d at%0d got%h expected%h",f,seen,out_data,expected[seen]);
   seen++;
  end
 end
''' + s[b:]
    a=s.index(' always @(posedge clk)begin\n  ack_valid');b=s.index(' initial begin\n  if(!$value',a);s=s[:a]+s[b:]
    a=s.index('   name=$sformatf("frame%0d.wire"');b=s.index('\n  end\n  $display',a)
    s=s[:a]+'''   name=$sformatf("frame%0d.expected",f);$readmemh(name,expected);
   seen=0;queries=0;wait(start_ready);@(negedge clk);enable=1;@(negedge clk);enable=0;
   wait(query_done);@(negedge clk);
   if(seen!=5741||queries!=group_count*33+224+object_count+exception_count+224+palette_count*32)$fatal(1,"count/queries");
   $display("QUERY235 frame=%0d bytes=%0d queries=%0d",f,seen,queries);
   manual_release=1;@(negedge clk);manual_release=0;frames++;
''' + s[b:]
    return s.replace('PASS GEOMETRY230 frames=','PASS QUERY235 frames=')


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
    p.add_argument('--skip-query',action='store_true');a=p.parse_args();d=a.out.resolve();assert str(d).isascii() and not d.exists()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    prior=BASE/'probes/nes-source234/test03';board=BASE/'probes/nes-counter224/mapfit02';pins={}
    def copy(f,to=d):
        shutil.copyfile(f,to/f.name);pins[str(f.relative_to(BASE))]=sha(f)
    def run(exe,args,name,cwd=d,timeout=600):
        with (cwd/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(exe),*map(str,args)],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(cwd/(name+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-6000:]
        return t
    qbin=a.questa_bin;bus=d/'bus';bus.mkdir()
    for f in (ROOT/'src/nes/rtl/nes_source_spi235.sv',ROOT/'tests/nes-functional/source_spi235_tb.sv',board/'nes_native_mailbox206.sv'):copy(f,bus)
    allrec=[];lines=['71'];byframe={}
    for f in range(905,976):
        rr=read_records(prior/f'frame{f}.stream');byframe[f]=rr;allrec.extend(rr)
        lines.extend(f'{len(b):x} {int(i==len(rr)-1):x} '+b.hex(' ') for i,b in enumerate(rr))
        pins[str((prior/f'frame{f}.stream').relative_to(BASE))]=sha(prior/f'frame{f}.stream')
    (bus/'records.hex').write_text('\n'.join(lines)+'\n')
    run(qbin/'vlib.exe',['work'],'vlib',bus)
    run(qbin/'vlog.exe',['-sv','nes_native_mailbox206.sv','nes_source_spi235.sv','source_spi235_tb.sv'],'vlog',bus)
    cases=[];first_blocks=None
    for phase in (3.5,17.0):
        t=run(qbin/'vsim.exe',['-c','work.source_spi235_tb',f'-gPHASE={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],f'phase{phase}',bus)
        assert 'PASS SPI235' in t
        received=[];index=0;wire=0
        for line in (bus/'blocks.txt').read_text().splitlines():
            tok,n,b=line.split();b=bytes.fromhex(b);assert int(tok)==len(received) and len(b)==int(n)<=248
            at=0
            while at<len(b):
                r=allrec[index];assert b[at:at+len(r)]==r and at+len(r)<=len(b),'record split/content';at+=len(r);index+=1
            received.append(b);wire+=len(b)
        assert index==len(allrec)
        if first_blocks is None:first_blocks=received
        else:assert received==first_blocks
        shutil.copyfile(bus/'blocks.txt',bus/f'blocks-phase{phase}.txt')
        cases.append(dict(phase=phase,records=index,blocks=len(received),payload=wire,summary=[l for l in t.splitlines() if '235 ' in l]))
    # Feed the bytes actually received over SPI to actual C234, not originals.
    host=d/'host';host.mkdir();flat=b''.join(first_blocks);at=0
    for f,rr in byframe.items():
        packed=bytearray()
        for r in rr:
            b=flat[at:at+len(r)];at+=len(r);packed+=struct.pack('<H',len(b))+b
        (host/f'frame{f}.stream').write_bytes(packed)
    for f in prior.iterdir():
        if f.suffix in ('.c','.h','.inc') or f.name in ('palette.bin','wrap.stream','coldwrap.stream'):copy(f,host)
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    run(gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],'build',host)
    ht=run(host/'host.exe',[BASE/'probes/nes-geometry230/rtl02','C:/Users/mohallo/Downloads/test/Super Mario Bros 3 (J).nes',905,975,host],'run',host)
    for f in range(905,976):
        for ext in ('geometry','raw','metadata','packets','plans'):assert (host/f'frame{f}.{ext}').read_bytes()==(prior/f'frame{f}.{ext}').read_bytes()
    query_pass=False
    if not a.skip_query:
        out=d/'query';out.mkdir();names=['nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181']
        for n in names:copy(board/(n+'.sv'),out)
        copy(ROOT/'src/nes/rtl/nes_source_query235.sv',out)
        (out/'source_query235_tb.sv').write_text(query_tb(),encoding='utf-8',newline='\n')
        stimulus=BASE/'probes/nes-geometry230/stim05';e=json.loads((stimulus/'result.json').read_text())
        for row in e['frames']:
            f=row['frame'];assert sha(stimulus/f'frame{f}.hex')==row['stimulus_sha256']
            for ext in ('hex','palette'):copy(stimulus/f'frame{f}.{ext}',out)
            (out/f'frame{f}.expected').write_text((prior/f'frame{f}.geometry').read_bytes().hex(' '))
        run(qbin/'vlib.exe',['work'],'vlib',out)
        run(qbin/'vlog.exe',['-sv',*[n+'.sv' for n in names],'nes_source_query235.sv','source_query235_tb.sv'],'vlog',out)
        qt=run(qbin/'vsim.exe',['-c','work.source_query235_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim',out)
        assert 'PASS QUERY235 frames=71' in qt;query_pass=True
    r=dict(passed=True,scope=__doc__,spi_cases=cases,c_output=ht,query71=query_pass,source_pins=pins,
           runner_sha256=sha(Path(__file__)),encoder_rtl=False,whole_board=False,physical=False,new_fit=False)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,spi=cases,query71=query_pass,c_output=ht)))


if __name__=='__main__':main()
