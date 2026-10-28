# 402 — capture/cache RAM 실구현과 host 교체 후보 기각

이 문서는 PR132의 401 다음 실험이다. 기준은 400 RTL·ARM, 401의 실제 65816 view/HDMA 관측 envelope와 연속 일정이다. production227·GBC164·save SRAM은 변경하지 않는다. 402는 실기 배포 후보가 아니다.

## 실제 변경과 선택 경계

두 대안을 분리했다. `fixed_host`는 byte398 범용 실행기·4096×18 program ROM·임의 IO 선택기를 삭제하고 고정 register/FSM으로 대체한 비교용 원형이다. 기존 396 의미 처리를 400 read-end 소유자와 현재 물리 SPI/queue/hint/plan ABI에 연결했다. 64×24 checker ROM과 active-record FF를 포함해 비용을 청구했다. **401에서 제안한 공통 RAM record 실행기는 구현하지 못했다.** source·plan·SPI 본체도 남는다.

`funded_RAM`은 기존 host 실행기와 독립 검사를 유지하면서 capture previous/rank, CHR cache metadata를 실제 RAM으로 바꾼 대안이다. 현재 사용 중인 1,979 program word와 정적 분기 목적지(max 1,966)는 그대로다. 뒤의 trap padding만 줄여 2,048×18 ROM(4,608B)과 11bit PC를 사용한다. 생성기는 기존 ISA의 4,096word 범위에서 사용량에 따라 다음 용량을 고른다. 영구 2,048word 제한이나 SMB3 ROM 개조가 아니다. 기존 제어 프로그램의 미사용 padding 비용을 줄여 데이터 RAM을 확보하는 것이다. 범용 실행기 삭제 실적으로 계산하지 않는다.

## 클록·RAM 포트

* previous는 33×15, rank는 8×62(상수 하위 bit 최적화 후 61bit) synchronous RAM이다. event와 row 제어를 함께 한 클록 지연하며 reset/release는 즉시 반영한다. 같은 rank의 연속 갱신은 forwarding한다. raw row 판정은 원래 edge의 lookahead로 유지한다.
* raw commit에서 previous[0]을 선행 읽고 delayed commit에서 첫 cell을 저장한다. 이후 1..32를 복사해 기존 33 copy clocks를 유지한다. map write는 첫 cell/복사 loop가 한 주소 mux를 공유한다. PPU 입력에 대기 신호를 추가하지 않았다. palette 384 FF와 기존 비교는 유지한다.
* 공유 cache는 144×18 true-dual-port RAM 한 개다. data 0..111, metadata 128..141을 사용한다. SCAN에서는 두 포트가 metadata, HIT에서는 B가 payload 선행 읽기, refill에서는 A가 byte/B가 valid를 맡는다. 각 물리 포트의 주소는 하나다. STOP drain과 늦은 DONE 차단은 유지한다.
* payload/context/expected RAM을 이 cache와 무조건 합치지 않았다. nominal M9K 계산은 capture 추가 3개를 program 8→4개와 cache 통합으로 조달한다. 이는 배치 후 block 여유나 Fitter 성공을 뜻하지 않는다.

## 검증과 발견된 회귀

선택 증거는 `probes/nes-joint402`의 capture07, cache04, host02/03, build05/07/08, map04/07, live02/04/06, header01이다. 경로는 workspace 상위의 보존 archive를 가리킨다. 재현 도구와 해시는 `analysis/joint402-verification.json`, 전체 self-cell 합계는 `analysis/joint402-cost.json`에 둔다.

capture07은 5 frames·38,078 events·6,226 query와 STOP 후 256 clocks를 이전 RTL과 비교한다. raw row·mixed planes·8개 OBJ rank·연속 동일 rank·flip attribute·cold/recovery를 포함한다. cache04는 977 ROM request/reply pairs·20,424 clocks에서 이전 cache와 cycle exact이며 22bit 주소 상위 bit, epoch32/generation16 wrap, error reply, STOP·late DONE 32 clocks를 포함한다.

host02의 합법적 소비 순서에서는 12 frames·25,462 actual reads·19 guards가 통과했다. host03은 같은 12 frames·reads와 VM RAM 보호를 포함한 20 guards가 통과했다. 독립 duplicate fault2/coverage fault3와 STOP freeze는 각각 확인한다. **host02의 양성 결과만으로 공개 조건 보존을 주장하지 않는다.** header01은 invalidate ACK 후 아직 staged되지 않은 header 주소 006080 접근을 실제 RTL에서 비교한다. 고정 host는 공개해 버리고 기존 host를 유지한 funded_RAM은 차단한다. 이 회귀와 증가한 제어 비용 때문에 fixed_host를 기각한다. 늦게 gate만 고친 뒤 예전 timing을 새 RTL 결과로 재사용하지 않았다.

