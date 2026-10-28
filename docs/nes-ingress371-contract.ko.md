# NES371 입력 저장 credit·두 RX buffer·hint→plan 소유권

PR132의370 커밋 `ce7fcf28bf8ffaa7cc4b6363083ccfbb4c923070`을 기준으로 같은 브랜치에서 진행했다. private 원본은 `probes/nes-source371`, 검증 결과는 `analysis/ingress371-verification.json`이다. production227/GBC164/saveSRAM 및 기존 VBlank firmware는 변경하지 않았다.

## 판정과 실제 일정

915 캡처는 **거절**됐다.914의 local 저장은2.614195→2.598514ms, 다음 캡처 인계 여유는-258.292us다. 914 처리 시간은21.545718→**21.493355ms**(-52.363us)다. 이번 실행의 최악 warm914는21.493355ms로60Hz 예산 대비4.826688ms 부족하다. **시간·회로 동시 개선 및 지속60fps·실기는 미승인**이다.

최종 `joint11`은905~914를 배출했다. 초기화2개/warm8개를 구분하며 다음 캡처8회 중7회 승인, 거절frame은[915]다. 관찰 종료 뒤의 거절도 coverage 오류로 남겼으며 정상 통과로 세지 않는다. `joint10` strict와 진단의 모든 event가 첫 거절 시점까지 정확히 같다.

|frame|370 ms|371 ms|변화 ms|동일 source 시작·ROM 위상|
|---|---:|---:|---:|---|
|907|12.040741|12.128468|+0.087727|예|
|908|12.417419|12.530236|+0.112817|예|
|909|16.215692|16.404508|+0.188816|예|
|910|12.030379|12.509600|+0.479221|아니오|
|911|12.479010|12.586327|+0.107317|예|
|912|15.424883|15.548427|+0.123544|예|
|913|12.130105|12.184604|+0.054499|예|
|914|21.545718|21.493355|-0.052363|예|

914의 첫 plan 전송 adapter 반환 계측은9.126413ms,zero는9.125163ms,첫BG는16.857025ms다. 전송 로그의 `RTL_ns`는 마지막 SCK edge가 아니라 adapter 반환 시각이므로 이미 승인된 tile의 zero가 반환보다 앞설 수 있다. 실행 후 확인한 BG tag6개는 모두 초기hint에 포함됐지만 첫BG의 ROM 대기는 남았다. 이 미래 plan 정보를 hint 입력으로 사용하지 않았다. source SPI는D5를 포함해777→801B,전체SPI는2095→2119B다. 추가 credit command의 wire 비용을 시간 이득에서 숨기지 않는다.

ARM text34234→34822B(+588),data4/BSS48740B(+264),관측stack1288B다. ROM 요청/응답57811/57811,입력 기원9353/9353,pending0이다. SysTick body39회와EXTI event215회를 실행·반영했다. 같은 시작·ROM 위상인 단독 비교와 앞선 backlog가 달라진 연속 일정을 표에서 분리한다.

914의 첫 payload 반환은1.164987ms,첫 저장 credit 반환은1.227844ms,hint 전송 반환은1.840010ms다. 두 번째 payload/credit 반환은2.471391/2.530319ms로 이미2.340222ms 캡처 기한을 넘는다. 전체 local 저장은2.598514ms이며 입력 의미 ACK는3.908140ms다. 실제 causal snapshot을 같은 ELF의 hint 함수에 재실행하면13817명령,해당 전송의 pending 명령은43582다. 나머지29765명령을 전부 decoder 비용으로 단정하거나 이 재실행 비용을 추가 시간 이득으로 더하지 않는다. 반복 버퍼 교대보다 앞선 첫 블록의 해석·hint 준비·공유 SPI 순서가 여전히 중요하다.

이번 경로는 연결·안전성 검증 후보로 보존하며 성능·회로 교체안으로 채택하지 않는다. 다른 동일 시작·ROM 위상 warm907/908/909/911/912/913은 각각87.727/112.817/188.816/107.317/123.544/54.499us 회귀했다. 370을 시간 비교 기준으로 유지한다.914의 입력 인계 이득은15.681us뿐이며258.292us 부족이 남는다.914 표시 부족도4.826688ms다.

## 저장 반환과 입력 의미 완료를 분리한 실제 경로

선택한 `nes_transport257.SPLIT_CREDIT371=1`에서는 D4 flags0으로 현재 immutable block을 읽고, CRC16을 확인한 payload를 ARM 소유 RX에 보관한 뒤 D5 flags1으로 저장만 반환한다. 이 반환은 source 입력 ACK·DMA receipt·표시 ACK가 아니다. D5 flags3은 마지막 pop과 입력 ACK를 결합하며 전체 N5 의미검사와 generation·최종 seal이 성공한 뒤에만 보낸다. 기존 token/generation/CRC8/marker/정확한 전체 읽기/다른 bank가 남아 있지 않음 검사를 유지한다. flags1은 ACK mailbox를 발행하지 않는다.

