"""687 replay entry using the unchanged validated686/685 observation chain.

An initial patch of the imported673 module did not bind to its runpy __main__
instance. No owner687 samples were produced. That attempt is archived; the
retained replay has only the original actual instruction/SPI/DMA observations.
Use the linked map guards for the new pending-owner rule, not invented samples.
"""
import runpy

if __name__=='__main__':
    runpy.run_module('test_nes_seal686',run_name='__main__')
