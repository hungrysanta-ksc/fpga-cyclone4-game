# NES334 ARM 계산 단축과 공동 실행 상태 교체

NES333 예산을 기준으로 ARM의 CRC·ordinary 압축 구간 탐색과 host/NES 실행 상태를 실제 변경했다. **공동 RTL 후보는 whole Quartus Lite에서 조합 논리가 38개 늘어 채택하지 않는다.** 332 RTL에 ARM 변경만 연결한 대조군을 별도로 실행해 시간 이득을 분리했다. 상태·FF 감소와 FSM 추출 성공을 면적 절감으로 간주하지 않는다.

재현 도구는 `tools/probe_nes_execute334.py`다. 유지할 ARM-only 조합은 `NES334_ARM_ONLY=1`, `NES332_ARM_ONLY=0`, `NES331_ARM_ONLY=0`, `NES330_MAP=1`로 지정한다. `NES334_ARM_ONLY=0`은 제외한 공동 RTL의 비교 재현용이다. 시뮬레이션은 승인된 Starter FLOAT wrapper, 합성은 Quartus Lite를 사용한다. 분석은 `tools/analyze_nes_execute334.py`가 archived evidence를 hash로 다시 검증한다.

## 실행 시간과 ARM-only 분리 결과

모든 값은 source 입력부터 최종 완료까지이며 새 ARM의 응답 증가 비용도 포함한다. 아래 시간은 실제 M4 명령을 사용한 CPI1/84MHz 일정 모델이다.

|일정/프레임|332 ms|334 ARM+332 RTL ms|변화 ms|334 공동 RTL ms|
|---|---:|---:|---:|---:|
|동일 시작·위상/905|101.874232040|98.618589290|-3.255642750|98.618543836|
|동일 시작·위상/906|121.387588786|117.968357090|-3.419231696|117.968311636|
|동일 시작·위상/907|25.511557494|25.059517464|-0.452040030|25.059472010|
|제한 연속/905|102.501724510|99.246081760|-3.255642750|99.246036306|
|제한 연속/906|116.876733826|116.712326708|-0.164407118|116.712326708|
|제한 연속/907|17.727787264|20.696615274|+2.968828010|20.696615274|
|정상 연속/905|78.328787316|74.841329166|-3.487458150|74.841283712|
|정상 연속/906|54.671662114|51.110795754|-3.560866360|51.110704846|
|정상 연속/907|13.967514206|13.435202412|-0.532311794|13.435156958|

ARM-only 제한 warm은 시작이-3.420050000ms 이동하고, 절대 완료는-0.451222000ms 이동했다. 첫 ROM 수락의 변화는0.000000000ms, 수락 뒤 처리 변화는-0.451222000ms다. 프레임 소요 시간 증가와 절대 완료 단축을 모두 보고한다. 고정 시작 warm의 순이득0.452040030ms를 연속17.727787264ms에서 단순 차감하여 실제 달성치로 부르지 않는다. 제한 연속의 남은 시간은4.029948607ms, 동일 고정 위상에서는8.392850797ms로 ROM 일정 목표는 미해결이다.

|ARM-only 제한 warm의 서로 겹치지 않는 구간|ms|333 상한 ms|
|---|---:|---:|
|ROM_to_last_tile|1.370023000|0.900|
|tile_to_first_map|0.531609000|0.400|
|map_span|0.277720000|0.280|
|last_map_to_last_ordinary|1.328463000|1.300|
|final_tail|0.334298000|0.300|

수락 후 합계는3.842113000ms이며3.180ms 예산까지0.662113000ms가 더 필요하다. 이전 ROM 허용 구간과 source 시작 관계도 분석 JSON에 기록한다. 이것만으로 전체60fps가 성립하지 않는다.

제한 연속에서 앞선 ROM 허용 구간은 source 시작 후1.726570190ms에 닫혔다. source 입력만2.666695272ms이므로 입력 완료보다0.940125082ms 이르다. input-COMMITTED 경계를 유지하는 한 같은 프레임 ARM 준비만 무료로 만들어도 그 구간을 잡지 못한다. 허용 구간을 넓히거나 미확정 이전 프레임 데이터를 읽는 가정은 넣지 않는다.

ARM text30054B(+60),BSS47404B(변화0),관측 stack1288B다. warm H2 호출 경계는8570명령, 첫 OAM 전송 전 묶음은19695명령이다. 개별 함수만의 비용이 아니므로 전체 시간에 다시 더하지 않는다. cold/warm SPI 변화는 각 실행 행에 기록했고, E1 payload·ordered DMA·E9 내용은 기준과 동일하다.

