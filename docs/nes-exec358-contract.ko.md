# NES358: 6클록 read 게이트와 실제 collector 취소 검증

338 RTL·355 ARM을 유지한다. 서로 다른 두 실험을 구분한다. (1) 실제338 read FSM과 독립 validator를22MHz에서 실행한 경계 시험, (2) 기각된356의 실제 collector/query/DONE 취소 경계만 보강한 host-clock 진단 후보다. (2)의 전체 MAP이나 일정은 NES 공통 실행기의 구현 결과가 아니다. 입력 전 ROM 선행 읽기는 실제 ARM prefix 확정 시각을 측정한 구조 검토이며 아직 ROM 요청 경로에 연결하지 않았다.

## 6클록 read 처리: 일반 상한으로는 실패

`nes_mux260.sv`의 실제 tap FSM/단위 주소 계산 블록을 추출하고 clock 이름만 바꾸어, 변경하지 않은 `nes_validator278.sv`와 동기 RAM을22MHz에서 함께 실행했다. 공개 grant/H2/BEGIN으로 시작하며 CRC는 별도 상수 oracle, map/OAM/raw coverage는 실제 RAM 값을 검사한다. validator 상태를 force하여 통과시키지 않는다.

| 실제 경로 | capture 이후 job clocks |22MHz 시간 |
|---|---:|---:|
| map receipt 완료 |4|181.818ns|
| 일반 OAM private receipt 완료 |6|272.727ns|
| scroll 시작·CRC 완료 |8|363.636ns|
| raw 마지막 byte CRC 저장+private receipt |10|454.545ns|

raw 중간 byte는3, 첫 byte는4clocks다. 최대10은6클록 상한을4클록 넘고 실제 관측된 최소 인접 read369ns보다 길다. scroll8도 약5ns밖에 여유가 없어 캡처/중재 여유를 입증하지 못한다. 따라서 기존 실행기를 그대로 NES 클록으로 이동하는 A는 기각한다. 느린 clock으로 옮긴 전체 queue/CPU를 실행해 성공했다고 주장하지 않는다.

이 시험의 aperture byte와 read-end는 qualified fixture다. 실제 aperture 응답/버스 동기화, queue·SPI·CDC까지 포함한6클록 증명이 아니다. 이미 더 작은 실제 제어 경계가 실패하므로 전체 경계를 통과했다고 볼 수 없다. raw 마지막 byte의12개 STOP 위치에서 쓰기·receipt·hash 공개·seal 차단은 통과했다. read01 선언 순서 컴파일 실패와 read02 CRC oracle의 주소896→448 수정 전 실패도 보존한다.

## 실제 collector 취소 ACK와 STOP 뒤 DONE

취소 검증은356의 실제 collector/source 선행 query 연결을 사용한다. 기존338을 선택한 채 진단 후보만 수정한다.

- collector는 release가 각 member의 owned/response와 자신의 joining/response를 실제 비운 뒤 `collector_cancel358`을 등록한다. common reset으로 비운 초기 상태도 ACK로 표시하고, 다음 capture start에서 ACK를 지운다.
- query WAIT는 정상 응답을 무한히 기다리지 않고 **STOP과 실제 collector 취소 ACK가 함께 확인되면** 한 번의 discard reply로 host busy/메일박스를 반환한다. drain 조건에도 collector ACK를 포함한다.
- source DONE의 pending 설정·송신을 STOP에서 차단하고, 도착지에서 다시 cancel을 검사한다. STOP 직전 송신된 DONE도 표시 lease 전환을 일으키지 못하게 한다.
- 전체 collector를 통과한 WAIT 중 취소, response 직후 취소, input→display handoff 중 취소를 실제 fault injection으로 검증한다. 독립 expected/final 검사와 aperture 회귀는 별도 보존한다.

