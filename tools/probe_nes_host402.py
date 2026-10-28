# SPDX-License-Identifier: MIT
"""Fixed host with400 physical SPI/read-end and independent checker guards."""
import probe_nes_joint396_rtl as old

def test402():
 s=old.test396().replace('[113:0]','[153:0]')
 s=s.replace('nes_output260 flow(',"nes_output260 flow(.tag_write400(1'b0),.tag_at400(4'd0),.tag_data400(8'd0),.hint_metaactive398(1'b0),.hint_meta_at398(4'd0),")
 return s

s=old.s.replace("'nes_stage396.sv','nes_check396.sv'","'nes_stage396.sv','nes_check396.sv','nes_read_owner400.sv'")
ns=dict(old.ns,test396=test402);exec(compile(s,'host402-rtl','exec'),ns)
if __name__=='__main__':ns['main']()
