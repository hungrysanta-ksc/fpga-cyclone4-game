# SPDX-License-Identifier: MIT
"""Fixed transaction400 protocol and tag RAM tests; no IRQ interpreter owner."""
import probe_nes_hint398 as old
from nes_fixed400 import TAG_PORTS
old.TB=old.TB.replace('reg response=0,hold_response=0,late_response=0;', 'reg response=0,hold_response=0,late_response=0;wire tag_write400;wire[3:0]tag_at400;wire[7:0]tag_data400;wire tag_ready400=1;')
old.TB=old.TB.replace('hint(.host_clk(', 'hint('+TAG_PORTS+'.host_clk(')
old.TB=old.TB.replace('queue.event_count','queue.count270')
old.TB=old.TB.replace(".read_at(10'd800+ma),.meta_write(mv&&mw&&ma<224&&!mseen&&!rst&&!failed),.meta_data(md)",".read_at(tag_write400?10'd928+tag_at400:10'd800+ma),.meta_write(!rst&&(tag_write400||mv&&mw&&ma<224&&!mseen&&!failed)),.meta_data(tag_write400?tag_data400:md)")
if __name__=='__main__':old.main()
