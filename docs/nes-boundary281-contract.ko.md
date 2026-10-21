# NES281 — host·manifest·receipt·ACK 공동 교체 경계와 예산

2026-10-21. PR130 / `codex/nes-wholepath-boundary-256`. 기준은 NES280
`b2cb792a4de9ac63792a81435ca27afe6c9e8329`다. 이번 단계는 **교체 계약과 예산 확정**이다.
새 Cortex-M4 보조 루틴의 실제 명령 실행과 71프레임 대조를 수행했다. 새 FPGA 실행기,
SNES ABI, RTL 일정, MAP/FIT/STA를 구현·측정한 결과는 아니다.

**다음 구현 범위는 압축된 기존 전송 형식을 유지하는 host 실행기·queue 수명 제어·독립
검증기·plan admission/retire 제어의 공동 교체다.** ARM이 dense manifest와 receipt 힌트를
추가 전송하는 대안은 현재 시간 여유를 소비하므로 우선 구현에서 제외한다. 실제 회로 회수는
아직 0개이며 시간·회로 공동 달성이 입증된 후보는 없다. production227/GBC164/saveSRAM은 유지한다.

## 1. 실제 없앨 제어와 반드시 남길 근거

|영역|교체 대상|남기는 기능·문맥|
|---|---|---|
|host 출력|`event264`, `consumer_word`, `event_return`, OISSUE/OWAIT의 이벤트 변환·복귀, 별도 parser/validator 호출 경로|원본 command 의미·길이·대상 범위 검사, 실제 SNES 읽기 감시와 typed map 소비|
|manifest/receipt|host manifest 단계와 validator 단계의 중복 진행·주소 선택·완료 전달|요구 bitmap과 실제 receipt의 독립 비교, fresh/inherited 구별, 중복·누락·초과 검출, H2/content CRC|
|queue/ACK|queue retirement와 host 명령 완료 사이의 중복 진행·return 제어|4-credit, CRC 통과한 packet만 공개, head 유지, ordered ACK와 token 검증, 마지막 range 뒤에만 batch credit 반환|
|plan|별도 endpoint dispatch와 admission/seal/retire 왕복 제어의 중복|불변 plan bank, CRC seal, tile producer가 사용하는 descriptor, 미완료 bank와 CDC 완료 상태|
|표시|별도 display request/return 호출과 manifest 최종 단계의 중복|H2 bank/generation/serial/epoch 결합, 12B 정확한 순차 읽기, 최종 token·표시 ACK 이후 lease 반환|

단일 host scheduler가 기존 순서대로 원본 command를 해석하고, 실제 byte tap으로 CRC를 만들며,
ordered ACK 뒤에만 receipt를 기록하도록 한다. 압축 manifest는 RAM에 별도 dense 사본을 만들지
않고 기존 RLE를 해석해 실제 coverage와 비교한다. 검사 알고리즘과 관측 근거의 독립성을 유지하는
것이지, 검사 FSM 자체를 반드시 별도로 보존하는 것은 아니다. ARM의 “이 범위를 처리했다”는
힌트를 receipt로 바로 인정하는 방식은 제외한다. CRC는 암호학적 인증이 아니다.

NES278에서 이미 제거한 descriptor/byte RPC와 출력 24/8bit mailbox는 재차 회수하지 않는다.
현재 host와 validator는 같은 clock이다. 둘의 호출 결합을 없애는 데 새로운 CDC 절감은 없다.
84bit input/display admission과 최종 ACK 1bit CDC, SNES read/write strobe 동기화, plan bank
ownership crossing은 유지하거나 동등한 대체 비용을 새 회로에 포함해야 한다.

## 2. 수명·RAM 포트·취소 계약

|단계|소유권/허용 동작|공개·반환 조건|
|---|---|---|
|입력|source/query가 NES A 포트로 source scratch 사용|검사된 input COMMIT; 최종 표시 ACK와 다름|
|출력 admission|host B 포트에 output lease; H2와 현재 serial 결합|이전 source owner 해제·grant 완료 뒤 시작|
|SNES 소비|queue head/명령 문맥 유지; 원본 byte tap의 CRC는 provisional|일반 ordered ACK 또는 typed token/정확한 읽기 완료 후 receipt|
|manifest/seal|같은 host scheduler/포트로 coverage·hash·H2 순차 검사|모든 요구 범위 확인 전 display-ready 금지|
|표시|sealed H2에서 12B view 제공; bank/namespace 고정|실제 12B 순차 읽기와 최종 token ACK 뒤 lease 반환|
|STOP/오류|새 admission·payload/receipt 공개 차단; pending 소유권 폐기|양 bank 재사용 유효성 무효화, token burn/serial 이력 유지; 늦은 ACK로 새 lease 완료 금지|

