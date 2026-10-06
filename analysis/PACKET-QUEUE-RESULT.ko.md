# Packet 소유권 RTL와 보드 클록 경로 — 027

2026-10-05. 후보 NES-R2-PACKET-QUEUE-027, NES core 구현 NES-P2-RDY-014 유지.
기존 FLOAT 경로로 새 원본 RTL을 Questa에서 실제 컴파일·실행했다.
최근 실제 SNES 화면 검증은025, NES CPU 기능017, 자원018이다.
이번 단독 RTL에는 upstream NES CPU/PPU를 넣지 않았고 새 Mesen/Quartus/실기 실행도 없다.

## 보드 클록 확인

변경하지 않은 소스와 제약을 해시·행 번호로 고정했다.

| 경로 | 정적 근거 | 판정 |
| --- | --- | --- |
|보드 CLKIN|pin.sdc:1,125ns; 두 PLL inclk 입력|선언 기준8MHz, 실제 oscillator 계측 아님|
|GBC core|gbc_pll0.v:107/109,151/36|CLKIN에서 생성|
|bus|gbc_bus_pll0.v:107/109,21/2|CLKIN에서84MHz 생성 선언|
|SNES PHI2|fxpak_gbc_top.sv:146 → full_core_link.sv:218 → snes_frontend → snes_sram_slots|2단 phi_sync로 받는 비동기 입력|
|NES CPU/PPU|upstream rtl/nes.v:230/231|입력clk의12/4분주 enable|
|기존 NES 시험|rdy_tb.sv:4,반주기23.280423ns|테스트벤치가 만든46.560846ns 클록|

현재 GBC 보드 경로가 NES/SNES를 공통 시계로 묶는 근거는 없다.
NES 보드 PLL/enable 연결은 아직 구현하지 않았다.026의 상대 속도 누적 문제를 닫지 않는다.
기존 GBC PLL·타이밍 제약·코어를 변경하지 않았다.
새 큐 시험의10ns 클록은 프로토콜용이며100MHz 보드 타이밍 통과를 의미하지 않는다.

## 원본 RTL 구현

src/nes/nes_packet_queue.sv는 MIT 원본이다. 한 클록에서3KiB×2개의 payload 저장소를 제공한다.
각 slot은 FREE→WRITING→READY→READING→FREE로 바뀐다.
producer가 길이/epoch/sequence로 begin한 뒤 바이트를 순서대로 쓰고,
선언한 길이만큼 모두 썼을 때만 publish할 수 있다.
consumer acquire는 READY 전에는 대기 응답이며 읽기를 허용하지 않는다.
정확한 epoch/sequence와 순차 주소를 가진 요청에만 등록된 data_valid가 나온다.
모든 바이트를 읽고 명시적 commit을 보낸 뒤에만 slot이 반환된다.
외부에서 실제 SNES PPU commit 이후에 이 commit을 보내는 연결은 아직 없다.

0길이/3072초과 길이, 잘못된 세대·순번, 조기 publish/commit, 초과 쓰기·잘못된 읽기,
두 slot 점유 중 재할당을 거부한다. 다른 slot의 쓰기와 읽기는 동시에 가능하다.
같은 에지에 반환되는 slot을 바로 재할당하지 않고 다음 에지부터 허용한다.
reset은 동기식이며 metadata와 유효 상태를 비우고, RAM 내용은 지우지 않는다.
reset_epoch는 상위 reset 관리자가 새 값으로 제공해야 한다.
오래된 요청이 살아 있는 동안 epoch를 재사용하면 보호를 보장할 수 없다.
16비트 sequence가65535를 지나0이 되면 새로운 begin/acquire를 거부한다. 세대 교체 절차와 wrap 장기 시험은 미완료다.

## 실제 실행과 재검증

| 항목 | 결과 |
| --- | ---: |
|Questa compile / simulation|성공 /14 case PASS|
|accepted byte writes|10,492|
|비교한 read bytes|10,460,전부 일치|
|완료 commit|68|
|서로 다른 slot 동시 write/read 에지|2,008|
|리셋으로 취소한 미소비 bytes|32|
|시험 cycle|38,510|

실제 기존 split2328B/sprite2052B/resident2008B packet을 그대로 hex 입력으로 만들었다.
최대3072B는 원본 생성 pattern으로 경계를 시험했고,64packet 반복 재사용을 추가했다.
14조건은 빈 큐 대기,길이 경계,producer token,미완성 publish,
두slot 점유,consumer token/조기commit,split 무결성/소유권,
동시 읽기·쓰기,resident 무결성,WRITING/READY/READING 중 reset,최대길이/덮어쓰기 방지,64회 재사용이다.
정상 완료와 reset 취소를 구분한다.32B 차이는 의도적인 reset 시험이며 정상 frame 삭제가 아니다.

Python 검증기가 ownership.tsv를 다시 파싱해 상태 전이와11종 오류 코드 관측,
전체 바이트열,68commit 및2008동시 에지를 별도로 확인했다.
초기 Python 기대열은 반복 시험의 fixture2를 생성 pattern으로 잘못 해석했다.
실제 TB의 fixture2는 resident packet 앞3B이므로9461..9463 위치3B가 달랐다.
기대열만 고쳤고 전체10460B 비교는 유지했다. RTL/TB/실행 기록은 변경하지 않았으며 초기 실패와 소스를 보존했다.
simulation 종료코드뿐 아니라 명시적 PASS와 Fatal/Error 부재를 모두 요구했다.

## 범위와 다음 연결

이 블록은 opaque packet transport다. NCR1/NSP1/NBP1 header나 palette/CRC를 해석하지 않는다.
상위 consumer는 기존 packet 검증을 유지해야 한다. 3KiB×2는 이 prototype의 배치이며 제품의 최종 FIFO 깊이가 아니다.
FPGA RAM 합성/M9K·LE/배치/STA는 아직 측정하지 않았다.
producer frame scratch,source assembler,비동기 CDC,외부 SRAM/PSRAM,SNES 주소/레지스터 frontend,
CPU ready polling과 실제 DMA commit 연결은 미구현이다.
consumer_active는 내부 읽기 소유권 신호이며 SNES PPU DMA를 실제로 구동한 결과가 아니다.

다음은 epoch/sequence/length를 안정적으로 전달하는 CDC와 SNES ready-gated frontend를 붙이고,
reset 중 요청/응답 및 실제 준비 대기 후 소비 시간을 검증하는 일이다.
026 속도 차이에 대한 clock/enable 전략,025CHR/023OBJ 겹침과024patch 결합을 함께 추적한다.
이후018 자원 구성에 통합 비용을 넣는다. 동시240줄/최종색/DMC/SMB3/실기 및 HDL 반입 hold는 남아 있다.
GBC C44/0.9.0, 기존 core014, upstream과 원본 probe를 보존했다.

[RTL 검증 JSON](packet-queue-verification.json), [클록 감사](packet-queue-clock-audit.json),
[재현 계약](../docs/nes-packet-queue-contract.md), [증거 목록](packet-queue-artifacts.json).
