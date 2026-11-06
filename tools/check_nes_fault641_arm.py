"""Feed the reproduced SPI reply to the packaged MMC639 Cortex-M4 FINISH path."""
import argparse
from pathlib import Path
import struct

from check_nes_fault641 import digest, evidence
from check_nes_supply485_arm import ARM, crc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--sim-log", required=True, type=Path)
    args = parser.parse_args()
    package = evidence("trial639-package.json")
    assert digest(args.src / "obj-nes-100/sd2snes.elf") == package["ELF"]
    assert digest(args.src / "obj-nes-100/firmware.stm") == package["firmware_SHA256"]
    fields = evidence("hardware640-mmc639.json")["runs"][0]["fields"]
    reply = bytes.fromhex(fields["plan_reply_hex"])
    trace = args.sim_log.read_text(errors="replace")
    assert "PASS641" in trace and trace.count("reply=" + reply.hex()) == 3
    cpu = ARM(args.src, "normal")
    cpu.setup()
    gen, sent = int(fields["plan_generation"]), int(fields["plan_sent"])
    cpu.put(cpu.s, "nes_native_sink165", "generation", gen, 2)
    cpu.endpoint.generation = gen
    for key in ("sent", "retired"):
        cpu.put(cpu.w, "nes_sink_window184", key, int(fields["sink_window_" + key]), 2)
    transfers = []
    batches = []

    def exchange(tx, clock):
        transfers.append(tx[0])
        if tx[0] == 0xe9:
            batches.append(tx)
            return bytes(len(tx))
        assert tx == bytes([0xe8]) + bytes(19)
        if len(batches) == sent:
            return reply
        status = bytearray(20)
        status[1:6] = bytes((0xd7, 4, 1, 0, len(batches)))
        status[19] = crc(status[1:19], 8, 7, 0)
        return bytes(status)

    cpu.endpoint.exchange = exchange
    assert cpu.emit(2, 0, 0) and cpu.emit(0, 1, 4)
    assert cpu.call("nes_plan200_end", [cpu.p]) == 1
    assert len(batches) == sent
    for tx, payload, count in zip(batches, [bytes.fromhex("82200080200001000400"), bytes.fromhex("832000")], [2, 1]):
        assert tx[:4] == bytes((0xe9, len(payload), 0, count)) and tx[4:-4] == payload
        assert int.from_bytes(tx[-4:-2], "big") == crc(payload, 16, 0x1021, 65535)
        assert tx[-2:] == bytes((crc(tx[:-2], 8, 7, 0), 0xa5))
    before_finish = len(transfers)
    assert cpu.call("nes_plan200_progress", [cpu.p, 1]) == 0
    assert cpu.get(cpu.p, "nes_plan200", "error") == 4
    saved = bytes(cpu.u.mem_read(cpu.data_symbols["nes_plan215"], 30))
    assert struct.unpack("<HHH4B", saved[:10]) == (sent, gen, 0, 0, 2, 4, 1)
    assert saved[10:] == reply
    assert cpu.call("nes_plan200_retire", [cpu.p]) == 0
    assert transfers[before_finish:] == [0xe8] and not cpu.get(cpu.p, "nes_plan200", "finished")
    print("PASS641 MMC639 ELF: emitted blank+BG and END; FINISH phase=2 reason=4 gen=32 sent=2; one FINISH E8, no EA")


if __name__ == "__main__":
    main()
