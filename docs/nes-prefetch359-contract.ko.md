# NES359 — host 공통 read 실행기와 17 tag 선행 읽기 비용

338 RTL·355 ARM을 기준으로 유지한다. host read 진행 제어 교체는 조합 논리 61개를 줄였지만 제한 ROM 시간은 그대로다. 17 tag 일괄 선행 읽기는 실제 ARM 준비 시각과 저장 비용 모두 목표를 충족하지 못하므로 선택하지 않는다. 국소 host 개선과 전체 prefetch 채택을 구분한다.

## 실제 삭제·유지한 경계

`nes_host359.py`는 host의 tap 진행 FSM, 별도 position/value 저장과 CRC→receipt 대기 제어를 삭제한다. 물리 read strobe·offset/count·중복 read·token/credit 검사는 host에 남기고, 34bit read event로 독립 validator의 기존 84MHz CRC·coverage·RAM RMW 상태가 진행을 맡는다. validator의 기존 RAM 주소/cursor를 재사용하고 job/byte/unit pending 상태는 새 비용으로 포함했다.

독립 expected, 실제 읽은 byte의 CRC/coverage, private receipt를 완료한 뒤 소비 ACK를 공개하는 조건, 12B 표시 문맥과 최종 lease 해제를 유지한다. source338의 NES 실행·query/CDC·plan cursor, host packet/manifest 해석 전체를 삭제한 것은 아니다. 358의 별도 취소 보강 진단을 이 후보에 합쳐 적용했다고 주장하지 않는다.

## 실제 ARM·IRQ·2슬롯 일정

355와 같은 실행 load image, SPI 출력 순서/내용, source bytes 및 동일 시작 ROM cycle을 확인했다. 원래 ordinary65816 trace, 실제 ARM 출력 실행·IRQ·SPI·2슬롯·staging/ROM 경쟁을 유지한다. source decode는 실제 M4 명령 비용을 replay하고 tile/map/display는 기존 버스 모델이다.

| warm907 | 기준338/355 | host359 | 차이 |
|---|---:|---:|---:|
| 제한 ROM 연속 |20.689706ms|20.689706ms|0|
| 동일 시작·ROM 위상 |25.051563ms|25.051563ms|0|

각 일정의905/906 cold도 실행했고 baseline과 전체 시간이 같다. 첫 ROM 허용 구간이 병목이므로 국소 read 제어 감소를 frame 시간 절감으로 환산하지 않는다. 연속 일정의60Hz 부족은4.023039ms이다. 고정 시작 위상의 값과 서로 빼서 이득을 만들지 않는다.

## 실제 ARM 17 tag 생산 비용

변경 map/row/exception/raster를 추적하고 prefix가 닫힌 뒤17개까지 중복을 제거한다. generation/epoch/serial과 CRC16이 포함된 EA 요청은48B다. 현재 producer는 별도 실제 Cortex-M4 실행으로 검증했으며355의 실제 SPI foreground에 EA 송신을 통합한 것은 아니다.

- 71프레임의4910B canonical 복원·CRC packet 일치, cold 무발행과 stale epoch/serial, STOP reset,17tag 초과 거부를 확인했다. 이전 표시 namespace가 맞아야 시도하고, hint가 실패해도 원래 source decode/최종 검사는 유지한다.
- warm907 첫 prefix는 기준1.458201190ms에 확정된다. 추가 decode5537 + filter18443 =23980명령, CPI1/84MHz에서0.285476190ms이다. 요청 준비는1.743677381ms로 앞선 ROM 구간의 끝 상한1.727706540ms보다15.971µs 늦다. SPI 전에 이미 놓친다.
- warm 전체 추가 decode12085/filter18459명령도 포함한다. 별도 decoder object는 text1416→2216B, BSS32→136B, 관측stack48→56B다. full firmware 링크 크기나 물리 MCU WCET는 아니다.
- packet을 모두 받은 뒤 채우는 계약에서는48B SPI+8µs CS가154.286µs,272B ROM의12NESclock/byte 낙관적 하한이148.364µs다. 합302.649µs는 prefix 이후 남은269.505µs보다33.144µs 크다. 이 직렬 하한을 SPI/ROM streaming 중첩 구조의 불가능성으로 일반화하지 않는다.

## 272B cache 실제 경계와 전체 합성

17개 tag와 byte valid를 가진 cache를 구현했다. RESET/STOP/epoch 변경은 validity를 닫고 기존 arbiter가 물리 READ16 응답을 drain한다. 실제 arbiter/physical reader,70ns ROM pin fixture,core 우선 경쟁에서272B fill 후 전부 재읽어 추가 ROM 요청0을 확인했다. STOP 응답 차단·drain과 epoch 변경 후 miss도 통과했다.

