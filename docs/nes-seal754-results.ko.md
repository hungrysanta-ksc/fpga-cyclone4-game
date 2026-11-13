# 754 · 957의 두 번째 VBlank 마감

753에서 가장 가까운 화면은 957이었다. 두 위상 모두 직전 공개 이후 SEAL을 가장 먼저 수락했고, 남은 PPU DMA도 가장 적었다. 판정 기준은 753과 같은 리셋·시작 클록에서 957 표시 2회, 951→957 여섯 표시 간격의 평균과 957 최종 ACK 동시 개선이다. 952·957의 1,536B map은 SEAL 수락 전에 보내고 957의 288B OBJ는 그 map과 같은 VBlank의 256선 이내에 시작해야 한다. [검증값과 원시 기록 해시](../analysis/seal754-verification.json)

## 어디서 마감을 놓쳤는가

| 화면 | 직전 공개 → SEAL 수락 ms, 위상 1 / 2 | 수락 후 남은 PPU DMA |
|---|---:|---:|
| 952 | 43.866 / 43.456 | 818B |
| 953 | 42.240 / 42.289 | 690B |
| 954 | 41.418 / 41.295 | 706B |
| 955 | 41.735 / 41.451 | 754B |
| 956 | 43.280 / 43.269 | 498B |
| 957 | **38.918 / 39.054** | **242B** |

957의 긴 map과 OBJ는 이미 두 번째 VBlank를 쓴다. SEAL 수락 시점은 이어지는 활성 화면의 66 / 68선이다. 수락부터 독립 검사를 거쳐 첫 업로드 대기에 들어가는 시간은 1.889 / 1.892ms다. 세 번째 VBlank에 raw 64B 두 건과 팔레트 2B·OAM 112B를 쓰고 235 / 236선에 공개한다.

긴 map을 첫 번째 VBlank로 옮기는 경로를 따로 계산했다. 그 VBlank의 실제 957 빔 래치를 기준으로 248선 끝과 마지막 map 패킷의 실제 수락 완료 ACK를 비교하면 **14.647 / 14.932ms** 차이가 난다. 이 값은 해당 선행 경로의 낙관적 필요량이다. 큐가 빈 시각, 48B BG, 1,536B map 및 288B OBJ의 DMA 설정·완료도 들어맞아야 한다. 다른 명령 순서에 대한 보편적인 하한은 아니다.

956 최종 ACK부터 957 마지막 map 반환까지 SPI 점유만 두 위상 모두 약 17.18ms였다. 입력 D1 1,120B, E1 2,357B, 나머지 credit·plan·반환 거래를 포함한다. 같은 구간의 벽시계 시간은 31.732 / 32.022ms다. 첫 VBlank의 248선 끝까지 사용 가능한 시간은 17.085 / 17.090ms다. 기존 거래를 그대로 이 구간 안에서만 실행하면 SPI만으로도 0.094 / 0.089ms 초과하며 ARM 계산·IRQ·ROM 대기와 DMA 설정에 쓸 시간이 없다.

## 실제 ARM과 65816 변경

- **입력 루프 공유**. 앞선 SEAL을 기다리며 7번째 블록을 반환한 뒤, warm 뱅크에 CRC·token을 확인한 128B 이상 head가 있으면 같은 수신 루프에서 최대 6블록까지 더 처리했다. 다음 입력이 준비되지 않거나 geometry 단계가 끝나면 반환한다. 이전 최종 ACK·EA가 다음 COMMIT의 선행 조건이다. 956 ACK 전 수신은 8→10 / 8→11블록, 입력 시작→planner는 약 2.08ms 단축됐다. 전체 ARM Flash 212,988B로 4B가 남았다. 별도 루프 후보는 213,008B로 16B 초과했다.
- **scroll 선행 발행**. 확정된 section 5 scroll을 최종 map 순회 앞으로 옮겨 독립 WRAM 수락 시간을 분리했다. 957 SEAL은 직전 공개 기준 0.105 / 0.494ms 일러졌지만 908 표시가 두 위상 모두 2→3 VBlank로 밀렸다.
- **raw DMA 설정 단축**. 65816 자체가 검증한 6행 이력 마스크가 `0x1D`이면 변경된 두 행만 직접 선택한다. 원래의 각 64B 서비스·STOP 검사, 목적지와 실제 전송 크기를 유지한다. 753 ARM으로 raw 실행 구간은 7,800 / 7,800→3,596 / 3,636 마스터클록이 됐다. 전송량은 그대로 128B다. 본문은 34B 늘었고 물리 ROM에는 25B가 남았다. 두 행 직전 각각 STOP을 주입해 실제 DMA 차단, 취소 응답 `0xE4`, 이전 956 RGB 보존을 확인했다.
- 리셋부터 같은 53화면을 실행하고 각 화면의 패킷 작업량과 RGB를 비교했다. 65816은 실제 정적 ROM이고 ARM은 전체 링크 이미지다. SPI·IRQ·ROM 경쟁은 707D 기록을 적용한 모델이다. 회로는 707D를 재사용했다. 메뉴·base 복귀는 링크 ARM의 종료 시험 범위다.

## 전체 링크 결과

각 칸은 위상 1 / 2다. 변화량은 같은 위상의 753 대비이며 음수면 빨라졌다. 753의 밀집 평균은 49.909830 / 49.912453ms, 957 ACK는 리셋 후 65,365,252 / 66,080,216 마스터클록이었다.

