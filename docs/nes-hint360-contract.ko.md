# NES360 — 작은 tag 집합과 source·host 교체 예산

338 RTL·355 ARM을 유지한다. 359 host 절감은 재사용하며, 작은 tag 집합은 **증분 준비 후 5개를 한 패킷으로 전송**하는 쪽이 유리하다. 연속 ROM 위상의 앞선 구간에 들어가는 경계 실험은 통과했지만 전체 회로는 기준보다90comb 증가했다. 시간·회로 동시 개선이나60fps 달성으로 판정하지 않는다.

## 실제 생산·전송 경계

기존 실제359/355 실행에서 첫 N5 입력 직전 resident RAM을 관측했다. 관측기는 명령을 추가하지 않으며905..907 전체 event CSV와 기존359 연속 실행이 정확히 같다. source decoder 명령 증가도0이다. 이전 표시 bank에는 있고 다음 bank에는 없는 immutable CHR tag를 최대16slot씩 탐색한다. warm907의5tags는6525/6424/6426/6425/6427이며 미래 geometry/최종 plan을 생산기 입력으로 쓰지 않았다. 이는 예측 hint이지 향후 모든 프레임의 필수 tag 집합 증명이 아니다. 미적중은 정상 ROM 경로로 처리해야 한다.

실제 Cortex-M4에서 generation/epoch/serial·CRC16 packet을 만들었다. cold905와 priming906은 무발행, stale epoch/serial·mutable ROM·STOP reset4건은 거부했다. resident 이력은 쓰지 않는다. 검증 범위는3프레임이며71프레임 새 경로 검증은 아니다.

| 생산 방식 | ARM 명령(reset 포함) | SPI payload | packet 수 | BSS |
|---|---:|---:|---:|---:|
|2/2/1tag 증분 전송|4295|52B|3|68B|
|16slot 증분 준비·5tag 묶음|3631|24B|1|74B|

두 object 모두text1916B/관측stack56B로 기존1416B/48B보다500B/8B 증가한다. 묶음의 BSS 증가는42B다. 최대 한 번의 준비는858명령(CPI1 10.214µs/CPI2 20.429µs)이다. full firmware 링크 크기나 물리 MCU WCET는 아니다.

## 실제 cache·ROM 경계 시간

5tag 순차 조회와80B 데이터 저장을128×8 M9K에 구현했다. 조회 지연도 실제 testbench에 포함한다. 실제 arbiter/READ16/70ns ROM pin fixture, 주기적 core 우선 경쟁에서80B를 채우고 재읽어 추가 ROM 요청0을 확인했다.80B cache 재읽기는22.272460µs다. pending fill 중 STOP은 응답을 차단하고 physical reader를 drain하며 epoch 변경은 miss로 돌아간다.

실제 ARM packet을2.625Mbit/s와packet당8µs CS의 TB serializer로 전송한다. 실제 연결된 SysTick handler66명령·stack32B와 예외 진입/복귀24cycle 할당을 청구했다. CPI1/2는 감도 비교이며 실제 사이클 계측치가 아니다.

|전송|ROM 시작 cycle|CPI|SPI+CS 종료|80B fill 완료|
|---|---:|---:|---:|---:|
|2/2/1|5677152 연속|1|1.692880ms|1.710389ms|
|2/2/1|5677152 연속|2|1.744796ms|16.872752ms|
|5 묶음|5677152 연속|1|1.583642ms|1.642753ms|
|5 묶음|5677152 연속|2|1.627653ms|1.686389ms|
|5 묶음|7368026 고정|1|1.583642ms|5.032076ms|

연속 구간 끝 상한1.727706540ms 대비 묶음 CPI2 여유는41.318µs다. 상한에는2NESclock 불확실성이 있어 전부 구현 예산으로 쓰지 않는다. 다음 EA admission·CDC·추가 software/중재는 우선20µs 이내를 검증 목표로 두고 나머지를 여유로 남긴다. 이것도 WCET 보증이 아니다.

