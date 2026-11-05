# 612: ROM_OE·CE 직접 출력과 전체 보드 타이밍

## 목표

611의 ARM610·SNES608·BG 48회 적중·OBJ 캡처와 표시 일정을 유지하고 `reading_active → ROM_OE`의 −0.629 ns를 기존 12 ns 제약 안에서 해결한다. STOP·독립 검사·최종 ACK·메뉴 복귀와 957 최종 대기 0회를 유지한다. 실기 기준은 아직 MMC577이다.

## 작업내용

원래 물리 reader는 `memory_reset[1]`로 reading_active를 비동기 초기화하면서, OE 앞에서 같은 reset을 조합 논리로 다시 마스킹했다. `psram_oe = !reading_active`로 출력 소유자를 하나로 만들었다. SETUP에서 assert, ACTIVE 마지막 edge에서 sample, HOLD에서 release하는 시각과 ACK·응답은 바꾸지 않았다.

OE만 바꾼 첫 후보는 기능 시험을 통과했지만 전체 FIT에서 964/963 LAB로 실패했다. LE 수만 보고 배치 성공으로 판정하지 않았고 해당 실패 보고서를 보존했다.

선택 후보는 두 CE에도 별도 `chip_active[1:0]` 출력 레지스터를 둔다. IDLE에서 이미 확정된 chip을 SETUP에서 받아 해당 CE만 켜고 HOLD에서 끈다. 비동기 reset은 두 비트를 직접 지운다. CE에서 reset 마스크만 제거하면 chip 자체의 초기화와 reading_active 해제 사이에 다른 칩이 잠깐 선택될 위험이 있어, 그 중간 후보는 RTL 시험까지만 보존하고 FIT 대상으로 선택하지 않았다. 새 CE 두 경로도 기존 OE와 같은 12 ns max-delay를 적용한다. 기존 IO 예산을 늘리거나 출력 경로를 false-path로 만들지 않았다.

611에서 검토한 rearm 첫 동기화 단계·async release pin 규칙은 이제 전체 보드 SDC에 포함한다. 새 CE 레지스터의 기능·recovery 경로에 예외를 추가하지 않는다. 실제 변경 파일은 `nes_rom_physical.sv`, `board.sdc`, 추가 `cdc611.sdc`이며 나머지 611 보드 입력 해시가 같다.

## 성과

### 기능·STOP·복구

611 원본과 후보 reader를 같은 입력에 연결해 주소·데이터·CE/OE·ready·응답·ACK를 edge마다 비교했다. 실제 READ_CYCLES=16의 두 클록 위상과 경계값 1·3을 포함한다. 총 260회 읽기, 32회 클록 정지 취소, 38,893회 관측 비교를 통과했다. CHECK/RUN 양쪽의 SETUP·ACTIVE·HOLD·RELEASE에서 두 클록을 멈춘 뒤 짧은 reset을 주어 CE/OE 해제, stale 응답 차단, 복구 후 읽기를 확인했다. RTL의 delta 안정화 뒤 비교이며 아날로그 glitch·보드 전파 지연을 시뮬레이션한 주장은 아니다.

실제 보드의 메모리 허가·heartbeat 고장·물리 reader를 연결한 기존 경계 시험도 새 RTL로 실행했다. 두 위상 각각 START veto 512개, 클록 고장 6조건, 두 클록 정지 중 active read 차단, 두 슬롯 STOP 16조건·오류 3조건·재사용·retire를 통과했다. 독립 검사·최종 ACK·메뉴 코드는 수정하지 않았다. 메뉴 복귀는 기존 608/610 검증과 실제 보드 reset/복구 경계를 유지하며, 새 실기 메뉴 실행은 아직 하지 않았다.

### 두 시작 위상의 시간 유지

ARM610·SNES608 바이너리와 source·BG/OBJ 캐시 RTL은 동일하다. 물리 reader의 pin·sample·response 시각도 위 동등성 시험에서 같다. 이에 따라 **611의 네 ARM/65816 실행 기록을 다시 검증**했다. 새 전체 ARM 일정을 실행한 것처럼 표시하지 않는다. 53개 RGB·114,352 B DMA·조회·실제 credit·최종 ACK/EA 소유권의 기존 검증을 재확인했고 새 시간 이득을 더하지 않았다.

| 동일 시작 클록에서 611 → 612 | 위상 1 | 위상 2 |
|---|---:|---:|
| 밀집 951–955 평균 표시 간격 | 76.529 ms 유지 | 76.474 ms 유지 |
| 밀집 구간 합계 | 23 VBlank 유지 | 23 VBlank 유지 |
| 952 표시 간격 | 81.782 ms / 5 VB | 81.782 ms / 5 VB |
| 957 표시 간격 | 66.571 ms / 4 VB | 66.535 ms / 4 VB |
| 957 최종 대기 | 0회 | 0회 |
| 53번째 최종 ACK masterclock | 86,477,322 | 86,119,184 |
| 마지막 ACK의 611 대비 변화 | 0 | 0 |
| 기존 BG 캐시 공정 대조군 대비 ACK | −33.052 ms | −33.080 ms |

