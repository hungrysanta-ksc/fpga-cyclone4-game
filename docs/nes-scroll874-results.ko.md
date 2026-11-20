# MMC872의 마지막 map 반환과 첫 스크롤 발행

모험도 4 무입력 데모의 950번 화면(원본 2300)을 대상으로 MMC872의 ARM 송신 경로를 변경했다. 이전 873의 소비기 분리 시험과 달리 Cortex-M4 펌웨어가 직접 E0 거래를 보내고, 반환 대기 중 IRQ와 공유 SPI 서비스도 결합 일정에 포함한다. FPGA·65816 ROM·패킷 형식은 MMC872 기준이다.

## 바꾼 경계

대기 대상은 map 패킷을 발행한 뒤의 송신 카운터다. 기존 `nes_window184_drain`이 E0의 CRC, 수락·반환 카운터, ACK 상태·opcode·sequence·serial·generation을 확인한다. 큐가 비고 마지막 map identity가 일치해야 첫 21B 스크롤 E1을 시작한다. 65816은 그 사이 비활성 뱅크의 수락된 map을 DMA할 수 있다. 화면을 공개하려면 이후의 독립 검사와 SEAL 최종 ACK를 거친다.

- `both-pages`는 왼쪽 페이지에도 dirty 행이 있고 오른쪽의 긴 map 발행이 끝났을 때 이 정책을 적용한다.
- `wire`는 실제 스크롤 패킷 조립 시점에서 직전 패킷이 literal map이고 오른쪽 23행을 끝냈는지 검사한다. 기존 ACK 버퍼를 쓴다.
- `adjacent`는 같은 위치에서 직전 literal map 반환을 확인한다. 왼쪽 페이지의 부분 map 뒤에도 스크롤이 이어지는 951·952가 추가 적용 대상이다.

## 두 페이지 조건에서 확인한 비용

950의 map 반환 시각을 기준으로 MMC872는 스크롤 E1을 1.272/1.218ms 일찍 시작했다. `both-pages`에서는 실제 반환 뒤 0.182/0.364ms에 시작했다. 마지막 map E1 종료부터 첫 스크롤 E1 시작까지 E0는 1/1회에서 8/9회가 됐다. 이 구간의 E0 SPI 비용은 0.109/0.109ms에서 0.873/0.982ms가 됐다. 1,088B DMA는 직전 VBlank의 250/248선에 시작했고, 950은 양쪽 모두 4→3 VBlank, 246선에 공개했다. [SPI 응답·DMA·연속 일정](../analysis/scroll874-both-pages.json)

951까지 한 VBlank 이득이 이어졌다. 952의 입력 캡처 준비 클록은 두 위상 모두 MMC872와 같았고, SEAL 수락은 6.26/6.93ms 빨라졌다. 그런데 수락 시점이 236/235선이어서 검사 뒤 업로드 진입이 VBlank 끝에 걸렸고, 공개 VBlank는 MMC872와 같아졌다. 위상 1의 밀집 마지막 ACK는 0.242ms 늦어졌다. 위상 2에서는 후반에 다시 한 VBlank를 줄였다.

## 전체 일정과 채택 판단

아래 숫자 쌍은 시작 위상 1/2 순서다. 마지막 ACK는 밀집 데모 마지막 화면의 65816 최종 ACK 공개 시각이며 음수는 MMC872보다 빠르다는 뜻이다. ARM이 다음 E0 응답으로 이 ACK를 확인하는 시각은 [875 비교](nes-deadline875-results.ko.md)에서 따로 집계했다.

| ARM 발행 조건 | 950 선행 1,088B | 950 표시 간격 | 밀집 60간격 합 | 마지막 ACK 차이 (ms) | Flash 여유 |
|---|---|---|---|---|---|
| MMC872 | 없음/없음 | 4/4 | 141/141 | 기준 | 36B |
| 양쪽 페이지 변경 | 성공/성공 | 3/3 | 141/140 | +0.242/−16.897 | 0B |
| 오른쪽 마지막 행 뒤 | 없음/성공 | 4/3 | 141/141 | −0.022/−0.259 | 0B |
| 직전 literal map 뒤 | 성공/없음 | 3/3 | 141/141 | −0.010/−0.259 | 12B |

직전 literal map 뒤에 대기하는 조건은 위상 2에서 949 자체가 한 VBlank 늦어졌다. 950 간격은 3이어도 실제 공개는 기준과 같은 VBlank 145였다. 선행 DMA의 바이트 수와 절대 공개 시각을 함께 확인해야 하는 사례다. [오른쪽 마지막 행 조건](../analysis/scroll874-wire.json) · [직전 map 조건](../analysis/scroll874-adjacent.json)

세 후보 모두 오프닝 703은 VBlank 59의 231선, 전환 48간격 합은 119/119, 936 표시 간격은 2/2였다. 오프닝 759는 세 후보 모두 위상 1에서 기준 176보다 한 번 늦은 177에 공개했다. 큐 반환 오류·STOP·독립 검사와 cold 복구·메뉴 복귀 검사는 통과했다. 양쪽 위상의 성능 조건을 동시에 충족한 후보가 없어 MMC872를 실기 기준으로 유지한다.

다음에는 952에서 캡처 준비부터 SEAL 수락까지의 시간과 검사 완료 뒤 같은 VBlank에 남은 DMA 시간을 맞춰 본다. 950·951에서 확보한 한 VBlank가 952 공개까지 이어지는지, 오프닝 759의 위상 1 마감을 지킬 수 있는지가 판단 기준이다.

## 검증과 재현

완성된 ARM Flash 한도는 212,992B다. 왼쪽에 연속 1KiB 이상이 필요한 `long`은 213,000B, 오류 함수를 공유한 `long-compact`는 213,024B, 세 drain 호출의 임시 ACK 버퍼를 함수 하나로 옮긴 `shared`는 213,004B였다. 이 세 링크는 크기 비교용으로만 남겼다.

1. [MMC872 최종 링크](nes-mmc872-trial.ko.md)에서 `tools/prepare_nes_scroll874.py BASE/link-credit/src WORK/patch --policy POLICY`를 실행한다. `tools/build_nes_mmc479_arm.ps1`로 BASE/link-credit과 패치를 WORK/link-credit에 전체 링크하고 BASE/client02를 WORK/client02에 복사한다.
2. `tools/replay_nes_strip869.py TEMP PHASE WORK TAG CLIP`으로 PHASE 1·2와 `dense`, `opening`, `transition`을 재생한다. 태그는 각각 `874-drain`, `874-wire`, `874-adjacent`다. 기준 재생 태그는 `872-final`이다.
3. `tools/guard_nes_scroll874.py`, `guard_nes_progress870.py`, `guard_nes_capture871.py`에 WORK/link-credit/src와 각각 WORK/scrollguard.json, begin.json, input-guards.json을 지정한다. `check_nes_menu533.py --arm WORK/link-credit/src --trial 872 --out WORK/menu869.json`으로 정상·오류 메뉴 경로를 확인한다. `check_nes_strip869.py guards TEMP WORK TAG WORK/guards.json`으로 65816 부분 쓰기·손상·STOP·cold 재시작을 실행한다.
4. `tools/check_nes_scroll874.py TEMP WORK TAG REPORT.json`으로 비교에 사용한 ARM·65816 실행 파일의 해시, 원본 map과 유효 RGB, 화면별 작업량을 대조한다. 비용 모델에는 실기에서 보정한 SPI 시간과 CPI 2 ARM 명령 실행이 들어간다. 표의 시간은 결합 재생에서 측정했다.
