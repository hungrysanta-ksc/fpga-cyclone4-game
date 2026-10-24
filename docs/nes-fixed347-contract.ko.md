# NES347 — fixed-block 반복 압축과 host·queue·plan 공동 교체 예산

**338 RTL·336 ARM을 유지한다.** 이번 결과는 새 압축 형식의 Python encoder·실제 Cortex-M4 decoder 검증과 회로/일정 설계 검토다. 새 FPGA RTL, 통합 ARM 일정, Quartus 합성을 실행하지 않았다. 따라서 선택 기준의 제한 ROM warm20.689660812ms,60Hz 대비4.022994145ms 초과와 whole17274comb/1866개 부족은 그대로다.

## fixed-block scan을 재사용하는 후보

338의 map32개×66B, nonmap36개(64B,마지막46B), raw64B 단위 순서를 유지한다. 변경 없는 block은 생략하고 map MASK·좌우 SHIFT record는 byte 단위로 그대로 둔다. nonmap/raw의 완성 block 전체가 동일 byte 또는2B 패턴이면 repeat8/16을 선택하되 기존 MASK보다 짧을 때만 사용한다. 나머지는 기존 MASK다.340/346의 가변 run 경계·region 이동·미소비 query byte 재처리가 필요하지 않은 형태다.

실험용 N5v4에서 index<32의 high bit는 기존 SHIFT, index>=32의 high bit는 repeat다. repeat record는`index|0x80, width(1/2), seed[width]`의3/4B이며, 출력 범위는 고정 block index에서 결정한다. 새 stream CRC와 GEO expanded-count를 실제로 계산한다. cold의 전체 block 순서/coverage, raw 값<64, 중복·순서·길이·epoch/serial 검사도 유지한다. 기존 N5v2/v3와 호환된다고 가정하지 않으며 제품 ABI로 채택하지 않았다.

GEO 위치도338과 동일해서 OBJ가 GEO 앞에 있다.346의OBJ-after-GEO 대응 bitmap/사전 준비 변경을 그대로 가져오지 않는다. 통합 시에는336 ARM에 새 decoder만 연결하는 비교부터 시작해야 한다. geometry 준비 가능 시각은 실제 SPI bank 완료와 새 decoder 실행 뒤 측정한다.

### 새로 실행한 증거

같은 ARM GCC 옵션으로 기준 N5v2와 후보 N5v4를 각각 빌드해71프레임×4910B=348610B를 실제 M4에서 정확히 복원했다. 모든 map MASK/SHIFT record가 기준과 동일하다.

|항목|338 형식 기준|347 후보|
|---|---:|---:|
|71프레임 성공 source wire 합계|52113B|28435B|
|warm907 wire|564B|189B|
|warm907 bank 수|3|1|
|warm907 decoder 명령 수|36220|16658|
|decoder text|1332B|1428B|
|decoder BSS|28B|28B|
|관측 decoder stack|48B|48B|

기준 대비 wire 회귀는71프레임 모두 없다. decoder 명령도 프레임마다12610..134973개 감소했다.340의합계32236B보다도 작지만 **cold905는340보다102B 크다**. 성공 wire는payload+bank당15B+최종8B이며 empty poll·IRQ·SPI 응답 대기까지 포함한 총 전송 시간은 아니다.

새 decoder의10개 검사는 잘못된 repeat 폭0/3, truncated repeat16,6bit raw seed 초과, 중복 block, cold block 누락, expanded count 오류, block CRC는 맞지만 stream CRC가 틀린 경우, ABI version 오류, reset 뒤 warm history 재사용을 거부했다. 이 reset 검사는 통합 RTL STOP 검증을 대체하지 않는다. RTL/독립 validator/최종 ACK/VBlank는 이번에 새 형식으로 실행하지 않았다.

### 실제 RTL 삭제·유지 경계

338에서`edge0/edge1`은 모든 block의 첫2B를 이미 보관한다. `left_row/right_row`도 매 block 시작에1로 초기화한다. map에서는 기존 좌우 SHIFT 비교를 유지하고, nonmap에서는 이 두 flag를 repeat8/16 비교 결과로 재사용하는 후보를 잡는다. seed16B나새 run buffer를 추가하지 않는다. raw/마지막46B도 현재 row_size를 사용한다.

|기존/거부된 경로|다음 구현의 계약|
|---|---|
|340/346 region340,region_base/end,offset340|추가하지 않고338 block_id/cursor/row_size 사용|
|run340,repeat340,pending340와 run 경계 재처리|전체 block 판정으로 대체; query byte는현재 FSTORE에서 한 번만 소비|
|seed340/seed_hi340,same_pair/any_change|edge0/edge1과 기존 flags/diff_count를 재사용하는지 실제 합성으로 확인|
|최종 record 출력|346의형식별 주소/seed mux 삭제는 참고하되, 고정 block builder 하나로 구성|
|query/history/MASK/SHIFT/CRC/lease|유지; phase RAM 포트와 mask_pending 쓰기 충돌을 계속 계상|

