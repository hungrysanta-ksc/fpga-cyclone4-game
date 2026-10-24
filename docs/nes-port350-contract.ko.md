# NES350 — 실제 RAM 포트 추적으로 확정한 교체 경계

338 RTL·336 ARM을 유지한다. 이번 변경은 **테스트벤치의 수동 관측기, 일정/포트 분석기와 계획**이다. 제품 RTL/ARM을 교체하지 않으며 관측기의 레지스터·파일 I/O는 합성 비용에 포함하지 않는다. 새 실행기 절감량은 아직 null이다. 선택 기준은 제한 ROM 연속 warm907 20.689660812ms, 60Hz 초과4.022994145ms, 전체17,274comb/1,866comb 부족 그대로다.

## 관측 방법과 증거 범위

`probe_nes_port350.py`는 기존338 생성 경로의 마지막에만 관측기를 넣는다. `ports350.csv`는 host clock의 RAM 요청 주소, 직전 주소, 반환 데이터, header/payload/descriptor capture, expected write, ingress write, accepted/retired/consumed, range_ready, reset/fault 및 validator 상태를 기록한다. RAM은 enable 없이 항상 읽으므로 **물리 read 전부를 유효 작업으로 세지 않는다**. state-change 행 수도 state 체류 clock 수와 다르다.

실제 RAM의 이전 clock 입력값과 현재 host capture 데이터를 테스트벤치에서 직접 비교하고, 양쪽 port의 동일 주소 동시 write를 금지한다. 분석기는 header field의 직전 주소, payload/descriptor 주소와 bank,2slot credit, expected 영역 범위 및 독립 final capture를 검사한다. 실제 실행 결과의 RTL hash, ARM PT_LOAD와 실행 결과, source cycles/bytes, CPU bus trace 및 `joint-events.csv` 전체를338 기준과 대조한다. 단순히 frame 완료 시간만 같다고 판단하지 않는다.

최종 실행/guard 결과와 pins는 `analysis/port350-verification.json`을 따른다. 같은905..907의 세 일정은9관측/3unique frames이며 새71-frame proof가 아니다. 기존 M4 instruction 실행+CPI1/84MHz·IRQ allocation, 유지된65816 ordinary trace+C map/tile consumer 모델의 한계도 그대로다. 실물 ARM WCET/full firmware RUN/full65816/whole pixels/FIT/STA/실물60fps는 주장하지 않는다.

## 실제 포트 소유권

SELECT `window01/fixed01/normal01/guards01/analysis-final01`.9정상 관측의 모든 원래 event와 ARM 결과가 baseline과 일치했다. 주소 순서 모델은429packet 관측(각 일정143)을 통과했다. 기존2200pins 재해시 후2351pins를 기록했다. 모든 Questa 실행은 승인된 Starter FLOAT 경로를 사용했다.

STOP30은 HLOAD(state55)에서 현재주소523/직전522, STOP31은 descriptor capture(state18) 주소789, STOP12는 독립 expected capture 중 MSEALWAIT(state53) 주소356에서 주입했다. 세 경우 모두 fault4·256host clocks RAM freeze·seal/lease/staged/ACK/retire 공개 차단을 통과했다. aperture 및 raw0/최종검사8cases도 PASS다. 이는 **기존338의 취소 계약 확인**이며 새 skip reader의 취소 proof로 자동 승계하지 않는다.

제한 ROM 연속 관측:

| frame | ingress byte | header capture | payload capture | batch descriptor capture | metadata capture | expected write / 독립 capture | 같은 clock의 유효 A/B 접근 |
|---|---:|---:|---:|---:|---:|---:|---:|
|905|8699|710|6996|192|321|446 /446|11|
|906|8867|790|7020|192|321|446 /446|11|
|907|569|155|205|21|68|446 /446|0|

수신 byte는 E1 command/CRC를 제외한 queue RAM 실제 write다. expected446은 display24 + requirements166 + map256이며, final scan의 독립 capture446과 대응한다. warm의metadata wire가 작아도 RLE 확장 결과와 독립 검사량은 줄어들지 않는다. canonical read가 장시간 유지될 때의 반복 물리 read를446개의 독립 capture에 더하지 않는다.

905/906/907에서 ingress byte 중1302/1305/167개는 host가 IDLE/DONE이 아닐 때 들어왔다. cold 두 프레임의 같은-clock A/B11회는 **port A와 B를 하나의 순차 RAM port로 합치면 새로운 stall이 생기는 실제 반례**다. warm에서 같은-clock 충돌0이라는 사실로 다른 프레임의 동시 소유권을 지울 수 없다.

