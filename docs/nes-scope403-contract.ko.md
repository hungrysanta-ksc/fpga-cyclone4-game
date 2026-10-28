# 403 — 402 RAM을 보존한 공동 교체 범위와 시간·면적 예산

PR132의 다음 구현 범위를 정하는 R0 검토다. 기준은 402 `funded_RAM`의 실제 34 RTL·ARM·program·전체 Lite MAP이다. previous/rank RAM, shared CHR cache, 3584B tile FIFO+512B ordinary, 2출력슬롯/4입력packet을 유지한다. 고정 register host 기각 원형은 기준으로 채택하지 않는다. 이번에는 수동 계측과 RAM 모드 합성만 추가하며, 새 실행기나 추가 면적·시간 절감을 구현했다고 주장하지 않는다.

## 범위를 넓혀야 하는 이유

402 전체는 20,199 LE / 16,508 comb / 7,917 FF / 347,991 RAM bit다. 장치 제한 15,408 LE보다 4,791개, reserve 포함 comb 목표 15,253보다 1,255개 많다. read-owner·hint·tile/mailbox 보존 경계를 새 보고서에서 닫으면 **370C/264FF**다. 제어 전체 1,172C 상한에서 새 제어 몫은 **802C**다. 401의 803C와 차이는 보존 셀의 재집계이며 1개 최적화 실적이 아니다.

다음 표는 현재 LUT/FF 합계를 사용한 **설계 상한 조건**이다. 합성 결과나 적합 예측이 아니다. palette384FF는 아래 삭제 FF와 새 FF 양쪽에서 제외해 계속 보존한다. cache와 402의 previous/rank 데이터 RAM도 보존한다.

| 교체 범위 | 현재 삭제 경계 C/FF | 새 설계 상한 C/FF | 상한을 실제로 쓸 때 필요한 C·FF 중복 사용량 |
|---|---:|---:|---:|
| host·IO·SPI·source/plan·queue | 3,095 / 1,777 | 802 / 480 | 5,427개: 현재보다 **1,201개 증가** 필요 |
| 위 범위 + staging + raster + lease 본체 | 4,338 / 2,445 | 1,538 / 774 | 4,546개: 현재보다 **320개 증가** 필요 |
| 위 범위 + compact·plane fetch·patch/frame 제어 | **5,143 / 2,973** | **2,094 / 1,120** | **4,115개 이상**: 현재보다 감소를 **111개 이내**로 제한 |

현재 MAP의 C+FF−LE는 4,226이다. 확장안이 상한을 실현하면 전체 C=13,459, FF=6,064이며 LE≤15,408에는 C와 FF의 LE 공유가 최소 4,115 필요하다. 이는 전역 집계 산술이다. parent/child를 합산하지 않고 실제 self row의 합집합으로 계산했다. 새 회로를 LUT/FF 합계만큼 LE로 보거나, 현재 공유량이 유지된다고 가정해 적합을 선언하지 않는다. 좁은 범위가 불가능하다는 증명도 아니다. 다만 추가적인 packing 개선에 의존하므로 첫 구현 범위로 확장안을 선택한다.

| 확장안의 구현 예산 | comb | FF |
|---|---:|---:|
| host record 실행·범위 ALU·완료 공개 | 256 | 160 |
| SPI framing·원자적 응답·IRQ | 224 | 96 |
| NES source/plan 로컬 제어·CDC | 192 | 128 |
| queue 저장 credit·소비 완료 | 130 | 96 |
| staging bind/copy/소비 | 192 | 128 |
| NES capture/raster/lease/fetch/patch/frame | 1,100 | 512 |
| 새 회로 합계, palette384FF 제외 | **2,094** | **1,120** |

마지막 capture 항목은 palette를 포함하면 1,100C/896FF다. 예전 900C/704FF 상한을 그대로 성공했다고 세지 않았다. cache254C/97FF를 포함한 데이터 경로의 새 상한은 1,546C/1,121FF이며 현재 2,302C/1,677FF보다 756C/556FF를 줄여야 한다. 제어에서는 2,293C와 1,297FF를 더 줄여야 한다. 이 상한도 실제 구현·whole MAP에서 충족해야 하며 111을 물리 여유로 부를 수 없다.

## 실제 삭제할 제어와 유지할 검사

