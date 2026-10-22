# NES280 — raw MASK·검사된 교환과 공통 요청 문맥의 실제 비용

PR130 / `codex/nes-wholepath-boundary-256`. 기준은 NES278의 71프레임 진단 일정과
whole Quartus Lite MAP이며, NES279의 OAM ROM→WRAM DMA를 유지한다.
이번 구현은 source raw codec과 source/plan/output의 **거래 단위 제어**를 교체한다.
host 출력 실행 FSM과 독립 receipt/CRC validator는 유지한다. 이 구분을 회로 절감으로
바꾸어 설명하지 않는다.

NES280: raw를 기존 MASK/base/query 경로로 통합하고 source POP+READ/최종 input ACK 교환 및 source·plan·output 공통 요청 문맥을 구현했다. 실제 ARM codec 71프레임 원본 복원과 SPI47·raw 전환·STOP/최종 ACK 검사를 통과했다. 실제 source codec/control 명령 비용을 block별로 재생한 71프레임의 warm 최대는 16.593392ms(frame954), 한도 초과는 0개다. whole Lite는 17,815comb로 기존과 같아 2,407개 부족하다. host 출력 실행기는 아직 유지되며 공동 시간·회로 후보로 채택하지 않는다.

## 구현한 교체

raw 전용 RAWASK/RAWWAIT/RAWCHECK, raw gather/offset 전송을 없앴다.
geometry와 같은 FETCH/FSTORE/MASK 경로로 raw를 읽고 비교하며, 기존 source base에
512B를 이어 붙였다. query 선행 읽기와 고정 NES A / host B phase RAM 포트를 유지한다.
원본 source serial의 이전 raw가 기준이며, SNES 표시 bank의 데이터와 섞지 않는다.

N5-v2 header의 bit0은 geometry cold, bit1은 raw cold다. 첫 입력과 raw 개수 변경은
raw 전체를 보내고, STOP·오류 뒤에는 reset/cold 절차를 거쳐야 한다. raw block은
68~75의 ID, 8B bitmap, 변경 값이다. 6비트 값은 바이트로 보내며 별도 포장기를 추가하지
않았다. 이 후보는 raw 0~2개에 한정한다. 3개 이상은 RAM에 쓰기 전에 거절한다.
기존 더 큰 raw 형식의 일반 지원을 증명한 것으로 취급하지 않는다.

`base_hi`는 512×8에서 1024×8로 늘어난 single-port M9K다. 총 base 범위는
5,120B이며 4,910B를 사용한다. phase RAM의 세 번째 포트나 클록 mux는 추가하지 않았다.
source FSTORE의 bitmap 쓰기는 기존 deferred slot으로 처리한다. 매 raw2 프레임마다
bitmap 쓰기가 64회 추가되므로, RAM 용량뿐 아니라 실행 비용에도 포함한다.

source D0/D1/D2 거래는 D4 교환으로 대체했다.

- 요청 8B: D4, 이전 token BE16, generation LE16, flags, CRC8, A5.
- 응답 5B: marker/상태, 길이, 현재 token BE16, header CRC8.
- 준비된 block이면 payload와 CRC16 BE를 이어 읽는다. 빈 응답은 총 13B다.
- flags bit0으로 **이미 끝까지 읽고 CRC를 확인한 이전 block**의 POP을 요청한다.
  prefix 검사가 끝나야 이전 bank를 해제하고 다음 bank의 길이·token·CRC를 고정한다.
- 마지막 D5 8B는 마지막 POP과 input COMMIT을 묶는다. 최종 SNES 표시 ACK와는 다르다.
  다음 sealed bank가 남아 있거나 token/generation/read coverage가 다르면 거절한다.
- prefix 뒤 POP을 완료한 다음 응답을 중단하면 token을 되돌리지 않는다. sticky fault와
  공통 STOP/reset 경계로 처리한다. 부분 응답을 재전송 성공으로 취급하지 않는다.

D5는 수신 성공만 승인한다. ARM codec이 실패하면 D5를 보내지 않고 공통 STOP으로
양쪽 history를 무효화해야 한다. 이번에는 ARM decoder의 실패와 RTL STOP 경계를 각각
검사했으며, 실제 source ARM SPI 드라이버가 그 STOP을 발행하는 전체 경로는 미연결이다.
16bit source token 소진도 fail-closed 경계이며 무제한 연속 실행을 증명하지 않는다.

공통 SPI 수신기는 source D4/D5와 plan E9/EA의 인자·CRC8/tail 판정 문맥을 보관한다.
output E1 CRC16 상태도 이 거래 문맥으로 옮겼다. source와 plan의 중복 인자 레지스터 및
queue의 별도 CRC 상태를 실제로 제거했다. 반면 source 두 bank CDC, plan accepted/retiring,
output 4-credit와 ordered ACK는 서로 다른 수명이므로 각각 유지한다.
E9의 payload CRC16은 기존 plan consumer가 독립 검사한다.