기존259B wire와 추가250B RX를 번갈아 사용한다. 첫 검증된 MAP frontier에서 기존28B EA hint를 전송한 다음 빈 wire로 다음 raw block을 받는다. 이후에는 매번 빈 쪽으로 다음 block을 수신·CRC검사·저장 반환한 뒤 현재 block의 의미검사를 계속한다. 해석 순서는 FIFO이고 현재 해석 중인 buffer를 SPI가 덮어쓰지 않는다. 다음 block을 이미 받았어도 현재 block의 검사에 실패하면 최종 입력 ACK는 없다. raw CRC는 한 번만 계산하고 기존 `feed280`의 누적 CRC·N5 의미·seal 검사를 유지한다. **SPI는 동기식이며 DMA를 구현하거나 CPU/SPI 동시 실행 이득을 계산하지 않았다.** 반환된 FPGA bank의 후속 생산과 ARM 의미검사가 겹치는 순서만 실제로 실행한다.

현재 record-atomic source는 room이 부족하면 record 앞에서 block을 seal한다. 따라서 최종6B N5 seal record가 block을 가로지르지 않는다. raw suffix `FF FF 00 04 + checksum`이 있으면 해당 bank는 의미검사까지 유지한다. literal의 우연한 suffix 일치는 저장 반환을 늦출 뿐 수락 권한을 주지 않는다. 마지막 seal·전체 CRC·generation·header ACK 가능·pending raw 부재를 확인해야 flags3을 보낸다. 임의로 record를 분할하는 별도 source ABI를 지원한다고 주장하지 않는다.

이 ABI는 ARM/FPGA를 함께 선택하는 실험 경로다. 기본 parameter0의 기존 D4 pop/D5 final 동작은 보존한다. 선택1에서 구형 ARM의 D4 flags1은 거부하고, 기본0에서 새 ARM의 D5 flags1도 거부한다. 보드 배포 전 ABI 선택/버전·session 재시작 검증이 필요하며 혼용을 호환이라고 취급하지 않는다.

## hint→plan은 request와 reply 소유권을 따로 전환

기존 hint_active가 zero를 포함한 모든 실제 plan 승인을 막던 gate를 대체했다. 실제 plan은 승인할 수 있고 실제 tile request가 hint보다 우선한다. cache가 요청을 수락하는 순간 hint/실제 tile 소유자를 latch하여 응답을 해당 소비자로 돌린다. 현재 hint_active 값으로 과거 요청의 응답을 분류하지 않는다.

실제 plan이 도착하면 남은 hint를 양보한다. 물리 reader에 아직 수락되지 않은 SCAN/HIT/MISS/REPLY는 철회할 수 있지만, 수락된 WAIT는 응답까지 drain한다. 그 늦은 응답을 zero/BG에 전달하거나 hint 완료 pulse로 만들지 않는다. cache의 byte validity·epoch·소유권·STOP 무효화, 실제 tile의 lease/generation 검사는 유지한다. STOP은 공유 reader를 reset하지 않고 drain하며 해제 뒤 늦은 DONE도 차단한다.

hint는 이미 raw CRC와 record 의미검사를 통과한 현재 MAP column들과 이전에 표시된 bank의 사용 이력에서만 만든다. MAP 순서가 닫혔거나 block의 검증된 prefix가 확정된 시점에 호출하며, 현재 group의 첫 column만 고르던 제한을 제거하되 기존7lane/28B/7entry cache 한도는 유지한다. 이미 보낸 hint에 다음 raw block이나 나중의 실제 plan 정보를 역으로 넣지 않는다. tag가 hint에 포함된 것과 그 tag의16B가 ROM 허용 구간 안에 채워진 것은 구분한다.

## 독립 검사와 기능·합성 경계

실제 M4의905~914 연속10입력을 기존370 decoder와 대조했다. 매 frame receiver28B와 history4910B가 일치한다. raw CRC 첫/두 번째 block 오류, 이미 hint를 보낸 뒤의 누적 의미/CRC 오류와 취소는 최종 ACK를 만들지 않는다. raw 오류가 발생하기 전에 반환한 저장 credit을 입력 성공으로 바꾸지 않는다. 별도11개 M4 검사에는 header CRC/token/flags/payload CRC/generation/마지막 seal/credit 전후 취소와 빈 수신 IRQ 재시도가 포함된다.

