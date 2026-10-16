# NES188 카트리지 bulk 읽기창 후보

2026-10-16. PR116 merge `7439179b45f7ce083a58362ffe5405c8a31d846a`에서 새 `codex/nes-bulk-aperture-188` 분기. [187 회고](nes-video-architecture187.ko.md)의 첫 작은 구현이다. **배포186은 그대로이며 새188 실기 ZIP은 없다.** [검증 JSON](../analysis/bulk188-verification.json).

## 작업 의미

현재 영상은 FPGA→SPI→MCU변환→SPI→SNES 순서다. MCU가 같은 데이터를 다시 보내지 않고 FPGA에서 준비한 내용을 SNES가 직접 읽는 후보를 구현하기 시작했다. 이번 변경은 **그 후보의 버퍼 소유권과 SNES 읽기 주소 경계**다. 게임 수집기·변환기·실제 SNES CPU와 아직 연결하지 않았으므로 전송 왕복 제거 완료나 FPS 향상을 주장하지 않는다.

`src/nes/rtl/nes_bulk_aperture188.sv`는2KiB×2 버퍼를 갖는다. 한 버퍼를 소비하는 동안 다른 버퍼를 준비할 수 있다. 완성된 묶음은 토큰을 확인한 consume까지 덮어쓰지 않는다. 현재 packet 큐 크기를 늘리는 변경이 아니며 기존 배포 경로에 추가 메모리를 사용하지 않는다.

## 인터페이스·수명 계약

| 경계 | 계약 |
|---|---|
| begin | 길이1..2048와32bit token. begin_ready일 때만 수락. 두 버퍼가 차면 backpressure |
| byte | begin 이후 순서대로 local host-clock 바이트를 받는다. 선언 길이 이상은 ready=0. seal/cancel과 같은 edge에는 byte를 수락하지 않음 |
| seal | 모든 바이트를 받은 **다음** edge에 명시적으로 공개. 조기 seal은 오류 후 작성 중인 묶음만 폐기 |
| cancel | 작성 중인 묶음을 폐기. 이미 공개된 이전 묶음은 유지 |
| descriptor | chunk_ready/length/token은 가장 오래된 완성 묶음을 가리킨다. 아직 SNES 레지스터/제어 패킷에 연결하지 않음 |
| read | 후보 주소 `$40:0800..0fff`. 현재 소비 버퍼의 선언 길이 안에서만 출력. raw 주소와 지연된 RAM 결과 태그가 일치해야 함 |
| consume | 일치하는32bit token만 해제. 잘못된/중복/빈 상태 응답은 오류이고 해제하지 않음. 이는 전송 버퍼 해제이며 최종 화면 표시 ACK가 아님 |
| reset/STOP/active loss | 즉시 출력을 차단하고 소유권을 무효화. 기존124 reset 모듈로 비동기 assertion/두 host-clock edge release. 클록이 멈춘 상태에서 active가 꺼졌다 켜져도 옛 데이터가 다시 노출되지 않음 |

producer/control은 모두 host clk 도메인이다. NES 수집 도메인에서 이 포트로 직접 연결하면 안 된다. immutable source snapshot과 CDC 인계가 다음 구현 대상이다. 외부 발행자는 STOP/restart를 포함해 오래된 응답과 겹치지 않는 새 token을 사용해야 한다. 무한 token 재사용/랩 안전성이 이 모듈 하나로 확보되지는 않는다.

메모리는 초기화/리셋하지 않는다. 선언한 바이트를 모두 쓴 뒤 공개하고 길이 밖 출력은 차단한다. SNES read strobe가 계속 내려간 채 주소만 바뀌는 DMA형 읽기를 처리한다. 원본 버스가 비동기이므로 실제 보드의 주소 유지·샘플 시각·IO/배선 타이밍 승인은 별도로 필요하다. 이번 두 위상 RTL 시험은 그 승인을 대신하지 않는다.

## 검증한 범위

SELECT `probes/nes-bulk188/test02` + `evidence01`. test01은 독립 endpoint 통과 결과를 보존했다. test02는 배포184/186의 변경 없는 `nes_sink_bus165.sv`와 ROM을 함께 사용했다.

