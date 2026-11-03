# 572 · loader START와 168MHz 메모리 고장 차단

**다음 기준은 571 A에 START 변경만 적용한 보드다.** 85°C에서 START로 들어가는 최악 setup은 −0.024ns에서 +2.466ns로 개선됐다. MMC558 대비 코너·클록별 WNS 회귀는 3개에서 1개가 됐다. 나머지 하나는 slow 0°C의 NES setup으로, MMC558보다 0.020ns 낮다. 실기 기준은 MMC558을 유지한다.

## 분리한 경로

571 A에서 `pending`은 STOP·CHECK_BEGIN 때 수신 중인 CHECK 응답을 무효화하는 데 쓰였다. 이 공통 판정이 START 출력까지 이어졌다. C2에서 START가 승인된 경우에는 같은 수락 건의 STOP·CHECK_BEGIN은 비활성이다. C3의 START는 보관한 응답의 상태와 주소 비교 결과를 직접 사용한다. SS, sticky fault, CHECK 고장과 boot 고장은 원래 C3 에지에서 검사한다. 명령 수락 에지는 바뀌지 않는다.

메모리는 두 구조를 시험했다. **출력 차단**은 시작 카운터의 reset에서 sticky fault를 떼고, 외부 메모리 허가에서 고장을 즉시 차단한다. 공통 reset을 거쳐야 재시작한다. **허가 철회**는 각 watchdog이 고장을 래치하는 에지에서 해당 자격 비트도 내린다. 참조 허가가 내려가면 기존 2단 동기화 레지스터가 메모리 에지 없이 비워지고 메모리 해제 체인이 닫힌다. 정상 허가는 기존처럼 메모리 클록을 통과한다.

| 보드 | 85°C START 최악 setup | 85°C 참조 고장의 실제 recovery 경로 |
|---|---:|---|
| MMC558 | +0.870ns | ref_fault → memory_release −5.397ns |
| 570 board05 | +1.508ns | ref_fault → memory_release −4.836ns |
| 571 A | −0.024ns | ref_fault → memory_release −6.571ns |
| START만 | +2.466ns | ref_fault → memory_release −4.983ns |
| 출력 차단만 | +1.164ns | ref_fault → PSRAM reader.memory_reset −8.678ns |
| START + 출력 차단 | +1.345ns | ref_fault → PSRAM reader.memory_reset −7.923ns |
| START + 허가 철회 | +2.462ns | ref_qualified → ref_ok_mem −4.658ns, ref_ok_mem → memory_release +2.980ns |

START를 수정한 세 보드에서는 원래 pending → start 경로가 세 코너 모두 사라졌다. START만 바꾼 보드에서 메모리 recovery도 개선된 부분은 배치 차이다. 출력 차단 방식은 recovery 위반이 reader 쪽으로 옮겨 가므로 제외한다. 허가 철회 방식은 실제 참조 crossing의 recovery를 개선했지만 여전히 음수다.

## Quartus Lite 전체 보드

모든 후보는 동일 QSF·SDC·seed에서 전체 FIT을 통과했다. 대상 setup/hold는 기존 implementation 보고서의 관련 클록 집계다. 전체 setup/recovery는 모든 코너의 최악값이다. 회귀 열은 각 대조군보다 악화된 음수 WNS 행 수 / TNS가 악화된 행 수다. 모든 시간 단위는 ns다.

| 보드 | LE | 대상 setup / hold | 전체 setup / recovery | MMC558 대비 회귀 | 570 대비 회귀 |
|---|---:|---:|---:|---:|---:|
| MMC558 | 15,164 | +0.078 / +0.139 | −7.081 / −8.480 | 0 / 0 | 19 / 13 |
| 570 | 15,227 | +0.355 / +0.142 | −6.930 / −7.790 | 0 / 6 | 0 / 0 |
| 571 A | 15,214 | −0.024 / +0.156 | −6.638 / −7.389 | 3 / 8 | 11 / 12 |
| START만 | 15,297 | +0.286 / +0.145 | −5.695 / −7.646 | **1 / 3** | 12 / 9 |
| 출력 차단만 | 15,216 | +0.234 / +0.148 | −6.938 / −8.678 | 13 / 13 | 19 / 16 |
| START + 출력 차단 | 15,221 | −0.416 / +0.131 | −6.130 / −7.923 | 12 / 9 | 12 / 12 |
| START + 허가 철회 | 15,288 | +0.101 / +0.174 | −6.731 / −8.056 | **3 / 9** | 10 / 14 |

