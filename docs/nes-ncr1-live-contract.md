#047 actual PPU binding contract

Candidate: `NES-R2-NCR1-LIVE-047`. Hardware baseline remains044.

## Causal path

The privately adapted014 CPU/PPU/MMC3 core runs the original021 `banks32` and `fine_x` ROMs anew.047 exports registered PPU/mapper state through explicit module ports, then connects `nes_ncr1_ppu_tap` → unchanged046 encoder → unchanged045 reader →044 transport. The input is neither a saved fetch trace nor a precomputed packet. Consumer output bytes are independently decoded against actual PPU output pixels after simulation.

All tap/encoder/producer signals use the NES master clock, nominal21.477MHz. Host transport uses a separate84MHz clock with1.1ns initial phase. `tap_ce` qualifies the PPU observations; no new CDC is introduced between core and encoder. Neither transport readiness nor encoder ownership drives the NES clock, pause input, or frame timing.

The testbench arms at60ms and takes four consecutive complete frames. A frame starts at pre-render line511/cycle1 and ends at line240/cycle1. Raw BG plane data are sampled at the actual BgPainter latch enable, cycles6/8…254/256 and326/328/334/336. They become NCR1 dot5/7…253/255 and325/327/333/335. VBlank and sprite slots are excluded. Physical CHR addresses are taken AFTER MMC3 mapping; each observed byte is also checked against actual PPU `vram_din`. Original012/014 CPU corrections are preserved.

## Explicit restrictions

- NTSC, standard MMC3,64KiB original PRG ROM, immutable16 or32KiB CHR ROM. PRG/CHR address masks must actually be applied by the local cart adapter; setting unused wrapper mask inputs alone is insufficient. This is a diagnostic ROM geometry, not a general loader.
- BG enabled, sprites disabled, BG pattern table0, left BG pixels enabled, grayscale/emphasis disabled, temporary scroll register0. Fine X is read from actual state, latched per frame, and may not change while captured. Positive execution covers fineX0 and1.
- All four actual BG palette groups must contain exactly NES colors15/33/48/22. This condition permits canonicalizing actual attribute0..3 to NCR1 group0. It does not support arbitrary palette groups. The fixed SNES palette equals the existing reference conversion only after that actual-state check. The attribute tap remains recorded and checked for unknowns in simulation; synthesis can eliminate its zeroed canonical output.
- Any active-frame PPU write to2000/2001/2005/2006/2007 or read of2007, any MMC3 write in8000..BFFF, or a CHR-memory write invalidates the frame. C000..FFFF IRQ controls are allowed because they do not change CHR mapping. Active unsupported mask/scroll/palette state also invalidates it. Unrelated PRG-register writes in8000..BFFF are conservatively rejected.
- Frame boundary, full raw cadence, tile row/plane stability and one16KiB CHR window per frame are still checked by046. Tap errors01(mode),02(active change),03(memory-address/read mismatch) are sticky until common reset;046 refuses incomplete/unsupported publication.
- The image is captured into046's single990-cell RAM. It cannot be overwritten until045 completes ownership. An incoming frame with no free source buffer is an error; frames are not silently dropped or delayed. The tap cycles diagnostic frame IDs1..4.046's sequence exhaustion and32-bit tick rollover limitations remain.
- The running core is assumed to continue generating PPU timing; no independent stalled-core/frame watchdog is added here. The testbench has a watchdog. Physical CHR immutability, loader identity and bounded external ROM response are still integration responsibilities.

## Memory, consumer and resource limits

Simulation supplies synchronous ideal PRG/CHR/CPU/CIRAM data and starts CPU/CIRAM at zero. This is not an external SRAM/PSRAM controller. The host consumer is testbench bus stimulus with qualified044 timing, not a running SNES program or measured SNES VBlank/PPU DMA deadline.

The joint area probe binds these exact functional modules and exported PPU signals, adding the existing0182KiB CPU RAM +2KiB CIRAM +8KiB PRG RAM resource wrapper. That wrapper is uninitialized, has synchronous read-old-data behavior and is not the simulation memory service. Its top-level elaboration/area fit is not a functional validation of the complete fitted machine. It has virtual ROM/IO pins and no board PLL, loader, physical memory controller, real board pin assignments, IO timing or STA signoff.

No new firmware/FPGA pair or SD image is issued by047. Preserve044 until runtime consumer, memory/clock/loader integration and complete board verification support a recoverable hardware candidate. The four upstream HDL adoption holds remain separate from the working free Questa FLOAT license.
