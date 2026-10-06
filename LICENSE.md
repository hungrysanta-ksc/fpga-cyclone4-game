# sd2snesHST licensing

Copyright (c) 2026 HungrySanTa, for original project contributions.

The project owner selected the following terms on 2026-10-04. These grants cover HungrySanTa's original contributions only, including the corresponding unchanged C44 files identified by `source-manifest.json`. They do not replace third-party copyright or license notices.

| Original contribution | License |
| --- | --- |
| FPGA integration HDL and its build constraints in src/fpga | GNU GPL version 3 or any later version |
| MCU additions and modifications in src/firmware-overlay | GNU GPL version 2 only |
| Independently authored renderer generators, tools, tests and documentation | MIT |

Full texts: [GPLv3](licenses/GPL-3.0.txt), [GPLv2](licenses/sd2snes-COPYING), [MIT](licenses/HungrySanTa-MIT.txt).

Third-party files retain their existing terms. In particular, T80's source/synthesized-form notice, SameBoy's MIT notice and Intel/Altera generated-source notices must be retained. A file without its own header is not automatically assigned HungrySanTa's license: its upstream provenance and accompanying notices remain applicable. The grants above apply only to our modifications where an upstream-derived file is involved.

The MCU and GBC FPGA are separate build outputs. This document does not relabel all upstream code or every packaged component under one license.

See [dependency register](docs/DEPENDENCY-REGISTER.ko.md) and [source license inventory](release/source-license-inventory.json) for scope and provenance. There is no warranty beyond the terms of the applicable licenses.

The independently authored NES diagnostic/adapter files in `src/nes` retain their existing SPDX MIT headers. They do not include the upstream NES CPU/PPU implementation. See [NES provenance and reproduction limits](cores/nes/REPRODUCING.ko.md) and [the upstream lock](analysis/source-lock.json); vendoring holds remain unresolved. No upstream grant is broadened by this publication.