* **host**: byte398 VM·4M9K program과 임의 IO read/write 선택기를 16bit 범위 ALU·RAM record 실행으로 함께 교체한다. 큐 header→별도 register active record→public header의 중복은 준비된 17B 공통 header 한 벌로 바꾼다. 마스크·범위·상한 검사는 삭제하지 않고 같은 연산기로 순서대로 수행한다. SNES gather/재구성을 되살리지 않는다.
* **staging**: copy와 bind가 같은 metadata 포트를 순차 소유하는 동안 쓰는 두 32bit stamp scratch를 합친다. `copy_tail`은 미공개 prefill 중 tail 진행으로, `base`는 유효 chunk가 보유한 head/ordinary 상수로 대체하는 후보이다. generation·길이·예상 slot은 ARM record에서 가져온다. 실제 받은 tile stamp와 비교하는 검사는 유지한다. consume와 prefill commit 동시 발생은 두 pending event로 받아 한 ALU에서 계산하고 한 번에 공개한다. 둘 중 하나를 잃거나 used/credit을 중간 값으로 공개하면 실패다.
* **lease**: capture/source/display의 동일한 epoch 복사와 context 복사를 줄이되, input과 old display generation·serial은 분리한다. source→display는 미리 채운 context의 slot 소유권 전환으로 설계해 완료 뒤 RAM 전체 복사를 하지 않는다. old display는 정확한 final ACK와 plan drain 전까지 보유한다. 다음 input이 materialized됐다고 old identity를 바꾸지 않는다.
* **capture/raster**: row 진행·fetch pairing·query 응답·lease 문맥의 중복 제어까지 포함한다. 402 previous/rank의 한 event/clock·same-rank forwarding·33 copy clocks를 보존한다. palette384FF 및 PPU 시점의 비교는 빠른 NES 경로에 둔다. 이 부분을 byte 단위 host 작업으로 바꿔 transient midline 변화를 놓치면 실패다.
* **독립 경계**: expected·실제 read-end CRC/coverage·duplicate 검사는 별도 저장과 데이터 기원을 유지한다. STOP는 RAM 실행기의 다음 명령을 기다리지 않고 write·bus 공개·늦은 DONE을 차단한다. header6080..6090은 packet CRC·독립 검사·staging bind가 완료되고 유효 token이 있을 때만 공개한다. 402 header01 반례를 새 실행기의 필수 negative test로 넣는다.

## 클록과 RAM 포트 계획

두 클록의 제어를 한 always/FSM으로 합치지 않는다. 84MHz host 실행기와 NES 로컬 row/lease 실행기를 각각 두고, record 형식·ALU 이용·완료 이벤트를 통합한다. 기존 CDC의 frozen data/toggle·취소 drain 비용을 상한에 포함한다.

| RAM | 실제 보존/재사용 영역 | 포트 소유권과 제약 |
|---|---|---|
| payload 4096×8 | tile3584/ordinary512 유지 | A는 prefill/ordinary write, B는 실제 SNES DMA read. context나 snapshot이 B를 빼앗지 않는다. |
| metadata 1024×8 | stamp32..799 유지, control800..1023 재배치 | NES 쪽 tile/hint 포트 유지. host 쪽 한 포트는 header·record·snapshot·bind가 명시적으로 중재한다. |
| queue 1024×8 | expected0..471와 packet512..1023 유지 | expected를 읽은 관측값으로 재생산하지 않는다. 저장 credit은 packet이 실제로 비워진 뒤, 소비 완료는 실제 DMA/receipt 뒤에 반환한다. |
| raster row | row0..223 유지, tail224..255에 NES context | 단일 writer+query 우선 중재 또는 true-dual-port를 비교한다. 한 포트에 서로 다른 read/write 주소를 몰아 넣지 않는다. |
| previous/rank/cache | 402의 배열·포트·우회 보존 | 새 제어 RAM의 무료 공간/포트로 계산하지 않는다. |

host control224B의 예산은 active header/work32, old display32, next input32, progress/staging32, 기존 hint14, 응답 snapshot32×2, reserve18B다. hint928..941을 침범하지 않는다. 진행 상태 중복을 실제 삭제해야 이 용량에 맞는다. 전체 기존 stage register를 그대로 옮기는 계획은 아니다.

SPI SS 중 SNES retire와 plan 상태가 변할 수 있어 응답은 원자적이어야 한다. 변하는 status key와 소유권은 먼저 고정하고, 남은 bytes를 RAM에 저장하되 첫 응답은 기존 시점에 내보낸다. SS를 핑계로 STOP를 늦추지 않는다. RAM snapshot 준비가 header/DMA나 첫 ROM hint를 늦추면 추가 비용으로 측정한다.

