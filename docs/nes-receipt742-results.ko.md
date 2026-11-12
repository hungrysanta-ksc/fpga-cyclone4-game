# 742 · 마지막 map 반환과 OBJ 발행

**742는 727을 유지한다.** 마지막 map 발행부터 OBJ 발행까지 E0 조회를 10 / 9회에서 3 / 3회로 줄였다. 957의 1,536B map은 선행했으나 OBJ 288B가 최종 업로드에 남았고, 두 위상 모두 952의 1,536B 선행 DMA를 잃었다. 마지막 ACK는 44.047 / 55.035µs 늦었다.

## 실제 ARM·65816 연속 일정

727과 같은 707D 인터페이스·694 소비기를 사용했다. ARM은 이전 bulk가 대기 중일 때 마지막 map까지 소비된 E0 응답 하나로 두 반환을 확인한다. outstanding 범위, E0 CRC·counter·마지막 map identity를 검사한 뒤 이전 소유권을 해제하고 다음 OBJ를 발행한다. E8 descriptor의 CRC·generation·token 검사와 STOP은 그대로 실행한다. E8은 queue ACK identity를 싣지 않고 E0는 새 OBJ descriptor를 싣지 않으므로 각 응답을 한 번씩 읽는다.

재사용 가능한 뱅크에 같은 페이지의 연속 24행이 있고 마지막 출력이 map일 때는 OBJ·OAM을 먼저 서비스한다. 첫 scroll은 기존 719의 실제 DMA 진행 또는 제한 시간 확인과 compact CHR 준비 뒤에 발행한다. 957이나 특정 시작 위상에만 적용하는 분기는 ARM에 없다.

| 같은 905–957 연속 실행 | 위상 1 | 위상 2 |
| --- | ---: | ---: |
| 마지막 map E1 이후 OBJ E1까지 E0 조회, 727 → 742 | 10 → 3회 | 9 → 3회 |
| 마지막 map 소비 ACK → OBJ 발행, 727 → 742 | 2.030 → 0.432ms | 1.746 → 0.403ms |
| 밀집 표시 간격, 727 → 742 | 49.932319 → 49.873218ms | 49.932304 → 49.877005ms |
| 957 최종 ACK, 727 → 742 (master clock) | 65,725,518 → 65,726,464 | 66,082,774 → 66,083,956 |
| 952 / 957의 1,536B 선행 DMA | 실패 / 통과 | 실패 / 통과 |
| 957 OBJ 257선까지 선행 DMA | 0B | 0B |

밀집 간격은 951 공개부터 957 공개까지 여섯 간격의 평균이며 양의 ACK 차이는 727보다 늦다는 뜻이다. 두 위상 모두 53개 최종 화면의 RGB와 프레임별 출력 작업량을 확인했다. 727과 후보의 시작 master clock·SPI 드라이버 비용·SysTick·ROM 허가 달력을 맞췄다. 링크한 ARM과 실제 65816 명령을 실행한 모델 결과다. [수치·뱅크·SPI 거래·원시 해시](../analysis/receipt742-verification.json)

밀집 평균이 59.101 / 55.299µs 짧아진 데는 기준점인 951 공개가 398.654 / 386.828µs 늦어진 영향이 있다. 952–957 여섯 표시 간격은 모두 3 VBlank였고, 957 공개와 최종 ACK는 모두 늦었다. 952는 384B map과 48B BG까지 선행했다. 957에서는 1,536B DMA가 254 / 257선에 끝났지만 OBJ 288B 전부가 SEAL 뒤에 남았다. 951 공개는 두 위상 모두 242선, 957 최종 추가 대기는 0회였다.

## 같은 map 발행 시각에서 분리한 결과

727의 map 여덟 패킷과 앞선 52개 화면을 master clock까지 고정했다. 마지막 map E1 직후 E8을 읽고 descriptor를 검사한 뒤 D0 입력 서비스를 실행했다. E0는 앞선 응답을 소비 완료로 간주하지 않고 실제 map ACK가 발생한 뒤의 첫 표본에서 identity를 확인했다. 다음 표의 값은 위상 1 / 위상 2 순서다. 이 비교의 65816은 741의 WRAM 시험 코드이며, ARM 전체 실행 결과는 위 표에 따로 실었다.

| 첫 scroll 발행 조건 | 957 OBJ 선행량 | 밀집 간격 차이 | 마지막 ACK 차이 |
| --- | ---: | ---: | ---: |
| 실제 첫 384B DMA 완료 뒤 조회·발행 비용 부과 | 0 / 0B | 0 / +2.592µs | 0 / +15.551µs |
| 727 원래 scroll 및 전체 후속 발행 시각 | 0 / 0B | +0.869 / +0.093µs | +5.215 / +0.559µs |

두 일정 모두 952·957의 1,536B map DMA를 유지했고, OAM ACK는 246선 끝보다 460 / 426µs 빨랐다. scroll을 원래 시각까지 늦춰도 긴 map 마지막 쓰기는 두 위상 모두 259선이었다. 같은 일정에 원래 694를 실행하면 957의 BG 48B도 최종 업로드에 남았고 마지막 ACK 차이는 +49.634 / +55.035µs였다.

## 257선에 필요한 시간

