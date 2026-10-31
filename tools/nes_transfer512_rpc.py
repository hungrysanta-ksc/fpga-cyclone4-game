# SPDX-License-Identifier: MIT
"""Private local pipes transport the same ARM/SNES clock rendezvous as joint506."""
import ctypes as C
from ctypes import wintypes as W
import json
import threading
import time
import uuid

from test_nes_service509_schedule import TraceLink
import test_nes_raw506_joint as joint

K = C.WinDLL("kernel32", use_last_error=True)
K.CreateNamedPipeW.restype = W.HANDLE
K.CreateNamedPipeW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.LPVOID]
K.ConnectNamedPipe.argtypes = [W.HANDLE, W.LPVOID]
K.WriteFile.argtypes = K.ReadFile.argtypes = [W.HANDLE, W.LPVOID, W.DWORD, C.POINTER(W.DWORD), W.LPVOID]
K.PeekNamedPipe.argtypes = [W.HANDLE, W.LPVOID, W.DWORD, W.LPVOID, C.POINTER(W.DWORD), W.LPVOID]
K.CloseHandle.argtypes = [W.HANDLE]


class Pipe:
    def __init__(self, outbound):
        self.name = r"\\.\pipe\mmc512-" + uuid.uuid4().hex
        self.handle = K.CreateNamedPipeW(self.name, 2 if outbound else 1, 8, 1, 65536, 65536, 0, None)
        if self.handle == W.HANDLE(-1).value:
            raise C.WinError(C.get_last_error())
        self.connected = threading.Event()
        self.error = None
        threading.Thread(target=self.connect, daemon=True).start()

    def connect(self):
        if not K.ConnectNamedPipe(self.handle, None) and C.get_last_error() != 535:
            self.error = C.get_last_error()
        self.connected.set()

    def write(self, data):
        if not self.connected.wait(45):
            raise TimeoutError("65816 pipe did not open")
        if self.error:
            raise C.WinError(self.error)
        sent = W.DWORD()
        if not K.WriteFile(self.handle, data, len(data), C.byref(sent), None) or sent.value != len(data):
            raise C.WinError(C.get_last_error())

    def read(self, process):
        data = bytearray()
        deadline = time.monotonic() + 60
        while not data.endswith(b"\n"):
            available = W.DWORD()
            if not K.PeekNamedPipe(self.handle, None, 0, None, C.byref(available), None):
                raise C.WinError(C.get_last_error())
            if available.value:
                buf = C.create_string_buffer(available.value)
                got = W.DWORD()
                if not K.ReadFile(self.handle, buf, len(buf), C.byref(got), None):
                    raise C.WinError(C.get_last_error())
                data.extend(buf.raw[:got.value])
            else:
                if process.poll() is not None or time.monotonic() > deadline:
                    raise TimeoutError("65816 reply missing")
                time.sleep(.0005)
        return data.decode("ascii").rstrip("\r\n").split("|")


class PipeLink(TraceLink):
    def __init__(self, a):
        self.commands, self.replies = Pipe(True), Pipe(False)
        emit = joint.lua_rpc
        def configure(args):
            emit(args)
            path = a.out / "capture.lua"
            s = path.read_text()
            start = s.index("local function nextCommand()")
            end = s.index("\nnextCommand()\n", start)
            # Open and flush the text streams in binary mode to preserve framing.
            s = s[:start] + """local cmds=assert(io.open(%s,'rb'))
local replies=assert(io.open(%s,'wb'))
local function nextCommand()
 sequence=sequence+1
 local id=tonumber(assert(cmds:read('*l')));assert(id==sequence)
 target=tonumber(assert(cmds:read('*l')));operation=assert(cmds:read('*l'))
 args={cmds:read('*l'),cmds:read('*l')}
end""" % (json.dumps(self.commands.name),json.dumps(self.replies.name)) + s[end:]
            start = s.index("  local f=assert(io.open(ROOT..'/reply.tmp'")
            end = s.index("  if finished then return end",start)
            s = s[:start] + """  local ans={tostring(sequence),tostring(target),tostring(now),tostring(retired),hex(lastAck)}
  local c={};for _,v in ipairs(consumed) do c[#c+1]=string.format('%d:%d;',v[1],v[2]) end
  local e={};for _,v in ipairs(retiredEvents) do e[#e+1]=string.format('%d:%d:%s;',v[1],v[2],hex(v[3])) end
  ans[6]=table.concat(c);ans[7]=table.concat(e);consumed={};retiredEvents={}
  replies:write(table.concat(ans,'|'),'\\n');replies:flush()
""" + s[end:]
            path.write_text(s,encoding="utf8")
        joint.lua_rpc = configure
        try:
            super().__init__(a)
        finally:
            joint.lua_rpc = emit
        self.packet_log = (a.out / "packets.jsonl").open("w")

    def exchange(self, seq, target, operation, args):
        if operation == "PUSH":
            self.packet_log.write(json.dumps([seq, target, *args])+"\n")
            self.packet_log.flush()
        fields = [str(seq),str(target),operation,*args]
        fields.extend([""]*(5-len(fields)))
        self.commands.write(("\n".join(fields)+"\n").encode("ascii"))
        reply = self.replies.read(self.process)
        if list(map(int,reply[:2])) != [seq,target]:
            raise ValueError("Wrong sequence or target in 65816 reply")
        if operation == "FINISH":
            self.packet_log.close()
            K.CloseHandle(self.commands.handle)
            K.CloseHandle(self.replies.handle)
        return reply[2:]
