# MMC493 실기 수신 분석494

[측정 JSON](../analysis/hardware494-mmc493.json) · [493 구성](nes-boot493-contract.ko.md) · [다음 순서](nes-output487-plan.json) · [PR138](progress/pr-138.md).

## 판정

사용자가 정상 실행·메뉴 복귀를 확인했다. 전체 체감은 조금 나아진 듯하지만 첫 레벨 플레이는 별 차이가 없었다고 보고했다. 표시 클라이언트 ready는50ms/495poll로 확인됐고, **60.07초에 최종 표시575회, 평균9.57fps /104.47ms**다. 492의 부팅 실패는493 구성에서 회복됐다. ARM 조회 변경과 정상489 FPGA·표시 프로그램 조합을 현재 기능 실기 기준으로 유지한다.

이전489는60.08초577회/9.60fps다. 이번 전체 평균은 비슷하며 **지속 성능 개선은 확인되지 않았다.** 장면·입력이 같지 않아 소수점 차이를 개선/회귀율로 해석하지 않는다. 레벨별 완료 시각이 없어 첫 레벨 전용FPS도 산출하지 않는다. 60fps는 미완료다.

## 실제 비용

| 관측값 | 이전489 | 이번493 |
|---|---:|---:|
| 전체 평균 fps /ms | 9.60 /104.12 | **9.57 /104.47** |
| 수신 포함 ms/표시 | 30.06 | **28.97** |
| 계획·타일 공급 포함 | 34.29 | **33.05** |
| SEAL·최종ACK 포함 | 38.65 | **41.33** |
| 전체 driver wire 투영 ms/표시 | 32.03 | **32.20** |
| D0/E0/E8 조회 비중 | 44.73% | **44.22%** |
| E8 조회 수/표시 | 67.72 | **62.85** |
| E0 조회 수/표시 | 121.42 | **130.52** |

이번 수신/계획은 각각1.09/1.24ms 낮고 SEAL·ACK는2.68ms 높다. 서로 다른 입력의 관측이므로 E8 절감이 E0에 의해 상쇄됐다는 인과관계까지 확정하지 않는다. 같은 시작·고정 입력에서 공급/소비를 연결해 비교해야 한다. DWT 단계에는 실제 ARM·IRQ·guard·SPI/ROM 대기 영향이 포함되지만 IRQ별/ROM grant별 단독 시간은 분해할 수 없다. driver/quiet는 단계에 중첩되므로 더하지 않는다.

5초 frame-start 묶음은68,74,49,36,43,34,39,40,31,38,65,58회다. 중간 구간의31~43회/5초는 첫 레벨 체감 보고와 양립하지만 장면 경계·레벨FPS·완료 간격p95를 뜻하지 않는다. screen_frames는 명시적으로 신뢰하지 않는 필드이며 완료 수는 ARM의 최종ACK 진행575회다.

## 남은 병목과 다음 순서

- D0/E0/E8 조회는4671.26B/표시,wire14.24ms/driver28.56ms다. E0 credit/소비·ACK 대기와 E8 공급을 함께 줄여야 한다. 검사·credit을 통째로 제거할 수 있는 비용으로 세지 않는다.
- CREDIT/plan10.50ms·DRAIN1.92ms·FINAL_ACK9.67ms의 quiet도 관측됐다. 이 구간들은 위 단계에 포함되고 guard/서비스를 포함한다. 단순 sleep 제거로 모두 회수할 수 있다는 뜻이 아니다.
- command 본문(D1 payload,E1 minus19B,E9 minus8B)의 wire 투영은15.79ms다. 관측된 조회를 전부 제외해도 비조회 wire 투영은 **17.96ms**로60Hz의16.67ms보다 길다. 실제 framing/입출력 packet·반복 왕복까지 함께 줄일 구조가 필요하다. 미완료 마지막 시도와 공유70/73 op를 포함한 관측 투영이며 프로토콜의 불가능성 증명은 아니다.
- 전체 평균과60Hz의 차이는 **87.80ms/표시**다. 작은 word 복원 모델7.25%나 조회 명령 감소만으로 지속60fps가 된다고 판단하지 않는다.

