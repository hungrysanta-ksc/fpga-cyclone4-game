/* SPDX-License-Identifier: MIT */
#ifndef NES_MENU_DIAGNOSTIC_H
#define NES_MENU_DIAGNOSTIC_H
#include <stdbool.h>
#include <stdint.h>
/* Manual-only compile candidate. Marker selects a fixed approved fixture;
 * neither the marker contents nor an arbitrary browser path becomes a ROM. */
bool nes_menu_diagnostic_marker(const uint8_t *);
/* true permits menu reload, including safely recovered test failures.
 * false requires RESET held and a fail-closed caller. Never STARTs. */
bool nes_menu_diagnostic_run(const uint8_t *);
/* Called after menu memory/configuration preparation, before RESET release.
 * Only a nonzero menu load and reliable SRAM permit release for a pending run. */
bool nes_menu_diagnostic_prepared(bool);
/* Called after RESET release. Records a reached code boundary, not a user
 * observation of a working screen. Logging failure never changes recovery. */
void nes_menu_diagnostic_released(void);
#endif
