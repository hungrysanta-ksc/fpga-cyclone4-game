# NES357: NES 공통 실행기와 host row 공급 경계 비교

338 RTL·355 ARM을 유지한다. 356은 실제 collector 취소 시 query WAIT가 끝나지 않고 STOP 뒤 queued DONE이 공개되는 결함 및 +29 combinational 비용 때문에 기각된 상태다. 이번 결과는 기존 실제 실행·전체 Quartus Lite MAP에 근거한 **구조와 합격 예산**이다. 새 RTL/ARM 실행, MAP/FIT/STA 또는 물리 60fps 검증이 아니다.

결론: A(NES 클록 공통 실행기)의 경계 실현성을 먼저 검증하고 B(host row 공급)를 비교 대상으로 유지한다. 어느 구현도 선택하지 않았다. 두 구조만 바꾸어서는 현재 연속 일정의 4.023ms 부족을 해결한다고 볼 수 없다. 입력 전체 완료 뒤 첫 BG plan을 만드는 시간 계약도 함께 재검토해야 한다.

## 기존 실제 결과와 시간 하한

355 warm907의 동일 실행 계열을 재분석했다. ARM은 실제 Cortex-M4 명령 수와 CPI1/84MHz 모델, SPI/IRQ/2슬롯 및 ROM 경쟁을 포함한다. 전체 펌웨어 RUN이나 전체 실제 65816 실행/WCET 증명은 아니다. 일부 과거 요약의 관측 끝점 차이 약45ns와 구분해 아래는 joint-events의 frame_done 끝점을 쓴다.

| ROM 일정 | 전체 시간 ms | 첫 BG 요청 ms | 첫 ROM 수락 ms | 수락 후 ms |
|---|---:|---:|---:|---:|
| 연속 제한 ROM | 20.689706 | 6.960484 | 16.855593 | 3.834113 |
| 동일 시작·ROM 위상 | 25.051563 | 6.962939 | 21.217995 | 3.833568 |
| 정상 ROM | 12.007311 | 기존 실행 유지 | 기존 실행 유지 | 기존 실행 유지 |

연속 일정에서 첫 ROM 수락부터 이미 16.666667ms 기한을 0.188926ms 넘는다. 고정 위상의 첫 요청을 앞 ROM 구간에 넣기 위한 기존 목표 0.873217ms와 별도 후반 예산 초과 0.653568ms를 연속 일정의 4.023039ms에 더해서는 안 된다. ROM 구간 하나를 놓치면 작은 준비 개선이 전체 시간 개선으로 이어지지 않는다.

warm907의 필수 nonempty source는 3패킷·556 SPI bytes, decoder 38,212 instructions, prefix/reply 2,336 instructions다. 기존 전송률 2.625Mbit/s와 패킷당 CS 비용 0.008ms를 유지하면:

`556*8/2625 + (38212+2336)/84000 + 3*0.008 = 2.201190476ms`

최종 D5, 빈 polling 8회와 codec 대기를 모두 없앤 낙관적 하한이다. 실제 입력 완료 2.690513ms에서 최대 0.489322524ms만 줄일 수 있다. B가 이 전부를 얻어도 고정 위상에서는 ARM 준비를 추가로 최소 0.383894476ms(순 32,248 instructions) 줄여야 한다. A가338 source 일정을 유지하면 0.873217ms가 그대로 필요하다. 이는 새 구현의 성능 예측이 아니라 필요조건이다.

더 강한 연속 일정 제약이 있다. 해당 시작 위상에서 이전 ROM 허용 구간 끝은 약1.727616ms이며 이벤트/카운터 관측 오차를 두 NES clocks 넓혀도 1.727707ms 이하다. 이는 필수 source 하한보다 약0.473484ms 이르다. **현재 입력 전체 완료 장벽을 유지하면 ARM 출력 준비를 0으로 만들어도 그 구간에 첫 BG를 공급할 수 없다.** 이 계산은 현행 N5/MASK/SHIFT bytes·ARM355 decode·CS·ROM 조건에 한정된다.

따라서 다음 일정 비교에는 검증된 BG prefix로 시작하는 speculative ROM/cache prefetch 또는 프레임 간 공급·lease 일정 변경이 필요하다. 첫 BG의 group/pattern mapping, epoch, palette/context 의존성이 언제 모두 확정되는지 실제 ARM에서 먼저 계측한다. 입력 collector lease의 유효성과 불변 source를 확인한 prefetch만 허용하며, 이는 display lease나 PPU/DMA 허가가 아니다. 최종 source CRC·독립 expected·coverage·VBlank·최종 ACK는 그대로 실제 표시를 막는다. STOP/fault는 speculative 결과의 namespace를 무효화한다. 이 확장은 아직 구현/선택하지 않았다.

