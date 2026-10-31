# NES506 — 정확한 raw 반복 전송과 ARM 단일 복원

기준은 실기에서 동작한 **MMC502**와 변경하지 않은489 SNES 소비 프로그램이다. 505의 선행 DMA는 이 후보에 포함하지 않는다. 이 문서는 [504 계획](nes-budget504-plan.json)의 다음 실행 경계를 구체화한다. 실기 기록10.59fps와 기존 MMC502 설치 파일은 그대로 유지한다.

## 교체한 처리

입력 raw 색상의 같은 값이10개 이상 이어지면 최대256개를 한 record로 보낸다. 짧거나 서로 다른 구간은 기존10색 literal을 사용한다. 같은색256개를 기존26개 record 대신1개로 표현하며, 색상이나 행을 버리는 방식이 아니다. header 버전을2232에서2233으로 바꾸어 구형 수신기와 섞인 전송은 거부한다.

FPGA는 기존 `pack_count`, `held_data`, `map_repeat`를 재사용한다. ARM은 범위·순서·세대·예약 비트를 한 번 검증한 뒤 bounded `memset` 또는 literal 복원으로 최종 raw 배열을 바로 채운다. 기존 pixel마다 `logical_record`를 다시 호출하는 경로를 제거한다. META_END, 전체 raw coverage, CRC8/CRC16, COMMIT과 표시 lease의 의미는 유지한다. 입력 완료가 앞당겨지면 기존 첫 BG 계획 발행도 앞당겨지는 구조다. 입력 완료 전 speculative 계획 발행을 새로 추가한 것은 아니다.

## 검증 경계

- 실제 exporter RTL에서12개 고정 게임 입력, uniform/alternating 경계2개, 잘못된 색상과 raw run 도중 STOP을 검증한다. 쿼리 응답 지연과 출력 backpressure를 넣고 STOP 뒤 COMMIT을 금지한다. 단일 Starter FLOAT 좌석을 사용한다.
- 실제 linked ARM의12개 연속 입력에서 의미 상태·resident·타일 계획·일반 출력·SEAL을 기준과 비교한다. 전송 token/status CRC만 packet 수에 따라 달라진다. RTL이 실제 출력한 record를 wire 바이트로 바꾸어 ARM 입력과 정확히 대조한다.
- run10/256과6개 잘못된 span 조건, payload/status CRC, 구형 header, PREPARE 거부를 검사한다. 실패 후 tentative raw 포인터와 재시도를 허용하지 않는다.
- 공동 시험은 실제 ARM runtime/planner/serializer/quiet loop와 실제489 65816의 검사·DMA·receipt·최종 ACK를 연결한다. 실제 SysTick 및 `native_service165` 코드와 정상 하드웨어 경계, 실기503의 SPI driver 평균 추가 비용을 구분한다.
- source201처럼 **입력 COMMIT 뒤 다음 capture를 시작하고 이전 표시 lease는 최종 ACK/EA까지 유지**한다. 다음 입력을 이전 EA 뒤에만 내보낸다. ROM은242..259행의 허용 창과 유한2-bank staging으로 모델링한다.

마지막 항목의 ROM safe-slot 밀도와 Cortex-M4 CPI는 민감도 파라미터다. 고정 capture/CHR 결과를 재생하며 전체 NES/PSRAM RTL, 실제 MCU peripheral 시간, 실기 메뉴 복귀를 새로 실행한 시험은 아니다. 관측한 시뮬레이션 시간을 실기 FPS나 전체60Hz 증명으로 사용하지 않는다. 독립 검사는 CRC만 비교하지 않고 실제 최종 HDMA/VRAM/RGB도 비교한다.

## 선택한 연속 비교 결과

ARM02/arm-test02, source rtl02, guards01/clock01, 공동 candidate11/baseline13, board01과 analysis03을 선택했다. 입력·초기 시각·ROM 위상은 동일하다. 공동 시험의 SPI 부가 비용은 실기503에서 wire 시간을 뺀 opcode별 평균48.10..50.39µs/회다. CPI2와 ROM 허용 창 안의48masterclock 간격은 명시적인 모델 값이다. 실제 SysTick을 callback 경계에서 실행하므로 driver 평균에 이미 포함된 IRQ와의 완전한 중첩 시간을 재현한 것은 아니다.

| 비교 | MMC502 기준 | 506 후보 | 변화 |
|---|---:|---:|---:|
| 12개 전체 SPI 전송 | 153,311B | 145,247B | −8,064B(5.26%) |
| 첫 프레임 이후11개 표시 간격 합계 | 1,263.881ms | 1,230.609ms | −33.272ms(2.63%) |
| 두 bank 초기 채우기 이후10개 간격 합계 | 1,014.289ms | 981.019ms | −33.269ms(3.28%) |
| 위10개의 입력 준비→첫 BG 발행 평균 | 32.888ms | 29.371ms | −3.516ms |

전체 마지막 ACK는49.914ms 앞당겨졌다. 첫 프레임에서만 생긴 약16.642ms와 이후 이득을 분리했다. 고정 입력별 최소 source wire는614~626B, 실제 ARM 복원은51,778~52,312명령 줄었다. planner/일반 serializer 명령과 실제 E1 출력41,376B는 동일하다. 두 구성 모두12개 최종 RGB, VRAM DMA36,144B와 ROM read 할당3,280개가 같다.

