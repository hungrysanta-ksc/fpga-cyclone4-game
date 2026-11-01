# 529. Flash 회수와 MMC529 실기 전달본

## 빌드

528의 링크 옵션이 예전 80/96KiB 진단 ROM 전용 `nes_mcu_load_probe`를 강제로 보존하고 있었다. 이번 시험 빌드에서 그 강제 옵션 한 개를 제거했다. 링크 시 해당 함수 912B와 전용 SPI 보조 함수 206B·126B가 함께 제거됐다. 남은 787개 함수의 이름·크기를 대조했고, 실제 MMC3 로더·readback 검증·검증 후 START 진입점이 ELF에 남았음을 확인했다. 함수 주소는 다시 배치됐다. 메뉴·ROM·FPGA·로그·버전의 식별자는 529로 갱신한 뒤 이 바이너리를 검증과 포장에 공통 사용했다.

| 메모리 | 528 | MMC529 |
|---|---:|---:|
| STM32 Flash 이미지 | 213,492B | 212,248B |
| 212,992B 한도 대비 여유 | −500B | +744B |
| BSS | 18,592B | 18,592B |

## 표시와 복구 검증

| 시작 클록 | 952 표시 간격 | 954 표시 간격 | 밀집 951–955 평균 | 957 최종 ACK | MMC524 대비 최종 ACK |
|---:|---:|---:|---:|---:|---:|
| 3,000,000 | 8 VBlank · 133.128ms | 7 VBlank · 115.236ms | 113.142ms | 110,034,594 | 99.832ms 빠름 |
| 3,178,684 | 8 VBlank · 133.112ms | 7 VBlank · 115.256ms | 113.150ms | 109,677,398 | 66.563ms 빠름 |

같은 ROM 일정과 시작 클록에서 링크된 ARM과 65816을 905–957까지 실행했다. 각 위상에서 528과 전체 패킷과 도착 클록, 모든 65816 소비 이벤트, OBJ ROM 일정, RGB 53개와 마지막 ACK가 일치했다. 독립 재생에서도 8,341/8,359개 이벤트의 클록, SEAL DMA·빔 좌표와 RGB가 일치했다. 527 대비 마지막 ACK는 66.549/66.541ms 빨랐고, 952·954의 마지막 표시 단계는 각각 한 번의 VBlank를 기다렸다. 이는 ROM 허용 구간, SysTick, 공유 SPI를 포함한 시뮬레이션 측정이다. [528 대조군](nes-quiet528-results.ko.md)

- 실제 전달용 ARM에서 END 후속 공급 경계 9건, 첫 map 경계 9건, 기존 응답 회귀 40건과 1–40초·40–60초 표시 카운터의 경계를 통과했다.
- 두 뱅크에서 STOP·새 head 우선, 독립 검사 실패, 이전 화면 유지와 cold 복구를 검증했다. 254번 행의 map DMA는 64B를 전송했고 255·256번 map 및 233번 tile은 거부됐다. 233번 tile 단위 시험은 현재 906에서 기대한 두 tile 명령이 함께 대기하지 않아 기존 526의 해당 입력으로 재실행했다. 초기 두 fixture 실패는 `nes-flash529-stop01/02`, 최종 비교는 `stop03`이다.
- 실제 ARM 메뉴 복구 코드에서 정상 base 복구와 programmer·DONE·busy·token 오류 시 안전 반환 차단을 확인했다. 이 시험의 주변장치는 모델이다. 실물에서의 실행·표시·메뉴 복귀는 사용자 시험으로 확인한다.

## 전달본과 재현

`MMC529-TRIAL.zip`은 503,260B다. 독립적으로 두 번 포장한 ZIP의 SHA-256은 모두 `a3a2a87edcfc4b9e9f28ca3130ca85027033c5bee9d23c9ec9207407de81b2a5`였다.

[MMC529 설치·비교 순서](nes-mmc529-trial.ko.md), [시간·메모리 검증](../analysis/flash529-verification.json), [ZIP 구성·파일별 SHA-256](../analysis/flash529-package.json)을 사용한다. ZIP에는 MMC529 펌웨어와 검증한 526 board SOF에서 Quartus Lite로 변환한 FPGA 이미지, 기존 MMC524에서 해시를 확인한 base·메뉴와 새 실행 항목을 넣었다. ROM과 RESTORE는 제외했다.

[준비기](../tools/prepare_nes_flash529.py)의 입력은 528 빌드 `probes/nes-quiet528/ARM01/src`다. 생성한 파일을 [ARM 빌더](../tools/build_nes_mmc479_arm.ps1)의 Patch로 사용한다. [공동 실행기](../tools/test_nes_quiet528.py)로 528과 동일한 fixture·calendar·client를 사용해 두 시작 클록에서 실행한 뒤 `--trace`로 독립 재생한다. [검증기](../tools/analyze_nes_flash529.py)로 CRC·STOP·표시·복구 결과와 SOF 해시를 대조한 뒤 [포장기](../tools/package_nes_flash529.py)로 만든다. 설치물은 저장소 부모의 `probes/nes-flash529/trial01/MMC529-TRIAL.zip`에 있다.
