reg [7:0] low_plane1065;
reg [38:0] expected_key[0:1791];
bit used_row[0:1791], matched_row[0:1791];
integer accepted_titles=0, rejected_titles=0;
wire [63:0] desc1065=collector.fetch.description;
always @(posedge clk)begin
 if(collector.fetch.begin_frame)
   for(int i=0;i<1792;i++)begin used_row[i]=0; matched_row[i]=0; end
 if(collector.fetch.mark_high && desc1065[49])begin
   int row,rank,fine,top,idx;
   row=desc1065[32:25];rank=desc1065[52:50];fine=desc1065[15:13];
   top=(row-(desc1065[48]?7-fine:fine))&511;idx=row*8+rank;
   // Independent observation at the two actual PPU loads.
   used_row[idx]=|pq || low_plane1065!=0;
   expected_key[idx]={desc1065[63],desc1065[48:41],desc1065[40:33],top[8:0],desc1065[12:0]};
 end
 if(ce && core.native_obj_low) low_plane1065<=pq;
 if(captured && field1060>=19 && valid_capture)begin
   for(int i=0;i<collector.object_count;i++)begin
     reg [63:0] obj;
     obj=collector.compact.objects[i];
     for(int fine=0;fine<8;fine++)if(obj[38+fine])begin
       int row,idx;
       row=(obj[21:13]+(obj[37]?7-fine:fine))&511;
       idx=row*8+obj[48:46];
       if(row>=224 || !used_row[idx] || matched_row[idx] || {obj[49],obj[37:0]}!==expected_key[idx])
         $fatal(1,"OBJ row mismatch field=%0d row=%0d rank=%0d",field1060,row,obj[48:46]);
       matched_row[idx]=1;
     end
   end
   for(int i=0;i<1792;i++)if(matched_row[i]!=used_row[i])$fatal(1,"missing OBJ row %0d",i);
   accepted_titles++;
 end
 if(captured && field1060>=19 && !valid_capture)rejected_titles++;
end
