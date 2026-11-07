"""Admit a ready capture behind an observed sealed END, with old staged tokens intact."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime


def admission(original):
    def offer(cpu):
        link=cpu.link
        if (not link.jobs or cpu.input_generation!=cpu.generation or not cpu.prepared
                or cpu.generation+1>=905+cpu.a.frames or cpu.clock<cpu.next_capture_ready
                or cpu.index!=len(cpu.packets) or not link.end or link.open or link.flight or link.todo):
            return original(cpu)
        # Demand a positive host-visible END snapshot in this generation.
        for event in reversed(cpu.events):
            if event["generation"]!=cpu.generation:return original(cpu)
            if event.get("opcode")=="0xe8":
                reply=bytes.fromhex(event["reply"])
                if reply[3]!=2 or reply[6]!=1:return original(cpu)
                break
        else:return original(cpu)
        tokens=[(j["gen"],j["token"],bytes(j["data"])) for j in link.jobs]
        assert all(g==cpu.generation for g,_,_ in tokens) and len(tokens)<=2
        cpu.start_token=(cpu.start_token+len(cpu.packets))&65535
        cpu.begin_input(cpu.generation+1)
        assert tokens==[(j["gen"],j["token"],bytes(j["data"])) for j in link.jobs]
        cpu.events[-1].update(previous_output=link.generation,held_tokens649=[t for _,t,_ in tokens])
    return offer


if __name__=="__main__":
    with patch.object(Runtime,"offer_input",admission(Runtime.offer_input)):
        runpy.run_module("test_nes_tail648",run_name="__main__")
