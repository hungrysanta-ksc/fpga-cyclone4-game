# NES368 source hint·CRC·collector 재시작과 전체 비용

PR132 같은 브랜치에서367 커밋 `0d3a520353249558b546a0852b02895929ebe0d7`을 기준으로 진행했다. 실행 원본은 private `probes/nes-source368`, 해시·비용표는 `analysis/source368-verification.json`이다. production227/GBC164/saveSRAM/기존 VBlank firmware는 변경하지 않았다.

## 결과

909는 동일 시작 시각·ROM 위상에서 **21.458493→18.218941ms**로 개선했다. 이전에 실패한910 캡처도 승인됐다. 하지만 **911 캡처는 거절**되며 연속60fps 후보로 채택하지 않는다. 이후 흐름의 중단 없는 성공을 가정하지 않는다.

콜렉터 읽기 완료만이 재시작 조건은 아니었다. ARM-only `fixed01`은 마지막 local 저장을910 기한보다18.251us 일찍 끝냈지만 owned=0 상태에서도 initialized=0 때문에 실패했다. required-tile bitmap의8192clock 지우기(22MHz 기준약372.364us)가 남아 있었다.

## 변경 범위와 실제 삭제

- `source_hint367`의 현재 geometry 우선 선택 뒤 부족한 tag를 이전 표시 bank의 최근 slot에서 **총3개까지만** 보충한다.909의0216을 current0213/0218 뒤에 넣는다. 현재 후보가 없을 때의 BG5/OBJ2 fallback은 보존하되, bank에 남아 있는 것뿐인 미사용 key는 `resident.used`로 제외한다.910은 실제plan이 zero tile뿐인데 낡은 tag7개를 읽던28B EA를 생략한다.
- source CRC16을16-entry nibble table에서256-entry byte table로 바꿨다. payload CRC와 N5 누적 CRC 및 H2 digest를 모두 유지한다.1280독립 벡터와 실제905..909의 모든 중간 decoder state/history가 기존 구현과 같다. 앞선909 두 block의 decoder 비용은39191→32863명령으로6328명령(할당CPI1/84MHz에서75.333us) 줄었다. 이 값을 IRQ/SPI 포함 실제 시간 이득으로 미리 합산하지 않았다.
- source core의 query_kind 선택은0..5/7뿐이다. cursor8192개×raw mode2개를 실제RTL 조합회로에서 모두 검사했고, 기능 실행의query mask는b7로query6이 없다. 선택된 source 포트에서만 `REQUIRED_BITMAP=0`으로8192×2bit RAM, scrub counter, bitmap RMW/query 경로를 실제 합성에서 제거했다. default는1이다. 기존query6 기능은 유지하며, 선택된 포트의query6은 hit를 주지 않는다.
- 실제 low/high plane 짝·주소·cross-tile·extra sprites·ROM fault·누락 high 검사와 event/retirement는 남겼다. 새 parameter1 구현을 원본legacy와, parameter0 구현을 같은PPU 입력으로 대조했다. query0..5/7, raw0/1/2 core, 독립 expected/read CRC·coverage·STOP·최종 ACK 경로는 유지한다.
- 검증기는 실제 flow_retired edge와 generation을 기록한다. 다음source가 live retired 상태를 내린 뒤 늦게 기다리던 문제를 고쳤다. 새로운 ACK를 만들지 않으며, ARM 완료와 독립12read/token ACK 검사는 그대로다. 종료 후 결과 파일 확인은 DPI op8로 수행해FOFIR poll 경고를 제거했다.

## 시간 비교와 캡처 판정

frame907의 캡처 시작을 사전에5,371,247clock으로 고정했다. 늦으면 기다려 주지 않고 실패한다. 이후PPU는357,368clock 주기로 독립 공급한다. 대조군과 새 후보의907..909 source 시작 시각 및 ROM cycle가 정확히 일치한다.905/906은 직렬 초기화로 따로 보고한다. 이 fixture는45.454ns/NESclock이며 실제 콘솔/전체VBlank의 측정치가 아니다.

|frame|대조군 ms|후보 ms|변화 ms|
|---|---:|---:|---:|
|907|12.157104|12.037605|-0.119499|
|908|13.117365|13.002730|-0.114635|
|909|21.458493|18.218941|-3.239552|

|frame|source 시작→완료 ms|마지막 local 저장 ms|입력 ACK ms|hint SPI B|
|---|---:|---:|---:|---:|
|905|99.646236|20.471255|22.574525|0|
|906|116.690213|0.579220|2.457129|0|
|907|12.037605|1.667798|2.752444|28|
|908|13.002730|0.576948|2.576901|28|
|909|18.218941|2.322063|3.906567|28|
|910|12.028333|0.567129|1.992226|0|

