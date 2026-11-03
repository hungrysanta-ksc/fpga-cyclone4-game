# 574 — 초기화 중 직렬 identity 인계

**직렬 후보는 채택하지 않는다. 개발 기준은 572 START 단독, 실기 기준은 MMC558이다.** RAM 초기화 동안 일회성 32비트 전송을 끝내고 첫 캡처·tile 공급을 유지할 수 있었지만, 전체 보드의 MMC558 대비 WNS 회귀가 1곳에서 7곳으로 늘었다. 새 ZIP은 만들지 않았다.

[기계 검증](../analysis/serial574-verification.json) · [573과 비교](nes-epoch573-results.ko.md) · [PR149](progress/pr-149.md)

## 교체와 기능 검증

기존 32비트 Gray 저장·NES 연속 샘플을 송신 shift, 수신 shift, request/ACK로 교체했다. ROM serial의 증가·포화 규칙은 유지한다. local core reset 중에도 전송하며, 완성된 값만 기존 source-ready 공개 시점에 사용한다. 마지막 비트에는 ACK를 돌려주지 않아 송신기가 추가로 진행하지 않는다. STOP·새 BEGIN·쓰기·고장·적재 무효는 양쪽 전송 문맥을 비동기로 취소한다.

데이터 2단과 request 3단, ACK 2단을 사용했다. 두 위상에서 각각 226개 정상·취소 사례를 실행했다. 모든 32비트 위치에서 STOP/BEGIN/쓰기/고장/적재 길이/loaded 무효화를 넣고, NES 또는 메모리 클록 정지, 양쪽 클록 정지 중 공개된 identity 차단, serial 포화를 확인했다. 데이터에 NES 1클록 지연을 추가한 시험도 통과했다. request를 2단으로 줄인 음성 대조군은 실제로 `mixed identity`를 검출했다. 이는 디지털 지연 시험이며 아날로그 metastability 증명은 아니다.

실제 RAM scrub·collector·capture lease와 source/cache/plan RTL을 연결한 결과다. NES 에지는 RUN 재개부터 센다.

| 사건 | 572 | 574 |
|---|---:|---:|
| identity 직렬 전송 완료 | 해당 없음 | 130 |
| core reset 해제 | 8,196 | 8,196 |
| source-ready 공개 | 8,200 | 8,200 |
| collector 초기화 완료 | 16,388 | 16,388 |
| 첫 eligible PPU 이벤트의 capture 수락 | 16,389 | 16,389 |
| capture identity를 이용한 첫 tile ROM 요청 | 16,391 | 16,391 |

cold, 같은 ROM에서 STOP 후 재개, NES 정지 중 두 BEGIN 후 재적재를 각각 확인했다. 캡처 identity는 `00c00000 → 00c00000 → 00c00003`이다. 각 첫 tile은 2개 주소를 읽어 16B를 생산하고 반복 요청은 cache hit로 ROM 읽기가 0회였다. 재적재 뒤 ROM 응답 값을 바꾸어 이전 cache 데이터가 나오지 않는지 검사했다. 첫 tile의 geometry lease와 1에지 ROM 응답은 시험용이다. 실제 전체 geometry export·물리 PSRAM 공동 실행 결과로 확대하지 않는다.

기존 loader START 1,429,799 SPI 주기/위상·512 거부 조합, 참조/메모리 클록의 6개 고장 위치, E9 차단, 두 슬롯·STOP·부분 ACK와 올바른 ACK를 다시 확인했다. 기존 메뉴 복귀 코드·ARM·65816 코드는 변경하지 않았다. 이번 단계의 새 실기 메뉴 시험은 없다.

## Quartus Lite 전체 보드

동일 보드·seed·QSF·SDC를 사용했다. MAP 1회 후 FIT·ASM·STA 1회이며 배치 탐색을 반복하지 않았다.

| 항목 | MMC558 | 570 | 572 START | 574 직렬 |
|---|---:|---:|---:|---:|
| FIT LE | 15,164 | 15,227 | 15,297 | 15,258 |
| 레지스터 | 8,394 | 8,390 | 8,390 | 8,347 |
| 조합 논리 | 14,172 | 14,182 | 14,195 | 14,244 |
| 관련 setup / hold ns | +0.078 / +0.139 | +0.355 / +0.142 | +0.286 / +0.145 | +0.006 / +0.152 |
| 전체 최악 setup ns | −7.081 | −6.930 | −5.695 | −6.540 |
| 전체 최악 recovery ns | −8.480 | −7.790 | −7.646 | −8.685 |
| MMC558 대비 악화 WNS / TNS 행 | — | 0 / 6 | 1 / 3 | 7 / 9 |

