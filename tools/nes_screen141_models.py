# SPDX-License-Identifier: MIT
"""Selected141 reader model: digital flights only, with explicit140 negative control."""
from pathlib import Path
import re

def prepare_models(O):
 p=O/'nes_rom_physical.sv';s=p.read_text();s='`timescale 1ns/1ps\n'+s.replace('parameter integer READ_CYCLES=3','parameter integer READ_CYCLES=3, parameter real REQ_DELAY=5.0, ACK_DELAY=16.0, parameter CAPTURE=1')
 s=s.replace('reg [21:0] address_hold;','wire request_flight,ack_flight;assign #(REQ_DELAY) request_flight=request_toggle;assign #(ACK_DELAY) ack_flight=ack_toggle;\n reg [21:0] address_hold;')
 s=s.replace('request_sync[0],request_toggle','request_sync[0],request_flight').replace('ack_sync[0],ack_toggle','ack_sync[0],ack_flight');s=s.replace('if(!owner_check)ack_toggle<=request_sync[1];','if(!owner_check && CAPTURE)ack_toggle<=request_sync[1];').replace('    RELEASE:', '    RELEASE:')
 s=s.replace('    HOLD:begin','    HOLD:begin\n     if(!owner_check && !CAPTURE)ack_toggle<=request_sync[1];')
 p.write_text(s)
 p=O/'rtl/nes.v';s=p.read_text();s=s.replace('module NES(','module NES #(parameter LEGACY_DEADLINE141=0) (')
 assert 'LEGACY_DEADLINE141=0' in s
 s=s.replace('((div_cpu == div_cpu_n - 5\'d1) || cpu_ce)',"((LEGACY_DEADLINE141?cart_ce:(div_cpu == div_cpu_n - 5'd1)) || cpu_ce)");p.write_text(s)
