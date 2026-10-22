# NES309 — 실제 ARM 준비 시각과 bounded 사전 준비의 분리 검증

## 범위와 판정

307의 실제 ARM·IRQ·ROM 경로에 수동 관측을 추가해 `next_step286`의 최초 완료와 `prepare289` 진입/복귀를 계측한다. 사전 준비 후보는 **ARM만 변경**하며 source·SPI packet·queue credit·FPGA host/validator·SNES 소비 경로는 유지한다. queue 보관/credit 재설계는 이번 구현에 포함하지 않는다. 실물 MCU cycle 계측이나 full RUN 실행이 아니다.

**후보 미채택.** ROM 대기 중 준비를 마치는 기능은 검증했지만 정상/제한 warm907 모두 회귀했고 회로 절감은0이다.

|조건/frame|307 ms|309 ms|차이 ms|
|---|---:|---:|---:|
|normal/905|78.493058072|78.509421512|+0.016363440|
|normal/906|54.952658742|54.943113402|-0.009545340|
|normal/907|14.356691354|14.377191108|+0.020499754|
|restricted/905|103.654756128|103.657528822|+0.002772694|
|restricted/906|116.901733526|116.879961060|-0.021772466|
|restricted/907|17.616924958|17.620470370|+0.003545412|

제한907은17.620470370ms/목표 초과0.953803703ms다.307 기준의0.950258291ms를 해결하지 못했다. source cycles까지 최종 합산한 차이는+0.003545412ms다. 정책 여유0.25ms를 포함하면 이 후보에서1.203803703ms가 더 필요하다.

|기준307 metadata 최초 완료|절대ms|첫 BG 승인까지 남은ms|
|---|---:|---:|
|905|53.167187857|-5.675234857|
|906|180.547738810|-35.592955810|
|907|271.890506857|+3.014535143|

제한907은 준비 가능 시점이 BG 승인보다3.014535ms 빠르지만 cold905/906은 이미 첫 BG 승인이 지난 뒤다. 모든 프레임에서3ms가 생긴다는 결론은 아니다.

309 제한907은metadata271.873507ms 확정→12단계 준비271.917043ms 완료→BG 승인274.905042ms다. 준비 완료 후 약2.987999ms 여유가 있고 마지막 `prepare289` 호출은1851→79명령으로 줄었다. 원래 준비 자체는1851명령/22.035714µs(CPI1/84MHz)다. 단계 사이 priority 확인을 포함한 일회 준비는 unit guard에서3639명령이며 새로운 CPU 작업은 공짜가 아니다.

정상907은metadata185.281243ms 확정, 첫 BG 승인184.022087ms로 이미 늦었다. 최종 준비가1851→2820명령으로 증가했고, 정상905도같은fallback 비용을 낸다. normal906은 다른 대기에서 준비하여79명령이다. 정상907의총명령694430→696446(+2016),제한907은697018→700060(+3042)다. SPI bytes는정상1019/제한1079로변하지 않는다.

제한907 absolute finish는280.265546→280.250092ms로15.454µs 빨라졌지만 frame start도262.648621042→262.629621630ms로18.999412µs 빨라졌다. BG 승인274.905042ms는그대로여서frame elapsed는3.545412µs 늘었다. 유리한ROM위상을고르거나frame 시작비용을빼지않는다.

whole Lite는307과같은22402LE/17583comb/8965FF/307808bits다. 추가MAP은없고실제functional RTL hashes가307과동일함을확인했다. comb 부족2175는그대로다. ARM text28094→28306B(+212),BSS47120→47124B(+4),live observed stack1288B 동일이다.

검증: 실제기준3+정상3+제한3=9개성공live 일정,후보E1/E9 bytes/order동일,4credit/최종ACK PASS. preparation24·native71/1039commands/73260B·STOP35/IRQ재개11·supply20·wait7·credit11·H2 9·IRQ8/33exceptions PASS. preparation단계최대는live340명령,함수호출guard341명령(약4.06µs)이며실물WCET가아니다. 새metadata준비를전체71live로검증했다고세지않는다.

## 사전 준비의 구현과 소유권

