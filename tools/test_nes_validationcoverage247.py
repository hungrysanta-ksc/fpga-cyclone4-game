# SPDX-License-Identifier: MIT
"""Every pattern coverage lane rejects missing validity in range receiver."""
import test_nes_fastlanes247 as prior


if __name__=='__main__':
    prior.CASES=tuple(f'coverage_lane{i}' for i in range(8))
    prior.__file__=__file__;prior.__doc__=__doc__;prior.main()
