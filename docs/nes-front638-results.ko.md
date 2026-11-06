# 638 — 953 입력 복원부터 첫 BG ROM 공급까지

637의 두 블록 후보 F가 비교 기준이다. 952에서 확보한 VBlank 한 번을 953 이후까지 유지할 수 있는지 확인하기 위해 ARM 변경을 세 경우로 나눴다. 65816, FPGA, 입력·출력 데이터, 두 슬롯, SysTick, 실기 기반 SPI 서비스 비용 및 기록된 ROM 허용 일정은 637의 동일 조건과 짝지었다. [637 결과](nes-dma637-results.ko.md)

**결합 후보를 다음 실기 준비 대상으로 선정했다.** 네 조건 모두 951은 3회·246번 선 이내, 952는 4회, 953은 4→3 VBlank, 957의 최종 추가 대기는 0회다. 951~955 합계는 19→18 VBlank다. 마지막 ACK는 같은 시작 시각에서 905~957 전체를 실행한 누계다.

| 조건 | 951 공개선 | 밀집 평균, 637 F → 638 결합 (ms) | 957 최종 ACK 차이 (ms) |
|---|---:|---:|---:|
| 부팅 중 1 | 246 | 63.143 → 59.809 | -65.909 |
| 부팅 중 2 | 246 | 63.217 → 60.004 | -82.819 |
| 부팅 후 1 | 246 | 63.163 → 59.834 | -82.992 |
| 부팅 후 2 | 245 | 63.160 → 59.870 | -66.538 |

**왜 개선됐나.** 952 표시 기준 953 D3 완료는 15.37~15.57 → 10.86~11.90 ms였다. 더 빠른 수신으로 이전 표시 전에 POP까지 끝낸 블록도 4개에서 6~7개로 늘었다. planner 진입 후 첫 E9 완료까지는 약 3.99 → 3.36 ms였다. 같은 953 plan에서 E9 거래는 2→3건, 146→154 B로 늘었지만 첫 BG ROM 응답은 33.25~33.41 → 16.48~17.30 ms에 도착했다. 마지막 OBJ ROM 응답부터 SEAL 수락까지도 결합 후보에서 6.30~7.48 ms였다. 수신 명령 절감, 표시 전후로 옮겨간 블록, ROM 대기는 겹치는 비용이므로 단순 합산하지 않았다.

발행만 바꾸면 네 조건 모두 953은 여전히 4회였다. 수신만 바꾸면 953은 모두 3회였지만 세 조건에서 951·952가 4·5회로 늘었다. 결합만 모든 조건을 통과했다. 원본 영상·PPU·map·tile 작업 비교, STOP·독립 검사와 최종 ACK 경로를 검사했다. 같은 637 보드 ROM·RTL을 사용하므로 해당 Lite FIT·STA 결과가 적용된다. ARM Flash 여유는 60 B다. 이번 단계는 실기 FPS를 측정하지 않았다.

다음은 637에서 남은 252번 선 수평 clock 1,000 이후 latch의 DMA 종료·STOP 검증, 그 뒤 새 파일명을 쓴 전체 링크·메뉴/base 복귀·설치본 점검이다. 성능 비교는 MMC613과 같은 동선에서 5–40초와 40–55초를 구분한다. RESTORE는 제외한다.

## 수신과 발행을 분리한 방법

- **수신만** 바꾼 경우에는 동일 map 값의 반복 레코드에서 tile 요구 비트를 한 번 설정한다. 네 셀을 담는 packed 레코드는 대상 범위와 패딩을 검사한 뒤 고정 15비트씩 풀어 원래 주소에 저장한다. 각 셀의 tile 요구와 BG·OBJ 공유 비트를 보존한다. D1 CRC는 기존 E1에도 링크된 CCITT 루틴을 초기값 `0xffff`로 호출한다. D1의 유효 길이는 1~256 B다.
- **발행만** 바꾼 경우에는 resident 할당기가 첫 BG를 확정하고 plan에 추가한 즉시 E9 묶음을 보낸다. 이전 warm 경로에서 묶음 개수나 행 경계를 기다리던 시간을 줄이는 대신 추가 SPI 거래가 생길 수 있다. D3·COMMIT·bank 소유권 확인과 기존 E9 credit은 그대로 거친다.
- **결합** 후보에서는 두 변경을 같은 ELF에 링크했다. 세 후보의 Flash는 각각 212,940 / 212,952 / 212,932 B다. 기존 보드 ROM과 RTL을 그대로 사용했다.

수신기 단위 시험은 cold 905와 951·952·953·957의 매 POP 및 D3 prepare 후 수신기 전체 메모리를 637 ELF와 비교했다. 토큰은 65530에서 시작해 wrap을 거쳤다. 정상 packed 끝 행·속성 혼합·기존 OBJ 요구와 BG 요구의 합집합, 잘못된 범위·상태·세대·레코드 폭·잘린 패킷 등 13개 경계 사례도 대조했다. 953의 수신 명령은 **295,392 → 216,399개**였다. 84 MHz·CPI 2 환산은 약 1.88 ms로, 표시 전에 이미 실행한 블록의 절감까지 포함한다. 연속 일정에서 독립 DMA·VRAM 검사를 실행했다. 별도 ARM 시험에서 첫 E9의 BG·slot·tag, 잘못된 E8 CRC, E9 수락 직후 STOP, 표시 이력 보존과 최종 ACK 거절을 확인했다.

## 재현

1. `tools/prepare_nes_front638.py ../probes/nes-dma637/arm05 ../probes/nes-front638/<mode> <mode>`를 `receive`, `first`, `both`에 실행하고 각각 `tools/build_nes_trial577.ps1`로 전체 링크한다.
2. [636의 연속 일정 명령](nes-export636-results.ko.md)에서 ARM은 각 후보, client는 `../probes/nes-dma637/client01`로 바꾼다. 905~957의 53화면을 `nes-front638-<mode><phase><tag>`에 기록한다. d는 부팅 중 3,000,000 / 3,178,684, h는 부팅 후 7,288,416 / 7,467,100 master clocks로 시작한다. h는 `--commit-pop-bound`를 사용한다. 병렬 실행 도중 `first1d`, `both1d`, `both2d`는 초기 Mesen RPC callback의 호스트 30초 시간 제한에 걸렸다. 해당 폴더는 보존하고 부하가 낮아진 뒤 동일 옵션으로 새 폴더 `-r2`에서 다시 실행한다. 각 실행과 같은 접미사의 `nes-dma637-two` 추적을 대조한다.
3. `tools/check_nes_front638.py --base ../probes/nes-dma637/arm05 --build ../probes/nes-front638 --data ../probes/nes-delta231/test07 --out ../probes/nes-front638/map-guards.json`으로 수신기를 검사한다. 각 ELF에서 `check_nes_overlap634_arm.py --in-place --before-seal`, `check_nes_dma637.py --late-receive --late-blocks 2`를 실행해 각각 `<mode>-faults.json`, `<mode>-seal.json`에 저장한다.
4. `tools/analyze_nes_front638.py --traces <raw> --calendar <raw>/nes-service509-rom03 --build ../probes/nes-front638 --out analysis/front638-verification.json`으로 확인한다. [조건별 수치와 해시](../analysis/front638-verification.json)