RAM은 264,816bit·51M9K로 동일하다. 572 대비 **−39 LE, −43 FF, +49 조합 논리**다. 미제약 출력 경로는 implementation setup/hold 3,008/3,011로 572와 같고, nominal은 3,011/3,011이다. 기존 PSRAM 70ns·왕복 PCB 각 2ns 가정의 최소 여유는 +4.081ns다. 전기적 전체 signoff는 아니다.

574의 START 최소 setup은 +1.865ns다. 직렬 CDC 첫 단은 세 코너 모두 raw setup 음수이며, 뒤 동기화 단계의 setup/hold는 양수다. 0°C NES 최악 경로는 더 이상 epoch bit 23이 아니라 기존 plan의 `held[0] → received[0]` −4.664ns다. 목표 endpoint 제거만으로 전체 gate를 통과하지 못한다. 관련 최소 setup도 +0.006ns까지 줄어 여유가 거의 없다.

## 표시 일정

같은 기록된 ARM·SPI·IRQ·ROM 도착열로 실제 65816을 재실행했다. 두 위상의 53개 RGB 화면·표시 시각·bank 소비 기록은 573과 일치했다. 952·957은 각각 **5 VBlank, 최종 대기 0회**, 밀집 평균은 **83.157 / 83.121ms**, 마지막 ACK는 **87,545,284 / 88,254,606 master clocks**다. 초기화 RTL 시험과 고정 입력 표시 재생은 별도 실행이며, 새 실기 FPS나 새 전체 ARM 공동 실행 결과가 아니다.

## 다음 순서와 재개 조건

1. **572를 유지한다.** epoch bit 배치·동기화 속성·일회성 직렬화의 추가 FIT 반복은 중단한다. 구조와 전체 비용의 개선 근거가 생길 때만 재개한다.
2. 572의 전체 위반 경로를 같은 클록의 데이터, 독립 클록의 첫 동기화 단, 비동기 reset assertion/동기 해제로 분리한다. 실제 top 클록·reset 연결 및 모든 초기 소비자의 소유권을 근거로 endpoint 목록을 확정한다. 현재 SDC는 board8과 nes를 별도 입력 클록으로 선언하므로 단순 slack 순위만으로 RTL 병목을 판정하지 않는다.
3. 실제 setup/해제 결함은 RTL에서 고친다. 제약을 바꿀 필요가 입증되면 정확한 endpoint·안정 유지 시간·동기화와 취소 증거를 먼저 제시하고 MMC558/572 양쪽에 같은 제약으로 비교한다. 기존 raw STA도 보존한다. blanket false path나 기준 악화를 숨기는 예외는 추가하지 않는다.
4. STOP·즉시 차단·첫 capture/cache/plan과 두 위상 952·957·마지막 ACK를 유지한 뒤 전체 gate를 다시 판정한다. 실기 기준 또는 전달 정책을 자동으로 바꾸지 않는다.

## 재현과 실패 보존

`prepare_nes_serial574.py --base <MMC558 board> --out <candidate>`로 572 START를 재생성한 뒤 epoch만 교체한다. 단일 FLOAT wrapper에서 `check_nes_serial574.py`, `check_nes_start572.py`, `check_nes_bus571.py`를 순서대로 실행한다. Lite MAP/FIT/ASM/STA와 기존 timing506·owner562·pins565·start572, 새 `report_nes_serial574.tcl`을 실행한다. 556 client·owner562-run1/2로 `replay_nes_close561.py --all-banks` 재생 후 `analyze_nes_serial574.py`로 해시와 전체 비용을 대조한다.

선택 자료는 Temp `nes-serial574-board01`, `test08`, `start01`, `pins01`, `replay1/2`다. test01은 새 BEGIN 뒤 송신 재시작을 금지한 과도한 fixture assertion, test03은 tick 선언 순서 컴파일 오류였다. test07/08의 request 2단 음성 대조군 실패는 의도된 결과다. test08은 기준 RTL에도 같은 첫 tile fixture를 연결한 대조를 추가했다. 한글 Tcl 경로 및 레지스터 패턴 오류는 ASCII 경로·정확한 이름으로 보고서만 다시 실행했다. 원래 실패와 중간 성공 기록을 남겼으며 새 license 오류나 제품 고장으로 분류하지 않는다.

생성기를 다시 실행해 보드 입력 73개의 해시를 대조했다. 원본 보고서·실패/성공 로그·53화면 두 위상 등 367파일은 작업공간 `probes/nes-serial574/archive01/evidence.zip`에 보관하고 전체 바이트를 재검증했다. ZIP SHA256은 `fa4b5fc8f95a5eebb8b72cfb7ccec0f7907d60284114b82f4c5e02b50dece3a3`이다. 라이선스 파일·서버 로그는 포함하지 않는다.
