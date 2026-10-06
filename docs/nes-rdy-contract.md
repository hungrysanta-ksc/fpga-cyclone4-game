# NES RDY 정지·재개 진단 계약

SPDX-License-Identifier: MIT.

자체 NROM에서 memory-read/write/RMW 7개 위치, 같은 페이지 BEQ의 3 cycles, 페이지 경계 BEQ의 4 cycles를 선택한다. 각 위치에 interrupt 없음/held IRQ/1-cycle NMI/두 입력 동시의 4조건을 조합해 56개다. 동일 ROM을 cold reset하여 두 번 실행한다. pass0은 RDY high와 interrupt 없음, pass1은 각 선택 위치부터 CPU 3-cycle RDY low 및 해당 interrupt 자극이다. 총 112개 case completion을 요구한다.

## 자극과 관측

`rdy_tb.sv`는 `pause_cpu`, `mapper_irq`, `nmi`를 시험용으로 force한다. cpu_ce 직전 master-clock negedge에 입력을 바꾸고 posedge에서 bus/RDY/IRQ/NMI를 기록한다. 기존 CPU enable 주기는 12 master ticks로 유지한다. 실제 DMA 엔진이나 외부 memory latency를 발생시키는 시험은 아니다. 외부 memory는 기존 ideal memory다.

메모리 프로그램은 `LDA $10; STA $11; INC $12`다. 초기 RAM10=5A, RAM11=00, RAM12=07을 설정하고 종료 값 5A/5A/08을 두 pass 모두에서 검사한다. 정지 시작 위치는 opcode, operand, data-read, STA write, INC read/old-write/new-write다. branch 조건은 Z=1로 고정한다. branch 목적지에서 같은 메모리 프로그램과 NOP6개, SEI, case completion marker를 실행한다.

IRQ/NMI는 3-cycle 정지 창의 두 번째 cycle에 활성화한다. IRQ는 handler의 RAM2 acknowledge까지 유지하고, NMI는 1 CPU cycle 뒤 해제한다. IRQ vector=FB00, NMI vector=FC00이다. 각각 RAM3/RAM4 INC로 처리 횟수를 확인한다. NMI handler는 pending IRQ를 해제하지 않는다.

## 비교 조건

RDY low이며 read인 CPU edge에서 다음 CPU edge까지 주소/RW/data가 유지되어야 한다. write는 RDY low여도 완료된다. 정지 창 총168 CPU cycles 중 blocked read152개와 unblocked write16개를 실제 기록에서 확인한다. Interrupt 없는 14조건은 blocked read 행만 제거한 전체 bus sequence가 pass0과 같아야 한다. 코드 범위는 anchor opcode부터 completion write까지다.

각 pass/case의 RAM 결과, 정확한 input waveform, CPU tick/relative step, IRQ/NMI vector pair 및 handler INC old/new write, acknowledge 횟수를 검사한다. pass0은 interrupt0개, pass1은 각 mode에 맞게 IRQ/NMI가 각각0 또는1회 처리되어야 한다. IRQ28회 및 NMI28회를 기대한다. 정지 중 NMI가 들어온 경우 재개 뒤 사라지거나 중복 처리되면 실패다. 이 검사는 정확한 interrupt acceptance microcycle 또는 Mesen runtime 동등성의 증명은 아니다.

주소·data·RDY·NMI·vector 변조, RAM snapshot 변조 및 trace 절단7종을 거부한다. baseline과 수정본 모두 같은 최종 verifier를 사용하며 수정 전 실패를 통과로 바꾸지 않는다.

## 국소 변경

기존 012의 CPU mode00 branch IRQ latch 및 011 branch bus 수정은 유지한다. 기존 T65는 branch operand cycle에서 NMI_n_o 샘플링과 NMIAct edge 감지를 모두 막는다. RDY low로 이 cycle이 반복되는 동안 짧은 NMI가 시작·종료하면 요청이 없어지는 현상을 baseline에서 재현했다.

`nes_rdy.py`는 생성된 사본의 두 조건에만 `(Mode_r = "00" and really_rdy = '0')` 예외를 추가한다. read stall 중 edge를 저장하는 조건이며 실행 중 branch의 기존 NMI 지연 조건과 다른 CPU mode는 보존한다. 새 register/savestate field나 instruction cycle은 없다. 원본 upstream 및 기존 driver는 수정하지 않는다. patch 전 CPU012 hash를 고정하고 `rdy-nmi-fix.diff`와 최종 compiled hash를 저장한다.

최신 실행 진입점은 `tools/run_nes_rdy.ps1`이다. [FLOAT 규칙](questa-execution.md)을 사용하며 기존 wrapper와 무료 Starter entitlement를 재사용한다. 변수는 설치된 도구/소스의 절대 경로, Out은 새 ASCII 경로다. 새 변환 도구는 시뮬레이터 실행 전에 Python syntax를 검사한다.

```powershell
& $PY -B -X utf8 -c "import ast,pathlib; ast.parse(pathlib.Path('tools/nes_rdy.py').read_text())"
& $PY -B -X utf8 tools/build_nes_rdy.py --out "$env:TEMP/nes-rdy-rom"
& ./tools/run_nes_rdy.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-rdy-rtl" -Diagnostic "$env:TEMP/nes-rdy-rom"
& $PY -B -X utf8 tools/verify_nes_rdy.py --rom "$env:TEMP/nes-rdy-rom" --rtl "$env:TEMP/nes-rdy-rtl" --out "$env:TEMP/nes-rdy-rtl/verification.json"
```

수정 전 baseline은 기존 `run_nes_branch_irq.ps1`에 `-Testbench tests/nes-functional/rdy_tb.sv`를 지정한다. 회귀는 새 runner에 기존 priority013/branch-IRQ012/Mapper4 ROM과 해당 testbench를 명시하고 각 기존 verifier로 확인한다. Mapper4에는 `-Mapper4`를 지정한다. 원시 trace/hash를 기존 결과와 비교하여 unpaused 실행이 바뀌지 않았는지 확인한다.

실제 OAM/DMC DMA·memory arbitration·MMIO side effects·임의 길이 또는 반복 RDY·정지 밖의1-cycle NMI·BRK hijack·상태복원·전체 CPU/PPU/APU·fit/STA·실기는 미검증이다. synthetic RDY 검증을 actual DMA 통과로 취급하지 않는다. 라이선스/임시 서버 로그는 Git 및 raw evidence 사본에서 제외하고 원본 HDL 고지와 개별 license hold를 보존한다.