nonmap 비교를 기존8bit 비교기 두 개로 공유하려면 피연산자 mux가 추가된다. flags를 재사용해도 LUT가 반드시 줄지는 않는다.340의+276comb를 피하는 것과338에서647comb를 줄이는 것은 다른 목표다. 첫 합성 게이트는 **338 대비 whole 증가 없음**이고, 이것만으로 보드에 맞았다고 판단하지 않는다.

## host·queue·plan을 함께 바꾸는 경계

346의host−27comb는 작은 목적지 cursor 공유의 한계를 보여준다. 다음 후보는 같은 host clock의 SPI transaction 처리와E1/E9 RAM 쓰기·seal 완료를 공동 실행기로 묶고, NES 쪽 plan의가변 형식 해석을 대체하는 범위다. 다음 항목은 설계 후보이며 아직 삭제·합성하지 않았다.

1. **transaction decode/length/commit 소유자 하나.** E1의queue`ingress_length312`를 SPI`request_length280`의command별 문맥으로 옮기는 것이 첫 명시적 삭제다. E1/E9는 한 SPI transaction에서 동시에 실행되지 않는다. 하지만D4/D5/EA가 같은 필드를 사용하므로 command별 의미와SS 종료 후 handoff 수명을 유지해야 한다. queue의bit/count·SS 분기와 plan endpoint의같은 분기는 공통 byte/commit event로 대체하고 두 endpoint는 RAM/credit 소유권 adapter로 줄이는 범위를 검토한다.
2. **enqueue에서 검증한 record를 head에서 다시 조립하는 경로.** 현재`field338` scatter 주소·HLOAD/HCHECK와 active field capture가 대상이다. 기존 queue RAM의472..511은40B로2×20B checked header 문맥을 둘 수 있는 산술 후보다. 이는 무료 RAM/이미 확보한 저장소가 아니다. 정확한20B layout과CRC commit·generation binding·2슬롯 불변성을 먼저 확정해야 한다. 동시에 active packet을 실행하므로 incoming 문맥을 active305 register에 바로 덮어쓸 수 없다. 원문 packet을 보존하고 incoming 쪽 A port의추가 쓰기/읽기와 expected RAM B port 소유권을 계상한다. header를 단순히 옮기고 HLOAD를 남기면 삭제로 세지 않는다.
3. **E9 wire는 그대로, RAM 내부 plan만32B 고정 slot으로 정규화.** 기존512B bank는16×32B를 수용한다.32B는kind/partial/generation/slot/tag/masks/rows16B+8개alt tag16B의후보 layout이다. ingress가 short/full의필드·기본값을 최종 위치에 쓰고 CRC seal 뒤에만 NES에 공개한다. NES READ/CAPTURE의short/full 분기·popcount 기반길이·alt_index 빈칸 순회를 대체한다. 해당 검사 비용은 host 쪽에 남거나 공통 실행기에 흡수되어야 하며 이전했다고 절감으로 세지 않는다.

packed payload를 받아 같은 bank 안에서 나중에 확장하면 아직 읽지 않은 다음 plan을 덮어쓸 수 있다. 따라서 이 후보는 **입력 byte가 올 때 최종 slot에 쓰는 방식**으로 제한한다. 각 slot 초기화32번 쓰기와필드 갱신을 계상한다.2.625MHz SPI/84MHz host에서 입력 byte 사이에는256host클록이 있으므로 초기화·필드 처리·RAM 중재·기존 출력 실행기 선점 비용을 모두 이 안에 끝내야 한다.32번 초기화만0.381µs이며 전체 처리 상한의 증명은 아니다. transaction 시작의admit 이후에는 SPI를 임의로 멈출 수 없으므로 이 보장을 못 하면 공통 실행기 단일 문맥 방식을 거부한다.

NES의lease/generation·BG 완료/최종 END·tile_done 검사는 유지한다. 현재 마지막 plan의CHECK에서 mailbox를 반환해도 decoded fields를tile_done까지 register에 보유하므로 안전하다. 이 register까지 없애고 RAM을 직접 읽으면 bank 반환을tile_done 뒤로 미뤄야 하며 별도 credit·ROM 일정 검증이 필요하다. 이번 예산에서 이 저장을 무료 삭제로 세지 않는다.

### 이미 공유된 것과 유지할 독립 검사

- SPI status snapshot은이미 하나이며 request/status CRC8도공유한다. plan CRC는`SHARED_CRC307=1`이다. 이를 다시 제거할 CRC/snapshot으로 계산하지 않는다.
- accepted/retired/consumed는각각 저장 수락/저장 재사용/실제 소비를 뜻한다. 하나의 완료 counter로 합치지 않는다. E1 sequence와host packet_seq를하나로 만들려면 불변FIFO·epoch·gap/duplicate/wrap·STOP에 대한 별도 증명이 필요하므로 당장은 유지 비용으로 둔다.
- source NES clock, SPI/host clock, plan NES clock의CDC와bank 소유권은 남는다. 통합 host FSM이 cross-clock mailbox를 없애주지 않는다.
- 독립 expected 저장과 실제 SNES read CRC/coverage/private job/final scan을 producer progress로 대체하지 않는다. STOP은부분 record·pending write·미공개 slot을 취소하고 token/lease 재사용을 차단한다. queue empty나plan seal만으로 최종 ACK/VBlank 표시를 승인하지 않는다.

