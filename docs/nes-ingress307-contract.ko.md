# NES307 — 실제 manifest 선행 큐잉·공통 ingress·실행기 검증

## 판단

마지막 DMA 뒤 manifest를 실제4credit/IRQ 경로에 연결했다. common SPI가 E1/E9의 CRC16과 transaction 종료 검사를 처리하고, 기존 validator의 bounded RLE 실행기를 requirements166B와 map256B에 함께 사용하도록 교체했다. 독립 bounds·실제 consume CRC·coverage·STOP·최종12read ACK와 BG ROM window/core 우선권은 유지했다.

**후반 경로와 회로는 개선됐지만 제한907 전체 일정은 회귀했다. 따라서 공동 목표 달성 후보로 승격하지 않는다.** 기존 ARM296/RTL300 기준, 부분 검증305와 production227/GBC164/saveSRAM은 보존한다. 아래 모든 수치는 새 실물 측정이 아니라 기존 범위의 실제 M4 명령·RTL 실행 및 whole Lite MAP이다.

## 실제 교체와 남은 제어

1. ARM `dispatch289`의 requirements 발행 전 `drain()`을 제거했다. 마지막 ordinary DMA packet이 이미 순서대로 accepted된 후 `send()`가 확인한 빈 credit으로 op15를 전송한다. 그 앞의 `flush260()`과4credit/sequence/CRC 검사, 최종SEAL 뒤 drain은 유지한다. `sent`는 enqueue 이후 증가하고 `retired`는 검증된 응답만 반영한다.
2. SPI link에 shared close/format-valid 두 신호를 추가했다. E1 exact length/CRC16 residue, E9 length/count/CRC8/trailer/CRC16, EA length/CRC8/trailer를 중앙에서 계산한다. queue·plan endpoint의 local enable/can_write/closed/retiring/ownership 검사는 남겨 두고 wire-format 재검사를 교체했다. 기존에 공유하던 bit/count를 새로운 절감으로 세지 않는다.
3. 기존 E1 CRC16 accumulator를 E9 payload에도 사용한다. 포함 범위는 E1 command+packet+CRC와 E9 payload-only로 다르며 transaction 시작의 seed/reset을 유지한다. 실제 plan path는 `SHARED_CRC307=1`로 기존 batch CRC16 accumulator와 전달용 CRC 저장을 합성에서 제거한다. standalone legacy transport의 기본값은0으로 유지한다. 독립 의미 검사·receipt CRC를 제거한 것이 아니다.
4. op15 section1/codec1을 compressed requirements 형식으로 사용한다. header16B와 display24B를 그대로 유지하고166B requirements만 zero/literal run으로 전송한다. 실행기의 내부op4는 이 형식만 의미하며 외부 ordinary op4와 별개다. 기존 map op11 decoder/zero expansion/검사 진행 상태를 공유한다. 도메인166/256, literal 끝, run 끝, codec, exact expanded count를 검사한다. 새 별도 decoder RAM/FSM은 추가하지 않았다.
5. ARM은 encoded packet이206B 이상이면 기존 section0 raw206B로 돌아간다. run 생성 전에 상한을 확인해259B wire buffer를 넘지 않는다. 실제71입력은 SPI64..87B이며 제한907은209→64B다. 최대128run/zero/literal/교대입력의 raw fallback도 실제 M4에서 확인한다.

출력4packet RAM과 plan2bank RAM, clock-crossing mailbox는 유지한다. plan과 DMA를 단일 FIFO로 합치지 않는다. host의 HEADER/body/read ownership과 validator 완료 relay 전체를 없앤 것은 아니다. **이번은306의 큰 공동 경계 중 ingress와 manifest 실행의 부분 교체**다. host 약750comb라는 요구 예산에는 아직 크게 미달한다.

STOP은 기존 cancel/lease 경로로 공개·RAM write·후속 DMA를 막는다. 진행중 transaction의 공통 CRC가 남아 있어도 endpoint의 live/cancel gate 없이는 seal/queue commit이 되지 않는다. namespace 재개에는 기존 quiesce 규칙이 필요하다. manifest 선행 전송은 accepted만 앞당기고 receipt/SEAL/display ACK는 기존 실제 소비·독립 검사 뒤에 남는다.

