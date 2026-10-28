# SPDX-License-Identifier: MIT
"""Materialize the SAME capture/admission, host joint and plan RTL for both uses.

The board resource wrapper and functional TB keep different external memory/PPU
drivers. They do not get different source admission, lease or plan implementations.
"""
import json,shutil
from nes_delta231 import BASE, ROOT, once,sha

REFERENCE = BASE / 'probes/nes-execute362/objmap01'
COMMON = ('nes_native_capture365.sv', 'nes_capture_lease201.sv',
          'nes_joint266.sv', 'nes_plan_path267.sv', 'nes_mux260.sv',
          'nes_transport257.sv', 'nes_chr_cache192.sv', 'nes_capture_lease366.sv',
          'nes_core257.sv','nes_joint257.sv')


def materialize(d):
    # These are checked-in RTL, not different strings generated for each target.
    source_root=ROOT/'src/fpga/nes_capture365'
    manifest=json.loads((source_root/'manifest.json').read_text())
    for relative,expected in manifest['source_files'].items():
        assert sha(source_root/relative)==expected,relative
    for name in COMMON:
        parent=ROOT/'src/fpga'
        if name not in ('nes_native_capture365.sv','nes_capture_lease366.sv'):
            parent=parent/'nes_capture365'
        shutil.copyfile(parent/name,d/name)


def board(d,early=False):
    materialize(d)
    p=d/'nes_live_joint.sv';s=p.read_text()
    s=once(s,'nes_native_capture201 native_frame(', '''nes_native_capture365 native_frame(
 .stop(cancel_nes267),.source_start_ready(source_start_ready267),.source_done(source_done267),
 .identity_ready(identity_ready267),.display_ack(flow_ack267),.flow_error(flow_fault267||plan_fault267),
 .source_start(source_start365),.identity_valid(identity_pending267),.prelease(prelease365),
 .source_epoch(source_epoch365),.source_generation(source_generation365),.source_serial(source_serial267),''')
    s=once(s,'nes_native_capture365 native_frame(',f'nes_native_capture365 #(.EARLY_RELEASE({int(early)})) native_frame(.capture_materialized366(materialized366),.source_owned365(source_owned365),')
    s=once(s,'.capture_begin(),.source_ready(source_ready204)', '.capture_begin(capture_begin365),.source_ready(source_ready204)')
    s=once(s,'.clk(clk),.reset(reset),.release_frame(export_release204),.ppu_ce(tap_ce)',
           '.clk(clk),.reset(reset),.ppu_ce(tap_ce)')
    a=s.index('reg source_started267,identity_pending267;');z=s.index('assign retire_commit204=',a)
    s=s[:a]+'''wire source_start365,prelease365,capture_begin365,identity_pending267,source_owned365,materialized366;
 wire [31:0] source_epoch365,source_serial267;wire [15:0] source_generation365;
 '''+s[z:]
    s=once(s,'.start(export_permitted204&&source_start_ready267&&!source_started267)', '.start(source_start365)')
    s=once(s,'.frame_generation(captured_gen204),.content_epoch(captured_epoch204),.frame_serial(source_serial267)',
           '.frame_generation(source_generation365),.content_epoch(source_epoch365),.frame_serial(source_serial267)')
    s=once(s,'.frame_owned(native_frame_owned),.geometry_valid(native_geometry_valid&&!rom_fault)',
           '.frame_owned(source_owned365),.geometry_valid(source_owned365)')
    s=once(s,'nes_joint267_board native_joint267(', 'nes_joint267_board native_joint267(.capture_materialized366(materialized366),')
    s=s.replace('.tile_generation(captured_gen204)', '.tile_generation(source_generation365)')
    s=s.replace('.end_generation(captured_gen204)', '.end_generation(source_generation365)')
    s=once(s,'.capture_begin(1\'b0),.source_ready(source_ready204)', '.capture_begin(capture_begin365),.source_ready(source_ready204)')
    s=once(s,'.prelease361(native_frame_owned&&native_geometry_valid),.epoch361(captured_epoch204)',
           '.prelease361(prelease365),.epoch361(source_epoch365)')
    s=once(s,'.generation(captured_gen204)', '.generation(source_generation365)')
    s=once(s,'.captured_epoch(captured_epoch204),.live_epoch(source_epoch204)',
           '.captured_epoch(source_epoch365),.live_epoch(source_epoch204)')
    p.write_text(s,newline='\n')
    p=d/'board.qsf';s=p.read_text();s+='\nset_global_assignment -name SYSTEMVERILOG_FILE nes_native_capture365.sv\nset_global_assignment -name SYSTEMVERILOG_FILE nes_capture_lease366.sv\n';p.write_text(s,newline='\n')