Lite `ram01`은 256×56 row/context의 simple/true dual port와 1024×8 dual-clock metadata 형태를 모두 추론했다. **포트 모양 검증이며 기능 실행기나 전체 절감 검증이 아니다.** Cyclone IV의 simple dual port는 최대36bit, true dual port는 parity 포함18bit 구성이므로 56bit row의 명목 폭 예산은 각각2/4M9K다. 동시 쓰기를 추가하면 row 쪽에2개를 더 배정한다. [Cyclone IV Device Handbook, pp.3–10..12](https://docs.altera.com/api/khub/documents/3srzmTgxxMHVsaxzQUGqXg/content)

기존 program4M9K를 실제 삭제하고 새 microcontrol에256×32 한 M9K를 배정한다. row tail 확장까지의 논리 RAM 산술은 321,111bit다. 이 용량은 이번 설계 예산이며 영구 program 제한이 아니다. 더 커지면 추가 block을 청구한다. 단순 중재안은 program 대비 명목3개, true-dual row안은 명목1개를 비우는 계산이지만 전체 Fitter 여유로 확정하지 않는다.

## 시간 예산과 실제 ARM 공급

현재 마지막 tile는 914에서389.480414ms, 915에서421.632274ms에 준비된다. 그러나 마지막 E1 완료는 각각398.505677ms/430.887416ms다. 현재 생산 일정을 고정하면 마지막 데이터 뒤 실행 시간을 0으로 해도 해당 다음 VBlank의 마지막 gate보다 **1.128634ms/0.231550ms** 늦다. 마지막 checksum/view만 줄이는 범위는 부족하다. 빠른 packet 해석·확장·저장 credit/IRQ 반환으로 ARM 발행도 실제로 당겨야 한다. 이 값은 고정한 현재 공급 일정의 하한이며, feedback이 바뀐 새 일정의 불가능성 증명이 아니다.

914/915의 실제 ARM은 각각693,378/733,453 instructions, SPI3,403/2,432B다. byte 전송과 실행·IRQ 비용을 새 실행기가 없애준다고 가정하지 않는다. 첫 구현은 ARM image·wire ABI를 유지해 FPGA 교체 효과를 분리하고 실제 polling/IRQ 실행 횟수를 다시 계측한다.

시간 후보는 두 단계로 구분한다. **A**는 같은 ARM 코드에서 byte VM의 record/RAM 왕복을 줄여 저장 credit과 실제 E1 발행을 당기는 것이다. 마지막 ACK polling 제거만으로 시간을 얻었다고 세지 않는다. **B**는 old frame의 모든 DMA가 SNES WRAM에 저장되고 old plan이 실제로 drain된 뒤, 표시 VBlank 대기 중 next-input generation의 plan/ROM을 미리 생산하는 것이다. B는 다음 소유권 변경이 필요해 A의 무료 시간 이득으로 합치지 않는다.

* prefill은 next input이 FPGA에서 materialized됐다는 사실뿐 아니라 실제 ARM 계획 입력도 준비된 뒤 시작한다. old 독립 seal·read drain·모든 DMA 저장·plan/ROM drain이 먼저 끝나야 한다. 별도 준비 lease와 generation을 사용하고 old display의 epoch/serial/fence·receipt·sealed/tile-closed 증거는 그대로 유지한다. 새 header·token·표시는 old final ACK 전 공개하지 않는다.
* old ACK의 조건은 전체 ring이 비었는지가 아니라 **old generation에 속한 미소비량이0인지**로 보존한다. old/next 양쪽의 payload 합계는3584B 이하, stamp 합계는192개 이하여야 한다. 전체 empty 검사를 단순 삭제하면 실패다.
* plan read/ROM drain과 display retirement를 분리해 다음 plan bank를 받을 수 있어야 한다. old drain 증거를 next plan 시작으로 지우지 않는다. STOP는 두 문맥과 late DONE을 모두 취소한다.
* ARM의 다음 plan 준비는 old-display ACK/credit/IRQ를 우선해 중단 가능해야 한다. 실제 compiler text/BSS/stack·실행 instructions·SPI·IRQ 증가분은 아직 null이며 prototype에서 청구한다. provisional history는 old ACK가 실패하면 폐기한다. source generation을 old display history와 혼동하지 않는다.

B의 대기 구간에는 큰 가능성이 있지만, 새로운 ARM·포트·generation 처리를 구현하지 않은 상태에서 그 시간을 차감하지 않는다. 같은 802C 제어 예산과 capture/lease 예산에 소유권 분리 비용도 포함해야 한다.

| 시간 gate | 914 | 915 |
|---|---:|---:|
| 현재 gate |398.778896ms|431.116201ms|
| 이전 실제 표시+1 목표 |VB23|VB25|
| 그 목표에 대한 추가 선행 |1.401853ms|0.460335ms|
| 누락 없는 전체 연속 목표 |VB23|**VB24**|

914를 회복하면 915의 목표도 당겨진다. 현재915 gate와 이상적인VB24 gate의 차이17.099747ms에는 이전 프레임이 놓친 VBlank의 대기까지 포함되어 있다. 이를 새 CPU 작업17ms로 해석하거나 1.402/0.460ms를 독립적으로 더해서 통과를 선언하지 않는다. 402 기각 host의 합법 replay는914VB23을 회복했지만915는VB24를 다시 놓쳐0.451431ms가 남았다. 이 원형의 공개 회귀·면적 증가는 여전히 기각 사유다.

새 실행기의 서비스 예산은 끊을 수 없는 microstep≤2 host clocks, 실제 header 요청 응답≤8 host clocks, 확장 payload byte≤8 host clocks다. **측정한 새 성능이 아니다.** PPU 검사·SNES read·STOP를 우선하고 background packet/CRC 작업은 그 사이에서 진행한다. stage word/consume 동시 이벤트·SPI snapshot·IRQ·2슬롯 포화까지 포함한 새 연속 일정에서 907/908 source 시각과 ROM cycle을 402와 정확히 맞춘 뒤 검증한다.

## 새 수동 계측으로 확인한 경계

`trace01`은 402의 34 RTL·program·M4 image와 같은 소스에 관측만 추가했다. 전체 `joint-events.csv`와 ARM 결과가 402와 바이트/객체 단위로 같으며 12회 정확한 ACK·908..917 capture 시작 수락10/10·read-event25,462·ROM71,964쌍/입력 중17,378쌍을 유지했다. 917 시작 수락은 917 전체 표시 완료의 증명이 아니다.

* 실제 header grant 최소 간격은 host **31clocks**다. 새 내부 응답 예산8clocks는 이보다 짧아야 하며 실제 arbitration·read pipeline으로 입증해야 한다.
* palette 검사 입력 간격은 최소 NES **4clocks=186.244ns**다. 192bit를 byte24개로 직렬 비교하면 다른 작업이 없어도 host24clocks=285.714ns라서 늦다. 빠른 비교를 공통 byte 실행기로 옮기는 안은 제외한다.
* SS 중 진행 key가 바뀐 응답은 E1 **142/349**, E2 **123/762**, E9 **50/50**이다. 새 snapshot RAM은 원자성을 실제로 제공해야 한다. command가 들어오기 전의 key 변화는 이 수치에서 제외했다.
* foreground915 구간에서는 다음 입력이 materialized된 채 이전 표시가 유효한 상태가 **32.184826ms** 관측됐다. 한 벌의 lease record를 덮어쓰는 설계는 제외한다. 이 counter의 frame은 foreground 표시 번호이고 실제 capture identity와 같지 않을 수 있다.
* IO62(final ACK 상태) 읽기가 foreground914/915에서 각각 **333,765/332,540회** 발생했다. 상당 부분은 이미 확정된 VBlank/표시 완료를 기다리는 polling이다. 이 횟수를 없애는 것을 그대로 처리 시간 이득으로 합산하지 않는다. 실행기 변경의 시간 평가는 record 처리→저장 credit→ARM 전송→실제 DMA/receipt의 연결로 한다.

## 다음 구현의 통과 순서

1. 공유 RAM record·staging scratch/진행·lease slot 전환을 연결하고 대응하는 기존 VM/IO/주소/완료 본체를 실제 삭제한다. 단위 tests에는 wrong generation/slot/CRC·중간 STOP·token/credit 재사용·header 조기 접근·late DONE을 포함한다.
2. raster/fetch/frame까지 확장 범위를 구현한다. palette/raw/mixed-plane/8rank/연속event와 query·row-commit/context 경합을 검사한다. 첫 source/hint 시각을 바꾸거나 raw fallback을 늘려 시간을 숨기지 않는다.
3. 실제 ARM·SPI·IRQ·ROM 경쟁에서 905..916 정확한 ACK, 908..917 캡처10/10과 누락 없는 warm 표시를 함께 검증한다. 908 hint의108.277µs 관측 여유와917 capture300.435µs를 무료 예산으로 쓰지 않는다.
4. 같은 source/program/kernel의 **whole Lite MAP**에서 LE≤15,408·comb≤15,253·제어≤1,172와 RAM·FF 상한을 동시에 대조한다. 상한 달성만으로 LE 적합을 선언하지 않는다. 실패하면 역할/용량을 재검토한다.
5. 그 뒤 FIT/STA·CDC/IO, resident ARM/65816의 RAM/stack·음향/입력·STOP 패키지, 더 긴918+/71frames·여러 시작 위상, 제한 실기를 진행한다.

이번 R0의 새 시간 이득·실행기 전체 비용은 null이다. 402의 검증된 절감은 유지하며, 추가 절감이나 물리60fps·MMC4/5 여유·실기 날짜·자동 구매/머지는 확정하지 않는다.
