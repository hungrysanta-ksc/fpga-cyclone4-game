# SPDX-License-Identifier: MIT
"""Share the compact collector's mutually exclusive previous-row read ports.

Copy cycles use copy_column. BG compare/write cycles use column and are already
rejected while copy_busy. This changes neither event latency nor lease limits.
The selected source remains separate from the immutable original181 evidence.
"""
from nes_reject180 import replace

def compact(s):
    s=replace(s,' reg different,copy_busy,retiring,row_bad,previous_valid;',
        ' reg different,copy_busy,retiring,row_bad,previous_valid;\n'
        ' wire [5:0] previous_address=copy_busy?copy_column:column;\n'
        ' wire [14:0] previous_value=previous[previous_address];')
    s=replace(s,'maps[copy_base+copy_column]<=previous[copy_column];',
                'maps[copy_base+copy_column]<=previous_value;')
    s=replace(s,'previous[0]!=cell_value','previous_value!=cell_value')
    s=replace(s,'previous[column]!=cell_value','previous_value!=cell_value')
    return s
