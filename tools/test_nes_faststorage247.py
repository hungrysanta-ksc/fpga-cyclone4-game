# SPDX-License-Identifier: MIT
"""Actual bus RTL equality for split6KiB versus direct8KiB; no board timing."""
import inspect
import test_nes_storage247 as base


def main():
    s=inspect.getsource(base.main).replace('split5k','split6k')
    ns=dict(base.__dict__);ns.update(__file__=__file__,__doc__=__doc__)
    exec(compile(s,'faststorage-rtl247','exec'),ns);ns['main']()


if __name__=='__main__':main()
