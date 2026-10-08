# CF87 메모리 비활성 클록 관측 계약

087은 CF86의 메모리 시험을 확장한 코어가 아니라 **실기 기준 클록 수집을 위한 별도 FPGA 관측 회로**다. CF86/071의 MCU·파일 쌍에 끼워 넣지 않는다. 사용자 기기의 RESET-held 기준 클록은 아직 측정하지 않았다. 현재는 RTL·새 fit/내부 STA·배선 감사 단계이며 ARM/ASM/실기 설치 패키지는 없다.

## 기존 base를 그대로 사용하지 않은 이유

보유 workspace의 `fpga_base.bi3`90개를 전체 해시 비교했다.88개는18바이트짜리 시험 fixture이고, 나머지2개는 수신 원본과075 동결 사본이다. 실제 파일 SHA256은 `eff3f675c93a0209caf4987d72e0f277492c3dddc2b4c2aff334a667b4dbfbc7`로 동일하지만, 빌드 소스와 연결되는 추가 산출물은 발견하지 못했다. 이 검색은 현재 workspace 안의 해당 파일명 범위이며 세상에 provenance가 없다는 뜻이 아니다.

086에서 조사한 MK3 source의 FE/96MHz 측정창을 실제 binary의 기능으로 단정하지 않는다. 사용자에게 파일·분해·LED·PCUSB를 다시 요구하지 않고, 소스가 명확한 CF87에서 값을 직접 관측하는 경로를 만들었다.

## 메모리와 클록 경계

- CF87에는 PSRAM/SRAM controller, NES CPU/PPU, H1 ROM, PLL이 없다. 외부 메모리 주소는0, CE/OE/WE/byte enable은 HIGH, 데이터는 high-Z다. SNES 데이터 출력도 high-Z이고 외부 버스 OE는 HIGH다. 두 클록이 멈춰도 **구성 완료 후 이 논리의** 비활성 출력은 변하지 않는다. FPGA 구성 중/전원 전환의 전기적 상태를 이 결과로 승인하지 않는다.
- 기존 물리 포트·핀 배치를 사용하며135개가 모두 지정된다. 새 fit에서337LE/27LAB/247registers, 메모리0bit/PLL0이다. CF86의191LAB나 전체NES의4LAB 여유와 혼동하지 않는다.
- 기준 입력은SNES_SYSCLK/A9, 계수 시간 기준은CLKIN의8,000,000주기다. 기준 클록을16분주한 신호를2단 동기화한 후 rising edge를 센다. 가정한20~22MHz 기준/8MHz CLKIN에서는 충분히 느리다. 임의로 높은 입력 주파수·짧은 glitch·아날로그 품질을 정확히 측정하는 계측기가 아니다.
- 새 내부 STA는3corner18summary 최소0.187ns다. 예외는 divider[3]→ref_sync[0] 하나이며, 예외를 제거한 실제 inter-clock 경로6개가 모두 그 첫 FF의 setup/hold임을 확인했다. 첫→둘째 FF는 계속 timed다. 메타안정성 MTBF나 외부 SPI setup/hold를 승인하지 않았다. 미제약 SPI 입력3포트4경로/출력1포트2경로와3.3V IO 경고를 보존한다.

## SPI 응답 형식

Mode0, 최대250kHz, 각 byte 이후2µs 이상 여유와 CS 전후2µs 이상을 시험했다. 첫 byte는 command이고 응답은 다음 byte부터다. CF 명령은87을 반환한다. C0는 명령 byte 수신 시 전체16바이트를 latch한다. 첫 command byte에서 받은 MISO는 해석하지 않는다.17번째 이후는0이며 byte count는63에서 포화되어 wrap하지 않는다. 알 수 없는254개 command는0을 반환하고, 중간에 CS를 끊으면 다음 frame에서 새 command를 받는다. CF87에는 RUN·LOAD·쓰기 명령이 없다.

| C0 응답 offset | 의미 |
| --- | --- |
| 0 | 후보 식별자87(hex) |
| 1 | bit0: 완료 구간 존재, bit1: 최근 reference edge 존재, bit2: 기동 이후 부재 이력, bit3: 마지막 완료 구간에 부재 포함, 상위4bit=0 |
| 2–5 | 완료 구간 sequence, little-endian32bit, FFFFFFFF에서 포화 |
| 6–9 | 마지막 완료 구간의 reference/16 rising edge 수, little-endian32bit |
| 10–13 | 구간 길이8,000,000 CLKIN주기, little-endian32bit |
| 14 | 분주값16 |
| 15 | 예약0 |

구간은 정확히WINDOW주기이며 마지막 주기의 edge도 포함해 바로 다음 구간을 시작한다. 순번0/valid0은 아직 완료 구간이 없다는 뜻이다. 기준 클록이 없어도 CLKIN이 돌면 valid1·count0인 구간이 완성된다. **valid는 기준 클록 정상 판정이 아니다.** live는 최근64 CLKIN주기 이내 분주 rising edge 여부다.8MHz 가정에서약8µs이며 CDC latency가 더해진다. ever-gap은 초기 기동 부재도 포함하므로 전원 기동 후1이 될 수 있다. 현재/마지막 구간과 역사 비트를 구분한다.

