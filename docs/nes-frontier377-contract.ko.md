# NES377: 현재 geometry와 첫 BG 부족분의 causal 선행 읽기

## 구현 범위

375 RTL을 그대로 사용하고 ARM의7tag 선행 읽기 선택만 바꿨다. source에서 CRC 확인된 현재 geometry의 group별 첫tag를 유지하고,이전 표시 bank에서 쓰였으나 대상 bank에 없는 첫 BG slot의 물리tag를 하나 추가한다. 남은 lane은 현재 확인된 geometry의 다른 부족tag로 채운다. group/call 한정2tag 중복 필터를 쓰며,미래 plan이나 사후 정답은 입력하지 않는다.

기존7entry FPGA cache·28B EA wire·source ring·2슬롯 queue·독립 검사·STOP·최종 ACK는 그대로다. mapper read를 실행하거나 latch를 다시 동작시키지 않는다. immutable physical CHR-ROM의 speculative read이며 DMA 권한은 실제 plan과 독립 검사가 결정한다. 높은 bank/ExRAM/CHR RAM 지원은 추가하지 않았다.

## 같은 시작·ROM 위상과 실제 전체 비용

최종joint01은 실제compiled M4와SPI/IRQ/ROM 모델에서905~916의12프레임 배출,다음908~917 capture10/10을 통과했다.917은 다음 캡처 승인까지만 확인했다. 오류0/경고0이며905~916의12쌍 모두 source 시작/ROM cycle가375와 같다. source payload와wire plan도12쌍 모두 같다.

|frame|375 처리 ms|377 처리 ms|변화 ms|
|---|---:|---:|---:|
|905|85.301863|85.301863|+0.000000|
|906|114.790146|114.790146|+0.000000|
|907|11.879834|11.880925|+0.001091|
|908|12.105150|12.195058|+0.089908|
|909|15.933423|16.082421|+0.148998|
|910|11.865971|11.868199|+0.002228|
|911|12.207240|12.256967|+0.049727|
|912|15.237840|15.384611|+0.146771|
|913|11.940471|11.952880|+0.012409|
|914|21.501082|14.751073|-6.750009|
|915|21.111496|16.471416|-4.640080|
|916|15.721197|11.326932|-4.394265|

914의첫BG 결과는16.857025→8.658441ms,전체처리는21.501082→14.751073ms(-6.750009)다. tag6136/6554/6555가현재/이전의허용된정보에이미있었는데이전선택정책이빠뜨렸던것을수정했다. 준비비용을제외한무료시간이득이아니다. source_hint의914 호출직전상태replay는8,084→18,526명령이며실제일정도그비용을포함한다.

914 early hint의완료1.607367ms,ROM cache 채움1.683479ms다. fixture의첫허용창종료는대략1.728525ms로약45.046µs만남는다. 이전8.322855ms의첫BG ROM대기가줄었지만,이45µs를mapper공통WCET여유로보면안된다. 실제보드는native_fill_slot/native_core_safe와live CPU/PPU 요구를함께검증해야한다.

ARM text35,862→35,982B(+120),data4/BSS48,476동일,관측stack1,288B동일이다. sharedSPI45,528→45,512B,IRQ body41회/EXTI252회다.915/916에는source empty polling13B씩늘고914에는응답42B가줄어합계16B절감이며,각프레임의실제비용에반영했다. hint당고정28B형식은그대로다.

ROM 요청/응답61,228쌍,pending0,입력기원9,327쌍이다. legacy 입력시간창에서응답을세면한개가다른phase에걸치므로,요청시기원을latch한accounting의9,327/9,327을사용한다.5,011독립unit/528private→publish와2credit/12exact displayread/token/실제retire를검사했다.915/916/917 capture여유1.738684/1.746003/1.772094ms는그대로다.

## 60fps와 mapper 여유 판정

10warm의최대처리시간은16.471416ms(frame915)로,16.666667ms보다195.251µs짧다. 이12프레임표본에서기존4.8ms처리초과는해소됐다. 그러나최대warm 완료간격은20.131168ms로16.666667ms보다3.464501ms길다. 처리시간한도와매VBlank의표시간격은다르다.

capture fixture의간격은16.243805ms이며실기NTSC/SNES VBlank 기준의동일시간표를대신하지않는다. compiled M4는CPI1/84MHz·IRQ/peripheral 할당모델,ROM은core_safe=1/synthetic core demand stress다. 전체65816/VBlank·live mapper/core·WCET·71/heavy7·다중위상·실기60fps는아직아니다.

|선택한예비시간 ms|현재최대처리에서더줄여야할시간 ms|
|---:|---:|
|0.25|0.054749|
|0.50|0.304749|
|1.00|0.804749|
|2.00|1.804749|

이표는mapper측정치가아닌민감도다. 예를들어1ms여유를목표로잡으면현재최대처리에서0.804749ms를더줄여야한다. MMC4/5 실제추가비용과live core에서줄어드는ROM기회는null이며,195µs를승인된mapper예산으로쓰지않는다.

## 회로 비용과 경계

모든공통기능/보드RTL입력을375 최종MAP03과해시대조했다. ARM-only변경이므로같은wholeLite22,390LE/17,663comb/8,985FF/300,640bits를상속하며새MAP을반복하지않았다. 부족2,255comb,155여유포함순삭제2,410은그대로다. 실제mapper/render/IO증분은여기에추가로포함해야한다.

이전375의standalone8/실제negative4는같은RTL이므로재사용하며새검사로세지않는다. 새정책은실제호출직전RAM12개를재현하고,선택한모든tag가현재확인geometry또는이전표시resident부족분에서나왔음을검사했다. resident/receiver/history를변경하지않는다. STOP/disabled/cold/open/prepared/fault/epoch/serial/generation의9가지guard는hint를차단한다. 객체RAM ABI도같다. 초기분석의GNU size DLL sandbox 오류와기록은보존하고,승인된native 실행으로완료된동일분석을대조했다.

## 다음 판단 기준

375 RTL·377 ARM의시간이득과독립검사를유지한다. 다음은실제presentation/VBlank정렬과완료간격을검증하고,첫ROM창의45µs여유를live core/여러위상에서검사하는것이다. 여유0으로60fps기한만넘기는것을완료조건으로잡지않는다.

MMC4/5는 `nes-mapper376-contract.ko.md`의확장gate를적용한다. MMC4는실제latch/admission/liveROM을,MMC5는16bit물리tag·mapper데이터출처·split표현·ExRAM/IRQ/audio/PRGRAM까지같은경계로측정한다. 기존8모듈+helper5957/codec-checker2375보존시제어3582→1172이하예산도mapper증분을넣어다시검증한다.

이공동교체예산을실제전체보드로맞출수없다면같은구조의작은counter/FSM최적화를반복하지않는다. ROM중재·렌더링표현·역할분담과대상하드웨어범위를다시비교하는재설계판단을기록한다. 지금까지의credit/독립검사/취소/재현도구는그비교에도유지한다. 자동구매/merge하지않으며production227/GBC164/saveSRAM은그대로다.

근거: `analysis/frontier377-verification.json`, `analysis/mapper376-verification.json`;raw로그는workspace `../probes/nes-frontier377/`와`../probes/nes-mapper376/`에보존한다.
