# SPDX-License-Identifier: MIT
import probe_nes_joint398_rtl as old
test=old.test398
def fixed_test():
 s=test().replace("flow(.hint_metaactive398(","flow(.tag_write400(1'b0),.tag_at400(4'd0),.tag_data400(8'd0),.hint_metaactive398(")
 for a,b in [('queue.event_count','queue.count270'),('queue.event_valid','queue.link270[110]'),('queue.event_end','queue.link270[112]'),('queue.event_value','queue.incoming'),('flow.queue.event_flags',"8'd0")]:s=s.replace(a,b)
 return s
old.ns['test398']=fixed_test
# The inherited driver resolves its function in this generated namespace.
old.ns['main'].__globals__['test398']=fixed_test
sources=old.ns['main'].__globals__
s=old.s.replace("'nes_byte398.sv'","'nes_byte398.sv','nes_read_owner400.sv'")
exec(compile(s,'fixed400-rtl','exec'),sources)
if __name__=='__main__':sources['main']()
