# NES288 — workset 검색 후보와 출력 시작 장벽 검토

NES288 workset 후보는 미채택: 실제 ARM71 plan/metadata 일치, 정상·제한 ROM3씩과 오류/STOP/IRQ/H2 검사 PASS. planner954 -0.429738ms지만907 +0.363738ms, live907 14.885003ms(+0.363723), 제한907 18.727048ms(+0.000000). ARM RAM+2048B, 동일 RTL287이므로 FPGA 절감0; 2263comb 부족 유지. 현재 통합 비교 기준은 NES287이며288의71프레임 전체 재일정/새MAP/FIT/STA/fullRUN은 없다.

## 검증한 변경

NES287의 actual row planner에서 각 BG/OBJ/exception의 tile membership 이진검색을2bit/tag workset으로 바꿨다. geometry 단계에서 tag 범위, kind와 strictly increasing 순서를 독립 검사한 뒤 bitmap을 초기화하고 재구성한다. 이전 frame의 검색표나 caller의 required bitmap을 신뢰하지 않는다. row 재사용도 membership을 확인하여 retained map만으로 누락 BG를 통과시키지 않는다. 순서·slot 배정·원본 E1/E9·8570B metadata·H2·CRC/receipt 프로토콜은 그대로다.

첫 arm01은 required[]를 재사용했다가 실패했다. required[2048]와 raw_pixels[2048]는 union이므로 input COMMITTED의 raw 복사가 검색표를 덮어썼다. BG keys[1024]와 patch CHR/HDMA도 union이어서 raw 변환을 무조건 앞으로 옮기는 대안도 유효하지 않다. 이 실패는 보존했다. 최종 후보는 별도 ARM workset2048B를 사용한다. arm02는 row 재사용 membership 보강 전 중간71PASS이며 최종 선택은arm03이다. 추가RAM이 없는 후보라고 주장하지 않는다.

## 비용 비교

| 항목 | NES287 | NES288 | 변화 |
|---|---:|---:|---:|
| 실제 M4 planner907 |5.713560ms|6.077298ms|+0.363738ms|
| 실제 M4 planner954 |10.503679ms|10.073940ms|-0.429738ms|
| 실제 M4 planner970 |10.570536ms|10.105381ms|-0.465155ms|
| 일반907 진단 전체 일정 |14.521280ms|14.885003ms|+0.363723ms|
| 제한 ROM907 진단 전체 일정 |18.727048ms|18.727048ms|+0.000000ms|
| 통합 ARM text |22214B|22274B|+60B|
| 통합 ARM BSS |46292B|48340B|+2048B|
| whole FPGA comb |17671|17671|0|

단독 planner71 중 개선33개, 회귀38개다. 최종 코드의 membership 보강과 workset 초기화 비용을 모두 포함한다. 진단 ELF의 stack 관측472B는 동일하다. BSS는 source history·진단용8192B plan buffer 등을 포함한 probe 총량이며 실제 firmware의 증분 배치 검증이 아니다.

정상·제한 각각905..907만 live ARM/E9/refill/IRQ/ROM으로 재일정했다. 제한907은 ROM 공급 창을 기다리는 위상 효과를 포함한다. 더 빠른 standalone954 값을 기존954 전체 시간에서 빼서 새 전체 시간으로 제시하지 않는다. NES288의71프레임 전체 일정 최대는 미측정이다. 현재 NES287의 warm 최악26.375411ms/한도초과9.708744ms와 회로 부족2263개는 여전히 해결해야 하는 기준이다.

모든 생성 RTL의 바이트 해시가 NES287 test06과 동일함을 확인하고 기존 matched whole Lite board01 결과22569LE/17671comb/9025FF/307808RAMbits에 연결했다. 새 Quartus MAP은 실행하지 않았으며 ARM RAM을 FPGA RAM에 더하지 않는다. host/validator/queue/plan/SPI+두 wrapper의 own logic4853comb, budget2590,128여유 목표2462도 그대로다. 단독 검색표 변경으로 이 회로 부족을 해결할 수 없다.

## 검사와 한계

actual ARM71 exact plans/metadata/H2, 기존 ARM 오류15, row guard5, 새 workset guard9, IRQ8case/33wake와 row touch 선점1, H2 guard8 PASS. workset guard는 poison 초기화·원본 input/raw512 불변·kind/duplicate/empty 목록·STOP·warm retained map에서 누락 BG 거부를 확인한다. live 정상3+제한3은 실제 E1/E9 바이트, 독립 CRC/receipt/coverage와 최종 ACK를 기존 기준에 대조한다. source 비용 재생·기존 ordinary/manifest template·CPU279 bus trace·tile/map/display 모델은 유지했다. RTL이 동일하므로 NES287의25 통합 STOP/ACK guards와315 범위 증거를 그대로 참조하며 새 실행으로 세지 않는다.

