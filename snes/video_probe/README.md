# Reproduce the SNES WRAM probe

SPDX-License-Identifier: MIT

1. Generate original ROM/data: `python -X utf8 snes/video_probe/build_probe.py --out <fresh-probe-dir>`.
2. Make a private portable copy of a known Mesen build in a local ignored folder:
   executable, its DLLs (except hostfxr.dll), Mesen.deps.json, Mesen.runtimeconfig.json,
   Dependencies.zip. Do not bundle these third-party binaries in this repository.
   The tested build uses existing .NET 8; set DOTNET_ROOT and DOTNET_ROOT_X64 to its
   installed location. This does not require modifying the global installation.
3. In that private copy only, create settings.json with
   `{"Debug":{"ScriptWindow":{"AllowIoOsAccess":true,"ScriptTimeout":10}},"Video":{"VideoFilter":"None","Brightness":0,"Contrast":0,"Hue":0,"Saturation":0}}`.
   Other settings default. Network Lua access remains disabled.
4. `python -X utf8 snes/video_probe/run_probe.py --mesen <portable-Mesen.exe> --probe <probe-dir> --out <fresh-ASCII-capture-dir>`.
   Windows Lua io requires an ASCII output path here. The runner uses absolute
   paths because Mesen changes its working directory to its portable directory.
5. Repeat build with `--diagnostic` and a fresh directory; same visible pixels
   should pass. Repeat with `--fault-split`: a deliberate one-line error must fail
   at source (0,116), with 256 mismatches per captured frame.

The .sfc is entirely original and has no commercial ROM input. It boots from ROM,
copies the host to WRAM, uploads static tiles once in startup forced blank and
replays one HDMA split each frame. It is not an FPGA image or installable NES core.
Two frames are compared over all 256x239 visible pixels; source row 239 is separately
reported as missing. No crop policy is thereby approved for a product.

The RGB LUT is a deterministic diagnostic LUT, not a NES palette selection. Initial
RGB comparison failed because the comparator used arithmetic floor expansion;
Mesen uses bit replication. Corrected comparison retains all original captures.

## Mode1 partial-pixel experiment

`build_patch_probe.py` builds the separate dot_palette case. It preloads Mode1 BG3
2bpp background maps and a sparse BG1 4bpp overlay covering 17 tiles. Four overlay
palettes preserve all source colors. A one-channel HDMA BG3 map switch at line 120
handles the state after the midline change. `--omit-patch` must reproduce 91 bad
pixels, first (123,119). `--diagnostic` repeats the marker-only regression.

This experiment uses 19,520 startup DMA bytes and no steady-state VRAM DMA. The
544-byte patch CHR, 34-byte map delta and 92 used palette bytes are not a measured
streaming budget. Full palette groups take 128 bytes; mode/layer/OBJ interactions
and dynamically changing backgrounds still require their own integration test.