## 정규화의 시간 비용도 포함한다

338 실제 plan 기록을32B 내부 slot으로 모델링한 값이다. 추가 READ/CAPTURE를byte당2NES클록으로 계산했으며 stall·검사·제어 클록은 별도다.

|프레임|plan 수|추가 내부 byte|추가 순차 read 산술|32회 초기화/plan 산술|
|---|---:|---:|---:|---:|
|905|93|2323B|0.211182ms|0.035429ms|
|906|91|2275B|0.206818ms|0.034667ms|
|907|9|231B|0.021000ms|0.003429ms|

이 확장을 wire에도 적용하면905는7.079619ms,907은0.704ms의SPI가 추가된다. 따라서32B wire 전송은 후보에서 제외한다. 내부 read 비용도 무료가 아니며 first plan 승인·후속 tile 공급·staging 경합에 실제로 포함해야 한다.

## 동일 위상·연속 일정 예산

338 고정907은시작 후8.381149ms에첫 ROM 요청을 냈고, 이전 허용창 종료는6.089722ms다. 그 창에 닿으려면 최소2.291427ms를 앞당겨야 한다.347의375wireB 감소는wire만1.142857ms,decoder19562명령 감소는CPI1/84MHz 환산0.232881ms다. 둘을 직렬로 모두 줄인다는 **조건부 산술**에서도1.375738ms이며 요청 선행량0.915689ms가 남는다. 이것은 새 요청 시각의 예측·상한이 아니고, SPI bank·poll·IRQ·준비 배치가 바뀌면 다시 측정해야 한다.

first request<=6.089722ms는 필요조건일 뿐이다. 실제 전체 완료<=16.666667ms와post-ROM<=3.180ms 목표를 함께 검사한다.338 고정post-ROM3.833249ms에서이미0.653249ms를 줄여야 하며 새 plan read21µs도 그 안에 들어가야 한다. 새로운 CPU/IRQ 중첩을 무료로 넣거나 wire 감소량을 전체 시간에서 직접 빼지 않는다.

동일 시작·ROM phase와905→906→907 연속 일정을 각각 실행한다. 기존346의제한 연속20.690661/고정25.056927/일반11.998038ms를구분했던 것처럼, 일반 ROM 개선이나이전 cold 프레임의종료 시각 변화를제한 ROM 개선으로 바꾸어 보고하지 않는다.347은새 통합 일정이 없으므로4.023ms 부족이 줄었다고 주장하지 않는다.

## 전체 Quartus Lite 채택 상한

이 수치는 새 MAP 예측이 아니라155comb 여유를 남기기 위한 실패 판정 기준이다. host·queue/SPI·plan 사이의비용 이동을 합쳐서 평가하도록 경계를 바꿨다.

|겹치지 않는 own 범위|338 comb|채택 상한|필요 감소|
|---|---:|---:|---:|
|host+queue/SPI+plan|3418|2044|1374|
|source|1747|1100|647|
|validator/aperture|1159|1159|0|
|외부 유지|10950|10950|0|
|whole|17274|15253|2021|

source가338 크기로 돌아오는 것뿐이라면 공동 제어에서2021개를 줄여1397comb에들어가야 한다. 공동 제어1374개만 줄고source 절감이0이면whole15900으로여전히492개 부족하다. **647/1374개 절감을 뒷받침하는 새 합성 증거는 없다.**346의실제whole17511도보존하며 작은state 공유로이 예산을 달성했다고 해석하지 않는다. 현재307808RAMbits보다늘리지 않는 것이초기 제약이고 M9K packing·LAB/FIT/STA는별도다.

다음 최소 실행은 (A)338 fixed scan의repeat 판정/최종 record builder+336 decoder만 연결해bytes/STOP/첫 ROM 요청을검증하고, (B)E1/E9 공통 transaction 소유자와내부 plan slot 정규화를독립적으로 검증한뒤 결합하는 것이다. 두 후보가전체 시간과whole Lite 비용을함께 줄이는 근거가 생긴 경우에만 다음 통합 후보로선택한다. production227/GBC164/saveSRAM은변경하지 않았으며자동 merge/FIT 반복은하지 않는다.

증거: `analysis/fixed347-verification.json`, 재현: `tools/analyze_nes_fixed347.py`, 실제 decoder 실행: `probes/nes-fixed347/{reference01,arm01,guards01}`.346의1369개pin을재검증했다. 최초 분석은stack-usage 파일명 가정으로실패했고analysis01.log를보존했으며 실제 파일명을찾도록 고친 최종 분석을사용한다.
