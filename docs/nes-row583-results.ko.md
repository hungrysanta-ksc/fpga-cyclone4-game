# 583: 행 좌표 재사용·진행 응답의 비용과 남은 경계

PR151의 R2에서 [582](nes-abi582-results.ko.md)의 큰 입력 변화 원인을 확인하고, 행 복원 코드를 실제 Cortex-M4 명령으로 실행했다. **951·954·957의 대량 변경은 같은33칸 행 안의 ±1칸 이동으로 대부분 표현된다.** 다른 행을 검색하거나 hash만으로 동일하다고 판단할 필요는 없었다. 이는 byte-exact 관계이며 실제 게임의 스크롤 원인 전체를 입증한 것은 아니다.

제품 MMC577과 실기13.95fps는 그대로다. 새 코드가 제품에 연결된 것은 아니며 새 전체 시간·FPS·FIT/STA·전달본은 없다. R2의 전송 가능성은 개선됐지만 **R3 제품 구현 승격은 아직 보류**한다. 핵심 미해결은 실제 조회 대체 횟수, 유지 데이터 검사, 순 Flash/LE와 RAM 포트다.

## 확인한 입력 변화

53개 sealed geometry/raw와 기존 두 위상 로그의 해시를581/580 근거와 대조했다. 아래 전송량은582의 D0/D1/D2/D3 비용식을 그대로 두고 행 표현만 바꾼 값이다. 새 진행 응답의 추가 비용은 뒤에서 따로 계산한다.

| 입력 generation | 같은 위치의 변경 word | 행 이동 뒤 전송 word |582 입력 wire B|583 행 표현 wire B|
|---|---:|---:|---:|---:|
|951|749|23|2427|954|
|952|12|12|897|916|
|953|1|1|882|901|
|954|755|75|2429|1077|
|955|0|0|866|885|
|957|754|31|2413|956|

951/954는29행 중−1칸5행,0칸6행,+1칸18행을 선택했다.957은6/6/17행이다. 작은 변화의952/953/955에서는32단위에서33단위로 바꾼 framing 때문에19B씩 증가한다. 밀집951–955 평균 입력은1500.2→946.6B다. 좋은 화면만 골라 절감량을 합산하지 않았다.

행 형식은 section/codec/start/count의6B header, 선택적 signed shift1B,33bit mask5B,변경 값당2B다. shift는−1/0/+1만 허용하며 행 밖 값은 반드시 literal이다. 새 행은 이전 base의 유효 count 안에 온전히 있어야 한다. literal72B가 더 작으면 literal을 선택한다. 나머지 section과 전체 canonical CRC·META_END/END/COMMIT은582와 같다.

## 실제 ARM 커널

[`nes_row583.c`](../tools/nes_row583.c)를 GNU Arm13.3.Rel1, Cortex-M4/Thumb/`-Os`로 독립 링크하고 Unicorn에서 실행했다. geometry53개·1537행의 결과가 원본과 일치한다. 참조 Python은 raw까지 포함한53개 입력의 canonical 복원을 대조했다. 커널 자체는 map 행만 처리한다.

| 항목 | 결과·범위 |
|---|---|
| 독립 `.text` | **248B**, global/BSS 추가0B |
| compiler/실행 중 최대 stack | **104B**; 전체 RUN/IRQ stack 아님 |
| 한 화면29행 실행 명령 |17400–23670 instructions; cycles/실기시간 아님 |
| 951/954 |23670 instructions; CRC·전체 의미검사·tile 열거 제외 |
| 정상 경계 |첫/마지막 가능 행 ×−1/0/+1,6조건 |
| 오류 경계 |17조건 모두 거절, 대상 map 전체와 양쪽 guard bytes 불변 |

오류 조건에는 header/section/mode/count/주소·mask 상위비트·범위 밖 재사용·잘린 마지막 값·여분 바이트·15bit 값 위반·base 없음·이전 base보다 늘어난 행이 포함된다.33word 임시 행을 완전히 검사한 뒤에만 commit한다. **한 행의 원자성이지 프레임 전체 rollback이 아니다.** 후속 행/CRC 실패나 STOP에서는 바깥 실행기가 전체 잠정 이력을 무효화해야 한다.

