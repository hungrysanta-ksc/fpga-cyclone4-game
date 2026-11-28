integer changes=0, first_error_count=0;
reg [7:0] old_fetch_errors=0;
always @(posedge clk) if(measuring1060)begin
 old_fetch_errors<=collector.fetch_errors;
 if(collector.fetch_errors!=0 && collector.fetch_errors!=old_fetch_errors && first_error_count<16)begin
  first_error_count++;
  $display("FETCH_ERROR field=%d y=%d x=%d new=%h lo=%b hi=%b read=%b valid=%b chr=%h mapped=%h",field1060,line_no,dot,collector.fetch_errors,core.native_bg_low,core.native_bg_high,pr,init_done && pa[21:13]==9'h100,core.native_chr_logical,pa);
 end
end
reg [63:0] colors=0;
reg [7:0] mask_sample;
always @(posedge clk) begin
 if(captured && measuring1060)begin
  $display("TITLE %d valid=%b errors=%h patch=%h count=%d groups=%d objects=%d colors=%h mask=%h chrwrites=%d", field1060,valid_capture,errors,collector.patch_errors,collector.patch_count,collector.real_groups,collector.object_count,colors,mask_sample,changes);
  colors<=0;changes<=0;
 end
 if(measuring1060 && ce && line_no>=8 && line_no<232 && dot>=2 && dot<=257)begin colors[color]<=1;mask_sample<=core.native_display_mask;end
 if(measuring1060 && mem.chr_changed && line_no>=7 && line_no<232)changes<=changes+1;
end
initial begin
 core.core.ppu.spriteeval.eval_count=0;
 fd=$fopen("prg.bin","rb");n=$fread(prg,fd);$fclose(fd);if(n!=$size(prg))$fatal;
 repeat(8)@(negedge clk);reset=0;wait(init_done);measuring1060=1;
 wait(field1060==32);$display("PASS opening capture trace");$finish;
end
