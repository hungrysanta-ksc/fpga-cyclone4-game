# 571 · SNES 읽기 해제와 출력 경로

570 board05의 상세 배치 보고서에서 `transport.hrelease.release_reset[1]`이라는 이름의 FF부터 실제 OE 핀까지 추적했다. 경로는 `bulk.aperture.enabled → aperture.oe_n → consumer_dir → SNES_DATABUS_OE`를 거쳤다. 합성기가 공통 reset FF를 병합했기 때문에 plan 인스턴스 이름이 붙었지만, 이 경로에서 읽기 허가를 결정하는 곳은 타일 뱅크다. 85°C에서 이 FF로부터 OE까지의 데이터 지연은 16.648ns였다.

## 회로 변경과 시험

- **A · aperture reset 입력.** 뱅크의 `hc`는 이미 `hr || source_failed || host_failed`에 비동기로 반응하고 host 클록에서만 풀린다. aperture의 별도 `reset(hr)` 입력을 제거하고 `stop(hc)`를 유지했다.
- **B · 읽기 허가.** 570의 reset 배선을 유지하고, 뱅크 공개와 읽기 방향은 aperture의 `local_reset`이 해제됐을 때만 허용했다. 쓰기 및 seal 판정은 570과 같다.
- **C · 출력 소유권.** A에서 direct와 sink 중 정확히 하나가 선택되고 읽기 방향일 때만 DIR을 올린다. 읽기 승인 자체로 DATA를 구동한다. 상태 쓰기는 OE가 활성이어도 FPGA가 DATA를 구동하지 않는다. 두 소유자가 겹치면 읽기가 해제된다.

동일한 direct·sink·status RTL에 각 보드 최상위의 핀 선택식 여섯 개를 그대로 연결했다. 두 시작 위상 각각에서 주소 이동·태그 불일치·sink와 direct 간 전환·상태 쓰기·버스 해제를 49회 검사했다. 두 클록을 멈추고 데이터가 실제 모델 핀에 구동된 상태에서 core fault, 공통 reset, 뱅크 자체 고장 래치 주입을 각각 시험했다. 모두 다음 에지 없이 OE 비활성·DIR 0·DATA 8비트 고임피던스로 돌아갔다. 정상·충돌·수신 조건을 포함한 128개 핀 선택 조합도 독립 판정과 일치했다. 이는 논리 시뮬레이션이며 핀 해제에 걸리는 실제 ns는 별도 STA 분석과 구분한다.

기존 570 시험도 반복했다. 고장 뒤 마지막 E9 수락은 0, 다음 E8의 고장 플래그는 `80`이었다. STOP 전 토큰의 절반과 이후 절반을 합친 잘못된 ACK의 소비는 0회였고, 새 16B를 읽고 전체 토큰을 쓴 경우에만 한 번 소비했다. 고정한 ARM·IRQ·ROM 도착 기록으로 65816을 재생했을 때 두 위상의 53개 화면과 마지막 ACK(87,545,284 / 88,254,606 master clocks)가 570과 같았다. 952·957 모두 표시 간격은 5 VBlank, 최종 준비 뒤 추가 대기는 0회였다.

## Quartus Lite 전체 보드

세 후보는 570과 같은 제약·seed로 전체 FIT을 통과했다. 아래 미제약 수는 implementation의 출력 setup / hold 경로 수다. WNS 회귀는 MMC558보다 나빠진 음수 코너·클록 항목, TNS 회귀는 해당 합이 더 음수가 된 항목 수다. 대상 setup/hold와 85°C ROM_OE는 원래 제약의 slack이다.

| 후보 | LE | 대상 setup / hold (ns) | 미제약 출력 setup / hold | WNS / TNS 회귀 | 85°C ROM_OE (ns) |
|---|---:|---:|---:|---:|---:|
| A · aperture reset | 15,214 | −0.024 / +0.156 | 3,008 / 3,011 | 3 / 8 | +1.199 |
| B · 읽기 허가 | 15,203 | −0.750 / +0.140 | 2,998 / 3,001 | 4 / 7 | −0.503 |
| C · 출력 소유권 | 15,266 | +0.188 / +0.145 | 3,008 / 3,011 | 5 / 8 | −0.618 |

MMC558의 출력 집계는 3,015 / 3,018, 570은 3,018 / 3,021이었다. 570 대비 A와 C는 DATA 8핀·OE·DIR에서 각각 한 경로, B는 각각 두 경로가 줄었다. 모두 8,390 FF와 51 M9K를 사용했다. 원래 제약으로 측정한 ROM_OE는 PSRAM용 출력이다. SNES 버스용 OE와 구분한다.

85°C에서 host 레지스터부터 SNES OE / DIR / 가장 느린 DATA 핀까지의 배치 지연은 570의 18.344 / 18.194 / 27.148ns에서 A의 16.023 / 15.031 / 24.101ns가 됐다. B는 18.421 / 19.481 / 25.096ns, C는 19.192 / 20.774 / 30.899ns였다. 별도 IO 조회의 /RD 입력 → OE는 570 24.16ns, A 19.41ns였다. 이는 내부 배치 지연이며 외부 트랜시버·실제 SNES 입력 타이밍은 포함하지 않는다. RTL에서는 주소 변경 후 세 번째 host 에지에 새 태그가 유효해졌고, 네 주소 변경 위상에서 23.810–35.712ns로 기준과 일치했다.

A에서 MMC558 대비 악화된 WNS 세 개는 모두 참조 고장 신호에서 168MHz memory_release로 가는 recovery였다. 85°C는 −5.660 → −6.571ns다. 별도로 loader pending → start의 대상 setup이 −0.024ns다. C는 이 대상 setup을 통과했지만 원래 ROM_OE와 전체 WNS 다섯 항목에서 회귀했다. 세 후보 모두 실기 전달 보류다. 두 시작 위상의 밀집 표시 간격은 종전 83.157 / 83.121ms로 유지됐다. 재생 결과로 실기 FPS를 갱신하지 않았다.

## 다음 작업

A의 loader pending → start와 168MHz memory_release의 recovery를 분리해 추적한다. START 수락·고장 차단·인가 후 해제 순서를 보존하면서 원래 제약으로 두 경로를 모두 개선할 수 있는지 먼저 판정한다. 실기 진입 전에는 MMC558 대비 전체 WNS·TNS와 핀 경로를 다시 비교한다.

## 재현

`prepare_nes_bus571.py`에 MMC558 보드를 전달해 A를 만든다. B에는 `--read-mask`, C에는 `--owner-mux`를 추가한다. `check_nes_bus571.py`를 기존 Starter FLOAT wrapper에서 기준과 각 후보에 실행한다. `--fixture`에는 570 로컬 해제 보드의 wire05/local 재현 입력을 쓴다. Quartus Lite 전체 compile과 기존 `timing506.tcl`, gate570·arg564·pins565·owner562·snes570 보고서를 실행한다. `report_nes_bus571.tcl`은 MMC558·569·570과 후보에서 별도 IO 조회를 수행한다. 두 위상의 65816 소비 재생 후 `analyze_nes_bus571.py`로 확인한다. [측정값과 입력 해시](../analysis/bus571-verification.json)
