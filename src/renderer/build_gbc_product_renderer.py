import struct

class Asm:
    def __init__(self, base):
        self.base = base
        self.data = bytearray()
        self.labels = {}
        self.fixups = []

    @property
    def pc(self):
        return self.base + len(self.data)

    def emit(self, *values):
        self.data.extend(value & 0xFF for value in values)

    def label(self, name):
        assert name not in self.labels
        self.labels[name] = self.pc

    def branch(self, opcode, label):
        self.emit(opcode, 0)
        self.fixups.append((len(self.data) - 1, label, "rel8"))

    def absolute_label(self, opcode, label):
        self.emit(opcode, 0, 0)
        self.fixups.append((len(self.data) - 2, label, "abs16"))

    def lda8(self, value):
        self.emit(0xA9, value)

    def ldx16(self, value):
        self.emit(0xA2, value, value >> 8)

    def read(self, address):
        self.emit(0xAD, address, address >> 8)

    def write(self, address, value):
        self.lda8(value)
        self.emit(0x8D, address, address >> 8)

    def sta(self, address):
        self.emit(0x8D, address, address >> 8)

    def stz(self, address):
        self.emit(0x9C, address, address >> 8)

    def jsr(self, label):
        self.absolute_label(0x20, label)

    def jump(self, label):
        self.absolute_label(0x4C, label)

    def finish(self):
        for offset, label, kind in self.fixups:
            assert label in self.labels, label
            if kind == "rel8":
                after = self.base + offset + 1
                delta = self.labels[label] - after
                assert -128 <= delta <= 127, (label, delta)
                self.data[offset] = delta & 0xFF
            else:
                self.data[offset:offset + 2] = struct.pack("<H", self.labels[label])
        return bytes(self.data)

def dma(a, source, count, mode, target, channel=7):
    base = 0x4300 + channel * 0x10
    a.write(base + 0, mode)
    a.write(base + 1, target)
    a.write(base + 2, source & 0xFF)
    a.write(base + 3, (source >> 8) & 0xFF)
    a.write(base + 4, (source >> 16) & 0xFF)
    a.write(base + 5, count & 0xFF)
    a.write(base + 6, count >> 8)
    a.write(0x420B, 1 << channel)
