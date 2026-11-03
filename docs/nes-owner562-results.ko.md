# 562 · RUN 요청과 메모리 초기화 해제

561은 타일 공개를 앞당겨 952를 5 VBlank에 표시했다. 이번 후보는 ARM·65816·타일 공개 방식을 유지하고 loader와 PSRAM reader 사이의 두 경계만 바꿨다. 실기 기준은 MMC558이다. [561의 비교와 실기 진입 조건](nes-close561-results.ko.md)

## 바꾼 경로

기존 회로에서는 메모리 클록의 loader RUN 비트가 NES 클록의 `request_toggle` 입력을 직접 게이트했다. CHECK도 같은 physical reader를 쓰므로 RUN 조건을 없애려면 요청 주체를 구별해야 한다. 562는 CHECK 동안 NES 쪽을 reset에 두고 RUN 허용을 두 NES 클록 에지로 해제한다. CHECK는 메모리 포트로 계속 읽는다.

기존 `init_done`은 NES RAM 8,192주소의 초기화 완료를 메모리 클록의 비동기 reset 해제에도 사용했다. 562는 기존 NES `core_release`가 끝날 때까지 로컬 ready와 valid를 함께 막는다. 메모리 reader는 RUN 소유권을 받은 상태에서 요청을 기다린다. STOP·SPI fault·외부 reset은 양쪽을 취소하는 경로를 그대로 사용한다. 변경 파일은 `nes_live_joint.sv`, `nes_rom_boot.sv`, `nes_rom_physical.sv` 세 개다.

## RTL 시험의 경계

Questa 한 좌석에서 561과 562를 차례로 실행한다. 각 실행은 실제 loader·physical reader·local memory·reset 체인과 해당 보드의 NES ready/valid 배선을 시험벤치에 연결한다. NES 클록은 약 21.48MHz, 메모리는 약 168MHz다. 실제 SPI·ARM·보드 핀의 전기적 타이밍은 이 시험 범위 밖이다.

각 보드는 합성용 loader의 원래 쓰기 펄스 길이로 시험용 패턴 393,216B를 핀 RAM에 한 번 채운다. CHECK에서 PRG·CHR의 처음·끝을 읽는 동안 NES 요청을 계속 제시한다. START 후 8,192번의 로컬 RAM 초기화 동안 요청을 유지하고 첫 RUN 응답을 검사한다. PSRAM OE가 내려간 뒤 STOP을 걸고, 늦은 응답이 없는지 확인한 다음 CHECK·START로 복구한다. 이어서 952·954에서 복원한 CHR 주소 480개를 해당 위상의 ROM 허가 시각에 맞춰 제시한다. 두 번째 위상은 정지 상태에서 NES 클록 위상을 바꿔 같은 메모리 내용으로 실행한다. 실제 포트가 준비된 에지에 수락하고 이전 데이터와 주소도 확인한다.

선택한 전체 적재 시험에서 기준과 후보 모두 393,216회의 핀 쓰기, 네 번의 RAM 초기화, 두 번의 읽기 도중 STOP과 재시작을 통과했다. 위상마다 수락·응답 965개 이벤트의 주소·값·시각 기록이 기준과 일치했다. 952·954에서 가져온 480개 읽기는 두 위상 모두 수락부터 응답까지 각각 232.810ns(시험 NES 클록 5주기)였다. 취소한 요청의 응답은 재시작 뒤 나타나지 않았다.

## 연속 표시 일정

시작 master clock 3,000,000과 3,178,684에서 561의 연속 일정을 각각 다시 실행했다. 각 위상의 53개 RGB, SPI 패킷, ARM 이벤트, 65816 수락·최종 ACK와 ROM 일정 추적이 561과 일치했다. 952는 5 VBlank, 951–955는 25 VBlank, 평균 표시 간격은 83.157 / 83.121ms였다. 957 마지막 ACK는 MMC558보다 82.989 / 33.501ms 빨랐고, 952·954·957 최종 검사 뒤 추가 대기는 0회였다. 562가 561에 더한 표시 시간 이득은 0이다.

전체 일정은 링크된 ARM·Mesen 65816과 SPI·IRQ·기록된 ROM 허가 달력을 사용한다. 아래의 loader/reader RTL 시험은 별도 실행이다. 실기 FPS는 MMC558에서 측정한 5–55초 13.72fps가 최신이다.

## Quartus Lite 전체 비용