시간은 CPI1/84MHz와 EXTI24cycle allocation이고 full firmware/RUN·임의IRQ WCET·물리60fps 증명이 아니다. source decoder는 material 생산에 실제 실행하되 기존source 명령 재생과 중복 계산하지 않는다. 새 실제 SNES 전체 실행·FIT/STA·전체 배치 성공을 주장하지 않는다. raw0의 H2 단위검사는 전체 raw2→0 화면 전환 검증과 다르다. production227/GBC164/saveSRAM은 변경하지 않았다.

## 다음 교체의 의존성

| 산출물 | 현재 소유자와 준비 시점 | 조기 실행의 필수 조건 |
|---|---|---|
| 로컬 H2 certificate32B | ARM geometry, local only | 입력COMMITTED·raw 검사를 통과한 동일 epoch/serial/gen에 결합하여 발행; 별도표 버퍼의 무단 가정 금지 |
| BG exact keys / raw CHR·HDMA | video 구조의 같은 union | BG allocation이 끝나기 전에 raw표를 이 영역에 덮어쓰지 않음 |
| tile batch / BG DMA | ARM row callback→credited E9→FPGA tile/staging | 완성된 batch와 실제 ready token을 대응시킨 descriptor만 실행; 바쁜 bank에서 producer가WFI로 교착하지 않음 |
| OBJ·OAM | 현재 모든 BG group 뒤 final step | 실제 OBJ 계획·OAM byte가 만들어진 뒤 전송; 이전 fixture를 준비된 데이터로 간주하지 않음 |
| map·manifest | map slot/dirty 결과, 독립 coverage | 최종 map row와 요구 범위 확정 후 생산; speculative receipt와 displayACK 분리 |
| 최종 SEAL/ACK | FPGA validator와 SNES display | 모든 receipt·CRC·H2·12Bread와 실제 finalACK 유지; queue drain만으로 resident commit 금지 |

기존 frame907/954 명령 순서는 BEGIN→BG DMA들→OBJ DMA→map→OAM→scroll/raw→manifest→SEAL이다. 준비된 row만 계산해도 다음 단일 BG descriptor가 여러 row의 tile 완료를 요구할 수 있다. BEGIN을 먼저 보내는 것만으로 OAM/map까지 동시 실행된다고 계산할 수 없다. resumable native producer와 batch 단위 descriptor 수명, 최종 manifest의 실제 생산을 같이 바꾸어야 한다.

다음 후보는 row/workset 이진검색 튜닝이 아니라 native ordinary/manifest 생산과 단계별 출력 실행의 공동 교체다. COMMITTED/raw 검사 뒤 로컬H2 인증서를 발행하되 BG exact-key/raw table union의 수명을 보존한다. 완성된 E9 batch에 대응하는 BG DMA descriptor만 공급하고, OBJ/OAM·map·manifest·SEAL은 각각 실제 생산 완료/coverage에 묶는다. ARM bounded cursor가 host의 descriptor 해석·반복 전송 제어를 실제 대체하는 범위를 먼저 구현하고 FPGA 독립 bounds/CRC/receipt/orderedACK/STOP/최종ACK는 남긴다. 공유SPI·credit·ROM 위상을 포함한 동일 일정으로 검증하며 회로 경계4853comb를2590(128여유2462) 이하로 줄여야 한다. 2KiB 검색표 단독 최적화나 근거 없는 earlyBEGIN 시간 차감은 반복하지 않는다.

## 재현

`tools/probe_nes_planner288.py --out <new-dir> --last 975`로 standalone71을 실행한다. live는 `tools/probe_nes_live288.py --out <new-dir> --last 907 --irq --plans ../probes/nes-joint284/test04 --cpu-trace ../probes/nes-joint279/cpu01 --questa-bin <bin>`이며 제한 조건은`--rom-window 1`을 추가한다. Questa는 AGENTS의 기존 Starter FLOAT wrapper를 사용한다. `tools/guard_nes_workset288.py --arm <arm-dir> --out <new-dir>`와 기존guard 진입점, `tools/analyze_nes_joint288.py --base <private-archive> --out <new-dir>`가 검증·분석을 재현한다. private fixture와 원본 ROM/license는 공개하지 않는다.