처음240B 커널에 이전 base의 유효 count 검사를 추가한 최종 결과가248B다. 기존 Flash 여유84B에 덧붙일 수 없다. **커널만으로도 최소164B의 실제 기존 코드 삭제가 필요**하며 새 block parser/CRC/진행 응답 비용은 그 밖이다. 기존 `logical_record`/`nes_native165_packet` 함수 전체 크기를 무료 삭제로 계산하지 않았다. 현재 확정된 순삭제는0B다.

## 진행 응답: 없앨 호출과 남겨야 할 호출

현재 `nes_sink_window184`의 E0는 accepted/retired와12B ACK를 검사하고, `nes_plan_service200`의 E8은 plan accepted·12B bulk descriptor·END를 검사한다. 단순 busy 조회가 아니다. 다음 공통 응답을 **제안·참조 검사**했으며 제품 RTL에는 아직 연결하지 않았다.

| byte |50B output snapshot|
|---|---|
|0–3|magic/version/flags|
|4–11|epoch32/display serial32|
|12–23|generation16/snapshot sequence16/accepted16/retired16/plan accepted16/reserved16|
|24–35|기존 latest ACK12B|
|36–47|기존 bulk descriptor12B|
|48–49|CRC16|

E1/E9 시작 시 **그 명령 이전의 일관된 상태**를 latch한다.2byte 준비 구간+50B 응답 때문에 최소52B transfer다. 짧은 E1/E9는 padding을 추가하고 outbound CRC/commit은 실제 끝으로 옮겨야 한다. 응답이 같은 transfer의 새 명령까지 수락했다고 가정하지 않는다. 기존 header/packet CRC·token/범위 검사는 유지한다. CDC snapshot을50B에 담을 수 있다는 것과 실제로 일관되게 latch할 수 있다는 것은 다른 검증이다.

Python 참조 검사6정상/20거절 조건에서 epoch/serial/generation·CRC·reserved·sequence·accepted/consumed 분리·16bit wrap·late STOP·bulk 미소비/END를 확인했다. 실패 응답은 진행을 공개하지 않는다. 입력 source identity는 이 **표시 identity**와 섞지 않는다. bulk의 실제 kind/bank/span 검사는 기존 독립 validator의 책임이며 이 참조 코드가 대신하지 않는다. 최종ACK·EA 허용도 기존 완전한 identity 검사 뒤에만 가능하다.

**데이터를 보낼 수 없는 상태에서는 이 응답을 실을 transfer 자체가 없다.** 따라서 별도52B snapshot 읽기와 진행 IRQ 경로가 필요하다. 기존 로그의 예는 다음과 같다.

| 화면/위상 |E0/E8 조회|같은 응답 반복|사이에 E1/E9 없이 바뀐 응답 E0/E8|
|---|---:|---:|---:|
|951/1|111/18|82/13|10/1|
|954/1|84/45|59/34|6/3|
|954/2|84/43|61/33|6/2|

이는 기존 일정의 관측 횟수다. 새 일정의 최소 조회 수가 아니며 반복 응답을 모두 삭제해도 된다는 증거도 아니다. 특히954의 새 진행 중8–9건은 기존 데이터 transfer에 뒤늦게 실어서 해당 기다림을 해결할 수 없다. **세 번만 조회하는 아래 표는 의도적으로 낙관적인 민감도이며 달성한 일정이 아니다.** IRQ가 깨어나는 즉시 새 generation의 응답이 준비된다고도 가정하지 않는다.

## 입력 ACK+FETCH 계약과 padding

D0 확인→D1 수신→D2 credit 반환을 바꿀 새 입력 transaction은 이전 packet ACK와 다음 packet 요청을 묶는다. 아직 source/host 구현이나 그 STOP 시험을 통과한 계약은 아니다.

- request16B: opcode/version2,epoch4,input serial4,previous ACK sequence2,requested sequence2,CRC16.
- response header16B: magic/status2,generation2,epoch4,input serial4,packet sequence2,length2.
- request CRC·입력 identity·sequence가 맞을 때만 이전 packet을 반환한다. ACK는 직전 확인된 head에만 적용하며 같은 요청 재시도는 idempotent해야 한다. response CRC를 확인하기 전 ARM이 다음 ACK를 보내면 안 된다.
- source가 다음 packet을 아직 만들지 못하면 BUSY다. 성공만 세거나 고정2byte가 NES 클록의 생산을 완료시킨다고 주장하지 않는다. BUSY/재시도·IRQ 비용은 다음 실제 경계 시험 대상이다.
- 마지막 packet의 ACK도 별도36B confirm으로 계산한다. COMMIT은 META_END/END 전체 검사 뒤이며, 기존의 **이전 표시 최종ACK·EA 이후 새 COMMIT** 조건을 유지해야 한다. 새 입력 수신 가능과 표시 교체 가능을 합치지 않는다.

