# NES470: 실기 약15fps의 비용과 다음 순서

PR133 머지8d472d50이 origin/master에 포함됨을 확인하고 새 codex/nes-hardware-cost-470 브랜치를 만들었다. 기준은 실제 시험467(FPGA457/ARM418/자체ROM428), 새 사용자 로그469다. 원본227 게임·402 등의 다른 workload 수치를 합산하지 않는다. 분석은 tools/analyze_nes_nrom470_cost.py로 재현하고 해시와 결과는 analysis/nrom470-cost.json에 기록한다. 새 ARM/RTL 성능 측정이나 합성은 이 분석에서 수행하지 않았다.

## 비용표

60.06초899표시 완료는14.968회/초, 평균66.808ms/표시다. 아래 시간은10ms tick 누계의 완료 프레임당 환산이며 개별 프레임 WCET나 순수 CPU 시간은 아니다.

| 구간 | 누적 | 평균/표시 | 코드에서 포함하는 작업 |
|---|---:|---:|---|
| 수신 | 33.77s | 37.564ms | capture/source 준비 대기·D0/D1/D2/D3·SPI·CRC·레코드 해석·중간 guard/service |
| 계획/준비 | 12.22s | 13.593ms | BEGIN1.235ms + planner 경로10.756ms + FINISH1.602ms |
| SEAL/최종 ACK | 13.50s | 15.017ms | 남은 output·queue drain·SNES 검사/실행·VBlank·E0 ACK polling·resident commit |
| 나머지 | 0.57s | 0.634ms | 바깥 guard/service·EA retire·시작/종료 및 누계 경계 차이 등; 세부 미계측 |

profile_receive_ticks=3376과 budget recv합3377에는1tick(10ms/전체실행) 차이가 있다. 두 번의 getticks 경계와 별도 누계이므로 숨기거나 같다고 강제하지 않았다. planner callback4tick은 planner967tick 안에 포함되며 빼면10.712ms/표시다. callback을 다시 계획 시간에 더하지 않는다. SEAL15ms를 순수 DMA 시간이나 반드시 고정된 VBlank1회 대기라고 부를 수 없다.

| 공유 SPI 분류 | 바이트/표시 | 2.625MHz 순수 wire/표시 |
|---|---:|---:|
| 입력 D0..D3 전체 | 6,284.34 | 19.152ms |
| 이 중 D1 payload(위 행에 포함) | 5,767.92 | 17.578ms |
| E0 상태 응답 | 1,774.15 | 5.407ms |
| E1 출력 | 557.48 | 1.699ms |
| E8 plan 상태 | 100.09 | 0.305ms |
| E9 plan | 14.02 | 0.043ms |
| 기타 | 7.00 | 0.021ms |
| 전체 | 8,737.07 | 26.627ms |

위 RUN 카운터의7,854,628B는 native_wire_bytes와 정확히 일치한다. observer/screen service는 nes_rom_spi_transfer를 직접 호출하므로 이 바이트/트랜잭션 카운터에 포함되지 않는다. 실제 공유 SPI 점유와 service 시간은 더 크며 P0에서 두 경로를 모두 계측한다. wire 점유 하한은 전체60.06초의39.86%다. 168,066 RUN 트랜잭션에는 각4×2us 명시 대기가 있어 평균1.496ms/표시의 추가 nominal 대기가 있으며 DMA/GPIO 재설정·guard 비용은 별도다. SPI가100% 포화된 것은 아니지만 **현재 전송량 자체가60Hz를 불가능하게 한다**. 입력 payload만17.578ms로16.667ms보다 크고, 집계된 wire만26.627ms에는 CPU·DMA·VBlank가 아직 없다. 버스는 공유 직렬이므로 단계 overlap만으로 이 바이트 한계를 없앨 수 없다.

수신을0으로 만드는 가정에서도 나머지29.244ms, 계획만0이면53.215ms, SEAL만0이면51.791ms다. 어느 한 구간 미세 최적화로는60fps가 되지 않는다. 전체 wire만16.667ms에 맞춰도 최소37.4% 바이트 감소가 필요하며 ARM·검사·일정 여유를 고려한8ms wire 목표는2,625B/표시(현 대비 약70% 감소)다. 이는 설계 목표이지 모든 장면의 달성 보장이 아니다.

## 먼저 줄일 병목