## 실제 ARM codec과 비용 반영 범위

새 Cortex-M4 C decoder는 N5-v2 header, serial/epoch, geometry MASK/SHIFT, 두 trailer CRC,
raw bitmap·값 범위·cold coverage와 각 전송 block CRC를 검사한다. 실패하면 speculative
history를 무효화한다. byte-for-byte 원본 복원을 확인하며 CRC 일치만으로 대체하지 않는다.
기존 geometry의 렌더링 의미 검사와 전체 N5 planner/RUN을 새로 실행한 것은 아니다.

별도 ARM 이미지의 text는 1,332B, static state는 28B, 관측 stack은 48B다.
caller history는 4,910B이며 기존 geometry history 대비 raw 512B가 추가된다.
출력 ARM의 기존 4,206B text/612B bss/248B 관측 stack과 별도로 실행했으므로
통합 firmware의 linker 결과나 peak stack으로 단순 합산하지 않는다.

954의 block CRC와 codec 해석은 실제 91,786개 ARM 명령이다.
CPI1/84MHz 민감도로 약 1.093ms이며, 이를 무료로 두었던 NES279의 조건부 시간과
직접 동일시하면 안 된다. prefix·응답 CRC8 검사도 실제 token/generation/length마다
다시 실행하여 거래별 명령 수를 구했다. 대표값 하나를 모든 거래에 적용하지 않는다.

연결 시험에서 source SPI는 TB consumer가 구동하고, 실제 ARM 명령 비용을 block 검증 후
POP 전에 재생한다. 각 payload·block 경계는 해당 ARM 실행 입력과 정확히 같아야 한다.
출력 serializer/refill과 IRQ body는 기존처럼 실제 ARM 명령을 live RTL에 연결한다.
이것은 source/출력 전체 firmware나 NVIC preemption의 실행 증명이 아니다.
CPI1은 하드웨어 cycle 상한이 아니며 SPI 드라이버·전체 planner·full RUN 비용도 남는다.

## 전체 일정

OAM 커널은 NES279에서 검증한 544개 실제 65816 명령 trace다. 일반 DMA·OAM DMA,
host CRC tap, DMA 뒤 ordered ACK, receipt·최종 표시 경로를 유지했다.
map/tile/final display는 기존 모델 경계이며 live CPU/FPGA 동시 실행과 구분한다.

|일반 조건|278 진단|280 진단|차이|60fps 시간 한도 대비|
|---|---:|---:|---:|---:|
|952|17.328610ms|15.337180ms|-1.991431ms|-1.329487ms|
|954|18.180055ms|16.593392ms|-1.586663ms|-0.073275ms|
|955|17.174976ms|15.070046ms|-2.104929ms|-1.596620ms|
|962|17.419518ms|15.633540ms|-1.785979ms|-1.033127ms|
|963|16.707390ms|14.801186ms|-1.906204ms|-1.865481ms|
|968|15.477223ms|13.566474ms|-1.910750ms|-3.100193ms|
|970|17.684424ms|16.002626ms|-1.681798ms|-0.664041ms|

|제한 ROM|278|280|차이|
|---|---:|---:|---:|
|905|90.225463ms|89.483199ms|-0.742264ms|
|906|114.266947ms|113.828089ms|-0.438858ms|
|907|18.372461ms|18.590413ms|+0.217952ms|

제한 ROM 세 프레임의 절대 종료는 264.957002→263.993832ms다. 전체 source payload는 83,240→47,900B다. 954의 source 구간은 5.424799ms, 출력 구간은 11.168593ms다. 위 시간은 실제 재연결 진단이며 전체 게임 프레임의 실기 시간 상한이 아니다.

954에서 일정과 polling을 고정하고 source codec만 CPI2로 늘린 산술 민감도는 17.686082ms다. 한도를 채우는 source codec CPI는 약 1.067이다. 이는 CPI2로 실제 일정을 재실행한 결과나 전체 ARM CPI 상한이 아니며, 추가 비용을 흡수할 여유가 작음을 보여준다.


제한 ROM은 전역 slot 위상이 유지되는 fixture다. 따라서 source를 빨리 마치면
다음 구간의 대기와 E2 횟수가 달라진다. 구간 길이와 절대 종료 시각을 함께 기록한다.
SPI wire 절감, source WAITACK, polling 절감을 각각 더해 중복 차감하지 않는다.
source 준비·blocked·WAITACK 카운터는 재생된 거래·ARM 비용과 이미 겹친다.
capture와 다음 프레임의 overlap, active VBlank, full RUN, physical 60fps는 미검증이다.

## 전체 회로 게이트

|동일 whole MAP 경계|278|280|차이|
|---|---:|---:|---:|
|LE|22,730|22,754|+24|
|comb|17,815|17,815|+0|
|FF|9,077|9,127|+50|
|RAM_bits|303,712|307,808|+4,096|

