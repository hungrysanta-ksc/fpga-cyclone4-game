# NES303 — plan credit 우선 공급과 공통 queue 포트·완료 제어

PR131에서302c와RTL300을 기준으로 실제 후보를 구현한다. 기존 ARM296·RTL300 기준과 production227/GBC164/saveSRAM은 보존한다. 이번 후보는 cursor 공유가 전체 부족분을 해결한다는 가정 없이, 구현한 제거·추가 비용을 한 번의 whole Quartus Lite MAP으로 판정한다.

## ARM 공급 우선순위

완성되어 append된 BG/완료표식 및 OBJ batch를 동일한 `plan_at267 < plan_bytes267` 대기분으로 본다. plan credit은 CRC·counter를 검증한 progress282의 cache/flags를 사용한다. 계산 중 새 batch가 완성되면 같은 조건을 다음 slice 경계에서 다시 검사한다.

|상태|동작|
|---|---|
|DMA-ready 또는 실제 progress GPIO asserted|계산을 멈추고 기존 DMA/응답 처리를 진행|
|queue credit/drain/phase 대기가 해소됨|대기 계산 없이 caller로 반환|
|완성된 BG·OBJ batch가 있고 plan credit이 writable|계산보다 기존 E9 refill을 우선|
|batch가 있고 plan credit을 아직 모름|계산을 멈추고 기존 checked E2로 credit 확인|
|batch가 있고 검사된 plan bank가 full|IRQ 경계까지 bounded OBJ 계산 가능|
|미송신 batch가 없음|기존 대기 사유가 남으면 bounded OBJ 계산 가능|

`work302`는 SPI를 재귀 호출하지 않는다. E9 serializer/두-bank refill loop가 여전히 유일한 송신자이며 응답의 accepted count가 sent count와 같은지 확인한다. 미완성 batch 강제 flush,sorting 변경,credit 선반환은 없다. BG 완료와 frame END도 구분한다. full bank 상태의 미송신 BG가 있다는 이유만으로 계산을 금지하지 않는다.

기존302의 최대16후보 또는 완전한 fragment 단위,rank/object continuation,STOP 초기화,phase snapshot 및 credit wrap 처리를 유지한다. 마지막 palette/raw/resident 정리31,275명령(관측 약0.372321ms)은 여전히 별도 final 단계다.

## 실제 RTL 교체

|경계|제거|새 소유권/유지|
|---|---|---|
|queue 주소|host8bit parser_address + validator9bit packet_at의 별도 저장 및 내부 주소 mux|host-clock9bit reader303 한 개. header/typed descriptor/payload/manifest가 같은 cursor를 사용|
|internal byte 진행|validator가 별도 cursor를 갱신|validator가 checked capture 단계에서 step을 보내고 host owner가 공통 cursor를 증가|
|descriptor handoff|internal cursor 주소 선택|exec_start 시 원본 payload16으로 이동,기존 descriptor 범위·길이 해석은 유지|
|SNES ordinary DMA|세 소유자 queue mux|NORMAL에서 SNES 주소만 선택. 공통 cursor는 고정,CRC tap은 실제 소비 바이트를 계속 검사|
|receipt 완료|complete298 pulse register|E_DONE303/E_DISPLAY_DONE303 상태에서 완료 표시. 독립 receipt write/certificate 검사가 끝난 후에만 host가 retire|

공통 cursor는9bit라 encoded length256을 주소0과 구별한다. queue의 물리 주소만 하위8bit다. 256 접근은 독립 length 검사에서 거부한다. 일반 DMA·typed batch·manifest를 임의로 동시에 포트에 올리지 않는다. 기존 registered RAM의 HREAD/HCAP·DREAD/DCAP·PREAD/PCAP·E_READ/E_CAP latency 단계는 유지한다. 따라서 이번 변경을 이 read pipeline 전체 또는 모든 descriptor 해석의 제거로 부르지 않는다. host XWAIT relay와 header 저장,encoded/expanded/RLE/checked_byte,receipt walk는 남는다.

STOP/reset/fault가 reader step·execution busy/done을 막고 기존 RAM write freeze 및 lease를 유지한다. 완료를 상태에 포함해도 마지막 RAM write 전에 done을 표시하지 않는다. live/guard assertion은 NORMAL과internal execution의 동시 소유 금지,NORMAL 동안 cursor 고정,owner 없는 step 금지,done과RAM write 동시 발생 금지를 검사한다.

독립 domain/overflow,raw CRC coverage,duplicate receipt,map ordering,manifest encoded/expanded bounds,H2 certificate,12개 정확한 display read·token·최종 ACK 검사는 유지한다. 검사를 줄여 면적을 확보하지 않는다.

## 결과

최종 결과는 analysis/joint303-verification.json의 동일 소스·실행 이미지·whole MAP 연결을 따른다. 정상/제한905..907 및 native71을 분리하고 source replay·실제 M4 명령/IRQ·SPI·ROM 경쟁을 합산한다. 정상907 한 프레임의 개선으로 전체60fps를 선언하지 않는다.

|조건/frame|기준298 ms|302c ms|303 ms|303−298 ms|
|---|---:|---:|---:|---:|
|normal/905|79.689998254|79.720816066|79.721134244|+0.031135990|
|normal/906|56.212189082|56.253234044|56.180144012|-0.032045070|
|normal/907|15.473814312|15.429905748|15.430951190|-0.042863122|
|restricted/905|104.876059654|104.883650472|104.883650472|+0.007590818|
|restricted/906|116.900688084|116.901188078|116.901188078|+0.000499994|
|restricted/907|17.468381286|17.462790444|17.462790444|-0.005590842|

