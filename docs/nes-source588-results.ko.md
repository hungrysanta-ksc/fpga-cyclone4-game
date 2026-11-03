# 588: 단일 입력 블록의 교체 범위·포트·예산

## 결과와 범위

MMC577의 D0/D1/D2/D3와 출력 경로를 유지하는 입력 교체 범위를 구체화했다. **53개 입력에서 source의 in-place map/row RAM 참조가 586과 같은 block·packet을 생산했고 독립 복원도 일치했다.** 기존 codec을 변형한 실험이 아니다. 선택 증거는 `analysis03`, [검증 JSON](../analysis/source588-verification.json), [재현 도구](../tools/analyze_nes_source588.py)다.

회로·Flash의 **교체 후 상한**과 RAM 배치를 정했지만 새 RTL/ARM의 비용을 측정한 것은 아니다. R3·실기 후보는 미선정이며 제품은 MMC577이다. 584/586의 입력4packet 모델을 사용하지 않는다. 참조의 source RAM 포트 접근과 single-block stall 검사는 FPGA 실행·STA를 대신하지 않는다.

## 유지·삭제·추가 경계

| 경계 | 유지 | 실제 교체 대상 | 새로 과금할 것 |
|---|---|---|---|
| NES `export203` | lease/query hit·generation·timeout·PREPARE·취소 drain | old record tag/index/header 조립, map/raw/raster record packing, old records/bytes control 표현 | section 직접 생산, base/scratch RAM 진행, canonical CRC, epoch/serial 및 취소 무효화 |
| `native_records` mailbox | common reset·양측 clock 정지·held/ack 소유권 | 96bit record 의미를 최대8B byte beat+길이+packet-end로 교체 | sideband 검증·STOP 뒤 stale beat 차단. mailbox 전체220LE를 공짜 삭제하지 않음 |
| host `spi165` |256B sealed buffer, D0 snapshot/CRC8, D1 read/CRC16, read_seen, D2 token/retire, D3 prepared | record width/tag/byte 선택, kind 기반 자동 seal | byte beat 소비, 길이 범위, packet-end에만 seal. 전체SPI frontend 삭제 아님 |
| ARM `native165` | D0/D1/D2 확인 및 D3/PREPARE, 외부 전송 함수, 출력 planner/queue/최종ACK | old packet decode + `logical_record` control/encoded BEGIN | 단일 section 수락·값 의미·required-tag·canonical CRC·META/END/COMMIT의 직접 실행 |

별도 공통 응답·shared259B RX·출력 history는 이번 범위에서 추가하지 않는다. [587 검사 대응표](nes-ownership587-results.ko.md)의 조건을 보존하며 새 parser가 old `logical_record`를 호출하는 구성은 제외한다.

## source RAM과 실제 접근 순서

| 영역 | 주소/크기 | 수명 |
|---|---|---|
| map base |0..2111 /2112B|마지막 source 입력 COMMIT 문맥|
| row base |2112..2335 /224B|동일 문맥|
| 공유 scratch |2336..2559 /224B|현재 map 행66B 또는 nonmap literal 최대224B|
| nonmap lookahead 예약 |14B|최대7B 값2개; 이미 받은 query 재사용|
| 총 예약 |3072B =1024×8 구성3개 가정|used2574B,498B 미배정. 실제 M9K inference 미검증|

map 한 행은 다음 순서를 따른다.

1. query의 새33값을 scratch에66B 저장한다. canonical CRC는 수락한 새 값에 한 번만 누적한다.
2. 이전 base와 shift0/−1/+1을 차례로 비교한다. 가장 짧은 기존586 표현을 고르며 tie 순서도 유지한다.
3. **세 비교가 모두 끝난 뒤에만** scratch를 읽어 선택 literal을 내보내고 base를 제자리 갱신한다. 인접 행으로 이동하지 않는다.
4. packet-end beat가 host에서 저장되면 sealed가 되고, D1을 읽었어도 D2 이전에는 덮어쓰지 않는다. 다음 byte beat는 mailbox에서 대기한다.

row section도32값 scratch→이전 row 비교→emit/base 갱신 순서다. map/row는 같은 base RAM을 직렬로 소유한다. host256B 버퍼는 별도 host clock이며 NES base RAM을 직접 읽지 않는다. nonmap의 반복/raster/literal 선택은 기존582 참조를 사용했다. **nonmap의 실제 RTL scratch 포트와 lookahead 실행은 아직 구현하지 않았다.** Python의 전체 arrays/packet 목록은 비교용 oracle이며 target RAM으로 주장하지 않는다. 참조가 packet 길이를 미리 아는 것을 실제 생산 준비 완료로 세지 않는다.

