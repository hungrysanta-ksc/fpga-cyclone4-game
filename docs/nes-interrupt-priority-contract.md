# NES NMI/IRQ 우선순위 진단 계약

SPDX-License-Identifier: MIT.

기존 BRANCH-IRQ-012의 로컬 코어 사본을 그대로 사용한다. 변경은 자체 ROM 생성기, testbench 및 검증기뿐이다. mapper_irq와 PPU nmi net을 testbench에서 force해 합성 입력을 넣는다. 실제 PPU vblank나 MMC3 A12가 발생시키는 인터럽트 시험은 아니다.

## 42개 시나리오

BEQ 조건 불성립(2 cycles), 같은 페이지 앞 분기(3), 페이지 경계 앞 분기(4)마다 다음 14개를 실행한다.

- IRQ만 활성화 1개.
- opcode cycle0부터 유지하는 IRQ에 NMI 시작을 cycle0..10으로 이동한 11개.
- NMI만 cycle0에 넣는 1개.
- IRQ mask(I=1)와 두 입력을 함께 활성화하는 1개.

NMI는 항상 CPU 2-cycle 폭, IRQ는 handler의 RAM2 acknowledge까지 유지한다. 입력은 cpu_ce posedge 직전 master-clock negedge에 변경한다. CPU 관측은 12 master ticks마다 cpu_ce에서 tick/address/read/data/case/step/IRQ/NMI를 기록한다. branch 이후 NOP6개와 SEI를 실행한 뒤 다음 case로 넘어간다. IRQ vector는 FB00, NMI vector는 FC00으로 분리한다. IRQ handler는 RAM3 INC 및 RAM2 acknowledge, NMI handler는 RAM4 INC를 수행한다. NMI handler는 IRQ를 해제하지 않는다.

## 기준과 확인 범위

로컬 Mesen의 NesCpu.cpp IRQ()/EndCpuCycle을 근거로 만든 제한된 벡터 선택 oracle을 사용한다. **Mesen 런타임 IRQ 주입이나 하드웨어 측정이 아니다.** 기존 base `20ba206cef5ba207c21203176d02cb9f43dda9fb` + emucap 변경, NesCpu.cpp SHA256 `94ea2e308ce16342d85e97d87dcd8606ff4e7811cc8ca7c9a014d3a509509196`을 기준으로 한다.

IRQ()는 dummy read2개와 PC stack write2개 뒤 NMI pending을 검사하여 vector를 선택한다. 이 시험처럼 IRQ가 branch cycle0부터 유지되는 경우 최초 진입은 branch length L, 첫 stack write는 L+2, 첫 vector low read는 L+5다. NMI edge가 L+3까지 관측되면 첫 vector는 NMI, 이후라면 IRQ로 예상한다. NMI-only 및 masked-IRQ 시나리오는 NMI가 cycle0부터 들어오도록 고정한다. 이 제한 밖의 임의 프로그램이나 모든 interrupt phase에 이 공식을 적용하지 않는다.

다음을 모두 만족해야 한다: 실제 입력 파형, CPU tick 간격, 첫 return PC/status/stack 주소, 최초 진입 cycle, vector low/high 주소·값, vector 순서, 두 handler의 INC old/new write 횟수, IRQ acknowledge 횟수. IRQ가 NMI 처리 뒤까지 pending으로 유지되는 것도 관측한다. 두 번째 진입의 전체 microcycle 동등성은 검사 범위가 아니다. NMI/IRQ 입력, vector, return PC, vector 누락, trace 절단6종 변조를 거부해야 한다.

## 재현

[기존 FLOAT 규칙](questa-execution.md)을 적용한다. 변수는 설치된 Python/Questa/upstream/승인된 FLOAT wrapper 절대 경로다. 각 Out은 새 ASCII 경로여야 한다. 별도 라이선스 smoke는 반복하지 않는다.

```powershell
& $PY -B -X utf8 tools/build_nes_interrupt_priority.py --out "$env:TEMP/nes-priority-rom"
& ./tools/run_nes_branch_irq.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-priority-rtl" -Diagnostic "$env:TEMP/nes-priority-rom" -Testbench tests/nes-functional/interrupt_priority_tb.sv
& $PY -B -X utf8 tools/verify_nes_interrupt_priority.py --rom "$env:TEMP/nes-priority-rom" --rtl "$env:TEMP/nes-priority-rtl" --out "$env:TEMP/nes-priority-rtl/verification.json"
```

build.json의 implementation candidate는 기존 012이고 진단 결과는 013이다. 소스 고정 및 과거 재현 때문에 기존 runner를 바꾸지 않는다. 새 코어 수정이 없으므로 기존 012의 branch56/MMC3 회귀를 이번에 새로 실행한 것으로 표시하지 않는다. 원시 입력/HDL/log는 ignored 경로에 보존하고 라이선스 및 임시 서버 로그는 제외한다.

1-cycle NMI, 다른 opcode, branch backward에서의 NMI, 반복 edge, BRK vector hijack, CLI/SEI/PLP 경계, RDY/DMA, savestate 복구, 전체 CPU/PPU/APU, 실기/fit/STA는 미검증이다. 이번의 NMI 우선순위 결과를 전체 NMI sampling 정확성으로 일반화하지 않는다.