## A: 22MHz NES 클록 공통 실행기

collector/query/source 및 NES plan cursor는 NES에 유지하고 source 이후 출력 실행의 descriptor·주소·CRC 진행 레지스터를 phase별로 공유한다. 독립 expected 값과 소비 CRC/coverage는 합치지 않는다. output 실행을 NES로 옮겨 실제 불필요해지는 admission/final ACK CDC만 제거하며 source descriptor/ACK의 SPI 경계는 남는다.

현재 queue의 양 포트를 단순히 저속 클록으로 바꾸지 않는다. packet write 포트 A는84MHz SPI host, packet read/expected write 포트 B는22MHz NES로 고정한다. expected0..471, packet512..767 및768..1023의 주소 소유권을 유지한다. 저장 공개·저장 반환·실제 DMA 소비 완료는 별개다. binary credit counter를 비동기로 직접 읽지 않고 검증한 async pointer 또는 슬롯별 held descriptor/반환 handshake를 사용한다. E0 응답은 동기화된 snapshot이어야 한다. 두 포트 동시 사용 기록이 있으므로 단일 포트로 없어진다고 가정하지 않는다.

실제 같은 chunk의 인접 read 최소 간격은369ns다. capture·CRC·RAM 진행을 포함한 합격 목표는6 NES cycles=272.727ns 이하로 둔다. 8cycles=363.636ns는 약5ns만 남아 CDC/중재 여유를 입증하지 못한다. literal 3cycles/byte의7.333MB/s가 SPI0.328125MB/s보다 빠르다는 사실만으로 SNES read 처리에 합격하지 않는다.

validator 최종 순회는 정적 no-stall 경로 raw1956/raw01856cycles다. 84→22MHz 이동만으로 약65.623/62.268µs가 추가된다. RAM 중재·clear·metadata·display 대기는 별도다. 이 비용은 아직 새 전체 일정에서 실행하지 않았다.

## B: row 단위 공급을 받는84MHz host 실행기

1957개 collector query의 per-query CDC를 없애고 NES가 로컬 query를 수행해 canonical block을 만든다. map32×66B, 기타35×64B+46B=4398B, 총68blocks다. raw 최대512B까지 포함하면76blocks다. 두66B 슬롯과 `{generation16, block7, length7, slot1}` held descriptor/반환 credit을 사용한다. frame epoch/namespace는BEGIN에 고정하고 순서·길이를 검사한다. generation 단독으로 stale 판정을 하지 않는다. collector 로컬 read 수, source SPI bytes, ARM decode가 자동으로 줄어드는 것은 아니다.

기존512B scratch의 delta0..65/header256..275/mask384..392와 겹치지 않는128..193,288..353에132B를 배정할 수 있다. phaseRAM 물리 주소는640..705,800..865다. **NES362 주소식 재검토 정정:** 현재338 validator의 H2는680..711이며,832..863이라는 이전 설명은 오래된 배치였다. 첫 슬롯은ordinary receipt640..677 및H2의680..705와, 두 번째 슬롯은map receipt800..865와 겹친다. row 반환·source 전송 drain·입력 ACK를 모두 완료한 뒤 output owner가 receipt를 초기화하고H2를 써야 한다. 공간 산술은 동시 소유나 실제 공동 실행기 구현 증명이 아니다. [NES362 검토](nes-execute362-contract.ko.md)를 따른다.

포트 A는 고정 NES row producer, B는 고정 host input codec/output validator로 둔다. runtime clock mux는 금지한다. initializer는 source 시작 전에 끝내며 B의 row read/capture와 delta/mask/header write를 직렬화한 새 비용을 계산한다. 원래 source A/mask 진행 제어는 실제 이 경로로 대체된 뒤 삭제한다. 이 포트·수명 조건을 입증하지 못하면 별도 row RAM 최소1M9K 비용을 명시한다. 여유132B만 발견했다고 RAM 절감으로 계산하지 않는다. MASK·SHIFT·base serial·CRC·출력 ABI를 유지한다.

## collector 취소 완료와 STOP 뒤 DONE 계약

