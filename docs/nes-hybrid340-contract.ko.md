# NES340 혼합 source·실제 ARM BG 준비·host 주소 교체

## 판정

340은 실제 구현·실행 후보지만 **공동 채택하지 않는다**. 선택 기준은 계속 338 RTL + ARM336이다. 새 whole Quartus Lite 조합 논리가 17,274→17,602로 328개 증가했다. 제한 ROM 연속 warm907은 20.689660812→20.691024432ms로 약 1.364us 느리다. 따라서 선택 기준의 부족분 4.022994145ms / 1,866개를 줄인 것으로 기록하지 않는다. 후보 자체 부족분은 4.024357765ms / 2,194개다.

## 실제 교체

- N5 버전3: map MASK/SHIFT를 유지하고 nonmap MASK를 영역별 literal/repeat8 및 raster의 bounded repeat16으로 교체했다. 실제 header·BG seal·END transcript CRC, D4 bank CRC를 계산한다. 영역 순서는 map/row/exception/raster/mask/palette/counts/BG seal/OBJ/raw/END다. 339의 offline greedy와 동일한 encoder가 아니다. 최대64B scratch를 사용하는 streaming 정책이며 raster는64B 안의 모든 word가 같을 때만 반복을 사용한다.
- source의 global byte threshold 분기를 영역 선택으로 대체했다. nonmap MASK 저장·출력을 run offset/seed/count로 교체하되 map MASK/SHIFT, source base의 byte RAM과 독립 query 의미 검사는 유지했다. 16bit base RAM 재배치는 구현하지 않았다. 새 scratch RAM은 추가하지 않았다.
- ARM은 BG seal 뒤 BG view·geometry·H2를 private 상태에서 준비하고, OBJ·raw와 최종 transcript 검사가 끝난 뒤에만 COMMITTED로 전환한다. 원래 required/raw union은 재사용할 수 없어, 기존 sorted tile 목록의 2KiB를 membership bitmap으로 대체했다. sorted 목록 작성·binary search를 없애고 bitmap으로 검사한다. 최대512개 서로 다른 tag 검사와 map/OBJ/raster 의미 검사는 남긴다.
- 같은 M4 인스턴스가 각 실제 SPI bank와 일치하는 입력을 decode하고 private BG 준비를 수행한다. RTL이 bank CRC와 모든 실제 wire byte를 비교한 뒤 checkpoint에서 그 CPU 비용을 청구한다. 이후 같은 상태로 출력 planner·IRQ·2슬롯 실행을 계속한다. 준비 비용을 무료 중첩하거나 출력 단계에서 중복 청구하지 않는다. D4 shifter는 여전히 RTL이며 prefix/reply 명령 비용은 측정 재생이다. 전체 firmware RUN 또는 실제 ARM 장치 실행은 아니다.
- 첫 clear+BG slot1이 확정된 경우18B E9를 emit callback 안에서 즉시 공급한다. 미리 보낸 bytes/plans도 원래 batch 용량에 예약해 후속 정렬 경계를 보존한다. cold905/906에는 적용되지만 warm907에는 slot1 조건이 성립하지 않아46B 공급을 유지한다. 임의 slot의 선행 발행을 입증한 것은 아니다.
- host는 batch의 별도 next-descriptor cursor를 삭제하고 packet reader 위치에서 다음 descriptor를 이어 읽는다. metadata run count는 사용 시기가 겹치지 않는 header/byte counter를 재사용한다. expected, 실제 read CRC/coverage, private receipt job 및 job drain 뒤 exact token ACK는 변경하지 않았다.

## 전송·ARM 비용

실제 Cortex-M4 decoder는71개 프레임의348,610B를 정확히 복원했다. 성공 source wire 합계는52,113→32,236B이며 기록 내 전송량 회귀는 없다. 339 모델의26,273B를 실제 결과로 사용하지 않는다.

