# 668: MMC666 출력 비용과 map 소비 경계

PR154의 master 병합 `3f8292795b8a5e53d6cf250fcc568223e748a3d6`과 포함 관계를 확인하고 `codex/nes-output-budget-668`에서 시작했다. 사용자 지정 개발 기준은 MMC666이다. MMC662·666 실기 동선의 map·OBJ 작업량이 달랐으므로 이전 평균 FPS 차이를 후보의 속도 개선율로 쓰지 않는다.

**두 후보 모두 종단 시간 조건을 통과하지 못해 선택 구현은 MMC666을 유지한다.** 계산 비용은 줄었으나 선행 DMA·업로드 진입 시각이 바뀌어 마지막 ACK까지의 이득이 보장되지 않았다. [전체 검증·비교 JSON](../analysis/output668-verification.json)

## 기준과 비용 분해

MMC666 ARM과 665 보드·65816을 고정했다. MMC666의 798개 실행 함수는 기존 664 all과 주소·크기·바이트가 같다. 계측을 추가한 MMC666 위상 1 재생의 53개 최종 ACK 시각은 기존 665 위상 1과 정확히 같다. 두 위상은 시작 클록 7,288,416 / 7,467,100과 같은 ROM 허용 달력을 사용한다. 후보마다 map 주소·길이·payload·중복 횟수와 OBJ 슬롯 순서·바이트, 최종 RGB/map/PPU 상태를 대조한다.

실기 로그의 **26.841ms**는 출력 함수 전체 DWT 평균이다. 실제 장면별 DMA/VBlank 시각이 없어 이 값을 아래 비율로 나눌 수 없다. 아래는 같은 53개 캡처 중 warm 52개의 실제 링크 ARM·65816 재생이며 CPI2·IRQ·공유 SPI·반복 ROM 허용 달력 모델의 시간이다. 물리 FPS 예측으로 바꾸지 않는다.

| 겹치지 않는 출력 구간 | 위상 1 | 위상 2 |
|---|---:|---:|
| 출력 진입→ARM의 SEAL 발행 완료 | 15.690ms | 15.703ms |
| SEAL 발행→65816 읽기 시작 | 0.074ms | 0.065ms |
| 독립 검사 | 1.626ms | 1.625ms |
| 업로드 VBlank 대기 | 9.255ms | 9.480ms |
| SEAL 이후 DMA 활성 구간 | 0.539ms | 0.578ms |
| 기타 65816 설정·제어 | 1.121ms | 1.129ms |
| 마지막 추가 VBlank 대기 | 0.288ms | 0ms |
| 65816 최종 ACK→ARM 반환 | 0.315ms | 0.351ms |
| 합계 | **28.910ms** | **28.931ms** |

발행 구간 안의 SPI는 11.589 / 11.561ms이며, 이 동안 ordinary 수신·복원·선행 DMA가 겹친다. 별도 비용으로 다시 더하지 않는다. 밀집 951–955에서는 마지막 추가 대기가 이미 두 위상 모두 0회다. 따라서 마지막 VBlank 제거보다 **발행 순서·수신 소비·map 선행 DMA 기회의 결합**이 다음 대상이다.

## 구현한 두 후보

`linear`는 `span_piece`에서 각 시작 위치마다 최대 64B를 재검사하던 탐색을 앞으로 한 번 진행하는 탐색으로 바꾼다. 두 칸 떨어진 바이트가 위치 j에서 다르면 j−2까지의 시작점은 모두 실패하므로 다음 후보 j−1로 이동한다. 최초 64B 반복의 위치·240B cap·packet opcode·분할·데이터는 동일하다. 이 변경은 검사 생략이나 이력 신뢰의 확대가 아니다.

`drain`은 위 변경과 함께 남은 map batch가 비어 있지 않을 때 기존 checked drain으로 소비 완료를 확인한 뒤 nonmap tail을 발행한다. 새 명령·고정 sleep·세대별 분기는 없다. 소비 ACK를 DMA 완료나 표시 ACK로 간주하지 않는다. 기존 19행 조건의 입력 선행 수신 정책은 그 조건 안에 그대로 둔다. SNES의 새 패킷·STOP 우선순위는 변경하지 않는다.

