# NES 분기 IRQ 샘플링 진단 계약

SPDX-License-Identifier: MIT.

자체 NROM에서 BEQ 조건 불성립, 같은 페이지 앞/뒤 분기, 페이지 경계 앞/뒤 분기를 검사한다. 각 명령 길이 L에 대해 IRQ 시작 위치를 opcode cycle=0부터 L+1까지 이동한다. 1 CPU-cycle 펄스와 handler acknowledge까지 유지하는 level을 각각 적용하여 총 52개다. IRQ mask는 PLP로 해제하고 NMI·PPU rendering·DMC 및 APU frame IRQ는 비활성화한다. 분기 뒤 NOP6개와 SEI가 이어지며 다음 시나리오로 넘어간다.

## 자극과 관측

기존 NES full wrapper의 mapper_irq net을 testbench에서만 force하여 합성 입력을 연결한다. MMC3의 실제 A12 IRQ 발생 시험이 아니다. stimulus는 cpu_ce 활성 posedge 직전 master-clock negedge에 바뀌며 다음 CPU edge까지 안정적이다. RAM0 case ID와 PRG 내 metadata table로 branch 주소·시작 cycle·pulse 종류를 결정한다. 계측은 cpu_ce에서 tick/address/read/data/case/relative step/IRQ level을 기록한다. 초기 reset-vector 처리 후 첫 SEI opcode부터 정상 bus 검사를 시작한다.

CPU mode00, enable당 12 master ticks, ideal memory이며 RDY/DMA stall은 없다. stack writes $01FF/$01FE/$01FD, IRQ vector reads $FFFE/$FFFF, RAM2 acknowledge를 확인한다. 첫 stack write보다 2 cycles 앞을 진입 시작으로 정의한다. 스택의 반환 PC와 status, 단일 IRQ 처리, 실제 입력 파형·tick 간격을 모두 검사한다. RAM3을 INC하고 RAM2에 0을 쓴 뒤 RTI하는 원본 handler를 사용한다.

## 기준 모델

이번 기준은 **Mesen 런타임이 아니라 로컬 소스에서 분리한 사이클 모델**이다. 하드웨어 측정이나 전체 에뮬레이터 동등성으로 표시하지 않는다.

- 기존 로컬 Mesen base: `20ba206cef5ba207c21203176d02cb9f43dda9fb` + emucap 변경.
- `Core/NES/NesCpu.cpp`: EndCpuCycle의 previous/current IRQ 두 단계 갱신, Exec의 명령 종료 검사, IRQ의 dummy read2개 후 stack write를 따른다. SHA256 `94ea2e308ce16342d85e97d87dcd8606ff4e7811cc8ca7c9a014d3a509509196`.
- `Core/NES/NesCpu.h:465`: BranchRelative는 taken branch의 이른 샘플을 복원하고 page-cross에서는 두 유효 샘플의 OR를 보존한다. SHA256 `e28ba272fe39ca61f44ec146f8d5d32f46d05385e819ac2e9aec2f056e61da08`.

검증기 reference()는 RTL 내부 state를 읽지 않는다. instruction별 end-cycle 갱신으로 예상 진입 cycle/return PC를 구한다. 짧은 펄스 26개 중 12개, 유지 입력 26개 모두 IRQ가 발생하고 나머지 짧은 펄스14개는 관측 구간에서 IRQ를 일으키지 않아야 한다. IRQ level/tick/실제 IRQ stack PC 변조 및 trace 절단4종을 거부한다.

## 로컬 변경과 실행

기존 011의 branch bus 수정은 그대로 재사용한다. `nes_branch_irq.py`는 생성된 로컬 T65의 mode00 page-cross branch Cycle_2에서 기존 active-low IRQ_n_o를 현재 IRQ_n과 AND하여 이른 요청을 보존한다. 새 저장 레지스터, instruction cycle 추가, NMI 로직 변경은 없다. 원본 upstream과 이전 driver는 변경하지 않는다. `irq-sampling-fix.diff`에 추가 변경을 남기고 생성된 T65의 실제 hash를 build.json에 기록한다.

수정본은 `run_nes_branch_irq.ps1`을 사용한다. [FLOAT 실행 규칙](questa-execution.md) 및 기존 무료 Starter wrapper를 적용한다. 변수는 설치된 도구/소스의 절대 경로이며 Out은 새 ASCII 경로다.

```powershell
& $PY -B -X utf8 tools/build_nes_branch_irq.py --out "$env:TEMP/nes-irq-rom"
& ./tools/run_nes_branch_irq.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-irq-rtl" -Diagnostic "$env:TEMP/nes-irq-rom"
& $PY -B -X utf8 tools/verify_nes_branch_irq.py --rom "$env:TEMP/nes-irq-rom" --rtl "$env:TEMP/nes-irq-rtl" --out "$env:TEMP/nes-irq-rtl/verification.json"
# 수정 전 기준은 기존 run_nes_branch.ps1 + -Testbench tests/nes-functional/branch_irq_tb.sv
# 기존 011 분기 ROM 회귀
& ./tools/run_nes_branch_irq.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-irq-branch-regression" -Diagnostic $BRANCH_ROM -Testbench tests/nes-functional/branch_tb.sv
& $PY -B -X utf8 tools/verify_nes_branch.py --rom $BRANCH_ROM --rtl "$env:TEMP/nes-irq-branch-regression" --mesen $BRANCH_MESEN --out "$env:TEMP/nes-irq-branch-regression/verification.json"
# 기존 009 MMC3 ROM / 010 기준 참조 회귀
& ./tools/run_nes_branch_irq.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-irq-integrated" -Diagnostic $MMC3_ROM -Mapper4 -Testbench tests/nes-functional/mmc3_irq_phase_tb.sv
& $PY -B -X utf8 tools/verify_nes_mmc3_integrated.py --run "$env:TEMP/nes-irq-integrated" --reference $MMC3_MESEN --rom $MMC3_ROM
& $PY -B -X utf8 tools/verify_nes_branch_regression.py --rtl "$env:TEMP/nes-irq-integrated" --baseline $RTL_010 --mesen $MMC3_MESEN --out "$env:TEMP/nes-irq-integrated/regression.json"
```

모든 opcode의 IRQ, NMI/IRQ 우선순위, CLI/SEI/PLP 경계, RDY/DMA, 16-bit wrap, MMIO, 실제 MMC3 IRQ 전기적 위상, savestate 복구, full fit/STA 및 실기는 미검증이다. BEQ 외 opcode의 IRQ 동작을 자동으로 통과 처리하지 않는다. 기준 모델과 실제 Mesen IRQ 주입 실행도 구분한다. 원시 HDL/ROM/log는 ignored 경로에 보존하고 라이선스 및 서버 로그는 사본에서 제외한다.
