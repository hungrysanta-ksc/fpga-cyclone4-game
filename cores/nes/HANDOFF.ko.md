# 현재 NES 인계

기준일2026-10-29. **사용자 지시로 성능 개발 재개.** PR134 merge93bb8f715914da12d46f1d5c8262d6e8b10d3362의 master 도달을 확인했고 `codex/nes-receive-cost-476`에서 현재 PC의 원본으로 아래 순서를 진행한다. 먼저 [프로젝트 현황](../../docs/PROJECT-STATUS.ko.md)과 [새 PC 재개 안내](../../docs/development/RESUME.ko.md)를 읽는다. 채팅 이력·이전의 긴 AGENTS를 읽을 필요는 없다.

## 선택 구성과 관측

| 구성 | 고정 기준 |
|---|---|
| 실기 선택 구현 | PR134의 NROM474, ARM474-02, 구현 commit06c71479e82a4fa1d76cddb810ea751b71d89880 |
| FPGA | 471-04 byte 동일, BI3 SHA256 `2c54ca3dc34a12215fe0fdcc468dab12cd3f0a60d9381155167e271de73f518a` |
| ARM firmware | SHA256 `ebb73014542165c834a2e15b2d73fa8e2048deba873ba152bc7435ff6518d1e2` |
| 이동 ROM | 자체 scene02, SHA256 `21799ff5d55d68c688bb70ce0e41aedc76b7b6de0ccc276d24c8ded9dc10791e`, CRC0fddf31c |
| protocol | input2232 / client2271 / loader profile78 /4credit |
| 최신 실기 | receipt475, 두 번 모두60.07초/1417표시 =23.59fps, 정상 구간 약24fps |
| 핵심 결과 | 같은 장면471보다20.29% 처리율 향상; 계획13.63→6.09/6.07ms; CRC0·STOP/base/menu 정상 |

정확한 source/산출물 해시는 [474 verification](../../analysis/nrom474-verification.json), ZIP은 [package 명세](../../analysis/nrom474-package.json), 측정/해석은 [475 JSON](../../analysis/nrom475-hardware.json)·[475 문서](../../docs/nes-nrom475-hardware.ko.md)에 있다. 설치 ZIP/사용자 TXT·영상 자체는 공개 Git에 없다.

**다음 실기 후보476:** CRC byte 식·sparse tag 열거로 고정 M4 수신 replay506568→309481명령(−38.91%), SPI/복원 상태 동일. text+28B/BSS·stack 동일, Flash352B. 정상/8fault·CRC 전수·bitmap25094건·native C/RTL/65816 최종ACK/STOP을 통과했다. [476 검증](../../docs/nes-receive476-contract.ko.md) · [설치](../../docs/nes-receive476-trial.ko.md). 실기 FPS는 아직474 기준23.59다.

## 이어서 읽을 코드

먼저 `tools/prepare_nes_receive476.py`·`tools/profile_nes_receive476.py`·`tools/check_nes_receive476.py`를 읽는다. 아래는 재사용한474 기반 경계다.

1. `tools/prepare_nes_nrom474_arm.py`: 실제11파일 변경 재현. 같은 프레임 exact BG group 재사용·무진행 E0 quiet·opcode snapshot.
2. `tools/build_nes_nrom418_arm.ps1`: 전체 ARM 결합. **기존 PC의 경로/입력 가정이 있으므로 새 PC에서 그대로 실행하지 않는다.**
3. `tools/check_nes_nrom474_arm.py`, `tools/test_nes_nrom474_native.py`: 실제 링크 M4·독립 renderer·guard/ACK/alias 검증 경계.
4. `tools/analyze_nes_nrom474.py`, `tools/analyze_nes_nrom475_hardware.py`: 같은 소스 게이트와 실기 비교. 필요한 로컬 입력은 재현 안내에서 확인한다.
5. `src/nes/experimental471`은471 CHECK/계측 template다. 최신474 전체 소스 트리와 혼동하지 않는다.

## 보호해야 할 경계

- 단일 ARM 복원, 독립 CRC/coverage, epoch/generation/token, 실제 DMA 소비, STOP·stale DONE/ACK 차단을 유지한다.
- 저장 credit·소비 완료·최종 표시 ACK는 서로 다르다. 마지막 미완료 packet을 표시 수에 포함하지 않는다.
- 최종 ACK 뒤 resident commit/EA retire, base/DONE/SPI/token/메뉴 복구를 유지한다. deadline의 부수 sink_error는 최초 runtime_result와 함께 해석한다.
- `nes_capture_lease201`은 export COMMIT 뒤 다음 한 프레임 capture를 이미 허용한다. 다음 export는 이전 display lease retire 전까지 차단한다. 이를 새 절감으로 재계상하거나 ARM receiver를 이전 표시 중 덮지 않는다.
- 현재 설치 경로는4credit다. 연구 경로의2slot·338/355/402 후보를 자동 승격하지 않는다.
- GBC164/save와 공개 G13C44/0.9.0·기존471/467/164 복원물을 보존한다. 바뀌지 않은 복원·GBC 시험을 매번 요구하지 않는다.

## 비용과 미완료

- FPGA14740LE/13672comb/8063FF/185824bits. nominal 관련 setup+0.081ns/hold+0.143ns, 강화 배치 예산−0.036ns 및 raw reset/CDC/미제약IO는 미해결.
- ARM text202569/data10040/bss18552B, 큰 RUN frame31848B. Flash 파일 후미380B, BSS와 이 frame 뒤 산술 RAM4984B는 중첩 호출/IRQ stack을 빼기 전이다.
- 두 회차 수신18.40/20.67ms, 계획6.09/6.07ms, SEAL17.29/14.91ms. E0 감소 일부가 quiet/D0로 옮겨갔으며 credit 부족 대기는 거의 없다.
- 30fps 평균까지9.06ms,60Hz까지25.73ms/표시 격차. p95/capture 무손실/일반 게임/MMC4·5와 전체 CDC/IO signoff는 미완료다.

## 재개 후 순서

1. **현재474 기준 고정**: branch/PR/master 상태와475 근거를 확인한다. 과거 경로로 되돌아가거나 동일 실기를 이름만 바꿔 반복하지 않는다.
2. **수신 hot path 분리**: 실제474 M4의 CRC/record/guard·전송 비용을 profile한다. 이미 단일 복원이므로 이중 복원을 가정하지 않는다. Flash/RAM 예산부터 확인한다.
3. **기존 중첩 일정 확인**: capture start/done, export 허용/생산, ARM 입력, SEAL/최종ACK를 같은 시각에 연결한다. 두 실기의 수신/ACK 시간 이동이 어느 경계에서 생기는지 판별한다.
4. **후보 선택·최소 검증**: 실제 입력/일정 이득이 있는 변경만 독립 검사·STOP·최종ACK·메뉴 경로와 결합한다. RTL을 바꾸면 같은 전체 Lite FIT/timing, 유지하면 기존 bitstream 근거를 재사용한다.
5. **실기 전달**: 476은 검증된 후보이며 아직 실기 전이다. 동일 이동 ROM, 새 marker/로그/ZIP와 원복을 묶어 비교한다. 30fps는 중간 목표이며60Hz 달성과 분리한다.

추가 정보는 [현재 계획 JSON](../../docs/nes-replan472.json)·[PR134 기록](../../docs/progress/pr-134.md). 사용자 보드는 PC에 직접 연결하지 않는다. ZIP을 전달하고 사용자가 설치한 뒤 TXT를 돌려주는 기존 방식을 따른다. Quartus Lite, 기존 Starter FLOAT1좌석 순차 실행 원칙을 유지한다.
