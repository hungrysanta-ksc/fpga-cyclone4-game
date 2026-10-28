# NES401: 실제 삭제 경계와 65816 서비스 비용

PR132에서 400 RTL·ARM·17B header DMA kernel을 유지한 범위/예산 검토다. 범용 실행기 교체 RTL을 구현하거나 새 회로 절감량을 측정한 단계는 아니다. 400의 917 캡처 회복을 회귀 기준으로 두고, 누락됐던 view CPU 루프와 이전 활성 bank HDMA 비용을 넣어 재평가한다. 독립 expected·CRC·coverage, STOP 취소, 마지막 DMA receipt, 12 view read, 최종 ACK와 VBlank 조건을 줄이지 않는다.

## 기존 숫자의 의미와 회로 경계

전체 Quartus **Lite** MAP400/map01은 22,114 LE / 조합 논리 17,376 / FF 8,903 / RAM 382,304bit다. 원시 기기 한도 15,408 LE보다 6,706 LE 많다. 조합 논리도 원시 한도보다 1,968개, 155개 여유를 둔 15,253 목표보다 2,123개 많다. 2,293은 전체 초과량이 아니라 기존 self 제어 3,465에서 1,172를 뺀 수치다.

하위 CDC와 RAM decode를 같은 교체 경계로 닫으면 제어는 3,515 comb / 2,045 FF이고 목표 초과는 **2,343 comb**다. 추가 50 comb / 376 FF는 기존 전체 합계에 들어 있던 셀의 재분류다. 새 비용이 아니다. read owner(113/93), tile link와 mailbox(58/113), hint(198/58)를 보존하면 369 comb / 264 FF다. 남은 host·source·plan·SPI·queue 교체기는 합쳐서 **803 comb 이하**여야 기존 1,172 제어 목표가 성립한다.

전체 hierarchy의 self 행만 한 번씩 더해 다음 삭제 후보를 계산했다. parent와 child의 inclusive 합계를 중복으로 빼지 않는다.

| 실제로 함께 바꿀 범위 | 기존 comb / FF | 제거 가능한 C+FF의 낙관적 상한 | 외부 배치 고정 시 남는 LE의 하한 |
|---|---:|---:|---:|
| 범용 host·IO·source·plan·queue·SPI, 보존 제어 제외 | 3,146 / 1,781 | 4,927 | 17,187 |
| 위 범위와 staging 제어 | 3,643 / 2,155 | 5,798 | 16,316 |
| 위 범위와 capture 임시 상태·CHR cache 메타데이터 | 6,289 / 4,440 | 10,729 | 11,385 |

앞의 두 범위는 새 회로가 0개라도 각각 1,779 / 908 LE가 부족한 **고정 배치 산술**이다. 재합성의 외부 재배치까지 불가능하다는 증명은 아니다. 세 번째 범위도 실제 적합을 보장하지 않는다. 최대로 셀을 제거했다고 가정한 경우에만 새 회로에 최대 4,023 LE가 남는다. 이 하한에 새 회로를 더한 값을 적합 예측치로 부르면 안 된다. 실제 삭제된 occupied LE와 새 회로는 whole MAP에서 확인해야 한다.

encoder 1,335 comb / 394 FF와 독립 validator 998 comb / 188 FF는 유지한다. NES CPU/APU/PPU, ROM arbiter와 외부 wrapper의 미교체 로직도 절감으로 세지 않는다.

## 다음 교체기의 설계 상한

아래는 구현을 거절하거나 구조를 다시 검토하기 위한 **상한 배분**이다. 측정치나 예상 합성 결과가 아니다. 하위 decode·CDC·주소 선택을 포함한 비용을 내야 한다.

| 새 블록 | comb 상한 | FF 상한 |
|---|---:|---:|
| 고정 host record 실행·manifest·receipt 공개 | 256 | 160 |
| SPI 물리 transaction·coherent response snapshot | 224 | 96 |
| NES source·plan cursor 실행 | 192 | 128 |
| 2슬롯 저장·credit·load·retire | 131 | 96 |
| staging bind·copy·소비 | 200 | 160 |
| capture compact·raster 임시 상태, palette384FF 보존 포함 | 900 | 704 |
| CHR metadata lookup·취소 | 300 | 128 |
| 합계 | 2,203 | 1,472 |

