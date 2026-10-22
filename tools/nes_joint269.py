# SPDX-License-Identifier: MIT
"""Sticky STOP-to-WRAM invalidation handshake on the retained output owner.

6001 bit7 is stopped/faulted, bit6 requires both SNES bank flags to be cleared.
Only a synchronized 6006=A5 write acknowledges invalidation. Packet admission
and internal processing may continue; SNES reads/ACK/consume remain blocked.
This does not merge source and output clock domains.
"""
from nes_joint266 import sources as prior
from nes_delta231 import once


def flow_patch(s):
 s=once(s,' wire rst=reset||cancel;', ''' wire rst=reset||cancel;
 reg invalidate_banks;
 wire status_address=address==24'h006001;''')
 s=once(s,' always @(posedge host_clk or posedge rst)begin', '''
 // Asynchronous assertion survives a short STOP; acknowledgement is local to
 // the existing synchronized SNES write observer, never an unsynchronized bus.
 always @(posedge host_clk or posedge rst)begin
  if(rst)invalidate_banks<=1;
  else if(fault)invalidate_banks<=1;
  else if(write_end&&ap==24'h006006&&dp==8'ha5)invalidate_banks<=0;
 end
 always @(posedge host_clk or posedge rst)begin''')
 s=once(s,'assign ordinary_ready=state==NORMAL&&qr&&!fault&&!rst;', 'assign ordinary_ready=state==NORMAL&&qr&&!fault&&!rst&&!invalidate_banks;')
 s=once(s,"8'h01:control={fault,7'd0};", "8'h01:control={fault||rst,invalidate_banks,6'd0};")
 s=once(s,'assign bus_valid=!rst&&!fault&&!read_n&&write_n&&(', 'assign bus_valid=!read_n&&write_n&&(status_address||(!rst&&!fault&&!invalidate_banks&&(')
 s=once(s,'||!aoe);','||!aoe)));')
 # No stale CPU read/ACK/consume may advance the reset parser. Internal
 # CRC/receipt/source work is not stalled by the host acknowledgement.
 s=s.replace('wire consume_write=', 'wire consume_write=!invalidate_banks&&')
 for token in ['if(state==NORMAL&&rs&&!rp', 'if(rs&&!rp&&display_read)', 'if(rs&&!rp&&ap[23:11]', 'if(write_end)begin']:
  replacement=token.replace('if(', 'if(!invalidate_banks&&',1)
  s=once(s,token,replacement)
 return s


def sources():
 src=prior();src['nes_mux260.sv']=flow_patch(src['nes_mux260.sv']);return src