| 동일 기기·seed·제약 | MMC558 | 561 | 562 |
|---|---:|---:|---:|
| LE / 15,408 | 15,164 | 15,256 | 15,213 |
| 조합 논리 / FF | 14,172 / 8,394 | 14,192 / 8,398 | 14,188 / 8,398 |
| M9K | 51 | 51 | 51 |
| 대상 클록 setup / hold (ns) | +0.078 / +0.139 | +0.079 / +0.154 | +0.386 / +0.140 |
| 전체 최악 setup / recovery (ns) | −7.081 / −8.480 | −6.601 / −8.153 | −7.073 / −7.671 |

561의 모든 코너에서 관측된 loader phase→request toggle setup과 init_done→reader memory reset recovery는 562에서 조회되는 경로가 0개였다. 동일 SDC에서 양 끝 레지스터가 배치됐는지 먼저 확인했다. 그럼에도 MMC558의 같은 코너·클록과 비교하면 **기존 음수 항목 7개가 악화**됐다. 메모리 클록 setup 3개, recovery 3개, NES setup 1개다. 기존 미제약 경로 집계는 같다.

- 메모리 setup의 85°C 최악은 `reader.address_hold[11] → reader.check_response_address[11]`의 −5.313ns다. 끝점은 RUN·CHECK가 공유하는 PSRAM 주소 레지스터에서 유래한다. 같은 행의 데이터 경로 지연은 2.432ns다. 현재 설계는 주소를 응답까지 보존하고 요청 토글을 두 단계로 동기화한다.
- 메모리 recovery는 85°C에서 `clock_guard.ref_qualified → memory_release.release_reset[0]`의 −7.017ns다. 나머지 두 코너는 `ref_fault`에서 같은 reset 체인으로 간다.
- 0°C slow 코너의 NES setup은 source epoch의 Gray 값에서 첫 동기화 단계까지 −4.598ns로, MMC558의 −4.586ns보다 0.012ns 낮다.

MMC558의 제한 실기 기준까지 남은 차이는 아래와 같다. 이는 해당 코너의 기존 음수 slack까지 회복하는 데 필요한 값이다.

| 코너 | 메모리 setup | 메모리 recovery | NES setup |
|---|---:|---:|---:|
| Slow 85°C | 0.635ns | 1.357ns | 충족 |
| Slow 0°C | 0.601ns | 1.326ns | 0.012ns |
| Fast 0°C | 0.363ns | 0.717ns | 충족 |

**실기 전달은 보류한다.** 다음 순서는 메모리 클록의 시작 허가와 고장 시 즉시 차단을 분리해 각 클록 정지 시나리오를 검증한 뒤, RUN 주소 전체 비트의 최후 도착과 동기화된 요청의 최초 캡처 시점을 비교하는 것이다. 변경 전후에 동일 seed·제약으로 코너별 음수 항목과 561의 두 표시 일정을 다시 확인한다. [측정값과 경로 양 끝](../analysis/owner562-verification.json)

## 재현

1. `prepare_nes_owner562.py --base <MMC558 보드> --out <새 디렉터리>`로 561의 조기 공개를 적용한 다음 562의 세 모듈을 생성한다.
2. 561·562 보드 디렉터리를 `check_nes_owner562.py --base ... --board ... --bin ... --out ...`에 지정해 기존 FLOAT wrapper에서 실행한다. 저장소의 `owner562-reads1.txt`, `owner562-reads2.txt`는 첫 허가 기준의 경과 tick과 전체 PRG·CHR 이미지 안의 바이트 오프셋이다. 원본 게임 ROM 없이 이 단계를 실행할 수 있다. `--plans`와 `--traces`를 함께 지정하면 561 기록에서 두 입력을 재생성해 검사한다. 내부 빠른 자체 검사는 양 끝 두 바이트만 쓰며 전체 적재 결과와 구분한다.
3. Quartus Lite에서 후보의 `quartus_sh --flow compile board`, 기존 `timing506.tcl`, 기준·561·562 각각의 `quartus_sta -t owner562.tcl` (저장소의 `report_nes_owner562.tcl`을 복사)을 실행한다. 561의 ARM·달력·fixtures로 두 연속 일정을 반복하고 `analyze_nes_owner562.py`로 RTL 증거와 전체 보드 예산을 합친다. 선택 보드는 board01, RTL은 rtl04다. 예비 실행 중 벤치 시간 상수·메모리 클록·마지막 바이트의 완료 조건을 바로잡았다.