공동 RTL16건과 ARM-only6건의 오류 주입, 각 aperture와raw0 최종 검사7건을 새 ELF/RTL에 결합했다. ARM-only RTL은332와 hash가 같으므로 새 ARM 일정과 관련된 ingress STOP·조기 최종 ACK·expected 변조·ROM STOP/drain·조기 소비·실제 소비 CRC 변조6건을 선택했다. 바뀌지 않은 source/plan 상태 및 경계 검사의 모든 조합을 반복한 것은 아니다. ARM71프레임 생산자와71프레임 강제 중단·재개,CRC5120/압축 탐색1562,응답205,발행8건도 통과했다. 원시 출력과 최종 hash는 `analysis/execute334-verification.json` 및 `probes/nes-execute334`에 보존한다.

## 실제 구현한 범위

ARM `crc16`은 바이트마다 8회 수행하던 bit loop를 16항목 nibble table의 두 단계로 대체한다. table은 읽기 전용32B이며 추가 BSS/동적 payload buffer는 없다. `span_piece`는 각 후보 offset마다 period-two 반복을 다시 탐색하던 경로를 한 번의 연속 탐색으로 바꾼다. 처음부터 이어지는 긴 반복의 길이와 이후 최초64B 반복 시작점,240B 분할 경계는 유지한다. 실제 Cortex-M4 ELF의 함수를 독립 oracle과 비교했다.

333에서 제안한 H2 재검사의 background slicing/cache는 이번에 넣지 않았다. material 버전·완료 표식을 새로 추가하기 전에 동일 결과를 내는 계산량을 줄이는 안을 먼저 분리했다. H2 의미·CRC 검사와 early certificate 비교는 마지막 호출에서 전부 다시 수행한다. 따라서 H2 검사를 생략하거나 cached 성공을 재사용하는 변경은 없다. ordinary 전체 분할 목록도 저장하지 않는다. 이 변경은 준비 작업을10µs 이하 slice로 나눴다는 증거가 아니다.

333의 추가 상태≤32B·새 payload buffer0B 예산은 지켰지만, 추가 응답0회 예산은 지키지 못했다. 계산이 빨라지면서 진행 응답을 더 읽는 비용이 생겼다. 변경된 응답 횟수와 wire bytes를 전부 포함한 고정·정상 일정의 순이득을 근거로 ARM 계산 단축만 후속 비교 후보로 남긴다. 이를333의 전체 합격 예산 달성으로 표시하지 않는다.

host는 ordinary payload와 manifest의 queue READ/CAPTURE를 공유하고, receipt 요청·완료 사이 SEND/CONSUME 상태를 실제 삭제했다. staging read count·순서·token 검사 뒤 validator의 완료를 받아 기존 소비 event를 발행한다. **descriptor destination 주소 decode와 validator receipt RAM RMW 실행은 남아 있다.** 333의 host+validator 전체 공동 실행기 교체를 완료한 것으로 보고하지 않는다.

NES clock에서는 source FSM의 상태 register가 입력 ACK 이후 plan 실행 상태도 소유한다. plan WAIT/READ/CAPTURE/CHECK/READY/RUN/ENDING 상태 register와 transport의 record-open/flush 중복 저장을 제거했다. 대신 output phase 구분과 source/plan 상태 decode를 넣었다. query 선행 읽기, source CRC, immutable bank publish/POP/ACK CDC, plan field decode, source·plan payload RAM과 tile ping-pong은 유지한다. host와 NES clock을 합치지 않는다. plan 단계에서 source RAM write/record/byte 출력이 없고 transport가 비었음을 실제 실행 모니터로 확인한다.

## whole Quartus Lite 결과

|비교|LE|comb|FF|RAM bits|comb 부족|
|---|---:|---:|---:|---:|---:|
|332 기준/ARM-only|22539|17649|9097|307808|2241|
|334 공동 RTL|22575|17687|9085|307808|2279|
|변화|+36|+38|-12|0|+38|

|중복 없는 영역 합계|332 comb|334 comb|변화|
|---|---:|---:|---:|
|host+validator|3401|3362|-39|
|queue+SPI|851|852|+1|
|source|1771|1808|+37|
|plan|460|486|+26|
|영역 밖|11166|11179|+13|
|whole|17649|17687|+38|

host own은2348→2312(-36), encoder own은1352→1394(+42), source transport own은395→390(-5), plan batch own은348→373(+25)다. 공통 core·host·validator FSM은 정상 추출됐다. plan의 별도 상태 FF는 사라졌지만 상태 재해석·진행 선택의 조합 논리가 증가했다. 바뀌지 않은 validator와 주변 회로의 mapping 변동은 명시적으로 삭제한 로직의 이득과 구분한다. **이번 구조를 FSM/seed/FIT 조정으로 반복 합성하지 않는다.** 333의2373comb 순감소 예산을 충족하지 못했다.

