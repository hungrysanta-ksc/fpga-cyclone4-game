# NES IRQ 관측 위상 비교 계약

SPDX-License-Identifier: MIT.

009 자체 Mapper4 ROM과 adapter/CPU/PPU 코드를 그대로 사용한다. 추가 계측만 `mmc3_irq_phase_tb.sv` 및 `capture_mmc3_irq_phase.lua`에서 수행한다. [통합 계약](nes-mmc3-integrated-contract.md)과 [FLOAT 실행 규칙](questa-execution.md)을 함께 적용한다. 기준 ROM SHA256은 `8b380949760320c993fd35a2a48af29a6afe2516f353d048f65f49fa1dd38ba9`다.

## 재현

변수는 기존 로컬 Python/Questa/Mesen/upstream/승인된 FLOAT wrapper의 절대 경로다. 모든 출력은 새 ASCII 경로를 사용한다. Mesen 실행에는 기존 DOTNET_ROOT 설치 설정을 사용한다.

```powershell
& $PY -B -X utf8 tools/build_nes_mmc3.py --out "$env:TEMP/nes-phase-rom"
& ./tools/run_nes_mmc3_integrated.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-phase-rtl" -Diagnostic "$env:TEMP/nes-phase-rom" -Testbench tests/nes-functional/mmc3_irq_phase_tb.sv
& $PY -B -X utf8 tools/run_nes_mmc3_irq_reference.py --mesen $MESEN --probe "$env:TEMP/nes-phase-rom" --out "$env:TEMP/nes-phase-mesen"
& $PY -B -X utf8 tools/verify_nes_mmc3_integrated.py --run "$env:TEMP/nes-phase-rtl" --reference "$env:TEMP/nes-phase-mesen" --rom "$env:TEMP/nes-phase-rom"
& $PY -B -X utf8 tools/verify_nes_irq_phase.py --rtl "$env:TEMP/nes-phase-rtl" --mesen "$env:TEMP/nes-phase-mesen" --out "$env:TEMP/nes-phase-rtl/phase-verification.json"
```

## 관측 위치와 비교 조건

RTL은 60ms 이후 scanline62/dot>=200 또는 scanline63/dot<80에서 cart_ce와 cpu_ce를 pre-NBA posedge로 기록한다. 원래 master_ticks 증가 바로 뒤에 기록하여 control.tsv와 시간 단위를 맞춘다. 열은 master_ticks, line, dot, RAM1 counter, cart_ce, cpu_ce, address, read, data, Instrnew, mapper_irq다. cart_ce→cpu_ce는 2 master ticks이며 관측 창 경계에서 잘린 짝을 제외한 365쌍의 주소/RW/data/counter를 검사한다.

Mesen frame6..9의 같은 창에서 read/write/exec callback을 기록한다. 열은 kind, frame, line, dot, ppu.masterClock, CPU cycleCount, RAM1 counter, address, value, cpu.pc, cpu.irqFlag 또는 -1이다. 마지막 값은 이 빌드 getState에 노출되지 않아 -1이다. Mesen IRQ pin assertion 시점은 측정하지 않았다.

Mesen exec callback은 opcode fetch 전의 관측이므로 비교에서 제외한다. read callback도 opcode/operand fetch 전체를 제공하지 않는다. 따라서 전체 CPU bus 일치 시험으로 취급하지 않는다. 로컬 Mesen NesCpu.cpp의 StartCpuCycle/EndCpuCycle, NesMemoryManager.cpp의 Read/Write, ScriptManager.h callback mapping을 기준으로 해석한다. pinned Mesen base는 `20ba206cef5ba207c21203176d02cb9f43dda9fb`이며 기존 emucap 변경이 포함된 로컬 빌드다.

공통 ROM counter3..6 각각에서 IRQ 전 RAM8 읽기 마지막 3개로만 위상 차이를 측정한다. IRQ 후 데이터를 사용해 offset을 맞추지 않는다. 그 뒤 스택 쓰기 3개, vector 읽기 2개, PHA 쓰기, RAM3 read/old-write/new-write, E000 acknowledge의 주소·R/W·값과 상대 사이클을 검사한다. 첫 스택 쓰기 기준 상대 CPU cycles는 0,1,2,3,4,7,10,11,12,18이다. 모든 IRQ bus landmark에서도 IRQ 전 offset이 그대로 유지되어야 한다. E000을 CPU 1사이클 늦춘 음성 시험을 거부해야 한다.

절대 부팅 시점·CPU/PPU 정렬·callback 위상은 공통 외부 시간축에 보정하지 않았다. 4 dot를 없애려는 지연이나 코어 변경을 적용하지 않는다. 분기 discarded read의 RTL E182 / Mesen E186 차이는 별도 검증 대상으로 남긴다. 라이선스 파일과 서버 로그는 증거 사본 및 Git에서 제외한다. 상용 ROM, MCU/FPGA 제품 코드, 원본 upstream은 변경하지 않는다.