EA 하드웨어 수신·CRC admission·collector lease/CDC·실제 foreground 송신은 아직 연결하지 않았다. TB queue는 합성 회로가 아니다. 새 SPI 전송이 후속 D4/D5와 DMA/plan 준비를 늦추는 전체 일정 효과도 미측정이다. 따라서 고정/연속 fill 차이를 프레임 이득으로 빼지 않는다. 기존 동일 위상 전체 warm25.051563ms와 연속20.689706ms는 그대로이며 선택 기준의60Hz 부족4.023039ms도 유지한다.

## Quartus Lite 전체 비용

|whole MAP|LE|comb|FF|RAM bits|15408comb 대비 부족|
|---|---:|---:|---:|---:|---:|
|338 선택|22144|17274|9018|307808|1866|
|359 host|22083|17213|8999|307808|1805|
|359 host+360 cache 용량|22234|17364|9005|308832|1956|

17tag cache18254comb보다890개 작지만 host-only보다151comb/6FF/1024bit가 추가된다. 유효80B 외에 물리128×8 M9K 전체를 청구했다. whole MAP은 정상 tile consumer의 cache 용량 교체이며 누락된 EA 수신/lease 회로까지 구현한 결과가 아니다. FIT/STA와 실물 적합성은 미검증이다.

## 남은 실제 삭제 범위와 예산

359 whole의 중복 없는 분할은 encoder1349 + transport399 + host flow self2057 = source-host3805comb다. checker/aperture1245, queue/SPI795, plan458, 나머지10910을 따로 둔다. flow inclusive2712와 자식 블록을 더하지 않는다. transport399에는 CDC mailbox가 이미 포함된다. 새 cache의 전체 증가151은 나머지에 배정한다.

목표15253comb(소자 대비155여유)을 유지하면 source-host 상한은 **1839**, queue/SPI는650이다. 각각1966/145개, 합2111개를 실제로 삭제해야 한다. 이전2035 상한보다196개 엄격하다. source encoder+transport1748을 비용 없이 전부 삭제한다고 가정해도218개가 모자라므로 host byte 실행 제어까지 함께 바꿔야 한다. 이 상한은 달성 예측이 아니다.

다음 교체는 NES row producer와84MHz host byte 실행기 사이 고정 RAM 포트 계약이다. source의 header/MASK/SHIFT/CRC byte continuation·주소 선택과 host의 PREAD/PCAP·RLE/staging 진행을 공동 교체한다. source RAM B 출력 상수0은 이미 제거되므로 새 절감으로 세지 않는다. 독립 expected/read CRC·coverage·receipt 공개·최종 ACK는 유지한다.

phase RAM A는 NES clock, B는 host clock으로 유지하며 clock mux를 도입하지 않는다. 후보2×66B row slot640..705/800..865는 H2의832..863과 겹친다. source drain 후 H2로 소유권을 넘기는 경계가 증명되어야 하며 동시 사용 가능한 무료 RAM이 아니다.5KiB base history 이동, query CDC와 NES plan cursor, collector 취소 적용 ACK·STOP 뒤 DONE drain도 비용에 남긴다. 이 넓은 source-host 교체는 이번에 구현하지 않았고 범위·예산을 확정했다.

hint는 ordinary2slot credit을 차지해 input COMMIT과 순환 대기를 만들면 안 된다. 기존 plan 저장을 빌린다면 HINT→PLAN 소유권과 drain을 실제 구현해야 한다. immutable epoch/serial·packet CRC 확인 전 cache 내용은 표시 권한을 갖지 않는다. 새 plan·DMA는 input COMMIT와 기존 검사를 통과해야 한다. hint 실패/STOP은 cache를 무효화하고 정상 경로로 복귀한다.

기존359 독립검사/STOP/잘못된 token/최종 ACK 증거는 해시 재검증하여 재사용했다. 새 전체65816/VBlank 실행 검증은 하지 않았다. 최종 ACK·VBlank 계약을 완화하지 않으며 전체 연결 후 다시 검증한다. Production227/GBC164/saveSRAM은 변경하지 않는다.

근거: analysis/hint360-verification.json의729개 해시, probes/nes-hint360의arm01..03/window01/cache01..03/map01 및 원시 로그. 초기 실험도 보존한다.
