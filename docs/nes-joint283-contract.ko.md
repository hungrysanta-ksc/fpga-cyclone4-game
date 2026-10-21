# NES283 — host 범위 분할 제거와 validator RAM 진행 통합

NES283: host의 receipt 분할과 validator의 잔여 범위 계산을 단일 RAM 진행으로 통합하고 ARM CRC8 검사를 nibble 표로 바꿨다. 정상71·제한ROM3, STOP/ACK17·범위307·ARM25·SPI51·실제 ARM CRC65,536쌍을 통과했다. warm 최대 16.063171ms(954, 282 대비 -0.103590ms), 제한 ROM907 18.721866ms(+0.013636ms). 전체 Lite 17,802comb(-108), 부족 2,394개다. 일반 시간·회로는 개선했지만 제한 warm 회귀까지 줄이는 공동 목표는 미달이다. P2·FITSTA·실물60fps는 미승인 상태다.

## 교체한 제어와 남긴 검사

기존 NES282는 host가 tile을 최대 16 granule, CGRAM/body를 최대 256B씩 나눈 뒤, validator가 같은 범위를 다시 RAM 바이트 단위로 나누었다. NES283에서는 host가 원본 descriptor에서 확인한 전체 granule 범위를 한 번 제출하고, validator가 완료할 때까지 queue head를 유지한다. host의 작은 범위 종료 계산·되돌아오기와 validator의 `v_left`·`v_take`·남은 개수 감소를 제거했다. validator는 독립적으로 검사한 exclusive end와 단일 bit cursor를 보유하고 다음 RAM 바이트로 진행한다. 원본 payload parser와 CRC tap, descriptor 소비를 확인하는 제어는 남아 있다. 전체 host/validator를 하나의 FSM으로 합쳤다는 주장은 아니다.

validator는 13bit 덧셈으로 overflow를 포함한 끝 위치를 검사한다. 일반 범위는 tile 0..1023, sprite 1024..1151, CGRAM 1152..1183, body 1184..1311의 경계를 넘을 수 없다. raw tail 1312..1327은 CRC granule마다 1개씩 승인한다. map 범위는 기존 최대 32개·2048 상한·단조 순서를 유지한다. receipt RAM의 중복 bit를 거부한 뒤 persistent validity를 갱신한다. 개수 상한 변경은 내부 receipt 요청 계약에 한정되며, SPI packet·원본 descriptor·DMA payload 형식은 바뀌지 않는다.

원본 bytes CRC, physical read coverage, ordered ACK, H2/manifest coverage, token·4 credit, STOP·clock freeze, 마지막 12B 표시 문맥 읽기 후 최종 ACK를 유지한다. source NES A / host B 고정 phase RAM 포트, query 선행 읽기, plan의 두 bank·reader·CDC도 유지한다. STOP 후 provisional state는 다음 reset/cold 절차 없이 재사용할 수 없다.

ARM은 진행 snapshot·E0/E2·E8·전송 CRC8의 비트 반복을 16B nibble 표 두 번 조회로 대체한다. 두 번역 단위에 각각 작은 상수표가 합성되는 비용까지 최종 ELF에 포함한다. 응답 길이·CRC·accepted/retired·reserved flags·plan 상태 검사를 생략하거나 polling 간격을 임의로 늘리지 않는다. command-start snapshot이 현재 패킷 승인을 포함하지 않는 계약, 짧은 terminal E9의 E8 fallback과 오류 고정도 그대로다.

ARM 응답 오류의 sticky failure와 RTL STOP은 각각 검증하며, 전체 firmware의 오류→STOP 발행 루프는 아직 별도 미검증이다. MISO 오류 발견 전에 MOSI 수신이 끝났을 수 있으므로 단순 재전송 성공으로 취급하지 않는다.

## 실제 ARM·polling·ROM 비용

| 일반 조건 | NES282 | NES283 | 변화 | 16.667ms까지 여유 |
|---|---:|---:|---:|---:|
|952|14.643870ms|14.313237ms|-0.330632ms|2.353429ms|
|954|16.166761ms|16.063171ms|-0.103590ms|0.603496ms|
|955|14.493553ms|14.285783ms|-0.207770ms|2.380884ms|
|962|15.143636ms|14.943912ms|-0.199725ms|1.722755ms|
|963|14.451417ms|14.370691ms|-0.080726ms|2.295975ms|
|968|13.257295ms|13.115070ms|-0.142226ms|3.551597ms|
|970|15.684994ms|15.561041ms|-0.123953ms|1.105626ms|

