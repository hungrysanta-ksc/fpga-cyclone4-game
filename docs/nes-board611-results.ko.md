# 611: BG 이력 보존과 실제 보드 캡처·해제 연결

## 목표

610의 OBJ bulk 뒤 map 발행과 608 팔레트 DMA를 그대로 유지하고, 기존 BG 캐시의 48회 적중을 보존한 상태에서 실제 보드의 캡처·COMMIT·표시 lease·EA 해제를 연결한다. 국소 MAP의 산술 여유 대신 전체 Cyclone IV 보드 FIT·STA로 판정한다. 실기 기준과 배포본은 **MMC577**이다.

## 작업내용

`prepare_nes_board611.py`가 선택된 576 보드의 입력 75개 해시를 확인하고 실제 `nes_live_joint → nes_direct206 → nes_source_tile192`에 새 캐시를 연결한다. 기존 tile205·ROM 중재기·host queue·SPI·독립 검사·최종 ACK 경로를 사용한다. 캡처는 실제 collector의 capture_begin과 다음 generation으로 시작하고, 유효한 OBJ PPU read의 물리 주소·값만 저장한다. geometry 확정 뒤 seal하며 `retire_commit && retire_permitted`와 그 generation으로 이전 뱅크만 해제한다. 입력 COMMIT은 표시 lease로 소유권을 넘길 뿐 캡처 바이트를 해제하지 않는다.

실제 시작 경계에서 두 문제를 고쳤다.

- START 뒤 128클록 동안 directory를 초기화하면 약 20클록 뒤 들어오는 첫 OBJ를 놓친다. 해제된 뱅크를 **START 전**에 지우고 clean인 뱅크만 수락한다. sample commit을 초기화보다 우선하고 held·capturing 뱅크는 건드리지 않는다. 준비되지 않은 캡처는 ROM miss로 복구한다.
- 첫 display lease가 없는 시점에는 captured epoch와 live epoch가 다를 수 있다. 캡처 허가는 물리 ROM의 source-ready·ROM 종류·쓰기 중 여부로 판단한다. 기존 query의 lease·epoch 검사는 남긴다. 실제 source_epoch207이 ROM 내용 변경 전에 unavailable을 먼저 내리므로 캐시도 무효화된다.

BG 16 B·byte-valid·tag 이력은 공통 miss 완료 경로에서 갱신하고 OBJ 조회 때문에 버리지 않는다. 주소·generation·오류가 일치한 응답만 저장한다. STOP·ROM unavailable은 이력을 무효화한다. 비동기 kill과 2단 drain으로 NES 클록이 멈췄을 때의 짧은 STOP도 유지한다. OBJ는 두 뱅크의 현재 캡처를 조회하고 누락이면 원래 중재기로 읽는다. 이 범위는 immutable CHR ROM이며 MMC5 등의 mapper override 일반화는 완료하지 않았다.

## 성과

### 기능과 시간

동일 보드 source RTL 시험에서 BG 반복 적중, OBJ 적중·누락, core ROM 경쟁, backpressure, 주소·generation 오류, STOP·drain을 통과했다. 캡처 시험은 8,416 sample·1,328 query·1,200 hit·3,072 concurrent query를 확인했다. 별도로 실제 collector/export/frame/lease RTL과 53개 PPU trace를 연결해 53회 시작, 1,200 적중, 52회 이전 세대 해제를 검증했다. 이 RTL 시험의 retire pulse는 최종 ACK/EA를 대신하는 시험 입력이다. **전체 NES/PSRAM/ARM/65816 동시 RTL 실행으로 부르지 않는다.** 최종 ACK→EA→뱅크 재사용은 아래 실제 ARM·65816 일정에서 별도로 전 거래 확인했다.

ARM은 610 arm06 전체 링크 바이너리(212,992 B·여유 0), 65816은 608 client03(본문 4,949 B·ROM 5,120 B)을 변경하지 않았다. 두 시작 클록 3,000,000 / 3,178,684에서 대조군과 후보 각각 53화면을 실행했다. 대조군은 기존 한 줄 CHR 캐시를 실제 시간 모델에 포함하고 후보는 BG 이력+OBJ 캡처를 포함한다. 양쪽 모두 기존 BG 적중 48회(912·931·939 각 16회)를 유지했다. 후보의 OBJ 적중은 1,200회, 물리 ROM 공급 요청은 5,568→4,368회다.

| 동일 ARM·65816, 기존 캐시 → 후보 | 시작 위상 1 | 시작 위상 2 |
|---|---:|---:|
| 951–955 밀집 표시 간격 평균 | 79.779→76.529 ms | 79.777→76.474 ms |
| 밀집 구간 합계 | 24→23 VBlank | 24→23 VBlank |
| 952 표시 간격 | 82.966→81.782 ms | 82.688→81.782 ms |
| 952 표시 간격 VBlank | 5→5 | 5→5 |
| 957 표시 간격 | 66.983→66.571 ms | 66.974→66.535 ms |
| 957 최종 대기 | 0→0 | 0→0 |
| 53번째 화면 최종 ACK 차이 | −33.052 ms | −33.080 ms |

952의 최종 SEAL 뒤 대기는 대조군 0→후보 1회다. 전체 표시 간격과 마지막 ACK는 빨라졌지만 **952의 마지막 대기까지 없앴다고 판단하지 않는다.** 610의 BG 적중을 누락했던 모델과 직접 비교하면 마지막 ACK는 +33.273 / −0.010 ms다. 초반 완료 위상이 뒤 장면의 ROM/VBlank 구간을 바꾸므로 BG 적중 시간을 단순 차감할 수 없다. 이번 동일 캐시 조건의 대조군을 다음 시간 비교 기준으로 사용한다.

