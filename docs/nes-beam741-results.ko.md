# 741 · 957의 BG와 map 선행 DMA

**727을 유지한다.** 두 시작 위상에서 957의 마지막 OBJ 명령과 OAM 이력 검사를 246선 안에 마치고, 같은 VBlank에서 384B map → 48B BG → 1,536B map을 순서대로 DMA했다. 마지막 OBJ 288B는 최종 업로드에 남았다. 실제 map 반환을 확인하고 D0 입력 서비스를 부과한 일정에서는 두 위상 모두 727의 표시 간격과 마지막 ACK를 앞당기지 못했다. [검증 수치와 원시 파일 해시](../analysis/beam741-verification.json)

## 727에서 수락을 막은 구간

957의 마지막 OBJ는 1,536B DMA 시작 전에 두 위상 모두 staging에 준비돼 있었다. 이전 BG 토큰이 반환된 뒤에도 ARM이 OBJ descriptor를 조회하기까지 7.996 / 7.789ms가 걸렸다. 실제 OBJ E1 발행 순간 큐 점유는 0이었다. 741에서는 마지막 map의 실제 소비 ACK와 identity를 확인한 뒤 OBJ와 OAM을 발행했다. OAM ACK는 246선 끝보다 0.381 / 0.345ms 빨랐다. [727의 staging·토큰·credit 시각](nes-owner739-results.ko.md)

## 선행 DMA가 최종 표시에 미친 효과

각 칸은 위상 1 / 위상 2다. 밀집 간격은 951 공개부터 957 공개까지 여섯 간격의 평균이다. ACK 차이가 양수이면 727보다 늦다. 모든 정상 비교에서 952의 1,536B DMA를 보존했다.

| 일정 | 957의 1,536B 선행 DMA | OBJ 선행량 | 밀집 표시 간격 (ms) | 957 마지막 ACK 차이 (µs) |
| --- | --- | ---: | ---: | ---: |
| 727 | 양쪽 | 0B | 49.932319 / 49.932304 | 기준 |
| 740 첫 완료로 후속 전송 재개 | 양쪽 | 0B | 49.940591 / 49.943044 | +49.634 / +64.440 |
| BG 48B만 먼저 선택 | 1,152B / 0B | 0B | 49.962941 / 50.045353 | +183.729 / +678.298 |
| 741 실제 map 반환·D0, 첫 DMA 완료에 후속 전송 연동 | 양쪽 | 0B | 49.933188 / 49.935997 | +5.215 / +24.025 |
| D0를 앞선 SPI 유휴 구간으로 이동 | 양쪽 | 0B | 49.933188 / 49.934896 | +5.215 / +15.551 |
| OBJ·OAM을 가장 일찍 제공한 진단 대조군 | 양쪽 | 64B | 49.931124 / 49.932024 | −7.170 / −1.676 |

65816은 직전 DMA 완료 뒤 STOP과 새 큐 head를 확인하고, 다음 descriptor에서 빔을 다시 읽었다. 1,536B map의 빔 표본은 249선 수평 클록 1,130 / 250선 수평 클록 500이었다. 마지막 PPU 쓰기는 260 / 261선에 끝났다. 위상 2에서 실제 명령 지연을 넣어 표본을 250선 수평 클록 644로 옮기면 1,152B로 제한됐다. 전체 map을 허용한 512클록 경계까지 원래 위상 2의 여유는 12클록이었다.

두 위상 모두 첫 scroll 패킷이 긴 map의 마지막 PPU 쓰기보다 **292 / 298µs 먼저** 준비됐다. DMA가 끝나자 새 패킷이 우선되어 OBJ를 선택할 빈 큐가 없었다. 이때는 OBJ 64B를 허용한 마지막 빔 표본인 257선도 이미 지났다. 실제 D0 전송과 ARM 처리 124µs를 앞선 유휴 구간에 겹쳐 넣어도 scroll은 양쪽 모두 약 290µs 먼저 도착했고 map은 258 / 259선에 끝났다. 후속 전송은 각 후보의 실제 첫 384B 완료 신호에 연결했고, 완료부터 scroll 발행까지 740의 조회·발행 비용을 다시 부과했다.

