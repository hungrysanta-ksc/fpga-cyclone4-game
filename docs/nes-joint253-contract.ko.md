# NES253: 64B CRC RAM과 source·전송·검증 경계 실측

NES253은 실제 frame201 query→4398B 투영→N5 source→SPI 핀과, 기록된 C 출력 소비 바이트→64B CRC RAM→H2 인증서를 검증했다. 71프레임·14오류 검사 PASS. 동일 독립 경계 MAP은 기존240 2646LE/2336comb/989FF/57344bits에서 새 검증을 포함한253 3404LE/3078comb/1100FF/49152bits로 변했다(LE +758). Warm 출력 검증 1949..2081cycles, 해시 상태 170..170cycles. 조건부500setup 최대15.993545ms/잔여0.673121ms. RAM 이득은 확인했으나 논리 증가로 이 구성은 회로 여유 확보 후보로 채택하지 않는다. 전체 회로·ARM·SNES 여유는 미입증이며 P2 미선정.

## 실제 구현 경계

- 기존240 source의 literal/gap/raster 제어를249 fixed-block source로 교체하고, 실제 frame201 query를4398B로 투영하는 RTL을 연결했다. query 상태기계는 별도로 남아 있다.
- source와 receipt의 상태 레지스터를 하나로 합쳤다. 입력 COMMITTED 뒤에만 출력 검증이 공유 RAM을 소유하며, final display ACK 뒤에 다음 source가 시작한다.
- source stream CRC16, SPI block CRC16, 출력 해시/H2 CRC16은 하나의 조합 계산 경로를 사용한다. SPI는 바이트를 받은 다음 클록에 block CRC를 계산한다. source stream과 출력 CRC의 누산 레지스터도 단계별로 재사용한다. 동시에 살아 있는 SPI block 누산기는 별도로 유지한다.
- SPI host 클록·두 immutable 버퍼·mailbox·SS/token/CRC8 제어는 유지한다. SPI 두 버퍼와 부분 레코드가 모두 비어야 입력 ACK를 커밋한다. 입력 커밋은 실제 최종 표시 ACK가 아니다.
- 16B raw-tail granule을 끝까지 소비해야 해시 두 바이트와 receipt/validity가 갱신된다. 마지막 granule은9B다. tail 범위를 일반 range 명령으로 표시하는 경로는 차단했다.
- H2의 epoch32/serial32/generation16/bank/display-base32/길이/mask/raw/content CRC/certificate CRC를 실제 RTL에서 대조한다. STOP·소유권/세대 상실은 봉인을 즉시 가리고, 오류 이후 RAM 쓰기는 중단한다.

**연결되지 않은 부분:** ARM의 새 N5 복원→계획→H2 생성→출력 전송과 SNES의 실제 소비/최종 ACK는 아직 구현 경계 밖이다. 입력은 실제 collector/SPI RTL이며 출력은 이전 실제 C가 만든 바이트와 완료 이벤트의 재생이다. 새 출력 packet parser, FIFO 소비 어댑터, CDC STA, fullRUN, 새 SNES 실행을 검증했다고 주장하지 않는다. CRC16은 오류 검출이며 인증이나 충돌 없는 증명이 아니다.
H2의 display-base는 입력 시작 때 받은 계획 문맥에 고정하여 비교하고 current serial 미만인지 검사한다. 실제 SNES 은행별 마지막 표시 serial과 연결하는 것은 소비/retire 어댑터의 남은 계약이다. fixture의 serial-2 값을 검증했다고 실제 최종 표시 이력을 검증한 것으로 해석하지 않는다.

## 공유 RAM

| 구간 | 용도 | 수명 |
|---|---|---|
|0..331|양 bank validity 332B|프레임 간 영속|
|332..395|16개 CRC16 ×2 bank =64B|프레임 간 영속|
|396..561|received166B|출력 단계|
|562..817|map receipt256B|출력 단계|
|512..1023|source scratch512B|입력 단계|

출력818B와 source scratch의 겹치는 부분은 하나의 상태기계로 배타 사용한다. 냉간 초기화는818B, 매 출력 초기화는422B다. 해시의 유효성은 기존 raw-tail validity에 묶이며 raw=0 경로는 양 bank의 raw validity를 무효화한다. 이번71개 실제 입력은 raw=2이므로 raw=0 전환 경로의 추가 통합 실행은 미완료다. 이전250의 전환 검사는 보존한다.

## 같은 독립 경계의 MAP

| 경계 | LE | comb | FF | RAM bits |
|---|---:|---:|---:|---:|
|기존240 query/source/SPI|2646|2336|989|57344|
|253 query/projector/source/SPI/receipt/H2|3404|3078|1100|49152|
|차이|+758|+742|+111|-8192|

두 번 모두 EP4CE15F17C8/Quartus25.1 같은 설정의 standalone MAP이다. 새 기능까지 포함한 교체 총비용 비교이며 CRC 공유만의 절약량을 분리한 실험이 아니다. 기존 whole240의2092comb/974FF와 독립 MAP 수치는 최적화 경계가 다르다. 이 차이를 full FIT의490LE/40LAB 부족에서 빼거나 LAB 여유로 바꿀 수 없다. 새 FIT/배치/STA는 실행하지 않았다.

| 같은 계층의 구성 | 기존 comb/FF | 새 comb/FF |
|---|---:|---:|
|source → source+receipt+H2 core|1505/409|2200/494|
|query → query+projector|292/150|348/163|
|SPI 전체(mailbox 포함)|493/430|469/439|
|top 자체|46/0|61/4|

