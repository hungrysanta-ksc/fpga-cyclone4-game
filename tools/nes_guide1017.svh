 // Capture a bounded prefix of validated OBJ records. Overflow drops advice only.
 // This cursor never stalls the exporter or replaces a resident row.
 reg [20:0] guide_words[0:31];
 reg [5:0] guide_written,guide_read;
 reg [12:0] guide_key;
 reg [7:0] guide_rows;
 reg [2:0] guide_lane;
 reg guide_checked,guide_closed;
 wire guide_stop=hint||plan963||page963;
 wire guide_open=live&&!guide_closed&&!guide_stop;
 wire guide_slot=guide_open && guide_rows[0] && !todo && !pending952 && !early963 &&
                 !demand && !hit_reply && !spec_owner && !reply;
 wire [21:0] guide_address={5'h10,guide_key,1'b0,guide_lane};
 wire guide_probe=guide_slot&&!guide_checked;
 wire guide_request=guide_slot&&guide_checked&&!lookup[WIDTH-1];
 always @(posedge clk)begin
  guide_checked<=guide_probe||(guide_request&&!grant_ready);
  if(!live)begin
   guide_written<=0;guide_read<=0;guide_rows<=0;guide_checked<=0;guide_closed<=0;
  end else if(guide_stop)begin
   guide_closed<=1;guide_checked<=0;guide_rows<=0;
  end else if(guide_open)begin
   if(guide_record&&guide_mask!=0&&!guide_written[5])begin
    guide_words[guide_written[4:0]]<={guide_tag,guide_mask};
    guide_written<=guide_written+1'b1;
   end
   if(!guide_rows)begin
    if(guide_read<guide_written)begin
     {guide_key,guide_rows}<=guide_words[guide_read[4:0]];
     guide_read<=guide_read+1'b1;guide_lane<=0;
    end
   end else if(!guide_rows[0]||(guide_slot&&guide_checked&&(lookup[WIDTH-1]||grant_ready)))begin
    guide_rows<=guide_rows>>1;guide_lane<=guide_lane+1'b1;
   end
  end
 end
