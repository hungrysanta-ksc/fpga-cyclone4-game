# NES313 공통 실행기·새 소비 경로의 전체 비용

NES313 공통 packet/RLE 실행·canonical manifest446B·새65816 descriptor/staging 소비 연결. raw queue/header/ordinary ACK relay와 validator packet_at/executing/E decoder 삭제. storage2credit/consume분리,E2 14B/E0 26B 유지. 제한907 16.905615ms(307대비-0.711310),정상14.747414;wholeLite22959LE/18150comb/9027FF/307808bits,307대비comb+567,부족2742. 907시작 위상 이동으로 warm만 단축/전체 일정과 회로 회귀로 미채택.

## 실제 구현

SNES용 virtual header/body mux, host의 raw queue read와12B ordered ACK identity/ACKWAIT/OSETUP/OTILE/OSELECT relay를 삭제했다. BEGIN12B 의미 검사와 tile4B token 읽기는 공통 reader가 맡는다. tile kind/slot/length/token은 실제 chunk와 대조한다.

ordinary2/4/5/8은 기존 shared staging으로 encoded payload를 한 번 복사한다. 새65816은9B descriptor와4B token, staging payload를 읽는다. actual read coverage/token 이후 독립 receipt가 끝나야 소비 완료가 된다. ordinary consume은6059, tile/map은6050으로 namespace를 구분한다. ordinary 단조32bit token은 STOP에서 초기화하지 않으며 소진 시 거부한다. board reset에는 기존 bus quiescence 전제가 남는다.

validator의 packet_at/executing/complete 및 E_READ/E_CAP/E_NEXT/E_ZERO packet/RLE decoder를 삭제했다. host의 하나의 FSM이 해석과 진행을 맡으며 독립 검사기의 ready를 기다린다. receipt·CRC·fresh/persistent validity·cold map exact coverage·H2 의미·certificate 검사는 유지한다.

같은1024B queue RAM의0..445에 display24+requirements166+map256 기대값을 저장한다. port A는 ingress, port B는 공통 reader/기대값 writer/최종 walker다. 480/752의272B 두 슬롯을 유지한다. 446..479의 directory 예약은 쓰지 않으며 수신 cursor/complete는 register다. SPI/plan FSM도 남는다. 311의 모든 정규화 field/directory 및 전체 SPI/plan 교체를 완료한 것으로 표현하지 않는다.

metadata는 canonical write 뒤 storage credit을 반환한다. collecting과 terminal 검사를 분리해 후속 DMA를 막지 않는다. 마지막 fence에서446B를 독립 검사기에 순차 제공하고 CRC/certificate→12display reads→VBlank/최종 token ACK 순서를 유지한다. storage 반환은 실제 소비가 아니며 active record/staging owner는 receipt까지 유지한다.

## 전체 일정

|ROM|frame|전체 ms|307 대비 ms|312 대비 ms|ARM 명령|SPI B|
|---|---:|---:|---:|---:|---:|---:|
|normal|905|80.076357|+1.583299|-5.934202|2241306|10168|
|normal|906|56.469550|+1.516891|-6.086382|1626145|10766|
|normal|907|14.747414|+0.390723|-0.245133|698910|1123|
|restricted|905|104.637290|+0.982534|-6.438605|2247180|10294|
|restricted|906|116.932597|+0.030863|-16.222760|1634451|10948|
|restricted|907|16.905615|-0.711310|-10.142742|700873|1165|

응답 확대와 2슬롯의 실제 전송 비용(횟수 / wire B):

|ROM|frame|E0|E2|E9|
|---|---:|---:|---:|---:|
|normal|905|3 / 78|42 / 588|10 / 736|
|normal|906|11 / 286|59 / 826|9 / 712|
|normal|907|4 / 104|24 / 336|4 / 92|
|restricted|905|3 / 78|51 / 714|10 / 736|
|restricted|906|11 / 286|72 / 1008|9 / 712|
|restricted|907|4 / 104|27 / 378|4 / 92|

제한907의60fps 부족은0.238949ms다. 시작→첫BG=11.243297ms, 이후=5.662318ms다. 실제 M4 명령/CPI1/84MHz, IRQ body, refill, 공유SPI, 고정 ROM 허용 창/core 경쟁, frame 시작 이동을 포함한 모델이다. 하드웨어 cycle/WCET/실물60fps 증명이 아니다. E2 14B/E0 26B와 짧은E9 fallback의 실제 횟수·bytes는 analysis.runs[mode].rows[].responses에 저장한다. 최대2credit과 최종 EA/진행 응답까지 전체 전송량을 대조했다.

312와 ELF 파일hash는 다르지만 ARM PT_LOAD 실행/데이터/BSS segment는 정확히 같다. 기존312 counter/CRC/credit20·공급20 guard는 동일 코드의 이전 증거로 재사용하며 새 실행으로 세지 않는다.

제한907은307보다 시작이1.013397ms 늦지만 첫BG 시각은 동일하다. BG 이후는+0.302087ms 늘었고905..907 합계도+0.302087ms다. warm907 한 행만으로 처리 성능/지속60fps 개선이라고 판단하지 않는다. 정상 ROM도 전체 비교에서는 회귀한다.

