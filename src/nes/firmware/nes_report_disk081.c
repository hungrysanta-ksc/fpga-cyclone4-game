/* SPDX-License-Identifier: GPL-2.0-only */
#include "diskio.h"
extern DSTATUS sdn_report_mounted081(BYTE);
/* Report-only strong definition overrides the legacy weak alias at link time.
 * sdn_initialize and its active077 rejection remain unchanged. */
DSTATUS disk_initialize(BYTE drv) {return sdn_report_mounted081(drv);}
