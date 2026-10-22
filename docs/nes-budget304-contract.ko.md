# NES304 — header·descriptor·RAM 주소 선택의 교체 경계와 공동 예산

## 결론과 기준

303을 제품 후보로 채택하지 않는다. 다음 구현은 ARM296와 RTL300을 기준으로 하며, 303의 공급 우선 조건은 독립 검증한 기능으로 보존한다. 303의 cursor/완료 상태 변경을 자동으로 이어받지 않는다.

현재 증거만으로 시간과 회로 부족을 동시에 해소할 수 있다고 판정할 수 없다. 아래는 **제거해야 할 기존 회로, 설계 상한, 다음 검증의 통과 조건**이다. 새 RTL·ARM 실행 또는 합성 결과가 아니다. 기대 절감값은 미확정으로 둔다.

|기준|whole comb|부족|시간 근거|
|---|---:|---:|---|
|RTL300|17,678|2,270|ARM296+RTL300 분리 검증은 제한 905~907에서298과 동일|
|미채택303|17,744|2,336|제한907 17.462790444ms,302c와 동일|

기준298의 제한907은17.468381286ms로60fps 예산을0.801714619ms 초과한다. cold905/906도 목표를 넘으므로907 개선만으로 전체 성공을 선언하지 않는다.

## 실제 교체 범위

|기존 부분|다음 후보에서 없앨 것|대체와 반드시 남길 것|
|---|---|---|
|host header[0..20],CHECK/OSETUP/DCHECK|완성된 header array의 opcode별 반복 선택과 plen/startpos/outlen 재해석,typed token/first/count/length의 중복 저장|원본 queue byte를 한 번 읽어 하나의 active record를 완성. identity2..9는 이미 미저장이라 새 절감으로 세지 않음|
|bad_data278/receipt_first282/receipt_limit287|admission 뒤에도 계속 존재하는 section별 global receipt 좌표 변환 네트워크|admission에서 byte first/end와 receipt domain/first/end를 한 번 결정. overflow·alignment·raw-tail/scroll 경계 검사 유지|
|tap_address/tap_end/pattern_index|동일 start+length/end의 별도 조합식과 header opcode mux|active record의 byte end·codec·start를 사용. 실제 SNES read strobe·read count·CRC·pattern expansion은 유지|
|validator v_addr/context_addr mux|큰 global cursor에 base를 더하거나166을 빼는 주소 선택,상태별 다단 mux|region/page+local byte offset,독립 bounds 확인 후 concat. 현재 물리 RAM 배치는 유지|
|packet retirement/receipt ownership|host와 executor가 별도로 보관하는 명령 완료 해석 및 XWAIT 분기|단일 immutable head owner가 receipt commit 결과를 받아 retire. 단순히 done pulse를 FSM으로 옮긴303과 구분|
|queue·SPI·plan ingress|source/output/plan의 중복 byte admission·길이/진행 저장과 opcode 분류|공통 ingress에서 stream을 분류하되 목적지별 credit/CDC/STOP·응답 문맥 유지. 공통화가 실제 기존 제어를 제거해야 함|

위 표 전체를 교체 계약으로 삼는다. 일부 주소식만 바꾸고 전체 경계의 절감을 주장하지 않는다. `descriptor_end287`의 공유는300에서 이미 했으므로 다시 절감으로 계산하지 않는다. manifest encoded cursor,expanded cursor,RLE remaining,checked_byte는 서로 다른 의미여서 합쳐 버리지 않는다.

### active record와 저장 예산

후보 record의 필수 payload는125bit다: op4,section3,codec2,encoded length9,byte first16/end17,token32,remaining6,packet cursor9,receipt first12/end12,domain3. control/valid를 포함한 설계 상한을160bit로 둔다. 이 ABI는 아직 RTL이 아니며, 명령별 필요한 필드와 STOP 원자성을 구현 전에 확정해야 한다.