- 기존 실제 C→65816 시험에서 보관한 합성7화면/259요청의 바이트28,039개를16묶음으로 나눠 local producer로 넣고 raw SNES 읽기 버스에서 그대로 읽었다. 패킷 경계를 넘는2048B 분할도 포함한다. 새 actual C/65816 실행은 아니다.
- host84MHz 참조 클록, 주소 위상0/3.5ns에서 각각28,049바이트를 확인했다(28,039 fixture +10 경계용 읽기). 각196,590검사는 반복 버스 소유권 검사도 포함하며 독립 시험 수가 아니다.
- 이전 버퍼를 읽는 동안 다음 버퍼를 작성·공개, 양쪽 full backpressure, 잘못된/중복 consume, 조기 seal, cancel, 길이0/2049, 경계 밖/주소 alias 차단을 확인했다.
- reset/STOP 즉시 출력 차단, 읽기 종료, write시 출력 금지, host clock 정지 중 active 취소·복귀 후 옛 묶음 미노출을 확인했다.
- 기존 packet `$40:0000`, control `$00:6000`, ROM `$00:8000` 읽기가 유지되고 두 decoder가 동시에 버스를 구동하지 않음을 확인했다. top-level 실제 mux/클라이언트 DMA는 아직 미연결이다.
- 승인된 Starter FLOAT 래퍼로 Questa를 실행했고 임시 서버를 종료했다. sandbox 시도는 simulation 디렉터리 생성 전에 종료되어 호스트 임시 경로로 실행했다. 라이선스·서버 로그는 공개하지 않는다.

## 자료 인벤토리 정정과 스크롤 절차

187 인계의 “기존 실제 SMB3 연속 스크롤 자료”는 과도한 표현이었다. 이번에 선택 자료를 대조한 결과 바로 사용할 수 있는 생산 변환 결과는 **오프닝 frame12/15**다. 이 두 장에서 BG16슬롯 중14개는 같은 슬롯/15개는 이전 어딘가에 같은 내용이 있고 OBJ2개는 같다. map64B 구역은63/64가 같다. 이것은 byte 비교이며 첫 레벨 스크롤 적중률·안전한 mapper cache key의 증거가 아니다.

당시165 record는 각1717×12=20,604B, 변환 section 합은5,493B다. **옛165 ingress와 현재186 합성 egress를 같은 프레임 성능으로 합치지 않는다.** level179의700frame Mesen 자료도 화면/PPU register 쓰기 참조이며 현재 compact/raw/CHR 전송 흐름이 아니다. 현재 생산 경로의 첫 레벨 연속 스크롤 양방향 자료는 미측정으로 남긴다.

사용자 재현 절차를 보존한다: 월드맵에서 숫자1 타일로 이동 후 A로 첫 레벨에 진입. 이후 **오른쪽+B를 계속 누른 채 A를 눌렀다 놓기를 반복**한다. 메뉴/레벨 진입은 상태를 확인하고 진행하며 임의의 고정 시간으로 대체하지 않는다. 이번 턴에 이 조작을 실행하거나 스크롤 캡처를 얻었다고 주장하지 않는다.

## 자원 예산과 다음 작업

payload RAM은4096B, 단순 블록 산정4M9K다. 현재42개에 추가한다면46/56, 잔여10개라는 **회계 추정**만 가능하다. 합성·LAB·포트 배치·STA 승인이 아니다. 제어 FF/주소 태그·원본 snapshot/CDC·매퍼 여유는 추가로 필요하다. 기존14M9K 여유를 이4개로 모두 해결했다고 보지 않는다. 세이브 SRAM은 사용하지 않는다.

다음은 일반 버퍼 시험을 더 늘리는 것이 아니라 실제 데이터 경계 연결이다.

1. 현재 수집기의 compact/CHR 읽기 포트에서 고정된 원본 세대와 읽기 수명을 정의하고 host 도메인으로 인계한다. MCU가 같은 SPI로 이 버퍼를 채우는 방법은 목표 후보로 채택하지 않는다. CHR 식별은 bank/내용 세대/행 mapping을 포함한다.
2. SNES 클라이언트가 descriptor를 받아 이 창을 WRAM으로 bulk 읽고 기존 section/표시 경로로 소비하게 한다. 전송 완료와 화면 최종 ACK를 분리하고 음성·입력 서비스/STOP을 보존한다. raw·정상 전환과 대상 VRAM bank 기준도 유지한다.
3. 위 경계를 갖춘 최소 경로에서 사용자 RIGHT+B/A 절차의 실제 연속 스크롤 입력/출력을 같은 generation으로 얻는다. 안정된 패턴 재사용과 작은 snapshot/streaming, 현재SPI 유지 후보의 전체 서비스 예산을 비교한다. 긴 무변경 cold boot/FIT/044 재시험을 먼저 반복하지 않는다.
4. 16.67ms 처리량·메모리 수명·실제 FIT/IO 타이밍이 성립한 후보만 실기 짝패키지로 연결한다. 그전까지186을 유지한다. MMC4/5·CHR-RAM/상태 복원 시 cache invalidate 요구와 매퍼 계열별 구성 후보를 보존한다.

이번 구현은 미래 전송 경로의 후보이고 새게임 표시 경로는 아직 아니다. 지속60fps, 실기 속도 개선, 새 매퍼 호환성, 실제 CPU DMA 또는 NES→host CDC를 통과했다고 보고하지 않는다.
