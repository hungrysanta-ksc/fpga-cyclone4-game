# 660 · 한 번의 PSRAM 허가로 BG 두 바이트 공급

657과 같은 ARM·65816·두 staging 슬롯으로 두 시작 위상 모두 954·955를 각각 3 VBlank에 표시했다. 905–957 연속 일정의 마지막 ACK는 33.044 / 16.408 ms 앞당겨졌다. Cyclone IV 전체 FIT에 성공했다. 배치 후 168 MHz reader setup이 −1.038 ns여서 실기 기준은 MMC643으로 유지한다.

## 교체한 경로

- 657 port 보드의 loader가 128 KiB CHR을 적재하면서 한 행의 plane 0·1을 같은 16비트 PSRAM word에 배치한다. CPU·PPU·CHECK에는 원래 NES 주소 순서대로 한 바이트를 돌려준다. 기존 256 KiB PRG와 CHR을 합친 적재량은 384 KiB다.
- ARM이 발행한 BG short plan의 CRC와 세대를 plan decoder에서 확인한다. tile 생산기는 기존 검사 응답을 첫 바이트로, 같은 응답에서 보관한 옆 lane을 둘째 바이트로 공급한다. staging이 찰 때에는 수락될 때까지 값을 유지한다. 일반 BG 및 OBJ는 원래의 주소 로직으로 공급한다.
- cache가 수락한 주소·세대를 물리 응답 또는 STOP drain까지 소유한다. 이 경로에서 arbiter의 중복 보관을 제거하고 응답 주소 검사와 세대 검사를 유지했다. 기존 묶음 DMA와 credit·최종 ACK 순서는 그대로 썼다.

## 동작 및 일정

| 비교 항목 | 위상 1 | 위상 2 |
|---|---:|---:|
| 954 BG 10개 실제 허가, 657 → 660 | 160 → 80 | 160 → 80 |
| 955 BG 9개 실제 허가, 657 → 660 | 144 → 72 | 144 → 72 |
| 954 / 955 표시 간격 | 3 / 3 VBlank | 3 / 3 VBlank |
| 954 SEAL 여유, 648의 직전 표시 기준, 657 → 660 | 1.658 → 1.523 ms | 1.592 → 1.234 ms |
| 951–955 평균 표시 간격, 657 → 660 | 53.281 → 53.244 ms | 53.249 → 53.244 ms |
| 957 최종 ACK, 동일 시작 기준 master clock, 657 → 660 | 68,589,578 → 67,879,890 | 68,589,458 → 68,237,054 |
| 951 공개선 / 957 최종 추가 대기 | 239 / 0 | 239 / 0 |

물리 RTL 시험에서 실제 loader로 393,216 B를 적재해 전체 메모리와 독립 원본을 대조하고, 원주소 CHECK 96회와 core PRG·CHR 읽기를 확인했다. 원래 묶음 순서·목적지·payload와 121개 chunk 9,072 B가 모두 일치했다. RTL의 53세대 BG 허가 주소·순서도 양 위상 연속 일정과 일치했다. 총 BG 허가는 4,240→2,144회, OBJ ROM 허가는 128회였다. CPU 연속 일정에서 OBJ 캡처 적중은 1,200회다. 물리 staging 시험에서는 캡처를 비워 OBJ의 원본 복구 경로도 사용했다.

53개 화면 각각의 RGB와 map을 기준 파일에 대조했다. 두 슬롯·독립 수락·최종 ACK를 확인했고, 부분 BG 쓰기 중 STOP, 둘째 바이트 직전 STOP, 늦은 응답 차단, 잘못된 주소·세대 거부와 cold 재시작을 검사했다. 같은 ARM에서 정상 menu 준비·해제, base 복구 및 네 가지 실패 시 해제 차단을 확인했다. ARM은 212,508 B로 Flash 여유 484 B다.

연속 일정에는 링크한 ARM·65816, SPI·IRQ 서비스 모델, 부팅 실측에서 얻은 ROM 허가 달력을 사용했다. 물리 핀/RTL 시험과 CPU 일정은 별도 실행으로, 전체 grant 순서와 DMA 바이트로 연결했다. 둘째 바이트는 추가 ROM 대기 없이 공급하며 기존 타일별 staging 서비스 비용은 유지한다. 밀집 표시 간격은 거의 같고 957 ACK 이득은 53세대 누적값이다. 실기 FPS는 MMC643에서만 측정했다.

## Quartus Lite 전체 보드

| 회로 | LE | LAB | FIT |
|---|---:|---:|---|
| 657 port | 15,425 | 977 | 실패 |
| word 반환 + 기존 BG 캐시 | 15,436 | 974 | 실패 |
| byte/word 응답 공유 | 15,419 | 975 | 실패 |
| 최근 word만 캐시 | 15,332 | 969 | 실패 |
| 형제 byte만 캐시 | 15,376 | 971 | 실패 |
| 핀에서 주소 변환 | 15,295 | 969 | 실패 |
| tile에서 두 byte 연속 공급 | 15,293 | 967 | 실패 |
| 검증된 short plan 판별 재사용 | 15,222 | 965 | 실패 |
| 요청 주소·세대 보관까지 공유 (660 owner) | **15,331** | **963** | **성공** |

EP4CE15F17C8는 15,408 LE·963 LAB·56 M9K다. 최종 배치는 조합 함수 14,479개, 레지스터 8,370개, 305,264 RAM bit, M9K 56개를 쓴다. 남은 77 LE는 이미 사용 중인 LAB 안에서만 쓸 수 있다.

전체 STA 최소 slack은 setup −1.038, hold +0.148, recovery +0.824, removal +0.370, minimum pulse width +2.635 ns다. 최악 경로는 slow 85°C에서 168 MHz 물리 reader의 state[0] → state[0]이고 해당 클록의 setup TNS는 −5.830 ns다. 같은 corner의 84 MHz에도 −0.159 ns가 있다. 새 8비트 반환 CDC의 세 corner 최저 slack은 +21.836 ns, ROM_OE / ROM_1CE / ROM_2CE는 각각 +1.397 / +3.130 / +3.366 ns다. MMC643 전체 setup은 +0.333 ns였다. SOF를 생성했고 실기 ZIP은 보류했다.

## 재현 및 다음 작업

1. 657 port 전체 보드에서 `tools/prepare_nes_owner660.py BASE OUT`으로 최종 RTL·제약을 생성한다. Quartus Lite A&S 후 `tools/bind_nes_bg659_sdc.py OUT`으로 실제 병합된 FF 이름을 바인딩하고 같은 프로젝트에서 전체 compile·STA를 실행한다. 보드 입력 64개가 재생성 결과와 바이트 단위로 일치했다.
2. 같은 보드를 `tools/check_nes_word660.py --decoded`와 `tools/check_nes_word660_guards.py --policy short`에 넣는다. 657 port sender와 654 combined ARM, 637 client를 `tools/test_nes_word660.py --emit`에서 시작 7,288,416 / 7,467,100 master clock으로 재생한다. `tools/analyze_nes_word660.py`가 grant·payload·화면·마감·FIT·STA 보고서를 대조한다. [수치·입출력 해시](../analysis/word660-verification.json)
3. 다음 수정 범위는 168 MHz reader의 상태 전이와 84 MHz 위반 경로다. ROM 핀·반환 CDC·STOP을 지키며 전체 코너에서 setup을 닫고, 양 위상의 3 VBlank·957 ACK를 다시 대조한 다음 실기로 넘긴다.