ARM이 만든48B를 실제 SPI bit 간격으로 보내는 **testbench serializer/capture**와 cache request driver를 썼다. EA 하드웨어 receiver/CRC admission, shared SPI 중재, 새 collector prefetch lease/CDC 및 실제 tile 소비에 선행 cache를 연결한 전체 경로는 아직 없다. 따라서 아래 시각은 bounded port 실험이며 전체 frame 개선 수치가 아니다.

| 시작 ROM cycle | SPI 종료+CS |272B fill 완료| ROM reads |
|---|---:|---:|---:|
| 연속5677152 |1.897963ms|17.019978ms|272|
| 고정7368026 |1.897963ms|5.138393ms|272|

고정 위상에서만 앞선 창을 사용하는 효과를 확인했다. 연속은 다음 창까지 기다린다. 두 실험 모두 core 우선 응답의 데이터와 허용 slot 밖 fill 금지를 확인했다. 실제 NES CPU 전체 부하가 아니라 기존 주기적 core 경쟁 fixture이다.

| whole Quartus Lite MAP |LE|comb|FF|RAM bits|15408comb 대비 부족|
|---|---:|---:|---:|---:|---:|
| 선택338 |22144|17274|9018|307808|1866|
| host359 |22083|17213|8999|307808|1805|
| host359+동기 cache 용량 |22982|18254|9353|311904|2846|

cache는272B 유효 저장을512×8 M9K 한 개에 배치하므로4096bit 전부를 청구한다. tag/valid/검색·replacement/응답 제어까지 host-only 대비+1041comb/+354FF이다. 이 whole MAP은 기존 정상 tile consumer의 cache를 교체한 **용량 비용**이다. 누락된 EA dispatch/CDC/prefetch lease를 무료로 계상하지 않으며, 전체 선행 읽기 경로의 기능 검증/합성 결과로 부르지 않는다.

초기 비동기 확장26891LE/19987comb/11537FF/307808bits와 자동 RAM 선택에 맡긴 동기판26911LE/20007comb/11537FF/307808bits도 보존했다. 고정 동기 port와512B 물리 M9K 배정을 명시한03만 최종 용량 비교에 사용한다. read-during-write 값은 pending fill 중 노출되지 않는 계약이다. 기존 전체 dual-clock RAM/CDC 경고, FIT/STA와 실제 보드 적합성은 해결했다고 주장하지 않는다.

## 검증·판정과 다음 예산

host의 private receipt STOP, raw CRC STOP, 완전 소비 뒤 wrong token 주입3건과 RAM/staging freeze가 통과했다. 독립 raw0/final7건(불완전 표시 read ACK, expected/CRC/coverage/consume 오류 포함), private STOP/cold reset 및 aperture 검사를 유지했다. read→unit→private write→publish 순서,2credit,12B 최종 표시를 별도 분석기로 다시 비교했다.

선택338/355의 부족4.023039ms/1866comb는 그대로다. host359는 재사용 가능한 국소 후보로 보존하며 목표15253comb까지 추가1960개가 필요하다. cache 용량을 더한 후보는3001개와 아직 없는 EA 제어 비용까지 줄여야 하므로 선택하지 않는다.

다음은 남은 source/host row·주소·RAM 소유권 제어의 실제 삭제와 더 작은 선행 작업 집합을 함께 검토한다. 최종 plan에서 관측한5tags는 oracle이며 prefix 시점에 사용 가능한 계획으로 간주하지 않는다. 이를 실제로 증명하면24B 요청+80B ROM의 직렬 하한124.779µs로 ARM/IRQ/제어에144.726µs가 남는다. 다른 후보는 incremental tag 생산과 SPI/ROM streaming 중첩이다. 이때 ROM은 immutable CHR 범위로 제한하고 cache는 packet CRC/input COMMIT 전까지 표시 권한을 얻지 않아야 한다. 작은 순차 tag 조회의 추가 cycle·RAM 포트 비용과 collector 취소 완료·STOP drain까지 다시 계상한다.

source-host2035/queue-SPI650 및 whole15253comb는 합격 상한이지 절감 예측이 아니다. 독립 검사·최종 ACK·VBlank를 유지한다. 전체 firmware RUN, 전체65816/VBlank 실행, FIT/STA, 실물60fps는 미검증이다. Production227/GBC164/saveSRAM 변경과 자동 merge는 없다.

근거: `analysis/prefetch359-verification.json`의548개 hash, `probes/nes-prefetch359`의 arm01 실패/arm02·03, window01 컴파일 실패/window02, fixed01, guards01, cache01, map01, cachemap01·02·03 및 원시 로그. analysis01은 기존 board 전용 `tile_closed267` 출력 포트와 simulation의 계층 관측 차이를 엄격 비교에서 검출했다. 이 두 passthrough 구문만 명시적으로 정규화한 analysis02·최종03은 통과했다. 그 외 read/validator/core 입력은 일치한다. 이전 실패 증거는 삭제하지 않았다.