장치 조합 논리 한도 15,408개를 2,407개 초과한다. 물리 배치 여유를 확인한 FIT/STA 결과는 아니다.

source·transport·SPI·plan·host·queue·validator의 중복 없는 합계는 6,683comb이고 나머지는 11,132comb다. 나머지를 유지하면 이 확장 경계의 예산은 4,276comb다. source/validator를 제외한 거래·출력 경계는 4,280comb이며, 같은 조건의 예산 1,873comb까지 줄여야 한다. 배치 여유는 이보다 추가로 필요하다.


source own은 1,399→1,347comb, plan endpoint는 300→166comb, output queue는
174→129comb로 줄었다. 그러나 공통 SPI는 512→658comb, source transport own은
309→403comb로 늘었다. generation을 descriptor와 함께 넘기는 두 mailbox는
FF가 총 64개 증가했다. 다른 경로의 합성 변화도 포함한 whole 합계로 판정한다.

host output 실행기는 여전히 약 2,488comb이며 독립 validator는 약 1,056comb다.
요청 인자를 공유했다는 이유로 이 실행기까지 대체했다고 계산하지 않는다.
새 source/transport/SPI/plan/output/queue/validator 경계의 own count 합계와
보드 나머지를 따로 산출하고, 부모의 inclusive count를 자식과 중복 합산하지 않는다.
MAP에는 기존 4096×8 SNES program ROM shell이 포함되어 있다. OAM 커널 1,296B가
그 용량 안에 들어간다는 것과 전체 표시 프로그램에 실제로 링크했다는 것은 다르다.
새 커널의 전체 program ROM 통합은 남아 있으며, 현재 실패한 회로 게이트를 통과한
보드 이미지나 실행 가능한 배포물로 제시하지 않는다.

이번 결과는 거래·codec 변경만으로 필요한 2,407comb를 회수할 수 있다는 근거가 아니다.
추가 opcode, FF 수, SPI 지연 또는 FIT seed를 조금씩 조정하는 반복은 다음 목표로
삼지 않는다. 전체 회로 게이트가 실패하므로 생산 경로 채택·FIT/STA는 진행하지 않는다.

## 검증과 보존

선택 증거: test05, window02, arm04, armguards01, spiguards02, rawguards02, guards02, board01, analysis01. 71프레임의 실제 block payload와 record 경계는 ARM 검증 입력과 일치했다. 원본 348,610B(raw 36,352B)를 복원했다. 출력 E1 1,231개, map receipt 2,069범위, 실제 일반 CPU trace 544명령, 최대 4-credit와 metadata/receipt/CRC fixture를 유지했다.

공통 SPI 47개 검사, ARM 오류 21개, 실제 RTL raw 2→0→2→1→2와 generation wrap·오류 query·STOP·용량 초과 거절을 확인했다. 출력/phase RAM 경계의 이번 STOP·최종 ACK 선택 검사는 [3, 23, 24, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55]다. 기존 전체52개 검사와 새 선택 검사를 합쳐 신규52개라고 부르지 않는다.


초기 실패도 보존한다.

- test01: 새 ternary 인접 숫자 표기의 SV 구문 오류.
- test02: 공통 plan 인자 분리 때 길이 바이트가 payload에 들어간 오류. count≥4로 수정했다.
- test03: 연결 시뮬레이터는 PASS였으나 원본 덤프에 `x`가 있어 증거로 선택하지 않았다.
  기존 259B TB 배열이 새 최대 263B 교환보다 작았고, `!=` 비교가 unknown을 놓쳤다.
  배열을 1024B로 늘리고 `$isunknown`/case inequality와 ARM 원본 대조를 추가했다.
- test04: source control의 대표 명령 수를 쓰던 중간 일정이다. token별 명령 수 차이를
  발견해 의도적으로 중단했다. 이후 실제 거래별 비용 표를 사용한다.
- arm01: 제한 실행 환경의 toolchain DLL 로딩 실패. arm02: signed 비교 compiler 경고.
  arm03은 codec PASS, arm04는 prefix·응답 함수까지 포함한 선택 이미지다.
- spiguards01: TB producer가 handshake를 놓쳤고 248B를 단일 record로 보내려 했다.
  허용 record 두 개를 합쳐 최대 block을 만들도록 수정했다.
- rawguards01: TB가 이전 lease 종료 전에 generation을 바꾸어 fault2를 냈다.
  종료를 기다린 뒤 바꾸는 후속 시험을 선택했다.
- guards01: 공통 코드 생성에 필요한 plan endpoint 파일이 기존 검사 fixture에 없어
  컴파일 전 준비 단계에서 중단됐다. 같은 278 입력 파일을 복사하는 후속 검사를 선택했다.

production227, GBC164, saveSRAM은 변경하지 않는다. 최종 판단과 다음 경계는 계획 JSON에
기록하며, 시간만 개선되었다고 회로 부족이나 전체 60fps 목표를 해결한 것으로 표시하지 않는다.
