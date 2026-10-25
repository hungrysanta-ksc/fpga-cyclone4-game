# SPDX-License-Identifier: MIT
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('check_nes_final359.py');s=p.read_text()
 marker=' # Preserve the eight established'
 extra=''' s=s.replace('nes_validator278 dut(', "wire [23:0] args362;wire [15:0] result362;\\n function automatic [15:0] crc362(input [23:0] a);reg [15:0] c;begin c=a[23:8]^{a[7:0],8'd0};for(integer j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction\\n assign result362=crc362(args362);\\n nes_validator278 dut(.crc_args362(args362),.crc_shared362(result362),")
'''
 s=s.replace(marker,extra+marker);exec(compile(s,'final362','exec'),dict(__name__='__main__',__file__=__file__))
