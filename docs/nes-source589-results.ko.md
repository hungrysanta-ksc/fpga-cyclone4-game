# 589: 실제 source RAM·CRC·단일 블록 경로 — 기능 통과, 회로 예산 실패

## 판정

**이 source 실행기는 채택하지 않는다.** 588에서 정한 순서대로 실제 RTL의 source RAM·CRC·mailbox·SPI를 연결했다. 고정53입력/282packet과8개 STOP·오류 조건은 통과했지만, 같은 경계의 Quartus Lite MAP이 **1668→4014LE(+2346)**로 늘었다. 예정된 중단 기준에 따라 ARM 직접 실행기 결합을 진행하지 않았다. 새 전체 FIT/STA·설치 ZIP·FPS 개선은 없다. 제품은 MMC577을 유지한다.

선택은 `test02 / map02 / analysis02`다. [수치·해시](../analysis/source589-verification.json), [실제 source RTL](../rtl/nes_source589.sv), [생성·시험·MAP 도구](../tools/check_nes_source589.py), [분석 도구](../tools/analyze_nes_source589.py)를 함께 보존한다.

## 실제 구현한 경계

NES clock의3072×8 동기 RAM에 map/row base와 block scratch를 두었다. query에서 얻은 현재 값으로 canonical CRC를 만들고, map의0/−1/+1 shift·row mask 및 nonmap repeat/raster/literal을 기존586 형식으로 생산한다. map의 세 비교가 끝난 뒤 base를 덮어쓰며, byte write는 reset·enable·frame ownership 조건을 통과해야 한다.

nonmap의 선택은 immutable query를 재조회하고 값의 실제 LOAD 단계에서만 CRC/records를 누적한다. 588 참조의 모든 값을 미리 아는 배열을 하드웨어에 숨겨 넣지 않았다. 이 구현의 재조회 비용도 query counter에 잡힌다.

source block은 packetizer에서 최대8B beat로 바뀐다. 기존 mailbox의 common reset/held/ack 방식은 유지하고 payload 폭을96→69bit(data64/count4/end1)로 바꿨다. host는 기존 `spi165`의 record width/tag 처리만 제거하고 byte beat를256B buffer에 저장한다. packet-end가 저장된 뒤에만 seal하며 D0 snapshot/CRC8·D1 CRC16·read_seen·D2 token/retire·D3 PREPARE를 유지했다. 새 FIFO나4packet 입력 ring은 없다.

META/END/COMMIT 경계가 wire에 실제 존재한다. PREPARE generation이 일치해야 COMMIT을 만들며, COMMIT 마지막 beat가 ordered mailbox에 수락된 뒤 source base를 공개하고 lease를 해제한다. ARM 쪽 COMMIT/D2 공개 규칙은 기존 경계이고 이번에 새 ARM을 구현한 것은 아니다.

기존 압축 source와 record 해석 host를 새 경계로 교체한 원형이다. production top·ROM controller·외부IO 제약에는 적용하지 않았다. actual frame collector 대신 pinned query 값과3–5 source-edge 응답 지연을 쓴다. source/host clock은45.454/11.904ns, 상대 시작 위상은3.5ns **하나**다. 두 ROM 시작 위상 시험이 아니다.

## 기능 검증

- 905–957 연속53입력,282개의 SPI D1 packet이586 참조와 경계·payload·canonical CRC까지 정확히 일치했다. D1의 전송 CRC도 별도로 확인했다.
- 실제 D2 pop 후 D0 token 증가와 D3 PREPARE를 실행했다. 일정한 packet마다100µs read 지연을 넣어 sealed buffer와 mailbox backpressure를 통과했다.
- STOP/common reset을 RAM WRITE·RAM READ 대기·host sealed 상태에서 실행했다. source clock 또는 host clock을 멈춘 경우에도 reset 중 query/전송이 차단되고, 재개 뒤 RAM 추가 write·base valid·sealed/ACK 잔여가 없음을 확인했다.
- 완전한 D1 없이 D2를 보낸 경우와 잘못된 token으로 D2를 보낸 경우는 host fault를 내며 기존 sealed/token 소유권을 보존했다.
- 다른 generation의 D3는 source fault5로 거절하고 COMMIT/base를 공개하지 않았다.

위8조건은 실제 RTL 시험이다. 모든 bit 오류·token wrap·warm STOP 뒤 전체 게임 복구를 망라한 검증은 아니다. 독립 ARM 의미검사·최종 표시 ACK·VBlank·메뉴 복귀는 제품 경계로 보존했고 새 원형에 연결하지 않았다. 임시 Starter FLOAT **1좌석**으로 순차 실행했으며 추가 라이선스를 쓰지 않았다.

## 회로 비용

| 동일 local MAP 경계 | 기존 | 589 | 차이 |
|---|---:|---:|---:|
|LE|1668|4014|+2346|
|조합 논리|1311|3517|+2206|
|FF|794|1370|+576|
|memory bits|2048|26624|+24576|

3072×8 source RAM은 **single-port M9K**,256×8 host buffer는 **simple-dual-port M9K**로 추론됐다. RAM이 FF 배열로 바뀐 실패는 아니다. 실제 physical M9K 배치/packing은 새 FIT를 실행하지 않아 판정하지 않는다.

source의 inclusive 조합 논리는814→2966, FF는240→807이다. host는451→423 조합 논리와304→273FF, record mailbox는39→11 조합 논리와208→154FF로 줄었지만, 새 packetizer108조합/94FF와 source 증가를 상쇄하지 못한다. unchanged17bit PREPARE mailbox도 양쪽에 포함했다. parent-child inclusive 값을 중복 합산하지 않았다.