## 실제 credit·ARM 일정

제한905/906/907에서 op15가 물리 SPI에 진입할 때 모두 **pending=3**이었다. 즉 미완료DMA를 앞에 두고 네 번째 credit에 manifest를 붙였다. 관측은 실제 CPU의 physical267 진입에서 sent/retired/sequence를 읽으며 모든 E1 발행의 pending<4를 확인한다. 계측은 CPU 명령을 추가하지 않는다.

|제한 조건/frame|305 ms|ARM 선행큐잉만/305 RTL ms|307 공동 후보 ms|
|---|---:|---:|---:|
|905|104.883650472|104.089432730|103.654756128|
|906|116.901188078|116.901097170|116.901733526|
|907|17.462790444|17.537925906|17.616924958|

제한907 목표 초과는 **0.796123777→0.950258291ms**,305 대비+0.154134514ms다. cold905는1.228894344ms 빨라졌지만 cold906의+0.000545448ms와907 회귀를 함께 보고한다. isolated01은 원본 E1/E9 bytes/order를 유지한 실제3프레임 분리 실행이며 새 issue307 계측은 worker 경로 수정 전이라 없다. joint window03에는 실제 issue 계측이 있다.

ARM text28094B(305 대비+176),BSS47120B 동일, live 관측stack1288B 동일. 별도 native intercepted producer의stack976B를 full live stack으로 대체하지 않는다. 제한907 명령703224→697018, SPI1236→1079B. 명령 감소·SPI byte 감소·ROM 대기를 단순 합산해 net gain으로 세지 않는다.

|정상 조건/frame|305 ms|307 ms|차이 ms|
|---|---:|---:|---:|
|905|79.721134244|78.493058072|-1.228076172|
|906|56.180144012|54.952658742|-1.227485270|
|907|15.430951190|14.356691354|-1.074259836|


## ROM window 때문에 후반 개선과 frame 결과가 갈린 이유

window 조건은 period357368,330088≤phase<354640,전역cycle%12==3이며 core 우선권도 그대로다.

|제한907 관측|305 절대ms|307 절대ms|해석|
|---|---:|---:|---|
|첫 BG plan|272.352573|271.124269|1.228304ms 먼저 공급|
|첫 miss 승인|274.905042|274.905042|같은 허용slot|
|첫 BG tile|274.905315|274.905315|cycle6047986 동일|
|최종 완료|281.339760|280.265546|절대 완료1.074214ms 단축|
|첫 BG tile 이후 tail|6.434445|5.360231|후반 경로 실제 단축|

앞 프레임의 개선으로907의 시작도 약1.228349ms 앞당겨졌지만 첫 BG ROM 승인은 그대로다. 그 대기 증가가 후반1.074214ms 개선보다 커서907의 source+output 경과시간은0.154135ms 늘었다. **후반 개선을 전체 frame 개선으로 주장하지 않는다.** ROM 위상을 유리하게 고정하거나 window를 완화한 재실행을 선택하지 않았다. 이3프레임 결과만으로 장기 정상상태 frame cadence를 증명할 수도 없다.

최소0.950258ms의 추가 net 개선이 필요하고0.25ms 여유를 포함하면1.200258ms가 필요하다. BG 이전 window를 잡으려면 큰 선행량이 필요하다는306 결론도 유지한다. 다음 구조 판단은 window 대기 중 가능한 메타데이터 준비·전송과 staging 소유권, 일반DMA의 의존관계를 함께 검토해야 한다. 실제 PPU DMA의 VBlank 제약을 지우거나 OAM/CGRAM을 임의로 앞당기지 않는다. 단순히 manifest를 더 앞당기거나 ROM 대기를 회계에서 빼는 방식으로 해결하지 않는다.

## 전체 Quartus Lite 비용

|항목|305|307|차이|
|---|---:|---:|---:|
|LE|22452|22402|−50|
|comb|17617|17583|−34|
|FF|8997|8965|−32|
|RAM bits|307808|307808|0|
|comb 부족|2209|2175|−34|

