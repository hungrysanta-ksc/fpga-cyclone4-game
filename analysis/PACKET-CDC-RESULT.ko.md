# Packet 요청·응답 CDC — 028

2026-10-05. 후보 NES-R2-PACKET-CDC-028. NES core014, 실제 SNES025, CPU 기능017, 자원018 유지.
027 큐를 변경하지 않고 consumer 요청/응답을 다른 클록으로 연결하는 원본 RTL을 구현했다.
기존 Starter FLOAT 경로에서 실제 Questa3실행,각13조건을 통과했다.
새 NES CPU/PPU,Mesen,Quartus 또는 실기 실행은 아니다.

## 구현과 연결 범위

src/nes/nes_packet_cdc.sv의 queue_clk 쪽은027 큐와 producer 입력을 구동한다.
host_clk 쪽은 cmd_valid/ready와 rsp_valid/ready로 acquire/read/commit을 요청한다.
한 요청만 outstanding으로 허용한다. 요청 필드는 응답 도착까지 고정하고,
2단 동기화한 toggle을 관측한 뒤 queue가 처리한다.
응답도 별도 held data와 동기화 toggle로 돌아오며 host가 받아 갈 때까지 유지된다.
multi-bit data를 각 bit마다 따로 동기화하는 구조가 아니다.

acquire가 READY 전에 도착하면 accept0/error0의 대기 응답이다.
성공한 acquire 응답에서 길이를 전달하고 host_read_owned 상태를 세운다.
완료 전 commit,잘못된 세대·순번·주소는027의 검사를 거쳐 거부한다.
응답을 받지 않은 동안 다음 명령은 수락하지 않으며, 입력 핀이 바뀌어도 이미 받은 요청은 바뀌지 않는다.
rsp_data_valid와 기타 payload 필드는 반드시 rsp_valid/ready와 함께 해석한다.
host_read_owned는 논리적 소유권 상태이며 실제 SNES DMA 시작 신호나 물리 버스 허가가 아니다.

reset은 양쪽에 함께 걸리는 비동기 assert이고, 각 도메인에서2에지 release한다.
상대 도메인의 release도 동기화해 확인한 후 host 명령을 수락한다.
큐 자체는027의 동기 reset이며 클록 재개 후 로컬 release 전에 초기화된다.
상위가 reset_epoch를 새 값으로 주고 큐 초기화까지 안정적으로 유지해야 한다.
단독 endpoint reset이나 epoch 재사용/롤오버를 지원하는 완성 reset 프로토콜은 아니다.

## 실제 검증 결과

| queue/host 주기와 host 시작 위상 | 시나리오 | 읽기 바이트 | 응답 수 | accepted read 응답 지연 min/median/max |
| --- | ---: | ---: | ---: | --- |
|10ns/14ns,위상3ns|13 PASS|6405|6426|84/98/182ns|
|14ns/10ns,위상1ns|13 PASS|6405|6426|90/100/160ns|
|10ns/22ns,위상9ns|13 PASS|6405|6426|110/132/264ns|

13개 고유 시나리오를3조합에서 실행한39회이며39개의 별도 기능을 뜻하지 않는다.
총19,215 read bytes를 raw trace에서 다시 연결해 기존 split2328B,sprite2052B,resident2008B와
reset 후 새17B pattern에 정확히 비교했다.
각 실행마다 요청6428,queue처리6427,host수락응답6426,정상commit4회를 관측했다.
reset이 취소한 요청은2개이며, 그중 하나는 queue가 읽었으나 host가 아직 받지 않은1B 응답이었다.
이 취소는 의도적인 reset 시험이며 정상 frame 삭제가 아니다.

검사한 조건은 빈 큐 대기,부분쓰기 publish 전 대기,세대/순번 오류,
held request와 response backpressure,조기commit/주소 오류,
다른slot 동시producer 및소유권유지,세종류실제packet,
요청전달중reset,보류응답중reset,queue clock정지,host clock정지,
두clock정지중공통reset,새세대복구다.
host의 입력을 요청 수락 후 일부러 잘못된 값으로 바꾸고,
응답 대기 중 추가 valid를 넣어도 기존 요청/응답이 유지되는지 검사했다.

검증기는 R(request),Q(queue result),H(host accepted response),X(reset)를 일대일 대조한다.
tag/op/address/data/error를 연결해 중복·누락·reset후stale 노출과 실제 읽기 바이트를 검사했다.
지연은 요청 수락부터 host가 응답을 받아 간 시점까지다.
최대값에는 의도적인 backpressure가 포함되고 테스트벤치의 요청 간격도 존재한다.
현재 보드의 서비스 속도나 SNES DMA 기한으로 환산해 통과를 주장하지 않는다.

## 실패 기록과 재현

첫 시도는 테스트벤치의 stopped-host receive 호출에 인수가 하나 많아 compile에서 실패했다.
초기 TB와 compile 로그를 보존하고 불필요한 마지막 인수만 제거했다.
CDC RTL은 변경하지 않았으며 두 번째 compile 뒤3개 simulation이 모두 통과했다.
라이선스 문제나 시뮬레이션 실패를 smoke 성공으로 대체한 것이 아니다.
현재 verifier는 모든 source/input/output hash와 실제 PASS,Fatal/Error 부재를 확인했다.

## 남은 경계와 다음 작업

이는 디지털 RTL에서의 논리적 CDC 검증이다. async_reg 선언과2단 control 동기화만으로
물리 metastability/MTBF 또는 bundled data 경로의 지연·skew를 증명할 수 없다.
실제 배치의 held data 도착,제어 동기화 경로,reset release/최소 pulse,clock 정지 복귀 제약을 정하고 STA/CDC로 확인해야 한다.
공통 reset만 시험했으며 독립 endpoint reset은 지원하지 않는다.

SNES 주소 디코더/MMIO,CPU의 ready polling,고정 시간 DMA read data 제공,
외부 SRAM/PSRAM,NES source assembler와 최종 PPU commit은 아직 연결하지 않았다.
027의3KiB×2payload와028의1outstanding 왕복은 prototype이며 최종 burst/FIFO 구조를 정한 것이 아니다.
바이트별 왕복으로 실제 SNES 버스의 고정 응답 기한을 충족한다고 가정하지 않는다.

다음은 host 측 명령/상태 레지스터와 read staging/prefetch를 붙여
SNES가 준비된 바이트만 DMA로 읽게 하는 frontend를 구현하고,
실제 준비 대기·전송 기한을 재측정하는 일이다.
026의 공통 clock/enable 전략,025CHR/023OBJ VRAM 충돌 및024patch 결합을 유지하고
018 자원/타이밍 구성에 통합 비용을 추가해야 한다.
GBC C44/0.9.0,core014,027큐,upstream을 보존했다.
동시240줄/최종색/DMC/SMB3/전체board fit·STA/실기/HDLhold는 미완료다.

[검증 JSON](packet-cdc-verification.json), [재현 계약](../docs/nes-packet-cdc-contract.md),
[증거 목록](packet-cdc-artifacts.json).