warm/dense 표본 최대는 map/row RAM byte 접근18006회, canonical CRC4446B, logical query1977개다. 순차 byte read에 issue+capture2cycle, write1cycle, CRC byte1cycle을 배정하면 이 부분의 합은 최대36182cycle이다. 이는 query 응답·nonmap 포트·상태 전이·CDC·sealed 대기·STOP drain을 뺀 **부분 설계 배정**이지 실제 최대 처리시간이 아니다. 전체는 이 배정에 `query 응답 비용 + nonmap 실행 + 제어 + mailbox/host 대기`를 더하고 중복 계산 없이 실제 clock으로 확인해야 한다.

CRC에 source의 재조회 응답을 중복 누적하지 않는다. host packet CRC는 압축 바이트, source canonical CRC는 권위 있는 새 query 값, ARM canonical CRC는 독립 복원 값이다. 기준 RAM이 손상돼도 새 query CRC를 이전 RAM 값으로 대신 만들면 안 된다.

## COMMIT·취소·입력 credit

기존 PREPARE 응답은 ARM이 geometry/raw·CRC 검사를 마쳤다는 뜻이다. 이를 받은 source는 COMMIT을 ordered mailbox에 넣은 뒤 source base를 공개할 수 있다. **ARM 공개는 별개로 COMMIT 검사와 D2 retirement 확인까지 기다린다.** source가 미리 다음 계산을 하더라도 host의 이전 sealed COMMIT packet을 덮어쓰거나 다음 BEGIN을 먼저 소비할 수 없다.

이를 위해 새로운 host→NES 최종-retirement mailbox를 당연히 추가할 필요는 없다. 대신 common STOP/reset으로 양측 tentative/base와 held beat가 함께 무효화되고 이전 epoch의 완료가 재시작 뒤 수락되지 않는다는 연결을 실제로 증명해야 한다. 새 epoch/serial 생산·reset namespace 연결은 미구현 비용이다. 입력 base는 표시 bank 이력이나 최종 표시 ACK를 대체하지 않는다.

참조8조건은 부분 행4위치의 STOP→cold literal 복구, PREPARE/COMMIT 큐잉 부족3조건, source COMMIT 공개 뒤 STOP 및 serial 재사용 상황의 이전 epoch 거절이다. 첫 `analysis01`은 더 강한 source-retirement 조건을 가정한 참조였으며, `analysis02`에서 기존 PREPARE+ordered COMMIT 역할로 좁히고 epoch 재시작 반례를 추가했다. `analysis03`은 동일 결과에 고정 ELF·SOF·6개 FPGA 입력 해시 검사를 추가했다. **새 RTL STOP/CDC 시험은 아니다.**

D0/D1/D2/D3 wire의 하한 계산은 실제577 poll/prepare 순서를 따른다. packet당 D1+ D2+확인D0, 첫D0, PREPARE의D0/D3/D0와 그 뒤COMMIT poll의D0를 포함한다. 다음 block이 확인D0 시점에 이미 sealed라면 positive metadata를 재사용할 수 있지만, 생산이 늦으면 BUSY polling이 추가된다. 이번 숫자에 BUSY를 없앴다는 의미는 없다.

## 전송 비용과 남는 전체 시간

동일 payload를 대상으로2.625MHz SPI와580에 고정한503 driver 평균을 사용했다. query/CRC/ARM 계산·IRQ·ROM·VBlank를 새로 실행하지 않은 **wire+driver 비교**다.

| 입력 표본 | 기존→후보 payload | packet 수 | wire+driver |
|---|---:|---:|---:|
|cold905|3198→2609B|15→14|13.223→11.221ms|
|warm907–957 평균|3212.16→693.98B|15.14→5.16|13.294→3.554ms|
|dense951–955 평균|3406.8→820.8B|16→6.2|14.066→4.156ms|

밀집 구간의 약9.910ms 차이는 새 생산·검사 비용 전의 가능성이다. 줄어든 SPI 호출과 늘어난 source RAM/CRC 작업을 실제 한 일정에 연결하기 전에는 처리시간 이득이라고 보고하지 않는다. model service delay를 ROM 시작 위상으로 부르지 않는다.