**지속 이득은 작고, 모든 프레임에서 같은 비율로 빨라지지는 않았다.** 첫 BG 발행은3.261~3.694ms 앞당겨졌지만 최종 표시의 큰 추가 이득은911·913에서 VBlank 한 주기씩을 앞당긴 데서 나왔다. 두 bank 초기 채우기 이후 후보의 SEAL→최종 ACK는 여전히 평균24.451ms다. 첫 bulk→SEAL 구간도37.186ms이며 ROM·후속 계획·일반 출력이 섞인 구간이라 순수 ARM 계산 시간으로 해석하지 않는다. 이 구간의 준비 의존성과 ROM 공급을 바꾸는 것이 다음 대상이다. 505의 고립된 선행 DMA를 다시 미세조정하는 결론이 아니다.

## 비용과 보드 판정

| 항목 | MMC502 | 506 후보 | 차이 |
|---|---:|---:|---:|
| ARM firmware | 212,844B | 212,852B | +8B |
| Flash 남은 공간 | 148B | 140B | −8B |
| ARM BSS | 18,572B | 18,572B | 0 |
| 전체 fitted LE | 15,287 | 15,198 | −89 |
| 조합 함수 | 14,135 | 14,168 | +33 |
| FF | 8,399 | 8,399 | 0 |
| 논리 RAM bit / M9K | 264,816 /51 | 264,816 /51 | 0 |
| 관련 clock setup / hold | +0.353/+0.142ns | **−1.276**/+0.137ns | setup 실패 |

동일70개 보드 입력 중 exporter1개만 교체하고 Quartus Lite 전체 합성·배치·STA를 실행했다. LE 감소는 배치·packing 결과이며 조합 논리 삭제량을 뜻하지 않는다. 늘어난33개 조합 함수와 setup 회귀를 함께 기록한다. 최소 setup 경로는168MHz loader `fault`에서 SPI control `error_code[2]`로 가는 기존 경로다. 변경된 raw 경로의 기능 통과만으로 보드 타이밍 통과를 주장할 수 없다. reset·CDC·IO 전체 승인도 여전히 별도다.

**후보의 실기 승격은 보류한다.** seed 반복이나 무관한 loader 동작 변경으로 결과를 고르는 대신, 타이밍을 유지할 수 있는 변경 경계와 다음 일정 이득을 함께 검토한다.

## 시험 모형의 수정 기록

초기 공동 시험의 END 상태를 모형이3으로 반환해 실제 ARM이 retire를 거부했다. 올바른 값2로 수정했다. 이 실패는 제품 RTL 오류로 분류하지 않는다. Windows RPC 공유 잠금은 제한된 재시도로 처리한다.

또한 초기 시험은 emulator의 atomic DMA 종료까지 ARM을 기다리게 했고, capture 재개를 EA 뒤로 잘못 늦췄다. 해당05/06 실행은 기능 연결 근거로만 보존하고 성능 선택에서 제외한다. 수정 모형은 미래 receipt/ACK를 발생 시각까지 보류하며, DMA overshoot를 ARM 대기로 더하지 않는다. 별도 clock 반례 시험으로 미래 ACK 공개와 가짜 ARM 대기를 막는다. 입력 COMMIT에서 capture를 재개하도록 실제201 ownership과 맞췄다.

07..10과12의 초기 RPC watchdog 원본도 남긴다. 선택11/13은 순서대로 실행했다. 동시 emulator 시작 중 watchdog의 정확한 원인은 확정하지 않았으며 Questa 라이선스 실패나 제품 실행 실패로 집계하지 않는다. 최초 nominal STA 지원 파일 누락 결과는 버리고, 기준 nominal SDC를 복사한 같은 fitted DB의 재분석을 사용한다. 첫 실패 로그를 보존하며 다시 FIT하지 않았다. 분석01의 report 문자 인코딩 오류도 보존했고 원본 bytes/hash를 바꾸지 않고 표의 ASCII 수치를 읽었다.

## 재현과 다음 순서

공개 recipe와 시험은 `tools/nes_raw506.py`, `test_nes_raw506_arm.py`, `test_nes_raw506_rtl.py`, `test_nes_raw506_guards.py`, `test_nes_raw506_joint.py`, `test_nes_raw506_clock.py`, `prepare_nes_raw506_board.py`에 있다. 상용 ROM·capture·firmware·FPGA 산출물·license는 Git에 넣지 않는다. 선택한 SHA와 결과는 [검증 보고서](../analysis/raw506-verification.json)에 기록한다.

1. 현재 setup 회귀의 loader fault→error_code 전달 경계를 추적한다. 기존 응답·STOP 의미를 바꾸지 않는 논리/등록 경계를 제안하고, seed 반복을 대신할 검증 조건과 비용을 먼저 정한다.
2. source 반복 전송 절감은 보존하고, 첫 bulk 이후 후속 BG/OBJ 계획·일반 출력 준비가 ROM 대기와 겹칠 수 있는 경계를 실제 포트/수명으로 확정한다. SPI query/quiet/IRQ를 중복 합산하지 않는다.
3. 그 변경을 실제 ROM arbiter trace와 공동 일정에 연결한다. 동일 입력·시작 시각에서 첫 프레임/두 bank 초기 채우기를 분리하고, 전체 Lite STA까지 통과하기 전 실기 전달 후보로 승격하지 않는다.
4. 승격 조건을 충족하면 새 번호의 전달본을 준비하고 실행·플레이·STOP·최종 ACK·메뉴 복귀를 실기로 확인한다. RESTORE 폴더는 포함하지 않는다.
