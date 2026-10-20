// Replacement ordinary reference executor, in the existing host FSM.
// cursor/first/count/length/header16..20 are the retired map context.
// The original descriptor remains the only DMA and receipt address source.
     RNEXT:begin
      if(header[1]==5&&header[0]!=15&&header[0]!=13&&
         (header[0]==2||header[0]==4||header[0]==5||header[0]==8)&&
         opos<oend&&opos>=scroll_length&&opos<1121)opos<=oend<1121?oend:12'd1121;
      else if(header[1]==5&&prelude_raw==0&&opos>=3169&&opos<oend)opos<=oend;
      else if(cursor==wire_length275)begin
       if(opos!=oend||rle_left!=0||rle_zero||
          (header[0]==3&&manifest_phase!=2))failed<=1;
       else state<=ORET;
      end else if(cursor>wire_length275||!inline275)failed<=1;
      else begin at<=0;parser_address<=cursor[7:0];state<=RREAD;end
     end
     RREAD:state<=RCAP;
     RCAP:begin
      cursor<=cursor+1'b1;parser_address<=parser_address+1'b1;
      if(at==0)begin
       header[20]<=qdata;
       if(qdata==1||qdata==9||qdata==10||qdata==11||qdata==12||qdata==4||qdata==6)
        begin at<=1;state<=RREAD;end
       else failed<=1;
      end else begin
       header[15+at]<=qdata;
       if((header[20]==1||header[20]==9)?at==3:
          (header[20]==10||header[20]==11)?at==2:at==1)state<=RDECODE;
       else begin at<=at+1'b1;state<=RREAD;end
      end
      if(cursor>=wire_length275)failed<=1;
     end
     RDECODE:begin
      case(header[20])
       1:begin
        // A range must exactly continue this consumed DMA descriptor.
        if(rle_zero||header[18]==0||header[18]>16||header[17]>5||
           (header[0]!=7&&header[0]!=2&&header[0]!=4&&header[0]!=5&&header[0]!=8))failed<=1;
        else if(header[0]==7)begin
         if({header[17],header[16]}!=opos||opos+header[18]>oend)failed<=1;
         else begin opos<=opos+header[18];event264(1,{header[18][5:0],opos},3'd0);end
        end else if(header[1]==3)begin
         if(opos[3:0]||oend[3:0]||{header[17],header[16]}!=1152+(opos>>4)||
            opos+({8'd0,header[18]}<<4)>oend)failed<=1;
         else begin opos<=opos+({4'd0,header[18]}<<4);
          event264(1,{header[18][5:0],(12'd1152+(opos>>4))},3'd0);end
        end else if(header[1]==5&&opos>=1121&&opos<3169)begin
         if(boff[3:0]||{header[17],header[16]}!=1184+(boff>>4)||
            opos+({8'd0,header[18]}<<4)>oend||opos+({8'd0,header[18]}<<4)>3169)failed<=1;
         else begin opos<=opos+({4'd0,header[18]}<<4);
          event264(1,{header[18][5:0],(12'd1184+(boff>>4))},3'd0);end
        end else failed<=1;
       end
       4:begin
        if(header[0]==3)begin
         if(opos==0&&header[16]==3)begin opos<=1;event264(4,18'd3,3'd0);end
         else if(opos==1&&header[16]==2)begin opos<=2;event264(4,18'd2,3'd0);end
         else failed<=1;
        end else if(header[1]!=5||rle_zero||
          (header[0]!=2&&header[0]!=4&&header[0]!=5&&header[0]!=8))failed<=1;
        else if(opos==0&&scroll_length!=0&&header[16]==1)begin
         rle_zero<=1;event264(4,18'd1,3'd0);
        end else if(opos>=3169&&opos<oend&&prelude_raw!=0&&hoff[3:0]==0&&
          header[16]=={2'd0,hoff[7:4],2'd0})begin
         rle_zero<=1;event264(4,{12'd0,hoff[7:4],2'd0},3'd0);
        end else failed<=1;
       end
       6:begin
        if(header[0]!=3||opos!=2||header[16]!=1)failed<=1;
        else begin opos<=3;manifest_phase<=2;event264(6,18'd1,3'd0);end
       end
       9:begin
        if(!rle_zero||!header[16]||header[1]!=5||
           opos+header[16]>oend||
           (opos<scroll_length?opos+header[16]>scroll_length:
            (opos<3169||hoff[3:0]+{1'b0,header[16]}>16))||
           header[17]!=16+(header[0]==2?(opos-startpos):0)||
           header[18]!=(header[0]==2?0:header[0]==8?
             (((opos-startpos)&3)<<4)|4:(((opos-startpos)&1)<<4)|2))failed<=1;
        else begin rle_left<=header[16];state<=RDATA;end
       end
       10,11,12:begin
        if(!header[16])failed<=1;
        else if(header[0]==15)begin
         if((opos<40?(header[20]!=11||opos+header[16]>40):
              (header[20]!=10||opos+header[16]>206))||header[17]!=opos)failed<=1;
         else begin rle_left<=header[16];state<=RDATA;end
        end else if(header[0]==10)begin
         if(header[20]!=10||header[17]!=opos||opos+header[16]>oend||
            manifest_at+header[16]>256)failed<=1;
         else begin rle_left<=header[16];state<=RDATA;end
        end else if(header[0]==11)begin
         if(header[20]==11||opos>=oend||manifest_at+header[16]>256)failed<=1;
         else begin parser_address<=opos[7:0];state<=RTAGREAD;end
        end else failed<=1;
       end
       default:failed<=1;
      endcase
     end
     RTAGREAD:state<=RTAGCAP;
     RTAGCAP:begin
      if(opos==16)begin
       if(qdata!=3)failed<=1;
       else begin opos<=17;parser_address<=17;state<=RTAGREAD;end
      end else if(header[16]!={1'b0,qdata[6:0]}+1'b1||
         (qdata[7]?header[20]!=12:
          (header[20]!=10||header[17]!=opos+1||opos+1+header[16]>oend)))failed<=1;
      else begin opos<=opos+1'b1;rle_left<=header[16];state<=RDATA;end
     end
     RDATA:begin
      if(header[20]==12)begin
       manifest_at<=manifest_at+1'b1;rle_left<=rle_left-1'b1;
       event264(3,18'd0,3'd1);
      end else begin
       parser_address<=header[20]==9?
        16+(header[0]==2?(opos-startpos):header[0]==8?((opos-startpos)&3):((opos-startpos)&1)):opos[7:0];
       state<=PREAD;
      end
     end
     RADVANCE:begin
      if(rle_left!=0)state<=RDATA;
      else begin
       if(header[20]==9&&(opos==scroll_length||opos==oend||(opos>=3169&&(opos-3169)%16==0)))rle_zero<=0;
       state<=RNEXT;
      end
     end
