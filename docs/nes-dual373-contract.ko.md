# NES373: 입력·표시 문맥,4packet source ring과 공통 진행 제어

## 구현과 판정 경계

NES372 ARM의 실행 이미지와 MASK·SHIFT 압축 ABI,causal BG5·OBJ2 hint를 유지한다. source core는 입력 ACK 뒤 IDLE로 돌아오며,별도 표시 문맥은 자신의 최종 ACK와 plan drain까지 유지한다. 이전 표시가 진행 중이어도 다음 collector를 source로 materialize할 수 있다.

새 회로는 검증 후보이며 production227/GBC164/saveSRAM과 기존 VBlank firmware는 변경하지 않았다. 전체 Lite MAP은 성공했지만 comb가 여전히 용량을 넘으므로 실기용 후보나 지속60fps 성공으로 승인하지 않는다.

## 같은 시작·ROM 위상과 연속 일정의 결과

372와907~914의 source 시작 시각/ROMcycle가 동일하며,capture907의 사전5,371,247clock과 이후357,368clock 기한을 유지했다. 이8쌍의 표시 처리 기간 변화는0..0.454µs 증가에 그쳤다. 새 footer 확정/reader 비용을 포함하며,새 시간 개선으로 세지 않는다.

|frame|372 표시 처리 ms|373 표시 처리 ms|373 materialized ms|
|---|---:|---:|---:|
|907|11.879334|11.879698|0.584993|
|908|12.104741|12.105105|0.577220|
|909|15.933014|15.933377|0.615447|
|910|11.865608|11.865926|0.567403|
|911|12.206831|12.207195|0.591448|
|912|15.237431|15.237795|0.595039|
|913|11.940062|11.940425|0.568994|
|914|21.500992|21.500992|0.601538|
|915|17.269452|21.111314|0.594220|

915는 시작 자체가5.172756ms 빨라져 같은 source 시작 위상의 A/B가 아니다. 시작부터 완료까지21.111314ms로 보이지만,이전372의17.269452ms와 기간만 비교하면 중첩을 놓친다. 절대 표시 완료는1.330894ms 빨라졌다. input915는 실제 이전 표시 retire보다5.097348ms 전에 시작해4.503128ms 전에 materialize했다.916도 이전 실제 retire 전에 source를 시작하고 materialize했다. 이중 문맥/별도 RAM을 통한 실제 실행이며 추정 중첩 시간을 더하지 않는다.

914 materialized는2.299063→0.601538ms(-1.697525ms),다음915 capture 여유는0.041159→1.738684ms다.916 capture는 기존4.408605ms 지각에서1.746003ms 여유로 바뀌었다.917도1.772094ms 여유로 승인했다. 최종905~916의12프레임(초기화2/warm10) 배출,908~917 capture10/10 승인,오류0/경고0다.917은 다음 캡처 승인까지만 확인했으며 표시까지 처리한13번째 프레임은 아니다.

source payload/CRC·causal hint packet과논리 plan record는372와905~915의11쌍 모두 같다. 916은 새로 실행한 프레임이다. 모든30개 공통 compiled module이 기능 테스트와 전체 보드에서 바이트 일치하며,새11개 canonical 파일의 SHA manifest도 대조했다. 독립 read coverage는5,011개 unit,528개 publish를 실제 read/private-write 순서와 맞췄고출력credit은2 이하다. 각 표시의12개 exact read/token과 실제 generation retire를 검사했다.

실행 ARM PT_LOAD는372와 같고 text35,862/data4/BSS48,476B,관측stack1,288B다. SPI는12프레임45,528B이며IRQ body41회/EXTI254회를 반영했다. ROM 기원 기준62,222요청/응답,입력10,877쌍,pending0으로 끝났다. input/display 경쟁을 제외한 시간은 사용하지 않는다.

lease 공백 수정 뒤907 첫 BG는6.829872ms로 기존6.829554ms와 같은 허용 구간을 사용했다.914 첫 BG는16.857025ms로 그대로이며 ROM window 대기는 남았다.914 처리21.500992ms는60Hz 예산을4.834325ms 초과한다. warm 연속 완료 간격의 최대도914의25.804373ms다. source를 일찍 저장해 다음 캡처를 보존한 것과 일정한60fps 표시 완료는 별도다.

