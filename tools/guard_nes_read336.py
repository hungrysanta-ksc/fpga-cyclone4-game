# SPDX-License-Identifier: MIT
import inspect
import guard_nes_execute332 as previous


if __name__=='__main__':
    previous.base.old.CASES.update({17:'STOP during private receipt RMW',18:'wrong token after all private reads',19:'missing qualified response at read end',20:'STOP during raw CRC job',21:'duplicate map unit',22:'coverage domain overflow',23:'final scan before publication'})
    original=previous.base.old.once
    def once336(s,a,b):
        if a=='endmodule':
            b=b.replace('  else $fatal(1,"unknown guard319");', '''  else if(NEG319==17)wait(dut.core.validator.state==dut.core.validator.V_PREAD);
  else if(NEG319==18)wait(dut.flow.state==dut.flow.DMA&&dut.flow.read_count==dut.flow.chunk_length&&dut.flow.read_count!=0);
  else if(NEG319==19)wait(dut.flow.read_pending336&&!dut.flow.rs);
  else if(NEG319==20)wait(dut.core.validator.state==dut.core.validator.H_WRITELO);
  else if(NEG319==21)wait(dut.core.validator.v_map_end!=0);
  else if(NEG319==22)wait(dut.flow.ordinary_range);
  else if(NEG319==23)wait(dut.flow.state==dut.flow.DMA&&dut.flow.chunk_ready&&v_ready);
  else $fatal(1,"unknown guard319");''')
            b=b.replace('||NEG319==13)begin', '||NEG319==13||NEG319==17||NEG319==20)begin')
            b=b.replace('  else if(NEG319==9)begin', '''  else if(NEG319==18)begin
   disable bus263;bus_read=1;bus_write=1;wait(dut.flow.tap_idle278);token261(dut.flow.chunk_token^1);
   wr261(dut.flow.data_command278?24'h006059:24'h006050,8'ha5);
  end else if(NEG319==19)begin
   disable bus263;bus_read=1;bus_write=1;force dut.flow.read_pending336=0;
  end
  else if(NEG319==21)begin disable bus263;bus_read=1;bus_write=1;force dut.flow.unit336=0;force dut.flow.range_valid=1;end
  else if(NEG319==22)begin disable bus263;bus_read=1;bus_write=1;force dut.flow.unit336=4095;force dut.flow.ordinary_range=1;end
  else if(NEG319==23)begin disable bus263;bus_read=1;bus_write=1;force dut.flow.ordinary_finish=1;end
  else if(NEG319==9)begin''')
        return original(s,a,b)
    previous.base.old.once=once336
    s=inspect.getsource(previous.main).replace('probe_nes_execute332.py','probe_nes_read336.py').replace('check_nes_final332.py','check_nes_final336.py')
    ns=dict(previous.__dict__);exec(compile(s,'guards336','exec'),ns);ns['main']()