첫 네 항목은 803 comb다. 전체 새 회로의 C+FF 상한은 3,675로, 낙관적인 4,023 LE 필요조건 아래지만 그 차이는 348개뿐이며 실제 packing은 미검증이다. 최종 통과는 **whole LE≤15,408, comb≤15,253, 닫힌 제어≤1,172**와 기존 기능·일정 조건을 동시에 요구한다. 155 comb는 MMC4/5 예산이 아니다. 이 범위로도 전체 MAP이 부족하면 소규모 FSM·opcode 조정 대신 ROM 공급/렌더 역할 또는 FPGA 용량을 다시 결정한다.

## 실제 삭제와 유지

1. 1,979-word 범용 semantic 프로그램·PC·arbitrary IO mux, descriptor/manifest/receipt별 진행 상태, 주소 응답 adapter를 **같이 삭제**한다. 수신 ABI와 독립 validator를 그대로 두고 고정 record 실행기가 한 번 해석한 범위·cursor를 사용한다. 범용 VM 옆에 새 FSM을 추가하는 방식은 제외한다.
2. source record writer·footer·NES plan decode/cursor/seal/retire와 관련 CDC를 교체한다. 각 clock의 단독 소유자를 명시하고 hot cursor·D4 고정 head·token은 레지스터에 남긴다. source head는 ACK 전 재사용하지 않는다.
3. SPI status별 넓은 snapshot과 CRC8 주소 mux를 RAM image 두 벌로 바꾼다. SS 도중 image는 고정하고, SS 종료의 길이·CRC8·A5 검증과 응답 마감은 물리 수신 경로에 남긴다. 동적 RAM 조회를 byte 응답 마감 뒤로 미룰 수 없다.
4. 2슬롯 저장 credit 반환과 실제 소비 완료·표시 lease 해제를 분리한 채 queue load/clear/retire를 단일 소유자가 갱신한다. 이전 표시 identity는 최종 ACK까지 유지한다. 입력 중 다음 source 수신은 이 문맥을 덮어쓰지 않는다.
5. staging의 open/bind/copy/consume 제어를 교체하되 **3,584B tile FIFO·512B ordinary 예약**, byte 저장, 실제 DMA read-end CRC/coverage와 마지막 receipt를 유지한다.
6. capture의 previous[33]495bit와 rank 상태496bit를 전용 RAM 후보로 삼는다. 한 이벤트/클록 입력과 동일 rank 연속 접근 bypass가 필요하다. PPU를 stall하거나 RAM read 비용을 0으로 세지 않는다. previous 복사와 OBJ rank 입력은 서로 다른 RAM에서 동작한다. previous_valid와 rank_valid8bit는 hot gate로 남겨 cold/STOP 직후 RAM clear 완료를 기다리지 않고 오래된 내용 공개를 막는다. **raster의 held/line palette384FF와 기존 비교는 유지하며 새 FF 상한에 포함했다.** 단순 write/revision counter로 없애면 같은 값 쓰기·원래 값 복원·mirror·copy 중 쓰기가 동치가 아니므로 절감으로 세지 않는다. 이번 경계에 새 PPU palette 관측기 비용이나 절감을 가정하지 않는다.
7. CHR cache의 7개 tag·byte-valid metadata를 전용 RAM에 두되 기존 128B 데이터 RAM과 epoch/generation 검증을 유지한다. STOP은 pending read를 drain하고 늦은 DONE의 캐시/plan 공개를 차단해야 한다. 실제 ROM 6클록 처리·공유 SPI/IRQ/캐시 hit 비용은 다시 계측한다.

## RAM과 포트 계약

삭제할 4,096×18 program ROM 73,728bit를 재배치 후보로 삼는다. host record 256B / SPI snapshot 2×64B / NES source-plan context 256B / capture previous-rank 256B / CHR metadata 128B / independent expected 512B, 합계 **1,536B**다. 기존 CHR data RAM 등 보존 RAM은 따로 남는다. 단순 bit 산술은 320,864bit다.