두 전송 방식의 비용을 비교했다. opcode/packet 크기를 미세 조정한 것이 아니라 고정 DMA와 길이 확인 후 재시작하는 드라이버 경계를 구분한 것이다.

| 방식 |성공 transfer wire|드라이버 제출 횟수|밀집 입력 평균|
|---|---|---:|---:|
|현 조회를 유지한 행 표현|기존582 비용식|3×packet+confirm|946.6B|
|고정 body 수신|request16+turnaround2+header16+payload256+CRC2|packet+confirm|1846.4B|
|가변 body,2단계 SPI/DMA|첫36B request/header/headerCRC,다음 actual payload+CRC2|**2×packet+confirm**|1092.4B|

가변 방식은 header CRC/길이 확인 후 CS를 유지한 채 두 번째 전송을 시작해야 한다. 그 CPU 계산·CS 점유 공백은 미계측이다. 두 제출에 각각 기존 D1 평균 비용을 부과했으며 한 호출로 무료 처리한 것이 아니다. 최종 confirm36B도 포함했다. 고정 방식의 약900B 증가는 호출 절감을 그대로 바이트 절감으로 계산할 수 없음을 보여준다.

## 동일 작업량의 비용표

map8B stale/70B manifest와 기존 nonmap을 유지한 안을B,582의 nonmap 범위 재사용까지 포함한 안을C로 부른다. C의 생산자 이력·독립 유지 데이터 검사는 여전히 해결되지 않았다. B도 map 이력의 독립 검사·실제65816 비용이 남는다.

|밀집951–955 평균|wire ms 위상1/2|wire+기존 드라이버 평균 ms 위상1/2|
|---|---:|---:|
|B 행 표현만,582 호출 민감도|—|17.427 /17.458|
|C 행 표현만,582 호출 민감도|—|14.379 /14.410|
|B 고정 FETCH+공통 응답,조회3 가정|13.943 /13.953|15.976 /15.986|
|C 고정 FETCH+공통 응답,조회3 가정|11.054 /11.064|12.500 /12.509|
|B 가변2단계+공통 응답,조회3 가정|11.646 /11.655|13.984 /13.994|
|C 가변2단계+공통 응답,조회3 가정|8.756 /8.766|10.507 /10.517|

가변 방식의954 개별 I/O는B14.916/14.965ms,C11.589/11.638ms다.52B 조회 한 번을 더 하면 wire+기존 driver 평균이 약0.207ms 늘어난다. 기존 E0/E8 횟수를 그대로 유지하면 C 가변 방식조차 밀집36.994/36.880ms다. 새 응답으로 **실제 불필요한 호출을 제거할 때만** 이점이 생긴다.

위 숫자는2.625MHz wire와503의 opcode별 평균 부가 비용을 적용한 직렬 I/O 민감도다. 실제 새 SPI 드라이버/IRQ·ARM 계획/전체 CRC·ROM 공급·65816 검사/DMA·VBlank는 포함하지 않았다. 기존 물리 DWT나 중첩된 ROM 대기를 여기에 다시 더해 전체 시간이라고 하지 않는다. 새952/957 표시 간격·마지막ACK 개선은 아직 측정하지 않았다. cold 두 뱅크의 가변 I/O 약33.25ms도 warm와 분리한다.

## 실제 삭제·RAM 포트 경계

