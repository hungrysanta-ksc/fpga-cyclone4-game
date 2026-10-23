# NES314 FSM 원인·SPI/plan/RAM 공동 제어 비용

NES314 FSM 원인 확정: state 범위 비교→명시적 equality만 변경해 host FSM 추출/wholecomb18150→18021(-129). SPI/plan shared seal·queue 기준주소·plan 절대cursor 공동 교체 최종22758LE/17964comb/9043FF/307808bits;313대비comb-186,부족2556. 제한907 16.905615ms/313대비+0.000000,정상14.747414. 시간·면적 동시 목표 미달/production 미채택.

## 원인 확인과 실제 교체

313의 `metadata313=state>=MREAD313&&state<=MSEALWAIT313`는 상태 값을 수치로 사용한다. fsm01에서는 이 조건만12개 상태 equality OR로 바꿨다. 합성 입력의 다른 SV 파일은313 board05와 동일함을 hash로 확인했다. host state가 다시 FSM으로 추출됐고 전체 comb는18150→18021(-129), LE22959→22830, FF9027→9058이다. 이 원인 확인용1회와 공동 변경 합성을 구분하며 FSM만의 수치를 전체 공동 교체 결과로 쓰지 않는다.

공동 변경은 다음 제어를 실제 대체했다.

- SPI 요청 length/value/number의 수명을 SS 해제까지에서 다음 명령 시작까지로 바꿨다. plan endpoint의 length10/number5/CRC16 재저장을 삭제하고 다음 cycle의 seal을 동일 요청 레코드로 전달한다. CRC16 출력은 기존 shared-CRC 경로에서 이미 합성 제거되는 부분이므로31FF 회수라고 계산하지 않는다. 실제 FF는 FSM-only 대비15개 줄었다.
- E9 payload 범위와 header 오류 판별은 SPI에서 한 번 만들어 endpoint와 CRC 갱신에서 사용한다. plan lifetime·end generation·accepted 비교·독립 batch count/shape/lease 검사와 CDC는 유지한다.
- queue의 `slot base +24+address-prefix`와 ingress 다중 덧셈/뺄셈을 슬롯·opcode별 상수 기준 주소 선택+단일 주소 덧셈으로 교체했다. 480/752 두272B 슬롯, 기대값0..445, 저장/소비 counter는 그대로다.
- plan RAM의 시작 offset+필드 위치 합산을 실제 바이트 소비마다 전진하는10bit 절대 cursor로 교체했다. shape는 cursor+1의 batch 끝 위치, READ는 cursor 범위로 독립 검사한다. 필드 의미를 해석하는 at는 유지한다. 가변 alt tag 건너뛰기에서는 cursor를 증가시키지 않는다.

SPI serializer/status snapshot/CRC8, queue clear/load/credit 및 plan CDC/lifetime 전체를 없앤 것은 아니다. 서로 다른 시간·clock domain의 소유권 검사를 삭제하거나 공짜로 계산하지 않는다. STOP은 shared endpoint/RAM 발행을 막고, 실제 receipt·최종 ACK·VBlank 순서는 유지한다.

## 전체 일정과 응답 비용

|ROM|frame|전체 ms|313 대비 ms|307 대비 ms|ARM 명령|SPI B|
|---|---:|---:|---:|---:|---:|---:|
|normal|905|80.076357|+0.000000|+1.583299|2241306|10168|
|normal|906|56.469550|+0.000000|+1.516891|1626145|10766|
|normal|907|14.747414|+0.000000|+0.390723|698910|1123|
|restricted|905|104.637290|+0.000000|+0.982534|2247180|10294|
|restricted|906|116.932597|+0.000000|+0.030863|1634451|10948|
|restricted|907|16.905615|+0.000000|-0.711310|700873|1165|

|ROM|frame|E0 횟수/B|E2 횟수/B|E9 횟수/B|
|---|---:|---:|---:|---:|
|normal|905|3/78|42/588|10/736|
|normal|906|11/286|59/826|9/712|
|normal|907|4/104|24/336|4/92|
|restricted|905|3/78|51/714|10/736|
|restricted|906|11/286|72/1008|9/712|
|restricted|907|4/104|27/378|4/92|

