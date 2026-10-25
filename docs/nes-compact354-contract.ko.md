# NES354 compact geometry 단일 준비와 clock/port 교체 계약

## 변경 범위

338 RTL과352의 source decoder·changed raw-group 처리를 유지한다. `nes_compact354.py`는 기존 native 생성기를 호출한 뒤 `expand286`의 map·OBJ·예외 복사와 요구 tile 수집을 한 순회로 합친다. count를 먼저 검사하고 compact history에서 바이트로 읽어 정렬·alias 가정 없이 값을 만든다. 각 활성 레코드의 예약 비트 검사 후 native 배열에 한 번 저장하고 required 비트맵을 갱신한다. 사용하지 않는 배열 꼬리는 복사하지 않는다.

warm907의 map957/OBJ8/예외0에서 배열 복사는3936B에서2266B로1670B 줄었다. rows224B와 palette64B는 유지한다. required 초기화·정렬 tile 목록·compact raster 의미검사·native64 raster 변환은 유지한다. geometry planner의 row/exception/HDMA 검사와352 raw material 검사를 제거하지 않았다. 다음 입력까지 history를 빌려 쓰는 포인터 ABI나 새 shadow RAM은 없다. 입력 준비 실패는 FAILED 상태로 남고, 실제 COMMIT과 외부 plan 공개의 기존 경계도 유지한다.

이번 수정은 모든 중간 표현을 없앤 최종 구조가 아니다. native64 raster의 저장 및 geometry/H2에서의 재해석은 여전히 남는다. generic native API와 구조 크기도 그대로이며, 실제로 줄인 것은 활성 compact 레코드의 복사·재읽기와 비활성 꼬리 복사다.

## 실제 검증 범위

`check_nes_compact354.py`는352/354 ELF의 모든 RAM object 주소·크기가 같은지 확인한 뒤 동일한 준비 snapshot에서 실제 M4를 실행한다. 기록된71개 geometry의 활성 planner 입력, video 결과, H2 certificate를 바이트 단위로 비교한다. 후보의 비활성 목적지 꼬리를0xA5로 채워도 결과가 같다. 이는71개 전체 프레임 실행이나 새 source CRC admission 검사가 아니다.

13개 malformed count/예약 비트/mask 사례, 최소·최대 count 및 예외1개,128개 예외 뒤 중복 예외,마지막 OBJ의 예약 비트를 추가로 비교했다. 최대 범위에서도 기존 planner의 독립 예외 검사까지 유지된다. 최초 guards01은 정상71사례 후 Python의 bytearray를 Unicorn에 전달한 harness 오류로 중단했다. bytes 변환 후 guards02 통과, 경계 사례를 추가한 guards03을 최종으로 선택하며 실패 증거는 보존한다.

전체 일정은 실제 M4 명령을CPI1/84MHz로 환산하고 live SPI·IRQ·2슬롯·staging·ROM 경쟁에 연결한다. ordinary는 기존65816 trace를 재사용하고 map/tile·최종 display는 기존 bus model 범위다. 이번에 전체65816 실행이나 물리 VBlank 완료를 새로 증명한 것은 아니다. 독립 final 검사,12B display 문맥 읽기,정확한 token ACK 후 lease 해제 assertion은 유지한다.

## 전체 시간과 회로 비용

| warm907 일정 |352 기준(ms)|354(ms)|차이(ms)|
|---|---:|---:|---:|
|제한 ROM·연속|20.689660812|20.689660812|+0.000000000|
|제한 ROM·동일 시작/위상|25.051517560|25.051517560|+0.000000000|
|일반 ROM·연속|12.246307588|12.040582784|-0.205724804|

9개 일정 관측(서로 다른3프레임)의 전송 내용·순서, DMA read→private receipt→token ACK 공개와2슬롯 credit을 검증했다. source decoder·비용표·RTL·CPU trace는352와 동일하다. Warm expand는70407→53129명령(-17278),기록71사례 절감은17198..17278명령이다. 최소/최대 count에서도48956→30722 및77461→60890명령으로 줄었다. `.text`30630B(-8),`.bss`47420B,관측stack1288B다.