warm69 한도 초과 0개. cold905/906은 초기화 비용으로 구분한다.

| 제한 ROM | NES282 | NES283 | 변화 |
|---|---:|---:|---:|
|905|89.140839ms|88.863888ms|-0.276951ms|
|906|113.987359ms|114.095949ms|+0.108590ms|
|907|18.708230ms|18.721866ms|+0.013636ms|

제한 조건 세 프레임 절대 종료 263.773835ms, 변화 -0.154725ms. 구간 변화와 절대 종료를 구분한다.

| 제한 ROM907 항목 | NES282 | NES283 |
|---|---:|---:|
|E2 polling|280|304|
|E8 polling|3|3|
|출력 SPI B|3485|3701|
|출력 ARM/IRQ 명령|248854|179226|
|ROM slot 대기 cycle|225524|229796|
|tile 대기 cycle|225537|229809|

명령 차이 -69,628는 CPI1/84MHz에서 -0.828905ms, SPI +216B 차이는 2.625MHz에서 +0.658286ms다. 두 항목의 합은 -0.170619ms이며 실제 구간 변화 +0.013636ms와 비교한다. ROM/동시 실행 일정의 변화가 포함되므로 독립적으로 비용을 다시 더하지 않는다.

제한907의 E2가 280→304회로 늘어 ARM 절감의 상당 부분을 추가 wire가 소비했다. slot 대기도 +4,272cycle(+0.194179ms) 늘었다. 이 대기는 SPI/ARM과 겹치므로 앞의 합에 그대로 더하지 않는다. 906의 절대 종료는 -0.168362ms 앞당겨졌고, 907의 종료는 -0.154725ms 앞당겨졌다. 따라서 warm 구간은 +13.636µs 길어졌지만 세 프레임 전체는 154.725µs 빨리 끝났다. 제한 ROM906 구간도 +108.590µs 회귀했다. 변경된 시작 위상과 실제 대기 기록을 함께 해석하며, CRC instruction 감소만으로 성능 향상을 보장하지 않는다.

ARM text 4682B(변화 +40), BSS 624B, 관측 stack 272B(변화 +8). 빈 queue의 진행 응답 검사 577→248명령. CRC 한 byte의 모든 입력 조합은 실제 ELF에서 14명령으로 검증했다. instruction 수는 하드웨어 cache/flash wait를 포함한 cycle 수가 아니다.

최악 일반 구간 source 5.424799 + output 10.638372ms. source codec만 CPI2로 둔 고정 일정 민감도 최댓값은 17.155861ms다.

일반954도 E2 85→93, E8 7→8, 출력 SPI 2443→2535B로 증가했지만 ARM/IRQ 195434→157782명령으로 줄어 전체 -0.103590ms를 얻었다. parser 22.425µs와 map receipt 1.746µs를 모든 절감의 원인으로 취급하지 않는다.


수치는 source 구간과 live output ARM/IRQ·SPI·tile ROM·65816 bus trace 실행 구간을 직렬 합산한 진단 일정이다. source ARM은 실제 ELF의 블록별 instruction replay, output ARM은 실제 Cortex-M4 ELF의 실시간 응답 경로다. CPI1/84MHz를 하드웨어 WCET로 보지 않는다. CPU279에서 검증한 65816 bus trace를 재사용했고 새로운 live 65816/full RUN/NVIC/active VBlank/완전한 program ROM/실물 60fps 검증은 아니다. ROM 대기와 polling은 이미 같은 출력 타임라인에 포함되어 있으므로 별도로 다시 더하지 않는다.

## 같은 전체 보드 경계의 Quartus Lite 비용

| 전체 Lite MAP | NES282 | NES283 | 변화 |
|---|---:|---:|---:|
|LE|22,847|22,751|-96|
|comb|17,910|17,802|-108|
|FF|9,092|9,088|-4|
|RAM_bits|307,808|307,808|+0|

| own 조합 논리 | NES282 | NES283 |
|---|---:|---:|
|host|2494|2408|
|validator|1087|1040|
|queue|127|125|
|plan|565|570|
|selected|4273|4143|
|outside|13637|13659|
|budget|1771|1749|

