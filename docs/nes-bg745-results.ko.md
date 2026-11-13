# 745 · 48B BG 소비와 957의 map 후속 OBJ

실제 Cortex-M4 발행 코드에서 48B BG의 receipt를 확인하고, 마지막 map 뒤에 준비된 OBJ와 재사용 OAM을 발행했다. 65816의 VRAM DMA에서 48B BG 완료와 1,536B map 시작을 따로 계측했다. 957의 긴 map이 시작될 때 바로 다음 descriptor에 288B OBJ가 있었다. ARM이 확인한 패킷 receipt와 VRAM 전송 완료는 서로 다른 시각이다.

## 같은 작업량의 연속 실행

정상 비교에 사용한 각 실행은 원래 694 압축 ROM으로 부팅해 905–957의 53화면을 처리한다. 시작 위상별 ARM 발행과 credit 반환은 실행 중인 65816과 동기화했다. 밀집 평균은 951 공개에서 957 공개까지 여섯 표시 간격의 평균이다. 표의 ACK는 727 대비 957의 최종 ACK 변화량(master clock)이다. 음수면 더 빠르다.

| 경로 | OBJ 선행 시작 (위상 1 / 2) | 밀집 평균 ms (위상 1 / 2) | 마지막 ACK 변화 (위상 1 / 2) |
|---|---|---|---|
| 727 | 없음 / 없음 | 49.932319 / 49.932304 | +0 / +0 |
| 발행 변경 | 없음 / 없음 | 49.935097 / 49.934026 | +398 / +334 |
| scroll 유예 | 없음 / 257선 H1026 | 49.933188 / 49.930643 | +112 / -500 |
| 727 map 시각 고정 · 발행 변경 | 없음 / 없음 | 49.935097 / 49.932397 | +398 / +12 |
| 727 map 시각 고정 · scroll 유예 | 256선 H1286 / 없음 | 49.929215 / 49.932397 | -400 / +12 |

- **발행 변경**은 두 뱅크의 표시 이력과 24개 연속 map 행, 직전 BG bulk 48B를 확인해 OBJ·OAM 발행을 앞당긴 전체 ARM 링크다. 이전 BG token과 마지막 map ACK를 각각 확인한다. 원래 65816만 결합하면 밀집 평균은 49.947157/49.946194ms이고, 원래 ARM에 변경된 65816만 결합하면 49.935299/49.935299ms다.
- **scroll 유예**는 첫 E0 진행 응답 뒤 1,536B의 DMA 데이터 시간에 해당하는 ARM 48,128클록을 한 번만 예약한다. 기존 719 마감과 poll 횟수 내에서 입력 서비스와 STOP·credit 확인을 계속한다. 진행 비트가 계속 1이어도 새 DMA 완료로 세지 않는다.
- **입력 먼저**는 E8에서 288B OBJ를 검증하고 이전 48B BG의 소유권을 정리한 뒤, 입력 서비스 한 번을 마지막 map drain 앞으로 옮겼다. 실제 OBJ 제출은 마지막 map의 CRC·identity·credit 검사를 모두 통과한 다음이다.
- **727 map 시각 고정**은 원래 ARM을 마지막 map 반환점까지 그대로 실행한 원인 분리 시험이다. 이후에는 727에 링크된 실제 이력 검사·입력 서비스·SPI 발행 블록을 Thumb 분기로 연결했다. 65816은 288B OBJ 수신 때 WRAM 루틴을 연결한다. 양쪽 모두 521개 map의 발행 시각과 payload가 727과 일치한다. 이 시험은 설치본의 상시 분기·부팅 비용을 입증하지 않는다.

## 두 위상의 차이

발행만 앞당긴 전체 ARM에서는 두 위상 모두 BG를 242선에 전송하고, 긴 map과 OBJ가 순서대로 큐에 남았다. 그런데 첫 scroll이 map 전송 중 도착해 255선에서 먼저 수락됐다. 957의 OBJ 선행량은 0B였다. scroll을 유예한 전체 ARM에서는 위상 2가 257선 H1026에서 64B OBJ DMA를 시작했다. 258선까지 338클록으로, 744의 고정 발행 재생에서 측정한 118클록보다 220클록 늘었다. 위상 1에서는 긴 map 마지막 쓰기 자체가 이미 258선이었다.

원래 map 시각을 고정하고 scroll만 유예하면 위상 1은 256선 H1286에서 시작한다. 위상 2에서 마지막 map의 ACK는 65,689,776클록이다. 직전 E0는 그보다 138클록 먼저 시작해 이전 credit를 반환했고 다음 E0는 5,908클록 뒤에 시작했다. 그 결과 OBJ 발행이 늦어지면서 긴 map의 마지막 쓰기가 260선에 도달했다. scroll 유예만으로는 이 비용을 회수할 수 없다.

