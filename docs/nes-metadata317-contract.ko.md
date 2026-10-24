# NES317 metadata 확정 계측·선행 발행·공동 terminal 실행 검증

NES317 actual M4 metadata+joint terminal measured: restricted907 ARM-only 17.119885ms/joint 17.119885ms;wholeLite 17891comb (+21vs315),deficit2483. Joint not selected; independent checks/STOP/finalACK retained. No physical60fps/FITSTA.

## 실제 ARM 계측

315 ELF의 PT_LOAD와 RTL을 그대로 사용한 observe02에서 next_step286의 최종 성공 반환, prepare289와 tile 공급 함수의 진입/반환을 관측했다. 관측기는 실제 M4 명령 수·RTL checkpoint·pending instruction/CPI1·exception allocation으로 같은 일정의 시각을 계산한다. GPIO/credit/plan 상태를 읽기만 하며 추가 checkpoint나 ARM 명령을 삽입하지 않는다.315 대비 frame time·ARM 명령·SPI byte가 동일함을 분석에서 확인했다. 하드웨어 cycle 실측은 아니다.

제한907의 최종 planner 완료는272.873841ms, 첫 BG tile 수락은274.905315ms로2.031474ms의 간격이 있었다. prepare289는275.834827→275.856863ms에 실행됐고1851명령이었다. 이 준비 비용만 삭제해도0.240ms 전체를 해결할 수는 없다. 그 뒤의 encoding·SPI·응답까지 실제로 겹쳐야 한다.

|907 실행|planner 완료 ms|첫 BG 수락 ms|requirements 전송 완료 ms|ready→BG ms|
|---|---:|---:|---:|---:|
|observe02|272.873841|274.905315|280.041265|2.031474|
|arm01|272.360651|274.905315|272.682210|2.544664|
|window01|272.360651|274.905315|272.682210|2.544664|
|normal01|188.374614|186.949734|192.751471|-1.424880|

## ARM 선행 준비·발행 구현

기존309의40B header/16B copy 준비 단위를 현재312/315 ABI에서 재사용했다. metadata는 source committed·video valid·resident/dirty prepared·generation/serial/target 일치와 정상 lifetime일 때만 발행한다. BG 완료만으로 준비됐다고 간주하지 않는다. work302는 DMA-ready·pending planner·plan 공급·IRQ를 먼저 확인한다. 준비 완료 후 확인된 저장 credit이 남을 때만 op15를 보낸다.

기존 DMA serializer buffer를 덮어쓰지 않도록209B metadata 전송 buffer를 추가했다. 실제 send/CRC/identity/sequence/credit 처리는 공통 send317을 사용하고 별도 버퍼의 직접 SPI 응답도 progress282로 검사한다. requirements 발행 후 일반 DMA를 금지하던 조건을 제거했지만 terminal op3의 순서, 실제 consume와 저장 반환 분리, 독립 coverage·최종ACK는 유지했다. 준비 상태는 reset/abort/new begin에서 폐기된다.

이번 선행 발행 대상은 display/requirements를 담은op15다. map manifest op10/11은 기존 후반 발행을 유지한다. 전체 metadata 전송을 모두 앞당긴 것으로 계산하지 않는다. 분리 실행은 `probe_nes_candidate317.py`에 `NES317_ARM_ONLY=1`로315 RTL을 유지하고,0으로 공동 RTL을 결합했다. 두 실행은 동일 ARM PT_LOAD를 사용한다.

DMA/plan/IRQ 양보는 각 준비 slice 및 발행 직전의 checked boundary에서 이뤄진다. 최종 encoding과 한 SPI transaction은 중간에 끊지 않는다. 그 사이 새 ready가 도착할 때의 지연까지 실행 일정에 포함하며 무조건적인 즉시 DMA 서비스나 물리 IRQ WCET를 주장하지 않는다.

ARM ELF text는28238→28986B, BSS는47132→47348B, 관측 stack은1288→1304B다. 전체 실험 ELF 비용이며 추가 RAM을 FPGA RAM 절감으로 계산하지 않는다.

## host·validator 공동 실행 변경

최종 canonical replay 주소는 validator의 실제 display/receipt 검사 cursor에서 제공한다. host가 마지막 byte 판정과 replay 증가를 별도로 하지 않는다. validator가 hash→certificate→최종 seal의 실행·완료를 연속 처리하고 host의 중간 MHASHWAIT/MCERT/MCERTWAIT/MFINISH 제어를 제거했다. terminal에서는 실제 coverage 위치·rec_i24·digest_ready·certificate_ok·all_consumed를 다시 검사한다.

