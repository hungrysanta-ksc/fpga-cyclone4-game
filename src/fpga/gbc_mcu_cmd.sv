// MCU commands used by the dedicated GBC loader and runtime SaveRAM path.
// Omits legacy SGB/MSU/cheat/RTC engines that the board shell never connects.
module gbc_mcu_cmd(
 input wire clk,cmd_ready,param_ready,input wire[7:0]cmd_data,param_data,
 input wire[31:0]byte_count,input wire ready,input wire[7:0]read_data,
 output reg read_request,write_request,output reg[7:0]write_data,spi_data,
 output reg[23:0]address,rom_mask,output reg[15:0]features,output reg[16:0]ram_mask,output reg[3:0]mapper
);
 reg ready_previous=1;reg[7:0]feature_high=0;
 initial begin
  read_request=0;write_request=0;write_data=0;spi_data=0;
  address=0;rom_mask=24'hffffff;features=0;ram_mask=0;mapper=5;
 end
 always @(posedge clk)begin
  ready_previous<=ready;read_request<=0;write_request<=0;
  if(!ready_previous&&ready)begin
   if(cmd_data[7:4]==4'h8)spi_data<=read_data;
   if((cmd_data[7:4]==4'h8||cmd_data[7:4]==4'h9)&&cmd_data[3])address<=address+1'b1;
  end
  if(cmd_ready)begin
   // Existing firmware sends the mapper in a command-only 0x3x packet.
   if(cmd_data[7:4]==4'h3)mapper<=cmd_data[3:0];
   spi_data<=cmd_data==8'hf0 ? 8'ha5 : 8'h00;
   if(cmd_data[7:4]==4'h8)read_request<=1;
  end
  if(param_ready)begin
   case(cmd_data)
    8'h00:case(byte_count)
     2:address[23:16]<=param_data;3:address[15:8]<=param_data;4:address[7:0]<=param_data;
    endcase
    8'h10:case(byte_count)
     2:rom_mask[23:16]<=param_data;3:rom_mask[15:8]<=param_data;4:rom_mask[7:0]<=param_data;
    endcase
    8'h20:case(byte_count)
     2:ram_mask[16]<=param_data[0];3:ram_mask[15:8]<=param_data;4:ram_mask[7:0]<=param_data;
    endcase
    8'hef:case(byte_count)
     2:feature_high<=param_data;3:features<={feature_high,param_data};
    endcase
    default:begin
     if(cmd_data[7:4]==4'h9)begin write_data<=param_data;write_request<=1;end
     if(cmd_data[7:4]==4'h8)read_request<=1;
    end
   endcase
  end
 end
endmodule
