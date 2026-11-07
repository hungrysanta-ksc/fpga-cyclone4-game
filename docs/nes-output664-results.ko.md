# 664 · MMC662 출력 비용과 section 5 선행 발행

PR153의 master 병합 `9a1aa775871ea6d5f19eedc9dc97e3e05f339a31`을 확인하고 `codex/nes-output-budget-664`에서 시작했다. 실기 기준은 MMC662이며 원본 ZIP·661 mux 보드·637 65816 client를 보존한다.

## 측정 범위

MMC662 실기 평균 출력·최종 ACK **26.510ms**는 1,224개의 완료 표시를 합산한 값이다. 단계별 DMA/VBlank 타임스탬프가 없는 이 값을 임의 비율로 나누지 않는다. 별도로 고정된 905–957의 53화면을 실제 링크 ARM·65816으로 실행한다. 시작은 7,288,416 / 7,467,100 master clocks, ARM CPI 2·SysTick·실측 기반 공유 SPI 서비스·반복 ROM 허용 달력·두 bulk 슬롯을 모두 유지한다. 서로 다른 플레이 장면의 평균과 이 재생 결과를 구분한다.

전달 ARM662의 798개 함수가 기존 654 combined와 바이트 단위로 같음을 확인했다. 원본을 두 위상에서 다시 실행해 기존 661 일정의 53개 최종 ACK 시각과 모두 일치했다. 후보는 map 목적지·바이트·횟수, OBJ payload·slot 순서, section 5 확장 바이트를 맞추고 최종 map/화면 RGB/CGRAM/OAM을 독립 확인했다. 원본·prefix·all 각 두 위상, 총 318화면을 완료했다. 실기 입력을 다시 캡처한 시험은 아니다.

## 원본 출력 구간 분해

다음은 cold 905를 제외한 52화면의 평균이다. 중첩된 SPI·65816 서비스 시간을 다시 합산하지 않는다.

| 서로 겹치지 않는 시간 구간 | 위상 1 | 위상 2 |
|---|---:|---:|
| 출력 진입→SEAL 발행 완료 | 15.801ms | 15.859ms |
| SEAL 큐 대기→65816 수락 | 0.074ms | 0.078ms |
| 독립 검사 | 1.624ms | 1.623ms |
| 업로드 중 VBlank 대기 | 9.450ms | 9.380ms |
| SEAL 수락 이후 직접 DMA | 0.546ms | 0.567ms |
| 나머지 CPU 설정·진행 | 1.129ms | 1.126ms |
| 최종 단계의 추가 VBlank 대기 | 0.288ms | 0.288ms |
| 최종 ACK→ARM 반환 | 0.330ms | 0.340ms |
| 합계 | **29.242ms** | **29.263ms** |

마지막 추가 대기는 906에서 한 번 발생한다. 밀집 951–955와 957에서는 이미 0회다. 따라서 '마지막 대기를 없애기'만으로 밀집 구간을 줄일 수 없다. SEAL 이전에 실행한 DMA는 발행 구간과 겹치므로 위 직접 DMA 행에 중복 합산하지 않는다.

## 952의 놓친 업로드 기회

위상 1의 첫 스크롤 패킷은 직전 표시 후 34.056ms에 준비됐지만 SPI 시작은 42.975ms였다. **8.919ms가 데이터 계산 완료 후의 계획·bulk 대기**였다. 1,100B 패딩은 실제 wire payload 2B이며, 65816 수락→개별 ACK는 약 1.497ms다.

원본 SEAL은 두 위상에서 218 / 223번 선에 수락됐고 독립 검사 뒤 업로드 진입은 243 / 248번 선이었다. 위상 1은 16B tile·384B map을 먼저 DMA했지만 253번 선에 이르러 남은 타일을 다음 VBlank로 넘겼다. 그래서 최종 추가 대기 0회여도 952 전체 표시 간격은 4 VBlank다. 최종 ACK 이후의 polling만 줄이는 것으로 이 기회를 회수할 수는 없다.

## 분리한 두 후보

