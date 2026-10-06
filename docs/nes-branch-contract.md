# NES 분기 버스 진단 계약

SPDX-License-Identifier: MIT.

`NES-P2-BRANCH-011`은 자체 NROM의 8개 분기 opcode × 7개 조건, 총 56개를 실행한다. BCC/BCS/BEQ/BNE/BMI/BPL/BVC/BVS 각각 조건 불성립, 같은 페이지 앞/뒤, 페이지 경계 앞/뒤, +127/-128 displacement를 검사한다. reset 후 SEI, PPU/DMC 비활성, frame IRQ inhibit 설정을 적용한다. PLP로 flag를 설정하고 JMP로 각 분기 지점에 들어간다. RAM0에 순차 case ID를 쓰며 255로 완료한다. 상용 ROM이나 BIOS가 필요하지 않다.

## 관측과 기대값

RTL은 기존 NROM NES/CPU/PPU/APU wrapper 및 ideal memory를 사용한다. reset vector 처리 뒤 첫 `$8000:SEI` 읽기부터 cart_ce마다 master tick, address, read, data, RAM0, Instrnew를 기록한다. 초기 reset의 미정 bus를 정상 instruction 실행으로 세지 않으며 이후 미정값과 12-master-tick 주기 위반은 실패다. Instrnew는 마지막 microcycle 표시이므로 opcode fetch로 해석하지 않는다.

검증기는 ROM의 opcode/offset 및 설정한 flag로 분기 여부와 target을 독립 계산한다. branch+operand 뒤 조건 불성립은 2 cycles, 성립은 sequential PC read를 포함하여 3 cycles, page-cross는 이전 high byte와 목적지 low byte를 합친 추가 read를 포함하여 4 cycles다. opcode부터 다음 opcode까지 주소, 읽기 방향, 실제 ROM data, tick 간격과 도착 주소를 확인한다. 56개에서 총 192 branch cycles, 그중 discarded read 80개를 검사한다.

Mesen exec callback은 opcode 전이므로 두 exec 사이 CPU cycle 차이로 instruction 길이를 비교한다. 일반 read callback이 제공하는 discarded read는 해당 instruction의 3/4번째 cycle에 비교한다. opcode/operand 전체를 Mesen read callback이 제공한다고 가정하지 않는다. 56개 모두 callback read 주소/값과 다음 opcode/사이클 수가 oracle에 일치해야 한다. 주소·tick·read·data 변조 및 trace 절단 5종을 거부해야 한다.

로컬 Mesen 기준은 기존 base `20ba206cef5ba207c21203176d02cb9f43dda9fb` + emucap 변경 빌드다. `Core/NES/NesCpu.h:465`의 BranchRelative에서 DummyPcRead 뒤 page-cross의 `(PC high | target low)` 읽기를 수행한다. 검사한 해당 파일 SHA256은 `e28ba272fe39ca61f44ec146f8d5d32f46d05385e819ac2e9aec2f056e61da08`이다. 실행 binary/settings 해시는 reference capture.json에 남긴다.

## 로컬 수정

`tools/nes_branch.py`는 해시 고정한 기존 RTL-006 driver를 재사용하고 생성된 로컬 T65 주소 출력만 바꾼다. CPU mode00의 branch Cycle_2는 현재 sequential PC, Cycle_3는 현재 target low와 이전 page high를 내보낸다. 저장 레지스터 추가 없이 기존 PC/DL로 주소를 조합한다. 내부 PC 갱신, microcode, IRQ detection 로직, cycle 수는 수정하지 않는다. 원본 T65와 LF 생성 사본의 서로 다른 해시를 각각 검증하며 patch diff를 저장한다. upstream은 고정 commit `49a0a662e244469ca77b2155746a066df704ffae` 그대로다.

기존 006/009/010 driver·testbench는 수정하지 않는다. 새 수정이 필요한 실행은 `run_nes_branch.ps1`을 사용한다. `-Mapper4`를 주면 기존 009 adapter와 조합한다. 과거 기록 재현과 수정본 실행 경로를 혼동하지 않는다. 생성 HDL은 라이선스 고지를 유지하고 ignored 로컬 증거에만 보존한다. 개별 source license hold 및 제품 채택 검토는 완료된 것으로 바꾸지 않는다.

## 재현

변수는 기존 Python/Questa/FLOAT wrapper/upstream/Mesen 절대 경로다. [FLOAT 규칙](questa-execution.md)을 따른다. 각 Out은 새 ASCII 경로여야 한다. 기존 무료 FLOAT 권한으로 실제 시험을 직접 실행하며 별도 smoke나 새 라이선스를 요구하지 않는다.

```powershell
& $PY -B -X utf8 tools/build_nes_branch.py --out "$env:TEMP/nes-branch-rom"
# 수정 전 실제 실패를 관측할 때만 기존 run_nes_functional.ps1 + branch_tb.sv 사용
& ./tools/run_nes_branch.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-branch-rtl" -Diagnostic "$env:TEMP/nes-branch-rom"
& $PY -B -X utf8 tools/run_nes_branch_reference.py --mesen $MESEN --probe "$env:TEMP/nes-branch-rom" --out "$env:TEMP/nes-branch-mesen"
& $PY -B -X utf8 tools/verify_nes_branch.py --rom "$env:TEMP/nes-branch-rom" --rtl "$env:TEMP/nes-branch-rtl" --mesen "$env:TEMP/nes-branch-mesen" --out "$env:TEMP/nes-branch-rtl/verification.json"

# 기존 009 최종 자체 MMC3 ROM 및 010 기준 출력/참조를 입력으로 사용
& ./tools/run_nes_branch.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-branch-integrated" -Diagnostic $MMC3_ROM -Mapper4 -Testbench tests/nes-functional/mmc3_irq_phase_tb.sv
& $PY -B -X utf8 tools/verify_nes_mmc3_integrated.py --run "$env:TEMP/nes-branch-integrated" --reference $MMC3_MESEN --rom $MMC3_ROM
& $PY -B -X utf8 tools/verify_nes_branch_regression.py --rtl "$env:TEMP/nes-branch-integrated" --baseline $RTL_010 --mesen $MMC3_MESEN --out "$env:TEMP/nes-branch-integrated/branch-regression.json"
```

분기 자체 진단은 interrupts disabled다. 통합 IRQ 회귀는 기존 진단 범위다. 분기 각 cycle의 IRQ/NMI sampling, RDY/DMA stall, MMIO 부작용, 16-bit address wrap, 전체 flag 조합, 다른 CPU mode, savestate 복구, 전체 CPU/PPU/APU 호환성, fit/STA 및 실기는 검증하지 않았다. 다음 우선 작업은 분기 주변 IRQ sampling을 독립 시나리오로 검사하는 것이다.
