# NES-P2-OAM-DMA-015 — 실제 OAM DMA와 CPU 복귀 확인

2026-10-05. **CPU가 `$4014`로 시작한 실제 OAM DMA16개가 실제 Mesen 실행과 일치했다.** 총4,096 source bytes의 read/write8,192개와 OAM snapshot4,096바이트를 검사했다. 코어 변경은 없으며 RDY-014의 컴파일 소스 inventory가 동일하다.

| 조건 | 결과 |
|---|---|
| source pages0200/0300 × OAM start00/01/FC/FF × 두 위상 | 16개 통과 |
| 각 page/start에서 CPU pause | 513/514 cycles 모두 확인 |
| 실제 DMA read256 → write256 | 주소·값·순서·상대 cycle 일치 |
| OAM 순환/attribute mask | RTL·Mesen·ROM 기대값 일치 |
| DMA 종료 후 CPU 복귀 | 다음 INC1회, RAM10의1..16 증가 확인 |
| data/address/tick/pause/OAM/누락/절단 | 변조7종 거부 |

처음 실행한 ROM은 첫 page/start 쌍에서 같은514-cycle 위상을 두 번 사용했다. 데이터 전송은 맞았으나 최종 verifier는 `phase_coverage` 실패로 거부했다. 초기3-cycle padding을 추가한 최종 ROM은 모든8개 page/start 조합에서 두 위상을 모두 자극한다. 초기 입력과 RTL/Mesen 기록을 삭제하지 않고 보존했다.

최초 verifier 실행은 snapshot 변수 `re`와 regex module 이름이 겹쳐 검증 전에 중지됐다. 변수명을 고친 뒤 같은 원시 trace를 검증했고, 이전 verifier와 실패 설명도 baseline에 남겼다. 이를 simulator/core 실패로 분류하지 않는다.

## 증거와 범위

최종 원본 ROM SHA256: `f409a4462b0b9f4b13bae018ad0084955735244a110ce48fba76f7e273ecc92a`. 실제 RTL 실행 두 번 모두 simulation 오류0/기존 경고42개, CPU period/미정 bus 오류0. 최종 기능/coverage 검증은 두 번째 ROM/실행을 기준으로 한다. 같은 ROM을 Mesen testRunner로 실제 실행했으며 callback clock은 `$4014` write 기준 상대 cycle로만 비교했다.

[재현·관측 계약](../docs/nes-oam-dma-contract.md), [검증 JSON](oam-dma-verification.json), [해시 목록](oam-dma-artifacts.json)을 따른다. ignored `analysis/local-oam-dma-015/{rom-01,rom-02,rtl-01,rtl-02,mesen-01,mesen-02,baseline,baseline-status}`에 모든 입력·실행과 이전 상태를 보존했다.

직전014 source/status/evidence245개 hash와 원래 draft를 확인했다. 전체 compiled source inventory와 T65가014와 동일하다. 기존014의 IRQ/NMI/영상 회귀 기록은 보존된 결과이며 이번에 새로 실행하지 않았다. GBC152 source hashes·Quartus 입력·2,048 boot bytes PASS, pinned upstream clean. 무료 FLOAT 종료 후 simulation/license process 및18000–18002 listener0개이며 라이선스/서버 로그는 증거 사본과 Git에서 제외했다.

다음은 실제 OAM DMA 도중 IRQ/NMI가 도착했을 때의 처리와 CPU 복귀 검증이다. DMC/OAM DMA 경쟁, rendering 중 쓰기, RMW trigger, 외부 memory stall/MMIO, 전체 CPU/PPU/APU, NES→SNES 통합, full fit/STA, 지정 일본판 SMB3 및 실기는 미완료다. GBC C44/sd2snesHST0.9.0·공통 MCU/FPGA·상용 ROM을 보존하며 화면 crop 정책과 upstream license hold도 유지한다.
