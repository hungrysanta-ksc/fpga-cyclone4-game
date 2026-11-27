"""Instrument the exported-input candidate in the existing D2 and diagnostic responses."""
import argparse
import shutil
from pathlib import Path
from prepare_nes_kirby1027 import replace
from prepare_nes_kirby1035 import BASE, prepare

ROOT=Path(__file__).resolve().parents[1]


def instrument(out):
    prepare(out)
    def edit(module,old,new):
        replace(out/(module+'.sv'),old,new)
    module='nes_input_times1035'
    shutil.copy(ROOT/'src/fpga/nes_capture1035'/(module+'.sv'),out)
    with (out/'board.qsf').open('a') as f:
        f.write('\nset_global_assignment -name SYSTEMVERILOG_FILE nes_input_times1035.sv\n')
    edit('nes_display1010','output reg [7:0] reply','output wire offer_phase,output reg [7:0] reply')
    edit('nes_display1010',' wire [15:0] now=', ' assign offer_phase=clock_count[14];\n wire [15:0] now=')
    edit('nes_screen_status151','module nes_screen_status151(', 'module nes_screen_status151(output wire offer_phase,')
    edit('nes_screen_status151','trace(.','trace(.offer_phase(offer_phase),.')
    edit('fxpak_nes_screen137_top',' wire accepted1034',' wire offer_phase;\n wire accepted1034')
    for instance in ('core','screen_status'):
        edit('fxpak_nes_screen137_top',instance+'(.group1034',instance+'(.offer_phase(offer_phase),.group1034')
    edit('nes_live_joint','module nes_live_joint(','module nes_live_joint(input wire offer_phase,')
    edit('nes_live_joint','nes_native_spi165 native_spi(','''reg release1035,start1035;
 always @(posedge clk)begin release1035<=!reset && native_release_frame;start1035<=capture_begin611;end
 nes_native_spi165 native_spi(.phase(offer_phase),.source_release(release1035),.source_start(start1035),''')
    edit('nes_native_spi165','module nes_native_spi165(','module nes_native_spi165(input wire phase,source_release,source_start,')
    spi=(out/'nes_native_spi165.sv').read_text()
    i=spi.index(' reg [21:0] first_wait;');j=spi.index(' reg [7:0] status_crc;',i)
    edit('nes_native_spi165',spi[i:j],''' wire [6:0] interval1035;
 wire pop1035=ss[1]&&!prev_ss&&command==8'hd2&&cursor==7&&bit_count==0&&!bad&&available&&read_seen&&offset==token&&arg==0;
 wire read1035=!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&cursor==511&&incoming==8'hd1;
 nes_input_times1035 capture_times(.clk(clk),.reset(reset),.phase(phase),.source_release(source_release),
  .source_start(source_start),.first_offer(available&&has_header),.first_read(read1035),
  .pop(pop1035),.pop_first(has_header),.stamp(interval1035));
 wire [6:0] ready_age=command==8'hd2 && reading && read_seen ? interval1035:7'd0;
''')
    # The existing independent return RAM still records the actual token retirements.
    name='nes_display1010'
    edit(name,'if(accepted1034 && n1034<5)','if(writer!=writer_previous && n1034<5)')
    edit(name,"1:reply<=8'ha4;","1:reply<=8'ha5;")
    # Only physical seal/return and final PPU events belong to this format.
    s=(out/(name+'.sv')).read_text()
    edit(name,s[s.index(' (* altera_attribute',s.index('reg [2:0] n1034;')):s.index('  aq1034<=')], ' always @(posedge clk) begin\n')
    for a,b in [('reg [7:0] aq1034,rq1034,last_group1034;','reg [7:0] aq1034,rq1034;'),
                ('n1034<=0;group_seen1034<=0;', 'n1034<=0;'),
                ('   if(start1034)begin last_group1034<=now[7:0];group_seen1034<=1;end',''),
                ('20:reply<=last_group1034;', "20:reply<=8'd0;"),
                ('{group_seen1034,n1034,','{1\'b0,n1034,')]:
        edit(name,a,b)
    path=out/(name+'.sv')
    assert path.read_text().count('accepted1034 || start1034 || ')==2
    path.write_text(path.read_text().replace('accepted1034 || start1034 || ',''),newline='\n')
    sdc=out/'board.sdc';s=sdc.read_text();i=s.index('set s1034 [cdc181_exact');s=s[:i]
    for source,dest in [('release1035','rs'),('start1035','cs')]:
        s+=f'set s1035 [cdc181_exact {{nes_live_joint:core|{source}}}]\n'
        s+=f'set d1035 [cdc181_exact {{nes_live_joint:core|nes_native_spi165:native_spi|nes_input_times1035:capture_times|{dest}[0]}}]\n'
        s+='set_max_delay 11.904 -from $s1035 -to $d1035\nset_false_path -hold -from $s1035 -to $d1035\n'
    sdc.write_text(s,newline='\n')


def arm(out):
    from prepare_nes_trial802 import rename_edition
    source=BASE.parent/'link'
    shutil.copytree(source,out)
    names=out.parent/'edition'
    rename_edition(source/'src',names,1034,1035)
    for entry in names.iterdir():
        shutil.copy2(entry,out/'src'/entry.name)
    budget=out/'src/nes_budget210.c'
    replace(budget,'edition=1034;', 'edition=1035;')
    replace(budget,'h[1]==0xa4','h[1]==0xa5')
    replace(out/'src/nes_native165.c','if(begin)begin|=', 'begin|=')
    replace(out/'src/nes_native165.c','block1029(begin,s->generation,n,t);',
            'block1029(begin | ((unsigned)tok<<16) | ((s->state==NES_NATIVE165_COMMITTED)<<8),s->generation,n,t);')
    replace(budget,'void block1029(', 'static unsigned last_commit_key,last_commit_d2;\nvoid block1029(')
    # The high half is the lag from the previous COMMIT block's checked D2
    # to this first D1, in 512 ARM cycles. Match its *next* token, including wrap.
    replace(budget,'if(begin)*a=', '''unsigned key=last_commit_key;
 last_commit_key=0;
 if(begin&256){last_commit_d2=t[4];last_commit_key=0x10000u|(uint16_t)((begin>>16)+1);return;}
 if(begin&1)*a=''')
    replace(budget,'.bytes=(begin>>1)<<24', '''.bytes=((begin&255)>>1)<<24,
   .retire=(key==(0x10000u|(begin>>16)) && ((t[0]-last_commit_d2)>>9)<65535 ?
             ((t[0]-last_commit_d2)>>9):65535u)<<16''')
    replace(budget,'pending950=NULL;latest900=0;', 'last_commit_key=0;pending950=NULL;latest900=0;')
    replace(budget,'if(begin)a->restore=t[1]-t[0]; a->retire+=t[3]-t[2];',
            '''if(begin&1)a->restore=t[1]-t[0];
 else if(a->blocks==2)a->retire|=128|((begin&255)>>1);
 else if(a->blocks==3)a->retire|=(128|((begin&255)>>1))<<8;''')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('--arm',action='store_true')
    args=p.parse_args()
    (arm if args.arm else instrument)(args.out)