기존 논리 저장의 상한은 header13×8 + length/first/count36 + token32 + cursor9 + remaining8 =189bit다. 이는 source 선언 기준 상한이며 Quartus FF 수가 아니다. 160bit record를 추가하고 기존189bit를 남기는 구현은 거부한다. identity namespace,CRC pattern,read coverage,독립 validator 상태는 이 제거량에 포함하지 않는다. 일반 명령의 SNES header는 원본 queue에 계속 남는다.

phase RAM716..747의32B는 수치상 비어 있고 기존 metadata와 겹치지 않는다. 그러나 이곳에 hot record를 두면 host port B에서 CRC tap·receipt·manifest와 read/write를 다투며, DMA 동안 다시 latch하면 레지스터도 남는다. 따라서 **현재 후보는 active register 대체**로 제한한다. descriptor RAM화를 공짜 RAM/포트 절감으로 채택하지 않는다.

### RAM 주소와 포트 소유권

|단계|queue read port|phase RAM port B|종료 조건|
|---|---|---|---|
|admission|head owner|context/validator,record 저장에는 쓰지 않음|raw bounds/identity 검사 후 active record 발행|
|ordinary DMA|SNES|실소비 CRC/scroll 상태|exact read coverage+ordered ACK;record 불변|
|typed DMA|staging으로 읽은 뒤head 유지|독립 receipt walk|실제 DMA token 소비 이후 receipt commit|
|manifest|내부 byte reader|독립 fresh/persistent coverage 검사|encoded와expanded 길이 모두 충족|
|display|head 없음,display lease|H2 view12byte|12 exact reads/token 검증 후 최종 ACK|
|STOP|read 결과 폐기|write enable 즉시 차단|busy/done/lease와 namespace 재사용 조건 유지|

출력 phase에서는 port A를 공짜 두 번째 host port로 쓰지 않는다. 입력/source와 다른 clock·lease를 갖기 때문이다. read latency를 생략하거나 SPI 수신 완료를 DMA 완료로 바꾸지 않는다.

주소 oracle은 receipt1328bit·map2048bit·두 bank의 manifest422byte·CRC64byte·display12byte를 포함해 **6,952개 주소 동등성**과8개 범위 조건을 검사했다. fresh는page2,valid는bank page,map은page3,hash는page1의192/224 offset이다. manifest는166-byte phase와256-byte phase를 분리해 local offset을 쓰는 후보를 비교했다. 최대256 offset을8bit로 먼저 잘라 alias시키지 않는다. page/offset 변환 전에 independent domain/end 검사를 끝내야 한다. 이것은 모델 검증이며 RTL·MAP 절감 증거는 아니다.

## 회로 예산

RTL300의 겹치지 않는 own-cost: host2103,validator1310,queue129,SPI655,plan576,glue54 =4827comb. 밖12851comb. 기기15408comb에 맞으려면 경계는2557 이하여야 한다.

- host 전체를0으로 만들어도167comb 부족한다.
- host+validator3413만 교체하고 나머지를 유지하면 두 블록 합계가1143 이하여야 한다. 약66.5% 감소가 필요하다.
- 따라서 queue/SPI/plan 제어까지 실제 제거 범위에 포함한다. 밖의회로가 그대로일 것이라는 가정도 최종whole MAP에서 다시 확인한다.

|다음 설계 상한|comb|
|---|---:|
|header admission·active execution·DMA ownership|700|
|독립 validator·CRC·manifest·display 검사|900|
|queue+SPI ingress/응답|450|
|plan transport/refill 연결|325|
|glue|54|
|정책상 여유|128|
|합계|2557|

이 배분은 **요구 예산이지 합성 예상치가 아니다**. 기능 회로 합계2429를 요구하므로 기준 대비2398comb 제거를 입증해야 한다. 특정 식이나FF 수에 임의 LUT 단가를 붙이지 않는다. 하위 블록 inclusive 수치를 중복 합산하지 않는다. 한 블록이 상한을 넘으면 총합 안에서 재배분할 수 있지만 독립 검사 삭제로 맞추지 않는다. 예상 면적은null이다.

## 시간·ARM·IRQ·ROM 비용