own 비용은 host2087→2093(+6),validator1250→1251(+1),queue129→118(−11),plan577→506(−71),SPI655→713(+58),glue48→49(+1). 경계4746→4730(−16),밖12871→12853(−18),whole 순절감34다. inclusive parent/child 중복 합산이나 FF감소를 그대로LE 절감으로 세지 않는다.

새 경계 hard cap은15408−12853=2555,128정책 여유 포함 기능2427이다. 현재4730에서 최소2175comb,여유 포함2303comb를 더 줄여야 한다.306 기능2409 예산을 달성했다고 주장하지 않는다. whole LE/comb가 여전히 과다하므로 FIT/STA 반복을 하지 않았다. board03이 최종 동일 HDL 기준 Lite MAP이며 undriven0이다.

## 검증·실패 보존

- test01/window03: 정상·제한3씩6개 공동 실행 PASS. 두 ELF의 PT_LOAD bytes와 functional RTL hashes 일치, 원본 E1 의미 바이트/E9 순서 동일,metadata8570B·receipt754B·CRC64B/4credit/bank0→1→0/최종ACK 유지. isolated01은305 RTL의별도3프레임으로합계9live다.
- guards05: retained44+compressed5=49개 PASS. 최종 fixture link 폭 일치; 기존 IRQ 미연결3경고는 실제 IRQ를검사하는live/ARM 경계와구분한다. 새codec/overflow/truncatedliteral/exactlength/STOPzero-run 포함.
- spi02: 실제SPI pins를쓴13개 boundary 검사 PASS. E1/E9 CRC domain,CRC8·CRC16손상,잘린전송,잘못된plan count,closed bank,4credit/5번째거부,STOP을확인한다.
- 새ELF native71/1039commands/73260B·fixture reads0,STOP35/IRQ재개11,credit11/supply20/actualwait7/H2 9/IRQ8·33exceptions PASS. native71은dispatch를intercept한생산자검사이며liveACK 검사는아니다.
- codec01: 실제ARM serializer71원본+5합성=76개 PASS. raw fallback·128/129run 경계 포함. SPI는intercept하므로시간·IRQ측정으로세지않는다.
- regenerate01: 현행변환기로생성한84개HDL이board03실제입력과동일하다. final SHA·원본로그·검증범위는analysis/ingress307-verification.json에고정한다.

- board01: based hex literal 바로 뒤 ternary 구문 오류. 공백 수정 후 board02 MAP 성공. window02에서 Questa가 SPI 신호의 선언 전 참조를 거부하여 선언 위치를 옮겼다. board03은 같은 기능·최종HDL로 비용을 확정했고 board02와 수치가 같다.
- window01: 독립 C observer의 misleading-indentation을 `-Werror`가 거부했다. braces로 수정했다. window03은 실제 ARM·RTL·독립 consumer까지 통과했다.
- spi01: fixture가 NES end_valid level을 여러 host cycle의 end_sealed로 전달해 자체 오류를 냈다. 실제 경로처럼 host edge pulse로 바꾼 spi02가13검사를 통과했다. 제품 RTL 조건은 완화하지 않았다.
- guards01: 기존 guard 경계에 plan_batch 파일이 없어 runner 준비 실패. 선택적 파일 처리를 추가했다. guards02/03/04는 legacy fixture의106→107bit 변환이 새110bit link를 덮어써 timeout했다. 최종 변환과 컴파일 전 폭 assertion을 고쳤다. 이는 기능 검사를 삭제한 수정이 아니다. 이전 실패 원본 로그를 보존한다.

실행 범위는 source replay + 실제 M4 instructions(CPI1/84MHz,IRQ24cycle 할당), 실제 shared SPI·GPIO IRQ·tile ROM arbiter, ordinary65816 trace와 map/tile/display bus 모델이다. full ARM RUN·full live65816·전체71/heavy7 live 일정·FIT/STA·실물60fps는 여전히 미검증이다. standalone ARM76/71이나 guard fixture를 전체 frame 실행으로 합산하지 않는다.
