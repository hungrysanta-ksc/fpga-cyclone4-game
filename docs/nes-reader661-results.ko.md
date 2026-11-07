# 661 · PSRAM reader와 SPI D1의 배치 후 타이밍

660에서 남은 168 MHz와 84 MHz setup 위반을 해소했다. 선택한 `mux` 보드는 두 시작 위상 모두 660과 동일한 시각에 표시·최종 ACK를 완료했다. 실기 측정 기준은 MMC643이다.

## 수정과 배치

168 MHz의 최악 경로는 reader의 IDLE 재진입과 요청 허가가 결합된 `state[0] → state[0]`이었다. CHECK 요청의 허용 여부는 reader가 idle일 때 한 번 판정하도록 바꿨다. 상위 모듈은 잘못된 CHECK를 원래와 같은 edge에 fault로 기록한다. reset 해제 때 CHECK와 RUN 허가를 각각 저장하고, SETUP에서 시작한 고정 길이 shift register가 sample·HOLD·RELEASE를 순서대로 발생시킨다. 응답이나 핀 활성 구간을 한 클록 미루지 않는다.

84 MHz 위반은 SPI의 `cells[1] → miso_hold`였다. D1 첫 바이트에서 이미 확보한 블록 크기를 재사용한다. RAM의 현재 바이트 주소를 직접 보관하고, 마지막 payload 바이트에서 CRC 상위·하위 바이트로 전환한다. 두 CRC 바이트 직후의 SS 해제만 완료로 인정한다. 짧은 D1과 초과 D1은 read credit을 만들 수 없다.

| Quartus Lite 25.1 전체 보드 | 660 | 661 mux |
|---|---:|---:|
| LE / 15,408 | 15,331 | 15,324 |
| LAB / 963 | 963 | 962 |
| M9K / 56 | 56 | 56 |
| 조합 함수 / FF | 14,479 / 8,370 | 14,418 / 8,386 |
| 168 MHz setup, ns | −1.038 | +0.511 |
| 84 MHz setup, ns | −0.159 | +0.616 |
| 전체 hold / recovery / removal / 최소 pulse width, ns | +0.148 / +0.824 / +0.370 / +2.635 | +0.149 / +1.828 / +0.393 / +2.630 |

새 배치에서 reader 내부 경로의 최소 setup은 +1.684 ns, MISO 레지스터로 끝나는 경로는 +1.947 ns다. 전체 최악 경로는 loader의 `phase[4] → loaded_bytes[4]`다. ROM_OE / ROM_1CE / ROM_2CE 최소 slack은 +2.142 / +5.058 / +5.488 ns이고 BG 반환 CDC 8비트는 +22.689 ns 이상이다. 같은 디바이스·seed·제약을 사용했고 세 corner의 보고된 모든 검사에서 TNS는 0이다. 미제약 클록은 0개다. 기존 미제약 I/O 집계는 입력 54개, 출력 setup 56개·hold 57개로 660과 동일하다. SOF를 생성했다.

reader만 바꾸고 길이를 재사용한 두 구조는 968 / 969 LAB, loader의 중복 상태 판별을 제거하면 964 LAB였다. SPI를 CRC 단계로 나눈 후보는 964 LAB였다. 주소를 직접 저장한 `index`는 963 LAB에 배치되고 전체 setup +0.155 ns였다. 여기에 reader 소유자 허가를 분리한 `mux`는 962 LAB에서 최소 setup 여유가 +0.511 ns로 커졌다. [모든 구조의 FIT 보고서 해시·측정값](../analysis/reader661-verification.json)

## 기능과 연속 일정

- 660과 661의 메모리 핀·주소·데이터·응답을 1 / 3 / 16 read clock에서 비교했다. 각각 48번의 reset·소유권 전환을 넣었고 실제 보드의 16클록에서는 RUN 47회와 CHECK 104회가 완료됐다. 비동기 취소 직후 CE·OE 해제도 검사했다.
- 최종 보드 RTL로 384 KiB를 적재하고 전체 PSRAM·원주소 CHECK·core 읽기를 확인했다. 53세대의 BG 허가 주소·순서 및 121개 chunk의 token·내용 9,072 B가 660과 같았다. 954 / 955의 BG 허가는 80 / 72회다. 부분 BG의 둘째 바이트와 진행 중 응답에서 STOP을 걸고, 늦은 발행 차단·cold 재시작·독립 주소와 세대 검사를 확인했다.
- SPI는 660을 같은 입력으로 함께 구동해 MISO·ready·fault·완료를 매 호스트 클록에서 대조했다. 모든 D1 바이트와 준비 클록이 같았고, EOF에서 1 B 부족·정확·1 B 초과를 구분했다. 같은 링크 ARM을 실행해 정상 메뉴 해제와 base 복구, 실패 네 종류에서의 잘못된 메뉴 해제 차단을 확인했다.

| 905–957 연속 일정 | 위상 1 | 위상 2 |
|---|---:|---:|
| 954 / 955 표시 간격 | 3 / 3 VBlank | 3 / 3 VBlank |
| 954 SEAL 여유, 648의 직전 표시 기준 | 1.523187 ms | 1.234088 ms |
| 951 공개선 / 957 최종 추가 대기 | 239 / 0 | 239 / 0 |
| 951–955 평균 표시 간격 | 53.243950 ms | 53.243671 ms |
| 957 마지막 ACK, master clock | 67,879,890 | 68,237,054 |
| 657 대비 마지막 ACK 단축 | 33.043675 ms | 16.408229 ms |

53개 화면 각각의 RGB·map, 실제 ARM·65816 실행의 DMA/ACK 로그와 SPI·ROM 일정을 대조했다. CPU 일정은 실측 기반 ROM 허가 달력과 IRQ/SPI 서비스 모델을 사용한다. RTL 핀 시험과 CPU 재생은 별도로 실행해 grant·바이트·준비 클록으로 연결했다. 재생의 마지막 ACK는 두 위상에서 660과 정확히 같은 master clock이다.

## 재현·인계

1. `tools/prepare_nes_reader661.py BASE OUT mux`에 657 port 전체 보드를 지정한다. 660 owner 생성기를 거쳐 위 수정만 적용한다. `quartus_map board` 후 `tools/bind_nes_bg659_sdc.py OUT`으로 A&S가 병합한 레지스터 이름만 연결하고 `quartus_sh --flow compile board`를 실행한다. 최종 보드 입력 79개를 재생성해 일치시켰다.
2. 배치 후 `report_nes_oe612.tcl`, `report_nes_word660.tcl`, `report_nes_reader661.tcl`을 Quartus가 읽을 수 있는 ASCII 빌드 디렉터리로 복사해 각각 `quartus_sta -t`로 실행한다. `check_nes_reader661.py`로 핀, `check_nes_d1661.py`로 SPI 정상·경계, 기존 `check_nes_word660.py --decoded`와 `check_nes_word660_guards.py --policy short`로 staging·STOP을 검사한다.
3. 661 SPI가 생성한 sender 시각을 660과 같은 `test_nes_word660.py --emit` 재생에 연결한다. `analyze_nes_reader661.py`가 두 시작 시각, 기준 화면, FIT·STA 및 메뉴·복구 검사를 대조한다.
4. 다음 단계는 661 SOF·기존 ARM·65816의 설치 파일과 로그 식별자를 고정한 뒤 제한 SMB3 실기로 넘기는 것이다. 같은 첫 레벨의 5–40초·40–55초 표시 횟수, 시작·스테이지 진입·STOP·메뉴 복귀를 MMC643과 비교한다.