map ACK의 바로 다음 master clock에 E0를 시작하는 이상적인 경우에도 응답·검사·OBJ E1까지 6,022클록(280.39µs)이 든다. 소비기별 실제 map ACK에 시각을 맞춰 재생하자 두 위상 모두 OBJ 선택 코드에 도달한 시각부터 259선이었다. 패킷 준비, DMA 선택, 실제 첫 PPU 전송을 구분했다.

위 이상적인 비용에서 처리 시간을 인위적으로 줄여 마감까지의 거리를 측정했다. 위상 1은 2,728클록(127.02µs)을 앞당긴 표본에서 64B OBJ가 257선에 시작했다. 위상 2는 2,728클록(127.02µs) 단축으로 258선, 4,092클록(190.53µs) 단축으로 257선이었다. 4,092클록을 앞당긴 경우 OBJ 64B가 256 / 257선에 시작했고 두 위상에서 마지막 ACK가 8.195 / 17.693µs 빨라졌다. 952·957의 1,536B 선행 DMA도 유지됐다. 이 값은 비용을 인위적으로 뺀 민감도 시험이며, 실제 ARM 결과는 위의 연속 일정 표에 있다.

두 위상에서 65816이 descriptor 마지막 바이트를 읽은 뒤 실제 OBJ 첫 바이트를 읽기까지 **477.43µs**가 걸렸다. `mark212` 진입부터 `append212` 호출까지가 312.52 / 310.65µs였으며 `bits212`는 32B 슬롯 9개에 한 번씩 실행됐다. 반면 288B의 첫 읽기부터 마지막 읽기까지는 110.63 / 108.77µs였다. 다음에는 727의 발행 순서를 두고 85–93번 슬롯에 걸친 두 bitmap 바이트의 검사·기록을 묶는 후보를 비교한다. 중복 슬롯 거부, 대상 뱅크별 이력과 최종 ACK는 각각 독립적으로 확인한다.

## 보호 조건과 자원

- 대기 중인 이전 bulk와 마지막 map이 함께 완료된 링크 ARM 시험에서 `E8 → E0 → E0 → E1`이 `E8 → E0 → E1`로 줄었다. 첫 E0에 map 한 건이 남으면 두 번째 E0까지 기다렸다. 16비트 counter wrap·범위 밖 watermark·잘못된 ACK·E8/E0 CRC·입력 뒤 STOP을 두 빌드에서 검사했다. 거부 시 다음 OBJ를 발행하지 않았다.
- 741 소비기에서 BG grant 직전 STOP과 오래된 OAM 이력을 각각 주입하면 956 화면을 유지하고 957 최종 ACK를 차단했다. BG grant 직전 첫 scroll을 제공하면 새 패킷을 먼저 수락했다. 실제 ARM의 17개 마감·STOP·최종 ACK 경계와 메뉴/base 복귀 5경로·파일명 4조건을 정상판과 장시간판에서 각각 통과했다.
- 60초판 Flash는 212,956B(36B 여유), 장시간판은 212,912B(80B 여유)로 각각 727보다 36B 작다. BSS는 19,548 / 19,556B로 각각 기준과 같다. FPGA 변경이 없어 707D 전체 FIT·STA를 승계한다. 741의 빔 시험 코드는 기준 ROM 한도를 초과하며 이 ARM 링크에 포함하지 않았다. 새 실기판은 만들지 않았다.

## 재현

1. 727의 `arm01`(장시간)·`normal01`(60초) 각각에 `tools/prepare_nes_receipt742.py <727 빌드> <새 patch 폴더>`를 적용한다. `tools/build_nes_mmc479_arm.ps1 -Base ... -Patch ... -Out ...`로 각각 `final-long`, `final-normal`에 링크한다.
2. [739의 905–957 전체 실행](nes-owner739-results.ko.md)과 같은 `tools/test_nes_observer717.py` 입력으로 ARM 경로만 `final-long/src`로 바꾼다. 7,288,416 / 7,467,100에서 시작해 ASCII 임시 폴더 `nes-receipt742-final1/2`에 기록한다.
3. 각 ARM에 `check_nes_receipt742.py`, `check_nes_deadline719.py`, `check_nes_menu533.py`를 실행해 probe 폴더에 `receipt742-N.json`, `deadline719-N.json`, `menu533-N.json`을 둔다. N은 장시간 690, 정상 704이며 메뉴 검사에 `--trial N`도 전달한다. 원래 장시간판에는 반환 검사에 `--original`을 추가한다.
4. [741의 재생 입력](nes-beam741-results.ko.md)에 `tools/replay_nes_receipt742.py --trace <temp>/nes-gap740-firstN-trace --phase N --policy poll --scroll original --client <694 client> --mesen <Mesen.exe> --out <temp>/nes-receipt742-poll-originalN`을 실행한다. `--variant control` 대조군은 `-694`, 읽기·범위 검사 추적 복제는 `-ranges`에 둔다. `--scroll first`로 재생 후 그 폴더를 `--pulse-folder`로 지정해 `poll-firstN-actual`에 다시 실행한다. `--policy floor`와 추가 `--lead-clocks 1364|2728|4092`는 `floor-originalN-aligned`, `floor-originalN-lead숫자-aligned`에 둔다. 위상 1의 `poll-original`에서 STOP(`--mode stop --inject before_bg`), 새 head(`--inject head`), 이력 손상(`--mode stale`)은 각각 `-stop`, `-head`, `-stale`에 둔다.
5. `tools/analyze_nes_receipt742.py --temp <temp> --probe <probe 폴더> --out analysis/receipt742-verification.json`으로 확인한다.
