# SPDX-License-Identifier: MIT
"""Passive native CPU phase markers;identical386 ROM, no timing substitution."""
import probe_nes_burst386 as native

for label in ('ready383','bounds_init386','ranges_done386','dense_compare386',
              'strategy386','convert_done386','columns386','map_job_done383',
              'budget383','budget_done383','flush383'):
 native.LUA+=f"\nemu.addMemoryCallback(function()mark('{label}')end,emu.callbackType.exec,LABELS.{label})\n"
if __name__=='__main__':native.main()
