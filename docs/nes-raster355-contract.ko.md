# NES355 compact raster·query STOP drain 경계 검증

## 적용 범위와 ARM 표현

통합 RTL은338을 유지하고354 ARM의 활성 레코드 단일 준비 및352 raw-group 최적화를 보존한다. N5의16bit compact raster를224행/448B 그대로 planner 저장소에 둔다. 기존64bit로의 확장·저장은 이 경로에서 제거한다. mask는 frame 공통1B이며 compact 표시와 함께 기존 구조의 padding에 들어간다. 네이티브 raster 저장소1792B의 크기는 통제 비교를 위해 유지하므로 ARM RAM1344B를 회수했다고 세지 않는다. 모든 RAM object 주소·크기가354 ELF와 동일함을 확인한다.

geometry·H2·dirty material·최종 raw table/BG 처리의 읽기를 compact 접근자로 연결했다. geometry는 호출 진입 시 compact/native64 표현을 한 번 선택한다. native64 직접 호출과 기존 generic receiver는 기존 의미검사를 가진 경로를 사용한다. 하나의 input을 두 receiver 사이에서 reset 없이 교차 재사용하는 전환은 이번 검증 범위가 아니다. 실제 통합 일정은 N5 receiver만 사용한다.

compact 경로에서도 raw의 예약 비트·low bits·slot 순서·patch count,normal의 예약/slot 비트·row group·palette epoch·display mask,예외 중복/범위·tile 요구 목록 검사를 유지한다. 실패는 출력 계획으로 공개하지 않는다. history를 빌려 쓰는 포인터나 새 shadow RAM,source wire 변경은 없다.

## 먼저 제외한 접근 비용과 선택한 경계

같은354 warm snapshot을 실제 M4로 재실행한 결과다. 하위 함수 비용을 중복 합산하지 않는다.5호출 합계는 전체 프레임이나 첫 BG 구간 전체가 아니다.

| 후보 | expand | geometry | H2 | input commit | begin step | 5호출 합계 |
|---|---:|---:|---:|---:|---:|---:|
|354|53129|35879|12060|2641|39075|142784|
|dual-per-access|52393|51538|12518|2641|41554|160644|
|dual-inline|52393|43230|12518|2641|39533|150315|
|entry-selected|52393|32548|12518|2641|39533|139633|


매번 표현을 검사하는 첫 후보와 접근자 호출만 inline한 후보는 회귀했다. geometry 진입점 선택 후보만 전체 일정에 연결했다. H2와 begin-step은 각각458명령 늘었으므로 geometry 절감만 보고 전체 이득을 산정하지 않는다. Warm 전체 ARM 명령은549015→546216으로2799개 감소했다. 코드 증가도 포함해 `.text`32014B(+1384),`.bss`47420B,관측stack1288B다.

71개 기록 geometry는 정규화한 활성 입력/video/H2가354와 일치했다. 비활성 map/OBJ/예외 꼬리와 compact raster 뒤1344B에 poison을 넣어도 같다. malformed13개·count 경계5개와 별도로, 준비 후 compact high bits/raw low bits/raw slot/normal slot/mask/palette를 손상시킨6개를 독립 geometry 검사가 거절했다. native64 직접 geometry 호출도354와 일치한다. 이는71개 전체 프레임 실행이나 모든 generic API 전환의 검증은 아니다. 실제 통합 snapshot의352 표시 이력/cold/STOP/COMMIT65사례도 재검증했다.

build01은 생성기의 return 공백 오류,build04는 legacy source receiver를 함께 바꾸지 않은 단일 표현 실험의 compile 실패다. 둘 다 보존한다. build02/03의 비용 회귀를 보존하고 build05를 선택한다. 실제 schedule ELF와 build05의 PT_LOAD 동일성을 확인한다.

## 동일 위상·연속 전체 일정

| warm907 일정 |354 기준(ms)|355(ms)|차이(ms)|
|---|---:|---:|---:|
|제한 ROM·연속|20.689660812|20.689660812|+0.000000000|
|제한 ROM·동일 시작/위상|25.051517560|25.051517560|+0.000000000|
|일반 ROM·연속|12.040582784|12.007265002|-0.033317782|

실제3프레임×3일정에서 source/RTL/기존 CPU trace,전송 내용·순서,독립 read→private receipt→token ACK 공개 및2슬롯 credit을 대조했다. 동일 위상의 각 프레임 시작시각·ROM cycle도 같음을 확인했다. 첫 BG 요청은7.012165→6.962939ms다. 앞선 ROM 창의 끝6.089722ms까지 **0.873217ms(최소73,351명령)**가 더 필요하다. 이후 ROM accept→완료의 별도0.653568ms 부족과 연속 전체4.022994ms 초과분을 단순 합산하지 않는다.


실제 M4 명령+CPI1/84MHz,live SPI·IRQ·2슬롯·staging·ROM 경쟁을 포함한다. ordinary65816 trace는 이전 것을 재사용하며 map/tile/final display는 기존 bus model이다. whole firmware RUN·전체65816·물리 WCET·물리60fps 결과가 아니다. 독립 final expected/CRC/coverage,12B display context 읽기,정확한 token ACK 뒤 lease 해제 assertion과 기존 VBlank 계약은 유지한다.

## 새 query CDC·STOP drain·NES plan cursor 경계

`nes_query355.sv`는 host 실행기로 이동할 source의 최소 경계 후보다. 실제338 source/host에 연결하거나 기존 제어를 삭제한 결과가 아니다. request(kind3/index13/generation16)32bit와 response(hit/data64)65bit를 기존 mailbox206으로 보낸다. 한 transaction만 outstanding으로 허용하며 request/response 값은 상대방이 소비할 때까지 고정한다.

