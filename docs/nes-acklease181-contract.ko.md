# NES181 — ACK 저장 공간 공유와 실제 자원 측정

## 작업 의미

1813 압축 전송과 1815 SNES 표시 경로를 유지하면서, 호스트 응답의 중복 저장을 줄였다. 실기 코어를 FPGA에 배치하기 위한 자원·응답 소유권 구현이다. 전송량이나 실제 FPS가 늘었다는 결과는 아니다.

**기능 검사는 통과했다. 레지스터 96개와 필요 LAB 4개가 줄었지만, 전체 FIT는 973/963 LAB로 실패했다.** 배치·배선 완료, 타이밍 승인, 설치 패키지는 아직 없다. 새 실기 시험을 요청하지 않는다.

## 저장 수명과 호환성

`tools/nes_acklease181.py`는 hostlease181 map01의 69개 입력을 해시 확인 후 복사하며 `nes_sink_spi165.sv` 하나만 바꾼다. QSF·SDC·클럭·핀·시드, 압축 exporter/SPI, SNES ROM, ARM 코드는 그대로다.

- 별도 완료 저장소 `ack_held[95:0]`를 없애고 `ack_work[95:0]`를 작성 중과 완료 후에 이어 쓴다.
- sealed packet 동안만 ACK byte를 작성한다. publish는 기존 12비트 mask 완성을 요구하며 valid를 설정하고 sealed를 내린다. 새 E1 packet이 완료되면 valid를 내린 뒤 다음 ACK를 작성한다.
- E0의 120비트 스냅샷은 유지한다. 같은 edge의 이전 flags와 work를 함께 캡처하며, 이후 ACK 쓰기·publish가 진행돼도 해당 SPI 응답과 CRC는 바뀌지 않는다.
- **ACK valid가 0이면 12바이트 payload는 0이다.** 기존처럼 이전 ACK가 남아 있지는 않는다. valid일 때의 응답은 기준 구현과 byte 단위로 같다. 실제 `nes_sink_spi170.c`는 F6/CRC/flags 검사 후 valid일 때만 ACK를 복사하므로 무효 payload를 소비하지 않는다. 형식·버전·유효 ACK의 의미는 유지한다.
- E0 snapshot과 publish가 같은 edge이면 이전 sealed/invalid 상태와 0 payload가 전송되고, 다음 E0에서 새 ACK가 보인다. valid와 일부 새 byte가 섞이는 응답은 금지한다.
- 실제 SNES bus는 ACK byte와 publish를 서로 다른 pulse로 낸다. endpoint를 직접 사용하는 비정상 동시 입력도 고려해, 완성된 mask에서 byte 재쓰기와 publish가 겹치면 이전 work를 발행한다. 같은 edge의 마지막 byte를 완성 mask로 인정하지 않는다. 부분 publish·범위 밖 index는 기존대로 fault다.
- RUN loss/reset의 즉시 취소와 재시작 유휴 승인, graceful STOP 레지스터는 hostlease181 그대로다. 모든 fault를 raw 취소로 바꾸지는 않았다.

## 검증

SELECT `map01/test01`. `tests/nes-functional/acklease181_tb.sv`는 실제 endpoint와 이전 endpoint를 같은 SPI/ACK 입력에 연결한다. CPU·SPI master는 fixture이며 전체 게임 실행이 아니다.

| 검사 | 새 결과와 범위 |
|---|---|
| 실제 endpoint 비교 | 16 시작 오프셋 × publish가 snapshot보다 한 edge 전/동시/후 = 48 전송, 총 322 확인 |
| 상태 응답 | 부분 ACK, 전체 작성 후 미발행, 새 packet에 의한 이전 valid 철회, SPI 전송 중 ACK 작성, CRC, 유효 ACK의 기존 값 일치, 무효 payload 0 |
| 거부 경계 | 부분 publish, 잘못된 packet CRC, 범위 밖 ACK index, 재시작, 동시 write/publish의 이전 값 보존 |
| 실제 MCU 소비자 | RTL wire trace 48개를 수정 없는 `nes_sink_spi170.c`/`nes_sink_io170.c`에 재생, C가 요청한 TX bytes도 trace와 대조 |
| MCU 음성 대조 | 위 trace의 최종 CRC를 한 비트 바꾼 48개와 마지막 poll에서 guard를 거부한 48개: 실패하고 출력 ACK 버퍼 미변경. 이 두 부류는 의도적으로 변형한 fixture이며 원본 RTL 응답으로 세지 않음 |
| 변경된 endpoint의 hostlease 회귀 | 실제 SPI endpoint+SNES bus, 16 오프셋/128 완료/128 취소/912 확인. pending write·publish·status 중 취소, stopped-clock reset, graceful STOP, 재시작 포함 |

C와 RTL은 파일 trace로 결합했다. 실시간 공동 실행이나 실제 MCU/SNES 보드 검사가 아니다. 실제 65816 클라이언트는 변경되지 않아 stream181의 기존 결과를 재사용했으며 새 실행으로 집계하지 않았다. paired181 전체 ARM 여유 1,384바이트 결과도 변경 없이 유지한다.