## 실제 삭제·대체한 제어

- source의 V_IDLE 표시 대기와 source cursor를 이용한 plan 진행을 제거했다. plan transport가 자신의 NES cursor를 소유한다.
- source의 두40bit descriptor mailbox와 descriptor0/1,publish/sent/busy 왕복을4슬롯 Gray-pointer ring으로 대체했다. 1KiB source RAM은256B×4이며 각 슬롯의250..255에 길이/final/generation/CRC를 둔다. 여섯 footer byte를 쓴 다음에만 write pointer를 공개한다. host footer reader의 준비 비용과 CDC는 실제 일정에 포함한다.
- source의 별도 header CRC8 함수를 제거하고 공통 SPI CRC8 datapath로 D4 reply를 계산한다. E1 ingress length도 SPI의 기존 request-length 문맥을 재사용한다.
- queue의 field338 재배열 LUT를 제거하고 header [0..3],[10..20]을 순차 공급한다. host active-record loader의 encoded/span 배치를 함께 바꾼다. 기존 header loader FSM과 descriptor/manifest/receipt 실행 FSM 전체를 삭제한 것은 아니다.
- 기존 source/validator phase RAM 공유를 폐지하고 source scratch512B를 분리했다. validator의1KiB RAM과 queue의 독립 expected 저장 및2개 출력 슬롯은 보존한다. source ring 증가512B+scratch512B로 실제 추가 RAM은8,192bit다. 이전 예산의 scratch1KiB를 모두 추가하지 않았다.

Gray write/read pointer만 packet ownership을 넘긴다. source와 host는 각각 footer와 payload를 확정한 packet만 접근한다. full/read_seen/token/generation/CRC8·END final·마지막 drain을 확인해야 POP/D5 입력 ACK가 가능하며,D5는 SNES 최종 표시 ACK가 아니다. token은 프레임마다 초기화하지 않는다. 공통 reset 이후의 STOP/fault는 sticky이며 부분 packet은 공개하지 않는다.

## 입력·표시·선행 hint의 수명

입력 context에는 epoch/generation/serial/raw와 armed/started/materialized/committed가 있다. 표시 context는 독립적으로 동결한다. 입력 materialized만 collector를 release하며 이전 표시 ACK/retire는 다음 입력을 지우거나 collector를 해제하지 않는다. source serial은 입력 ACK에서 증가하고 표시 serial은 promotion 때 바인딩된다.

표시가 invalid인 동안 표시용 레지스터는 다음 입력의 prelease identity를 운반한다. 표시가 valid이면 이전 문맥을 유지한다. retire 후 이미 admitted인 입력 문맥으로 넘겨 plan·ROM 경로의 별도 input/display mux를 줄였다. 이 레지스터의 speculative 값은 display lease 없이 ACK를 허용하지 않는다.

첫 통합에서 입력 ACK와 display promotion 사이1클록 동안 prelease와 display lease가 모두0이 되어 in-flight hint를 취소했다. 첫 긴 실행은 캡처를 놓치지 않았지만907 첫 BG가6.829554→16.856888ms로 밀렸다. 두 번째 후보의 실행은 같은 원인을 확인한 뒤 의도적으로 중단했다. 최종 후보는 promotion 전까지 prelease를 유지하고,이1클록 공백을 잡는 회귀 검사를 추가했다. 중간 실행을 시간 개선 근거로 사용하지 않는다.

## 전체 Quartus Lite 비용

|항목|372 기준|373 최종 MAP03|변화|
|---|---:|---:|---:|
|LE|22,710|22,601|-109|
|comb|17,698|17,757|+59|
|FF|9,171|9,091|-80|
|RAM bits|292,448|300,640|+8,192|