303의 실제 실행 로그를 다시 대조했다. 제한907은 ARM703224명령(CPI1 환산8.371714ms),SPI1236B,E2 26회,timer fallback1회,ROM slot 대기56831cycle(점유2.583196ms),core 우선 차단13회다. 이 항목들은 서로 겹치므로 합산하지 않는다. 실제 ARM·IRQ 실행과 ROM arbiter를 쓴 기존 측정이며 새 타이밍은 아니다.

첫 BG plan→첫 tile 출력은2.552742ms이고 첫 OBJ는0.000545ms다. 이는 첫 출력까지의 관측이지 모든tile의 변환 비용이나 순수 ROM stall이 아니다. ROM 허용 창은기존357368cycle 주기의330088..354639 구간 및12cycle 조건을 유지한다. core 우선권이나허용창을임의로늘려목표를맞추지않는다.

907의기록된 OSETUP→retire 서비스 합계는0.026830ms,typed receipt는0.000249ms,마지막ARM 정리는0.372321ms다. 모두무료로없애고고정일정에서직렬로절감된다고가정해도합계0.399400ms이며303의초과중0.396723ms가남는다. OSETUP로그는앞선header/DMA를포함하지않고순수decode시간도아니다. 따라서이는전체header최적화의불가능성증명도아니며,ROM창의비선형효과까지포함한상한도아니다. 작은제어정리만으로0.802ms회복을보장할근거가없다는진단이다.

다음후보는BG의실제필요byte가ROM창에들어가는지함께확인해야한다. 기존BG선행공급을새최적화로재명명하지않는다. source COMMITTED·generation·lease를유지한상태에서 필요한cache miss/공급량과공급시점을줄일구체변경이필요하다. 현재로그만으로몇cycle앞당기면이전창을쓸수있는지확정할수없다.

필수 신규 계측은각 E9 접수 시 ROM cycle/qualified/cache miss/required byte,첫·마지막 BG/OBJ tile와DMA deadline,IRQ/WFI진입·복귀다. 기존qualified 정의와core경쟁을보존하고정상/제한905..907의최종ACK까지동일일정으로비교한다. 생산자명령/CPI,새record발행·검사,refill·polling을모두과금한다. 기준907대비최소0.801715ms 순개선이필수이며,정책상0.25ms 여유를두려면1.051715ms가필요하다. 이것도예상이아닌통과기준이다.

## 구현 진입 및 통과 조건

1. 300 기준에서 header array·반복 field decode·중복range 저장의 실제 삭제 목록과125bit record의명령별 binding을검사한다. 독립 원본bounds/CRC/coverage가생산자승인bit로대체되지않아야한다.
2. page/offset engine은같은물리배치와STOP write-freeze를유지한다. 원본packet·record·실제DMA·receipt간bank/generation/token 불일치,범위overflow,duplicate·누락,RLE truncation,raw0,bank 재사용,각handoff에서STOP을검사한다.
3. ARM의writable/unknown/full plan priority를유지하며새ingress로연결한다. 실제cycle계측으로BG ROM공급량/시점의개선근거를먼저확보한다. ARM의부분실행결과만더하지않는다.
4. 동일소스의6live/71native·독립44guard와새handoff guards 후 **한 번의whole Quartus Lite MAP**. 기대되는최소순절감2270comb·0.801715ms를둘다만족하지못하면후보미채택. FF나localMAP만으로통과시키지않는다. 정상/제한905~907에서정당화되지않은새시간회귀를숨기지않으며cold와warm을구분한다. 여유목표는위별도정책값이다.
5. whole comb만으로board fit를선언하지않는다. 통과후에만wholeFIT/STA/CDC/IO와전체71/heavy7/fullRUN/full65816·실물60fps를검증한다.

현재는구조계약과예산의재설정이완료됐고,공동목표를달성할새구조의타당성은미확정이다. 예상실행시간/합성비용은null,새ARM/RTL/MAP/FIT/STA 실행없음. production227/GBC164/saveSRAM 및303의실패·PASS 증거를보존한다. 분석근거는analysis/budget304-verification.json 및budget304-costs.csv,재현도구는tools/analyze_nes_budget304.py다.
