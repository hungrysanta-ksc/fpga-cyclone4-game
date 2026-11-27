"""Represent verified backdrop rows during PPUMASK=0, when the PPU fetches no map."""
from prepare_nes_kirby1023 import edit


def patch(board):
    edit(board, 'nes_native_raster181.sv',
         (' input wire non_backdrop,',' input wire non_backdrop, output wire blank_no_fetch,'),
         (' assign row_needs_patch=', " assign blank_no_fetch=(line_mask==0 && !row_bad && !non_backdrop);\n assign row_needs_patch="),
         ("display_mask!=8'h10 && ((", "display_mask!=0 && display_mask!=8'h10 && (("))
    edit(board, 'nes_native_frame201.sv',
         (' nes_native_compact181 compact(', ''' wire blank_no_fetch;
 wire [5:0] real_groups;
 // A fully closed screen has no BG fetch. The source ABI requires a group.
 // Its 33 zero words are returned by the compact RAM query below.
 assign group_count=(real_groups==0 ? 6'd1 : real_groups);
 nes_native_compact181 compact(
  .blank_no_fetch(blank_no_fetch),'''),
         ('.exception_count(exception_count),.group_count(group_count)', '.exception_count(exception_count),.group_count(real_groups)'),
         ('.non_backdrop(non_backdrop),\n  .begin_packet', '.non_backdrop(non_backdrop),.blank_no_fetch(blank_no_fetch),\n  .begin_packet'))
    edit(board, 'nes_native_compact181.sv',
         (' input wire row_commit,row_patched,',' input wire blank_no_fetch, row_commit,row_patched,'),
         ('assign row_needs_patch=row_bad || column!=33;', '''wire empty_row=blank_no_fetch && column==0;
 assign row_needs_patch=row_bad || (column!=33 && !empty_row);'''),
         ('(row_patched || selected_group<32)', '(row_patched || empty_row || selected_group<32)'),
         ("<= row_patched ? 16'd0 :", "<= (row_patched || empty_row) ? 16'd0 :"),
         ("read_kind==0?{48'd0,map_q}:", "read_kind==0?{48'd0,(group_count==0?16'd0:map_q)}:"),
         ("0:if(query_address<group_count*11'd33)", "0:if(query_address<(group_count==0?11'd33:group_count*11'd33))"),
         ('previous_valid<=!row_patched;','previous_valid<=!row_patched && !empty_row;'),
         ('if(row_patched)begin\n       // raster descriptor', 'if(row_patched || empty_row)begin\n       // raster descriptor'))
