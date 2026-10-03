// Snapshot E00000..E1FFFF into reserved E20000..E3FFFF, without reset.
// Pause only for PSRAM copy; SD writes happen later against the held image.
module gbc_save_snapshot # (parameter WATCHDOG_BITS=22)(
 input wire clk,reset,run_core,start,input wire[16:0]ram_mask,
 input wire save_write_accepted,save_busy,
 output wire pause_core,output wire[7:0]status,
 output reg[31:0]generation,snapshot_generation,
 output wire req_valid,req_write,output wire[22:0]req_addr,
 output reg[15:0]req_data,input wire req_ready,rsp_valid,input wire[15:0]rsp_data,input wire rtc_enabled,rtc_release,watchdog_tick
);
 reg[2:0]state;reg[5:0]settle;reg[15:0]offset;
 // Loader installs RAM size before RUN and never changes it during a snapshot.
 wire[15:0]last_word=ram_mask[16:1];
 reg valid,error;reg[1:0]watchdog;
 assign pause_core=state!=0;
 assign status={5'b10101,error,valid,(state!=0&&state!=6)};
 assign req_valid=(state==2||state==4);
 assign req_write=(state==4);
 assign req_addr={7'b1110000,offset}+(state==4?23'h010000:23'b0);
 always @(posedge clk)begin
  if(reset)begin state<=0;settle<=0;offset<=0;valid<=0;error<=0;watchdog<=0;generation<=0;snapshot_generation<=0;req_data<=0;end
  else begin
   if(run_core&&save_write_accepted)generation<=generation+1'b1;
   if(state!=0&&watchdog_tick)watchdog<={watchdog[0],1'b1};
   if(!run_core)begin state<=0;valid<=0;end
   else if(state!=0&&watchdog_tick&&(&watchdog))begin state<=0;valid<=0;error<=1;end
   else case(state)
    0:if(start)begin
     valid<=0;error<=0;
     if(ram_mask!=0||rtc_enabled)begin state<=1;settle<=0;offset<=0;watchdog<=0;end
     else error<=1;
    end
    1:if(settle!=63)settle<=settle+1'b1;
      else if(!save_busy&&!save_write_accepted)begin snapshot_generation<=generation;state<=ram_mask==0?6:2;if(ram_mask==0)valid<=1;end
    2:if(req_ready)state<=3;
    3:if(rsp_valid)begin req_data<=rsp_data;state<=4;end
    4:if(req_ready)state<=5;
    5:if(rsp_valid)begin
     if(offset==last_word)begin state<=rtc_enabled?6:0;valid<=1;end
     else begin offset<=offset+1'b1;state<=2;end
    end
    6:if(rtc_release)state<=0;
    default:begin state<=0;error<=1;valid<=0;end
   endcase
  end
 end
endmodule