입력 서비스를 먼저 호출한 두 전체 링크·두 고정 시각 실행은 956까지 52화면을 표시한 뒤 957의 빈 출력 큐 검사에서 중단됐다. 지키고 있던 BG token은 반환됐지만 마지막 map의 credit가 아직 남아 있었다. 이 경로의 밀집 간격과 957 ACK는 산출할 수 없다.

scroll 유예 전체 링크에서는 727 대비 521개 map 중 위상별 519/518개의 발행 시각이 달라졌다. 고정 시각 시험에서는 521개 전부 일치했다. 두 조건의 성공 위상이 서로 바뀌므로 개발 기준은 727을 유지한다. 다음에는 reason 4 입력을 빈 큐 경계에 두고, 마지막 map credit을 기다리는 동안 이미 확정된 OAM 116B를 준비해 E0 재조회·발행 비용을 줄일 수 있는지 검증한다.

## 독립 검사와 용량

- 완주한 경로에서 두 위상의 패킷별 작업·payload와 53화면 RGB를 727과 대조했다. 952·957에서 긴 map의 VRAM 시작과 종료, OBJ 시작의 실제 $420B 쓰기, SEAL 뒤 잔량까지 추적했다. 시작 시각은 65816/PPU 에뮬레이션 값이다. ARM은 링크된 Thumb를 실행했고 SPI·IRQ·ROM 경쟁에는 기존 계측 모델을 사용했다.
- 원래 발행 변경의 실제 패킷으로 957 OAM 처리 때 STOP과 손상된 재사용 이력을 각각 주입했다. 두 위상 모두 956 화면을 보존하고 957 ACK를 차단했다. 64B OBJ가 선행된 두 실행에서는 MDMAEN 직전 STOP 시 0B, 첫 PPU 쓰기 뒤 STOP 시 진행 중인 64B만 완료했다. 허가 직전 새 scroll을 넣으면 65816이 먼저 수락하고 OBJ를 미뤘다.
- scroll 유예의 60초판/장시간판은 ARM Flash가 212,964/212,920B여서 각각 28/72B 남는다. 두 링크에서 receipt 9조건, 마감·STOP·최종 ACK 17조건, 메뉴/base 5경로 및 파일명 4조건, 진행 비트가 계속 1인 경우를 포함한 6조건을 확인했다.
- 입력 우선 전체 링크는 60초판 213,056B, 장시간판 213,012B로 각각 64/20B 초과한다. 기존 reason 4 진입 검사는 sent 17, retired 16에서 실패했다. 바뀐 인터페이스에서 실제 submit 전 독립 검사 9조건은 통과했다. 두 검사의 결과는 별도로 보존한다.
- 65816 WRAM 본문은 6,362B다. 727의 512B prefix와 같은 압축·배치에서는 부트스트랩·prefix·압축 본문에 5,335B가 필요해 배치 가능한 5,056B보다 **279B** 크다. 시험은 원래 압축 ROM을 풀고 WRAM에 코드를 연결했다. FPGA RTL 변경, 새 Quartus FIT·STA 및 실기 설치 시험은 없다. [수치·해시·보호 조건](../analysis/bg745-verification.json)

## 재현

1. `tools/prepare_nes_bg745.py <727 arm01 또는 normal01> <patch>`를 실행한다. scroll 유예는 `--service`, 입력 우선은 여기에 `--input-first`를 더한다. 각 patch를 `tools/build_nes_mmc479_arm.ps1`로 같은 기반에 전체 링크한다. 출력 경로는 `probes/nes-bg745` 아래 발행 변경 `long02/normal`, 유예 `budget-long/budget-normal`, 입력 우선 `input-long/input-normal`이다.
2. `tools/run_nes_bg745.ps1 -Phase N -Variant V -Game <원본 ROM>`을 실행한다. N은 1·2, V는 arm·control·live·budget·input·matched·reserved·priced이다. 동일한 기존 727 원본 기록과 707D 보드 근거를 사용한다.
3. 60초판 trial 704와 장시간판 trial 690에 기존 `check_nes_menu533`, `check_nes_deadline719`, `check_nes_receipt742 --original` 및 `tools/check_nes_bg745.py`를 적용한다. 입력 우선에는 `--check-input-order`로 기존 거부와 변경된 submit 경계를 각각 기록한다. `trace_nes_owner739.py`의 stop/stale 재생과 `check_nes_dma745.py`의 pre/during/head 주입에는 각 실행에서 관측한 실제 패킷을 사용한다.
4. `tools/analyze_nes_bg745.py --temp <ASCII 임시 디렉터리> --probe ../probes/nes-bg745 --client ../probes/nes-longrun694/client01 --out analysis/bg745-verification.json`으로 두 위상의 결과를 대조한다.
