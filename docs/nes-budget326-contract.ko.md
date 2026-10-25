# NES326 — 목적지·receipt·manifest와 ROM 공급 공동 예산

325의 단일 압축 확장, 실제65816 native DMA, tile/map 두 chunk 선행 생산을 유지한다. 이번 단계는 기존325의9개 실제 ARM/RTL 일정과 전체 Quartus Lite MAP을 재분석한 **구조 검토**다. 새 RTL·ARM·CPU·합성 실행이나 추가 절감 실측은 없다. 재현 도구는 `tools/analyze_nes_budget326.py`, 입력 hash와 결과는 `analysis/budget326-verification.json`이다.319 비교 기준과325의 정상·오류·STOP 증거를 보존한다.

## 시간: 시작 위상과 후반 비용을 분리

|907 일정|고정 시작/ROM 위상|제한 연속|정상 연속|
|---|---:|---:|---:|
|전체 duration ms|26.186595|18.314098|14.370237|
|BG 요청→ready-gated backend 요청 ms|12.782710|4.912941|0|
|마지막 실제 소비→완료 ms|0.570534|0.570531|0.854103|
|그중 소비→seal release ms|0.363810|0.363810|0.647376|
|seal release→완료 ms|0.206724|0.206721|0.206727|
|terminal op3 parser 점유 ms|0.033998|0.033998|0.033998|

parser 점유는 후반 구간에 포함되므로 합산하지 않는다.0.570531ms는 ARM 준비·SPI·응답·checker·표시/종료를 모두 포함한 구간이며 전부 제거 가능한 시간도 아니다. 제한 ROM의1.647431743ms 초과에서 이 구간 전체를 공짜로 만드는 불가능한 낙관 가정을 적용해도1.076900743ms가 남는다.446B canonical replay의 제거만으로 목표를 달성한다는 근거는 없다.

제한907은 source 시작261.559270, BG 요청269.992101, backend 요청274.905042, 첫BG 출력 byte274.905315, 마지막OBJ tile의 첫byte275.364991, 마지막consume279.302883, seal279.666693, 완료279.873414ms다. metadata op15 release271.100706ms는 BG보다 앞서지만 map manifest op11은마지막consume 뒤279.534535ms에 release된다. 마지막OBJ tile 첫byte를 전체tile 완료로 세지 않는다.

관측 명칭을 엄밀히 한다. `romtile305`는 tv/tr/ti==0인 **tile 출력 첫byte**이며 ROM 수락 이벤트가 아니다. `firstmiss305`는cache가ready로gate한backend request 관측이며 별도PSRAM 응답 시각은 아니다.325 문서의 '첫BG' 수치는 그대로 유효하지만 이를 실제 ROM grant 시각이라고 부르면 부정확하다. 다음 구현에서는 첫request, arbiter accepted, PSRAM response, staging first/last, consumer start/end를 각각 기록해야 한다.

319→325 제한 연속은 시작−1.587663ms, 첫BG 출력 동일, 절대 완료−0.393450ms다. duration 증가+1.194213ms는 앞선cold 개선에 따른 위상 변화와 분리한다. 같은 source 시작/ROM cycle의warm 개선0.391768ms와 제한 연속18.314098ms를 모두 유지하며 원래0.453219ms에서 차감한61µs를 새 실측으로 발표하지 않는다. 정상 연속metadata release는189.084824ms로 첫BG183.669864ms보다 늦다. 선행 정책이 모든 ROM 조건에서 선행 완료를 보장하는 것은 아니다.

실제 ARM/SPI/IRQ·2슬롯·staging 비용은325 통합 일정에 이미 들어 있다. 제한907은702,185명령/1,123SPI B/max2credit, 제한3프레임은21,847SPI B/SysTick27/EXTI68, 관측stack1,304B다. CPI1/84MHz 모델이며 물리 MCU 주기 측정은 아니다. ROM wait counter나chunk_ready 점유를 독립적인 절감 시간으로 추가하지 않는다.

## 회로: 전체 MAP에 맞춘 교체 예산

전체22,617LE/17,802comb/9,021FF/307,808RAM bits, 목표15,408comb 대비2,394 부족은 그대로다. 부모 inclusive 값과 자식 own 값을 중복 합산하지 않은 분해는 다음과 같다.

|교체 검토 범위|현재 comb|
|---|---:|
|host 자체 + validator|3,426|
|queue + 공통 SPI 자체|973|
|source encoder + transport subtree|1,769|
|plan 자체 + transport subtree + endpoint|464|
|위 네 영역 합|6,632|
|그 밖 전체 보드|11,170|

외부 비용이 그대로라면 네 영역은4,238 이하, 추가128comb 여유를 요구하면4,110 이하가 필요하다. 이는 설계 허용 상한이며 예상 합성 결과가 아니다. host+validator만 바꾸면3,426→1,032 이하(69.88% 감소)가 필요하다. source+plan 전체2,233개를 가정상 없애도2,394개에 못 미친다. 어느 경로든 일부 주소식이나 FSM 정리만으로 부족 해소를 약속하지 않는다. 실제 외부mapping 변화도 최종 전체 MAP에서 다시 계산한다.

