# 577 — 576 적재 타이머·외부 IO 감사와 MMC577 제한 전달

**576 회로를 그대로 사용해 MMC577 제한 시험판을 준비했다.** +0.045ns인 적재 경로는 세 코너에서 양수이며 실제 명령 우선순위를 구현한다. 경로를 제외하거나 타이머를 바꾸지 않았고 새 MAP/FIT도 하지 않았다. 외부 IO의 전체 전기적 검증은 남는다.

## 적재 타이머

85°C 최악 경로는 168MHz control.load_end → loader.remaining[0]이다. 관계 5.952ns, clock skew −0.079ns, data delay 5.829ns, setup slack +0.045ns다. 네 논리 단계이며 IC 3.638ns, cell 1.930ns, uTco 0.261ns다. 모든 remaining 비트의 setup/hold를 세 코너에서 확인했다.

END가 timed phase에서 들어오면 명령 거부와 이미 수락한 WRITE/HOLD의 drain 우선순위를 결정한다. 잘못된 입력에서도 필요한 경로이므로 false path나 다중 주기 예외로 처리하지 않는다. 현재 양수인 경로에 임의 여유 목표를 설정해 반복 배치하지 않는다.

실제 loader를 정상 BEGIN·DATA 입력으로 진입시킨 뒤, SETUP/WRITE/HOLD/RELEASE의 **130개 시점 × 64개 명령·차단 조합**을 두 위상으로 시험했다. 내부 state를 강제로 설정하지 않았다.

| 각 위상의 결과 | 값 |
|---|---:|
| 명령 조합 | 8,320 |
| 실제 발생한 쓰기 | 7,308 |
| busy END 거부 / 차단된 END 무시 | 130 / 130 |
| 최소 RTL SETUP / WRITE / HOLD | 130.944 / 380.928 / 130.944ns |
| 이중 쓰기·drain 미완료·쓰기 중 주소/데이터 변경 | 0 |

위 시간은 RTL 출력의 펄스 길이다. 외부 PSRAM 핀에서 측정한 시간이나 데이터시트 보증값으로 확장하지 않는다.

## 외부 IO의 실제 범위

원래 SDC를 바꾸지 않고 별도 virtual-clock netlist에서 배치 경로를 추출했다. 표는 FPGA 경로 지연이며 외부 수신기의 setup/hold를 뺀 여유가 아니다.

| 최대 경로, ns | MMC558 | 576 |
|---|---:|---:|
| SPI_MISO | 16.592 | 16.421 |
| MCU_RDY | 7.806 | 7.113 |
| SNES_DATA | 24.044 | 26.177 |
| SNES_DATABUS_OE | 18.680 | 18.251 |
| SNES_DATABUS_DIR | 17.478 | 17.860 |
| SNES raw 제어 핀→출력 | 28.620 | 31.892 |
| loader→PSRAM 출력 | 17.503 | 17.572 |

SNES raw 경로는 **+3.272ns**, SNES_DATA는 +2.133ns 늘었다. 외부 경로가 모두 무회귀라고 선언하지 않는다. 입력 54·출력 57개의 전체 min/max 제약이 없는 포트 집합은 MMC558과 같다. 입력은 ROM_DATA·SNES 주소/제어/데이터·SPI, 출력은 ROM 주소/제어/데이터·SNES DATA/OE/DIR·SPI_MISO·MCU_RDY·DAC이다. 기존 ROM CE/OE 세 포트도 일부 제약만 있다.

576의 내부 STA 최악 setup/hold/recovery/removal은 **+0.045/+0.140/+2.364/+0.490ns**로 그대로다. 77개 동기화 chain과 231개 유한 데이터 쌍을 검증한 정확 CDC 정책을 유지한다. 원래 SDC의 raw setup/recovery −8.849/−11.602ns도 보존했다. 따라서 이 전달은 이전 raw SDC 요약이 MMC558과 같은 전달이 아니라, 실제 동기화·reset 경계를 검사한 **제한 실기 후보**다. PCB·수신기·DAC·전원/온도 조건의 전체 sign-off는 아니다. PSRAM 읽기 여유 +3.213ns도 70ns 부품·왕복 각 2ns PCB 가정이다.

## 전달본과 검증