같은 RTL의 기존 보드 FIT1433LE 표와 local MAP1668LE는 경계·packing이 달라 직접 뺄 수 없다. 여기에는 unchanged PREPARE mailbox도 포함된다. 따라서2346을 실제 보드의 배치 부족량으로 부르지 않는다. 다만148LE 여유 안에 들어갈 선택 근거는 분명히 확보하지 못했다.

원인 분해는 다음과 같다.

- old source의 `state`는 FSM으로 추출됐지만 새 source의 주 `state`는 추출되지 않았다. 코드에 `state<=ret/query_ret/byte_ret`의 동적 복귀 제어가 남는다. packetizer의 state/back과 source control_kind만 추출됐다. 속성 변경으로 면적을 회복할 수 있다고 검증한 결과는 아니다.
- `loaded*width`, 길이·주소 선택 등에 합성된5개 multiplier subtree는 합계224개 조합 논리다. 이미 source2966에 포함된다. 이것만 제거한다고2206개 증가가 해소되는 규모가 아니다.
- generic 폭·kind·mask·반환 경로를 하나의 실행기에 모으면서 넓은 register 선택과 진행 제어가 남았다. old record 표현을 없애도 비용이 자동으로 줄지 않는 실제 사례다.

따라서 FSM 속성·카운터 폭·opcode·seed를 바꾸며 같은 후보를 반복 합성하지 않는다. warning에는 폭 축소·공통 mailbox의 기존 async_reg 인식 경고·합성 정리가 남지만 undriven10034/latch10240은 없었다. 이는 전체 timing sign-off가 아니다.

## 처리 시간의 해석

| source+SPI 시험 구간 | source tick 평균 | query 평균 | mailbox 대기 tick 평균 |
|---|---:|---:|---:|
|cold905|265822|2786|196871|
|warm907–957|140155.24|2789.16|41794.08|
|dense951–955|152740.2|2840|53659.2|

tick은 enable부터 시험 consumer의 최종 D2/D0까지다. query 지연·SPI wire·의도한100µs hold를 포함하지만 ARM driver·IRQ·ROM 경쟁·65816을 포함하지 않는다. 비교용 old RTL의 종단 재실행은 하지 않았다. 회로 gate에서 실패했으므로 새 표시 시간/FPS를 증명하기 위한 추가 실행은 중단했다.

588의 dense wire+driver14.066→4.156ms 가능성과 이 tick을 더해 전체 시간을 만들지 않는다. 588의 input 외 비용59.983/59.989ms도 그대로 남아 있으며 입력 원형만으로60Hz를 달성했다는 결론은 없다.

## 다음 판단과 중단 범위

589 generic source 확장·ARM 결합·전체 FIT·새 ZIP은 중단한다. 의도했던 검사는 없애지 않고 기능 통과 자료를 다음 구조의 oracle로 보존한다.

다음 R2는 **재사용 결정을 ARM에 두고 FPGA가 고정 행 요약·요청 범위·canonical CRC를 공급하는 역할**을 기존577과 비교하는 한 번의 비용 조사다. 이것은 채택된 새 ABI가 아니다. 특히 FPGA의 이전 frame base와 세 shift 비교, generic block 선택·길이·복귀 제어를 실제로 없앨 수 있는지 확인한다.

기존53입력에서 요청/응답 횟수, cold 및 요약 불일치 시 전체 행 전송, ARM 이력/결정 비용, epoch/credit/CDC·STOP·독립 CRC를 모두 포함한다. 요약 hash를 독립 검사 대신 쓰거나 충돌이 없다고 가정하지 않는다. 최종 canonical 검사 실패 시 fail-closed/cold 복구 비용도 별도다. nonmap 압축과 출력/표시 잔여 비용을 빼먹지 않는다. 전송량만 좋아도 전체 Flash·LE·실행 예산이 없으면 새 RTL을 만들지 않는다.

이 단계에서 계속 같은 “범용 source 실행기”를 다듬지는 않는다. MMC577과 GBC/save·README 상태는 유지한다. PR151의 목표/작업내용/성과/후속작업 형식과 사용자 설치·고유 전달본 이름·RESTORE 제외·5–40/40–55초 집계도 유지한다.

## 재현·중간 기록

`check_nes_source589.py prepare`로 hash-pinned576 source와 private581 archive에서 ASCII 경로의 시험 디렉터리를 만든다. 기존 FLOAT wrapper의 `-RunOnly -AfterSmokeScript <절대 job>`에서 `run`을 실행한다. `map`은 installed Quartus Lite를 사용한다. 전체 명령 옵션은 각 도구의 `--help`를 따른다.

test01의 cold/warm2입력이 먼저 통과했다. reset 시 즉시 query 차단과8guard를 포함한 test02의53입력이 최종이다. map01의 reference가 old module 기본 timeout을 사용한 것을 발견해 실제 보드33554432로 맞춘 **reference만** map02에서 재실행했다. 기준1677→1668LE로 바뀌었으며 candidate elaboration은 바뀌지 않아 map01의4014LE를 재사용했다. 초기+2337 수치는 최종+2346으로 대체한다. 이는 성능 변형 반복이 아니다.

`probes/nes-source589/analysis02/evidence.private.zip`에 선택 source·query fixture·SPI raw·logs·MAP report를 보관했다. 원본 test01/map01/analysis01도 유지한다. 공개 Git에는 RTL/도구/숫자·hash만 넣고 ROM 본문·license server 자료·설치 바이너리는 넣지 않는다. 다른 PC에서 private evidence가 필요한 재현이며 clean-clone 전체 보드 재현이 완료됐다고 주장하지 않는다.