BG 적중 48회·OBJ 적중 1,200회, bulk 최대 2슬롯을 유지한다. 952의 SEAL 뒤 최종 대기 1회는 남아 있다. 이 일정은 실제 ARM·65816 실행과 CPI 2·기록된 ROM calendar·평균 SPI driver 비용을 결합한 모델이며 실기 FPS나 전체 NES/PSRAM 동시 RTL 실행이 아니다.

### Quartus Lite 전체 FIT·STA

| 전체 보드 | 611 | 선택 612 | 변화 |
|---|---:|---:|---:|
| LE | 15,329 | 15,332 | +3 |
| 조합 논리 | 14,360 | 14,359 | −1 |
| FF | 8,474 | 8,474 | 0 |
| RAM bit | 303,216 | 303,216 | 0 |
| M9K | 56/56 | 56/56 | 0 |
| LE 여유 | 79 | 76 | −3 |

새 CE 레지스터 2개와 reader FSM의 합성 인코딩 변화가 포함된 전체 결과다. 선택 후보는 reader 상태가 독립 FSM으로 추출되지 않는다. 이를 FSM 절감 성과로 계산하지 않으며, 최종 연결의 기능·전체 FIT·STA 결과로 판정한다. 같은 seed의 동일 RTL FIT 반복을 하지 않았다. 전체 FIT 시도는 OE 단독 실패 1회와 CE/OE 소유자 교체 성공 1회다.

| 최소 slack, 모든 corner | 611 CDC 검토 후 | 612 전체 compile |
|---|---:|---:|
| setup | −0.629 ns | **+0.487 ns** |
| hold | +0.144 ns | +0.163 ns |
| recovery | +1.540 ns | +1.652 ns |
| removal | +0.489 ns | +0.490 ns |
| ROM_OE, 12 ns 제약 | −0.629 ns | **+0.592 ns** |
| ROM_1CE, 12 ns 제약 | 기존 경로 | +3.928 ns |
| ROM_2CE, 12 ns 제약 | 기존 경로 | +3.662 ns |

새 보드는 FIT·전체 STA를 통과했다. 기존 선택 576의 전체 최소 setup +0.045 ns보다도 양수 여유가 크다. 다만 이 결과는 저장소에 정의된 제한 보드 제약의 통과이며, 외부 PCB/PSRAM 전체 sign-off나 장기 실기 안정성을 새로 증명한 것은 아니다. ARM Flash는 212,992 B로 여유 0이며 M9K도 여유 0이다.

## 후속작업

612 보드·610 ARM·608 SNES 조합을 제한 실기 전달 후보로 고정한다. 다음 단계는 새 파일명·로그 marker를 적용한 전달본 전체 링크 및 산출물 해시 확인이다. 코드·크기·배치가 달라지면 그 경계만 다시 검증한다. RESTORE는 포함하지 않고, 기존과 같은 첫 레벨 동선에서 5–40초·40–55초 및 실행/STOP/메뉴 복귀를 비교한다. 실기 확인 전에는 MMC577 기준이나 FPS를 갱신하지 않는다. 추가 발행 상수·FSM·seed 조정은 보류한다.

## 재현

`prepare_nes_oe612.py --base <611 candidate01> --out <새 폴더> --all-pins`가 611 해시를 검증하고 선택 보드를 만든다. 옵션 없는 OE 단독은 실패 대조군이다. `check_nes_oe612.py`와 `check_nes_start572.py`는 승인된 단일 Starter FLOAT wrapper로 순차 실행한다. Lite `quartus_sh --flow compile board` 후 `report_nes_oe612.tcl`을 같은 배치 DB에 실행한다. `budget_nes_board611.py`로 기존 네 일정 기록을 재검증하고 `budget_nes_oe612.py`가 해시·기능·시간·전체 비용을 묶는다.

[612 기계 판독 결과](../analysis/oe612-verification.json). 선택은 Temp/nes-oe612-board04·sim03·boundary03이다. board01은 생성기 하위 폴더 생성 누락, board02는 OE 단독 LAB 부족, board03은 CE 조합 마스크 제거의 미선택 RTL 시험이며 모두 보존한다. 저장소 부모 probes/nes-oe612/archive01에 비공개 원시 근거를 보관한다. 공개 Git에는 ROM·바이너리·license를 넣지 않는다.