장치 15,408comb 기준 부족분 2,502→2,394개. 변화한 selected 영역만 차감하지 않고 outside 13,659개도 반영했다. 새로운 합성 경고 0개, 제거 경고 1개다. 기존 manifest cursor truncation은 ready가 열린 실제 index 범위와 구분해 유지한다.


Lite MAP만 수행했다. FIT·STA 성공이나 물리 자원 배치를 뜻하지 않는다. own resource를 합산해 parent/child 중복 차감을 피했고, 변경 영역 밖의 합성 변동도 전체 비용에 포함했다. FSM 추출·경고·실제 QSF 입력 hash를 검사했다. 기존 shell의 미연결 program ROM 경고를 완전한 실제 프로그램 연결 증거로 해석하지 않는다.

## 검증과 증거

선택 증거: test02, window01, guards01, armguards01, spiguards01, board01, rangeguards02, crcguards01, analysis01. 전체 71프레임 E1 1,231개·E9 payload가 NES282와 byte exact이며 source 47,900B, map 2,069범위, 544 CPU trace명령, 최대4 credit를 확인했다. metadata 8,570B/receipt754B/CRC64B의 프레임별 독립 검사를 유지했다.

실제 일반 receipt 요청은 395회이며, 그중 2회가 16 granule을 초과하고 최대 82개다. 같은 승인 범위를 기존 16개 정책으로 나누면 403회인 산술이다. 이를 따로 시간 절감으로 더하지 않는다.

범위307·실제 ARM CRC65,536쌍·ARM 진행 오류25·SPI51·통합 STOP/ACK17 검사 PASS. rangeguards01은 단위 시험 fault 출력 미연결 실패를 보존했고 rangeguards02에서 명시 연결·unknown 검사를 추가했다. RTL은 이 수정으로 바뀌지 않았다. test01은 최종 RTL/ARM의 초기3프레임이며 test02는 receipt 요청 관측을 추가한 전체71프레임이다.


범위 단위 시험은 RAM bit별 독립 oracle로 첫/마지막 byte, offset 0..7, 작은 범위와 최대 domain, duplicate·overflow·경계 교차·map 역순, 네 RAM 상태의 STOP을 검사한다. 이 시험만큼은 admitted lifetime을 직접 설정하며, 실제 grant·원본 payload·ACK 연결은 별도의 통합 시험이 담당한다. CRC 단위 시험은 실제 ELF에서 256개 CRC 상태 × 256개 입력 byte를 모두 비트별 독립 oracle와 대조한다.

원시 build/Questa/MAP 로그·ELF·request/response·hash 목록은 `../probes/nes-joint283/`에 보존한다. 라이선스 파일/서버 로그는 포함하지 않는다. production227/GBC164/saveSRAM은 변경하지 않는다.

## 남은 예산과 다음 경계

일반 진단 일정의 한도 부족 0.000000ms, 0.5ms 계획 여유까지 부족 0.000000ms, source만 CPI2로 둔 민감도 부족 0.489195ms, 제한 ROM warm 부족 2.055200ms다. 아직 재지 않은 full RUN·NVIC·active VBlank·하드웨어 flash wait 비용은 이 여유로 입증되지 않는다.

회로는 2,394comb를 더 줄여야 한다. 현재 selected 4,143개를 <= 1,749개로 줄여야 하며 128개 계획 여유를 두면 목표는 1,621개다. 이번 범위 공유의 절감만으로는 부족하다. 다음 검토는 descriptor decode·physical read/ACK coverage·receipt/H2/manifest 종료와 plan/tile 수명 제어의 실제 중복을 함께 대상으로 하고, 유지할 독립 검사와 RAM 소유권을 먼저 고정한다.

이번 후보는 일반 시간·회로에 국한한 개선이며 제한 warm까지 개선한 공동 후보로 채택하지 않는다. 다음 시간 검토는 checked ready/progress 전달·plan refill 수명·실제 ARM IRQ/NVIC service를 함께 연결해 변하지 않은 상태의 반복 polling을 줄이는 경계다. 임의의 polling 지연값 조정으로 결과를 맞추지 않고 conservative credit·fallback·STOP·최종 ACK를 유지한다.


전체 회로와 시간 게이트가 충족되기 전에 FIT seed 반복이나 물리 60fps 후보 채택으로 넘어가지 않는다. 압축 바이트·독립 검사·실제 소비/STOP/최종 ACK는 다음 후보의 비교 기준으로 보존한다.