기존580 전체 일정에서 입력 `source_to_planner`만 빼고 다른 항을 고정하면 warm은48.352/49.045ms, dense는59.983/59.989ms가 남는다. **재배치 후의 물리 하한이나 미래 FPS 예측은 아니다.** 입력 교체 단독이60Hz 전체 달성 근거가 될 수 없음을 보여주는 비용 분리다. 이후 출력/계획/표시를 구조적으로 줄일 과제는 남는다.

## 교체 상한과 다음 실행 순서

선택576 보드의 기존 FIT에서 서로 겹치지 않는 세 instance를 읽었다. source731LE/240FF, mailbox220LE/206FF, SPI482LE/304FF, 합계1433LE/750FF/1M9K다. 기존 보드148LE 여유를 전부 써도 **같은 영역의 새 합계는1581LE 이하여야 한다.** 유지할 SPI/mailbox 비용까지 포함한 상한이며 순절감이나 새 FIT 결과가 아니다. base/scratch3M9K 가정이면 기존51→54/56으로2개가 남지만 실제 폭·포트·packing에 따라 검증해야 한다.

ARM은 baseline577 packet1434B+logical1112B와 남은84B를 합쳐 직접 실행기의 **산술 상한2630B**다. 유지되는 poll452B/prepare200B·required-tag68B·출력/runtime은 삭제에 세지 않는다. 586 parser1530+row246+value/CRC208=1984B를 단순 참고하면646B가 남지만, 이 함수들의 구성은 직접 실행기와 다르므로 통과 증거가 아니다. 최종 전체 링크212992B 이하, 정적 RAM 및 전체 caller/IRQ stack 확인으로만 판정한다.

다음은 문서만 더 쪼개는 대신 **이 고정 경계의 한 번짜리 R2 실행 가능성 원형**이다. 순서를 지킨다.

1. source의 base/scratch·canonical CRC·최대8B mailbox beat·host seal을 연결해 실제 clock별 포트/중단/재시작을 확인한다. 단일 block과 기존 D0–D3를 유지한다. source/host를 모두 live로 둔 같은 경계의 기준/후보 비용과 추가3M9K 예산을 확인한다. 1581LE는 기존 전체FIT에 대한 영역 상한이며 local MAP의 숫자를 직접 빼서 통과로 부르지 않는다. 예산 초과가 확인되면 ARM 결합 확장을 중단한다. 국소 비용만으로 전체 FIT 통과를 주장하지 않는다.
2. source 경계가 맞으면 ARM 직접 section 실행기로 old packet/logical을 실제 삭제한다. 2630B 산술 예산과 전체212992B 링크·RAM/IRQ를 함께 확인한다. 새 진행 응답이나 출력 history는 추가하지 않는다.
3. 한 쌍이 통과한 뒤에만 실제 생산 대기·ARM·SPI·IRQ·ROM·65816을 같은 두 시작 위상/연속 일정에 연결한다. 종단 이득이 없으면 codec/poll 변형을 반복하지 않는다. 출력 잔여 예산을 포함한 R2 전체 판정 전에는 R3·실기 ZIP을 선택하지 않는다.

현재는 이 상한을 **측정할 대상**을 고정했으며 통과를 미리 승인하지 않았다. 실제 비용이 맞지 않으면 같은 adapter 조합을 더 다듬지 않고 역할/지원 범위를 재선택한다. MMC577·독립 검사·STOP·최종 ACK·VBlank·메뉴·GBC/save와 README 제품 상태는 유지한다.

## 재현

`tools/analyze_nes_source588.py --archive <private nes-body581/evidence01.zip> --arm <MMC577/src> --board <576 board01> --out <private analysis.json>`

53개 geometry/raw는 ZIP에서 직접 읽고581 해시·기존 packet 수/바이트를 확인한다. 새 raw 파일을 공개하지 않는다. 원본 JSON에는 기존 FIT report·ELF·도구·입력 archive 해시와 frame별 숫자를 기록한다. `probes/nes-source588/analysis01.json`, `analysis02.json`과 실행 log를 보존한다. private artifact가 필요한 재현이며 clean-clone 전체 실행 완료는 아니다. 이번에 Quartus/Questa/새 compiler를 실행하지 않았다.