live는 실제 M4 실행·공유 SPI·IRQ·2슬롯·입력 중 ROM 경쟁·17B header DMA service·view/HDMA envelope를 연결한다. 입력 capture 원점은 그대로지만 RAM pipeline의 owned 완료가 한 NES 클록 늦어져 907/908 source 시작도 각각 46.561ns 늦어졌다. 이 차이를 숨기지 않는다. 기존 401 RTL에 테스트 admission만 한 클록 늦춘 live06을 추가하고, 402 live02/04의 실제 source 시각과 ROM cycle이 그 대조군과 같은지 검증한다. live06은 production RTL 변경이 아니다. 단위 테스트·live·전체 MAP의 RTL 및 program을 해시로 일치시킨다. native 1778B kernel과 M4 PT_LOAD는 401과 같다. 새로운 전체 resident 65816 실행을 한 것은 아니다.

## Quartus Lite 전체 비용

| 전체 MAP | LE | 조합 논리 | FF | 논리 RAM bits |
|---|---:|---:|---:|---:|
| 400/401 기준 | 22,114 | 17,376 | 8,903 | 382,304 |
| fixed_host + 별도 cache metadata RAM, map04 | 21,053 | 17,352 | 8,079 | 311,383 |
| RAM만 적용·program 미축소, map05 (면적 분리용) | 20,247 | 16,555 | 7,921 | 383,575 |
| funded_RAM + 공유 cache, map07 | **20,199** | **16,508** | **7,917** | **347,991** |

funded_RAM은 기준 대비 **−1,915 LE / −868 조합 논리 / −986 FF / −34,313 RAM bits**다. 그러나 15,408 LE 제한보다 **4,791 LE** 많고, 155개 reserve를 포함한 조합 논리 목표 15,253보다 **1,255개** 많다. 서로 겹치지 않는 closed control은 3,465 comb로 cap 1,172보다 **2,293개** 많다. 데이터 경로의 이득은 검증됐지만 host/source/plan/SPI의 삭제 목표는 미완료다.

논리 RAM 차이도 전체 보고서와 일치한다. program padding −36,864bit, previous +495bit, rank +488bit, 공유 cache의 기존 128×8 대비 +1,568bit를 합하면 −34,313bit다. nominal program 4개를 비우고 capture 3개를 추가하며 cache는 기존 한 block을 재사용한다. 1개 nominal 차이는 fitted 여유로 확정하지 않는다.

fixed_host의 closed control은 3,515→4,249 comb, 2,045→2,203 FF로 늘었다. 범용 ALU의 공유를 없애면서 주소·범위·분기 계산을 병렬 복제한 탓이다. program ROM 제거만으로 성공을 판정하면 잘못된 선택이다. inclusive parent/child를 중복 합산하거나 실패한 RAM inference를 개선 기준으로 쓰지 않았다.

RAM 적용만으로 401의 데이터 경로 예산을 달성한 것도 아니다. funded_RAM의 capture 1,545C/1,206FF, cache 254C/97FF, staging 503C/374FF 합계는 **2,302C/1,677FF**다. 401 R2 cap 1,400C/992FF보다 **902C/685FF** 많다. host만 803C로 줄이면 전체가 맞는다고 가정할 수 없다. capture의 남은 비교·row 진행과 staging 본체까지 포함해 이 초과분도 다시 배분해야 한다.

capture 1,545C의 내부 self 내역은 raster 506C/422FF, compact 478C/299FF, capture/lease 문맥 234C/256FF, plane fetch 163C/139FF, patch row 98C/62FF, frame 44C/27FF, pixel bind 22C/1FF다. previous/rank가 있는 compact만 남은 capture 전체라고 세지 않는다. palette384FF를 유지하는 조건에서 단순 RAM 이전만으로 나머지 capture 목표를 달성했다고 볼 수 없고, raster/lease/fetch 경계의 실행·문맥을 함께 검토해야 한다.

map01/02는 다중 주소 RAM 포트 때문에 FF fallback이 난 실패 증거다. map03은 선언 순서 오류, map06은 오래된 4096-word image가 복사된 source-binding 오류를 보존한다. 선택 map04/07은 실제 inferred RAM을 보고서에서 확인하고 기능 검증 source/program과 일치한다. 어느 것도 FIT/STA는 수행하지 않았다. 순수 LE 숫자로 LAB packing·M9K 배치·CDC/IO timing 여유를 보장하지 않는다.

