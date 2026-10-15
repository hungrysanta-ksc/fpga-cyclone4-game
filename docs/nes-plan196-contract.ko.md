# NES196: 작은 RAM을 통한 타일 계획 전달

## 작업 의미와 범위

MCU가 픽셀을 다시 복사하지 않고 FPGA가 계획에 따라 타일을 생성하여 SNES로 직접 전송하는 경로를 연결한다. 이번 범위는 C 계획 인코딩 → 32바이트 dual-clock RAM → NES 측 해석 → 실제192 READ16/타일 생성 → 193 카트리지 읽기창이다. 디버그 확장이 아니라 데이터 전달 구현이다. 생산 SPI 명령, descriptor 취득, 프레임 epoch/controller, 실제 C runtime 호출 및 전체 board 연결은 남았다. 배포186과 GBC164, 세이브 SRAM은 변경하지 않는다.

## Version1 형식

모든 다중 바이트 정수는 little-endian이다. payload 길이는 `16 + 2*popcount(alt_mask)`, 최대32바이트다. CRC16 CCITT-FALSE(poly1021, initFFFF)는 payload 전체에 적용하고 framing에서 별도로 전달한다.

| 위치 | 의미 |
|---|---|
| 0 | kind: BG0 / OBJ1 / zeroBG2 / END3 |
| 1 | alternate-row bitmap |
| 2–3 | generation16 |
| 4–5 | slot10, 나머지0 |
| 6–7 | tag13, 나머지0 |
| 8 | pixel row mask |
| 9–14 | 16개3bit row를48bit little-endian으로 배치 |
| 15 | version=1 |
| 16 이후 | bitmap의 낮은 행부터 alt tag13, 각2바이트 |

BG는 slot!=0/mask255, OBJ는 slot<128/mask!=0/alt 없음. zeroBG와 END는 generation/version을 제외한 모든 필드0. C 입력 alt=FFFF는 부재를 뜻한다. 잘못된 길이·CRC·예약 비트·version·형태·generation은 출력 전에 거부한다. END는 tile engine으로 보내지 않는다.

## 소유권과 취소

payload RAM은 reset하지 않는다. 길이6bit mailbox만 CDC를 통과하며, seal 검증 후 NES가 모든 필드를 복사할 때까지 host의 덮어쓰기를 금지한다. 해석된209bit 필드는 plan handshake부터 tile_done 또는 common cancel까지 유지한다. 이후 host가 다음 계획을 RAM에 쓰더라도 현재 타일 계획은 변하지 않는다.

191/192의 `EXTERNAL_PLAN=1`은 이 유지된 필드를 사용하여 내부 복제 레지스터를 제거할 수 있게 한다. 기본값0은 기존 동작이다. 합성 제거와 자원 절약은 아직 MAP/FIT로 측정하지 않았다. 새32바이트 RAM은 M9K 사용을 요청하며 전체 FPGA 수용 가능성을 보장하지 않는다. 세이브 SRAM이나 전체 프레임 계획 배열을 사용하지 않는다.

common reset/STOP/inactive/source fault는 양쪽 endpoint와 producer/consumer를 함께 취소해야 한다. 내부 hf/nf는 common reset까지 sticky다. 외부 source_fault의 지속/취소 소유권은 controller 책임이다. fault를 그 원인을 지우는 reset으로 바로 되먹임하여 오류가 자동 소멸하는 배선을 만들지 말 것. 독립 endpoint reset은 지원하지 않는다. deadline/STOP service는 상위 controller에서 유한하게 보장해야 한다.

다음 production 연결의 필수 조건:

- plan credit를 기다리는 동안에도 완성 chunk descriptor를 읽고195 op7/barrier를 서비스한다. 모든 계획 송신 완료 후에만 chunk를 비우면2KiB 버퍼와 plan credit가 서로 기다리는 교착이 생긴다.
- captured_epoch/geometry와 generation은 해당 계획 및 source lease가 끝날 때까지 고정한다.
- END 수신은 프레임 표시 완료가 아니다.193 end_sealed, 모든 chunk consume, 기존 sections/SEAL과 final display ACK까지 구분한다.
- 취소 후 fresh token/generation으로 재시작한다. consume 성공 뒤 ACK 유실 가능성이 있으므로 불명확한 op7을 재전송하지 않는다.

## 검증과 한계

선택 결과는 `probes/nes-plan196/test02`와 `evidence01`이다. test01은 byte15=0 중간 형식의 성공 기록으로 보존하되 선택하지 않았다. test02는 version1이며 실행 실패는 없었다.

- 실제 C191이 과거에 생성한97개 계획을 새 C encoder로 인코딩: payload1580바이트. 각 CRC2바이트 및 transport framing은 별도이며 END8개도 별도다.
- 8합성장면의 RAM decoder→192 실제 arbiter/READ16(70ns PSRAM fixture)→193 aperture 결과1840바이트가 기존186 변환 결과와 일치했다. scene7은 EXTERNAL_PLAN=0도 추가 확인했다.
- C268경계 검사, RTL273검사:256개 alt bitmap, 다음 계획 선기록 중 필드 유지,12개 잘못된 형식/CRC/길이, NES clock 정지 중 STOP, 부분 쓰기 취소, END 포함.
- 이전195의 실제 C→65816 검증은 재사용한다. 이번 시험에 실제 SNES CPU/SPI 또는 live game planner를 동시에 연결한 것은 아니다.

새 FW/FIT/STA/전체ARM/SD ZIP/실기 결과는 없다. 스크롤 `collected_runs`는 여전히 비어 있고 FPS·부하 감소율은 미측정이다. 다음은 production framing/descriptor/controller를 연결한 최소 수명 시험과 전체ARM/FIT/IO 확인, 이후 짝패키지 실기다. SMB3 tile1+A로 첫레벨을 확인한 뒤 RIGHT+B 유지/A press-release 반복의 연속 스크롤을 측정한다. 같은 generation의 생산·전송·고유 화면 완료 간격을 연결하여16.67ms 목표와 비교한다. 오프닝/정지장면이나 ACK 수를 FPS로 대신하지 않는다.