|경계|대체할 부분|유지할 부분·비용|
|---|---|---|
|NES source|map의15bit record 포장·동일위치 비교 대신 행 scratch/shift mask 선택|query·ROM 중재·capture lease·record CDC·watchdog 유지. map2112+row224B base에 최소3M9K 필요;현재 여유5중 사용하면2남음,합성 승인 아님|
|source RAM|new row66B와최대encoded row78B를 같은3M9K 남는 공간에 배치|old row의−1/0/+1 비교가 끝나기 전 base overwrite 금지. byte port로3후보를 모두읽으면 최악198old-byte reads/행;새row조회·scratch·후속base쓰기·emit은 추가. 무비용 선행 처리 아님|
|ARM 입력|기존 record decoder/reset 중 map 경로를 block decoder로 교체|map/row 유지와 receiver metadata/required bitmap 수명 분리. canonical CRC는재사용word포함.248B 커널·104B stack와나머지새parser/오류처리필요;순삭제0|
|입력 SPI|D0/D1/D2 분리 상태를 ACK+FETCH로 교체|CRC·sealed packet 소유권·재시도/STOP·마지막confirm 유지. source-ready IRQ/CS 유지·header DMA 비용 미검증|
|출력 SPI/ARM|E0/E8 중복 snapshot·read/CRC 호출을50B 공통응답으로 교체|현재accepted/retired·latestACK·plan/bulk 검사 의미는 유지. 실제기다림/최종ACK용 standalone 읽기와IRQ 필요|
|SNES map/nonmap|582의행/범위표현 후보|actual-consume CRC/coverage·bank 이력·STOP·부분전송복구·VBlank/최종ACK 유지. C의최대8948B producer cache를확보했다고가정하지않음|

source base와 표시 이력의 publication은 다른 문제다. 다음 설계에서는 **성공한 input COMMIT의 source base**와 **최종 display ACK의 bank 이력**을 별도 identity로 표현해야 한다.582에서 source base도 표시ACK/EA에 묶어 둔 보수적 가정을 자동 승계하지 않는다. 그렇다고 새 COMMIT을 이전 표시EA보다 앞당기는 것은 아니다. 기존 입력 수신 overlap·ARM workspace가 이 분리를 지원하는지, STOP 뒤 두 문맥을 모두 무효화하는지 실제 경계 시험이 필요하다.

## 판정과 다음 한 단계

1. **행 주소 재사용의 데이터 효과와 작은 ARM 복원 비용은 확인했다.** 같은행3후보 이상으로 검색/codec을 늘리는 최적화는 보류한다.
2. **고정256B 성공 수신만 가정한 호출 절감은 채택하지 않는다.** padding을 포함한 비용이 크다. 가변2단계는 추가 제출/CS 점유까지 계산할 대상이며 아직 제품 선정이 아니다.
3. 다음 R2 gate는 **실제577 ARM의 입력/출력 문맥을 사용한 제한된 transport 교체 시험**이다.951/954의 source-ready·유한 queue·actual consumed/plan 진행을 연결해 ACK+FETCH와공통응답이 실제로 대체하는D0/D2/E0/E8 횟수,STOP/late completion/새COMMIT 경계를 확인한다. old calls를남기고새응답을추가하는 구현은 실패다. 새이벤트가없는IRQ/조회3회가정으로진행하지않는다.
4. 같은 경계에서 기존decoder/status 함수의 **실제순삭제·전체link Flash/stack/RAM**을 계산한다. map/비map 유지 데이터의 독립 검사와생산자이력이 예산에들어가지않으면C를버리고역할/지원범위를재검토한다. 그전에는 전체FIT/53화면새일정/실기ZIP을반복하지않는다.

현재MMC577·STOP·독립 검사·최종ACK·VBlank·메뉴 복귀·GBC/save는 변경하지 않았다. R2는 진행 중이며R3 미선정이다.

## 재현·실패 보존

```powershell
python tools/check_nes_row583_arm.py --data ../probes/nes-delta231/test07 --cc <arm-none-eabi-gcc.exe> --out <새-폴더>
python tools/check_nes_progress583.py --out <새-json>
python tools/analyze_nes_row583.py --data ../probes/nes-delta231/test07 --capture ../probes/nes-output489/audit01 --traces <원본-Temp> --out <새-폴더>
```

[전체 예산](../analysis/row583-verification.json) · [ARM 실행](../analysis/row583-arm.json) · [응답 참조 검사](../analysis/row583-progress.json)

선택은로컬`probes/nes-row583/arm04`, `analysis04`, `progress02.json`이다. arm01의sandbox DLL623,arm02의보고서UTF-8읽기실패,arm03의이전240B/15조건결과를보존했다. analysis01은raw배열연결누락을검출했고02/03도보존했다.04는base유효count검사까지포함한다. raw/ROM/컴파일산출물은Git에추가하지않으며공개metadata의입력·도구hash로기존근거를연결한다.