동일 시작/위상은 기존 시작시각과 ROM cycle을 각 프레임에 대해 정확히 비교했다. Warm 첫 BG 요청은7.012165ms로0.205725ms 빨라졌지만 앞선 ROM 허용 구간의 끝6.089722ms까지 여전히 **0.922443ms(최소77,486명령)**가 부족하다. ROM accept 이후 완료는3.833568ms이며 별도3.180ms 예산 대비0.653568ms가 남는다. 이 기준들을 연속 일정의4.022994ms 초과분과 단순 합산하지 않는다.

새 RTL 변경이 없으므로 byte 동일338의 whole Quartus Lite **22144LE /17274comb /9018FF /307808bits**를 재사용한다. 새 MAP 결과가 아니며 **1866comb 부족과2021comb 순삭제 목표는 그대로**다. 이번 실제 확보는 ARM 준비 비용 절감이며 제한 ROM 전체 프레임이나 회로 절감으로 환산하지 않는다.


## source·host 교체의 clock별 계약

아래는 다음 RTL 교체에 필요한 계약과 예산이다. 이번 ARM 개선에 적용한 새 회로나 CDC 검증 결과로 세지 않는다.353의 실제 포트 추적과338의 RTL을 기준으로 정한다.

| 자원/단계 | 유지할 소유권 | 교체할 때 필요한 동작 |
|---|---|---|
| collector query | collector는 NES clk, capture lease 동안 source 내용 불변 | host 요청을 kind/index/generation 단위로 고정하고 NES 도메인에서 한 번만 수락 |
| query 응답 | NES에서 collector 응답을 확정 | hit/data를 host까지 안정적으로 전달하고 소비 ACK 전 재사용 금지 |
| source cursor | 현재 NES의13bit cursor가 source와 plan에 재사용됨 | source 주소를 host로 이동해도 NES10bit plan cursor는 남김; plan_zero/step 및 동기 read 계약 유지 |
| phase RAM A | 현재 NES source, input phase | host source로 이동하려면 주소/쓰기/응답을 host에 연결; 단순 clock 치환만으로 완료하지 않음 |
| phase RAM B | host validator, cold 초기화·expected·receipt | A/B 주소와 read 응답 소유자를 분리; cold 초기화와 source 시작 barrier 유지 |
| queue RAM A/B | ingress 저장과 실행 소비가 실제로 동시 발생 | 두 포트 유지. 저장 credit 반환과 실제 소비 완료를 합치지 않음 |
| plan RAM·tile ROM | NES plan cursor와 공급 일정 | host가 준비 중이어도 DMA/plan 진행을 막지 않음; 별도 동시 경로를 FSM 공유 이득으로 삭제하지 않음 |

host query 이동 후보는 한 outstanding transaction으로 시작하는 편이 작은 계약이다. 기존 mailbox206을 사용할 경우 request payload32bit와 response65bit가 각각 held/received 저장과 request/ACK 동기화·capture·valid 단계를 갖는다. NES collector 응답1clock 뒤에도 host 수신과 소비 완료가 필요하다. 단순2FF 왕복이나84/22배 source 가속을 가정하지 않는다.1957 warm query의 추가 지연은 prefetch와 SPI 대기 중 실제로 숨겨지는 부분만 중복 차감한다.

### STOP과 재시작 순서

1. STOP 시 새 query·plan 발행과 RAM write/receipt 공개를 차단한다. 현재 frame lease를 무효화하고 final ACK를 거부한다.
2. 이미 수락한 query/response는 두 도메인에서 소비 완료까지 drain하되 폐기한다. 오래된 응답이 새 source cursor나 RAM에 쓰이지 않도록 cancel 상태를 유지한다.
3. request/response mailbox 모두 idle이고 RAM read 응답·source bank·queue 소비가 정리된 뒤 새 BEGIN을 허용한다. generation 값 일치만으로 오래된 응답을 구분하지 않는다.
4. mailbox206은 공통 reset과 각 도메인의 동기 release를 전제로 한다. soft STOP에 한쪽 endpoint만 reset하는 방식은 금지한다. 한쪽 clock이 멈추면 drain을 기다리는 동안 재시작도 보류한다.

이 drain 계약이라면 새 transaction tag를 무조건 추가할 필요는 없지만, pending/cancel/idle 및 양쪽 완료 동기화 비용은 반드시 포함해야 한다. bounded STOP-to-restart 시간은 두 clock의 진행 조건이 있어야 정의할 수 있다. 아직 이 후보의 RTL·STOP phase sweep·합성 결과는 없으므로 비용을0으로 두지 않는다.

