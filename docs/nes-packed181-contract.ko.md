# NES1813 — FPGA 묶음 전송과 실제 C 수신기

## 결과와 작업 의미

오프라인 계산에 그치지 않고 실제 exporter·SPI와 C receiver를 짝으로 변경했다. 픽셀/짧은 행 정보의 묶음과 반복값 압축을 구현해, 기존 합성 장면의 FPGA→MCU 전송량을 약79~81% 줄였다. **60fps에 필요한 전송량을 직접 줄이는 구현 작업**이다. 현재 수집·표시 구조를 그대로 둔 채 FPGA 배선만 최적화한 결과와 구분한다.

선택 결과는 `probes/nes-packed181/evidence/test02`다. 전체 보드/FIT/ARM link·SNES 갱신·실기 FPS 승인은 아직 없고 설치 ZIP도 없다. 현재 배포180·GBC·164복원본·세이브SRAM은 변경하지 않았다.

## 실제 SPI 전송 비교

| 같은 fixture | 기존 wire181 | 묶음1813 | 감소 | 새 RTL 모델 시간 |
|---|---:|---:|---:|---:|
| raw0행 |4,861B|922B|81.0%|2.994ms|
| raw1행 |6,559B|1,311B|80.0%|4.244ms|
| raw7행 |16,774B|3,486B|79.2%|11.097ms|
| 추가32group/1,056map·7raw행 |비교 fixture 없음|3,542B|비교하지 않음|11.275ms|

기존7행 시간은53.164ms다. 같은 SPI 속도2.625MHz와8µs transaction gap 모델에서 비교했고 새 속도 가정을 넣지 않았다. 데이터/명령/CRC/상태·POP/ACK 전송이 포함된 실제 bench byte 수다. MCU 실행시간·SNES 송신/표시와 실제게임은 포함하지 않는다. PPU/PSRAM 조회 데이터는 합성 fixture이며 같은 map과 raster값 반복이 많다. 실제 SMB3에서79% 절감 또는60fps를 보장하는 수치가 아니다.

첫 test01은 기능상 통과했으나7행9,183B/225block이었다. 기존 SPI는 kind7의0번 외 모든 record를 종료 제어로 처리해 버퍼를 닫았다. 새 묶음까지 매번 닫아 왕복이 늘어난 것이다. test02는 낮은 제어 index만 강제로 닫도록 수정했고,7행14block이 됐다. test01도 원시 근거로 보존하며 최종 선택하지 않는다.

## 형식과 데이터 수명

FPGA→MCU BEGIN version은 **0x1813**이다. 기존1811 receiver/exporter와 혼용하지 않는다. SNES 쪽1812/SEAL24는 변경하지 않았으며 수신 결과 구조체/API는 기존과 같다. 이전 오프라인 codec의 비트 순서를 그대로 채택한 것도 아니다. 실제 구현은 쉬프트 레지스터 비용을 줄이기 위해 아래 순서를 쓴다.

96비트 내부 record와 기존 SPI 폭표를 유지한다. 상위 kind3bit·generation16bit·index13bit·value64bit이며, kind7은 wire에서12B다.

| 형식 | index | payload 및 검증 |
|---|---|---|
| 기존 제어 |0 BEGIN,1 END,2 ABORT,3 COMMIT,4 CHR_END|새 BEGIN 버전, 나머지 소유권/완료 조건 유지|
| 같은 값 반복 |`0x0800 \| kind<<8 \| (count-1)`|kind0/2/3/4, count2..256, value는 원래 값; 현재 kind의 다음 index부터 확장|
| 짧은 값 묶음 |`0x1800 \| kind<<8 \| (count-1)`|kind1/5, 최대8개 byte, 첫 항목이 사용 payload의 가장 높은 byte; 남는 상위 bit0|
| raw 픽셀 묶음 |`0x1000 + 시작픽셀`|상위4bit 개수1..10, 하위60bit 색6bit씩, 첫 항목이 사용 payload의 가장 높은6bit; 남는 bit0|
| 단일 값/CHR |기존 kind0/2/3/4 또는 kind6|기존 index/value 검사; raw 단계의 단일kind6은 거부|

짧은 값/raw의 개수는 `min(최대묶음, 남은항목)`과 정확히 같아야 한다. count0/초과/비정규 짧은묶음/패딩/단계/세대/순서/구버전/잘못된 token은 실패한다. 모든 복원 항목은 기존 logical record 검사 경로를 통과한다. CHR_END의 geometry 완결·missing0·lane0·raw slot 검사를 유지한 뒤에만 required bitmap을 raw scratch로 전환한다. **END의 records/bytes는 압축 전 논리 개수**다. 물리 record 수로 바꾸면 안 된다.

FPGA는 기존 `held_data[63:0]`를 반복값/byte묶음/raw묶음에 재사용하고 `pack_count[8:0]`만 상태로 추가했다. 같은 값의 run이 끊기면 다음 값을 별도64비트 레지스터에 보관하지 않고, 앞 run을 전송한 후 같은 index를 다시 조회한다. 이는 sealed lease가 불변이라는 기존 계약에 의존한다. lease/enable/세대가 무효가 되면 기존 ABORT 우선 처리를 한다. tx stall 동안 묶음은 그대로 유지한다.

SPI는 `kind7 && index!=0 && index<0x800`인 제어에 대해 강제 seal한다. 확장 묶음은 일반 데이터처럼 기존256B buffer에 모으고, 공간 한도/END/ABORT/COMMIT/CHR_END에서 닫는다. 기존 CRC·token·read/pop·prepared ACK·COMMIT 소유권은 그대로다. 추가 전송 buffer나 세이브SRAM을 만들지 않았다.

## 검증과 자원 범위

