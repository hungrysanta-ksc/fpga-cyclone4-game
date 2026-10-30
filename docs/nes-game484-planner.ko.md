# NES484 — 실제 ARM 계획 비용과 공급 경계

PR135 merge `948a2e9bc6542aaec7737e28f4431cb0c0350f6d`와 마지막483 분석 commit의 origin/master 도달을 확인하고 `codex/nes-game-plan-supply-484`에서 시작했다. [실기 기준483](nes-mmc483-hardware.ko.md)·[검증 JSON](../analysis/game484-planner.json)·[다음 관문](nes-game484-next-plan.json)을 함께 읽는다.

현재 실기 기준은 **MMC482의14.60fps**다. 아래21.38%는 실제 연결된 M4 코드의 **계획 명령 수 절감**이며 FPS 개선율이 아니다. 새 전달본이나 실기 시험을 만들지 않았다.

## 무엇을 측정했나

- 실제482 firmware/ELF를 고정하고 기존 게임 입력905..975의 geometry/raw71쌍을478 해시와 대조했다. 실제 수신·planner를 Cortex-M4 명령으로 실행했다.
- planner 내부의 실행 PC를 ELF 함수/소스 행에 귀속했다. 메모리 함수는 exclusive 집계이며 부모 함수와 중복 합산하지 않았다.
- 입력2232 encoder·SPI 응답·writer/DMA 완료는 시험 모델이다. 실제 IRQ/ROM/VBlank 대기나 전체 RUN 시간·물리 SRAM/stack의 증명이 아니다.
- 별도로 기존480 실제 RTL transaction 시험의 E8 요청/응답23개를 CRC/ABI까지 검사했다. 이는482 실기의 프레임당 약89회 polling을 재현한 기록이 아니다.

## 계산에서 확인하고 바꾼 부분

기준의71프레임 합계는56,068,750명령이다. resident 슬롯 함수26.88%, memset10.38%, 타일 조회10.17%, 해시 탐색8.36%, memcmp8.03%다. 이미2816B 해시 인덱스와 타일 이진 탐색이 있으므로 이를 새 최적화로 다시 도입하지 않았다.

1. `nes_resident211_slot`의 같은 프레임 exact-hit를 먼저 반환한다. 기존 `ordinary()`는 retained-key 자격을 분류하는 순수 함수이며 exact-hit에서는 결과가 사용되지 않았다. 이를 miss 경로로 옮겨 반복되는 alt8개/row16개 검사를 없앴다. generation·open/fault·kind 등 입구 검사와 miss의 모든 검사는 유지한다.
2. BG·OBJ의40B 계획을 `memset`한 뒤 전부 덮어쓰던 경로를 바꿨다. generation/slot/tag/kind/mask와 row16B·alt16B를 모두 명시적으로 채운다. 실제 송신 전 슬롯을 다시 지정하는 동작도 유지한다. RAW/END 초기화·CRC·wire encoder는 그대로다.

| 항목 | 482 기준 | 484 후보 |
|---|---:|---:|
| 71프레임 계획 명령 합계 | 56,068,750 | 44,083,214 |
| 절감 | — | **11,985,536 /21.38%** |
| 프레임 중앙값 | 799,681 | 618,178 |
| 개별 프레임 절감 범위 | — | 18.83..22.71% |
| 실제 출력 계획 | 598개 | 40B 전체·순서·bank 일치 |
| 수신 명령 / 전체 상태 | 기준 | 71개 모두 일치 |
| ARM text / data / BSS | 202313 /10040 /18552B | 202317 /10040 /18552B |
| firmware / Flash 잔여 | 212356 /636B | 212360 /632B |
| 기존 RUN / 새 할당 | 31848B | 동일 /0B |

77개 object의 allocated section과 relocation을 비교하면 실제 변경은 planner/resident 두 개뿐이다. crc.o/startup.o의 raw 차이는 assembler `.stabstr`뿐이며 실행 코드 차이가 아니다. 전체 stack/IRQ 여유는 여전히 미증명이다.

기존 collision/180-frame workload·cold/epoch·generation wrap·고갈·writer 실패·잘못된 commit/abort 시험을 현재482와484 allocator에 적용했다. 총243645요청/187프레임/5 fault cases에서 슬롯·출력·video와 **인덱스까지 포함한 전체 resident 상태**가 일치했다. 이 host 시험을 새로운 RTL/65816 STOP·최종 ACK 결합 시험으로 부르지 않는다. 해당 transport·검사·STOP·commit 경로는 수정하지 않았다.

