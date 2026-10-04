// Only delay cold startup. Once armed, the handheld runs continuously even
// when capture_active falls between frames or after an error. Never pause
// the CPU per frame or silently discard pixels to hide an overrun.
module gbc_capture_start_guard(
 input wire clk,reset,run_core,capture_armed,
 output wire core_reset
);
 reg started;
 always @(posedge clk)begin
  if(reset||!run_core)started<=0;
  else if(capture_armed)started<=1;
 end
 assign core_reset=reset||!run_core||!started;
endmodule