- `seal289[206]`를 그대로 사용한다. 새 encoded packet 버퍼 없이 cursor4B만 추가한다. header40B를 준비한 뒤 requirements166B를16B씩 복사한다. 총12단계이며 마지막은6B다. metadata prepared/valid와 기존 source COMMITTED·serial/generation/target·open/fault 검사를 유지한다.
- `work302`에서 기존 OBJ planner와 plan 공급을 우선한다. 기다릴 이유가 남고, planner가 끝나고, 공급할 writable/unknown plan이 없고, GPIO IRQ가 낮을 때만 한 단계 실행한다. 각 단계 사이에 이 조건을 다시 확인한다. SPI 호출/재귀·credit 변경·receipt 발행은 없다.
- `packet_wire`는 synchronous dispatch 대기 동안 producer를 BUSY로 둔다. 내부 `prepare_slice309`만 BUILD 또는 BUSY에서 **별도 seal buffer**를 쓸 수 있다. 전송 중인 stack packet/wire259는 변경하지 않는다. 공개 `prepare289`의 BUILD 조건은 유지하며 final 준비가 BUSY에서 성공할 수 없다.
- reset/abort/새 begin/commit에서 준비 cursor를 초기화한다. STOP 뒤 완성된 cache도 준비·commit을 허용하지 않는다. 아직 준비가 남으면 마지막 `prepare289`가 같은 단계를 동기적으로 마친다. 불완전한 seal이 전송될 수 없다.

단계별 고정 비용은 hardware latency 상한이 아니다. 실제 GPIO 관측과 IRQ adapter는 기존 foreground checkpoint 모델이다. 조건 확인 직후 도착한 DMA/IRQ는 다음 확인 시점까지 기다릴 수 있으며, flash wait-state/실물 NVIC latency를 검증한 것은 아니다. 준비 함수의 CPU 명령 수와 SPI/ROM 대기를 중복 차감하지 않는다.

## 검증과 보존한 실패

기준 reference01은307 ELF의 loadable bytes와 일정·명령 수가 같아야 한다. 관측 hook은 target 명령을 삽입하지 않고 기존 callback의 RTL 시각에 미정산 ARM instructions/명시 exception cycles를 보간한다. 이것이 metadata 확정 시각의 의미다. `next_step286`가2를 반환한 첫 시점은 valid/resident/dirty prepared와 최종 plan flush가 끝난 시점이며, 각 flag의 개별 store 시각은 아니다.

새 preparation guard는 원본 ARM이 만든206B seal과 새12단계 결과를 비교한다. DMA ready/plan writable·unknown/IRQ high/queue credit 여유/16bit wrap, 단계 사이 IRQ,0~12단계 각각의 STOP, BUSY 중 wire259 불변과 공개 prepare 거부, FAULT에서 완성 cache 거부를 검사한다. 제어 입력을 주입하는 실제 M4 함수 검사이며 live SPI 일정과 구분한다.

정상·제한905~907은 원본 E1/E9 bytes와 순서를 바꾸지 않고 max4credit·최종 ACK를 확인한다. 원본71 producer와 retained ARM STOP/IRQ/credit/H2 검사도 같은 ELF에 적용한다. FPGA RTL hash가307과 동일하므로 기존49 RTL/13 SPI guard와 whole Lite MAP을 재사용하며 새 합성 절감으로 세지 않는다. 동일 RTL을 다시 합성하는 반복은 하지 않는다.

window01은 실제 실패로 보존한다. 처음 내부 준비 함수에도 BUILD-only 조건을 적용하여 BUSY 전송 대기에서 준비가 실패했고, producer `tiles290` 실패 뒤 simulator가 ARM rendezvous를 기다리다 종료했다. 라이선스 문제가 아니다. 내부 seal 쓰기와 공개 final 준비의 허용 상태를 분리한 뒤 window02/normal01로 다시 검증한다. 상태 검사를 제거하거나 STOP·독립 FPGA 검사를 완화하지 않는다.

## queue·credit 및 host·validator 교체 판단

이 후보는 준비 CPU 비용만 옮기며414B metadata의 SPI 전송과 실제 소비를 앞당기지 않는다. 작은 준비 비용을 ROM 대기 전체3.78ms와 동일시하거나 host 회로 절감으로 계산할 수 없다. 따라서 NES308의 넓은 교체 경계가 여전히 필요하다.