이 검증은 paused-clock·namespace wrap·STOP 후 무reset 재시작 전체를 새로 증명하지 않는다. 기존 common reset/취소 전파와 FIFO 반환을 사용하며 실제 CDC/STA는 여전히 열려 있다. 356 실패 증거는 수정하거나 삭제하지 않는다.

### 동일 위상과 연속 일정의 실제 결과

취소 보강 진단은 두 일정에서 각각905..907 세 frame을 실행했다. ARM355 ELF load image와 실제 출력 wire를 기준과 대조하고 read→unit→private RAM→token 공개 순서,2credit 상한과12B display view/최종 lease retire를 확인했다. warm907은 연속20.689706ms, 동일 시작·ROM 위상25.051563ms로338/355와 같았다. source SPI는668→707B, 입력 완료는2.690513→2.861238ms로356의 회귀를 유지한다. 정상 ROM의 개선을 새로 측정하지 않았으며, 제한 ROM 구간 때문에 전체 시간이 같다고 입력 경로가 빨라졌다고 해석하지 않는다.

collector WAIT/returned-response/handoff STOP3건과 aperture 회귀, raw0/final/private STOP/cold reset8건이 통과했다. 이 일정은 실제 ARM 명령·SPI·IRQ·2슬롯·ROM 경쟁 모델과 기존 ordinary65816 trace를 포함한다. map/tile/display는 busmodel이며 전체65816·VBlank 실행을 새로 증명하지 않는다. 기존 최종 검사·표시 제약을 제거하지 않았으며 완전한 VBlank/hardware gate는 남긴다.

## 입력 완료 전 BG ROM 선행 읽기

355와 동일한 Cortex-M4 source decoder ELF로905..907의 실제 source packet을 다시 실행했다. 각 packet의 block CRC·엄격한 증가 record 순서 및 reconstruction을 확인하고, 측정 명령 수가 기존 실제 SPI/IRQ 일정에 반영된 decode 명령 수와 일치함을 검사했다.

warm907에서 첫237B payload가 끝난 뒤 `last=61`, `phase=1`, `valid=0`이다. map·row·exception prefix는 확정됐지만 최종 source CRC와 전체 geometry는 아직 승인되지 않았다.

| warm907 시점 | 동일 위상 ms | 연속 일정 ms |
|---|---:|---:|
| 첫 prefix decode 완료 |1.458201|1.458201|
| 전체 geometry/raster/count 확정 |2.656426|2.656427|
| 이전 ROM 구간 끝 보수적 상한 | 별도 위상 |1.727707|

연속 일정의 raw-tag 선행 요청 여유는 최대0.269505ms다. 전체 BG 변환 plan은 이 구간 전에 만들 수 없다. E9를 단순히 앞당기면 기존 COMMITTED/lease 계약을 깨므로 적용하지 않았다.

기존 `nes_chr_cache192`는16B짜리 **한 타일 cache**다. 실제 warm907 BG plan은서로 다른5tags를 사용한다. 한 타일만 데워서는 다음 miss의 ROM 대기를 없애지 못한다. 실제 최종 plan의5tags는 분석용 oracle이며 입력 초기에 사용할 수 있는 목록으로 간주하지 않는다.

prefix에서 가능한 후보를 비교했다:

| 후보 선정 | tag 수 | 실제 BG5tags와 교집합 | 의미 |
|---|---:|---:|---|
| 첫8화면 행 |5|0|화면 위쪽 우선은 이 frame의 첫 실제 DMA를 돕지 못함|
| 변경 map/row만 |0|0|exception/raster 변화 원인을 놓침|
| 확정 prefix의 변경 exception/raster/row 함께 |17|5|다음 실제 ARM 후보; Python 분석이며 새 ARM 처리비용 미측정|
| 확정 map+exception 전부 |82|5|164 tag bytes의 SPI만약0.500ms로 구간 초과|

