# NES353 — 첫 BG 준비와 source/host clock·RAM 경계 재검토

이번 기준은 **338 RTL·352 ARM**이다. 352의 raw 그룹 최적화를 유지했다. 새 실행 제어를 구현하거나 시간 절감을 추가했다고 주장하지 않는다. 실제 M4 준비 함수의 비용을 분해하고, 동일 시작·ROM 위상의 통합 실행에서 clock과 RAM 소유권을 수동 관측했다. 관측 실행의 원래 event CSV·ARM 결과·source cycles는352와 byte 단위로 동일하다.

## 동일 위상과 연속 일정

| warm907 일정 | 시간 ms | 60Hz 예산 초과 ms | 이번 변경량 |
|---|---:|---:|---:|
| 제한 ROM 연속 |20.689660812|4.022994145|0|
| 동일 시작·ROM 위상 |25.051517560|8.384850893|0|
| 일반 ROM 연속 |12.246307588|−4.420359079|0|

고정 위상의 첫 BG 요청은 source 시작7.217890ms 뒤다. 앞선 ROM 창 종료6.089722ms에 진입하려면 **1.128168ms**, CPI1/84MHz 환산으로 최소 **94,767명령의 순감소**가 필요하다. SPI·CDC·IRQ 비용이 늘면 필요한 감소량도 커진다. 첫 ROM accept 뒤3.833568ms에는3.180ms cap 대비0.653568ms가 별도로 남는다. 이 두 수치를 연속 일정의4.022994ms와 합산하지 않는다.

| source 완료→첫 BG 요청 | ARM 명령 | ARM ms | SPI ms | 활성화·clock 정렬 등 잔여 ms | 합계 ms |
|---|---:|---:|---:|---:|---:|
| 제한 연속 |340407|4.052464286|0.464762|0.007651714|4.524878|
| 동일 위상 |340614|4.054928571|0.464761|0.007687429|4.527377|
| 일반 연속 |340404|4.052428571|0.464761|0.007687429|4.524877|

세 구간 모두 checkpoint31회, IRQ 대기0회다. 따라서 이 구간을 polling 대기 제거만으로1ms 이상 줄일 수 있다는 근거는 없다. 실제 IRQ 처리는 기존 일정 모델에 남아 있다.

## 준비 함수에서 실제 줄여야 할 것

352의 실제 ELF와 input_commit 직전 snapshot을 재사용했다. geometry 내용이 변하지 않는 준비 함수를 다시 실행해 기록된 명령 수와 일치시켰다. cold의 expand는 geometry seal 뒤 phase2, warm은 같은 block에 raw seal까지 있어 phase0였다는 차이를 보존했다. geometry 재실행은 context의 phase만 준비 진입 상태로 복원했다. 이는 재실행 프로파일이며 새 planner나 새 전체 실행 결과가 아니다.

| warm907 함수 | 전체 명령 | 자기 함수·wrapper | memcpy | memset | 나머지 |
|---|---:|---:|---:|---:|---|
| expand286 |70407|32840|19710|8197|need286 9650, geometry_ready 9, return 1|
| geometry_plan286 |35879|25164|0|4489|fine 6225, return 1|
| h2early286 |12060|6609|0|1134|CRC 4316, return 1|

표는 실행 PC를 함수별로 배타적으로 분류했다. 하위 함수 비용을 상위 전체에 다시 더하지 않는다. 세 함수의 memcpy/memset 합계는33530명령, **0.399166667ms**다. 모두 무료라는 불가능한 가정에도 필요한1.128168ms 중 **0.729001333ms**가 남는다. 정렬된 word 복사·초기화는 보조 후보일 뿐, 단독 해법이 아니다.

초기 top-level 준비는 expand70407 + begin7577 + geometry35879 + H2 12060 + input_commit2641 + begin_step39075 =167639명령이다. 첫 BG 요청 전 전체340614명령과 같지 않다. 이후 row 계산·plan 생성·serializer/서비스 비용도 존재한다. 초기 세 함수만으로94,767명령을 줄이려면118346명령의 약80%를 제거해야 하므로, 기존 검사를 그대로 수행하면서 함수 몇 개를 합치는 것만으로 달성 가능하다고 보지 않는다.

### 비교한 다음 후보