가장 이른 진단 일정에서는 OBJ 첫 64B를 DMA하고 남은 224B의 source·destination·길이로 독립 검사를 통과했다. 이 일정은 마지막 map 반환 확인과 입력 서비스까지 포함한 ARM 발행 일정을 증명하지 않는다. 개선 폭은 두 위상 모두 8µs 미만이었고 957 표시는 모든 경우 3 VBlank였다.

## 보호 조건과 비용

- 실제 65816 명령을 Mesen에서 실행하고, 905–956의 CPU 이벤트와 master clock, 905–957의 53개 최종 화면 RGB·패킷 identity·ACK를 대조했다. 951 공개는 246선 이내, 952 표시는 3 VBlank, 957 최종 추가 대기는 0회였다.
- BG 시작 직전의 STOP은 새 DMA를 막았다. OBJ 64B의 첫 PPU 쓰기에서 들어온 STOP은 해당 동기 DMA 완료 뒤 후속 DMA와 957 최종 ACK를 막았다. 오래된 OAM 이력은 0xE0으로 거부했다. 세 경우 모두 956 화면을 유지했다. 첫 scroll을 BG grant 직전에 주입한 경우에는 새 패킷을 먼저 수락했다. 기존 정상·장시간 ARM의 메뉴/base 복귀 5경로와 파일명 4조건도 각각 통과했다.
- 65816 실행 본체는 6,020B에서 6,123B로 늘었다. 기존 512B prefix로는 물리 ROM 예산을 88B 초과했고, 시험한 384·256·128B prefix에서도 각각 87·79·45B 초과했다. 실험 코드는 957 첫 패킷에서 WRAM에 설치했다. 새 ARM 전체 링크·FPGA 합성·실기 측정은 수행하지 않았다.

## 다음 작업과 재현

727에서 마지막 map 반환과 OBJ descriptor 수락의 identity를 함께 확인할 수 있는 기존 응답을 먼저 찾는다. 이어서 첫 384B 완료 때 발행하는 scroll과 OBJ DMA 사이의 약 0.29ms 충돌을 실제 ARM·SPI에서 없앨 수 있는지 확인한다. 두 위상에서 257선 이내 OBJ 선택과 새 패킷 우선이 양립하는 예산이 나오기 전에는 빔 허용선을 더 늦추지 않는다.

1. [740 재현 절차](nes-gap740-results.ko.md)의 727·694 client 및 두 위상별 `first`, `issued`, `checked` 시각과 진행 쓰기를 준비한다.
2. `tools/replay_nes_beam741.py --phase N --variant V --calendar C --trace <temp>/nes-gap740-CN-trace --client <694 client> --mesen <Mesen.exe> --out <temp>/nes-beam741-C-VN-trace`로 재생한다. `first`는 `control`, `bg`, `budget`, `issued`는 `fragment`, `overlap`은 `budget`을 사용한다. `overlap`의 입력은 동일 위상의 `first`다.
3. 두 `budget` 일정은 해당 첫 실행 폴더를 `--feedback`으로 지정해 출력 이름 끝에 `-feedback`을 붙여 다시 실행한다. 위상 2의 `first/budget`은 `--lag-nops 4`로 `-edgeprobe`에도 재생한다.
4. 위상 1에서 `first/budget`에 `--mode stop --inject before_bg`, `--mode stale`, `--inject head`를 각각 사용한다. `issued/fragment`에는 `--mode stop --inject during_obj`를 적용한다. 출력 이름 끝은 각각 `-stop-before`, `-stale-fault`, `-trace-head`, `-stop-during`이다. 740과 같은 두 메뉴 검사를 실행한 뒤 `tools/analyze_nes_beam741.py --temp <temp> --client <694 client> --probe <메뉴 검사 폴더> --out analysis/beam741-verification.json`으로 재검증한다.