경계·반복·비반복·최대 길이의 464조건에서 실제 링크 ARM의 분할 위치가 기존·독립 참조와 같다. 합계 탐색 명령 수는 2,691,110→1,046,223으로 줄었다. 실제 밀집 입력의 탐색 비용도 CPI2 기준 약 0.739–0.757→0.145–0.177ms다. 이 절감만으로 종단 가속을 판정하지 않는다.

## 같은 작업량의 결과와 회귀 원인

양수는 MMC666보다 늦거나 간격이 길다는 뜻이다. 두 후보 모두 밀집 951–955의 합계 15 VBlank, 952 3 VBlank, 957 마지막 추가 대기 0회를 유지했다. 새 대조군 53화면과 두 후보×두 위상 212화면, 총 265화면을 실행했다.

| 후보 | 밀집 평균 간격 차이, 위상 1 / 2 | 957 마지막 ACK 차이, 위상 1 / 2 | 판정 |
|---|---:|---:|---|
| linear | +0.000317 / −0.042110ms | +0.214739 / −0.213994ms | 두 위상 동시 개선 실패 |
| drain | −0.043041 / −0.046170ms | +16.848509 / +16.640102ms | 911 추가 VBlank로 누적 회귀 |

MMC666 밀집 평균은 49.920847 / 49.916880ms다. 40µs 수준의 후보 간격 감소를 실기 FPS 개선으로 표현하지 않는다.

linear 위상 1의 954 선행 map DMA는 1,344→320B, 957은 1,664→1,280B로 줄었다. 954에서는 같은 이전 VBlank의 큰 1,152B 전송 대신 128B만 실행됐다. 위상 2의 957은 반대로 1,280→1,664B로 늘었다. 패킷이 빨리 준비돼도 bulk/ordinary 도착 순서·빈 큐 구간·실행 명령의 연결이 달라져 절감한 탐색 시간이 업로드 대기와 남은 DMA로 바뀐다. 개별 스케줄 차이 모두를 탐색 루프만의 직접 효과로 분리한 고정 도착 반사실 시험은 아니며, 전체 연결 후보의 결과로 판정한다.

drain은 911에서 발행 구간을 9.183/9.181→9.718/9.718ms로 늘렸다. 65816의 SEAL 수락은 189번 선→196/197번 선, 검사 후 업로드 진입은 214번 선→221/223번 선으로 늦어졌다. 설정·대기 진입 경계가 바뀌면서 업로드 VBlank 대기는 0.327/0.295→15.923/15.735ms로 늘었다. 마지막 추가 대기는 계속 0회다. 즉 911의 회귀는 최종 표시 검사선보다 앞선 **업로드 시작 대기**에서 생겼으며 이후 마지막 ACK까지 남았다. 소비 완료를 모든 map batch의 후속 발행 조건으로 삼는 방식도 선택하지 않는다.

## 후속 범위와 보류할 작업

1. MMC666을 유지한다. linear의 단독 탐색 튜닝, 일괄 map drain, 세대/시작 위상별 고정 지연 변형은 이번 근거로 보류한다. Flash 여유만으로 채택하거나 새 실기 ZIP을 만들지 않는다.
2. 다음에는 954·957에서 이미 수락된 map의 **실행 가능한 바이트 수·명령 병합·빈 큐 시점**을 함께 추적한다. 후속 입력·출력을 전부 멈추는 대신 DMA에 필요한 최소 수락 범위와 소유권만 확정할 구조를 비교한다. 새 패킷·STOP 우선은 그대로 둔다.
3. 911을 발행 마감 대조군으로 추가한다. SEAL 수락 189번 선/검사 완료 214번 선의 기존 여유를 보존하고, 951 공개선·952 3회 이하·957 추가 대기 0회와 밀집 평균·마지막 ACK가 두 위상에서 함께 개선돼야 선택한다. 검사선을 늦추거나 ACK를 조기에 확정하지 않는다.
4. 부분 비용이 줄어도 전체 조건을 통과하지 못하면 선택하지 않는다. 이번 두 변형을 더 작은 상수·seed로 반복하지 않는다. 보드·65816을 바꾸는 구조가 필요하면 그 경계의 STOP·독립 검사와 ROM 결합 전체 Lite FIT/STA를 추가한다.