제한907은기준298보다5.591µs 개선,302c와동일하고 초과0.796123777ms가 남는다. 제한905/906도302c와동일하여 plan priority 추가의 제한 ROM 시간 이득은 관측되지 않았다. source9072.666649818ms는기준보다1hostcycle(45.454ns) 짧으며 이 차이도합계에 포함한다. 정상906은기준보다32.045µs,907은42.863µs 개선이나905는31.136µs 회귀한다. 이 값은ARM+RTL 결합 결과이며 개별 변경 효과로 분리하지 않는다.

|전체 Lite MAP|300|303|차이|
|---|---:|---:|---:|
|LE|22578|22644|+66|
|comb|17678|17744|+66|
|FF|9022|9015|−7|
|RAM bits|307808|307808|0|
|comb 부족|2270|2336|+66|

한 번의 fresh whole MAP 결과다. host own2103→2114(+11),validator1310→1314(+4),glue54→51(−3),queue129·plan576·SPI655는동일이다. 고정 출력 경계4827→4839(+12),경계 밖12851→12905(+54),현재 합성 기준 경계 한도는2503이다. 경계 밖 RTL 기능을 바꾸지는 않았으나 전체 mapper의 배치 전 논리 합성 결과도 달라졌다. +66 전체를 cursor 한 개의 순수 비용으로 단정하지 않는다. 소스 변경은mux/validator와연결wrapper총4개이며 실제 header/receipt 영역에서도 절감은 없다.

ARMtext27918B(302c+60,296+460),BSS47120B(302c동일,296+20),live observed stack1288B. 제한907703224명령(302c+132),SPI1236B동일,정상907700078명령(302c+88),SPI1164B동일이다. 새 조건이 계산비용을 없앴다는 주장은 하지 않는다.

**시간·회로를 함께 줄이는 후보로 미채택**한다. 기준ARM296/RTL300의0.802ms·2270comb 부족을 해결하지 못했고,303후보 자체는0.796ms·2336comb 부족이다. 기존 기준 부족분과 미채택후보 부족분을 섞어 개선을 계산하지 않는다.

검증 목록은 최종plan/result의 완료 상태를 따른다. test01/window01의6live와native01의71native를 구분한다. 원본E1/E9 byte/order,metadata8570B·receipt754B·CRC64B,4credit,map receipt64/64/7,finish/최종ACK/commit을검사한다. native71/1039commands/73260B/fixture0및6negative,ARM continuation35STOP/11IRQ재개,H2 9,IRQ8/33exceptions,credit11과새plan공급20조건을검사한다. 실제COMMITTED/BG완료 상태에서 컴파일된work302를호출하는7조건도검사한다: writable/unknown이면계산0,full/drained이면계산진행,DMA-ready/queue-free이면즉시반환,16bitwrap에서도full판단유지. credit입력은메모리로제어한단위검사이며liveSPI결과와구분한다. fresh44RTLguards의checksum/domain/중복/STOP/최종ACK/RAMfreeze는이전300결과를재사용하지않는다.


## 판정과 다음 경계

cursor/완료 저장을 공유해도 descriptor interpretation,header 선택,독립 범위 검사 및RAM write address 선택이 대부분 남는다. 한 주소로 모으면서 mux/enable/fanout가 증가할 수 있으므로 FF 감소를 LUT 절감으로 치환할 수 없다. 이번 MAP의 host·validator 자체 합계도 증가했다. 두 FSM 모두 Quartus에서 추출되므로 FSM 인식 실패를 원인으로 돌리지 않는다.

이 후보의 작은 상태 재배치나 합성 seed 반복은 하지 않는다. 다음 구조 검토는 원본 descriptor의 admission 결과를 한 번 저장하고 DMA 실행과 독립 receipt가 같은 범위 record를 소비하는 경계까지 포함해야 한다. 기존 header/select 계산을 실제 제거하지 않고 checked record를 추가하는 접근은 제외한다. 독립 검사기는 생산자의 승인 bit를 신뢰하지 않고 원본 길이/domain/실소비 CRC/coverage를 계속 확인해야 한다.

시간은 plan 공급 우선 조건이 계산 기회를 줄이는 tradeoff와 마지막0.372ms 정리를 포함해 평가한다. 현재 포트 교체가 제한 ROM 시간을 줄였다는 인과 분해는 하지 않으며,ARM/RTL을 분리 실행하지 않은 합산 결과로 표시한다. 전체 목표 규모의 제거 예산을 확보하기 전에는 FIT/STA나 전체71/heavy7로 성공을 추정하지 않는다.

full ARM RUN,실물 MCU WCET,전체live65816,whole FIT/STA,지속60fps는 미검증이다. ordinary65816 trace와map/tile/display bus 모델,CPI1/84MHz와IRQ entry/exit24cycle 할당을 사용한다. 원본 raw log와 실패도 보존한다.

단독 RTL guard harness의 SPI progress_mode284/progress_irq284 미연결3경고는300과같은별도검사경계다. 이44개를actualARM IRQ 검증으로세지않는다. 실제IRQ·refill연결은test01/window01과ARM IRQ guards에서검사한다. wholeMAP은undriven경고0을확인하며기존보드경고전체를새오류0으로축약하지않는다.

analysis01은IRQ wrapper293의hash를내부실행기284가보고한hash와직접비교하여실패했다. 분석에서wrapper293과실행기284를각각pin하고보고된hash를실제실행기와비교하도록수정했다. 원래실패로그를보존하며시뮬레이션결과는바꾸지않는다. analysis02는board wrapper가별도파일이라는잘못된5파일예상을거부했다. 실제whole입력diff는nes_joint257/nes_joint266/nes_mux260/nes_validator278의4파일이며이를명시적으로검사한다. 최종분석은analysis03다.