미사용 hint 제외 전 `joint04`의910은19.463653ms, 제외 후에는12.028333ms다. 앞선 연속 일정과 source 시작 위상에는 미세한 차이가 있으므로 이 차이를 독립 이득으로 합산하지 않는다. 보충·CRC·bitmap 제거의전체 효과와, 연속 일정의 실제 결과를 나누어 기록했다.

`joint03` strict 실행은911에서 즉시 중단했다. 선택한 `joint07 --observe-last --last910`은 거절된911을 승인하지 않고910만 배출한 뒤 `capture coverage367` 오류로 종료한다. **905..910 여섯 완료 프레임 중 두 개는 초기화**이며, 다음908/909/910 시작3회 성공·911 시작1회 실패다. 계획한905..911 strict 정상 완료는 달성하지 못했다.

911의 local 저장 여유는-0.117611ms이다.909 출력이 다음source 시작을 밀어910 읽기를 기한보다117.611us 늦췄다.909 표시 시간은16.666667ms보다1.552274ms 길다. 두 부족량을 같은 것으로 취급하지 않는다.

## Quartus Lite와 ARM 전체 비용

|전체 MAP|367|368|변화|
|---|---:|---:|---:|
|LE|22803|22710|-93|
|comb|17762|17698|-64|
|FF|9218|9171|-47|
|RAM bits|308832|292448|-16384|

실제8192×2bit inferred bitmap RAM이 보고서에서 없어졌고FF로 전환되지 않았다.13개 canonical file과30개 공통 compiled module이 기능/whole QSF에서 일치한다. parent/child inclusive 값은 합산하지 않는다. 새 제어를 무료로 계산하지 않는다. **comb2290개 부족**,155개 여유 포함 **2445개 순삭제**가 남았다. FIT/STA는 실행하지 않았다.

같은 build의367 ARM image 대비 text33618→34178B(+560B), data4B/BSS48476B는 그대로다. 관측stack1288B이다. 코드 확장은 포함했으며 production 전체firmware 용량/WCET 승인은 아니다.

## 검사와 한계

1280CRC 벡터와 모든 중간source state/history 대조, 기존source37개 시나리오/차단 검사와6개frontier/used 검사, plane/event/query6/rearm/STOP10case, query selector16384조합, 새설정의22session guard를 통과했다. 변하지 않은SPI/cache/arbiter의68EA/STOP guard도 해시로 연결한다. 매 완료 프레임의 actual read→unit→private write→publish와2slot credit,12exact display reads/token을 다시 대조했다.

ROM 감사는 요청 당시 input/output 구간을 저장해 응답과 대응시킨다. 전체 요청/응답은49,775/49,775, 입력 구간에서 시작한 요청/응답은6,647/6,647이며 남은 요청은0이다. 기존 구간별 카운터는 요청과 응답이 경계를 건너면 차이가 날 수 있어 그대로 보존하고, 새 origin counter의requests-replies=pending을 별도로 확인한다. 모든 ROM 응답 값 검사는 유지한다.

Cortex-M4 C/IRQ body는 실행했지만 CPI1/84MHz와24cycle exception 및 주변장치 adapter는 할당 모델이다. ROM은 입력/출력 모두의 ready-gated stress이며 liveNES CPU가 아니다. ordinary65816 trace는 재생하지만 map DMA/최종 표시는 bus model이다. 기존 VBlank firmware를 유지했으나 새로운full65816/VBlank 증명은 없다. source token wrap의drained-session 회복도 기존 미완료 범위다. 실물60fps·전체71/heavy7·다중 시작위상·전체firmware·FIT/STA를 승인하지 않는다.

다음 단계에서는368의 개선과911 실패 조건을 유지한다. 관측된 backlog에서909 표시 시간을 최소1.552274ms 더 줄이고 다음source 인계를117.611us 앞당겨야 한다. row별 planner·후반 ordinary 준비와 E2·credit·DMA 대기 구간부터 계측한다. ARM SPI DMA·2buffer 수신과 증분 row 준비를 실제로 실행해 비교하되, 선행hint의 ROM 기한과 CRC·의미 검사를 유지하고 아직 실행하지 않은 중첩 이득은 차감하지 않는다. 더 넓은 교체 전에 source·host·RAM 포트 소유권과 전체2290comb 부족(155개 여유 포함2445개 순삭제)을 함께 맞춘다. opcode·작은FSM·seed·FIT 반복으로 대체하지 않는다. 전체65816/VBlank·heavy7/71·다중 시작위상·firmware WCET·token/session 회복·실기 검증은 계속 미완료다.