- STOP은 host에서 새 요청과 응답 공개를 즉시 막고 NES에 level로 전달한다. 이미 수락한 collector query는 늦은 응답까지 기다려 폐기한다. 아직 발행하지 않은 요청은 query 없이 실패 응답으로 drain한다.
- host busy,request mailbox 반환,response mailbox 반환,NES idle을 모두 확인한 뒤 drained를 공개한다. 이때만 BEGIN을 수락하며,STOP 해제를 NES가 관측한 뒤 host active를 다시 올린다. generation 일치만으로 오래된 응답을 재사용하지 않는다.
- soft STOP으로 한쪽 mailbox만 reset하지 않는다. 공통 reset assertion과 각 clock의 동기 release를 사용한다. NES clock 정지 시 drain 완료를 기다려 재시작을 막는다.
- plan cursor10bit는 NES clock에 남는다. host clock 정지 중에도 허용된 display phase에서만 진행한다. query가 진행 중일 때 phase를 넘기면 cursor 진행을 차단하고 owner fault 및 실패 응답을 낸다. display phase에 새 query가 도착하거나 input phase에서 plan step이 들어와도 실패 처리한다.

3개 clock 위상(0/3.1/11.8ns)에서 각93개,총279개 사례가 통과했다. STOP을 요청 수락·응답 공개와 같은 edge에 넣는 경우,수락 후32개 host-edge 위치의 취소,늦은 응답,host/NES clock 정지,동일 generation/index 재사용,plan wrap/phase 충돌,clock 정지 중 공통 reset을 포함한다.

첫 query01에서 **STOP 관측 뒤 cursor clear 전에 host drained가 먼저 올라오는 오류**를 검출했다. host가NES보다 빠르기 때문에 stop 동기화만으로는 로컬 처리 완료를 보장하지 못했다. `stop_applied`로 NES 로컬 STOP 처리 완료까지 확인한 query02가 최종이며,같은 소스를map04에 사용했다. 실패 로그와 이전map01..03을 보존한다.

정상12개 요청의 host 수락→응답 ready는380..393ns다. 기존NES 내부 query의45.454ns와 인터페이스 범위가 다르며 전체 source 지연으로 직접 치환하지 않는다. 단순 직렬 민감도에서는1957회 차이가 약0.655..0.680ms지만 실제codec/pre-fetch/SPI와 겹치는 양은 아직 측정하지 않았다. 이 비용을0으로 두거나 ARM의33µs 절감에서 공제했다고 주장하지 않는다.


이 경계에는 실제 collector의 RAM 및 source codec·host 실행기가 없다. unit의 collector는32bit 요청 전부로 응답을 만들고, 재시작마다 별도 salt를 바꿔 같은 generation/index의 늦은 이전 응답을 식별한다. collector 정상 응답은NES 한 clock이고 delay/clock pause를 별도로 주입한다. host 요청 데이터와 collector 응답 데이터를 수락 뒤 바꿔도 mailbox 값이 유지되는지 검사한다. 논리 시뮬레이션이며 metastability/FIT/STA sign-off는 아니다.

## 전체 Lite 비용과 다음 교체 예산

통합 일정의 RTL이338과 byte 동일하므로 whole Lite는 **22144LE/17274comb/9018FF/307808bits**를 재사용한다. **1866comb 부족은 그대로**다. 여유155개를 두는 cap15253에는2021개 순삭제가 필요하다.

새 경계 최종 map04는 standalone **372LE/125comb/339FF/0RAM**이다. map01은 local release 보완 전,map02는 query/plan 충돌 검사 전,map03은 STOP 로컬 처리 완료 확인 전 결과이며 선택하지 않는다. source/host를 지우지 않은 추가 경계 합성으로 whole 개선을 주장하지 않는다. 기존 mailbox의 선언242bits와 새 경계339FF도 서로 다른 측정이므로 직접 뺄 수 없다. 기존 q_held/result/address 저장의 alias는 실제 통합 후에만 인정한다.

source+host3908→2035cap에는 이 query CDC·controller·NES cursor·RAM owner 비용이 전부 들어가야 한다. standalone125comb를 별도 유지한다고 가정하면 나머지 실행기의 조건부 상한은1910comb다. 이는 회수 실측이나 통합 MAP 예측이 아니다. queue+SPI798→650,기존 plan459/checker·aperture1159/기타10950 유지 조건도 여전히 남는다. phase RAM A/B와 queue ingress/consumer의 실제 동시 접근을 없앤 증거는 아직 없으므로 RAM port나 독립 검사 비용을 삭제하지 않는다.

Quartus Lite는 기존 mailbox와 새 경계의 `async_reg` 속성을 인식하지 않았다는 경고를 냈다. 논리 동기화 체인은 합성되지만 적절한 Quartus CDC/배치 제약과 STA는 추후 전체 통합의 별도 gate다. 현재 MAP을 CDC sign-off나 보드 FIT 성공으로 취급하지 않는다.

다음은 더 많은 accessor 분기/코드 복제로 좁은 이득을 반복하기보다 compact raster의 공통 row 의미검사·H2/raw-table 준비와 실제 소비 순회를 함께 줄일 범위를 정한다. FPGA는 검증한 경계에 source 실행을 연결할 때 기존 descriptor/ACK mailbox,source/host 주소·응답·진행 제어의 실제 삭제 목록과 새 비용을 같은 whole MAP으로 확인해야 한다. 새 CDC의1957 query 왕복을 SPI/pre-fetch와 얼마나 겹칠 수 있는지는 아직 미측정이므로 ARM 절감에 무료로 더하지 않는다. production227/GBC164/saveSRAM 및 자동 merge는 변경하지 않는다.
