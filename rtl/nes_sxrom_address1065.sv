// SXROM connects three MMC1 CHR output pins to the CPU memory address bus.
// CHR RAM itself uses only A0..A12. In 4 KiB mode A12 selects the register
// even during a CPU access. The two registers are allowed to disagree.
module nes_sxrom_address1065(
 input wire chr_4k, ppu_a12,
 input wire [4:0] chr0, chr1,
 input wire [17:0] inner_prg,
 input wire [12:0] cpu_offset,
 output wire [18:0] prg_address,
 output wire [14:0] battery_address
);
 wire [4:0] bank = chr_4k && ppu_a12 ? chr1 : chr0;
 assign prg_address = {bank[4], inner_prg};
 assign battery_address = {bank[3:2], cpu_offset};
endmodule
