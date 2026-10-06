# NES-P2-RDY-014 — 정지 중 분기 NMI 요청 보존

2026-10-05. **분기 피연산자를 읽다가 RDY로 멈춘 동안 짧은 NMI를 놓치는 네 조합을 재현하고 로컬 T65 사본에서 수정했다.** 기준 실행56개와 RDY 정지 실행56개, 총112개 completion을 검사했다. 수정 후 모든 조건이 통과했다.

| 검사 | 결과 |
|---|---|
| 14개 위치 × interrupt 없음/IRQ/NMI/동시 입력 | 56조건 통과 |
| RDY low 168 CPU cycles | read152개 정지, write16개 진행 |
| interrupt 없는14조건 | 정지 read를 제거한 bus sequence가 기준 실행과 동일 |
| 모든112개 completion의 RAM10/11/12 | 5A/5A/08 일치 |
| 정지 중 입력된 interrupt | IRQ28회, NMI28회 처리 |
| 주소/data/RDY/NMI/vector/snapshot/절단 변조 | 7종 거부 |

기존 코어는 같은 페이지 및 page-cross BEQ의 operand cycle에서 NMI 감지를 지연한다. RDY low로 해당 cycle이 반복되는 동안 NMI가 활성화됐다 사라지면 pending edge가 남지 않았다. NMI-only 및 IRQ+NMI 각각2개, case35/36/47/48에서 누락을 확인했다. 읽기 정지·쓰기 진행 및 최종 RAM 값은 수정 전부터 맞았으며 실패 범위를 NMI 보존과 구분했다.

수정은 mode00의 실제 read stall(`really_rdy=0`) 동안 NMI_n_o 샘플링과 NMIAct edge 감지에 예외를 주는 두 조건뿐이다. 기존 저장 레지스터를 사용하며 새로운 state나 instruction cycle을 추가하지 않는다. 실행 중 분기의 기존 NMI 조건과 다른 CPU mode는 변경하지 않는다. 정지 밖의 짧은 NMI까지 완료했다고 선언하지 않는다.

## 회귀와 보존

- 기존 013 NMI/IRQ42개, 012 branch IRQ52개를 수정본으로 실제 재실행해 통과했다. 두 원시 interrupt trace는 이전 통과 기록과 SHA256으로 동일하다.
- Mapper4 140.02ms 실제 RTL 및 검증 통과. 4프레임 245,760화소·화소 사용 CHR fetch61,440건 일치, BG latch65,552건 검사. PRG/CPU period/미정 bus 오류0, IRQ service6회.
- frame/fetch/control/edges8개가 010 최종본과 동일하다. IRQ 상대 cycles 및 4-dot 관측 offset, 수정된 polling discarded-read9개도 유지된다.
- 실제 실행 모두 오류0/기존 경고42개. driver 문자열 인용 오류로 중지한 launcher02는 컴파일/시뮬레이션 전 실패이며 성공 실행으로 세지 않았다. 잘못된 소스와 원인을 baseline에 보존했다. 수정 후 syntax를 검사했고 최종 wrapper에도 라이선스 서버 시작 전 syntax 검사를 추가했다.

자체 ROM SHA256: `1eb2b2208b2e90a4b75e3d7f6f0d09f8d286e2963bdc5fd9af9cf5ec52470565`. [재현·관측 계약](../docs/nes-rdy-contract.md), [검증 JSON](rdy-verification.json), [해시 목록](rdy-artifacts.json)을 따른다. 최신 실행 경로는 `tools/run_nes_rdy.ps1`이고 Mapper4에는 `-Mapper4`를 지정한다. 과거 driver는 원래 결과 재현용으로 보존했다.

ignored `analysis/local-rdy-014/`에 rom-01, 수정 전 rtl-01, 수정 후 rtl-03, priority-01, irq-01, integrated-01과 baseline/baseline-status를 보존했다. 직전013의60개 hash 및 이전 각 단계 source/원래 draft를 확인했다. GBC152 source hashes·Quartus 입력·2,048 boot bytes PASS, upstream clean. GBC C44/sd2snesHST0.9.0과 공통 MCU/FPGA는 변경하지 않았다. 기존 무료 FLOAT 종료 후 simulation/license process 및 18000–18002 listener0개, 라이선스/서버 로그는 증거 사본과 Git에서 제외했다.

다음은 실제 `$4014` OAM DMA의 256-byte 전송과 CPU 복귀 검증이다. 이번은 시험용 RDY·IRQ·NMI 입력이며 실제 DMA/bus arbitration, 외부 memory stall protocol, MMIO 부작용, 임의 RDY 길이, 반복 NMI, 상태복원, 전체 CPU/PPU/APU, NES→SNES 통합, full fit/STA, 지정 일본판 SMB3 및 실기는 미완료다. 화면 crop 정책과 upstream license hold도 유지한다.