고정 phase RAM은 1024×8 TDP를 유지한다. valid 0..331, raw hash 332..395,
receipt 396..561, map 562..817, H2 832..863, display offset 864..867을 사용한다.
source scratch 512..1023과 출력 영역의 겹침은 **phase grant로만** 허용한다.
외부 SNES byte read는 막연히 backpressure할 수 없으므로 기존 read tap의 처리 간격/보관 능력을
보존해야 한다. RAM scheduler가 CRC·receipt·seal을 합쳐도 tap 유실 또는 읽기 도중 head 반환을
허용하지 않는다. 추가 skid/port mux가 필요하면 회로·RAM 예산에 포함한다.

plan bank는 tile producer가 읽는 동안 다음 output packet 수신/소비와 수명이 겹칠 수 있다.
plan/output counter와 payload RAM을 단순 alias하지 않는다. 기존 queue 4×256B, plan 2×512B,
tile/map staging 및 live plan 문맥은 제거 가능한 임시 메모리로 계산하지 않는다.
plan의 NES tile-side reader는 유지하고, host admission/retire의 중복을 합친다. 유지하는 reader와
bank CDC도 선택 경계의 새 합계에 포함한다.
ARM dense scratch 256B를 사용해도 FPGA RAM 256B가 자동으로 회수되지는 않는다.
현재 whole 논리 RAM 307,808bits를 넘기지 않는 것을 prototype 목표로 삼되, 실제 block packing과
포트·placement는 후속 whole MAP/FIT에서 확인한다. 프로그램 크기는 임의의 4KiB 목표로 제한하지
않으며 전체 SNES 프로그램을 링크해 ROM shell 변경 비용까지 청구한다.

## 3. 동일 whole 경계에서의 회로 예산

NES280 Quartus **Lite** MAP의 parent 제외 own count를 다시 합산했다.
whole은 22,754LE / 17,815comb / 9,127FF / 307,808bits이다. 장치 comb 15,408 대비 2,407개 초과다.

|교체 범위|기존 comb|남는 외부 comb|새 범위 최대 comb|
|---|---:|---:|---:|
|host 2,488 + queue 129 + validator 1,056|3,673|14,142|1,266|
|위 범위 + plan endpoint/batch/CDC 577|4,250|13,565|1,843|
|선택 범위에 계획상 여유 128개 추가|4,250|13,565|**1,715**|

선택 목표는 whole **15,280comb 이하**, 즉 새 범위 1,715comb 이하이며 기존 범위 대비
2,535개(59.65%)를 줄여야 한다. 128개는 설계용 reserve이고 FIT 여유를 보증하지 않는다.
외부 회로가 Δ 증가하면 새 범위 허용량도 Δ만큼 감소한다. FF/LE/LAB/M9K/Fmax 제약은 별도로 통과해야 한다.

validator 1,056개를 물리적으로 그대로 두면 좁은 범위에서 host+queue에 남는 예산은 210개뿐이다.
이는 불가능성 증명은 아니지만 host만 소폭 수정하는 계획으로는 회로 부족을 닫을 근거가 없다.
plan 577개를 경계에 포함해도 제거하지 않은 bank/CDC 비용은 새 합계에 다시 들어간다.
source 1,347, source transport 428, 공통 SPI 658은 이번 선택 경계 밖에 유지한다.
계층 경계를 넓혔다는 이유만으로 그 회로가 절약된 것으로 계산하지 않는다.

## 4. ARM으로 옮기는 대안의 실제 비용