| 후보 | ARM Flash | 957 표시 VBlank | 밀집 평균 변화 µs | 최종 ACK 변화 ms |
|---|---:|---:|---:|---:|
| scroll 선행 | 212,948B | 3 / 3 | +2.173 / -1.443 | +49.913 / +33.257 |
| 별도 입력 루프 | 213,008B | 3 / 3 | -34.765 / -93.044 | -33.278 / -49.918 |
| scroll + 별도 루프 | 212,996B | 3 / 3 | -47.057 / -49.743 | -16.650 / -16.661 |
| 공유 입력 루프 | 212,988B | 3 / 3 | -37.668 / -63.540 | -33.289 / -49.918 |
| raw 두 행 직접 선택 | 212,960B | 3 / 3 | -31.165 / -37.311 | +16.444 / -0.212 |
| 공유 루프 + raw 직접 선택 | 212,988B | 3 / 3 | -69.655 / -74.063 | -33.485 / -50.135 |

결합 후보는 952·957의 1,536B 선행 DMA, 749 E8 시작·종료 마감, 두 위상 OBJ 244선, 957 최종 대기 0회, 908·911 각각 2회를 지켰다. 951 공개는 239 / 240선이었다. 951에 이르기 전에 표시가 이미 2 / 3 VBlank 앞섰고 952–957 여섯 간격은 모두 3회였다. 전체 종료와 각 VBlank 안의 공개 시각은 개선됐지만 이 구간에서 줄인 VBlank는 0회다. 753을 비교 기준으로 유지하고 결합 후보는 재현 가능한 부분 개선으로 보존한다.

## 같은 수신기로 분리한 공급 시각 시험

753 원래 발행 시각을 재생하면 두 위상 모두 모든 소비 이벤트와 53화면 RGB가 동일하다. 각 E1 길이·거래 시간, 4개 queue credit, 2개 bulk 소유권, 이전 화면 최종 ACK와 새 패킷 우선을 유지한 채 957의 패킷 제공 시각만 바꿨다. ARM의 생산·ROM 제공을 앞당기는 비용은 이 재생 바깥에 있다.

| 957 공급 조건 | 표시 VBlank, 위상 1 / 2 | 관측 |
|---|---:|---|
| 원래 753 | 3 / 3 | OBJ는 두 위상 모두 246선 |
| 마지막 tile 이후 최대 8.5ms 선행 | 4 / 4 | SEAL 수락이 3.385 / 3.230ms 빨라져도 빈 큐 선행 DMA 기회 상실 |
| 전체 최대 8.5ms 선행 | 4 / 3 | 두 위상 모두 map·OBJ 같은 VBlank 조건 실패 |
| 전체 최대 16.64ms 선행 | 2 / 2 | 288B OBJ가 map 다음 VBlank의 225선으로 이동 |
| 같은 16.64ms + 마지막 map 뒤 ordinary 제공을 1ms 늦춤 | **2 / 2** | 1,536B map 뒤 OBJ가 같은 VBlank의 **253 / 252선**에 시작 |

마지막 재생의 957 표시는 33.027 / 33.026ms, 밀집 평균은 47.137 / 47.137ms, 최종 ACK는 753보다 약 16.64 / 16.66ms 일렀다. 이 재생은 956 ACK 약 0.050ms 뒤에 첫 BG를 큐에 넣었다. 실제 753은 957 입력 COMMIT이 8.408 / 8.465ms, planner 진입이 10.454 / 10.511ms 뒤다. 재생의 2 VBlank에는 아직 이 생산 비용이 빠져 있다.

## 재현

1. `prepare_nes_seal754.py`에 `--base ../probes/nes-credit753/arm-prefix --policy K --out ../probes/nes-seal754/patch-K`를 주고 기존 `build_nes_mmc479_arm.ps1`으로 각각 전체 링크한다. K는 section, geometry, both, shared다. `build_nes_seal754.py`는 `--client ../probes/nes-static751/sharedfast --raw ../probes/nes-reuse635/client04 --out ../probes/nes-seal754/raw`로 실행한다.
2. `run_nes_seal754.ps1`의 `-Variant K -Phase N -Game <ROM> -TraceRoot <temp>`로 두 시작 위상을 실행한다. raw는 753 ARM과 새 ROM, combined는 shared ARM과 새 ROM이다. 전체 링크와 같은 시작점을 사용해 부팅 압축 시간까지 반영한다.
3. `replay_nes_deadline711.py`에서 `--trace <temp>/nes-credit753-prefixN --client ../probes/nes-static751/sharedfast --mesen <Mesen.exe> --generation 957 --through 957`를 고정한다. 출력 경로는 `<temp>/nes-seal754-replay-T-N`이다. T에 대응하는 (mode, advance-us, tail-gap-us)는 control0 (control,0,0), tail8500 (tail,8500,0), all8500 (all,8500,0), all16640 (all,16640,0), gap16640 (all,16640,1000)이다.
4. `check_nes_seal754.py`로 shared의 `--arm ../probes/nes-seal754/arm-shared/src --out ../probes/nes-seal754/guards-shared.json`을 생성한다. `check_nes_static751.py`의 before/during/head/stale는 shared와 combined의 두 위상 기록에, `check_nes_seal754_raw.py --row 0|2`는 raw의 두 위상 기록에 적용한다. 각 출력 경로는 `analyze_nes_seal754.py`의 consumer_guards, raw_STOP 항목에 따른다. 마지막으로 `analyze_nes_seal754.py --temp <temp> --probe ../probes/nes-seal754 --out analysis/seal754-verification.json`을 실행한다.
