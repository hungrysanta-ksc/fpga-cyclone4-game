# 762 · PPU 포트에서 1,536B map DMA 검사

**753을 유지한다.** Cyclone IV의 배선으로 전송 바이트를 검사할 수 있다. 마지막 바이트를 확인하는 후보는 957을 두 번째 VBlank로 앞당기지 못했고, Quartus Lite 전체 FIT에서 M9K 한 블록이 부족했다. [계측과 원시 기록 해시](../analysis/watch762-verification.json)

## 관측 위치와 표시 조건

원본 Cyclone IV QSF는 주변장치 쓰기 신호를 C9에, PA[7:0]을 E9/D9/L4/N1/L1/L3/K5/L2에 배정한다. 707D의 실제 보드 QSF에는 이 아홉 입력이 빠져 있다. 762는 WRAM 읽기 중 수신 방향으로 트랜시버를 열고, 84MHz에서 동기화한 /PAWR 종료 에지 직전의 A주소·PA·데이터를 사용했다. 확인 범위는 PPU의 $2118/$2119에 보낸 값이다. PPU 내부 VRAM 저장은 Mesen에서 별도로 확인했다. 실기 전기 타이밍·핀 계측은 미검증이다. [Cyclone IV 핀맵](../src/fpga/pin.qsf) · [카트리지 커넥터 도면](https://gamesx.com/wiki/lib/exe/fetch.php?media=schematics%3Apinout_cartridge_slot.pdf)

FPGA는 E1의 일반 map payload를 4,096B 참조 RAM에 저장한다. BEGIN이 대상 뱅크·행 유효성을 초기화하고 정렬된 literal의 마지막 바이트가 행을 완성한다. 적용할 수 없는 쓰기는 해당 행 또는 전체 이력을 무효화한다. E1 수신 도중의 참조는 해당 거래의 CRC 판정까지 결과를 공개할 수 없다. 65816이 기존 우선순위 검사를 거쳐 1,536B map 전송을 시작할 때 선택한 뱅크의 WRAM 시작 주소를 기록한다. FPGA가 byte마다 source 주소·수신 방향·교대하는 $2118/$2119·해당 행의 원본과 실제 값을 비교한다. 마지막 동기 RAM 비교가 끝난 뒤 결과를 한 번 읽어야 표시 경로로 진행한다. 진행 중이거나 검사가 실패하면 독립적인 큐 측 SEAL ACK 검사도 거부한다. [보드·ROM 생성기](../tools/prepare_nes_watch762.py) · [검사 RTL](../tests/nes-functional/nes_map_watch762.sv)

## 결과

| 957 및 밀집 구간 | 위상 1 · 753 → 762 | 위상 2 · 753 → 762 |
|---|---:|---:|
| 952 / 957 선행 map DMA | 각각 1,536B 유지 | 각각 1,536B 유지 |
| 957 OBJ DMA 시작선 | 246 → 247 | 246 → 246 |
| 957 표시 간격 | 3 → 3 VBlank | 3 → 3 VBlank |
| 951→957 평균 표시 간격 | 49.909830 → 49.912872ms | 49.912453 → 49.914673ms |
| 957 최종 ACK, 리셋부터 master clock | 65,365,252 → 65,365,140 | 66,080,216 → 66,080,216 |

753의 53화면 수신 기록을 두 위상에서 재생해 기존 8,719 / 8,720개 이벤트와 일치하는지 확인했다. 762의 정적 65816과 기존 ARM을 리셋부터 실행했고, 두 위상 모두 53개 RGB가 753과 일치했다. 952·957 각각 1,536개의 PPU 쓰기가 원래 E1의 값과 일치했고, 마지막 PPU 쓰기 → 결과 읽기 → 표시 → 최종 ACK 순서를 확인했다. 951 공개선은 236선, 957 최종 대기는 0회였다. SPI·IRQ·NES ROM 경쟁은 기존 모델을 사용했다. 실행 일정의 FPGA 상태 응답은 동작 모델이고, 같은 핀 조건의 RTL 검사는 별도 Questa 시험이다.

두 버스 샘플링 위상의 RTL 시험에서 마지막 바이트 1비트 손상, 마지막 쓰기 직전 STOP, 잘못된 포트·source 주소, 누락 및 추가 쓰기를 주입했다. 1,535B만 보낸 뒤 성공 SEAL을 직접 제출해도 큐가 최종 ACK를 반환하지 않았다. 65816 독립 재생에서는 위상 1에서 마지막 관측 바이트를 손상시키고 위상 2에서 끝에서 두 번째 바이트에 STOP을 걸었다. 두 경우 모두 52개 표시 후 956 RGB를 보존했고 957 표시·최종 ACK가 없었다. 실기 메뉴 복귀는 이번 진단에서 재시험하지 않았다.

ARM은 기존 212,960B 이미지를 사용했다. 정적 65816 ROM 여유는 61B에서 19B가 됐다. Cyclone IV의 기존 배치는 M9K 56/56, LAB 962/963이다. 같은 장치·seed의 전체 Quartus Lite 빌드는 **M9K 57/56**에서 실패했다. 배치 후 STA 및 실기 전달본은 없다.

## 다음 검증

753의 957 입력 시작→planner는 17.424 / 17.422ms였다. 양쪽 모두 956 최종 ACK 전에 17블록 중 8개가 확인됐다. D1 거래 6.238ms, ARM 복원에서 D2 준비까지 3.133 / 3.129ms, D0·D2 거래 2.823ms가 포함된다. 첫 BG의 ROM 요청→첫 허가는 2.574 / 2.306ms다. 같은 ROM 허가 일정에서 직전 구간의 마지막 24개 허가를 모두 쓰려면 첫 요청이 실제보다 적어도 **13.342 / 13.610ms** 빨라야 한다. 이 값은 다른 요청이 이 허가를 점유하지 않는 조건의 필요량이다. 우선 D1과 ARM 복원·credit 반환을 겹치고, 선행 수신 중 실제 BG 주소가 확정되는 시각을 측정한다.

## 재현

1. `prepare_nes_watch762.py --board <temp>/nes-bg707-board04 --client ../probes/nes-static751/sharedfast --raw ../probes/nes-reuse635/client04 --out <temp>/nes-watch762-05`. 이 프로젝트에서 Quartus Lite `quartus_sh --flow compile board`를 실행한다.
2. 기존 `run_nes_credit753.ps1 -Variant prefix`의 인수를 사용해 실행기를 `test_nes_watch762.py`, client를 생성한 client, 출력명을 `nes-watch762-run1` 및 `run2`로 바꾼다. 시작 클록은 7,288,416 / 7,467,100이다. `replay_nes_watch762_trace.py`는 기존 prefix 기록과 기존 client로 `nes-watch762-base1/2`를 생성한다.
3. `check_nes_watch762.py --trace <temp>/nes-watch762-base1 --packets <temp>/nes-credit753-prefix1/packets.jsonl --board <project>/board --out <temp>/nes-watch762-rtl04`. `WATCH762_TEST`를 이 출력으로 설정하고 기존 FLOAT 래퍼에서 `run_nes_watch762_questa.ps1`을 실행한다.
4. `replay_nes_watch762_fault.py`에 정상 후보 기록·client·Mesen 경로와 `--fault data` 또는 `--fault stop`을 준다. 출력명은 `nes-watch762-data01/stop01`이다. `analyze_nes_watch762.py --temp <temp> --out analysis/watch762-verification.json`이 두 일정과 RTL·FIT 근거를 대조한다.
