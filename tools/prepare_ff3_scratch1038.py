"""Use spare map RAM addresses for the FF3 capture's 33-cell comparison row."""
from pathlib import Path


def share_map_scratch(board: Path):
    p = board / "nes_native_compact181.sv"
    s = p.read_text()
    edits = {
        '(* ramstyle="M9K" *) reg [15:0] maps[0:1055]': '(* ramstyle="M9K", max_depth=512 *) reg [15:0] maps[0:1503]',
        " reg [15:0] previous[0:32];": " localparam [10:0] SCRATCH=11'd1088;",
        " wire [5:0] previous_address=copy_busy?copy_column:column;\n wire [15:0] previous_value=previous[previous_address];": "",
        "  map_q<=maps[query_address];row_q<=": "  map_q<=maps[owned ? query_address : SCRATCH+next_column];row_q<=",
        "    maps[copy_base+copy_column]<=previous_value;": "",
        "      previous[column]<=cell_value;": "",
        " reg [1:0] read_kind;": """ reg [1:0] read_kind;
 wire [15:0] previous_value=map_q;
 wire write_cell=accept && !invalid_extension && row<224 && !obj &&
                 row==row_count && position<=32 && attribute<=3 && rank==0 &&
                 !copy_busy && position==column && !row_bad;
 // Register the next read address with the operation that advances the cursor.
 // A changed row starts its copy at zero on the edge that commits the row.
 wire commit_row=active && row_commit && committed_row==row_count &&
                 row_count<224 && !copy_busy && !event_valid;
 wire [5:0] next_column=(reset || release_scene || starting || commit_row) ? 6'd0 :
                        copy_busy ? (copy_column==32 ? column : copy_column+6'd1) :
                        write_cell ? column+6'd1 : column;
 always @(posedge clk) if(!reset && !release_scene && (copy_busy || write_cell))
   maps[copy_busy ? copy_base+copy_column : SCRATCH+column] <= copy_busy ? previous_value : cell_value;""",
    }
    for before, after in edits.items():
        if s.count(before) != 1:
            raise ValueError(before)
        s = s.replace(before, after)
    # The row descriptor is written only on a valid row commit. That edge
    # explicitly excludes both an incoming cell and an in-progress copy.
    s = s.replace(' (* ramstyle="M9K" *) reg [7:0] rows[0:223];', " localparam [10:0] ROWS=11'd1280;")
    s = s.replace("map_q<=maps[owned ? query_address : SCRATCH+next_column];row_q<=rows[query_address[7:0]];",
                  "map_q<=maps[owned ? (query_kind==1 ? ROWS+query_address[7:0] : query_address) : SCRATCH+next_column];")
    s = s.replace("read_kind==1?{56'd0,row_q}", "read_kind==1?{56'd0,map_q[7:0]}")
    s = s.replace("reg [7:0] row_q;", "")
    s = s.replace("rows[row_count]<=0;", "")
    s = s.replace("rows[row_count]<={selected_group[4:0],row_fine};", "")
    s = s.replace("if(!reset && !release_scene && (copy_busy || write_cell))",
                  "if(!reset && !release_scene && commit_row && (row_patched || selected_group<32))"
                  "\n   maps[ROWS+row_count] <= row_patched ? 16'd0 : {8'd0,selected_group[4:0],row_fine};"
                  "\n else if(!reset && !release_scene && (copy_busy || write_cell))")
    assert "rows[" not in s and "row_q" not in s
    # While capturing, the object table's query port is free. Read the
    # previous fragment as the fetcher registers the next event's rank.
    s=s.replace("module nes_native_compact181(", "module nes_native_compact181(input wire [2:0] next_rank,")
    s=s.replace("reg [38:0] rank_key[0:7];reg [7:0] rank_mask[0:7],rank_row[0:7];",
                "reg [7:0] rank_row[0:7];")
    s=s.replace(" wire same_object=", """ reg [63:0] object_q;
 reg forward_object;
 reg [38:0] last_key;
 reg [7:0] last_mask;
 wire [38:0] prior_key=forward_object ? last_key : {object_q[49],object_q[37:0]};
 wire [7:0] prior_mask=forward_object ? last_mask : object_q[45:38];
 wire same_object=""").replace("rank_key[rank]==key","prior_key==key").replace("same_object?rank_mask[rank]","same_object?prior_mask")
    s=s.replace("reg [15:0] map_q;reg [63:0] object_q;", "reg [15:0] map_q;")
    s=s.replace("object_q<=objects[query_address[6:0]];", "object_q<=objects[owned ? query_address[6:0] : rank_slot[next_rank]];")
    s=s.replace("response<=0;hit<=0;", "response<=0;hit<=0;forward_object<=0;")
    s=s.replace("rank_key[rank]<=key;rank_mask[rank]<=mask;", """if(rank==next_rank)begin
        forward_object<=1;last_key<=key;last_mask<=mask;
       end
       """)
    assert "rank_key[" not in s and "rank_mask[" not in s and s.count("reg [63:0] object_q;")==1
    p.write_text(s)
    p=board/"nes_native_planes165.sv"
    s=p.read_text().replace("output reg event_valid,", "output wire [2:0] next_rank,output reg event_valid,")
    s=s.replace(" wire [63:0] description=", " assign next_rank=rank;\n wire [63:0] description=")
    p.write_text(s)
    p=board/"nes_native_frame201.sv"
    s=p.read_text().replace("nes_native_planes165 ", "wire [2:0] next_rank;\n nes_native_planes165 ",1)
    s=s.replace(".event_valid(fetch_event)", ".next_rank(next_rank),.event_valid(fetch_event)")
    assert s.count(".next_rank(next_rank)")==2
    p.write_text(s)