네 후보 모두 8,390 FF·51 M9K다. START만·허가 철회의 미제약 출력 setup/hold 경로 수는 3,008 / 3,011, 출력 차단 두 후보는 3,012 / 3,015다. MMC558은 3,015 / 3,018, 570은 3,018 / 3,021이다. START만·허가 철회의 85°C ROM_OE slack은 각각 +0.717 / +0.956ns였다. 허가 철회에서 MMC558보다 악화된 WNS 세 행은 모두 168MHz setup이다. PSRAM reader의 address_hold → check_response_address가 slow 85°C −5.097ns, slow 0°C −4.610ns, fast 0°C −2.472ns였다.

## 고장·STOP·표시 검증

- 실제 SPI 수신기와 571 A를 에지마다 비교했다. 위상마다 1,429,799회 비교했고 정상 CHECK·ACK·START·STOP을 포함했다. C2에서 START를 승인한 뒤 C3의 fault·SS·응답 주소·busy 조건을 조합한 512가지도 기준 회로 및 독립 기대값과 일치했다.
- 합성한 최상위의 메모리 허가 배선을 guard 시험에 그대로 넣었다. 두 위상에서 초기 자격 확인 전·시작 대기 중·PSRAM 읽기 중에 메모리 또는 참조 클록을 정지시켰다. 고장 검출 뒤에는 멈춘 쪽 에지 없이 핀을 차단하고 미완료 읽기를 폐기했다. 두 클록이 모두 멈추고 외부 reset도 없으면 watchdog은 정지를 검출할 수 없다. 이 상태에서 공통 reset을 인가하면 핀은 차단됐다. 클록 재개만으로 재무장되지 않았다. 시작 순서와 watchdog 검출 시각은 기준과 같았다.
- 두 슬롯 STOP 16개 위치·고장 3종·토큰 재사용·최종 retire, 고장 뒤 E9 수락 0회, STOP을 걸친 부분 ACK 소비 0회, 올바른 ACK 소비 1회를 확인했다. 핀 선택 128조합과 두 위상의 aperture 읽기 해제도 571 A와 같았다.
- 동일 ARM·SPI·IRQ·ROM 도착 기록으로 65816을 다시 실행했다. 두 위상 각각 53화면의 RGB·표시·뱅크 이벤트·도착 기록이 바이트 단위로 571 A와 일치했다. 952·957 모두 **5 VBlank, 최종 대기 0회**였다. 밀집 평균 간격은 83.157 / 83.121ms, 마지막 ACK는 87,545,284 / 88,254,606 master clocks였다. 실기 FPS나 새로운 ARM 스케줄 측정은 이번 결과에 포함하지 않았다.

## 다음 작업과 재현

START 단독 보드의 유일한 WNS 회귀인 `content_lifetime.gray[23] → epoch_meta[23]`를 먼저 본다. 0°C에서 −4.606ns로 MMC558의 −4.586ns보다 0.020ns 낮다. 32비트·세 코너를 다시 조회했다. 첫 단 최대 데이터 지연은 MMC558 6.729ns, START 단독 6.730ns이며 두 번째 단의 최악 setup은 +42.300 / +41.768ns였다. 다음은 두 단의 배치와 STOP 뒤 첫 generation의 실제 사용 시점을 함께 확인하는 것이다. 570을 전체 WNS 대조군으로 유지하고 FIT seed와 제약은 고정한다.

MMC558 보드에서 `prepare_nes_start572.py --mode loader|memory|joint|revocable`로 네 후보를 생성한다. 단일 Starter FLOAT 좌석에서 `check_nes_start572.py`와 `check_nes_bus571.py`를 실행한다. guard·banks 재현 입력은 570의 wire05/local·local01/local이다. 기존 보드 compile·timing506·owner562·pins565·arg564 보고서 및 `report_nes_start572.tcl`을 실행한다. MMC558과 START 단독에는 epoch568 보고서도 실행한다. 65816 재생은 556 client와 owner562-run1/2를 사용한다. 첫 에뮬레이터 실행은 설치 DLL을 찾지 못해 시작 전 종료됐다. 저장소 작업에 쓰던 532 Mesen으로 두 위상을 다시 완료했다. `analyze_nes_start572.py`에서 보드 소스·기존 SOF·각 결과를 대조한다. [검증 데이터](../analysis/start572-verification.json)
