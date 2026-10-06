# NES P1 synthetic fixtures

SPDX-License-Identifier: MIT

Run `python -X utf8 tools/video_schedule_model.py --out <new-local-directory>`.
The generator owns all patterns and accepts no ROM input. Its ten scenes cover
scroll 0/1/255/256, split y=117, all eight CHR windows, generation replacement,
palette/emphasis/greyscale, x=123 palette write, 8x8/8x16 sprite selection,
priority, left mask and game blank. Exact 256x240 reference is always retained.

A is an analytic synthetic renderer, not the MiSTer PPU. B decodes planar CHR
and resolved tile runs, including first-eight-per-line sprite decisions.
The line-only/native-sprite comparison is a deliberately restricted software
candidate, not a SNES PPU emulator. C requires the separate WRAM host experiment.

Resolved runs can be large: zero A/B differences do not imply a feasible wire
format. Cold CHR counts, hypothetical patch cost and example DMA loads are
reported separately. No game measurement or worst-case SMB3 bound is asserted.

The CLI uses a fresh output directory, preserving failed runs. Output JSON
contains full packets and exact first differing coordinates. Negative tests
cover delayed consumer, stale ack/reset epoch, owner/order errors, overflow,
invalid events and stale CHR generation. Diagnostic on/off is budgeted separately.
