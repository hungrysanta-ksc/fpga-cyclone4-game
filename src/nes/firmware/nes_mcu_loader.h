/* SPDX-License-Identifier: MIT */
#ifndef NES_MCU_LOADER_H
#define NES_MCU_LOADER_H
#include <stdbool.h>
#include <stdint.h>
enum nes_mcu_load_result {
 NES_MCU_LOAD_OK, NES_MCU_LOAD_OPEN, NES_MCU_LOAD_HEADER,
 NES_MCU_LOAD_READ, NES_MCU_LOAD_CONTENT, NES_MCU_LOAD_SEEK,
 NES_MCU_LOAD_CONFIG, NES_MCU_LOAD_OWNERSHIP, NES_MCU_LOAD_ID,
 NES_MCU_LOAD_SPI, NES_MCU_LOAD_CHANGED, NES_MCU_LOAD_CLOSE
};
struct nes_mcu_load_report {
 enum nes_mcu_load_result result;
 uint32_t acknowledged_bytes;
 unsigned file_result;
 bool chr_32k, end_accepted, stop_ok, base_restored, recovery_attempted;
};
/* Internal load-only diagnostic, no menu hook or deliverable FPGA image yet.
 * Caller must own the synchronous menu/configuration path; not ISR/reentrant.
 * Uses a local read-only FIL. Never STARTs or releases SNES reset.
 * true means safe to reload the menu, NOT successful ROM execution/loading.
 * Check report.result/end_accepted separately. false requires fail-closed
 * recovery; do not re-enable USB or release reset. image must be an explicitly
 * approved materialized044+054 image, not the stock044 hardware baseline. */
bool nes_mcu_load_probe(const char *path, const char *image,
                        struct nes_mcu_load_report *report);
#endif