| 프레임 | 기존 성공 wire | 340 payload / bank | 340 성공 wire |
|---|---:|---:|---:|
| cold905 | 6,058B | 3,198B / 14 | 3,416B |
| 906 | 기준338 기록 참조 | 324B / 2 | 362B |
| warm907 | 564B | 183B / 1 | 206B |

warm의 BG seal과 OBJ/raw가 한 bank에 들어가므로 GEO 위치를 옮긴 것만으로 별도 bank 준비 중첩이 생기지 않는다. 별도 GEO bank 강제 flush는 채택하지 않았다. 실제 source 생산·poll·ARM decode·준비 checkpoint와 D5를 모두 일정에 포함했다.

빈 poll을 포함한 warm 실제 wire는668→336B다. 첫 bank 공개가455.517→554.834us로 늦어져 빈 poll은8→10회로 늘었다. 성공 wire 절감358B에서 추가 poll26B를 빼야 실제332B 감소가 된다. 압축한 한 bank를 공개하기 전에 전체 source scan이 끝나야 하는 비용이다.

whole M4 ELF는 text30,370B(+260), BSS47,428B(+24), data0, 관측 stack1,288B(동일)다. 진단용 큰 frame/output 배열을 target RAM 절감으로 계상하지 않는다. standalone decoder는 text1,636B/BSS48/stack48이며 이것을 whole M4 비용 대신 사용하지 않는다.

## 동일 위상·연속 일정

| 일정 | 905 ms | 906 ms | 907 ms | 907의338 대비 |
|---|---:|---:|---:|---:|
| 동일 시작·ROM 위상 | 84.169717224 | 117.966993470 | 25.051199382 | 0 |
| 제한 ROM 연속 | 84.797209694 | 114.915030094 | 20.691024432 | +0.001363620 |
| 정상 ROM 연속 | 63.900278642 | 50.078762684 | 11.992901538 | −1.417164812 |

각 일정에서905..907을 실제 M4/공유SPI/IRQ/2슬롯/ROM/출력 경로로 실행했다. 출력 E1 material 및 DMA 순서는338과 정확히 같다. E9는 검증된 prefix 분할만 다르다. 정상 ROM에서 보인1.417ms 개선을 제한 ROM에서의 개선으로 옮겨 적지 않는다.

제한 연속907의 source 시작은 기존보다16.244805ms 빨라졌다. 이는 앞선 cold 일정 변화로 생긴 시작 위상 변화이며 warm 자체 이득으로 빼지 않는다. 첫 ROM 요청은 source 시작 후6.969666ms이고, 실제 허용까지9.887609ms를 더 기다린다. ROM 허용 뒤3.833794ms는 기존과 사실상 같다. 3.180ms 상한까지 약0.653794ms가 여전히 필요하다.

339의 nonwire1.20ms 예산은 달성하지 못했다. warm은 source 입력·BG 준비까지2.692377ms, 그 뒤 첫 ROM 요청까지 약4.277289ms가 남는다. 전송량을 줄였어도 일반 warm 첫 plan의 확정·공급을 충분히 앞당기지 못했다. cold의18B prefix 효과를 warm의 이득으로 전용하지 않는다.

또한 구현된206wireB는339 모델126B보다80B, 약0.244ms 크다. 같은1.728ms ROM close 예산을 적용하면18B prefix를 가정해도 nonwire 허용량은 약1.026ms로 줄어든다. 이전의 조건부69us 여유는 이 구현에 존재하지 않는다.

## 전체 Quartus Lite 비용

| whole MAP | 338 | 340 | 변화 |
|---|---:|---:|---:|
| LE | 22,144 | 22,489 | +345 |
| comb | 17,274 | 17,602 | +328 |
| FF | 9,018 | 9,041 | +23 |
| RAM bits | 307,808 | 307,808 | 0 |
| 15,408comb 대비 부족 | 1,866 | 2,194 | +328 |