`nes_boundary281.c`를 GCC -Os/Cortex-M4로 컴파일해 실행했다. 71프레임의 실제 E1 1,231패킷에서
manifest 256B와 receipt span을 만들고, 독립 Python granule oracle 및 기존 expected754B/frame과
비교했다. 모든 map 2,069범위의 coverage도 일치했다. 원래 packet과 세 대안의 E1 CRC를 각각
실제 ARM에서 생성해 Python CRC와 대조했다. 잘못된 길이·범위·manifest version/cursor 등 10입력을
거절했다. 추가 9개 forged-hint 데이터는 독립 근거와 달라야 한다는 예시이며 새 RTL guard 증명이 아니다.

별도 helper 이미지 758text / 0data / 0bss, 관측 stack 24B. caller dense scratch 256B와 span scratch
최대 9B를 별도 청구한다. 이는 통합 firmware의 peak stack/RAM/사이클 측정이 아니다.
기존 source ARM과 output refill/IRQ 비용은 baseline에서 유지했다. 새 helper의 normalization 명령과
기준/대안 wire helper 명령 차이(음수는 0으로 제한)를 추가한 **직렬 비용 민감도**다.
기존 serializer loop가 실제 교체됐거나 중첩 실행됐다고 가정하지 않는다.

954프레임, 84MHz/CPI1, SPI 2.625Mbit/s와 거래당 8µs setup:

|대안|추가 SPI B|추가 ARM 명령|추가 비용|기존 일정에 더한 민감도|
|---|---:|---:|---:|---:|
|압축 wire 유지 기준|0|0|0|16.593392ms|
|dense manifest 256B|144|10,969|0.569440ms|17.162832ms|
|dense + receipt span/count|179|13,723|0.708893ms|17.302285ms|
|위 대안 + packet header 16→12B|103|13,682|0.476786ms|17.070178ms|

dense는 240B+16B의 두 payload packet으로 나눈다. receipt는 명령별 최대 두 개의 first16/count16
span과 count8을 덧붙인다. span은 실제 소비의 증거가 아니라 검증 대상 힌트다.
span trailer를 원래 DMA payload와 분리하는 새로운 consumer ABI도 필요하며 이번에는 구현하지 않았다.
compact header는 generation16과 payload-length16을 빼고 queue length·admitted serial/H2에서
복원하는 **ABI 변경 가정**이다. 독립 lease 결합과 실제 SNES 소비·ARM 통합 비용은 미검증이다.
원래 256B 논리 envelope를 유지하고, packet sequence/CRC를 재작성했다.

세 대안 모두 warm69 중 954에서 고정 일정 민감도가 한도를 넘는다. 71프레임 추가 wire 합계는
각각 12,797 / 14,995 / 9,907B다. cold905/906은 기존 3 manifest packet을 2개로 줄여 일부 이득이
있지만 warm 최악을 해결하지 않는다. 이 결과가 wire 변경의 전면 불가능성을 증명하지는 않는다.
일정을 다시 실행하면 중첩·ROM 위상·poll 횟수가 달라지므로 위 값은 실제 완료시간 예측/상한도 아니다.

## 5. parser·poll·ROM을 포함한 남은 시간 예산

954 기준 source 5.424799ms + output 11.168593ms = 16.593392ms, 여유 **73.275µs**다.
source codec/block CRC 91,786명령과 output ARM/IRQ event 190,251명령, E2 91회·출력 SPI 2,577B를
그대로 청구한다. event에 기록된 명령에는 다음 거래 전 planner/refill 작업도 들어 있어 poll 명령으로
모두 분류하거나 절약할 수 없다. full RUN/NVIC·source live driver·hardware CPI는 아직 미검증이다.

기록된 OSETUP→retire parser 구간 전체는 27.664µs, 그중 manifest/requirements는 23.986µs다.
typed receipt 구간은 별도로 1.752µs다. parser를 **전부 0**으로 놓는 낙관적 고정 차감도
16.565728ms에 그친다. source codec만 CPI2로 늘리면 기준 17.686082ms,
parser 전체 0 가정에서도 **17.658418ms / 0.991752ms 부족**이다.
parser·receipt·poll·ROM 대기 절감은 서로 겹칠 수 있으므로 합산 차감하지 않는다.