## 공급에서 남은 직렬 구간

기존 E8 분류는 credit-empty4 /busy-empty15 /descriptor-ready2 /finished-empty2다. busy 이유나 소요 시간까지 나타내지 않으므로 전부 불필요한 polling이라고 제거할 수 없다.

71개 실제 계획에 현재 `append/finish` 정책을 투영하면 warm69개 중61개는 첫 E9가 planner 반환까지 기다린다. 예를 들어907은 첫 BG 계획이150629명령에서 준비되지만, 총561822명령 뒤 finish에서 첫 묶음을 발행하는 모양이다. 이는 callback이 즉시 끝난 시험에서 얻은 **발행 가능 시점**이며 실제 SPI 전송 시각이 아니다.

첫 BG에서 flush하는 정책만 투영하면71프레임에서 E9가30개 늘어 최소240B의 E9 framing이 추가된다. 새 flush마다20B E8 검사를 비용 장부에 넣되, 기존 finish polling을 대체하는지는 실제 공동 일정에서 판정해야 한다. 계획 payload·순서·세대는 그대로다.

**선행 flush만 추가해서는 충분하지 않다.** 현재 tile bulk(op7)는 blocking exchange로 실제 소비/ACK까지 기다리고, E8에서 descriptor를 발견하면 그 경로를 실행한다. 작은 선행 묶음 뒤 lease가 멈추면 ROM 선행 읽기도 멈추며, 추가 SPI만 늘 수 있다. 다음은 선행 묶음과 기존 window를 이용한 bulk 소유권을 함께 비교한다. 저장 credit 반환을 소비 완료로 취급하거나, 미완료 token을 재발행하거나, ACK 전에 staging을 재사용해서는 안 된다.

## 전체 예산과 통과 조건

FPGA 소스/bitstream은482 그대로이며 변경 없는 Lite 합성을 반복하지 않았다. 기존 whole FIT15254/15408LE·14049comb·8392FF·256608bits,154LE 잔여를 재사용한다. 새 회로 절감·CDC/IO 승인으로 해석하지 않는다.

실기 전체68.4835ms/표시와60Hz까지의51.8168ms 차이는 새 측정 전까지 그대로다. 수신17.1571ms·계획/공급32.3183ms·SEAL/최종 ACK18.4430ms를 모두 포함한다.21.38% 명령 절감을 이 시간에 곱해 새 FPS를 만들거나, nested E8/E0/quiet 비용을 더하거나 빼지 않는다.

다음 관문은 **같은 ROM 위상에서484 ARM+482 RTL+실제 plan service/window+65816**을 연결한 전체 일정이다. 선행 E9와 op7 in-flight/lease를 함께 검토하고, 기존248B plan buffer·window 저장을 우선 재사용한다. 추가 ARM Flash는 우선384B 이내를 후보 예산으로 두며 실제 링크·소유권 증명 전 확보됐다고 보지 않는다. 독립 검사·4credit·STOP·최종 ACK·VBlank·메뉴 복귀와 다음 입력의 진행을 유지해야 한다.

## 재현과 보존

공개 도구는 [prepare](../tools/prepare_nes_game484.py), [profile](../tools/profile_nes_game484.py), [guards](../tools/check_nes_game484_guards.py), [analyze](../tools/analyze_nes_game484.py)다. ARM 빌드는 기존 `tools/build_nes_mmc479_arm.ps1`을 사용한다. 로컬 선택 근거는 workspace의 `probes/nes-game484/{candidate01,ARM01,profile01,profile02,guards01}`다. 새 출력 경로를 사용하며 기존 실패/로그를 덮지 않는다.

profile02 최초 aggregate는 event 리스트 참조를 공유한 집계 오류가 있었다. 명령/상태 결과에는 영향이 없으며, 먼저 저장된71개 frame JSON의 해시·개수·나머지 필드 일치를 검사해 event를 재집계했다. 원본 aggregate도 보존했다. 현재 profile 도구는 리스트를 복사하며 analyzer는 원본 frame을 검사한다.

전체482 source/ELF·478 입력/참조·480 transaction·Arm toolchain·Unicorn/pyelftools는 로컬 선행 입력이다. clone만으로 모두 포함된다고 가정하지 않는다. 공개 JSON에는 해시·수치만 넣고 상용 ROM·pixel/raw·바이너리·로그·라이선스를 추가하지 않는다.482 설치본·476/164/467 복원물과 GBC/save를 보존한다.