실제 SPI·dual-clock transport의15개 검사는 저장 반환만 성공한 뒤 final ACK, 잘못된 flags/token/generation·다른 bank가 남은 조기 final·기존 D4 pop 거절·7개 절단 credit·읽기 없는 credit·STOP을 포함한다. 실제 hint/cache/tile/arbiter의6개 검사는 SCAN/HIT/MISS/WAIT/REPLY에서 양보 후 zero/BG byte 결과와 STOP drain/늦은 DONE 차단을 대조한다. 기존68개 EA guard 전체를 새 RTL에서 재실행했다고 주장하지 않는다.

전체 일정은 실제 M4 C/IRQ body·공유 SPI 신호·source collector·ROM 경쟁·2슬롯 출력과 연결했다. read→unit→private write→publish, 독립 CRC/coverage, 프레임별12 exact display reads/token, 실제 generation retire 검사는 그대로다. 기능 실행과 Lite 보드의 공통 compiled module30개가 바이트 일치하고 새 canonical5파일 SHA256도 manifest와 대조한다. guard와 전체 실행의 ELF는 파일 전체 해시 대신 PT_LOAD의 주소·메모리 크기·바이트 및 함수/객체 symbol 주소·크기의 동등성을 대조했다. 실행 image는 같으며 파일 메타데이터까지 같다고 주장하지 않는다. 축소된 guard만 보드 비용으로 계산하지 않는다.

## 전체 회로·메모리 비용

|전체 Lite MAP|370|371|차이|
|---|---:|---:|---:|
|LE|22710|22747|+37|
|comb|17698|17735|+37|
|FF|9171|9172|+1|
|RAM bits|292448|292448|0|

저장 credit RTL만 선택한 별도 전체 MAP은22711LE/17699comb/9171FF/292448bits로 **+1comb**다. transport self comb는378→354(-24)이지만 전체 절감으로 계산하지 않는다. hint→plan 안전한 양보를 더한 차이는 전체+36comb다. 둘 다 Quartus Lite의 실제 새 MAP이며 Standard/FIT/STA는 실행하지 않았다. 새 조합 논리 부족은2327개,155개 여유 포함 순삭제 필요량은2482개다.

겹치지 않는7개 대상 모듈의 self comb를 다시 읽으면 codec1358+checker1041을 보존하는 시나리오에서 나머지 제어 pool은3423이다. 다른 비용이 고정이라는 조건에서 이 pool을 **941comb 이하**로 교체해야2482순삭제를 충족한다. 이는 필요 예산이며 실제 삭제나 FIT 보장이 아니다. 이번의 전체 회로 절감 인정량은0이다. source/queue/expected/plan의 RAM clock·포트·STOP/CDC를 포함해 기존 제어를 실제로 대체해야 한다.

source512B(NES 쓰기/host 읽기), expected472B+256B슬롯2개를 담는 queue1KiB, phase RAM1KiB, plan1KiB는 유지한다. ARM의 추가 RX 비용을 FPGA RAM 절감으로 계산하지 않는다. 전체 firmware RAM/stack/WCET 적합성은 이 probe의 ELF 수치만으로 확정하지 않는다.

## 보존한 실패와 다음 경계

초기 joint01의 선언 순서 compile 실패, handoff02의 BG plane byte 순서 oracle 오류를 보존했다. RX copy/CRC 재계산이 hint를 늦춘 joint03은910, 직접 RX joint04는913에서 캡처 실패했다. 첫 MAP record만 보고 hint를 발행한 joint05는 필요한 다른 tag를 놓쳐909에서 실패했다. MAP frontier·7lane를 고친 joint06/07도915를 놓쳤다. 첫 두 block만 선행 수신한 joint08/09와 최종 반복 교대 경로를 구분하며 실패의 coverage를 통과로 바꾸지 않는다. raw 로그와 생성 소스는 private에 보존한다.

다음에는 입력 저장 반환 뒤 실제 BLOCKEND/materialized 기한과 hint의 첫 유효 ROM byte 공급을 함께 줄여야 한다. EA에 tag가 존재한다는 이유만으로 prefetch 이득을 인정하지 않는다. 더 큰 host/source/queue/expected/plan 공동 실행기 교체는2482순삭제 필요량과941comb 시나리오 상한 안에서 포트 중재·검사·취소를 포함해 설계한다. 추가 control/응답만 얹는 구조를 회로 개선이라고 승인하지 않는다.

907 capture는 사전5371247 NESclock, 이후357368clock마다 시작하며 readiness에 따라 기한을 옮기지 않는다. CPI1/84MHz·exception/주변장치는 할당 모델이고 ROM은 ready-gated stress다. ordinary65816 trace는 재생하지만 map DMA·최종 표시는 bus model이며 전체65816/VBlank·live NES CPU·firmware WCET·heavy7/71·여러 시작 위상·session 회복·FIT/STA·실기60fps는 미완료다. 기존 VBlank 검사를 유지한 것과 전체 CPU/VBlank를 새 경로로 검증한 것을 구분한다.