`MCU_RDY=1`은 관측용 SPI 서비스 표식이며 메모리 승인 또는 CLKIN 생존 증명이 아니다. CLKIN이 멈추면 SPI 응답도 정지할 수 있다. MCU는 별도 시간/반복 예산과 새 sequence 진전을 검사해야 한다. 같은 값의 반복이나 이전 정상 count를 새 실기 성공으로 처리하지 않는다. 현재 응답에는CRC가 없으므로 이 단독 RTL 시험을 전체 C GPIO 전송 무결성 검증으로 확대하지 않는다.

조건부 계산식은 `reference_hz = count × 16 × actual_CLKIN_hz / WINDOW`다. CLKIN이8MHz임을 별도로 뒷받침하면 기본WINDOW에서 count×16이다. 아직 실제 주파수를 측정하지 않았으므로 로그에는 원시 count/window/divisor/sequence/flags와 가정 주파수를 함께 기록한다. 누락·정지·불완전 구간은 주파수 PASS로 표시하지 않는다.

## 검증과 재현

실제 기본8,000,000주기의20MHz 시험을 통과했고,20/22/약21.477MHz 및 경계·명령 대조는 짧은80,000주기도 사용한다. 짧은 시험은 TB parameter override이며 배포 기본값을 바꾸지 않는다. 각 시험의 실제window는 result에 구분한다. 결과를 읽는 중 새 구간이 완료되는 경우에도 sequence/count/flags는 command에서 latch한 한 snapshot이어야 한다. 실기 가용성과는 다른 디지털 시험이다.

```powershell
& ./tools/run_nes_clock_observation087.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $Questa -Out $NewASCII
# 추가 별도 출력: -ShortWindow, 또는 -ShortWindow -Mutation same-clock / live-snapshot / memory-enable
& $Python -B -X utf8 tools/nes_clock_observation087_fit.py --out $NewFitASCII --quartus-bin $Quartus
& $Python -B -X utf8 tools/nes_clock_observation087_audit.py --fit $NewFitASCII --out $NewAuditASCII --quartus-bin $Quartus
```

각 출력은 새 절대 ASCII 경로를 사용한다. 실제 기존 Starter FLOAT1seat를 순차 재사용한다. 원시 실패/성공과 실행 소스를 동결하며 현재 파일로 옛 evidence를 덮지 않는다. 첫 실행의 hex literal 옆 공백 누락·TB timeout integer 경고는 컴파일 오류로 보존했다. 라이선스 문제로 해석하지 않는다. 초기22MHz 기본창 시험은 TB의22.727273ns half-period가1ps 해상도에서22.727ns로 반올림되어1375017회를 셌는데 이상적인1375000회와 비교해 실패했다. 이후 기대값은 실제 양자화된 stimulus 주기를 사용한다. RTL 수정이나 허용 오차 확대가 아니다. 최종 실제 길이 근거는20MHz 실행이며 다른 두 주파수의 기본창 전체 재실행을 주장하지 않는다.

## 다음 완료 조건: 외부 실기용 단일 수집 패키지

1. 실제 MCU GPIO로 CF87/C0를 읽는 bounded C 경로와 snapshot 검사를 구현한다. 시간·총poll·CS 종료·공유fault 전파, malformed/부분응답/CLKIN정지·sequence정체를 검사한다. RESET은 관측 동안 계속 유지한다. ready가 기준 클록 PASS가 아니라는 의미를 지킨다.
2. 검증된084 보고서 경로를 기반으로 관측→RAM 보관→기존 mini 복귀→SD TXT/화면까지 한 session을 시험한다. CF87 자체는 화면/메모리를 제공하지 않는다. FPGA를 교체하기 전에 저장할 데이터를 RAM에 확정하고, 불확실 오류 뒤 추가 SD/SRAM IO 금지를 지킨다. 이미 성공한 정적 저장시험의 재요청으로 대체하지 않는다.
3. 같은 CF87 fit의 ASM/압축과 해당 ARM을 고정하고 원본044복원 파일을 포함한다. 실제 GPIO/SPI 외부 타이밍과 구성 전환/RESET 소유권을 확인한 뒤 report-only package를 제공한다. 사용자는 외부 기기에서 실행하고 새 TXT/영상만 전달한다. 이때야 RESET-held 가용성을 실측했다고 할 수 있다.
4. 그 결과는 CF86의 기준 클록 가정에만 활용한다. CF86의 비동기 clear 지연·외부 PSRAM 타이밍·공통 고장 정책·최신 MCU/전체80/96KiB/동일쌍은 여전히 별도다. CF87의 양클록 정지 중 메모리 비활성을 CF86의 active write 차단 증거로 대체하지 않는다.

084 실제 저장·재읽기·화면·정상044복원·메뉴/GBC PASS와044–086 archive를 보존한다. 전체 준비도4완료/7부분/1미완료, installable=false를 유지한다.
