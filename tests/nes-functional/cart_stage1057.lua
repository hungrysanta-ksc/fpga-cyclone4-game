local f=assert(io.open(@OUT@,"w"))
local frame,mask=0,0
local pages={}
local pattern=assert(io.open(@PATTERN@,"w"))
emu.addMemoryCallback(function(a,v)
  if frame~=2100 then return end
  local loc=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
  if loc then pattern:write(string.format("%05x %02x\n",loc.address,v)) end
end,emu.callbackType.read,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
local mutations={}
local function record(a,v)
  if a==0x2001 then mask=v end
  if frame%60~=0 then return end
  local s=emu.getState()
  local line,dot=s["ppu.scanline"],s["ppu.cycle"]
  if a>=0xb000 and a<0xf000 and (line<0 or line>=240) then return end
  local key=string.format("%04x %02x %d %d",a,v,line,dot)
  mutations[key]=true
end
emu.addMemoryCallback(record,emu.callbackType.write,0x2000,0x2001)
emu.addMemoryCallback(record,emu.callbackType.write,0xb000,0xefff)
emu.addMemoryCallback(function(a,v)
  if frame%60~=0 then return end
  local s=emu.getState()
  f:write(string.format("READ %d %d %d %04x\n",frame,s["ppu.scanline"],s["ppu.cycle"],s["ppu.videoRamAddr"]))
end,emu.callbackType.read,0x2007,0x2007)
emu.addEventCallback(function()
  emu.setInput({start=frame>=150 and frame<5800 and frame%90<8,
                a=frame>=180 and frame%40<8,right=frame>=5800},0)
end,emu.eventType.inputPolled)
emu.addMemoryCallback(function(a,v)
  if frame%60~=0 then return end
  local s=emu.getState()
  local addr=s["ppu.videoRamAddr"] & 0x3fff
  local line=s["ppu.scanline"]
  if addr<8192 then
    local key=string.format("CHR group=%d line=%d",addr//128,line)
    pages[key]=(pages[key] or 0)+1
  end
end,emu.callbackType.write,0x2007,0x2007)
emu.addEventCallback(function()
  if frame%60==0 then
    local s=emu.getScreenBuffer()
    if frame%300==0 then
      local image=assert(io.open(@IMAGE@..frame..".ppm","wb"))
      image:write("P6\n256 240\n255\n")
      local row={}
      for i=1,#s do
        local p=s[i]
        row[#row+1]=string.char((p>>16)&255,(p>>8)&255,p&255)
        if #row==256 then image:write(table.concat(row));row={} end
      end
      image:close()
    end
    local colors={}
    for _,p in ipairs(s) do colors[p]=true end
    local count=0
    for _ in pairs(colors) do count=count+1 end
    f:write(string.format("FRAME %d colors=%d mask=%02x\n",frame,count,mask))
    for key in pairs(mutations) do f:write(key.."\n") end
    for key,n in pairs(pages) do f:write(key.." n="..n.."\n") end
    pages={}
    mutations={}
    f:flush()
  end
  frame=frame+1
  if frame==7201 then f:close();pattern:close();emu.stop(0) end
end,emu.eventType.endFrame)