## 검증 경계와 실패 기록

실제 ARM ELF·SPI·IRQ·2슬롯·ROM 경쟁 일정과 기존325의536B 65816 bus trace를 연결한다. 새65816 실행이나 실물 계측이 아니다. ARM 시간은 실행된 M4 명령을84MHz/CPI1로 환산한 일정이며 실제 MCU WCET가 아니다. 고정 시작·동일 ROM cycle과 연속 제한/정상 일정을 분리한다. 연속 실행에서 cold 개선으로 warm 시작 위상이 이동하면 ROM 대기 증가와 실제 처리 이득을 따로 기록한다. ROM 허용 구간은 그대로 유지한다.

새 모니터는 tile 마지막 생산 바이트, staging-ready, DMA-ready, ARM wire 시작을 기록한다. DMA-ready를 실제 DMA 시작으로 부르지 않는다. payload read 수·연속 주소도 실제 parser read마다 검사한다. 원래 `MREAD313` 상태 번호에 의존한 old-body-reread assertion은 일반 PREAD와 상태를 합치자 잘못 발동했다. `window01` 실패를 보존하고, 실제 read 수·주소 검사로 바꾼 `window02`부터 비교한다. DUT를 통과시키기 위해 검사를 삭제하지 않았다.

`board01`은 board wrapper의 module 이름을 generator가 찾지 못한 생성 실패로 Quartus 실행 전 종료됐다. 이름 처리 수정 뒤 `board02` 한 번의 Lite MAP을 기록했다. 두 실패는 라이선스 오류가 아니다. production227/GBC164/saveSRAM은 변경하지 않았다. FIT/STA/physical sustained60fps와 전체71프레임 fullRUN은 미검증이다.

`guards01`은1..10번을 통과한 뒤11번 expected 저장 중 STOP에서 새 empty 모니터가 실패했다. transport의 정의는 `source_empty=source_live&&!busy&&!record_open319&&!used&&!crc_pending`이므로 STOP으로 source_live가 내려가면 empty도0이 된다. 이 정상 취소 전파 구간에 output phase의 정상 실행 불변식을 적용한 문제다. `guards02`는 동일 DUT에서 source_live일 때 empty를 검사하도록 적용 구간만 바로잡아11..16번을 수행한다. plan 단계의 source RAM write/record/byte 금지 및 독립된 취소 후 RAM freeze·완료 비노출·ROM drain 검사는 그대로다. 먼저 통과한1..10의 원시 로그와 실패11도 모두 hash로 보존한다.

## 후속 교체 조건

332 RTL을 유지한다. 다음 면적 후보는 상태 register 재사용이 아니라 **실제 descriptor 목적지 주소·receipt RAM 진행의 중복 datapath와 plan field 해석을 삭제하는 경계**가 필요하다. 독립 expected와 실제 DMA/CRC 증거를 합치거나 queue 저장 credit을 소비 완료로 취급하지 않는다. ARM으로 옮길 때도 추가 직렬화·SPI bytes·cold 분할·IRQ·staging 비용을 먼저 계산한다. source/plan만의 교체로2241comb 부족을 해결할 수 없다는333의 경계는 유효하다.

구체적인 잔존 경로는 host의 `decoded_first305/decoded_limit305`와 active record의 receipt 범위, validator의 `range_end283/domain_end283` 및 `V_RREAD` 이후 RAM 순회, SNES 실제 읽기의 `tap_address278/tap_state278`다. 다음 설계에서는 실제 읽기의 coverage-unit 완료 이벤트가 CRC·receipt RAM 작업의 진행을 직접 소유할 수 있는지 비교한다. 범위 admission 검사, 마지막 실제 byte/token 증거와 독립 expected scan은 유지해야 한다. SNES read 간격에 RAM RMW가 들어가는지, tile/map/ordinary의 granule 경계와 reused bank를 정확히 표현하는지, STOP 직전 pending write가 차단되는지를 먼저 예산화한다. 현재 tap은 일부 ordinary CRC만 담당하므로 이를 모든 receipt의 증거로 바로 간주할 수 없다. 이 대안은 아직 구현·합성하지 않았으며1301comb 절감 같은 수치를 배정하지 않는다.

시간은 실제 공급이 막힌 구간을 대상으로 한다. H2·ordinary 계산 단축만으로 ROM 허용 구간을 앞당기거나 VBlank 제약을 없앨 수 없다. 독립 검사·STOP 및 지연 ROM drain·정확한 최종 ACK·VBlank·tile 선행 생산·metadata 선행 발행을 유지한다. post-ROM3.180ms와 whole15276comb은 계속 합격 요구조건이며 현재 달성치가 아니다.