- 실제 기존 fill + 새 exporter + 새 SPI RTL, C poll/prepare/packet 경로의4장면 통과. 총3,840 raw픽셀과 최대256반복 run·1,056map을 포함한다.
- Python 독립 기준 압축과 실제 RTL의 **모든96bit record** 일치. 원래0/1/7행은 기존 C 수신기와 전체18,064B 구조체가 동일하다. 전송 block 수에 따라 달라지는 token 두 필드만 정규화했다. 추가32group 장면은 map/rows/raster/palette/object/exception/CHR/raw 및 논리 개수를 실제 C에서 검사했다.
- C 수신/전송 오류·구버전/잘못된 run·byte묶음·raw·논리 END·조기COMMIT·ABORT 후 재시작 등 총677확인. tentative 픽셀은 노출하지 않는다.
- 실제 exporter의 별도8경우: 불규칙 backpressure, raw 중간 query miss/잘못된 색, lease 상실, disable, stall deadline, 멈춘 전송 중 reset,5픽셀만 모인 partial buffer reset. 모두 완료 또는 의도된ABORT/해제를 확인했다. fill은 이 취소시험에서 stub이고, 별도4장면 결합시험에서는 실제 fill을 썼다.
- ARM ABI18,064B 유지. 새 frame buffer 없음. object-only stack 보고에서 poll→packet→logical_record→require_tile 경로는664→704B로40B 증가했다. 전체 ARM link/IRQ 여유를 새로 승인한 결과가 아니며 기존1,032B 여유를 그대로 적용하지 않는다.
- 압축 packet은 같은256B에서도 더 많은 논리 항목을 복원한다. 한 run은 최대256항목으로 제한했지만, MCU 실행시간과 guard/service 사이 최악 지연은 이번 RTL wire 시간에 포함하지 않았다. 다음 전체 ARM 연결에서 가장 조밀한 packet의 처리시간도 확인해야 한다.
- 소스 수준 추가 상태9bit는 물리 FF/LE 증가량이 아니다. 비교/누적/주소·SPI seal 논리도 바뀌었으므로 전체 자원·타이밍은 새 통합에서 확인해야 한다. 현재963/963LAB의 기존 후보에 바로 들어간다고 주장하지 않는다.

원시454파일을 해시 보관했다. 완료된 wire181/client181/cadence181/replyjoin181 결과를 수정하지 않았다. 기존 긴 부팅/게임 replay/FIT는 반복하지 않았다.

## 60fps를 위해 남은 작업과 다음 경계

이번 구현은 기존 대량전송을 줄였지만 **프레임 수집 lease와 SNES 전체표 송신은 그대로**다. 7행 ingress 모델11.097ms만으로16.667ms의 대부분을 쓰고, 정상0행도 약2.994ms로 다음 capture 시작까지의 참조 간격2.401ms보다 길다. 서로 다른 fixture의 SNES 시간을 더해 종단 실측으로 해석하지 않는다. 현재 상태를60fps로 선언할 수 없다.

다음은 MCU→SNES 쪽 map/CGRAM/OAM/HDMA·작은 CHR callback 송신을 줄이는 실제 C/sink/client 경계다. 전송량/packet 수뿐 아니라 아래 제약을 함께 만족해야 한다.

1. **메모리 안에서 가능한 방식부터 선택:** ARM에 또 하나의16KB plan/cache를 추가할 공간은 없다. 기존 BG key는 raw staging에 덮어쓰므로 영구 이전프레임 cache로 쓰면 안 된다. 대상 bank 기준 generation/dirty 추적의 저장 위치·수명을 먼저 명시한다. 이전 복사본이 없어도 가능한 lossless section 묶음은 대안이지만, 그 자체를 차분 갱신이라고 부르지 않는다.
2. **SNES raw 매프레임 full-bank rebuild 제거:** 작은 변경은 유효한 기준 bank에서 변경분만 한 vblank에 적용하고, 큰 scene 전환/기준 상실만 기존 안전한 inactive-bank keyframe으로 복구한다. CGRAM/OAM/3HDMA와 raw CHR까지 일관된 최종공개·ACK·STOP 계약이 필요하다. 현재 SNES 본문은3,768/3,776B이므로 decoder 코드 공간도 실제 확보해야 한다.
3. **capture/export 겹침:** FPGA COMMIT release와 MCU display ACK release를 분리해 유지하고, 다음 수집을 막지 않을 snapshot/row streaming 포트·용량을 계산한다. 단순 압축만으로 이 조건이 해결됐다고 하지 않는다. 새로운 버퍼 수명은 이후 hostRUN/STOP 활성 경계에도 그대로 적용한다.

위 공동 설계에서 바뀐 최소 경계를 검증한 후 한 번의 정당한 보드/ARM/FIT/조건부IO, SMB3 숫자1+A 실기로 진행한다. 실제 화면 지속·오디오·표시 간격과 source frame 누락을 확인한다. 모든게임 최적화까지 기다리지는 않되, 느린 복구판을 내면60fps 미완료를 명시한다. AV→장기플레이·오류/리셋로그→입력유지 순서 유지.

## 재현

`tools/nes_packed181.py --out <새경로> --spi-source <고정된 기존SPI소스>`가 실제 후보3소스+동일header를 생성한다. `tools/test_nes_packed181.py`는 이전 wire181 원시 근거를 workspace에서 읽어 검사한다. 기존 FLOAT wrapper를 `-RunOnly -AfterSmokeScript <절대작업스크립트>`로 사용한다. 완료 경로에는 덮어쓰지 않는다.

[검증 데이터](../analysis/packed181-verification.json) · [전체 성능 계약](nes-cadence181-contract.ko.md) · [현재 인계](../cores/nes/HANDOFF.ko.md)
