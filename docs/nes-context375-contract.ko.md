# NES375: host 문맥 RAM과 header·token 공통 진행

## 구현과 선택 경계

373 RTL·372 ARM을 기준으로 구현했다. 374 native plan 후보는 합치지 않는다. 373의 입력/표시 문맥 분리,4packet source ring/512B shadow,압축 plan wire와 독립 NES cursor를 유지한다. 이번 후보는 host의 header 읽기와 cold token 검사 진행을 함께 대체하며,전체 descriptor·manifest·receipt·SPI·plan 실행기를 교체한 것은 아니다. production227/GBC164/saveSRAM과 VBlank firmware는 그대로다.

validator 1KiB RAM의 비어 있는 A port를 실제 host-clock 문맥 port로 연결했다. reserved716..767의52B만 쓰고,init278 전·reset·STOP·fault에서는 쓰기를 막는다. 독립 validator는 기존 B port로 실행한다. 초기 V_CLEARALL은 전체1024B를 지우므로 init 전에 접근하지 않는다. 프레임 clear의677→768 이동과 기존 coverage/CRC/H2 주소 경계를 유지한다.

|문맥 offset|내용|
|---|---|
|0..1|op/section|
|2..3|start|
|4..5|encoded length|
|6..7|span|
|8..11|token|
|12|batch ranges left|
|13..51|이번 경로에서 사용하지 않음|

실제 저장량은13B다. 이전42B 예산 전체를 옮겼다고 계산하지 않는다. token4B는 RAM에서 cold 검사하고,나머지9B의 일부는 실행용 active-record cache에도 남는다. queue credit·namespace/serial burn 이력·SPI snapshot/CRC·read capture/fault 상태도 유지한다.

## 실제 삭제한 제어와 유지한 cache

- 기존 HLOAD/HCHECK case와 queue field-loader 주소 경로를 제거하고,queue B port를 공통 header reader가 직접 순차 읽는다. 기존 loader enable은0으로 묶여 합성에서 제거된다. 오래된 state 상수는 번호 호환용으로만 남는다.
- 새 header/token 실행기는 별도 byte counter 없이 기존 flow `at`를 공유한다. sequence 필드를 검사하지만 문맥 RAM에 다시 저장하지 않는다.
- 기존84bit admitted 문맥 register 복사본을 제거하고,표시 소유권 동안 유지되는 기존 CDC mailbox의 destination 값을 사용한다. 다음 admission은 DONE/소유권 해제 경계를 따른다.
- active record의32bit token과 batch token+1 증가기를 제거했다. logical record는121→89bit다. 이 차이를 별도의 물리 FF 절감으로 전체 MAP에 다시 더하지 않는다.
- MAP은 첫 OPEN 전에 RAM token을 기존 allocator와 비교하고,같은 batch의 후속 range는 배타적 MAP 소유권과 allocator 진행을 사용한다. TILE은 immutable aperture token과 비교한다. TILE이 다음 chunk를 준비할 때 allocation이 바뀌는 것은 허용하며,MAP 검사 중 allocation 변경만 금지한다.

각 header는 token lane-valid4bit를 새로 시작한다. type7 payload 또는 typed header에서4lane이 모두 채워져야 검사할 수 있다. read prime 뒤4byte를 순차 비교한다. 마지막 byte의 lane 계산을 명시적2bit로 제한해 underflow/part-select 폭 문제를 막았다. 잘못된 token은 fault로 이어져 DMA/공개/최종 ACK 권한을 차단한다.

SNES 실제 byte read는 이미 존재하는 immutable aperture `chunk_token` cache를 사용한다. 매 DMA byte마다 문맥 RAM을 다시 읽지 않는다. header/cold 검사 중에는 queue head를 고정하며,DMA와 cold token fetch가 겹치지 않는 것을 실행 guard로 검사한다. B port 독립 검사를 순서대로 우회하거나 validator의 expected와 실제 소비 정보를 합치지 않는다.