1. **493을 정상 실행 기준으로 유지한다.** 이번에는 새 firmware/ZIP/FPGA 합성·Questa를 만들지 않는다. 489 및 기존 원복과GBC/save를 보존한다.
2. 같은 고정 입력에서 E0 credit/SEAL ACK quiet·65816 수신/독립 검사와 E8/D0 공급의 시각을 공동 추적한다. 순수 계산·wire·실제 소비 대기를 분리하고, 바이트 수만 줄이는 후보를 전체 시간 개선으로 승격하지 않는다.
3. 상태 응답과 packet/ACK 왕복·framing을 함께 줄이는 후보를 actual ARM·SPI·IRQ·ROM·65816 비용과 **136LE/Flash148B** 예산 안에서 비교한다. 새 SNAPSHOT/범용 FSM을 더하는 대신 삭제할 제어와 유지할 검사를 먼저 명시한다.
4. 새 SNES word DMA/MVN과492 FPGA는 계속 보류한다. 정상493이492 단일 원인 확정은 아니다. 다음 실제 FPGA 변경은 정상489 SNES ROM·부팅 경계를 유지해 검증하고, 의미 있는 전체 개선 뒤에만 새 번호의 paired 전달본과493 원복을 만든다. STOP·독립CRC/coverage·최종ACK·VBlank·메뉴 복귀는 유지한다.

## 종료 중단과 독립 검사

384KiB 적재/CRC/readback·START/run·boot ready·STOP/base_restored/safe_to_reload는 정상이다. 마지막에는 runtime result1(60초 제한),plan error0/sent1/END1,video/receiver error0이면서 **sink2/window3**이 남았다. 이를 일반 전송 오류의 무조건 허용으로 처리하지 않았다.

전달된493 실제 linked ARM에서 준비된 최소 SEAL fixture를 실행했다. 외부 SPI 응답·ticks/service는 모델이며, runtime transfer의 **전송 후 guard**에서 제한이 발생하면 result1→window3→sink2로 전파되고 SEAL commit/표시 확정은 일어나지 않았다. 마지막1건 pending/flags3·ACK 미공개가 로그와 일치한다. 정상 응답은 commit되고, 진짜 IO 실패는 result3으로 구분됐다. 오류 뒤 재호출은 추가 SPI/표시를 만들지 않는다. 로그16개 반례와 기존489-label fixture12개 반례를 거부했다. 실제 물리 종료 순간을 그대로 재생한 증명은 아니다.

실제 로그도 failed_transfers/CRC/trace abort0,trace576=표시575+1,SEAL request168B/identity 일치,미공개ACK0,한 건 pending을 모두 요구한다. **마지막 미완료 입력은 표시575회에 추가하지 않는다.** screen_error169는 로그에 명시된 SPC_INIT_RESULT_165/a9이며 일반 화면 오류 수로 해석하지 않는다.

## 보존·재현

반환3TXT는 로컬 `probes/nes-hardware494/run01`에 byte/hash 그대로 저장했다. receipt.json·termination02/result.json·parser01/result.json·analysis02.json을 선택했다. 첫 termination01은DWARF member offset 읽기 중단이며 대상 통과 근거로 사용하지 않는다. [분석기](../tools/analyze_nes_hardware494.py)와[linked 종료 검사](../tools/check_nes_hardware494_termination.py)로 공개 판정을 재계산한다. 원시로그·상용ROM·영상·라이선스·바이너리는 Git에 포함하지 않는다.

493 제작 시점의 package/boot493-verification 미확인 표기는 스냅샷으로 보존하고 새 실기 근거는494에 기록한다. whole Lite15272LE/14078comb/8392FF/264800bits/51M9K·관련setup/hold+0.183/+0.168ns,ARM Flash148B/RUN31848B는 그대로다. full reset/CDC/IO/full stack·IRQ·capture 무손실·NES 실시간 속도는 미증명이다.
