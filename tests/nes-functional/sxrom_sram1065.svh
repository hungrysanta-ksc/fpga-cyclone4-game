wire [18:0] sx_addr;
tri [7:0] sx_data;
wire sx_oe,sx_we;
reg [7:0] sx_memory[0:32767];
assign sx_data=(!sx_oe && sx_we)?sx_memory[sx_addr[14:0]]:8'bz;
always @(posedge clk) if(!sx_we)begin
 if(!sx_oe || sx_addr[18:15]!==4'hf || $isunknown(sx_data))$fatal(1,"invalid SRAM write");
 sx_memory[sx_addr[14:0]]=sx_data;
end
function automatic logic [7:0] sx_pattern(input int addr);
 return 8'(addr^(addr>>7)^(addr>>13));
endfunction