## 동일 시작·ROM 위상과 연속 실행

최종 joint01은905~916의12프레임을 배출하고 다음908~917 capture10/10을 승인했다.917은 다음 캡처 승인까지만 확인했다. 오류0/경고0이며,실제 M4 PT_LOAD·source payload·causal hint·wire plan은373과12쌍 모두 일치한다. SPI45,528B,관측stack1,288B,IRQ body41회/EXTI254회를 포함한다. ARM text35,862/data4/BSS48,476B는 같다.

|frame|373 처리 ms|375 처리 ms|같은 source 시작/ROM cycle|
|---|---:|---:|---|
|905|85.301772|85.301863|예|
|906|114.790145|114.790146|아니오|
|907|11.879698|11.879834|예|
|908|12.105105|12.105150|예|
|909|15.933377|15.933423|예|
|910|11.865926|11.865971|예|
|911|12.207195|12.207240|예|
|912|15.237795|15.237840|예|
|913|11.940425|11.940471|예|
|914|21.500992|21.501082|예|
|915|21.111314|21.111496|예|
|916|15.720925|15.721197|예|

10warm 모두 같은 시작/ROM cycle에서45~272ns의 작은 회귀가 있다. cold token 검사의 비용을 제외하지 않았다. cold905는91ns 늦고906은 source 시작도 달라져 동일 위상 순수 비교로 계산하지 않는다. 이번 교체는 시간 단축 성공이 아니다.

914 materialized0.601538ms/첫BG16.857025ms는 그대로다. 처리21.501082ms는60Hz의16.666667ms보다4.834415ms 길고,최대warm 완료 간격25.804417ms도 지속60fps가 아니다.915/916/917 capture 여유1.738684/1.746003/1.772094ms는 유지했다. 저장 credit과 표시 완료를 다시 결합해 캡처 기한을 늦추지 않았다.

ROM은62,222요청/응답,pending0이며 입력기원10,877쌍이다. 5,011개 독립 unit/528개 private→publish와2슬롯 credit,12exact display read/token,실제 retire를 검사했다. 문맥 쓰기2,623회/86개 cold token 검사를 실행했다. 모든 쓰기는offset0..12이며 validator B는 초기화 뒤 reserved52B에 접근하지 않았다.

E1 전송 중SNESread12,104개/E2 중3,398개가 있었다. 최소관측read주기는369ns이며 WCET가 아니다. 이 경쟁을 유지한 채 매byte cold RAM lookup0회를 확인했다. E9 표본에 동시read가 없다는 것을 일반 배타성으로 가정하지 않는다.

## 전체 Quartus Lite 비용과 남은 예산

|항목|373|375|변화|
|---|---:|---:|---:|
|LE|22,601|22,390|-211|
|comb|17,757|17,663|-94|
|FF|9,091|8,985|-106|
|RAM bits|300,640|300,640|+0|

기존 phase RAM은 하나의1024×8 True Dual Port M9K로 추론됐고 총RAM300,640bit를 유지한다. source shadow도 별도512B로 유지한다. 새52B 때문에 FF RAM이나 추가 logical RAM이 생겼다고 계산하지 않는다.

flow self2048→1841comb(-207),새 shared helper101comb/9FF를 포함한다. 기존8개 self6071→5856에 helper101을 더한5957로114개 줄었지만,나머지 전체보드 영역은20개 늘어 **전체 순절감94comb**다. local 감소를 중복 더하지 않는다.

용량15,408comb보다2,255개 부족하고155개 여유까지 확보하려면2,410개를 더 삭제해야 한다. 현재8개+helper5957 중 codec/checker2375를 그대로 두는 시나리오에서는제어3582를**1172 이하**로 줄여야 한다. 전체 묶음 상한은3547이다. 이는 삭제 예산이며 달성 증명이 아니다. 이번94개는373의2349개 부족의 약4%를 해소했다.