**6개 논리 영역을 6 M9K로 세지 않는다.** Lite `ram01`은 previous33×15와 rank8×62를 각각 독립 simple-dual-port M9K 배열로 추론했다(논리991bit, 기능 pipeline 미구현). [Cyclone IV handbook 표3–3](https://cdrdv2-public.intel.com/653974/cyclone4-handbook.pdf)의 simple-dual-port 최대36bit 폭을 적용하면 rank에는 명목2블록, previous에는1블록을 배정해야 한다. 전체 후보는 **명목8 M9K 대 삭제할 ROM8 M9K**로 예산을 수정했고 palette384FF도 유지했다. RAM 여유를 얻었다고 세지 않는다. `ram01`은 폭/모드 합성 확인이며 실제 pipeline·전체 교체 MAP·Fitter packing의 증명이 아니다. 깊이·폭·port·clock에 따른 전체 적합과 여유는 미확정이다.

| RAM | A 포트 소유자 | B 포트 소유자 / 금지 |
|---|---|---|
| host record | host 고정 실행기 | 독립 checker 전용 RAM과 혼합하지 않음 |
| SPI 두 image | host publisher | SPI 고정 image read; SS 도중 bank 교체 금지 |
| NES context | NES source | NES plan; phase/STOP로 양 포트 공개를 차단 |
| capture temporary | PPU capture pipeline | previous/rank 조회; backpressure 금지 |
| CHR metadata | cache lookup | refill/invalidate; 동일 주소 충돌 명세 필요 |
| independent expected | expected 생산 | 독립 검증 순회; 수신 payload가 expected를 덮지 않음 |

기존 metadata/header RAM과 source/tile 고정 포트에 세 번째 포트를 가정하지 않는다. 64B image를 84MHz에서 채우는 산술 최소는 약 0.762µs지만 CDC와 최신 상태 공개·실제 최소 SS 간격을 함께 만족해야 한다. 이 숫자만으로 SPI latency가 보장되지는 않는다. SS 도중 소비가 진행돼도 저장 credit의 과대 공개는 금지한다. STOP은 양 image와 다음 transaction commit을 무효화하고 최종 ACK 우회가 없어야 한다.

## 65816 비용 측정과 일정 연결

`native09/10/11`은 warm 시작 line 0/112/224에서 실제 65816을 실행한다. 현재 bank의 초기 이력은 두 프레임 전, **이전 활성 bank HDMA는 직전 표시 프레임** 데이터로 분리했다. 실제 HDMA read를 그 데이터와 비교한다. 400의 1,778B kernel은 바이트 동일하며, prior-display 설정은 별도 fixture stub이다. 이 stub의 준비·이전 프레임 대기는 현재 작업 시간에서 제거하고 원본 REP 두 명령 44 master clocks는 남겼다. `native08` HDMA-off control로 44클록을 확인했다.

단계 사이의 CPU jump/loop, source header DMA, 12회 indexed view read, 현재 PPU DMA·최종 ACK를 포함했다. 이전 활성 HDMA 대기는 이미 native event 간격에 들어 있어 별도로 더하지 않는다. warm view head는 약 118~123µs, polling은 관측 최대 280~282 master clocks다. 기존 400의 12×400ns view task와 고정 92클록 poll보다 넓은 비용이다. 914 view head 예시: receipt→첫 view 15.738µs, 첫→마지막 view 73.473µs, 마지막 view→첫 poll 33.245µs.

각 source job·view head·tail은 세 phase 중 가장 긴 **온전한 native 구간**을 선택해 actual ARM·SPI·IRQ·2슬롯·ROM 연속 일정에 공급한다. 이전 준비 시간은 포함하지 않는다. 이것은 관측된 서비스 envelope이며 모든 위상의 resident CPU/WCET 증명이 아니다. 시작 시각·ROM 위상은 400과 같은 고정 조건을 사용하고, 이후 연속 일정이 달라지는 효과는 구분한다. native HDMA 컴포넌트 통과만으로 917 회복이나 60fps를 선언하지 않는다.

연속 일정의 최종 결과·최신 gate 부족분은 `analysis/control401-verification.json`과 본 문서의 결과 절에 기록한다. 400의 914 **1.032200ms**, 915 **0.083284ms**는 일부 비용만 넣은 최소 부족분이며 새 측정 뒤에도 같은 숫자로 고정하지 않는다.

## 최종401 결과

선택은 `native09/10/11`·control`native08`·`service02`·`live02`·폭 합성`ram01`이다. native35건(정상32·STOP3), 연속12프레임, source/합성 일치 audit을 통과했다. line224 STOP은 첫 HDMA read 전에 취소되므로 해당 STOP의 read0은 정상이다. HDMA 비용용 정상 warm30건은 모두 이전 활성 데이터 read와 PPU write를 확인했다.

| 항목 | 기존400 | CPU 비용 보완401 |
|---|---:|---:|
| 표시·정확한 최종 ACK | 12/12 | 12/12 |
| 908..917 캡처 | 10/10 | 10/10 |
| 916 materialization | 416.178165ms | 416.184684ms |
| 917 기한416.485026ms 대비 여유 | 0.306861ms | **0.300342ms** |
| 908 hint ROM 구간 여유 | 166.386µs | **108.277µs** |
| 914/915 표시 VBlank | 24/26 | 24/26 |
| 최대 warm 완료 간격 | 34.044940ms | 34.048237ms |
| actual M4 명령 / SPI bytes | 8,853,510 / 52,962 | 8,858,292 / 53,011 |

907/908 시작 시각과 ROM cycle은 400과 정확히 같다. 이후에는 변경된 CPU 서비스에 따라 연속 일정과 polling·IRQ·source 선행 수신이 달라진다. 917 회복은 이 강화된 모델에서도 유지됐지만, 300µs를 물리 여유나 mapper WCET 예산으로 부르지 않는다. M4 적재 코드는 동일하고 text36,800/data4/BSS48,792, 관측 stack1,288도 유지된다. 명령·SPI 증가분은 바뀐 일정의 실제 코드 실행 결과이며 하드웨어 cycle 계측이나 full RUN은 아니다.

| 목표 표시 | 관측한 view 이후 gate | 같은 cutoff/tail의 마지막 허용 gate | 더 앞당겨야 할 gate |
|---|---:|---:|---:|
| 914, VBlank23 | 398.778955ms | 397.377042867ms | **1.401912ms** |
| 915, VBlank25 | 431.116379ms | 430.655865763ms | **0.460513ms** |

기존 1.032200/0.083284ms는 일부 비용으로 계산한 하한이었다. 새 값은 실제 replay gate를 관측해 계산했으며, global CPU 모든 위상의 WCET는 아니다. 아직 구현하지 않은 제어 교체의 시간 이득은 **null**이다. 새 RAM 실행기를 작게 만든다는 이유만으로 이 1.402/0.461ms가 해결됐다고 세지 않는다. 첫 ROM 기한, ARM 준비·발행, source·tile 저장, 최종 CPU 검사·PPU gate의 critical interval을 별도로 줄여야 한다.

ROM request/reply는 **71,964쌍**, 입력 중 **17,378쌍**, pending0이다. actual read event와 staging read-end는 각각 **25,462회**로 일치한다. host core 요청과 staging atomic은92클록, header 요청과 atomic은1클록 겹쳤으므로 고정 payload 포트를 임시 제어 RAM의 무료 포트로 가정할 수 없다. source write와 추가로 관측한 네 종류 NES 동시 수요는 이12프레임에서0이지만, 보편적 비중첩 증명은 아니다. port counter는 ready/valid 레벨 클록도 포함하므로 고유 ROM transaction 수나 삭제 가능한 시간으로 그대로 합산하지 않는다.

전체 비용은 동일한 **22,114LE / 17,376comb / 8,903FF / 382,304bit**다. 실제 새 제어 회로 절감은0이고, 교체 후 비용은 미측정이다. 이번 결과는 917 회복 보존과 CPU 비용 보완 및 **닫힌 제어2,343개 초과·LE6,706개 초과를 함께 다룰 교체 경계**의 확정이다. sustained60fps·기기 적합·실기 진입은 여전히 미달이다.

## 근거와 보존

`analysis/scope401-budget.json`은 원본 whole Lite hierarchy로 재계산한다. native·service·live raw 증거는 workspace의 `probes/nes-control401/`에 보존하고, 최종 audit은 실제 34개 RTL·program·M4 PT_LOAD·kernel과 400 whole MAP의 일치를 확인한다. 전체 기능 RTL이 같으므로 동일 whole 합성을 반복해 새 절감량으로 세지 않는다. 별도 ram01 RAM 폭/모드 확인은 whole 비용과 구분한다.

native01 build, native02 Lua, native07 control 준비 실패, native03 잘못된 이전 활성 이력, native04~06 준비 시간이 섞인 중간 측정, service01 과대 준비 비용, live01 준비 문자열 교체 실패를 보존한다. 선택한 결과와 혼합하지 않는다. audit01의 line224 STOP read0 과잉 조건, audit02의 cold 마지막 read handshake 허용 누락도 보존했고 분석 조건만 수정했다. 기능 simulation은 바꾸지 않았다. license 문제로 재분류하지 않는다.

보존 기준375RTL/377ARM과 production227, GBC164, save SRAM은 그대로 둔다. whole 용량 확보와 FIT/STA/CDC/IO, resident ARM·65816 RAM/stack·입력/음향·STOP 회복, 71/heavy7·긴 연속 일정·mapper 경계가 남아 있다. 최초 제한된 실기 시험은 이 gate를 통과한 뒤 진행하며, 현재 실기 60fps나 MMC4/5 여유를 확정하지 않는다.