`prefix`는 scroll·padding(시작 offset <1121)에만 기존 ordinary progress/credit 정책을 사용한다. raw·테이블은 기존 HDMA 대기를 유지한다. `all`은 확정된 section 5 전체에 같은 정책을 사용한다. 둘 다 실제 `packet_wire`의 진행 모드 선택만 바꾼다.

새 opcode·캐시·FPGA 회로·65816 코드는 추가하지 않는다. 계획 공급은 E8/E9·준비된 bulk를 우선하며, bulk가 남아 있으면 기존 네 credit 중 두 개 이하를 사용한 상태에서만 ordinary를 허용한다. section 5는 별도 WRAM에 수신되고 독립 검사를 통과한 SEAL 뒤에만 PPU에 사용된다. SEAL의 `NES_FINAL553`은 모든 END·bulk 소비 완료를 계속 요구한다. 최종 ACK 전 이력 확정이나 EA retire는 허용하지 않는다.

원본 212,508B 대비 prefix는 212,516B(여유 476B), all은 212,496B(여유 496B)다. 세 구성의 data 10,040B·BSS 19,544B는 같다. 661 전체 보드 15,324 LE·962 LAB·56 M9K와 SOF/전체 FIT·STA 해시를 고정하므로 이번 ARM 시험의 회로 추가 비용은 없다. 변경 없는 합성을 반복하지 않는다. 이는 외부 IO 전체 sign-off의 새 증명이 아니다.

## 결과와 다음 판단

| 구성 | 952 표시 간격 | 밀집 951–955 평균 간격, 위상 1 / 2 | 957 ACK 단축, 위상 1 / 2 |
|---|---|---|---|
| MMC662 | 4 / 4 VBlank | 53.243950 / 53.243671ms | 기준 |
| prefix | 4 / 4 VBlank | 53.242628 / 53.243540ms | 0.235598 / 0.225541ms |
| all | **3 / 3 VBlank** | **49.919878 / 50.016930ms** | **0.026447 / 16.639450ms** |

prefix는 첫 스크롤 준비→발행 대기를 8.919→0.304ms로 줄였지만 첫 raw 패킷이 6.950ms를 기다렸다. 대기 위치가 옮겨져 밀집 평균은 0.001322 / 0.000130ms만 줄었다. 이 미세 차이를 실기 FPS 향상으로 주장하지 않는다.

all은 952 출력 첫 E1→SEAL 발행을 25.139 / 25.483→22.917 / 23.132ms로 줄였다. 업로드 대기는 14.656 / 14.712→0.474 / 0.474ms가 됐고, 밀집 다섯 간격 합계는 두 위상 모두 **16→15 VBlank**다. 951 공개선은 239 / 239, 954·955는 3 / 3 VBlank, 957 최종 추가 대기는 0회를 유지했다. [측정 JSON·원본 해시·guard 결과](../analysis/output664-verification.json)

**실기 기준과 ZIP은 MMC662를 유지한다.** all은 요청한 밀집 간격·957 ACK의 수치 조건을 두 위상에서 통과했지만, 위상 1의 914가 3→4 VBlank로 회귀했다. 이 한 번의 추가 대기가 952의 절감 대부분을 상쇄해 누적 ACK 이득이 26µs에 그쳤다. 따라서 `candidate_gate=true`, `release_ready=false`를 따로 기록했다. 검증을 통과한 all을 후속 개발 후보로 보존하되 바로 전달하지 않는다.

## 다음 병목: 914의 246번 선 경계

914의 SEAL은 더 일찍 도착했고 map·tile 작업량과 선행 DMA(0B map / 16B tile)도 같았다. 그러나 VBlank polling 위상 차이로 첫 DMA command가 225번 선 h680→h918, 최종 credit 검사가 246번 선 h98→h336으로 **238 master clocks(약 11.08µs)** 늦어졌다. 원본은 같은 VBlank의 최종 표시 경로로 진입했고 all은 기존 246번 선 검사에서 다음 VBlank를 기다려 **15.239ms**를 추가했다. 직접 DMA 평균 바이트 비용을 줄이는 문제와 구분된다. 위상 2에는 이 새 대기가 없다.

후속 순서는 다음으로 고정한다.