## 후보 비교와 선택할 구현 경계

1. **같은 압축 wire에서 native 목적지·receipt endpoint를 admission 때 한 번 만든다.** 기존 start/end/section의 반복 mux와 이후 granule 변환을 record 소비로 대체할 후보이다. 단, bound/alignment/17bit overflow와raw 마지막9B 검사는 admission에서 유지한다. SNES 목적지와 CRC domain의 일치를 원본oracle로 검증하고 독립 expected manifest는 이record로 생성하지 않는다. active145bit의 각 필드가 마지막으로 사용되는 state를 확인한 뒤 실제 삭제하고 새 native 필드 폭을 비용에 포함한다. ARM wire를 바꾸는323의 역변환·cold 분할을 다시 도입하지 않는다. 이 후보 단독의 시간/회로 절감은 미측정이며 전체 부족 해소 후보로 단독 선택하지 않는다.

2. **expected 저장과 최종 소비 검사를 분리한 공동 manifest 실행기.** op15/10/11 압축expected는queue RAM0..445에 유지하고, terminal446B 재생을 위한 host MREAD/MCAP/MISSUE/MWAIT와checker의중복진행을 하나의 명시적 RAM read/compare 진행으로 대체한다. 마지막소비 전에expected를 준비할 수 있지만 receipt는실제read count/token/ACK 후만 기록한다. payload read/credit를 우선하고 남는host port에만expected 준비를 배치한다. 최종 seal은expected 길이·독립coverage·CRC/H2 certificate·모든consume 완료를 확인한 뒤만 허용한다. op3 도착과 complete flag 없이 임의 선검사/조기ACK를 허용하지 않는다. queue B포트의slot/canonical 경쟁과phase B포트의receipt/hash/display 경쟁을 한 일정에 기록한다. 추가RAM/포트는공짜로 두지 않는다. parser33.998µs는전체 재생+검사 점유이며 절감 보장이 아니다.

3. **ROM 허용창을 유지하면서 ARM 공급·metadata 준비를 겹친다.** BG요청은이미4.913ms 기다리므로 같은창 안에서요청을조금앞당기는것만으로ROM서비스가앞당겨지지 않는다. DMA/plan credit/IRQ를우선하며ROM대기중확정된map manifest 준비·발행을시도하고, op15처럼입력의존성이끝났는지따로기록한다. 기존2슬롯에서마지막DMA를막는head선행발행은금지하고storagecredit와consumed를분리한다. 이전허용창을잡으려면해당시점의source commit·plan확정·cache/lease 유효성부터증명해야한다. 다른프레임의CHR을유효성없이미리쓰거나source시작을늦춰duration만줄이지않는다. 허용창 확대/ROM추가대역폭은현재보드조건변경이므로현후보의절감으로세지않는다.

우선 검증할 조합은2+3이며1은공동record의실제삭제목록이확정되는범위에만포함한다.325 단일staging안은−104comb였지만906+13.494ms로거부했으므로tile ping-pong을다시삭제하지않는다. 네 영역4,238comb 상한을달성할구체적삭제근거가없으면'목표충족구조확정'으로승격하지않고source/plan까지공동제어범위를재설계한다.

## 다음 실제 검증의 통과 조건

- 압축E1/E9 유지,metadata 선행,2슬롯storage≠consume,단일확장과tile 두chunk를동시에보존한다. 새ARM명령/응답/IRQ/stack·cold분할이생기면전부비용화한다.
- ROM동일시작/cycle A/B와제한·정상연속905/906/907을모두실행한다. request/accepted/response 및staging 충돌을분리하고VBlank/최종12display reads/tokenACK까지포함한다. 시간목표는동일위상악화없이제한일정≤16.666667ms이며,위상별미검증을명시한다.
- 독립manifest mismatch,실제소비byte CRC 변조,부분확장/packet/plan/ROMpending STOP,조기consume/finalACK,bank/token 재사용을유지한다. STOP후phase/queue/staging RAMfreeze와ROMdrain도확인한다.
- 동일소스전체Quartus Lite MAP에서17,802보다감소하는지먼저비교하고,15,408이하및RAM포트/용량성립후에만wholeFIT/STA단계로진행한다. 현재는FIT/STA/live full65816/71 ARM/fullRUN/실물60fps 증명이없다.

이번 결론은 **후반manifest만으로시간목표가닫히지않고,목적지·receipt부분정리만으로회로목표를닫는근거도없다**는것이다. ROM공급과공동실행기 교체를함께검증할예산과실패조건을확정했으며,실제개선량은아직325의−22comb와동일위상warm−0.392ms다.