### 삭제·유지·추가 예산

| 항목 | 판정 |
|---|---|
| 기존 source descriptor 두 mailbox와 input ACK mailbox | host에 source·transport 생산을 실제 통합한 경우에만 삭제 후보. 기존 불변 bank/입력 COMMIT 검사까지 없애지 않음 |
| source/host의 순차 RAM 주소·read 응답·진행 FSM | input/output phase가 배타적임을 증명한 부분만 공동 실행. codec와 CRC·독립 expected 계산은 유지 |
| collector query mailbox 쌍 | 새 비용.32+65bit payload의 선언 저장량226bits이며 MAP 비용은 미측정 |
| NES plan cursor10bit·phase/abort/drain 제어 | 새/잔류 비용. 기존13bit source cursor 공유를 잃는 비용 포함 |
| queue의 A/B, 독립 expected/read CRC·coverage, 최종 표시 ACK | 유지. 순차 RAM 공유로 무상 제거하지 않음 |

기존 descriptor/input ACK mailbox의 선언242bits에서 새 query226bits와 NES cursor10bits만 빼도 gross6bits다. 이는 FF/comb 합성 절감이 아니며 drain·phase 제어는 아직 미포함이다. 따라서 source를 host clock으로 옮기는 것 자체를1866comb 해법으로 채택하지 않는다.

`nes_transport257`의 `descriptor0/1`, `publish/sent/busy`, `pop0/1`, `ack_pending/ack_data`는 생산과 SPI 소비를 같은 host 실행으로 묶을 때 검토할 실제 삭제 대상이다. 다만 token, immutable bank의 저장 credit, block CRC, 입력 COMMIT 검사는 새 실행기에 계속 필요하다. `nes_core257`의 `q_held/q_have/q_pending` 및 compact raster 의미검사는 새 query adapter가 맡아야 하므로 전부 삭제 이득으로 세지 않는다. 합성에서 이미 제거된 legacy 상태 선언도 회수량에 포함하지 않는다.

| 구조 대안 | 장점 | 목표를 막는 비용 | 결정 |
|---|---|---|---|
| source 전체를 host로 이동 | 입력과 출력의 주소/진행 제어 공유 가능 | query 왕복 CDC, NES cursor 잔류, drain/phase 제어;1957 query의 실시간 비용 | 큰 교체는 보류. 경계 구현의 순비용부터 측정 |
| NES query/source를 유지하고 host만 공유 | 새로운 collector CDC 없음 | source codec/control 상당량이 그대로 남아 source+host2035cap 근거 부족 | 안전한 기준선이지만 회로 목표 달성안으로 미선정 |

whole Lite의 목표는 source+host3908→2035, queue+SPI798→650이다. plan459, checker/aperture1159, 기타10950을 유지하면17274→15253,2021comb 순삭제가 필요하다.2035cap은 query CDC·잔류 NES cursor·RAM owner·STOP drain을 모두 포함한다. 새 경계 제어 비용을B라고 하면 공동 실행기 자체는2035−B 이하여야 한다. B와 새 실행기 MAP은 미측정이며 확보한 회로 절감은0이다.

## 다음 단계

native64 raster를 직접 compact view로 읽는 다음 후보는 geometry·H2·dirty material·최종 raw table의 모든 소비자를 함께 바꾸고, generic API의 독립 의미검사를 보존해야 한다. 단일 함수의 검사만 생략하는 최적화는 하지 않는다. 첫 BG 이전 실제 순절감과 ROM 창 진입 여부를 기준으로 결정한다.

RTL은 먼저 query 왕복·STOP drain·NES cursor를 포함한 작은 경계 구현의 비용을 측정하고, source+host2035cap에서 실제 삭제할 제어를 명시한 뒤 넓은 교체로 진행한다. 기존350/351 reader 미세조정이나 clock 치환만으로 목표가 달성된다고 보지 않는다. production227/GBC164/saveSRAM은 변경하지 않는다. 전체 firmware RUN·물리 WCET·전체65816·FIT/STA·물리60fps는 미입증이다.