## 합성 및 한 번의 전체 FIT

| 항목 | hostlease181 | acklease181 |
|---|---:|---:|
| MAP 추정 LE |19,895|19,819|
| MAP 전체 FF |8,643|8,547|
| MAP sink 전체 조합/FF |558/578|558/482|
| MAP endpoint 조합/FF |469/422|469/326|
| 실패한 FIT의 준비 LE |15,079|15,155|
| FIT 필요 LAB / 장치 한도 |977/963|973/963|
| M9K |38/56|38/56|

MAP에서 실제 FF 96개 감소를 확인한 뒤 통합 FIT를 한 번 실행했다. 조합 논리는 줄지 않았고, FIT 준비 단계의 LE는 오히려 증가했다. MAP 추정치·FF 수·LAB 포장·완료된 배선 수치를 서로 바꿔 해석하지 않는다. 두 FIT 모두 실패한 중간 자원 값이다. 새로운 STA/IO/ASM은 실행하지 않았으며, 이전 replyjoin의 setup −1.408ns 해결 여부도 아직 측정하지 못했다. 같은 후보의 seed·설정 반복은 하지 않았다.

## 다음 변경: 큰 OAM 저장 구조부터

이번 MAP에서 `OAMEval:spriteeval`은 조합 4,015개/FF 2,366개/M9K 0이다. ACK 같은 작은 제어 변경을 반복하기보다 primary OAM의 저장·읽기 포트를 재설계할 근거다. 이전 [OAM165 조사](nes-oam-port165-contract.ko.md)의 onehot-read, row-writer, enable 인식 OFF, 같은 AREA 재배치는 실패 자료로 유지하며 반복하지 않는다.

현재 선택 소스의 접근 조건은 다음과 같다. 아래는 **읽기 검토 결과이며 새 OAM RTL은 아직 없다.**

| 소비자/쓰기 | 현재 조건 | 다음 구조가 보존해야 할 것 |
|---|---|---|
| PPU main/CPU `$2004` | CE에서 `oam_read_addr`, `$2003` 쓰기 시 같은 cycle의 `oam_din` 주소 우선 | CPU 즉시 주소 변경, attribute E3 mask, non-render CPU write의 `oam_data` bypass |
| primary 행 복사 | rendering 상승, NTSC, secondary 선택 변화 때 8개 byte lane 동시 복사 | 원본 행의 pre-edge 값, 같은 행 복사, CPU/상태 저장 쓰기와 per-byte 우선순위 |
| sprite 평가/반복 판정 | Y 및 Y/tile/attr 다중 읽기 | `spr_counter`, `repeat_count`, overflow와 sprite0를 같은 PPU CE에 갱신 |
| extra sprite 읽기 | 확장 Y 검사와 4바이트 읽기 | 현재 보드에서 사용하지 않는 경로의 합성 제거와 일반 core의 의미를 구분; 기능을 몰래 삭제하지 않음 |
| native OAM snapshot | `nes_live_joint.sv`가 주소를 0에 고정, 새 collector는 평가된 geometry 사용 | 옛 매프레임 snapshot 비용을 현재 필수 포트로 오인하지 않음. 실제 fanout 제거 여부를 MAP에서 확인 |
| 상태 저장 포트 | 읽기는 별도 enable, 쓰기는 CE 밖에서도 가능 | 현재 연결/합성 결과와 미래 savestate 계약 구분. 두 쓰기를 무조건 한 우선순위로 바꾸면 서로 다른 주소의 동시 갱신을 잃을 수 있음 |

`rtl/nes.v`의 PPU CE는 divider 비교이며 freeze/skip 경로도 있다. 따라서 “항상 남는 클럭이 있다”는 가정만으로 동기 RAM을 넣지 않는다. 다음은 실제 core의 `$2003/$2004` 주소·CE·freeze 시점을 포함한 소비 시간표를 만들고, primary lane RAM의 사전 읽기/우회 경로가 기존 값을 같은 CE에 제공하는지 검사한다. CE 사이 주소 안정성이 입증되지 않은 포트는 그대로 둔다. 원본과 cycle별 상태/행 복사 비교 및 실제 SMB3 소비 경계의 짧은 재생을 통과한 뒤, 큰 자원 절감이 MAP에 나타나는 후보만 전체 FIT로 진행한다.

고정된 60fps 목표는 유지한다. OAM 구조 변경은 내부 RAM을 쓰더라도 게임/PPU를 느리게 하지 않고, save SRAM을 건드리지 않으며, 전송 압축도 유지해야 한다. 남은 raw 송신 하한 약22ms 모델과 capture lease는 별도 미완료 항목이다. 자원·타이밍·조건부 IO가 통과하면 paired ARM/1815 SNES와 SMB3 숫자1 타일→A 실기로 간다. 배포180/GBC164/세이브/기존 archive는 보존한다.