MAP02는 Quartus가 helper를 파일명으로 자동 탐색했다. 최종 MAP03은helper를QSF에명시하고 기능/보드 공통compiled31module과4개canonical RTL의SHA를모두 대조했다. 결과 비용은동일하다. 중간analysis의module-count/보고서encoding 실패도 원본로그로남기며 RTL 오류나기능실패로바꾸지 않는다. FIT/STA는 실행하지 않았다.



## 검증 범위와 실패 기록

standalone8case는 정상14/12/type7 경로,token4byte 각각의 변조,새 header 뒤 미완성 token,52B 범위 밖 쓰기,STOP 뒤 완료 차단과 frame-clear 중 문맥 보존을 검사한다.

실제 M4·SPI 경로에는 CRC를 다시 계산한 type7/type14 token 오류,실제 cold 검사 중 STOP,DMA staged 뒤 byte 소비 전 최종 ACK를 주입한다. 예상 fault 뒤 validator1024B·queue1024B·source shadow512B가256host clock 동안 바뀌지 않고,seal/lease/staged/retire/ACK가 공개되지 않는 것을 검사한다. 잘못된 입력 뒤 정상 frame 재시작까지 검사한 결과는 아니다.

negative03의case0..2는 정상적으로 기대 거부와 RAM freeze 검사를 통과했다. 뒤 case3에서 positive 실행용 fail-fast가 먼저 동작한 suite 실패는 보존한다. 주입 플래그 시점만 고친 negative04의case3과 합쳐4개 개별 성공 근거를 만든다. negative03 전체를 성공으로 바꾸지 않는다. 앞선 선언 순서/old121bit harness assertion/positive fail-fast 실패도 원본 보존한다.

최종 연속 실행에는 init 전/범위 밖 context write,validator B의716..767 접근,동일 주소 write 충돌,queue head 해제,표시 중 CDC 문맥 변경,MAP allocation 변경,실제read 중 cold fetch,검사 전 typed DMA 시작 guard를 연결했다. 이는 실제 trace와 기존 accepted-unit/cursor 제한을 전제로 한 RTL 주소 감사이며 모든 불법 상태의 형식 증명은 아니다.

## 다음 교체와 실기 gate

독립 expected·read CRC/coverage·STOP·최종12exact read/token·실제 retire와 VBlank 제약을 유지한다. 다음은 아직 남은 descriptor/manifest/receipt·ingress/credit·source/plan 진행을 RAM port의 실제 소유권과 함께 교체하는 범위다. cache/port/bridge 추가량을 포함한 전체 MAP 순삭제로 예산을 맞춰야 한다. local parent/child 비용을 중복 합산하거나 FF 감소를 comb 용량 확보로 대신하지 않는다.

914의 후반 ROM 창과 첫 BG 공급은 별도 병목이다. 이번 header/token의µs 단축을 ROM 창의ms 이득으로 계산하지 않는다. CRC 확인된 현재 geometry와 실제 ARM·SPI·IRQ·2슬롯 credit로 준비·발행 가능한 시점을 앞당겨야 하며,실행 후에 알게 된 tag를 hint로 넣지 않는다.

compiled M4는 CPI1/84MHz와 IRQ/peripheral 할당 모델이고 ROM은 ready-gated stress다. ordinary65816 trace와 map DMA/display bus model이며,전체65816/VBlank·live NES·firmware WCET·heavy7/71·다중 ROM 위상·session 회복·FIT/STA·실기60fps는 미완료다. Lite MAP을 사용하며,전체 용량 확보 전 FIT/STA를 반복하지 않는다.

근거는 `analysis/context375-verification.json`,실행/합성 SHA는 `src/fpga/nes_context375/manifest.json`에 저장한다. raw 성공/실패 로그는 workspace의 `../probes/nes-context375/`에 보존한다. 자동 merge하지 않는다.