E2 9B wire+setup은 35.429µs다. CPI2에서 부족한 1.019416ms는 단순 크기로 29회의 wire+setup에
해당하지만 **29회 제거 가능하다는 뜻은 아니다.** 후속 후보는 같은 E1/E9 full-duplex 응답에 검사된
credit/progress snapshot을 실어 별도 조회를 대체하고, 진전이 없는 동안만 bounded wait를 하는 방식이다.
기존 RX MISO 경로·CRC·latched snapshot·ARM sequence 처리 비용을 모두 청구한다. full queue,
tile 미준비, idle 오류 발견에는 E2/IRQ fallback을 유지한다. 오래된 snapshot은 credit을 과다 허용하면
안 되며, STOP·오류는 진행/timeout으로 결국 발견해야 한다. NES271의 단독 backoff 회귀를 고려해
poll 간격만 조절하는 후보는 반복하지 않는다.

정상954의 ROM 증분은 tile wait 53cycles / slot wait 0 / core priority 9건이다.
제한ROM907은 tile wait 225,581cycles / slot wait 225,567 / priority 14건,
E2 279회 / output ARM/IRQ 236,148명령 / output SPI 3,496B,
기준 **18.590413ms / 1.923747ms 부족**이다. ROM 카운터는 누적값의 프레임 차분으로 계산했다.
제한3프레임 절대 종료 263.993832ms를 함께 유지하며 cold905/906은 warm 예산과 분리한다.
동일 제한 조건에 dense/spans/compact 비용을 고정 추가하면907은 각각
19.558009 / 19.658199 / 19.457961ms다. 새 일정의 결과가 아니다.

계획상 0.5ms 여유를 목표로 하면 정상 CPI1에서도 추가 **0.426725ms** 절감이 필요하다.
source CPI2 기준은 1.519416ms, 제한907 기준은 2.423747ms가 필요하다.
0.5ms도 engineering reserve이며 실제 VBlank/전체 실행 여유의 검증값은 아니다.
타일 plan은 불변 bank seal이 끝나자마자 ROM producer에 공급하고, output credit 대기를 위해
불필요하게 plan 공급을 늦추지 않는 공동 일정만 검토한다. 실제 같은 ROM arbiter/공유 SPI/ARM IRQ와
SNES trace에서 재실행해 절대 시작·종료·poll·slot 위상을 대조해야 한다. ROM 우선순위를 무료로
바꾸거나 main core stall을 새 여유로 간주하지 않는다.

## 6. 다음 구현과 통과 조건

1. 먼저 기존 wire/ARM/SNES ABI로 host+validator+queue의 직접 진행을 구현하고, plan 제어와 통합한다.
   위 표의 기존 제어를 실제 제거한다. 단일 FSM 이름 변경이나 wrapper 통합은 교체 완료가 아니다.
2. 71프레임 원본 metadata/receipt/hash, cold/raw0..2/bank0→1→0, partial read/ACK, stale token,
   credit wrap, pending plan, STOP의 ingress/tap/receipt/seal/display 각 경계와 늦은 completion을 검증한다.
   기존280 STOP/최종ACK PASS를 새 구현의 PASS로 대체하지 않는다.
3. 같은 전체 Lite에서 comb≤15,408은 필수, 계획 목표≤15,280이다. 새 경계 목표≤1,715이며
   RAM/FF/LE/LAB와 clock/포트 비용도 합산한다. 목표 미달이면 이 boundary의 구조적 절감 근거를
   재평가하고 opcode/FF/FIT seed 반복을 하지 않는다.
4. 진행 snapshot/plan 조기 공급은 실제 ARM producer/refill/IRQ와 연결해 정상71/제한3 및 heavy7을
   재실행한다. warm≤16.666667ms, 계획 목표≤16.166667ms; cold 별도. CPI/WCET·fullRUN·active
   VBlank·전체 SNES ROM 링크·FIT/STA·실기 지속60fps는 이 뒤의 gate다. P2는 선택하지 않는다.

재현: `probe_nes_boundary281.py --out <새 ASCII 폴더>` 실행 후
`analyze_nes_boundary281.py --arm <해당 폴더> --out <새 분석 폴더>`.
선택 증거 `probes/nes-boundary281/arm02`, `analysis02`; arm01은 sandbox DLL 시작 실패,
analysis01은 ROM 누적값 표기를 포함한 중간 분석으로 보존했다. analysis02에서 차분 표기로 수정했으며
시간·ARM·회로 숫자는 동일하다. 새 Questa/Quartus 실행이나 라이선스 변경은 없다.
공개 결과: `analysis/boundary281-verification.json`, `analysis/boundary281-costs.csv`.