| 후보 | 실제 삭제/이동하려는 작업 | 아직 필요한 증거 | 현재 판정 |
|---|---|---|---|
| word 단위 copy/clear | byte loop 반복 | 정렬·tail·alias와 전체 호출 비용 | 단독으로 ROM 창 진입 불가. 최대 절감 상한조차0.399ms |
| compact geometry 직접 사용 + 증분 준비 | N5 compact 값을 native64bit 배열로 복사·확장한 뒤 다시 해석하는 반복 | 동일 의미검사, 예외/row 그룹 경계, tag membership, source history 수명, 실제 M4 순절감 | 우선 검토할 ARM 후보. 새 코드·실측 이득은 아직 없음 |
| 기존 BG frontier 조기 flush | 완성된 일부 plan을 일찍 전송 | 낮은 slot의 미래 할당과 batch/credit 순서 |342에서 warm frontier가 slot8에 막혔고344의 순서 변경도 회귀. 같은 안을 새 이득으로 재사용하지 않음 |
| source 실행기를 host clock으로 이동 | source/host FSM·주소 진행의 배타적 제어 | 아래 query CDC·plan cursor·RAM 수명 및 whole MAP | 단순 이동은 미채택. 시간·면적 순이득이 미입증 |

compact geometry 후보는 검사 삭제가 아니다. count/tag/raster/exception/HDMA 검사를 직접 compact view에서 수행해 중간 표현의 복사·재해석을 없애는 방향이다. 현재 source history를 다음 입력까지 빌려 쓰려면 표시 중 불변 소유권을 명시해야 한다. immutable block에서 내부 준비를 앞당겨도 전체 source CRC·COMMIT 전 외부 plan 공개는 허용하지 않는다. raw/required union과 이전 표시 material의 수명 문제를 다시 만들지 않는다. 별도 shadow RAM·refcount table·새 E9/credit 비용도 무료로 두지 않는다.

## 실제 clock·RAM 관측

`probe_nes_boundary353.py`는 RTL 신호를 관측할 뿐 구동하지 않는다. source A write가 output phase에 나타나거나 plan cursor가 input phase에 진행하면 즉시 실패한다. 905..907의 실제 기록은 다음과 같다.

| frame | collector query | source A write | validator B write | plan step/reset | queue write |
|---|---:|---:|---:|---:|---:|
|905|1959|5580|4044|646/10|8699|
|906|1957|938|3070|631/9|8867|
|907|1957|1055|500|56/4|569|

source A의 관측 쓰기 주소는512..904였고 모두 input phase였다. phase RAM의 전체 배정 범위512..1023가 전부 사용됐다고 주장하지 않는다. cold905의 input-phase B write970회는 초기화이며 마지막12.366µs, 첫 source A write14.906526ms보다 앞선다. warm의 input-phase B write는0이다. plan step/reset은 모두 output phase였다. 이번 세 정상 관측에서는 plan step과 host의 비IDLE/DONE 상태가 겹친 사례는0이었다. 이 사실은 모든 backpressure·STOP 조합에서 두 실행기를 직렬화할 수 있다는 증명이 아니다. plan payload RAM, tile ROM 소비와 host queue는 별도 수명을 유지한다.

중요한 기존 공유는 encoder의13bit `cursor`다. 입력 때 source 주소를 진행하고, `V_IDLE`에서 `plan_zero319/plan_step319`를 받아 NES plan payload의10bit 주소로 재사용한다. 따라서 encoder를 host clock으로 옮기면서 이 cursor까지 옮기면 NES plan read와 동기 RAM 응답 계약이 깨진다. 최소한 NES 쪽10bit plan cursor와 해당 reset/STOP 경계를 남기거나 별도 새 CDC를 입증해야 한다. 기존 공유를 잃는 비용은 추가 비용이다.

source phase RAM은 A=`clk`, B=`host_clk`의1024×8 dual-clock RAM이다. A를 host 실행기로 옮기면 clock은 같아질 수 있지만, 주소 선택·1clock read 응답·validator 초기화/STOP 억제까지 다시 연결해야 한다. host queue의 port A ingress와 port B 실행은 이 RAM과 다른 저장소다.350에서 실제 cold ingress/consume 동시 사용이 있었으므로 queue를 한 port로 직렬화하는 절감은 인정하지 않는다.

## Query CDC와 전체 회로 예산

현재 query→response는 NES 한 clock이다. trace의 `$time` 반올림 때문에45/46ns로 기록되며, 실제 NES 주기는45.454ns다. warm마다1957번 요청한다. host clock 실행기에서 이 인터페이스를 직접 쓰면 안 되고, 안정된 request/response와 STOP 취소를 갖춘 clock crossing이 필요하다.