부모의 전체 값과 자식 값을 중복 합산하지 않았다. SPI는24comb 줄었지만9FF가 늘었고, 새 검증을 포함한 core는695comb 늘었다. core 증가를 순수 공유 제어 overhead로 단정할 수는 없다. Quartus FSM 표에는 새 reader만 있고 통합 core의 state는 추출되어 있지 않다. RTL의 단일 상태 레지스터가 효율적인 합성 FSM이 됐다는 뜻은 아니다. state의 대소 비교를 포함한 단계 판별 표현은 점검 대상이지만, 별도 검증 없이 이를 전체 증가의 원인이나 회수 가능한 비용으로 계산하지 않았다.

## 실행 시간

| Warm69 구간 | 실제 RTL 사이클 범위 | 22MHz 환산 |
|---|---:|---:|
|query/source/SPI/input ACK 전체|75214..138081|3.418818..6.276409ms|
|그중 source 준비|11836..11854|0.538000..0.538818ms|
|출력 receipt/해시/H2 재생 전체|1949..2081|0.088591..0.094591ms|
|해시/인증서 처리 상태|170..170|0.007727..0.007727ms|

기존240보다 입력 전체가 빨라진 warm 프레임은27개, 느려진 것은42개다. 준비 시간 감소만으로 전송량·SPI 대기까지 줄었다고 볼 수 없다. SPI2.625MHz와 명령 간 fixture 지연을 포함한 실행 사이클이며 실제 MCU 서비스 시간이나 전체60fps 측정은 아니다.
평균 입력 시간 변화는+0.156522ms다. 입력 계측은 frame201 capture가 준비된 뒤 시작한다. NES 프레임 실행/캡처 시간과 실제 display lease 아래의 중첩은 이번 시간 실험에 포함하지 않았다.

## 조건부 전체 일정 재계산

252의 source wire+source prepare 두 항을 함께 제거하고 실제 query/source/SPI/input-ACK 시간을 넣었다. 기존 receipt+shadow 할당도 실제 출력 검증 시간으로 교체했다. 입력 wire와 실측 전체를 동시에 더하지 않았다. ARM32000cycles, 추가32B, 출력 parser8cycles/byte, SNES setup 등 나머지 배정은 유지했다. SNES validate181 약0.652ms 제거는 여전히 새 소비 경계 연결을 전제로 한다.

| setup | 남은 SNES 검사 정책 | 최대 ms | 잔여 ms | 초과 프레임 |
|---:|---|---:|---:|---|
|500|command_tail|15.993545|0.673121|없음|
|500|only_bitmap_removed|16.374413|0.292253|없음|
|1000|command_tail|16.854921|-0.188255|970|
|1000|only_bitmap_removed|17.235789|-0.569122|954,962,970|

잔여는 미측정 ARM·출력 소비 어댑터·SNES 일반 DMA/dispatch·poll·VBlank가 함께 써야 한다. 이 표는 구현된 새 전체 경로나60fps 보장이 아니다.

## 재현과 보존

- 선택: private `probes/nes-joint253/test07`, 부분 갱신 `test08`, `map02`, `reference01`, `analysis01`. test와MAP의 RTL 해시를 일치시켰다. test08은 실제 C 인증서를 다시 생성하여 양 bank에서 각각 granule2/7/12/15를 갱신했다. 마지막9B granule도 포함한다.
- test01 선언 순서 컴파일 실패, test02 정상2프레임 뒤 패딩 포함 비교 harness 실패, test03 정상3프레임 뒤 guard 라이브러리 경로 실패, test04 3프레임/10guards 통과, test05 중간 RTL71프레임/11guards 통과, test06 lease 신호 선언 순서 실패를 모두 보존한다.
- map01은 상대 증거 경로 검사에서 Quartus 실행 전에 종료했다. 절대 경로로 고친 map02에서 후보의 실제 MAP을 한 번 실행했다. reference01은 별도의 기존240 경계 MAP이다.
- 최종14guard: 내용 CRC/serial/cert CRC 변조, 해시 갱신 누락, 중복 granule, 부분 소비 STOP, 인증서 없는 finish, 조기 display ACK, 잘못된 query 비트, 조기 input ACK, 잘못된 bank, 봉인 뒤 STOP/lease/generation 상실.
- 원본 ROM/PPU fixture/RTL materialization/도구 로그는 private evidence에 보존하며 공개 저장소에는 생성기·집계·계획만 추가한다. production227, unplaced240, rejected241/246/2472, GBC164 및 save SRAM은 변경하지 않았다.

실행 도구: `tools/probe_nes_joint253.py`, `tools/map_nes_boundary253.py`, `tools/analyze_nes_joint253.py`. Questa는 기존 승인된 FLOAT wrapper를 사용하고 ASCII 임시 디렉터리에서 실행한다. MAP은 성공한 최종 test의 해시를 요구한다.

## 판단과 다음 단계

실측 경계의 query/projector와 source 입력 커서·행 제어 중 중복을 실제로 제거하고, 출력 인증서 문맥의 단계별 RAM 수명과 소비 어댑터 비용을 함께 비교한다. source/receipt 한 FSM 및 CRC 공유만으로 전체490LE/40LAB 부족이 해소됐다고 보지 않는다. 실제 ARM N5 복원·계획·H2 생성·출력 소비/최종 ACK 연결과 fullRUN/IRQ·SNES 잔존 DMA·poll/VBlank 비용이 필요하다. 독립 CRC/ROM/seed 미세조정이나 근거 없는 fullFIT 반복은 하지 않는다.

[현재 계획](nes-joint253-plan.json) · [실측 집계](../analysis/joint253-verification.json) · [프레임별 시간](../analysis/joint253-frames.csv) · [조건부 일정](../analysis/joint253-schedules.csv)