17tags를 모두 유지하는 저장 시나리오는272B+tag/valid/epoch 정보다. tag bytes34B의 전송 하한은0.103619ms다.12NESclocks마다 ROM 수락 가능하다는 기존 제한에서272byte의 서비스 간격 비용은약0.148362ms이며, 두 비용을 직렬로 치르면 약0.251981ms로 약17.5µs만 남는다. 이는 제어 header·CRC·CS·ARM 필터·IRQ·arbiter·CDC를 제외한 **낙관적 예산 계산**이다. 실제 ROM request를 실행한 성능이 아니다. SPI 수신 중 ROM 생산을 겹치고, bounded priority/cache capacity를 함께 검증해야 한다.

새 prefetch는 collector 입력 lease의 captured epoch/generation 및 ROM 읽기 허용권을 확인해야 한다. tentative cache와 descriptor는 최종 source CRC·독립 expected/coverage·실제 DMA 소비 검사와 분리한다. STOP, source write, epoch 변경, ownership fault는 in-flight read를 drain하고 valid를 폐기해야 한다. output/display lease 전환 시 같은 namespace인지 재검증한다. final ACK/VBlank를 앞당기거나 생략하지 않는다. 추가272B와 새 포트를 기존 scratch/staging에서 공짜로 쓸 수 있다고 가정하지 않는다.

## 전체 회로 예산과 선택

| 전체 Quartus Lite MAP | LE | comb | FF | RAM bits | device 대비comb 부족 |
|---|---:|---:|---:|---:|---:|
| 선택338 |22144|17274|9018|307808|1866|
| 기각356 |22142|17303|9074|307808|1895|
|358 취소 보강 진단 |22116|17277|9075|307808|1869|

취소 보강 진단은356 대비26comb 줄었지만338 대비3comb/57FF 늘었다. 이것으로 회로 부족이 줄었다고 선언하지 않는다. source/query의 host-clock 이동을 다시 선택하지 않는다. whole MAP과 simulation의 source/core/transport/collector 변경본을 대조한다. FIT/STA는 실행하지 않았고 보드 수용·물리60fps를 확인하지 않았다.

357의 목표15253comb(155여유), 순감소2021은 유지한다. source+host2035와 queue+SPI650 상한 안에 새 취소/row/선행읽기 제어를 포함해야 한다.272B cache 시나리오는 아직 할당하지 않았으며 M9K/포트/valid 제어의 실제 비용은 미확정이다. parent-child MAP 합산이나 고립 FSM 면적을 전체 절감으로 계산하지 않는다.

## 다음 교체 범위

기존 raw CRC와 private receipt를 그대로 둔22MHz A는 중단한다. B의 고정 NES row producer/host RAM executor 경계에서84MHz read 서비스는 유지하고, source·host의 descriptor/주소/진행 제어를 실제로 삭제하는 후보를 우선한다. 또는 raw CRC 저장과 receipt를 공유 RAM 단일 포트에서6클록 이내 끝내도록 재구성한 근거가 있을 때만 A를 재검토한다. 새 latch 하나만 줄이거나 합성 seed를 돌리는 단계로 돌아가지 않는다.

시간 쪽은 변경 exception/raster를 포함한 prefix 후보 선정의 실제 ARM 순비용,17tag 제한·272B 저장/포트, SPI와 ROM 겹침 및 STOP drain을 작은 경계에서 먼저 검증한다. 그 뒤 독립 검사·최종 ACK·VBlank를 유지한 동일 ROM 위상/연속 일정을 각각 비교한다. 이번 결과는 미달 원인과 교체 조건을 좁힌 것이며 선택338의4.023039ms·1866comb 부족은 유지된다. 생산227/GBC164/saveSRAM은 변경하지 않는다.

증거: `analysis/exec358-verification.json`, `tools/probe_nes_read358.py`, `tools/nes_cancel358.py`, `tools/analyze_nes_prefix358.py`. 실행 결과와 최초 실패는 로컬 `probes/nes-exec358/`에 보존한다. 세부 일정·guard 최종 결과는 verification JSON을 기준으로 한다.
