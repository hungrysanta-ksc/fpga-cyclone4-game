# NES310 저장 credit과 실제 소비 완료 분리

이번 후보는 압축 requirements의 선행 저장으로 순환 대기를 없애는 실제 ARM/RTL 실험이다. 전체 목표 후보로는 채택하지 않는다. 307 대비 whole Lite 조합 논리가 134개 증가했고, 제한 ROM warm907의 전체 시간도 0.323632480ms 늘었다. production227/GBC164/saveSRAM은 변경하지 않았다.

## 구현한 경계

- ARM은 309에서 검증한 40B header/16B 단계 준비를 재사용하되, 준비만 숨기는 것으로 끝내지 않고 checked phase-2 poll 뒤 선행 전송에 연결했다. 새 packet buffer는 없다. DMA-ready/plan supply/queue credit를 확인하고 io259 밖에서 전송하므로 재귀 SPI가 없다. SPI 전송 도중 새 IRQ가 발생하는 비용은 실제 일정에 포함한다.
- op15/section2는 압축 requirements의 저장 요청이다. 기존 독립 SPI CRC, 16B header, physical sequence/serial/generation/길이 검사를 통과해야 한다. payload가 90B를 넘으면 기존 raw/후반 전송을 유지한다.
- phase RAM 166..255의 90B 공백만 사용한다. 기존 bank0 validity 0..165, bank1 validity 256..421, hash448..511, receipt512..677, H2/offset680..715, map768..1023과 겹치지 않는다. CLEARFRAME/RAW invalidation도 이 공백을 덮지 않는다.
- 마지막 payload write가 완료된 다음 completion state에서 host가 queue slot credit을 반환한다. 이때 receipt/coverage cursor와 display 상태는 변경하지 않는다. 저장 ACK는 DMA 완료나 최종 표시 ACK가 아니다.
- 이후 일반/typed DMA가 원래 독립 소비 검사를 거쳐 진행한다. 첫 map manifest가 head에 오면 그 head를 유지하고 저장본을 재생한다. 24B display/H2 의미와 정확한 166 requirements를 기존 독립 검사기가 다시 검사한다. 성공 후 현재 map manifest를 실행하며, 재생 완료 자체는 queue retire/physical sequence를 증가시키지 않는다.
- host reader9bit가 기존 parser8bit와 validator packet9bit를 대체한다. queue와 저장 RAM 재생은 같은 reader를 사용하며, exec-address mux와 별도 complete FF를 제거하고 완료 상태를 공유한다. 새 상태는 host replay/replay-wait와 stored-valid/length이다.
- STOP에서는 저장 소유권·실행·RAM write·표시를 폐기한다. 중복 저장, 잘못된 codec/정확한 길이, 조기 최종 ACK를 거부한다. 최종 coverage, hash/certificate, 12 exact display reads, token/final ACK, 기존 PPU VBlank 경계는 유지한다.

## 실제로 대체하지 않은 부분

기존 queue의 4×256B RAM과 accepted/retired 카운터는 유지한다. 새 credit 의미는 **보관된 requirements 한 패킷**에만 적용하고 일반 명령은 소비 완료 후 credit을 반환한다. SPI/plan 제어와 일반/typed 실행 FSM 전체를 없앤 구현은 아니다. 9개 metadata packet을 담는 byte arena나 out-of-order completion protocol을 완성했다고 하지 않는다. 이 제한된 경계에서조차 면적이 늘었으므로 별도 보관 큐를 더 붙이는 방식은 승격하지 않는다.

## 실제 일정의 의미

같은 source replay, Cortex-M4 실행(CPI1/84MHz), IRQ/공유 SPI, tile ROM arbiter, 고정 ROM 허용 창, ordinary65816 bus trace, map/tile/display 모델을 사용했다. 선행 op15 때문에 physical sequence가 달라져 trace의 packet sequence read/ACK 두 바이트만 현재 admitted sequence로 재결합했다. event 수·시각과 다른 데이터는 그대로 검사했다. 새 전체 65816 프로그램 실행 증거는 아니다.

제한907은 다음과 같다.

- 307 전체 17.616924958ms → 310 17.940557438ms: +0.323632480ms.
- 60fps 프레임 예산 초과는 0.950258291ms → 1.273890771ms.
- 저장 credit 반환271.884667ms, requirements 재생 완료280.041907ms. 그 사이 뒤 tile/map 소비 10건이 진행되어 순환 대기 해소를 확인했다. 제한905/906도 각각66/69건이 진행됐다.
- 첫 BG ROM 승인274.905042ms, 첫 OBJ 승인275.212675ms는307과 동일하다. ROM 창이나 위상을 임의 변경하지 않았다.
- 절대 완료280.265546ms → 280.209683ms로55.863µs 빨라졌지만, 프레임 시작은379.495µs 먼저 이동했다. 최종 분석 JSON의 정확한 시작 차이를 기준으로 하며 절대 완료 개선을 frame elapsed 개선이라고 하지 않는다.
- 제한907 ARM697018→700776명령, SPI1079→1091B. 선행 E1의 payload 총량을 줄인 결과가 아니며 추가 E2 12B와 준비/credit/IRQ 비용도 포함한다.