2슬롯, E0 26B/E2 14B, E9 공급, 실제 ARM 명령·IRQ·refill·공유 SPI·고정 ROM 창/core 경쟁·프레임 시작 시각을 모두 포함한다. 313 CPU544개 명령으로 얻은 새 ordinary65816 trace를 변경 없이 재사용한다. ARM PT_LOAD도 동일하다. 새CPU/ARM guard를 다시 실행했다고 세지 않는다.

제한907은16.905615ms이며60fps까지0.238949ms 부족하다. 313 대비905..907 합계 변화는+0.000000ms, 정상 합계는+0.000000ms다. 307 대비 제한907 단축은 여전히 시작 위상 이동 효과이며 전체 합계는+0.302087ms다. 회로 감소를 처리 시간 감소로 표현하지 않는다.

## Quartus Lite 전체 비용

|항목|313|FSM-only|314 최종|313 대비|
|---|---:|---:|---:|---:|
|LE|22959|22830|22758|-201|
|comb|18150|18021|17964|-186|
|FF|9027|9058|9043|+16|
|RAM bits|307808|307808|307808|+0|

FSM-only 이후 queue/SPI/plan 필드 공유는 board01 17974comb, plan cursor까지 연결한 board02는17964comb다. 최종 부족분은2556개(15408 기준)로 여전히 초과한다. 전체 합성 수치이며 parent/child를 중복 합산하지 않는다. 기존 cache_index141 외 새control latch/undriven이 없음을 확인하고 FIT/STA는 실행하지 않았다.

세부 own comb는 host2520→2432(-88), queue389→340(-49), SPI781→814(+33), validator1012 동일이다. SPI 자체까지 감소했다고 표현하지 않는다. 네 영역 합계-104와 나머지 plan/전체 매핑 변화-82를 합쳐 전체-186이다.

## 검증과 범위

SELECT fsm01/board02/window01/normal01/guards01/early01/queue01/spi01/plan01; probes/nes-control314 보존.

- 같은 최종 RTL 정상·제한905..907 6개 일정: metadata/receipt/CRC/display/finalACK/최대2credit 확인.
- 공통 실행기 오류 주입12건+별도 정상 대조: 독립 map/범위 검사, STOP/RAM freeze, 조기 consume/최종ACK, namespace/token, RLE, 미지원 opcode 유지.
- queue14건: payload 최대길이, 두 슬롯 주소, batch/typed 레코드, 저장·소비 분리, CRC/identity/length, credit 초과, counter wrap, STOP.
- 실제 SPI15경계: E1/E9 integrity, payload/CRC domain, STOP,2credit, shared seal 필드의 SS 이후 유지, EA 완료와 요청 레코드 재사용.
- plan48건: 기존313 decoder와36 mixed short/full/alt-tag 정상·4 malformed·8 STOP에서 실제 dual-clock RAM과 cycle별 제어/출력 대조.
- early manifest를 BEGIN 직후로 옮겨 후속DMA와 최종 독립coverage 완료 확인. fixture stress이며 실제 ARM 시간으로 사용하지 않는다.

시간은 actual M4 instruction을 쓰는 CPI1/84MHz 모델이며 실측 hardware WCET가 아니다. tile/map 및 VBlank/최종 표시 service 모델, 실제 ordinary CPU trace 결합 범위를 유지한다. full live65816/whole71/fullRUN/FITSTA/실물60fps는 미검증이다. production227/GBC164/saveSRAM은 변경하지 않았다.

307 비교 기준과 production227,313/314 증거 유지. serializer snapshot/CRC8 주소 mux, queue clear/load/credit와 공통 실행 주소·완료 소유권의 남은 비용을 같은 전체 경계로 재예산한다. 상태 번호/seed/FIT 반복 대신 실제 삭제할 제어와 전체 일정 이득을 먼저 제시한다. 두 예산 통과 전 whole71/fullRUN/FITSTA/실물60fps 승인 금지.
