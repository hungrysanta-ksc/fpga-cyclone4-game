# Questa execution contract

SPDX-License-Identifier: MIT.

The Windows host has a working free Starter FLOAT entitlement. The default inherited
uncounted license file fails in this Terminal Services session. This is an execution-route
problem, not evidence that a new paid license is required.

Use `tools/run_nes_functional.ps1` with `-Python`, `-FloatWrapper`, `-QuestaBin`,
`-Upstream`, `-Out`, and `-Diagnostic`; optional `-Testbench` selects another original test.
Paths are explicit. The known local paths are in the user's global AGENTS.md.
The wrapper runs the actual job with `-RunOnly -AfterSmokeScript`; no recurring license
smoke check is needed. It pins the previously approved wrapper hash and changes only its
private output directory so historical license diagnostics are preserved.

The legacy wrapper checks host/ports, starts the temporary server, sets the child
`SALT_LICENSE_SERVER=18000@localhost`, and stops the server in finally. Never terminate
another task's server or change permanent settings. The NES Python driver rejects an
inherited file-based license before creating build output. Compilation without a testbench
is still available without simulation checkout.

Keep all licenses and server logs private. The original file and signed feature content
must remain unchanged. An absent server between jobs is normal. Investigate an actual
new checkout error separately from compile/test failures; do not retry the known-bad
uncounted route. Treat a completed simulation and an explicit assertion pass as separate
checks, and preserve raw failure logs.

## Reproduce the original NES RTL diagnostic

Use installed tool paths from the local global instructions. Each output directory must be new.

```powershell
& $PY -B -X utf8 tests/nes-functional/build_smoke.py --out "$env:TEMP/nes-smoke-repro"
& ./tools/run_nes_functional.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-rtl-repro" -Diagnostic "$env:TEMP/nes-smoke-repro"
& $PY -B -X utf8 tools/verify_nes_rtl.py --run "$env:TEMP/nes-rtl-repro"
```

The verifier checks the exact original smoke ROM identity, RTL PASS and error markers,
clock/audio metrics, and an independent full-frame CHR-derived pixel reference. Simulator
exit zero alone is insufficient: observed `$fatal` stops can still return zero in batch mode.
Keep the raw log and require the diagnostic PASS marker with no Fatal/Error markers.
The output color contract is `cycle=x+2`; this follows the registered color pipeline and
preserves all 256 source pixels through cycle 257.