기존 mailbox206을 그대로 쓴다고 가정한 **선언 저장량**은 다음과 같다. 이는 합성 FF 수나 comb 절감 예측이 아니다.

| 경계 | payload | mailbox 내부 선언 bits |
|---|---|---:|
| 새 query request |kind3+index13+generation16=32|80|
| 새 query response |hit1+data64=65|146|
| 새 두 mailbox 합계 | |226|
| 기존 source descriptor2개+input ACK |40×2,17|242|

기존 source descriptor/input ACK mailbox를 전부 제거할 수 있다고 해도 새 query mailbox226bits와 NES plan cursor10bits만으로 gross 차이는6bits까지 작아진다. 추가 lease/phase/abort·query 소유권은 아직 포함하지 않았다. 반대로 기존 q_held 등과 alias할 여지가 있어 실제 저장량은 구현 후 달라질 수 있다. 어느 경우든 이 산술로 comb1873개가 줄었다고 주장할 수 없다. mailbox는 두 단계 동기화 외에 capture·valid·소비·ACK가 있으므로 query 왕복을 단순2FF 지연으로 계산하지 않는다.

같은 clock으로 옮기는 것만으로 source 작업 시간이84/22 비율로 줄어든다고 계산하지 않는다. input SPI·block 소비 대기, query 왕복과 prefetch가 남는다. query를 묶거나 NES 쪽 local reader를 남기는 대안은 새 buffer·진행 제어·CDC를 포함해야 한다. local reader에 기존 codec 제어를 대부분 남기면 source FSM을 삭제했다는 예산도 철회해야 한다.

whole Quartus Lite 결과는 byte 동일 RTL에 대해352가 검증한 **22144LE /17274comb /9018FF /307808bits**를 재사용한다. 장치 대비1866comb 부족,155comb 여유를 둔15253cap까지2021개 순삭제가 여전히 필요하다. 새 RTL이 없어 MAP/FIT를 반복하지 않았다.

| 전체 예산 | 현재comb | 목표cap |
|---|---:|---:|
| source+host, 새 query CDC/phase/plan cursor 비용 포함 |3908|2035|
| queue+SPI |798|650|
| 기존 plan 영역 |459|459|
| 독립 checker+aperture |1159|1159|
| 그 밖의 보드 |10950|10950|
| 합계 |17274|15253|

2035는 공통 실행기만의 cap이 아니다. 새 CDC·남겨 둘 NES cursor·RAM owner까지 모두 들어가야 한다. 추가 비용을B라고 하면 순수 실행기 cap은2035−B다. B와 새 실행기 비용은 아직 `null`이며,2021개는 목표이지 확보한 절감이 아니다. register 명칭 변경이나 이미 합성에서 제거된 선언을 삭제 실적으로 세지 않는다.

## 다음 실행 조건과 보존

1. 352 ARM을 유지한 compact geometry/증분 준비 후보에서 기존 의미검사를 유지하고, 중간 표현·복사·재해석의 실제 삭제 목록을 만든다. 같은 raw/geometry 입력의 실제 M4 검사와 first-BG 전체 순절감을 측정한다. memory loop 단독이나 실패한 frontier를 반복하지 않는다.
2. source→host 공통 실행 후보는 collector query, NES plan cursor, phase RAM A/B, queue ingress/consume, input lease→display lease의 clock별 소유권·완료·STOP drain을 먼저 고정한다. 새 CDC 비용을 포함한2035cap의 근거가 없으면 큰 RTL 교체를 시작하지 않는다.
3. 정당화된 후보만 같은 시작·ROM 위상과 연속 일정, 실제 ARM/IRQ/2슬롯/ROM 경쟁, 같은 경계의 whole Lite MAP으로 평가한다. 독립 expected/read CRC/coverage, 최종 ACK·VBlank를 유지한다.

새 측정은3프레임의 수동 포트 관측과9개 준비 함수 재실행이다. 세 일정9관측과352의decoder71프레임·77사례/ARM65사례는 그대로 재검증한 기존 증거이며 새 실행으로 세지 않는다. whole firmware RUN·물리 WCET·전체65816·FIT/STA·물리60fps는 미검증이다. Production227/GBC164/saveSRAM은 변경하지 않는다.

arm01/02의 초기 프로파일은 cold와warm의 geometry-ready phase 차이를 같게 둬3명령 assertion에 실패했다. 실제 block 경계를 반영한arm03에서9개 명령 수가 모두 기존 기록과 일치했다. 실패 디렉터리와 원본 로그를 보존했다. 자동 merge하지 않는다.