1. STOP은 양쪽의 신규 수락·쓰기·DONE·최종 ACK 공개를 막는다. source DONE과 최종 표시 ACK는 별개다.
2. collector가 query pipeline·응답·쓰기 소유권을 실제 비운 뒤 registered cancellation-applied ACK를 반환한다. release가 정상 응답을 지울 수 있으므로 정상 응답이 반드시 온다고 기다리지 않는다. timeout이나 비동기 `!owned`로 취소 완료를 만들어내지 않는다.
3. 수락된 query/row는 응답 또는 취소 중 정확히 하나로 끝낸다. STOP 동안 mailbox handshake는 유지해 partial/full rows·inflight 응답·queued DONE을 drain한다. 한쪽만 reset하지 않는다.
4. DONE 공개는 live namespace, 모든 row 소비, query/CRC/RAM write pending 없음, STOP/fault 없음이 필요하다. 목적지에서도 다시 검사해 STOP 직전 큐잉된 DONE의 지연 공개를 차단한다.
5. 재시작은 collector 취소 ACK, 모든 슬롯/credit 반환, pending completion drain 이후만 가능하다. 한 클록이 멎으면 기다리며 timeout 성공으로 바꾸지 않는다. wrap 재사용에는 bus quiescence가 필요하다.

분석기에서 한 stale namespace·2슬롯·8종 사건의40,320 순열을 확인했다. 정상 공개2016회, 차단78624회이며 공정한 drain 후 재시작을 확인한다. 이는 논리적 계약 모델이며 **실제 RTL 취소·CDC·metastability·정지 클록 검증이 아니다**. 356의 두 실제 실패는 해결되지 않은 증거로 그대로 보존한다.

## Quartus Lite 전체 경계의 합격 예산

338 실제 whole MAP은22144LE/17274comb/9018FF/307808RAM bits다. device15408comb 대비1866 부족하다. 155comb 여유를 두어 목표15253, 필요 순감소2021로 정한다. 아래는 합성 예측이 아닌 구현 합격 상한이다.

| 겹치지 않는 경계 | 현재 comb | 목표 상한 | 필요한 감소 |
|---|---:|---:|---:|
| source encoder1348 + transport399 + host own2161 | 3908 | 2035 | 1873 |
| queue+SPI | 798 | 650 | 148 |
| 독립 checker+aperture | 1159 | 1159 | 0 |
| plan | 459 | 459 | 0 |
| 나머지 전체 | 10950 | 10950 | 0 |
| 전체 | 17274 | 15253 | 2021 |

A의2035는 transport399+새 CDC/cancel allowance100+공통 실행기1536으로 배정한다. B는 direct transport allowance335+row/CDC/cancel200+공통 실행기1500이다. B의335는 실패한356에서 관측한 부분 비용일 뿐 안전한 구현 확정값이 아니며 DONE 수정 비용도 상한 안에 포함한다. LE/FF/RAM의 새 측정값은 없다.

현재 SPI front573을 그대로 두면650 중 queue/CDC에는77밖에 남지 않는다. queue만 줄여148을 회수한다고 가정하지 말고 SPI snapshot/응답/admission의 실제 삭제까지 확인해야 한다. 새 early-plan/cancel/row 제어를 outside나 유지한plan459에 무료로 붙이지 않는다. 부모·자식 MAP 값을 중복 합산하지 않는다.

## 다음 구현 게이트

우선 A의 실제22MHz read-event 처리6cycle 및 dual-clock2슬롯 저장/반환/소비 분리와 collector 취소 ACK·양단 DONE 차단을 작은 통합 경계에서 검증한다. 동시에 첫 BG 의존성 확정 시각과 입력 완료 전 prefetch/프레임 간 일정의 허용 범위를 계측한다. 이 결과가 예산에 맞을 때만 기존 source/host 제어를 실제 삭제한 전체 후보를 구현한다. B는 고정 RAM 포트로 두 row와 MASK/SHIFT를 처리하는 비용을 동등 조건에서 비교한다.

각 후보는 독립 expected/CRC/coverage, credit, STOP 위치별 취소, stale DONE, 최종 ACK, VBlank를 통과한 뒤 동일 시작·ROM 위상 및 연속 ARM/SPI/IRQ/2슬롯/staging 일정을 별도로 비교하고 전체 Lite MAP을 한 번 수행한다. 구현 전 새 회로 절감이나60fps 달성을 선언하지 않는다. 생산227/GBC164/saveSRAM, 과거 실패 증거는 유지한다. 자동 merge하지 않는다.

재현: `tools/analyze_nes_arch357.py`; 결과 `analysis/arch357-verification.json`(97 source/evidence pins). 로컬 로그 `probes/nes-arch357/analysis01.log`.