회로 부족은2,290→2,349comb이며155여유를 포함하면2,504개 순삭제가 필요하다. FF/LE 감소를 comb/FIT 성공으로 바꾸어 말하지 않는다. 같은 board boundary의 전체 수치이며 inclusive parent와 child를 중복 가산하지 않는다. MAP01은17,775comb,context mux를 줄인 MAP02는17,749comb,lease 공백까지 수정한 MAP03은17,757comb다. 필요성이 있는 구조 변경마다 합성했으며 seed/opcode/FIT 반복은 하지 않았다.

host descriptor/manifest/receipt FSM과 NES plan operand decode 본체는 남아 있다. 공통 CRC/길이/header address/cursor 경계의 실제 대체와,공통 host 실행기 전체 교체를 구분한다. 현재 구조만으로 시간·회로를 함께 줄였다는 결론은 성립하지 않는다.

## 검증

최종 검증 수치와같은 시작·ROM 위상/연속 일정의 차이는 analysis/dual373-verification.json 및 nes-dual373-plan.json에 기록한다. 실제 compiled M4 code·SPI 신호·IRQ body,입력과 출력 기원별 ready-gated ROM 경쟁,2슬롯 출력 credit,독립 read→unit→private write→publish·CRC/coverage,12개 exact display read/token과 실제 retire를 검사한다. capture 기한은 readiness에 맞춰 미루지 않는다.

14개 directed case는 context 겹침/이전 ACK/late DONE/잘못된 retire generation/epoch 변경/STOP,4슬롯 full/잘못된 token·generation·CRC8/중간 취소/END 전 D5/tokenFFFF 말단/read 재사용과 fault 뒤 RAM 불변을 확인한다. context 단위 검사는 collector stub을 사용하며,실제 collector는 긴 연결 실행에서 별도로 검사한다. unit의 성공을 전체 PPU 검증으로 부르지 않는다.

실제 ARM은 compiled C의 실행이며 CPI1/84MHz·exception/peripheral 할당모델이다. ordinary65816 trace와map DMA/최종 표시 bus model을 사용한다. 기존 VBlank firmware를 보존했으나 전체65816/VBlank·live NES CPU·firmware WCET·heavy7/71·다중 ROM 시작 위상·session reset·FIT/STA·실기60fps 증명은 남아 있다. 기록된71입력 중 최대6packet은4슬롯만으로 전부 저장되지 않으므로 ARM raw500B와 실제 refill/IRQ 공급을 연결하기 전에는71프레임 캡처 성공을 주장하지 않는다.

## 다음 교체 경계와 예산

현재8모듈 self comb 합은6,071이다. source codec1,337+validator1,039=2,376을 보존하면나머지 제어3,695를1,191 이하로 바꿔야155여유 포함2,504순삭제를 충족한다.8모듈 전체 교체 시에는3,567 이하가 필요하다. 입력·표시 context와 bridge가 이8모듈 밖에 남는 비용도 전체 board에서 계속 부담한다. 새 replacement의 합성 비용은 아직 없으며 이 상한을 절감 실적으로 쓰지 않는다.

다음은 이미 연결한 입력/표시 ownership과1KiB ring/512B scratch를 유지하면서 host HLOAD/HCHECK·descriptor/manifest/receipt 주소 진행,queue ingress/credit,plan endpoint/operand decode 본체를 함께 교체하는 경계다. 기존FSM을 남기는 wrapper나 FF 감소만으로 승인하지 않는다. source RAM은 NES write/host read,validator RAM은 host expected/read-event 우선,plan RAM은 host write/NES read를 유지하며 clock mux로 합치지 않는다. native32B/32bit word plan,queue context RAM과 ARM raw500B는 후속 후보이고 이번 구현/시간 이득에 포함하지 않는다.

시간은914의ROM 허용 구간을 놓치지 않는 plan 준비·공급과후반 OBJ/DMA/manifest 실행을 함께 검토한다. 시작 위상을 옮겨6.8ms와16.8ms 창을 비교하지 않으며 같은 capture/ROM origin과연속 schedule 둘 다 검증한다. 이후6packet/heavy7/71·다중위상과전체65816/VBlank·firmware WCET·CDC/IO/전체Lite FIT·STA·실기 순서로 진행한다. 현재는 회로 부족으로 FIT/STA를 실행하지 않았다.