producer의 manifest byte 수/길이 검사는 유지한다. 기대값 queue RAM과 실제 receipt phase RAM은 독립 저장소로 남는다. 이번 변경은 최종 replay/완료 경계이며 ingress 전체·source/plan 전체를 교체한 것으로 표현하지 않는다.

## 동일 전체 일정 비교

|실행|frame|전체 ms|315 대비 ms|ARM 명령|SPI B|
|---|---:|---:|---:|---:|---:|
|observe02|905|104.635790|+0.000000|2247180|10294|
|observe02|906|116.932415|+0.000000|1634451|10948|
|observe02|907|16.906343|+0.000000|700873|1165|
|arm01|905|104.148023|-0.487767|2244521|10280|
|arm01|906|116.906824|-0.025591|1634292|10934|
|arm01|907|17.119885|+0.213543|703982|1165|
|window01|905|104.148023|-0.487767|2244521|10280|
|window01|906|116.906824|-0.025591|1634292|10934|
|window01|907|17.119885|+0.213543|703982|1165|
|normal01|905|80.013631|-0.061090|2237083|10168|
|normal01|906|56.410914|-0.056136|1623486|10780|
|normal01|907|14.763186|+0.016682|701133|1123|

제한3프레임 합계 변화는 ARM-only -0.299815ms, joint -0.299815ms다. joint907의 절대 완료 변화는-0.299815ms, 첫 BG 이후 tail 변화는-0.299815ms다. 시작 위상 변화만을 처리량 개선으로 세지 않는다. joint907은17.119885ms이며60fps까지0.453219ms 차이가 남는다.

## Quartus Lite 전체 비용과 판정

|항목|315|317|차이|
|---|---:|---:|---:|
|LE|22664|22685|+21|
|comb|17870|17891|+21|
|FF|9040|9037|-3|
|RAM bits|307808|307808|+0|

host/validator FSM 추출은 유지됐다. 주소·terminal control의 새 선택 비용이 회수 비용을 상쇄해comb는21개 증가했다. 전체 조합 논리 부족분은2462→2483개다. 더 넓은316의4474→2012 예산을 충족하지 못하므로 공동 후보는 채택하지 않는다. FIT/STA·seed 변경은 하지 않았다.

## 검증·실패 보존

- observe02는315 PT_LOAD/RTL 및 시간·ARM·SPI 동일. 최초 observe01은 자식 worker 진입 경로로 관측 hook이 실행되지 않아 계측 근거에서 제외하고 보존했다.
- guards01의12개 독립 검사·STOP·소비/token/범위/최종ACK 오류 주입과 정상 대조 통과.
- terminal01은 autonomous certificate digest mismatch, certificate 중 STOP, all_consumed=false의3개 추가 오류 및 정상 대조 통과.
- ARM29검사: bounded 준비 내용 일치, DMA/plan/IRQ 양보,13개 중간 STOP, BUSY에서 기존 DMA 버퍼 보존, 준비 후 FAULT, metadata credit/CRC/STOP/counter wrap/중복 발행 방지. 최대 준비 slice341명령. controlled endpoint 검사와 live schedule을 구분한다.
- ARM-only 제한905..907 3개 일정과 결합 정상·제한905..907 6개 일정에서 실제 bytes/metadata/receipt/CRC·2credit·표시/최종ACK 확인.315와 hash 동일한 queue/SPI/plan은 기존 unit 증거를 재사용하며 새 실행으로 세지 않는다.313 ordinary CPU trace 재사용, 새CPU 시험 아님.

기존 cache_index141 외 새control latch/undriven 경고가 없음을 raw MAP 로그에서 확인했다. VBlank/tile/map service 일부는 모델이고 whole71/fullRUN/full live65816/실물60fps는 미검증이다. production227/GBC164/saveSRAM을 변경하지 않았다.

Preserve315 baseline and317 rejected joint terminal evidence. Do not tune isolated state/seed/FIT. Compare validated ARM scheduling separately; widening address mux alone did not meet the4474->2012 regional budget. Reconsider whole host/validator/source/plan roles and RAM port ownership with measured metadata ready and BG timing before another implementation. Keep independent expectation/receipt/CRC, storage!=consumption, STOP/finalACK/VBlank and actual ARM/IRQ/2slot costs.