|조건/frame|307 ms|310 ms|차이 ms|
|---|---:|---:|---:|
|normal905|78.493058072|78.507466990|+0.014408918|
|normal906|54.952658742|54.941522512|-0.011136230|
|normal907|14.356691354|14.375327494|+0.018636140|
|restricted905|103.654756128|103.299351302|-0.355404826|
|restricted906|116.901733526|116.877642906|-0.024090620|
|restricted907|17.616924958|17.940557438|+0.323632480|

전체 정상/제한3프레임 수치와 저장/재생/뒤 DMA 이벤트는 `analysis/storage310-verification.json`에 기록한다. 후반 wire 시간, CPU 준비, ROM 대기, DMA 점유는 겹치므로 독립 절감으로 더하지 않는다.

## 전체 Quartus Lite 비용

|전체 동일 경계|307|310|변화|
|---|---:|---:|---:|
|LE|22402|22536|+134|
|조합 논리|17583|17717|+134|
|FF|8965|8968|+3|
|RAM bits|307808|307808|0|
|조합 논리 부족(15408 대비)|2175|2309|+134|

새 whole MAP은 성공했으며 기능 검증의 host/validator/queue/SPI 입력 hash와 연결한다. board의 기존 tile_closed267 출력 alias 두 줄만 live와 다르며307에도 동일한 차이가 있음을 확인한다. host 자체2093→2132, validator1251→1315로 두 블록만도103개 증가한다. parent inclusive와 child를 중복 합산하지 않는다. 나머지31개는 전체 합성 차이이며 무료 회수나 특정 블록 절감으로 간주하지 않는다. 기존 nes_rom_service cache_index141 latch 경고는307과 동일하고 새 host/validator latch나 undriven 경고는 없다. FIT/STA를 실행하지 않았고 이 상태로 보드 적합성을 주장하지 않는다.

## 판정과 다음 경계

저장 credit≠소비 receipt 분리는 필요한 구조이며 실제 경로에서 작동한다. 그러나 **기존 실행 제어를 대부분 남긴 채 작은 보관·재생 경로를 추가하는 후보는 시간과 회로 예산을 동시에 맞추지 못한다.** 307을 기준으로 유지하며310을 production에 승격하지 않는다.

다음 검토는 기존 queue/host/validator 저장·해석·완료 상태를 직접 삭제하는 정규화 record 실행 경계가 먼저다. requirements 외 일반 DMA와 map manifest까지 포함한 저장 수명/포트/credit 규약, 전송 identity와 소비 fence의 분리, independent semantic checks를 한 표로 확정해야 한다. 기능2427comb+128여유라는307 경계 예산은 요구치이지 예상 합성값이 아니다. 새 비용이 이를 지지하기 전 별도 FIFO/미세 FSM/seed/FIT 반복을 하지 않는다. 시간은 고정 ROM 창에 대한 실제 frame start까지 포함해 비교한다.

실물60fps, full ARM RUN, 전체 live65816/71frames/heavy7, FIT/STA/CDC·IO는 계속 미검증이다. 모든 실패 및 성공 원본은 로컬 probes/nes-storage310에 보존한다.

## 검증 및 실패 보존

- 정상3/제한3 live 성공. 제한3만 실제 early storage를 사용하고 정상3은 기존 후반 경로를 사용한다. max queue credit4, 최종 ACK와 기존 display/VBlank 검사 PASS.
- 저장 도중/credit 반환 후/재생 중 STOP, bad codec, 조기 최종 ACK, 중복 저장, 재생 길이 오류 7개와 기존 독립 소비·STOP·최종 ACK 회귀 25개 PASS. RAM freeze 포함.
- 동일 M4 ELF: bounded 준비24, STOP35/IRQ재개11, credit11, supply20, native71프레임 PASS. native는 intercepted sink이며 실제 ACK 증거로 합산하지 않는다.
- window01 unused C variable 컴파일 실패, window02 SV 선언 순서 실패를 수정했다. window03의 기존 RAM 범위 검증기는 새 전용166..255 쓰기를 거부했고 새 owner/state/범위로 한정해 허용했다. window04는 packet sequence 변경을 기존 CPU trace가 거부하여 해당 identity 데이터만 재결합했다. window05/normal01 최종 PASS. 라이선스 오류는 없었다.
- ARM text28094→28450B(+356), BSS47120→47124B(+4), observed stack1288B 동일.