307 own-cost는 host2093/validator1251/queue118/SPI713/plan506/glue49=4730comb, 밖12853comb다. host를0으로 해도82comb 부족하다. 새로운 보관 FIFO를 덧붙이는 대신 다음을 한 경계로 교체해야 한다.

1. queue의 고정 slot 보관과 byte/record credit. 907의9packet/387storedB가1024B에 들어간다는 산술만으로4slot 제한을 없앨 수 없다. cold/raw fallback 및 tile 진행 공간, ordered retirement와 wrap 비용을 포함한다.
2. host header/body reader와 validator manifest reader의 포트 선택을 단일 active record/reader로 교체한다. encoded cursor와 expanded cursor는 다른 의미이므로 검사를 없애며 합치지 않는다.
3. host의 XBEGIN/XWAIT→CONSUME/retire와 validator의 별도 완료 소유권을 record의 수신/보관/실행/실소비/retire로 대체한다. 수신 완료를 DMA receipt 또는 최종 표시 ACK로 사용하지 않는다.
4. manifest를 앞에서 보관하더라도 terminal 검사와 display 허가는 실제 소비가 끝난 fence에서 수행한다. 독립 CRC/coverage/H2와 STOP write-freeze,12 display read·최종 ACK를 유지한다.

이번 준비 시각 계측으로 metadata가 첫 BG 승인 전에 확정된다는 조건은 확인했다. 그러나 이것이 선행 전송의 진행 가능성을 증명하지는 않는다. **manifest를 보관한 채 기존 ordered retired counter를 붙들면**, 뒤의 tile/DMA가 완료되어도 앞 manifest를 건너뛰어 credit을 반환할 수 없고4개 창이 차면서 다음 DMA 발행이 막힌다. 단일 head bypass만 추가하는 방식도 이 순환 대기를 풀지 못한다.

공동 후보는 ingress 저장 credit과 실제 실행/receipt 완료를 명시적으로 분리해야 한다. 원본 CRC·identity를 검사한 후 예약된 byte/record 공간에 저장했을 때만 ingress credit을 반환하고, 실제 소비는 generation/token별 별도 fence로 확정해야 한다. 공간이 부족하면 credit을 반환하지 않는다. 이 변경은 기존 retired counter의 의미를 그대로 유지하는 최적화가 아니라 프로토콜 교체다. 새로운 byte/record credit·ordered fence·STOP 무효화 비용까지 포함하여 기존 queue/host/validator 제어를 없애야 하며, FPGA 저장을 ARM 전송 완료로 대체하지 않는다. RAM 총량과 최대 record 수·cold fallback·포트 동시 사용이 증명되기 전 구현 채택이나 면적 절감을 주장하지 않는다.

기능 예산2427comb(입장/DMA700,독립검사900,queue/SPI450,plan328,glue49)+128여유=2555 hard cap은 **요구 상한**이다. 새 arena/record/credit/포트/CDC 제어 비용이 이 안에 들어온다는 합성 근거는 없다. 예상 MAP은 null이다. 307 전체17583comb에서 최소2175,정책 여유 포함2303comb를 줄여야 하며 source/control 밖 비용도 최종 whole Lite에서 다시 측정한다.

PPU DMA·VBlank·최종 bank 전환 조건 및 ROM 허용 window/core 우선권은 변경하지 않는다. 새 packet 저장 구조를 구현하면 저장→실행 순서 변경이 실제65816의 VBlank에 미치는 영향을 별도로 검증해야 한다. 이번 unchanged wire/RTL 검증이 그 미래 구조의 VBlank 증명은 아니다.

full ARM RUN·전체71/heavy7 live 일정·full live65816·FIT/STA/CDC/IO·실물60fps는 미검증이다. production227/GBC164/saveSRAM과307/308 증거는 보존한다. 실행 및 입력 SHA의 근거는 `analysis/prepare309-verification.json`, 재현 도구는 `tools/analyze_nes_prepare309.py`다.

분석 analysis01은 다른 빌드 디렉터리의 ELF 파일 전체 SHA를 guard 입력과 비교하여 실패했다. 실제 guard 입력은 window02 ELF에 고정하고 normal01과 window02의 PT_LOAD bytes 일치를 별도로 확인한 analysis02/03을 선택한다. metadata/schedule 입력은 변경하지 않았다.