def cadence(d):
    """Free-running next-frame attempts, independent of output completion.

    Replay the same warm scene, so no future oracle or palette replacement is
    introduced. Record a miss as a failed timing objective, not a functional PASS.
    """
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' task clear_output;', r'''
 integer capture_cycle365=0,attempts365=0,missed365=0,admitted365=0;
 integer next_cycle365,free_t365;reg free_run365=0,free_done365=0;
 always @(posedge clk)if(!reset&&capture_begin)capture_cycle365=romcycle267;
 always @(posedge clk)if(!reset&&lease_valid)begin
  if(source_generation365!==captured_generation365||source_epoch365!==captured_epoch365)
   $fatal(1,"active display context changed365");
 end
 initial begin : independent_ppu365
  wait(free_run365);
  next_cycle365=capture_cycle365+357368;
  repeat(2)begin
   while(romcycle267<next_cycle365)@(negedge clk);
   scanline=7;dot=257;drive=stimulus[7*341+257];ppu_ce=1;#1;
   attempts365++;
   if(capture_begin)admitted365++;else missed365++;
   $fwrite(events261,"capture_attempt365,907,%0d,%0d,%0d,%0d,%0t\n",attempts365,owned,capture_begin,generation,$time);
   @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
   if(attempts365==1)begin
    for(free_t365=7*341+258;free_t365<=232*341+1;free_t365++)begin
     @(negedge clk);scanline=free_t365/341;dot=free_t365%341;drive=stimulus[free_t365];ppu_ce=1;
     @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
    end
   end
   next_cycle365=next_cycle365+357368;
  end
  free_done365=1;
 end
 final $display("CADENCE365 attempts=%0d admitted=%0d missed=%0d",attempts365,admitted365,missed365);
 task clear_output;''')
    s=once(s,'   repeat(64)@(negedge clk);', '   if(f==907)free_run365=1;\n   repeat(64)@(negedge clk);')
    s=once(s,'   manual_release=1;', '''   if(f==907)begin
    wait(free_done365);
    if(attempts365!=2||admitted365+missed365!=2)$fatal(1,"missing capture attempts365");
   end
   manual_release=1;''')
    p.write_text(s,newline='\n')


def cadence366(d):
    """Actual frame908 capture overlaps frame907 output at the fixed PPU cadence.

    A following909 start is also checked. This is a bounded two-deadline test,
    not a sustained71-frame or whole-firmware throughput result.
    """
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' task clear_output;', r'''
 reg [106:0] next_stim366[0:89341];reg [191:0] next_palette366[0:0];
 reg free_run366=0,free_done366=0,capture908_done366=0;
 integer capture_cycle366=0,next_cycle366,free_t366,attempts366=0,missed366=0,admitted366=0;
 always @(posedge clk)if(!reset&&capture_begin)capture_cycle366=romcycle267;
 always @(posedge clk)if(!reset&&lease_valid)begin
  if(source_generation365!==captured_generation365||source_epoch365!==captured_epoch365)
   $fatal(1,"display context replaced during overlapping capture366");
 end
 initial begin : independent_ppu366
  $readmemh("frame908.hex",next_stim366);$readmemh("frame908.palette",next_palette366);
  wait(free_run366);next_cycle366=capture_cycle366+357368;
  while(romcycle267<next_cycle366)@(negedge clk);
  palette=next_palette366[0];scanline=7;dot=257;drive=next_stim366[7*341+257];ppu_ce=1;#1;
  attempts366++;if(capture_begin)admitted366++;else missed366++;
  $fwrite(events261,"capture_attempt366,908,%0d,%0d,%0d,%0t\n",owned,capture_begin,generation,$time);
  @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
  for(free_t366=7*341+258;free_t366<=232*341+1;free_t366++)begin
   @(negedge clk);scanline=free_t366/341;dot=free_t366%341;drive=next_stim366[free_t366];ppu_ce=1;
   @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
  end
  capture908_done366=1;
  next_cycle366=next_cycle366+357368;
  while(romcycle267<next_cycle366)@(negedge clk);
  scanline=7;dot=257;drive=next_stim366[7*341+257];ppu_ce=1;#1;
  attempts366++;if(capture_begin)admitted366++;else missed366++;
  $fwrite(events261,"capture_attempt366,909,%0d,%0d,%0d,%0t\n",owned,capture_begin,generation,$time);
  @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);free_done366=1;
 end
 final $display("CADENCE366 attempts=%0d admitted=%0d missed=%0d",attempts366,admitted366,missed366);
 task clear_output;''')
    s=once(s,'   for(t=7*341+257;t<=232*341+1;t++)begin', '''   if(f==908)begin
    wait(capture908_done366);wait(owned);
   end else for(t=7*341+257;t<=232*341+1;t++)begin''')
    s=once(s,'   repeat(64)@(negedge clk);', '   if(f==907)free_run366=1;\n   repeat(64)@(negedge clk);')
    s=once(s,'queries!=group_count*33+224+object_count+exception_count+224+palette_count*32+patch_count*256',
           'queries!=dut.core.encoder.q_maps+224+dut.core.encoder.q_objects+dut.core.encoder.q_exceptions+224+dut.core.encoder.q_palettes+dut.core.encoder.admitted_raw*256')
    s=once(s,'   manual_release=1;', '''   if(f==908)begin
    wait(free_done366);
    if(attempts366!=2||missed366||admitted366!=2)$fatal(1,"next capture deadline missed366");
   end
   manual_release=1;''')
    p.write_text(s,newline='\n')