## 새 65816 비용

새 ROM으로544개 ordinary 명령/128041출력B를 실행해 WRAM/PPU byte를 검증했다. body864B+ROM zero/template513B=1377B로 기존 body783B보다81B 크다. 프로그램 크기 제한을 최적화 목표보다 우선하지 않는다.

버스 event는35299→28771개다. 첫 버스 접근부터 consume까지의 paired 합은905 331326→324158,906 330806→323710,907 44822→43294 master clocks다. 907은1528clocks(약0.071145ms) 감소한다. timing.csv의total_clocks는 준비 시간을 제외하므로 부분 값40468→42550만으로 CPU 회귀라고 판단하지 않는다. 실제 일정에는 첫 버스 접근부터 새 ROM trace를 재생한다. token 값만 실행 문맥에 재결합하고 시각은 줄이지 않는다.

actual ordinary CPU와 RTL trace coupling은 검증했다. tile/map 및 VBlank/최종 표시는 기존 service 모델이다. 전체 live65816/fullRUN/whole71/FIT/STA/물리60fps는 미검증이다.

## 전체 Quartus Lite

|항목|307|313|차이|
|---|---:|---:|---:|
|LE|22402|22959|+557|
|comb|17583|18150|+567|
|FF|8965|9027|+62|
|RAM bits|307808|307808|+0|

comb15408 기준 부족은2742개다. validator own1251→1012(-239)보다 host2093→2520(+427),queue118→389(+271),SPI713→781(+68) 증가가 크다. 네 영역의 own 합계는+527이며 나머지 전체 매핑 변화+40까지 합쳐+567다. parent/child 중복 합산이나 FF 감소를 면적 회수로 쓰지 않는다.

board01은 port B read/write 주소 표현 차이로 RAM이 register가 되어29645comb/17205FF/299616bits였다. 같은 port 주소로 고쳐307808bits/M9K를 회복했다. board05는 후속tile 소유권, ordinary 잔여 manifest 차단 조건 수정, 미지원 opcode 거부를 포함한 최종 source다. 기존ROM cache_index141 latch 경고 외 새control latch/undriven은 없고 FIT/STA는 실행하지 않았다.

합성 보고서에서307의 host state는 FSM으로 추출됐지만313의 공통 host state는 추출되지 않았다. validator state는 추출됐다. 새 metadata 판별에 state 범위 비교가 있으며 이는 점검 대상이다. 별도 비교 합성을 하지 않았으므로 FSM 미추출이 전체 증가분 중 몇 개를 설명하는지는 확정하지 않는다. 이번 배치의 회귀를 공통 실행 구조 자체의 불가능 증명으로 확대하지 않는다.

## 검증·실패 보존

SELECT window12/normal04/board05/guards06/cpu03/early04, archive probes/nes-executor313.

- 최종 RTL로 정상/제한905..907 6개 실제 ARM·IRQ·ROM 일정의 metadata/receipt/CRC/display/finalACK 및2credit을 확인했다.
- guard81..92 12건+별도 GNEG0 양성 대조군: 조기 consume, 잘못된 token, canonical map 변조, canonical write 중 STOP, storage 반환 후 STOP, 조기 finalACK, 잘못된 consume namespace, token 소진, 독립 range bound, RLE overflow, 미지원 opcode6/9 거부. fault 뒤 phase/queue RAM freeze를 검사했다.
- early04은 manifest를 BEGIN 직후로 옮긴 양성 producer stress다. 2슬롯에서 후속 tile/DMA/최종coverage 완료를 확인하지만 실제 ARM 시간 증거로 쓰지 않는다.
- 빠른 tile fixture에서 후속 chunk가 준비됐는데 owner를 해제하는 실제 오류를 찾았다. 다음 chunk가 열렸거나 준비됐으면 owner를 유지하도록 수정하고 guard/양성 대조군과6일정을 재실행했다.
- test01 선언 순서,03 reset anchor,05 CPU544/522 입력 불일치,06 fixture 경로,07 옛 ordered-ACK assertion, board01 RAM fallback, guards01 옛 BEGIN ACK 대기,guards02 후속tile 소유권 오류,guards03 raw fixture에 없는 RLE 주입점, early01 컴파일 캐시 누락, early02 ordinary 잔여 manifest 차단 조건 오류를 보존한다. 차단 조건을 실제 seal 이후 거부로 고친 최종 RTL로 모두 재검증했다. 중간 성공은 최종 증거에서 제외한다.

Questa는 승인된 임시 Starter FLOAT, 합성은 Quartus Lite다. production227/GBC164/saveSRAM은 변경하지 않았다.

307 기준/production 유지. validator 절감보다 host·queue·SPI 증가가 크다. SPI/plan 상태·RAM 주소 선택·수신 directory/실행 cursor까지 실제 없앨 더 넓은 교체와 RAM 포트 배치를 전체 예산으로 재검토한다. 고정 ROM 창/실제 ARM·IRQ/새 CPU 준비·consume 비용을 유지하고, 두 예산 동시 통과 전 FIT/seed/부분 FSM 반복 금지.