## 일정 판정과 다음 구현

정확한 frame별 gate·present·capture·ARM instructions/SPI bytes·ROM pairs는 verification JSON에 보존한다. target VBlank는 **이전 frame의 실제 표시 VBlank+1**로 정한다. 앞 frame을 당기면 뒤 frame의 목표도 당겨지므로 예전 늦은 목표를 재사용해 60fps 통과로 만들지 않는다. fixed_host의 합법 소비 replay에서 914는 VB24→23으로 당겨졌지만 915는 다음 VB24를 놓쳐 VB25에 표시됐다. 이 결과는 공개 회귀가 있는 기각 원형의 참고 일정이다.

위상을 맞춘 live06과 funded_RAM의 **표시·완료·capture·source 시작·materialization 전 기록과 10개 display gate 시각이 정확히 같다. ARM 8,858,219 instructions/SPI 53,011B, ROM 71,964 request/reply pairs(입력 중 17,378)도 같다.** 이 일정에서는 면적을 줄이면서 추가 처리 시간을 만들지 않았다.

12회 표시·정확한 ACK, 908..917 캡처 10/10을 유지한다. 916 materialization 416.184591ms, 917 기한 416.485026ms 대비 **300.435µs** 여유다. 914/915는 VB24/26, 최대 warm 간격은 34.048237ms다. 관측 gate 기준 필요한 추가 선행은 914 **1.401853ms**, 915 **0.460335ms**다. area_goal/time_goal은 모두 false이며 audit 성공은 후보 채택을 의미하지 않는다. CPI1 checkpoint 모델과 3개 HDMA phase의 관측 envelope이며 모든 위상 WCET·실기 60fps·918 이후·MMC4/5 여유의 증명은 아니다.

다음은 고정 FSM을 더 붙이는 작업이 아니다. payload/context/expected의 독립 포트와 per-byte hot cursor를 유지하고 record 해석·range ALU·완료 공개를 실제로 공유하는 구조가 필요하다. source/plan/SPI 본체까지 삭제할 연결 경계와 비용을 먼저 제시하고, 이번 803-comb 미달 원형은 재사용 채택하지 않는다. 첫 ROM 허용 구간과 908 hint 여유를 깎아 후반만 빠르게 만드는 방식도 제외한다. 전체 용량과 다음 VBlank를 함께 만족하지 못하면 ROM/render 역할 또는 FPGA 용량을 재검토한다.

실제 funded_MAP의 남은 self cell은 host physical IO 810C/477FF, byte VM 427C/63FF, SPI front 721C/328FF, source transport 393C/186FF, NES plan transport 356C/284FF, queue 213C/85FF, plan SPI endpoint 97C/46FF다. 이는 해당 self row만의 목록이며 전체 합계에서 중복 차감할 수 없다. 이 중 VM 하나만 없애는 원형이 실패했으므로 다음 교체는 다음 경계를 함께 다룬다.

* **공유 연산**: descriptor 범위·payload cursor·receipt 진행에 한 연산기를 배정하고 active record는 RAM에 둔다. 독립 expected/CRC/coverage 저장은 남긴다. 매 byte 주소 mux를 큰 register record의 가변 선택기로 되돌리지 않는다.
* **완료 공개**: read-end 소유자와 header staged gate, old display identity, 마지막 실제 DMA receipt·final ACK를 별도 보존한다. 수신 credit과 소비 완료를 합치거나 STOP를 RAM 실행기의 다음 명령까지 지연하지 않는다.
* **SPI/CDC**: 현재 176bit immutable response view와 progress key는 단순 중복이라고 지울 수 없다. SS 중 SNES retire/plan 진행이 변할 수 있다. RAM snapshot을 쓸 경우 같은 transaction의 원자성·CRC·첫 응답 시각과 실제 read port를 검증해야 한다. NES 로컬 plan/query의 6클록 ROM read와 host SPI도 같은 FSM 이름만으로 합칠 수 없다.
* **데이터 경로**: capture의 남은 row 비교/진행과 staging의 bind/copy를 별도 상한에 포함한다. 이번 R2 초과 902C/685FF를 무시하고 host 803C만 목표로 삼지 않는다.

실기 테스트 시점은 아직 날짜로 정할 수 없다. 장치에 맞는 전체 구현의 FIT/STA·CDC/IO와 paired resident ARM/65816의 RAM/stack·sound/input·STOP 패키지가 먼저다. 이번 RAM 절감은 그 조건에 대한 실측 진전이며 실기 승인이나 자동 구매·머지가 아니다.
