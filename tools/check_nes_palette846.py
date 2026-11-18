"""Execute the linked wait gate with pending input and planner ownership."""
import json
from check_nes_game478 import Machine, ELFFile, UC_HOOK_CODE, sha
from check_nes_hardware494_termination import member_offset
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_PC
from nes_palette846 import OUT, link


def verify(mode):
    src = link(mode)/"src"
    m = Machine(src,bytes(128))
    with (src/"obj-nes-100/sd2snes.elf").open("rb") as stream:
        elf = ELFFile(stream)
        for cu in elf.get_dwarf_info().iter_CUs():
            for d in cu.iter_DIEs():
                name = d.attributes.get("DW_AT_name")
                size = d.attributes.get("DW_AT_byte_size")
                if d.tag != "DW_TAG_structure_type" or not name or not size:
                    continue
                name = name.value.decode()
                if name not in ("nes_native_runtime165","nes_plan200"):
                    continue
                m.layout[name] = dict(size=size.value,**{
                    c.attributes["DW_AT_name"].value.decode(): member_offset(c)
                    for c in d.iter_children() if c.tag=="DW_TAG_member"})
    rt = 0x20003000
    layout = m.layout["nes_native_runtime165"]
    assert rt+layout["size"] < m.state
    check = 0x0807ffc0
    polls = []
    answer = True
    def ret(u,value):
        u.reg_write(UC_ARM_REG_R0,int(value))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def service(u,at,size,name):
        if name in ("guard","pause"):
            ret(u,answer)
        else:
            polls.append("input")
            state = m.layout["nes_native165"]
            m.u.mem_write(m.state+state["next_token"],(1).to_bytes(2,"little"))
            m.u.mem_write(m.state+state["state"],bytes([2]))
            ret(u,True)
    for name,addr in (("guard",check),("pause",m.syms["nes_cost474_pause"]),("input",m.syms["nes_native165_poll"])):
        m.u.hook_add(UC_HOOK_CODE,service,name,begin=addr,end=addr)
    def put(addr,kind,name,value,size=1):
        m.u.mem_write(addr+m.layout[kind][name],int(value).to_bytes(size,"little"))
    records = []
    for prepared in (0,1):
        for finished in (0,1):
            for reason in (0,1):
                for progress in (0,1):
                    for answer in (False,True):
                        polls.clear()
                        m.u.mem_write(rt,bytes(layout["size"]))
                        put(rt,"nes_native_runtime165","receiver",m.state,4)
                        put(rt,"nes_native_runtime165","resident",m.resident,4)
                        put(m.resident,"nes_resident211","prepared",prepared)
                        put(m.resident,"nes_resident211","open",1)
                        put(m.state,"nes_native165","state",4)
                        put(m.state,"nes_native165","next_token",0,2)
                        put(rt+layout["plan"],"nes_plan200","finished",finished)
                        result = m.call("wait634",[rt,check|1,reason,progress])
                        expected = bool(finished and not progress and answer and (prepared or mode=="first"))
                        assert bool(polls)==expected and bool(result)==answer
                        if not expected:
                            assert m.u.mem_read(m.state+m.layout["nes_native165"]["state"],1)==bytes([4])
                        records.append(dict(prepared=prepared,finished=finished,reason=reason,
                                            progress=progress,guard=answer,polls=len(polls)))
    return dict(firmware=sha(src/"obj-nes-100/firmware.stm"),cases=records)


if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    result={m:verify(m) for m in ("first","safe","queued")}
    (OUT/"ownership.json").write_text(json.dumps(result,indent=2)+"\n",newline="\n")