## 검증 경계와 자원

후보별 실제 ARM의 수신 IO/CRC/service/deadline, packet routing/STOP, 잘못된 credit·중간 취소·최종 ACK 실패, 메뉴 5조건과 base 복구 정상/실패 5조건을 모두 통과했다. `drain`에는 19행 특수 조건이 아닌 단일 map 행의 소비 완료·실패 5조건을 추가했다. 최종 ACK 실패 시 이력이 확정되지 않는다. 모델이 주입하는 응답 경계와 실제 CPU 실행 범위를 각 검사 JSON에 남긴다.

| 자원 | MMC666 | linear | drain |
|---|---:|---:|---:|
| ARM Flash | 212,496B | 212,512B | 212,544B |
| 남은 Flash | 496B | 480B | 448B |
| data / BSS | 10,040 / 19,544B | 동일 | 동일 |
| FPGA / 65816 | 665 선택본 | 동일 | 동일 |

선택 보드 입력·ROM·전체 timing 보고서 hash를 확인한다. 기존 Lite 전체 FIT 15,324 LE·962 LAB·56 M9K, setup +0.511 / hold +0.149 / recovery +1.828 / removal +0.393ns를 유지하며 회로 변경 없는 합성을 반복하지 않는다. 캡처 회복은 같은 HDL과 MMC666의 REJECT→RECOVERY 실기 근거를 유지한다. 새 실기·외부 IO 전체 sign-off·물리 60fps를 주장하지 않는다.

## 재현

- `prepare_nes_output668.py BASE_ARM OUT_ARM --mode linear|drain`은 MMC666 firmware 해시를 먼저 확인한다. `build_nes_trial577.ps1 -SourceRoot OUT_ARM`으로 전체 링크한다.
- `check_nes_output668.py`는 실제 ARM 검색 결과를 독립 참조와 비교한다. `check_nes_map668.py`는 단일 map 행의 drain 경계를 확인한다.
- `test_nes_output668.py`는 664/660 실제 연결 실행에 읽기 전용 탐색 계측만 추가한다. 원본 53개 ACK 일치를 확인하므로 계측이 시간 모델을 바꾸지 않았음을 대조한다.
- 로컬 `../probes/nes-output668/replay.ps1`은 base/linear/drain·두 위상 인자를 기록한다. 출력은 ASCII Temp의 `nes-output668-*`, ARM·guard는 `../probes/nes-output668`에 보존한다. 상용 ROM·고정 캡처·Mesen·도구 체인은 Git에 포함하지 않는다.

```text
python tools/test_nes_output668.py --emit --game GAME_NES --geometry650 --sender653 SENDER661_JSON --commit-pop-bound --arm ARM_SRC --client CLIENT665 --samples STIM601_TSV --data DELTA231_TEST07 --fixture DENSE519_FIXTURE02 --plans SEAL538_PLANS01 --capture OUTPUT489_AUDIT01 --calendar SERVICE509_ROM03 --driver503 analysis/hardware503-mmc502.json --mesen MESEN --start-clock 7288416 --out ASCII_OUT --keep-run
```

분석은 `analyze_nes_output668.py --mode linear`로 첫 후보를 저장한 뒤, 같은 인자의 `--mode drain --linear-result LINEAR_JSON`으로 합친다. 필수 경로는 `--traces`, `--probe`, `--base-arm`, `--old-arm`, `--arm`, `--client`, `--board`, `--out`이다. 기준은 MMC666 ARM·664 all ARM·665 client/board이며 원본 해시가 다르면 중단한다. 드레인 후보의 `--probe`는 `drain-checks`다.

실행·후보 바이너리·변경 C·guard·분석 도구 1,210개 파일은 `../probes/nes-output668/archive01/evidence.zip`(7,042,027B)에 보존하고 압축 해제 바이트를 전부 재검증했다. ZIP SHA256은 `b49ab584a7bd40e53981fa59bd3e731f8c31f059ac1af832af0290126bdfa5d7`, manifest SHA256은 `529b3a828d98d028b9692c10d823eec8ffd6111216f886a591050806af37ee0e`다. 개인 원본·게임 ROM·도구 라이선스는 Git에 올리지 않는다.