1. **기존 capture snapshot에서 반복되는 geometry/row 레코드를 SPI에 내보내기 전에 줄인다.** 정상 warm bin도 payload5,764B/프레임으로 거의 일정하며 정적 패턴인데도 전체 geometry를 보내고 ARM이 다시 해석한다. compressed record/span과 literal fallback을 비교하고 ARM에서 한 번만 canonical 데이터로 복원한다. palette/A 변화가 누락되지 않아야 하며 CRC·정확한 coverage·generation/token 검사를 유지한다. 화면이 같으면 프레임을 생략하는 방법으로60fps라고 보고하지 않는다.
2. **ARM의 반복 planner와 빈 상태 polling을 줄인다.** planner 경로는 callback을 제외해도10.712ms/표시다. 세부 CPU profile 전까지 어느 내부 함수를 주범이라고 단정하지 않는다. E0는79,748회(약88.7회/표시)로 wire5.407ms를 소비한다. credit/최종 ACK에 필요한 응답은 남기고 무진행 조회를 구분한다. E9는 전체에서 작으므로 descriptor 포맷 미세 조정부터 시작하지 않는다.
3. **표시 준비·검사·실행·VBlank·최종 ACK의 실제 시각을 분리하고 다음 capture와 겹칠 수 있는 소유권 경계를 확인한다.** 현재 SEAL 구간을 삭제하거나 ACK를 조기 반환하지 않는다. 수신37.564ms 중 입력 wire19.152ms 외 부분은 capture 대기·ARM·service 등이 섞여 있어 추정만으로 분리하지 않는다.

SPI를5.25MHz로 올리면 half period95.238ns가 이전 조건부 응답 envelope164.848ns보다 짧다. 기존 observer22MHz 동기화·IO 가정 그대로 단순 배속을 해답으로 선택하지 않는다. 457 전체14,770/15,408LE는 산술638LE가 남지만 실제 LAB·routing 여유나 codec 비용이 무료라는 뜻은 아니다. 과거 대형 FPGA 공동 실행기를 재도입하기 전에 실제 병목과 최소 교체 비용부터 비교한다.

## 실행 순서와 통과 조건

P0은 FPGA457의 실제 ARM RUN에 미세 시간계와 opcode별 전송/무진행 polling 통계, source-ready/계산/최종 ACK 경계를 추가한다. timer wrap과 계측 overhead를 확인하고 deadline 취소와 CRC 오류를 다른 원인으로 기록한다.10ms 통계만으로 sub-ms 최적화를 평가하지 않는다. 예산은 wire8ms + ARM 비전송계산3ms + 겹치지 않은 외부 실행3ms + service/scheduler0.667ms + 여유2ms의 **초기 설계 목표**다. VBlank 대기를 공짜로 넣거나 latency와 throughput을 혼동하지 않고, capture와 전송·준비가 어느 범위에서 겹치는지 먼저 증명한다.

P1은 bounded source 압축을 기존 RAM·source 경계에 최소 구현하고 canonical replay·cold·최악 literal·STOP을 확인한다. P2는 기존 안전한 ARM 변경분을 재사용할 수 있는지 검토하며 raw-group/history 무효화와 progress/credit을 연결한다. P3은 검증된 변경을 공통 일정으로 묶고 매16.667ms의 다음 capture와 VBlank deadline·최종 ACK를 확인한다. P4는 RTL이 바뀔 때 같은 소스의 Lite 전체 비용/관련 timing, ARM·65816/STOP 회귀 후 새 실기를 전달한다. MMC4/5는 실제 mapper/ROM 경쟁을 연결하는 다음 관문이며 NROM 개선으로 자동 보장하지 않는다. machine-readable 순서와 보존 조건은 nes-cost470-plan.json을 따른다.

독립 CRC/coverage, bank/token/epoch 재사용, STOP 취소와 stale DONE 차단, 최종 표시 ACK 후 resident commit/EA retire, base DONE·SPI 유휴·토큰·메뉴 복귀를 유지한다. 저장 credit·DMA 완료·화면 표시 완료는 서로 대체하지 않는다.

## 다음 전달본 이름

다음 비용 계측 전달본은 **NROM471-COST-PROBE.zip**, 실행 항목 **NES NROM 471.nh1**, 로그 **nes-progress-nrom471.txt / nes-budget-nrom471.txt / nes-game-last-nrom471.txt**로 예약한다. ARM 빌더 기본 label을 nrom471로 갱신하고 소스 생성에서 marker·report identity·expected ID78·세 로그를 함께 바꾼다. 이미 사용한467은 보존한다. 이470 단계에서는 새 설치 ZIP/firmware를 만들지 않았으며 같은 smoke를 이름만 바꿔 반복하지 않는다. 계측이 의미 있는 정보를 추가한 다음에471을 전달한다.
