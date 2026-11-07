# MMC662 실기 · 완료 표시와 종료 확인

MMC662는 60.32초에 1,224화면을 표시했고 사용자가 정상 실행·메뉴 복귀와 체감 향상을 확인했다. MMC643 대비 시작·마지막 5초를 제외한 표시율은 **18.32→19.96fps(+9.0%)**다. 새 실기 비교 기준은 MMC662로 삼는다. 지속 60fps 달성을 뜻하지 않는다.

## 같은 집계 구간의 비교

| 완료 표시 기준 | MMC643 | MMC662 | 변화 |
|---|---:|---:|---:|
| 5–40초 | 636회 / 18.17fps | 682회 / 19.49fps | +7.2% |
| 40–55초 | 280회 / 18.67fps | 316회 / 21.07fps | +12.9% |
| 5–55초 전체 | 916회 / 18.32fps | 998회 / 19.96fps | +9.0% |
| 전체 실행 | 1,152회 / 60.33초 | 1,224회 / 60.32초 | 19.09→20.29fps |

표는 완료 시각 누적 계수를 사용한다. frame-start 작업량 bin과 혼동하지 않는다. 두 버전 각각 한 번의 플레이이며 입력과 장면을 동기화한 실험은 아니다. 특히 후반 frame-start bin의 변경 map 행은 표시당 16.90→7.31개로 줄었고 OBJ는 16.22→18.77개로 늘었다. 표시율 향상은 확인됐지만 전체 향상률을 구현 변경만의 효과로 분리할 수는 없다.

## 비용과 다음 병목

| 전체 실행 DWT 합계 / 완료 표시 수 | MMC643 | MMC662 | 차이 |
|---|---:|---:|---:|
| 입력 수신 | 10.752ms | 10.662ms | −0.090ms |
| 계획·타일 공급 | 11.352ms | 11.321ms | −0.031ms |
| 출력·최종 ACK | 29.506ms | 26.510ms | −2.996ms |

실기에서 가장 크게 감소한 단계는 출력·최종 ACK다. 여전히 전체 평균 표시 간격은 49.281ms이고 60Hz의 16.667ms보다 약 32.61ms 길다. 단계에는 IRQ·대기 시간이 포함된다. SPI operation·polling은 중첩 계측이므로 다시 더하지 않는다. 이 로그만으로 26.51ms를 실제 DMA와 마지막 VBlank 대기로 정확히 나눌 수는 없다.

다음 작업은 MMC662의 map·OBJ 작업량을 고정하고 ARM 발행→65816 수락→선행/잔여 DMA→마지막 VBlank→최종 ACK를 두 시작 위상에서 대조하는 것이다. ARM 수신 바이트 감소만으로 성과를 판정하지 않고 첫 두 화면 이후 밀집 표시 간격과 마지막 ACK의 동시 개선을 확인한다. 기존 STOP·독립 검사·캡처 거부 뒤 회복·메뉴 복귀와 951 공개선·957 최종 추가 대기 0회를 유지한다.

## 실행·종료와 오류 해석

- 적재 readback 393,216B, 검증·STOP·base 복구·재적재 허가가 모두 성공이다. 마지막 progress는 `MENU_PREPARED`이며 사용자도 실제 메뉴 복귀를 확인했다.
- runtime 결과는 시간 제한 `DEADLINE=1`이다. run/ROM/first/STOP 오류, receiver/video/plan 오류, CRC 오류, 실패 SPI 집계와 trace abort는 0이다. 완료 EA는 표시와 같은 1,224회다.
- capture history에는 오류 0인 REJECT→RECOVERY 두 쌍이 있다. 첫 거부는 group 2, 둘째는 group 0이다. 둘 다 완전히 빈 캡처였다고 해석하거나 특정 스테이지 시각으로 단정하지 않는다.
- 마지막 입력 serial 1,225 / generation 1,265의 SEAL 1개는 최종 ACK 없이 종료됐다. `native_sink_error=2`, `sink_window_error=3`은 원본 그대로 보존한다. window 3은 transfer callback 실패이고 runtime의 첫 종료 원인은 deadline이다. guard가 transfer 전후 어느 지점에서 종료했는지는 로그에 없다. 이를 완료 표시나 새 plan FINISH 실패로 세지 않는다.
- `screen_error=169(0xa9)`는 로그의 `SPC_INIT_RESULT_165` 역할이며 `screen_telemetry_trusted=0`이다. 신뢰 가능한 화면 오류로 해석하지 않는다. 부팅 timeout이나 중간 메뉴 이탈은 이번 로그에서 관측되지 않았다. 한 번의 성공이 과거 간헐 실패의 소멸 증명은 아니다.

## 산출물과 재현

MMC662 패키지는 변경하지 않는다. [패키지 고정값](../analysis/trial662-package.json), [661 보드 FIT·STA](nes-reader661-results.ko.md), [설치·로그 안내](nes-mmc662-trial.ko.md)를 유지한다. ARM Flash는 212,508B / 여유 484B, 전체 보드는 15,324 LE·962 LAB·56 M9K다. 이번 작업은 실기 로그 분석이며 합성·펌웨어·새 ZIP을 만들지 않았다.

원본 세 로그는 저장소 부모 `probes/nes-hardware663/run01`, MMC643 원본은 `probes/nes-hardware644/run01`에 보존했다. [분석 JSON](../analysis/hardware663-mmc662.json)에 입력 SHA256·기준 분석 해시·집계·미완료 명령·복구 이력을 기록한다. 상용 게임 데이터는 추가하지 않는다.

저장소에서 다음 명령으로 다시 계산한다. 기존 MMC643 원본의 해시가 다르면 분석을 중단한다.

```text
python tools/analyze_nes_hardware663.py --raw ../probes/nes-hardware663/run01 --baseline ../probes/nes-hardware644/run01 --out analysis/hardware663-mmc662.json
```
