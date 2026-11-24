"""Replay the 978 schedule while changing only the wire time of selected 911 packets."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_page963
from nes_hdma990 import BASE
from replay_nes_supply905 import joint

MODES = ("table", "seal", "both", "oracle", "all3")
SPI_HZ = 2_625_000


def encode(raw):
    # One occupancy bitmap per eight bytes. The checked logical span fixes the
    # last group's width. Literal form is retained if this would grow.
    occupied = bytearray()
    values = bytearray()
    for i in range(0, len(raw), 8):
        mask = 0
        for bit, value in enumerate(raw[i:i+8]):
            if value:
                mask |= 1 << bit
                values.append(value)
        occupied.append(mask)
    return bytes(occupied + values)


def decode(packed, length):
    masks = (length + 7) // 8
    if len(packed) < masks or (length % 8 and packed[masks-1] >> (length % 8)):
        raise ValueError("invalid occupancy")
    mask = int.from_bytes(packed[:masks], "little")
    values = packed[masks:]
    if mask.bit_count() != len(values) or 0 in values:
        raise ValueError("noncanonical literal count or value")
    literals = iter(values)
    return bytes(next(literals) if mask & (1 << i) else 0 for i in range(length))


def run(temp, phase, mode):
    # Counterfactual. Preserve every logical byte, CRC, credit and receiver
    # instruction. No encoding or decoding cost is charged on either CPU.
    init = joint.Runtime.__init__
    log = []

    def install(cpu, args, link):
        init(cpu, args, link)
        response = link.response
        accept = link.accept
        original_cost = None

        def timed(tx):
            nonlocal original_cost
            if tx[0] == 0xe1:
                header, payload = tx[1:17], tx[17:-2]
                offset = int.from_bytes(header[10:12], "little")
                key = {(2, 5, 1322, 240): "table", (3, 0, 0, 168): "seal",
                       (2, 5, 1121, 201): "raw"}.get((header[0], header[1], offset, len(payload)))
                if cpu.generation == 911 and key:
                    assert int.from_bytes(header[8:10], "little") == 911
                    compressed = encode(payload)
                    assert decode(compressed, len(payload)) == payload
                    n = len(payload)
                    if mode == "oracle" and key != "raw":
                        n -= payload.count(0)  # positions supplied for free
                    elif mode == key or mode == "all3" or (mode == "both" and key != "raw"):
                        n = min(n, len(compressed))
                    assert original_cost is None
                    original_cost = cpu.driver_extra.get(0xe1, args.spi_us * joint.MASTER / 1e6)
                    cpu.driver_extra[0xe1] = original_cost - (len(payload)-n)*8*joint.MASTER/SPI_HZ
                    log.append(dict(kind=key, logical_B=len(payload), zeros=payload.count(0),
                                    packed_B=len(compressed), charged_B=n, start=cpu.clock))
            return response(tx)
        def retire(tx, at):
            nonlocal original_cost
            if original_cost is not None:
                cpu.driver_extra[0xe1] = original_cost
                original_cost = None
            return accept(tx, at)
        link.response = timed
        link.accept = retire

    tag = "995wire" + mode
    with patch.object(joint.Runtime, "__init__", install):
        nes_page963.simulate(temp, phase, "cold", True, BASE, True, tag=tag, edition=966)
    assert [x["kind"] for x in log] == ["raw", "table", "seal"]
    from nes_ready958 import directory
    (directory(temp, phase, tag, "cold")/"transport995.json").write_text(json.dumps(log))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp", type=Path)
    p.add_argument("phase", type=int, choices=(1, 2))
    p.add_argument("mode", choices=MODES)
    a = p.parse_args()
    run(a.temp, a.phase, a.mode)
