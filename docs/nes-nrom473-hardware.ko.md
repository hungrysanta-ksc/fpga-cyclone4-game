# NROM473: 사용자가 돌려준 NROM471 이동 장면

2026-10-29. 사용자는 모든 동작이 의도대로였고 메뉴 복귀도 정상이었다고 확인했다. 원본3개 TXT와 IMG_3721.MOV를 바이트 그대로 `probes/nes-nrom473/hardware01`에 보존했다. 분석은 `tools/analyze_nes_nrom473_hardware.py --raw ../probes/nes-nrom473/hardware01 --out analysis/nrom473-hardware.json`으로 재현한다. 이 단계에서 새 firmware/FPGA/합성/설치본은 만들지 않았다.

## 실기에서 확인한 것

- NROM471 label/board ID78, 이동 ROM CRC `0fddf31c`가 전달본과 맞는다. runtime에서 firmware/bitstream 자체의 SHA를 읽은 증거는 아니다.
- 384KiB 적재·동일 길이 readback, verified1/verify_error0, START/RUN/STOP/base 복구/safe_to_reload가 정상이다. 사용자 보고와 progress의 MENU_PREPARED까지 확인했다.
- 60.07초 동안 **1,178회 최종 표시 완료**, 평균 **19.610454fps / 50.993209ms**다. 초기5초78회, 이후5초 bin은100/100/100/100/100/101/100/100/100/100/99회로 대체로20fps다. 표시 최대 gap은10ms tick 기준 초기 포함130ms, 이후 bin50ms다. 프레임별 timestamp가 없으므로 p95는 계산하지 않는다.
- 입력 commit1,179회와 표시 완료1,178회, EA retire1,178회다. 마지막1개 입력은 표시 완료로 세지 않았다. deadline에서 output1packet이 남은 상태를 STOP이 취소했다.
- D1 CRC 오류0/transfer stop0, driver 실패 전송0, input abort0이다. 영상60.4초에서 파랑→빨강→파랑과 이후 빨강 막대, 달라진 막대 위치를 표본 확인했다. pixel exact·카메라 기반 FPS·capture 누락 없음·사운드 합격을 의미하지 않는다.

현재 결과는 **제한 이동 NROM 기능 시험 통과**, 중간 목표30fps 및 최종60fps는 미달이다. 종전469의14.968fps는 정적428 장면이어서 두 숫자로 개선율을 확정하지 않는다. 같은 정적 장면의471 실기 로그는 아직 없다. 입력 압축의 동일 장면 payload/실제 M4 명령 감소 증거는 이전471 분석에 유지한다.

## 실제 DWT 비용

`cost_counter_available=1`, 84MHz cycle 합을 환산했다. 아래는 전체 누계를 완료 표시1,178회로 나눈 값이며 개별 완료 frame의 WCET나 순수 CPU 시간은 아니다. 실패한 마지막 phase는 완료 phase 누계에 포함되지 않으며 IRQ/guard/service/대기가 섞인다.

| 포함 구간 | 누적 | 완료 표시당 평균 |
|---|---:|---:|
| 입력 수신·준비·CRC·해석 | 18.914981s | 16.056860ms |
| BEGIN·계획·plan END 준비 | 16.055916s | 13.629809ms |
| SEAL·출력 drain·표시·최종 ACK | 24.489155s | 20.788756ms |
| 완료 phase 밖의 나머지 | 0.609948s | 0.517783ms |

10ms 누계도1886/1612/2448tick으로 전체와 bin이 일치한다. planner 안의 callback2tick을 제외한 기존 coarse planner 경로는10.738540ms/표시다. 함수 내부 순수 CPU 시간을 세분한 것은 아니다. 전체 DWT phase 합과 opcode 시간을 더하지 않는다.

| SPI 분류 | 호출/표시 | 측정 평균/표시 | 순수 wire 하한/표시 |
|---|---:|---:|---:|
| 입력 D0–D3 | 35.134 | 7.974098ms | 6.217143ms |
| **E0 상태 조회** | **133.460** | **14.692643ms** | **8.134711ms** |
| E8 plan 상태 | 5.066 | 0.557840ms | 0.308798ms |
| E1·E9 합계 | 9.563 | 1.934173ms | 1.472639ms |
| EA retire | 1.000 | 0.069361ms | 0.021333ms |
| 직접 observer70/screen73 | 2.036 | 0.217216ms | 0.049631ms |
| 전체 | 186.259 | 25.445332ms | 16.204255ms |