ARM은 실제 MMC558 소스를 빌드해 시험 식별자·메뉴·ROM·로그 이름만 577로 바꿨다. ELF 함수 **792개가 주소·크기·바이트까지 동일**하다. Flash **212,908B / 여유 84B**, BSS **18,592B**로 같다. 이미지 헤더 CRC와 라벨 외 바이트 일치도 확인했다.

새 ARM에서 다음을 실행했다.

- 5–40초·40–55초 경계 tick, STOP 뒤 집계, 미완료 표시 제외.
- bulk·credit·STOP·진행 응답 오류와 선행 공급.
- 메뉴 수락/취소, base 복구 정상·program·DONE·busy·token 실패 분기.
- 실제 FatFS/FPGA programmer에 새 BI3/RBF를 공급하고 압축 해제 바이트·GPIO/DONE 모델을 확인.

정상 base 복구는 완료했고 오류 네 분기는 안전 복귀를 성공으로 공개하지 않았다. 이는 모델 IO에서 실행한 ARM 결과이며 실기의 메뉴 복귀 확인은 사용자 시험으로 남는다.

FPGA SOF는 576과 동일하다. 전체 **15,260LE / 14,191 조합 논리 / 8,407FF / 51M9K**다. 576의 두 위상 53화면·952/957 각각 5 VBlank·최종 대기 0회·마지막 ACK 87,545,284/88,254,606 근거를 그대로 유지한다. 이번 단계에서는 해당 재생을 반복하거나 새로운 FPS로 환산하지 않았다.

[설치 안내](nes-mmc577-trial.ko.md) · [검증 JSON](../analysis/gate577-verification.json) · [패키지 해시](../analysis/trial577-package.json)

ZIP의 base/menu는 MMC558과 같다. ROM·세이브·RESTORE는 포함하지 않는다. 전달 파일은 probes/nes-gate577/trial01/MMC577-TRIAL.zip이다. 사용자가 설치하며 SD 연결을 요청하지 않는다.

## 다음 작업

1. MMC577의 실행·약 60초 뒤 메뉴 복귀와 새 로그 세 개를 확인한다. 실패 시 재실행 전 로그를 보존한다.
2. MMC558과 비슷한 동선의 5–40초·40–55초를 나눠 비교한다. 초반/정적 클리어 구간을 성능 향상으로 포함하지 않는다.
3. 새 실패가 있으면 MMC558 대조와 증상을 먼저 확인한다. 새 입력 없이 epoch 배치·직렬화·seed·양수 timer 경로 최적화를 반복하지 않는다.
4. 실기 근거로 다음 공급/표시 병목을 선택한다. 현재 실측 기준은 MMC558 14.01fps, 5–55초 13.72fps다.

## 재현·실패 보존

report_nes_io577.tcl과 기존 report_nes_bus571.tcl은 기존 세 배치를 읽기만 한다. check_nes_pulse577.py는 한 좌석 FLOAT wrapper로 실행한다. 선택 pulse577-test02는 포트 연결을 명시했으며 test01의 implicit 출력 연결 실패를 보존했다.

prepare_nes_trial577.py → build_nes_trial577.ps1로 같은 ARM 코드를 만든다. 첫 make에서 생성 헤더를 준비하며 발생한 실패를 보존하고, 기존과 같은 bootstrap/build 순서로 성공했다. check_nes_windows518 / tile532 / supply549 --keep-run / menu533 및 transfer512_recovery의 5분기를 실행한다. 처음 5개 transport 시험에 이어 실제 대조군과 같은 --keep-run 9개를 수행했다. analyze_nes_gate577.py가 해시와 결과를 묶고 package_nes_trial577.py가 ZIP을 다시 열어 모든 파일을 검사한다. 기존 558 manifest는 CP949이며 원본을 고치지 않고 읽었다. 새 manifest·설치 안내는 UTF-8이다.

원시 시험·적재/IO 보고서·ARM 빌드·전달본 872파일을 probes/nes-gate577/archive01/evidence.zip에 보존하고 전체 바이트를 검증했다. SHA256은 f29db0ef986dbc64b69f890e409200edb205328876736fbe6de8a3b34a5f55f5이다. 라이선스/서버 로그는 포함하지 않는다.
