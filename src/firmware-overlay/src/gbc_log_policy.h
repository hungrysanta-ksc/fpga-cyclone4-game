/* C44: SD diagnostic reports only. Do not remove GBC_DIAGNOSTIC,
 * GBC_PROBE_G12, GBC_SAVE_G12 or GBC_DUMP_G12: they also select live paths.
 * Volatile read keeps the existing profiling/diagnostic code observable to
 * the compiler while the release default suppresses filesystem operations.
 * Set -DGBC_FILE_LOGS=1 only for an explicitly requested diagnostic build.
 */
#ifndef GBC_LOG_POLICY_H
#define GBC_LOG_POLICY_H
#ifndef GBC_FILE_LOGS
#define GBC_FILE_LOGS 0
#endif
#if GBC_FILE_LOGS != 0 && GBC_FILE_LOGS != 1
#error GBC_FILE_LOGS must be 0 or 1
#endif
static const volatile unsigned char gbc_file_logs_enabled = GBC_FILE_LOGS;
#endif