관측 정상 경로에서 `range_ready=0`인 expected write는0이었다. 그러나 RTL의 `canonical_write313` 자체는 range_ready로 gate되지 않는다. 현재 ISSUE의 쓰기 의미를 generic grant로 옮길 때는 stalled ISSUE의 반복 같은 값 쓰기와 STOP/fault 억제를 명시해야 한다. 정상 trace0만으로 모든 backpressure 조합의 동치를 증명하지 않는다.

최종 op3의 MREAD→MDONE 순회 구간은9관측 모두 **23.308µs**였다. 이 안의 독립 expected capture446을 유지해야 한다. 전체 구간을 없애는 불가능한 가정조차 후반0.653249ms 요구의 약3.6%에 해당한다. ACK/VBlank 경계와 결합한 전체 이득은 별도 측정이 필요하며, 순회 시간 전체를 삭제 가능한 overhead로 계상하지 않는다.

## 삭제·유지·추가를 묶은 구현 경계

| 경계 | 실제 삭제 대상 | 반드시 유지/추가할 것 |
|---|---|---|
| queue→host header 전달 | queue `field338`, load_enable/load_at/record_at/record_valid/record_byte 전용 adapter; host HLOAD 전용 반환 dispatch | 원본 slot RAM,packet_seq 재검사,명령별 의미검사,최종 필드가 모인 뒤 CHECK |
| packet 읽기 | HLOAD/PREAD/DREAD/MREAD별 RAM 발행·응답 전용 연결 | 공통 READ/RETURN과 consumer kind;1clock 응답 귀속,header pipeline 처리량 |
| 주소 소유권 | queue의 load-specific mux와 host/parser의 별도 field index 연결 | packet-vs-expected 물리 선택,retired bank,현재 byte와 다음 batch descriptor 끝 값 |
| 진행 | 각 return 경로의 별도 완료/증가 연결 중 동치가 증명된 부분 | encoded 소비와 expanded 출력 cursor 분리,range 수·token 갱신은 실제 consume 뒤 |
| expected 접근 | metadata write/final scan을 각자 RAM으로 전달하는 adapter | expected 독립 내용,validator read 시각,write grant,STOP pending 취소 |
| ingress/credit | 이번 삭제 대상 아님 | port A·SPI CRC/identity·accepted/retired/consumed 분리·불변 slot 수명 |
| receipt/display | 이번 검사 삭제 대상 아님 | 실제 read CRC/coverage/private receipt,정확한 finalACK/token·12read·VBlank |

host port B의 단일 소유자는 **같은 RAM port에 대한 dispatch를 하나로 만드는 것**이다. producer와 checker의 상태/데이터를 동일한 성공 비트로 합치지 않는다. final scan은 canonical expected 주소를 validator가 제공하고, 해당 응답을 같은 clock 계약으로 전달한다. 포트에 우선순위 arbiter를 덧붙이는 방식은 기존 phase 배타성을 낭비할 수 있으므로 먼저 phase별 정적 선택으로 설계한다.

현재 active121bit는 mutable 실행 문맥이라 유지한다. header/record312는 이미 wire이므로 삭제 절감0이다. `cursor`는 batch 끝 주소를, `parser_address`는 현재 payload byte를 가지므로 둘을 무조건 하나로 합치지 않는다. `at`도 BEGIN/repeat seed 등 다른 역할이 있어 header 사용을 없앴다고 전체 레지스터를 제거했다고 세지 않는다.

## 349의 순차 header 안을 수정한 후보

기존 field 순서는 `[0,1,2,3,10,11,14,15,12,13,16,17,18,19,20]`의 명령별 prefix다. 개선 후보는 **0..3을 읽고10으로 한 번 건너뛴 다음 끝까지 증가**한다. 주소12/13의 encoded와14/15의 span을 채우는 순서만 바뀌며 CHECK 전에 둘 다 완성된다. identity4..9는 이미 ingress에서 검사하며 기존 loader도 읽지 않았다. packet_seq2/3은 계속 읽고 검사한다.

349의 전체16/20/21B 순차 읽기와 달리, 이 후보는10/14/15개의 같은 필드만 읽으므로 **추가6clock/packet이 필요하지 않다**. 실제905..907 E1 packet의 최종 field dictionary를 두 순서로 비교한다. 이는 주소/필드 모델의 동치이며 새 RTL 구현·STOP 동치·합성 절감 proof가 아니다.

삭제되는 field lookup 대신 physical cursor의3→10 jump와 반환 byte의 주소 decode가 들어간다. 공통 response tag/valid가 추가될 수 있고, 기존 state가 암묵적으로 보장하던 응답 소유권을 다시 저장하면 절감이 상쇄될 수 있다. header는 현재1byte/clock pipeline이므로 일반 READ/RETURN의2clock/byte로 바꾸지 않는 것이 필수다. 새 format,normalized header copy,40B gap 사용,wire byte 증가는 필요하지 않다.

