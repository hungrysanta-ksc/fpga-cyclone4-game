# SPDX-License-Identifier: MIT
"""Inherited independent/STOP injections plus the common-context port fence."""
import guard_nes_joint396 as old
s=old.s.replace('range(1,20)','range(1,21)')
ns=dict(old.ns);exec(compile(s,'guards398','exec'),ns);guards=ns['guards']