SPI6,263,451B = 기존 runtime6,244,267B + 직접 observer/screen19,184B다. 기존 runtime 카운터가 빠뜨리던 직접 service도 이번 DWT 카운터에서 포함됐음을 확인했다. 전체 SPI 밖25.547877ms는 IRQ/guard/준비/검사/대기/시작·종료를 포함하고 순수 ARM 계산으로 부르지 않는다. wire 하한도 거의16.667ms를 차지하므로60fps에는 E0 감소가 필수다.

**E1/E9 분류 결함:** `nes_native165_bulk` wrapper는 전송 후 `tx[0]`을 읽는다. E1과 E9가 in-place full-duplex buffer를 쓰면서 opcode가 응답으로 덮여 OTHER로 분류됐다. OTHER569,221B는 기존 별도 budget의 E1552,687B + E916,534B와 정확히 일치한다. 따라서 합계 시간/byte·E0·phase·FPS는 유효하지만 E1/E9 각각의 cycle은 복원할 수 없다. 제품 전송/ACK 결함이 아니며 전달471과 그 증거는 고치지 않는다. 다음 후보에서 전송 전 opcode snapshot과 alias buffer 회귀를 추가한다.

## 종료 필드의 해석

`native_result=1`은 예정된6000tick deadline이다. `guard()`가 최초 원인을 먼저 기록한 뒤 마지막 SEAL/status를 취소하면서 `native_sink_error=2`/`sink_window_error=3`을 남겼다. sent10086/retired10085, 입력 commit−표시 완료1과 일치한다. 이를 CRC 손상이나 RUN 중 첫 실패로 판정하지 않는다. 반대로 미완료 packet을 최종 ACK한 것으로 처리해서도 안 된다. STOP20ms/base850ms/MENU_PREPARED까지의 실제 진행과 사용자 메뉴 복귀 확인을 함께 보존한다. `screen_error=169`는 기존 SPC init 결과 필드이며 trusted screen frame counter가 아니다.

## 다음 작업 순서와 판정

1. **471 실기 조합을 고정한다.** 기존 ZIP과467/164 복원물은 유지한다. 선택 FPGA14740LE/13672comb/8063FF/185824bits, nominal 관련 clock setup+0.081ns/hold+0.143ns, 강화 예산−0.036ns 및 raw CDC/IO 미해결 상태도 그대로다. 새 로그 때문에 합성을 반복하지 않는다.
2. **ARM 계획 재사용과 상태 조회 일정을 함께 바꾼다.** 현재 실기 runtime의4credit 구조를 기준으로 credit·drain·최종 ACK 대기를 구분한다. E0 중 몇 회가 무진행인지 계측하고, 유효한 진행 확인·guard·deadline·STOP 빈도를 유지하면서 안전한 준비 작업을 대기 중 처리한다. 조회 호출 감소 자체를 표시 latency 감소로 단정하지 않는다. final ACK를 조기 반환하거나 수신/표시 소유권을 겹쳐 쓰지 않는다.
3. **warm changed-group/raster 재사용을 연결한다.** epoch/serial/표시 이력/cold/STOP 무효화와 실제 payload·계획 결과를 비교한다. geometry가 정적인 경우에도 palette/A와 실제 scroll 변경은 반영해야 한다. 현재 계획13.63ms와 E0 포함 SEAL20.79ms를 함께 줄이는 후보를 만들며 E0 전체14.69ms를 공짜로 제거해도60fps에 모자란다.
4. **같은 실제 경로로 검증 후 다음 전달을 만든다.** E1/E9 snapshot 수정, STOP/독립 검사/최종 ACK/메뉴 회귀, 같은 이동/정적 ROM을 묶는다. 다음 예약 번호는 **NROM474**이며 marker·로그·ZIP 이름도474로 바꾼다. RTL을 유지하면 FPGA471 byte/hash 재사용을 명시하고, RTL이 바뀌면 같은 source의 전체 Lite FIT/관련 timing을 다시 확인한다. 30fps는 중간 목표이고 capture/display ID·누락·p95·VBlank까지 확인해야60Hz 합격이다.

정적 비교는 이미 전달한 ZIP의03 ROM만 교체해 추가할 수 있다. 그 결과는 개선율 판정에 필요하지만 위 병목 분석과 다음 구현을 막는 조건은 아니다. 이후 같은 게임 T2·실제 MMC4/5 ROM 경쟁 T3로 확장하며 이번 mapper0 결과를 자동으로 일반화하지 않는다.
