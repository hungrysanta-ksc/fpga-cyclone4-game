# NES-P2-INTERRUPT-PRIORITY-013 — NMI/IRQ 우선순위 확인

2026-10-05. **자체 NMI/IRQ 중첩 진단 42개가 제한된 소스 기반 기준과 일치했다.** 조건 불성립·같은 페이지·페이지 경계의 BEQ에서 IRQ 유지 중 NMI 도착 시점을 이동했고, IRQ-only/NMI-only 및 IRQ 마스크 시나리오를 포함했다. 기존 012 코어를 그대로 사용했으며 이번에 코어 수정은 없었다.

| 실제 처리 순서 | 시나리오 수 |
|---|---:|
| NMI → 남아 있던 IRQ | 21 |
| IRQ → NMI | 12 |
| IRQ만 | 3 |
| NMI만(IRQ 없음 또는 마스크) | 6 |

총 IRQ handler36회/NMI handler39회를 vector read, RAM INC old/new write와 acknowledge 횟수로 확인했다. 최초 stack의 return PC/status와 2/3/4-cycle 분기 뒤 진입 시점도 일치한다. NMI handler는 IRQ를 해제하지 않으므로 pending IRQ가 이후 처리되는 것을 별도로 확인할 수 있다. IRQ mask가 NMI까지 막지 않는 조건도 포함했다.

NMI는 2 CPU-cycle 펄스이고 IRQ는 handler acknowledge까지 유지한다. 첫 vector 선택 이전에 들어온 NMI와 그 이후 도착한 NMI를 구분했다. 기준은 로컬 Mesen NesCpu.cpp IRQ()/EndCpuCycle에서 도출한 bounded oracle이며 **실제 Mesen 런타임 비교나 하드웨어 측정은 아니다.** 임의의 IRQ/NMI edge timing이나 모든 CPU instruction으로 결과를 확장하지 않는다.

## 실행과 실패 검출

Questa 실제 실행 완료, 오류0/기존 경고42개, CPU period/미정 bus 오류0. NMI 입력·IRQ 입력·vector·return PC 변조, vector 누락, trace 절단6종을 모두 거부했다. 원본 ROM SHA256은 `ef3580d8c063e4285f408367df7826f1d37ceb2f606f60747dbdf436c896527a`다.

컴파일된 T65 SHA256 `c7c8647f6293f6ea7a949892f8e666341ba23426167ae6c3d0d83a55ca00d065`가 012와 동일하다. 직전 단계의 source/status/evidence199개 해시와 원래 실험 draft를 확인했다. 이전 branch56/MMC3 140.02ms 회귀 결과는 보존된 012의 결과이며 이번에 새로 실행하지 않았다.

[관측 계약·재현](../docs/nes-interrupt-priority-contract.md), [검증 JSON](interrupt-priority-verification.json), [해시 목록](interrupt-priority-artifacts.json)을 함께 사용한다. ignored `analysis/local-interrupt-priority-013/{rom-01,rtl-01,baseline-status}`에 원시 기록과 이전 상태를 보존했다. 기존 무료 FLOAT workflow 종료 후 관련 process/listener는0개이며 새 라이선스나 영구 설정 변경은 없다.

GBC152 source hashes·Quartus 입력·2,048 boot bytes 검증 PASS, pinned upstream clean. GBC C44/sd2snesHST0.9.0 및 공통 MCU/FPGA를 보존했다. 생성된 외부 HDL의 라이선스 고지와 개별 license hold도 유지한다.

다음은 RDY에 의한 CPU 정지·재개 시 bus/interrupt 보존을 확인하는 것이다. 1-cycle NMI와 반복 edge, BRK hijack, 다른 opcode와 상태복원도 별도 관문으로 남는다. 전체 CPU/PPU/APU, NES→SNES 통합, full fit/STA, 지정 일본판 SMB3 및 실기는 미완료이며 240→239/224줄 정책도 승인되지 않았다.