## 첫 BG 요청의 비용 분리

제한 ROM 연속 warm907에서 source done→첫 BG ROM 요청5.712000ms는 다음과 같이 분해된다.

| 항목 | 측정/모델 비용 |
|---|---:|
| 실제 M4 실행440125instructions,CPI1/84MHz |5.239583333ms|
| 완료된 E1/E2/첫 E9 transaction |0.464762ms|
| source→output 활성화·clock 정렬·plan/ROM 요청 전달 등 잔여 |0.007654667ms|

IRQ wait0,planner/service checkpoint31개다. 따라서 이 구간의 주원인은 반복 polling 대기나 header RAM 대기가 아니다. 첫 E2 응답 검사는 유지해야 하며, 이것을 없애도 수ms가 나오지 않는다. 고정 위상 값은 별도 분석 행을 사용하며 연속값을 그대로 빼지 않는다.

warm의 초기 top-level 준비는 expand70407 + begin7577 + geometry35879 + H2 12060 + input_commit2591 + begin_step138843 = **267357instructions/3.182821429ms**다. 첫 E1 앞의268634instructions에는 여기에 serializer 등의 나머지가 포함된다. nested start/geometry watch와 top-level costs는 중복 합산하지 않는다.

`start286`은 COMMITTED/generation을 검사하고 raw pixel 범위 검사,dirty material 비교,bank 준비를 한 뒤 BG 진행을 허용한다. `nes_dirty231_material`의 주석과 구현은 이전 표시 material을 **BG key 준비가 patch scratch를 덮기 전에** 비교하도록 요구한다. 이 준비를 첫 BG 뒤로 옮기는 것만으로는 안전하지 않다. 다음 ARM 후보는 해당 비교의 입력 수명·정확한 dirty 결과를 유지하면서 재사용 가능한 준비를 찾는 것이며, 별도 shadow RAM/재검사/복사 비용을 모두 포함해야 한다. 무조건 생략하거나 full COMMIT 이전에 유효 표시로 공개하지 않는다.

고정 ROM 위상 기준 요청8.381149ms는 이전 허용 구간 끝6.089722ms보다2.291427ms 늦다. ROM accept 이후3.833249ms는 계획 상한3.180ms까지0.653249ms를 더 줄여야 한다. 첫 BG를 몇µs 당기는 것만으로 이전 창을 넘었다고 주장하지 않으며, 창 안의 전체 ROM read와 arbitration을 검증한다. 연속 일정의4.022994ms 초과와 고정 일정의8.384533ms 초과는 다른 비교축이다.

같은 시작/ROM 위상의 source done→첫 요청은5.714409ms다. ARM440332instructions/5.242047619ms +SPI0.464763ms +잔여0.007598381ms로 분해되며, 연속 일정 대비207instructions 차이도 그대로 비용에 남겼다. 첫 E1까지3.204751ms, 첫 E9 시작→첫 요청0.149063ms다. source_done 관측 edge와 source cycle 합산의45ns 수준 차이를 숨기기 위해 어느 항도 조정하지 않는다.

## 전체 회로 예산과 판정

관측 RTL hash가338과 같으므로 기존 Quartus Lite 전체 MAP **22144LE /17274comb /9018FF /307808RAMbit**를 그대로 사용한다. 관측기 때문에 제품을 재합성하거나 새 절감을 주장하지 않는다. 순회로 절감0,시간 이득0이다.

이번 좁은 삭제 경계인 host2161 +queue225는2386comb다. SPI573·plan459·source1747·validator/aperture1159·나머지10950을 유지하면,여유155를 둔 전체cap15253에 닿으려면 host+queue가 **365comb 이하**여야 한다. 즉2386에서2021comb(약84.7%)를 지워야 하므로, 이 포트 통합만으로 전체 부족을 해결할 구조라는 근거는 없다. 삭제 state 수·121FF·주소식 수를 LUT 절감으로 환산하지 않는다.

다음 구현의 좁은 gate는 (1)header 처리량 유지,(2)추가wire/slot/RAM 없음,(3)consumer별 응답/STOP 동치,(4)host+queue를 포함한 whole Lite 순회로 감소,(5)동일 위상/연속/정상 ROM의 전체 일정 비회귀다. 이 gate를 통과하더라도60fps/whole fit 달성으로 승격하지 않는다. 전체2021comb와첫 BG2.291427ms 요구를 별도로 닫을 더 넓은 실행/준비 구조가 필요하다. 미달 시 상태 번호·seed·FIT 반복 대신 경계를 재설계한다.

Production227/GBC164/saveSRAM은 변경하지 않으며 자동 merge하지 않는다. 과거338/336 및348 실패 증거를 보존한다.
