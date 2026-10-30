# NES501 — 렌더링 전환 행의 검증된 raw 복구

2026-10-31. [A1 계획](nes-audit499-plan.json) · [500 원인 분리](nes-capture500-contract.ko.md) · [검증](../analysis/capture501-verification.json) · [PR139](progress/pr-139.md).

## 구현 경계

493에 사용한 489 전체 보드의 70개 입력을 고정하고 `nes_native_planes165.sv`와 `nes_native_frame201.sv`만 교체하는 후보다. ARM·65816·SPI ABI·loader·표시 lease·최종 ACK·VBlank·메뉴 경로는 변경하지 않았다. 배포 선택은 계속493이며 이번 후보의 실기 FPS는 측정하지 않았다.

- PPUMASK의 rendering enable 두 비트가 바뀌면 현재 보이는 행과 다음 행을 기존 raw 저장소로 보낸다. 게임명이나 고정 주사선 예외는 없다. 범위는 보수적으로 잡았으므로 일부 조건에서 raw 행이 하나 더 필요하다.
- 같은 전환이 영향을 주는 BG pending만 취소한다. 전환 범위 밖의 불완전한 low/high와 OBJ 검사는 유지한다. raw 행은 native BG 이벤트 발행을 중단한다.
- 실제 ROM 읽기가 있으면 DATA-valid, CHR 영역, logical/physical 주소의 하위 비트 일치를 계속 검사한다. ROM fault는 PPU CE 없이도 전체 수집을 거부한다.
- **PPU의 high/low load 이름과 ROM 주소의 plane 비트는 서로 다른 조건이다.** 재개 직후 high-load와 정상 low-plane 주소가 겹치는 실제 반례가 있다. raw로 보존하는 행에서는 이 load 순서 불일치를 허용하지만, 실제 logical/physical bus lane 불일치는 허용하지 않는다. native 행의 기존 plane 짝 검사는 그대로다.
- 기존 raw 수집기가 256픽셀 순서와 행 순서·용량을 검증한다. fetch 쪽도 `row_commit`, `row_patched`, 행 식별 정보를 요구하며, 다음 행으로 넘어갈 때 증명이 없으면 새 fetch 오류 bit6으로 거부한다. 최종 frame join에는 raw 세대 일치도 추가했다.
- 부분 raw, 다른 행/세대, 용량 초과와 STOP은 승인되지 않는다. query는 전체 frame 승인 뒤 같은 세대에만 열린다. 기존 7개 보존 행+1개 scratch를 재사용하며 새 framebuffer는 없다.

## 검증 결과

- 최종 `equivalence02`의 정상/전환27조건이 모두 geometry valid로 끝났다. 기존500의24조건 중 거부되던9조건이 모두 복구됐다. 추가로 capture 시작, 마지막 raw 행, dot0 근처 재개를 검사했다.
- raw 픽셀15,360개와 raw 밖 native 이벤트197,604개가 정확히 일치했다. native 이벤트는 X값, 개수, 순서, 64bit 내용까지 검사했다.
- 최종 `guards04`의12반례: 잘못된 CHR 영역, DATA-invalid, byte lane, ROM fault, 누락 픽셀, 다른 행, raw 완료 통지 누락, 세대 불일치, 용량 초과, STOP, 전환 밖 high 누락, logical/physical plane lane 불일치를 모두 거부했다.
- 조기 query와 잘못된 세대의 query는 hit를 내지 않았고, 정상 완료 후 같은 세대의 query만 허용했다. STOP 뒤 각 수집 멤버의 active/owned가 해제됐다.
- 제품에 설치하지 않은 후보 검증이며 A1 전체 완료나 새 실기 FPS를 뜻하지 않는다.

실제493 PPU와 수집기를 실행하되 외부 VRAM은 결정적 always-ready 응답이다. 기존179의 PPUMASK/선택적2006 기록과 위상 변화를 재생했다. CPU/MMC3/PSRAM·실제 ARM/IRQ/공유SPI·게임 전체를 실행한 시험이 아니다. OAM은 비어 있는 fixture이며 모든 실기 거부 episode의 원인을 증명한 것도 아니다.

raw RAM의 픽셀은 같은 PPU의 별도 post-CE 관측기와 비교한다. 기존 planes와 후보 planes를 같은 PPU에 연결하고, raw로 바꾸지 않은 행의 모든 64bit native 이벤트를 순서·개수까지 정확히 비교한다. 이중 관측기의 이벤트 배열은 시험용이며 보드 합성 입력에 포함되지 않는다. 이는 독립 NES emulator의 전체 장면이나 실제65816 출력 픽셀 검증과 다르다.

## 전체 비용과 처리 시간

| 항목 | 실기493 기준 | 501 후보 | 차이 |
|---|---:|---:|---:|
| LE | 15,272 | 15,308 | +36; 잔여100 |
| 조합 논리 | 14,078 | 14,133 | +55 |
| FF | 8,392 | 8,399 | +7 |
| 논리 RAM bit | 264,800 | 264,816 | +16 |
| M9K | 51 | 51 | 동일; 잔여5 |
| implementation 관련 setup/hold | +0.183/+0.168ns | +0.077/+0.145ns | 양수, 여유 감소 |
| nominal 관련 setup/hold | +0.224/+0.168ns | +0.077/+0.145ns | 양수, 여유 감소 |

