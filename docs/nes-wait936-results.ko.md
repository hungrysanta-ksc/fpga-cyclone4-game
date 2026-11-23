# 936 · 909 OAM 발행과 910 입력 수신

935의 정적 65816 ROM을 그대로 사용했다. ARM 후보 `batchfast`는 기존 캐시 위상 1에서 13 VBlank를 회복했고, 빈 캐시 두 위상에서는 세대 912의 SEAL 전 496B와 15 VBlank를 유지했다. 기존 캐시 위상 2는 14회이므로 실기 기준은 MMC925, 다음 비교의 65816 기준은 935 `bounded`를 유지한다.

## 909 공개 전 수신과 캡처선

| 기존 캐시, 위상 1 / 2 | 935 | OAM 앞 E0 한 번 (`receipt`) | 짧은 plan 우선·입력 완료 후 즉시 E0 (`batchfast`) |
|---|---:|---:|---:|
| 935 대비 910 첫 D1 시각 변화, ms | 0 / 0 | −1.407 / −1.405 | −0.365 / +0.633 |
| 909 공개 직전 VBlank까지의 선행 DMA | 16 / 624B | 0 / 16B | 624 / 48B |
| 910 마지막 D2의 캡처선 여유, µs | −358 / −58 | −452 / −425 | +42 / −280 |
| 밀집 여섯 표시 간격 합 | 14 / 14 | 14 / 14 | 13 / 14 |
| 935 대비 912 최종 ACK 시각 변화, ms | 0 / 0 | −0.057 / −0.007 | −16.650 / +0.017 |

첫 D1은 SPI 응답이 끝난 시각이다. 캡처 여유는 같은 위상의 기준 캡처선에서 COMMIT 뒤 마지막 D2 응답 시각을 뺀 값이다. 두 D2는 구분한다. 위상 2의 `batchfast`에서 마지막 **데이터** D2는 14,981,872, 909 공개는 14,994,456, COMMIT 뒤 마지막 D2는 15,015,476 masterclock이었다. 데이터는 이미 공개 전에 도착했다. 이전 최종 표시 ACK와 EA 회수·E8 재무장 뒤에만 COMMIT을 허용했다.

`receipt`는 OAM 반복 명령에 앞선 E0 대기를 12회에서 한 번의 검증된 큐 반환으로 줄였다. `batchfast`는 이미 발행한 E9 묶음이 두 개 이하일 때만 팔레트 앞에서 짧은 OBJ 후속 처리를 우선하고, 다음 입력이 COMPLETE인 표시 대기에서 96µs의 휴지 없이 E0를 다시 확인했다. 세대 번호나 시작 위상으로 분기하지 않는다. 두 변경을 분리한 대조군 중 `twobatch`의 기존 캐시는 14 / 14였다.

위상 2에서 차이를 만든 사건은 909의 VBlank 41이다. 935는 226·231선에 16B·32B를 보낸 뒤 236선의 32B, 241선의 384B, 이어지는 네 OBJ DMA까지 끝내고 250선에 OAM을 수락했다. `batchfast`는 235선에 OAM을 수락했고 반환은 253선이었다. 후속 OBJ 수락은 254선으로 밀렸다. 935 대비 잔여 DMA 종료는 0.403ms, 공개는 0.404ms 늦었다. 표시 간격을 회복하려면 이 VBlank에서 32B·384B 후속 descriptor가 선택될 기회를 확보해야 한다.

## 나머지 타일·메모리·복구

- 빈 캐시의 `batchfast`는 두 위상 모두 같은 여섯 VRAM 목적지에 496B를 전송했다. 935 대비 912 최종 ACK는 134 / 106 masterclock 늦었다. 나머지 타일 37묶음 중 늦어진 수는 기존 캐시 13 / 21, 빈 캐시 4 / 1이다. 가장 큰 지연은 기존 캐시 위상 2 세대 909 token 23의 32B OBJ에서 52,208 masterclock(2.431ms)이었다.
- 다른 후보 `finishobj`는 짧은 OBJ 뒤 OAM을 발행하기 전에 기존 FINISH 경로로 타일 반환을 확인했다. 빈 캐시 496B·15회와 935의 912 최종 ACK 시각이 두 위상 모두 일치했다. 기존 캐시는 14 / 14였고 캡처선 부족은 0.119 / 0.297ms였다.
- 실제 큐 반환 직후 긴 plan에서 입력 수신 기회를 두 번 또는 네 번 주는 대조군도 재생했다. 두 링크 모두 기존 캐시는 13 / 14회였고 Flash가 72B 초과했다. 네 번 시도한 위상 2에서는 909의 DMA가 일찍 끝나도 910의 마지막 데이터 D2가 909 최종 ACK 뒤에 도착했다. 다음 변경에서는 235선의 OAM 수락, 236·241선의 OBJ 선택, 다음 입력의 첫 성공 D1을 같은 시간축에서 다뤄야 한다.
- `batchfast` 최종 ARM 링크는 212,980B로 12B 여유가 있다. `finishobj`는 212,988B다. 검색 및 보고서 압축 변경이 있는 링크는 마커·보고서·메뉴 검사로 확인한다.
- 두 링크 모두 실제 ARM에서 네 곳의 SRAM D0 송신, 잘못된 수신 CRC 거부, STOP 뒤 base 복구와 메뉴 해제를 통과했다. 65816의 잘못된 descriptor·중복·잘못된 SEAL 거부, 복사·표시 도중 STOP, 32B·352B OBJ 마지막 바이트의 STOP을 검사했다. 빈 캐시에서는 288B 뒤 마지막 32B 선택 시점에 STOP과 새 패킷을 각각 넣어 DMA head가 그대로 유지되는지 확인했다.
- 실제 ARM과 정적 65816을 함께 재생하고 화면·타일·map·section 5 및 VRAM 쓰기를 세대별로 대조했다. 공유 ROM·캐시·SPI와 보드 복구 I/O는 모델이다. 실기 FPS 측정이나 신규 보드 합성은 이번 비교에 포함하지 않았다.

## 재현

1. 935의 `arm-final` 링크와 `bounded` ROM을 준비한다. `tools/nes_wait936.py prepare MODE TEMP`와 `tools/build_nes_trial577.ps1 ../probes/nes-wait936/MODE/link`로 후보별 전체 ARM 링크를 만든다.
2. `tools/nes_wait936.py replay MODE TEMP PHASE CACHE`를 실행한다. `PHASE`는 1·2이며 `CACHE`는 warm·cold다. 원본은 935의 같은 위상·캐시 재생을 사용한다.
3. 보호 조건은 `tools/nes_wait936.py proof MODE TEMP`와 `guards MODE TEMP`로 확인한다. 마지막 32B OBJ의 STOP·새 패킷 주입은 해당 후보의 실제 빈 캐시 송신 시각을 재생한다.
4. `tools/analyze_nes_wait936.py TEMP analysis/wait936-results.json receipt finishobj twobatch batchcredit batchfast batchhold batchroom retireinput tailinput`로 결과를 집계한다. 네 실행이 모두 있어야 전체 통과 조건을 계산한다.

[위상별 측정·링크 해시·보호 조건](../analysis/wait936-results.json) · [935 기준](nes-chain935-results.ko.md)