양쪽 VRAM DMA 114,352 B·53개 RGB·출력 내용이 일치하고, 실제 E0 sent/done은 PUSH/65816 ACK 시각과 일치했다. bulk 최대 2슬롯, 일반 queue 최대 4, capture 조회는 해당 입력 준비 뒤, EA는 최종 ACK 뒤, 동일 뱅크 재사용은 이전 EA 뒤임을 확인했다. 변경하지 않은 610 ARM guard와 608 독립 검사·STOP·메뉴 복구 근거를 유지한다. 새 실기 메뉴 시험을 수행한 것은 아니다.

시간 모델은 실제 M4 코드·SysTick·65816 실행에 SPI 거래·평균 driver 비용·CPI 2·기록된 ROM 허용 구간을 연결한다. 캡처와 tile 내용은 고정 자료를 재생한다. 따라서 이 값은 실기 FPS가 아니며 60 Hz 달성 근거도 아니다.

### 전체 보드 비용과 STA

| Quartus Lite 25.1 전체 FIT | 선택 576 보드 | 611 후보 | 변화 |
|---|---:|---:|---:|
| LE | 15,260 | 15,329 | +69 |
| 조합 논리 | 14,191 | 14,360 | +169 |
| FF | 8,407 | 8,474 | +67 |
| RAM bit | 264,816 | 303,216 | +38,400 |
| M9K | 51/56 | 56/56 | +5 |
| 남은 LE | 148 | 79 | −69 |

한 번의 전체 FIT는 성공했다. 610 국소 source −171 LE를 전체 절감으로 합산하지 않는다. 실제 BG 이력·START 전 초기화·보드 연결까지 포함한 최종 결과는 +69 LE이며 새 RAM 여유는 없다.

전체 원본 STA의 최악 setup/hold/recovery/removal은 −4.249 / +0.144 / −9.087 / +0.489 ns였다. 새 배치에서 별도 레지스터로 남은 기존 `rearm` mailbox의 ready 첫 동기화 단계와 async release pin에 기존 control/tiles와 같은 검토 규칙을 적용했다. 45.454/11.904 ns의 첫 단계 max-delay와 네 async clear pin만 분류하고, 2단계 및 기능 데이터·ROM IO는 제외하지 않았다. 후보의 두 번째 동기화 단계는 세 corner 모두 통과했으며 최소 setup +10.736 ns, hold +0.196 ns다. 기준 배치는 rearm 레지스터가 병합돼 해당 정확한 이름의 경로가 없으므로 기존 제약으로 보고했다. 기준에 억지 wildcard 예외를 추가하지 않았다. 이는 기능 속도 개선이 아니라 CDC 분류 보완이다.

| 전체 STA 최소값 | 기준 배치 | 후보 CDC 검토 후 |
|---|---:|---:|
| setup | +0.045 ns | **−0.629 ns** |
| hold | +0.140 ns | +0.144 ns |
| recovery | +2.364 ns | +1.540 ns |
| removal | +0.490 ns | +0.489 ns |

남은 실패는 `loader_boot → reader.reading_active → ROM_OE`의 실제 12 ns IO 경로다. 원본 보드에서도 필요했던 경로이며 새 배치에서 회귀했다. IO 허용치를 늘리거나 false-path로 숨기지 않았다. **시간·FIT 조건은 통과했으나 전체 STA는 실패했다. 후보를 실기 전달본으로 선택하지 않는다.**

## 후속작업

1. ARM610·SNES608·BG 48/OBJ 1,200 적중과 이번 두 위상 대조군을 고정한다. 79 LE·추가 M9K 0·추가 Flash 0을 예산으로 삼는다.
2. `reading_active→ROM_OE`의 조합 경로·IO 출력 소유자를 추적해 실제 제어를 줄인다. loader/실행 ROM read·STOP 즉시 차단·base 복구를 유지하는 구조 변경만 비교한다. seed 변경이나 같은 RTL의 반복 FIT는 하지 않는다.
3. 그 변경의 기능 검증 후 전체 FIT·STA 무회귀와 957 대기 0·두 위상의 표시/ACK를 확인한다. 통과 전 ZIP은 만들지 않는다. 60 Hz·외부 IO 전체 실기·장기 신뢰성은 여전히 미완료다.

## 재현과 근거

- `prepare_nes_board611.py --base <nes-cdc576-board01> --out <새 보드 폴더>`: 75개 원본 해시 확인, 실제 연결 생성.
- `check_nes_board611.py`와 `check_nes_lifecycle611.py`: 기존 Starter FLOAT wrapper로 순차 실행. 새 좌석이나 라이선스 시험은 필요 없다. 보드 source와 시험 입력 해시는 결과에 묶는다.
- `test_nes_board611.py --reference-cache` / 옵션 없는 후보: 같은 610 ARM·608 client·601 samples·ROM calendar·driver503로 위 두 시작 시각 실행.
- `quartus_sh --flow compile board`: Lite 전체 합성·FIT·STA. 원본 STA를 보존하고 `constraints_nes_board611.py`의 cdc611.sdc 및 `report_nes_board611.tcl`로 동일 배치 DB만 재검토한다. 기준 배치는 rearm 추가 제약 없이 보고한다.
- `budget_nes_board611.py`: 원본/후보 입력 해시·source/collector 시험·cache service·RGB·credit·ACK·전체 비용을 대조한다.

[기계 판독 결과](../analysis/board611-verification.json). Temp의 nes-board611-{candidate01,sim01,life01,ref1,ref2,run1,run2}와 raw 실패 로그를 보존한다. 재개용 로컬 보관본은 저장소 부모 probes/nes-board611/archive01에 두며 ROM·바이너리·license를 Git에 넣지 않는다.