1. all의 선행 발행을 고정하고 914의 `wait169` 반환·첫 DMA 설정·raw 두 묶음·최종 credit 검사 시각을 대조한다. 246번 선 조건을 늦추지 않고 VBlank 진입 지연과 설정 비용을 줄여 이 약 11µs 경계를 회수할 방법을 검증한다. 특정 generation/시작 위상에 맞춘 상수 대기는 추가하지 않는다.
2. 같은 53화면·두 시작 위상에서 914의 새 추가 대기가 없어지고, 952 3 VBlank·밀집 15 VBlank·951 공개선·957 추가 대기 0회와 마지막 ACK 이득이 유지되는지 판정한다. 915/954의 map 선행량 감소도 함께 확인한다.
3. 실제 65816 ROM이 바뀌면 독립 검사·STOP·부분 복원·메뉴 복귀를 재검증하고 보드 ROM 결합 후 전체 Lite FIT·STA를 확인한다. 그 전에 설치본 번호를 새로 만들지 않는다.

## 재현과 보존

- `prepare_nes_output664.py BASE OUT --mode prefix|all`: MMC662 패키지 firmware 해시를 확인한 뒤 별도 ARM 트리를 생성한다. `build_nes_trial577.ps1`로 전체 링크한다.
- `test_nes_output664.py`는 660/661과 같은 board-bound sender·ROM 달력·실제 ARM·65816 경로에 읽기 전용 packet/credit 계측을 추가한다. 상세 인자는 로컬 `probes/nes-output664/replay.ps1`에 보존하고 원본/후보 산출물은 ASCII Temp의 `nes-output664-base1/base2/prefix1/prefix2/all1/all2`에 둔다.
- `check_nes_output664.py`는 실제 패킷 조립·CRC·큐 수락과 진행 모드·STOP 경계 12조건을 확인한다. 진행 결과를 주입하는 단독 시험이며 전체 독립 검사의 대체물이 아니다. 연결 재생에서 모든 최종 표시 바이트를 다시 확인한다.
- 실제 링크 후보마다 수신의 정상/IO/CRC/service/deadline, 잘못된 credit·중간 STOP·최종 ACK, 메뉴 4종 및 base 정상/실패 5종을 검사한다. FPGA 캡처 회복 회로는 변경하지 않고 661 검증·MMC662 실기 회복 기록을 보존한다.
- 최초 workspace 한글 경로의 Lua ROOT escape 때문에 pipe가 열리지 않은 실행은 `probes/nes-output664/base1`에 보존했다. 기존 ASCII Temp로 옮겨 실행한다. 최초 빌드의 임시 드라이브 매핑 권한 오류도 제품·Questa 실패와 구분한다. 이번 시험에는 Questa 좌석을 사용하지 않는다.
- 1,420개 실행·바이너리·수정 소스·guard 산출물을 로컬 `probes/nes-output664/archive01/evidence.zip`에 보존하고 압축 해제 바이트의 해시를 전부 재검증했다. `manifest.json` SHA256은 `ccab9b95a922f97961cf31077b0b8fc492f48bbb0d0c5ce794c64c66e45526f9`다. 이 private archive와 상용 ROM/화면 데이터는 Git에 넣지 않는다.

연속 시험 진입점은 아래와 같다. 대문자 경로는 기존 로컬 증거이며 clone에 포함돼 있다고 가정하지 않는다. 각 자료의 해시는 분석 JSON과 기존 661/662 증거로 확인한다. 두 시작 시각은 7288416과 7467100이고, 같은 CLI에서 `ARM_SRC`만 원본/prefix/all로 바꾼다.

```text
python tools/test_nes_output664.py --emit --geometry650 --commit-pop-bound --keep-run --game GAME_NES --sender653 SENDER661_JSON --arm ARM_SRC --client CLIENT637 --samples STIM601_TSV --data DELTA231_TEST07 --fixture DENSE519_FIXTURE02 --plans SEAL538_PLANS01 --capture OUTPUT489_AUDIT01 --calendar SERVICE509_ROM03 --driver503 analysis/hardware503-mmc502.json --mesen MESEN --start-clock 7288416 --out ASCII_OUT
```
