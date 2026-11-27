"""Use the private headroom of each FF3 sprite fragment for its last row."""
from pathlib import Path


def pack_rank_row(board: Path):
    path = board / "nes_native_compact181.sv"
    text = path.read_text()
    edits = (
        (" reg [7:0] rank_row[0:7];", " reg [7:0] forwarded_row;"),
        ("row<=rank_row[rank]", "row<=(forward_object ? forwarded_row : object_q[57:50])"),
        ("forward_object<=1;last_key<=key;", "forward_object<=1;forwarded_row<=row;last_key<=key;"),
        ("rank_row[rank]<=row;rank_valid[rank]<=1;", "rank_valid[rank]<=1;"),
        ("read_kind==2?object_q:", "read_kind==2?{14'd0,object_q[49:0]}:"),
    )
    for old, new in edits:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    fragment = "{14'd0,key[38],rank,mask,key[37:0]}"
    assert text.count(fragment) == 2
    path.write_text(text.replace(fragment, "{6'd0,row,key[38],rank,mask,key[37:0]}"))