def functional(d,early=False):
    materialize(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'nes_native_frame201 frame(.*);', '''wire source_start365,prelease365,export_permitted365,retire_permitted365,source_owned365,materialized366;
 wire [31:0] source_epoch365,captured_epoch365;wire [15:0] source_generation365,captured_generation365;
 wire plan_commit365;wire [31:0] live_epoch365=32'd1;
 nes_native_capture365 frame(.stop(test_abort),.source_start_ready(start_ready),.source_done(source_done),
  .identity_ready(idready),.display_ack(rack),.flow_error(flow_fault||romfault267),
  .source_start(source_start365),.identity_valid(idvalid),.prelease(prelease365),
  .source_epoch(source_epoch365),.source_generation(source_generation365),.source_serial(serial),
  .source_ready(1'b1),.source_is_rom(1'b1),.source_writing(test_drop),.live_epoch(live_epoch365),
  .export_error(source_fault),.reader_drained(romdrained267),.retire_commit(plan_commit365),.retire_generation(captured_generation365),
  .effective_release(release_frame),.lease_valid(lease_valid),.retire_permitted(retire_permitted365),.export_permitted(export_permitted365),
  .waiting_display(waiting_display),.lease_fault(lease_fault),.captured_epoch(captured_epoch365),.captured_generation(captured_generation365),.*);''')
    s=once(s,'nes_native_capture365 frame(',f'nes_native_capture365 #(.EARLY_RELEASE({int(early)})) frame(.capture_materialized366(materialized366),.source_owned365(source_owned365),')
    s=once(s,'reg enable=0;', 'wire enable=source_start365;')
    s=once(s,'reg [31:0] serial=1;', 'wire [31:0] serial;')
    s=once(s,'reg idvalid=0;', 'wire idvalid;')
    s=once(s,'nes_joint266 dut(', 'nes_joint267_board dut(.capture_materialized366(materialized366),.tile_closed267(),')
    s=once(s,'.frame_owned(owned&&!test_drop),.geometry_valid(geometry_valid)',
           '.frame_owned(source_owned365&&!test_drop),.geometry_valid(source_owned365)')
    s=once(s,'.release_frame(release_frame),.lease_valid', '.release_frame(),.lease_valid')
    s=once(s,'.frame_generation(generation^{15\'d0,test_gen}),.content_epoch(32\'d1)',
           '.frame_generation(source_generation365^{15\'d0,test_gen}),.content_epoch(source_epoch365)')
    s=s.replace('.tile_generation(generation)', '.tile_generation(source_generation365)')
    s=s.replace('.end_generation(generation)', '.end_generation(source_generation365)')
    s=once(s,'tx[3]=generation[7:0];tx[4]=generation[15:8];',
           'tx[3]=source_generation365[7:0];tx[4]=source_generation365[15:8];')
    s=once(s,'nes_plan_rom267 planrom(.prelease361(owned&&geometry_valid&&!test_drop),.epoch361(32\'d1)',
           'nes_plan_path267 planrom(.prelease361(prelease365),.epoch361(source_epoch365)')
    s=once(s,'.clk(clk),.host_clk(host_clk),.mem_clk(mem_clk267),.reset(reset),.stop(test_abort)',
           '.clk(clk),.host_clk(host_clk),.reset(reset),.stop(test_abort||lease_fault)')
    s=once(s,'.lease(waiting_display||flow_retired),.retire_permitted(flow_retired),.generation(generation)',
           '.lease(lease_valid),.retire_permitted(flow_retired&&retire_permitted365),.generation(source_generation365)')
    s=once(s,'.psram_address(psaddr267),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe267),.psram_we(we267),.psram_bhe(bhe267),.psram_ble(ble267),.psram_data(psdata267),',
           '''.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(test_drop),.captured_epoch(source_epoch365),.live_epoch(live_epoch365),
   .retire_commit(plan_commit365),.core_error267(),.core_response_address267(),
   .mem_ready(mem_ready365),.mem_response(mem_response365),.mem_error(mem_error365),.mem_response_address(mem_address365),.mem_data(mem_data365),
   .mem_request(mem_request365),.mem_address(mem_request_address365),''')
    marker='  nes_plan_path267 planrom('
    # Declaration indentation is intentionally independent of old TB formatting.
    marker='nes_plan_path267 planrom('
    a=s.index(marker)
    s=s[:a]+'''wire mem_ready365,mem_response365,mem_error365,mem_request365;
 wire [21:0] mem_address365,mem_request_address365;wire [7:0] mem_data365;
 nes_rom_physical #(.READ_CYCLES(16)) physical365(.clk(clk),.mem_clk(mem_clk267),.reset(reset),
  .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
  .rom_request(mem_request365),.rom_address(mem_request_address365),.rom_ready(mem_ready365),.rom_response(mem_response365),.rom_error(mem_error365),.rom_response_address(mem_address365),.rom_data(mem_data365),
  .psram_address(psaddr267),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe267),.psram_we(we267),.psram_bhe(bhe267),.psram_ble(ble267),.psram_data(psdata267));
 '''+s[a:]
    # Prepare the passive reference/logging before automatic admission can fire.
    a=s.index('   name=$sformatf("frame%0d.expected",f);');z=s.index('   @(negedge clk);enable=1;',a)
    preparation=s[a:z]
    s=s[:a]+s[z:]
    marker='   for(t=7*341+257;t<=232*341+1;t++)begin'
    s=once(s,marker,preparation+marker)
    s=once(s,'''   @(negedge clk);enable=1;
   $fwrite(events261,"start319,%0d,%0t,%0d\\n",f,$time,romcycle267);
   @(negedge clk);enable=0;''', '')
    s=once(s,' initial begin : consumer', ''' always @(posedge clk)if(!reset&&source_start365)
   $fwrite(events261,"start319,%0d,%0t,%0d\\n",f,$time,romcycle267);
  initial begin : consumer''')
    s=once(s,'   wait(idready);@(negedge clk);idvalid=1;@(negedge clk);idvalid=0;', '   wait(!frame.identity_pending);')
    s=once(s,'manual_release=0;serial++;frames++;', 'manual_release=0;frames++;')
    # Input-stage competition is now explicit and independently countable.
    s=once(s,'wire core_req267=active263&&core_ready267&&romcycle267%120==3;',
           'parameter integer CORE_INPUT365=1;\n wire core_req267=(active263||(CORE_INPUT365&&frame.started&&!waiting_display))&&core_ready267&&romcycle267%120==3;')
    s=once(s,' task clear_output;', ''' integer input_core365=0,input_core_reply365=0,last_query_cycle365=0;
 always @(posedge clk)if(!reset)begin
  if(query)last_query_cycle365=romcycle267;
  if(frame.started&&!waiting_display&&core_req267)input_core365++;
  if(frame.started&&!waiting_display&&core_response267)input_core_reply365++;
  if(materialized366)$fwrite(events261,"materialized366,%0d,%0d,%0t\\n",f,romcycle267,$time);
  if(frame.local_source365&&query)$fatal(1,"collector query after local handoff366");
 end
 final $display("CAPTURE365 input_core=%0d replies=%0d last_query=%0d",input_core365,input_core_reply365,last_query_cycle365);
 task clear_output;''')
    a=s.index(' nes_native_capture365 #');z=s.index('.*);',a)+len('.*);')
    instance=s[a:z];s=s[:a]+s[z:]
    s=once(s,'assign selected=main_selected267||plan_selected267;',instance+'\n assign selected=main_selected267||plan_selected267;')
    s=s.replace('planrom.source.cache_path.cache.hit,',
                '(planrom.source.cache_path.cache.state==planrom.source.cache_path.cache.HIT),')
    p.write_text(s,newline='\n')