같은493 보드 경계의 Lite 전체 FIT와 기존 제약의 두 timing view를 통과했다. 새 timing 예외나 seed 변경은 없다. map/FIT/STA의 warning ID별 개수는 기준과 같으며, 이것이 미해결 reset/CDC/외부 IO 조건의 sign-off를 뜻하지는 않는다. ARM·65816 바이너리는 변경하지 않아 추가 Flash/static RAM은0이다. 실행량·SPI·IRQ 시간은 raw 개수에 따라 달라질 수 있다.

LE는 배치·packing 결과를 포함하므로 조합 논리·FF 증감과 별도로 기록한다. bit6이 실제 신호가 되면서 기존 history RAM의 최적화된 폭이 90에서91bit로 늘어난 것이 RAM16bit 증가의 원인이다. raw 저장소의 행 용량은 늘리지 않았다.

복구 전에는 거부되던 프레임을 승인할 수 있게 된 정확성 수정이다. 일부 정상 조건도 raw 보존이 2행에서3행으로 늘어 256픽셀을 더 처리한다. 이를 256 SPI byte라고 단정하지 않는다. 실제493 `nes_native_sink165.c`는 `patch_count<=2`일 때만 `3×행수×32×2`바이트를 모으고, 3행부터는 전체2,048바이트 CHR을 `span`에 넘긴다. 따라서2행384바이트에서3행2,048바이트로 전송 전 배열 크기가 바뀌는 분기점을 넘는다. `span`의 RLE·packet·상태 대기가 있으므로1,664바이트를 실제SPI 증가량으로 계산하지 않는다. 이 경계는 A1 후속의 우선 검토 사항이다.

압축·history reuse·출력 DMA 비용과 수집 거부 감소가 합쳐진 최종 시간은 아직 미측정이다. 실기493 평균9.57fps를 새 속도로 갱신하지 않는다.

## 중간 실패와 재현

- test01/guards01은 초기 제한 조건을 통과했지만 프레임 시작과 rendering 전환이 겹치는 조건을 보완하기 전 버전이다.
- guards02의 처음10개 반례는 통과했다. 추가 high 누락 반례는 rendering-off 이후 시각에 잘못 배치해 실제 high를 제거하지 못했다. 이 실패를 보존하고 guards03부터 실제 high 발생 시각으로 수정하고 제거 횟수1을 확인했다.
- test03은 기존24조건과 시작/마지막행/행 전환 경계27조건을 검사했다.699/+1dot 두 조건에서 정상 low-plane ROM 주소와 high-load 이름의 불일치를 여전히 거부했다. board01은 FIT/관련 timing을 통과했어도 이 기능 실패 때문에 채택하지 않았다. 수정된 RTL에 대해 새 전체 build를 한 이유는 이 실제 기능 변경이며 seed 변경이나 동일 회로 반복이 아니다.
- 최종 선택은 `equivalence02`/`guards04`/`board02`다. test03·board01의 실패와 비용을 보존했다. 공개 generator가 최종27조건의 source/testbench/입력 manifest를 정확히 재생성하는 것도 `reproduce01`에서 확인했다. 원시 입력·동작 로그·board 보고서는 작업공간 `probes/nes-capture501/evidence`와 `archive01.json`/`archive02.json`에 보존한다. 이 비공개 보존본은 clone에 포함되지 않는다.

`tools/test_nes_capture501.py prepare/run`은500의 고정 입력과 raw 관측기를 재사용한다. `--guards`는 반례, `--guard-list`는 특정 반례를 선택한다. `tools/test_nes_capture501_equivalence.py`는 기존 planes를 함께 실행한다. `tools/prepare_nes_capture501_board.py`는493 입력 hash 확인 후 두 파일만 교체한다. `tools/analyze_nes_capture501.py`가 입력·로그·whole board 일치와 결과를 재검증한다. Questa는 기존 Starter FLOAT 한 좌석에서 순차 실행했고 Quartus는 Lite만 사용했다.

## 다음 순서

A1은 전체 완료로 표시하지 않는다. 먼저 불필요한 세 번째 raw 행을 줄이는 소유권 범위와 기존 compact/full CHR 분기를 비교한다. 실제로 필요한 raw 행을 누락하거나 개수를 강제로2로 제한하지 않는다. 이 후보의 raw descriptor·payload를 실제493 source/ARM 복원·planner·65816 소비와 연결해 추가 행의 처리 비용과 최종 픽셀/검사를 확인해야 한다. 그 뒤 같은 장면의 실기 거부·표시 간격으로 판단한다. 기존 STOP·최종 ACK·VBlank·메뉴는 변경하지 않았지만 이번 수정본의 실기 재검증은 별도다.

A2의 구조 예산에는 복구된 프레임의 새 raw 비용을 포함한다. 단독 status/FSM 최적화나498 승격으로 건너뛰지 않는다. 전체 reset/CDC/외부 IO sign-off, 실제 ROM 경쟁 및 MMC4/5 일반화도 이번 제한 시험의 성과로 주장하지 않는다.
