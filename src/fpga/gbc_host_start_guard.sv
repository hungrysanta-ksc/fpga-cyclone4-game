// G7: producer may start only after the SNES renderer has reached its first
// upload transaction. host_boundary is ALREADY in clk's domain, from the
// existing upload_boundary_cdc request handshake. Never pause between frames.
module gbc_host_start_guard(
 input wire clk,reset,run_core,capture_armed,host_boundary,
 output wire core_reset
);
 reg host_seen;
 always @(posedge clk)begin
  if(reset||!run_core)host_seen<=0;
  else if(host_boundary)host_seen<=1;
 end
 gbc_capture_start_guard capture_guard(clk,reset,run_core&&host_seen,capture_armed,core_reset);
endmodule
