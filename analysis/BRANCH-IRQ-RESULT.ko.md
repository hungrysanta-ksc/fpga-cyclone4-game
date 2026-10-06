# NES-P2-BRANCH-IRQ-012 — 분기 중 이른 IRQ 요청 보존

2026-10-05. **페이지 경계 분기의 첫 사이클에 들어온 1-cycle IRQ 펄스를 놓치는 두 사례를 재현하고 로컬 T65 사본에서 수정했다.** 자체 RTL 진단 52개가 Mesen 소스에서 분리한 사이클 모델과 일치한다. 이번 비교는 Mesen 런타임이나 실기 측정이 아니다.

| 시나리오 | 개수 | 수정 전 | 수정 후 |
|---|---:|---|---|
| 처리까지 유지한 IRQ | 26 | 모델 일치 | 일치 |
| 받아야 하는 짧은 펄스 | 12 | page-cross 앞/뒤 2개 놓침 | 12개 처리 |
| 관측 구간에서 무시되는 짧은 펄스 | 14 | 모델 일치 | 14개 무시 |

BEQ 조건 불성립, 같은 페이지 앞/뒤, 페이지 경계 앞/뒤의 5종에 opcode cycle0부터 분기 종료 후 두 번째 cycle까지 입력을 이동했다. IRQ는 CPU enable edge 직전 negedge에서 바꾸고 실제 pin level을 함께 기록했다. 스택의 return PC/status, 진입 상대 cycle, vector read 및 acknowledge를 검사했다. 모델이 요구하는 38개 IRQ 처리와 14개 미처리가 모두 일치한다.

기존 T65는 page-cross branch의 이른 IRQ 샘플을 뒤의 비활성 샘플로 덮어썼다. 로컬 수정은 해당 Cycle_2에서 기존 active-low IRQ latch와 현재 입력을 AND하여 둘 중 한 요청을 보존한다. 추가 state나 instruction cycle은 없다. 011의 discarded-read 주소 수정도 유지한다. IRQ/NMI/RDY 전체 동작을 이 결과만으로 일반화하지 않는다.

## 회귀 및 검증기 확인

- 기존 8 opcode × 7 조건의 분기 버스 56개 회귀 통과. Mesen 런타임 참조는 이 기존 분기 버스 회귀에만 재사용했다.
- 수정본 Mapper4 full-wrapper 실제 RTL 140.02ms 통과. 전체 4프레임 245,760화소 및 화소 사용 CHR fetch 61,440건 일치, BG latch 65,552건 검사, PRG/CPU period/미정 bus 오류 0, IRQ service 6회.
- frame/fetch/control/edges 8개 파일이 010 최종 기록과 SHA256 일치한다. IRQ bus landmark의 상대 cycles와 기존 4-dot offset도 유지되며 첫 stack write→ack는 18 CPU cycles다. polling loop discarded-read9건도 Mesen 주소/값과 일치한다.
- 실제 실행 모두 오류 0, 기존 경고42개. IRQ level·tick·IRQ stack PC·절단4종 변조 검출 통과. 기존 분기5종 변조 검출도 통과.
- 최초 stack PC 변조 시험은 setup PHA를 골라 수정본에서 실패 검출을 못 했다. IRQ 관측 구간의 실제 stack write를 선택하도록 검증기만 고쳤으며 이전 검증기와 그 실패 결과를 baseline에 보존했다. 최종 검증기로 수정 전 실제 오류2개도 재확인했다.

## 재현과 보존

원본 진단 ROM SHA256은 `3803440863e3b92d66ac1d1b377b2a8e35a36998b5e2a667e489e4aec2a4fa43`이다. [관측 계약·재현](../docs/nes-branch-irq-contract.md), [검증 JSON](branch-irq-verification.json), [해시 목록](branch-irq-artifacts.json)을 따른다. 수정본 실행 진입점은 `tools/run_nes_branch_irq.ps1`이며 Mapper4 회귀에는 `-Mapper4`를 사용한다. 과거 011 및 이전 driver는 원래 결과 재현용으로 그대로 남긴다.

ignored `analysis/local-branch-irq-012/`에 rom-01, 수정 전 rtl-01, 수정 후 rtl-02, branch-regression-01, integrated-01 및 baseline/baseline-status를 보존했다. 원본 upstream은 수정하지 않았고 생성 HDL은 라이선스 고지와 함께 로컬 증거에만 둔다. 직전 011의 source/status/evidence225개 및 이전 각 단계 source/원래 draft의 hash를 확인했다. GBC152 source hashes·Quartus 입력·2,048 boot bytes 검사도 통과했다.

기존 무료 FLOAT workflow를 사용했고 실행 종료 후 simulation/license process와 18000–18002 listener가 0개다. 새 라이선스·영구 환경변수/서비스 변경은 없다. 라이선스 파일·서버 로그는 Git 및 증거 사본에서 제외한다.

다음은 NMI와 IRQ가 겹치는 경우의 우선순위·분기 경계 관측이다. RDY/DMA stall, 모든 opcode의 IRQ, CLI/SEI/PLP 경계, savestate 복구, 전체 CPU/PPU/APU, NES→SNES 통합, full fit/STA, 지정 일본판 SMB3 및 실기는 미완료다. 240→239/224줄 정책과 upstream license hold도 유지한다. GBC C44 / sd2snesHST 0.9.0 및 공통 제품 MCU/FPGA는 변경하지 않았다.