host 자체는2,161→2,148(−13), source encoder는1,348→1,668(+320), queue 자체225→224(−1)이다. 이 부분합을 전체 변화와 동일시하지 않는다. map MASK/SHIFT를 유지한 상태에서 region run/offset/seed/data mux가 추가되어 source에서 실제로 사라진 논리보다 신규 비용이 컸다. scoped4,303comb 예산을 충족하지 못하며 FF 감소나 RAM 유지로 성공 판정을 바꾸지 않는다.

동일 변경 소스의 whole Lite MAP 한 번이다. 신규 undriven/latch는 없고 기존 cache_index141 latch와 보드의 고정 pin 경고는 남는다. FIT/STA/타이밍 closure를 수행하지 않았다. 미배치 상태를 실물60fps로 해석하지 않는다.

source `state`, host `state`/`owner`/`tap_state278`, validator `state`는 MAP 보고서에서 FSM으로 추출됐다. 이번 증가를 FSM 추출 실패로 설명할 근거는 없다.

## 검증·실패 보존

71프레임 실제 M4 codec와 15개 거부·복구 검사, 3프레임×3일정의 통합 실행, 8개 RTL 오류 주입(1/3/5/6/7/18/20/23), aperture·final raw0, 실제 M4 BG 수명 검사 4개가 모두 통과했다. STOP 중 source/E1/ROM 취소, 조기 최종 ACK, 독립 expected/receipt 불일치, 잘못된 token 등을 검사했다. 각 일정의 ELF 파일 메타데이터는 달라도 PT_LOAD 실행 이미지·메모리 배치는 동일하다. 실제 read coverage·CRC·최종 ACK와 기존 VBlank 경계를 검사했으며 전체 65816 실행 증명은 아니다.

초기 source helper 선언 순서 오류(test01/02), required/raw alias를 드러낸 test03/04, prefix의 원래 batch 용량 예약 누락으로906 tile byte가 달라진 test05를 보존한다. live01은 기존 출력 checkpoint 변환이 새 입력 checkpoint까지 잡은 harness 오류였으며, fail-fast로 종료했다. bgguard01은 진단 코드의 struct tail padding 크기 가정 오류이고 실제 ELF의9,880B를 확인한 bgguard02로 수정했다. arm01은 샌드박스 DLL 재할당 오류로 컴파일 전에 중단했으며 승인된 native 실행으로 재실행했다. 라이선스 부재 문제가 아니다.

live02의 입력 checkpoint는 실제 exception cycle이 모두0임을 확인했다. 이후 fixed/normal harness는0을 포함해 exception 항을 명시적으로 청구한다. output checkpoint는 기존 IRQ/exception 비용을 그대로 유지한다.

## 다음 경계

338을 유지하고 이 후보를 그대로 확대하지 않는다. source는 map MASK와 nonmap run을 병렬로 남기는 구조를 피해야 한다. region/query/비교/기록 생성의 실질적인 데이터 경로 삭제가 먼저이며, 현재340 source1,668을 예산701 수준 encoder로 줄일 근거는 없다. host도13개 감소로는1,015개 목표에 턱없이 못 미친다. 단순 상태 병합이나 주소 단위 변경 후 원래 byte 계산을 복원하는321/323 방식으로 돌아가지 않는다.

시간 쪽은 arbitrary warm slot의 immutable plan 발행 순서, 후속 낮은 slot·중복·bulk 분할·credit을 독립적으로 입증해야 한다. 첫 계획을 앞당겨도 새 DMA/setup/SPI 비용과 post-ROM0.654ms를 포함해 비교해야 한다. 단순 압축률·첫 요청 시각·시작 위상을 목표 달성으로 대체하지 않는다.

production227/GBC164/saveSRAM은 변경하지 않았다. metadata 선행 발행, full input COMMIT 전 출력 금지, 독립 검사, STOP 취소, 최종 ACK·VBlank는 유지한다. 물리 ARM WCET, 전체65816 polling/dispatch, 71개 fullRUN 연속 실행, 실물 지속60fps는 미검증이다.
