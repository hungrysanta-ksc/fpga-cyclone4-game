# 현재 NES 인계

사용자 지시로 개발 재개. PR134 merge93bb8f715914da12d46f1d5c8262d6e8b10d3362의 master 도달을 확인했고 `codex/nes-receive-cost-476` / [PR135](../../docs/progress/pr-135.md)에서 진행한다. 현재 PC를 유지한다. 먼저 [프로젝트 현황](../../docs/PROJECT-STATUS.ko.md)·[실기477와 시험 대표성](../../docs/nes-receive477-hardware.ko.md)을 읽는다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | NROM476 / ARM476-02, commit d1de042c6dfadf6079a91f72a2745d58f1585e8d |
| ARM SHA256 | a57755e63dd04a9dbc1cfb93541b77361551d1b7af53f230bace80857019b49e |
| FPGA | byte 동일471-04, BI3 SHA256 2c54ca3dc34a12215fe0fdcc468dab12cd3f0a60d9381155167e271de73f518a |
| ROM | 자체 이동 scene02, SHA256 21799ff5d55d68c688bb70ce0e41aedc76b7b6de0ccc276d24c8ded9dc10791e, CRC0fddf31c |
| protocol | input2232 / client2271 / profile78 /4credit, cost_schema474 유지 |
| 실기477 | 1회60.07초/1432표시 =평균23.84fps, 정상 구간 약24fps |
| 비교 | 474 2회23.59fps. 수신15.65ms로 감소, SEAL19.58ms로 증가; 정상 cadence 개선 미입증 |
| 정상 종료 | CRC/driver/입력abort0, START·STOP·base·메뉴 복귀 정상; deadline 마지막 프레임의4packet 취소 |

선택 소스는 [476 verification](../../analysis/receive476-verification.json), ZIP은 [package](../../analysis/receive476-package.json), 실기는 [477 JSON](../../analysis/receive477-hardware.json)이다. 원본3TXT는 `probes/nes-nrom477/hardware01`에 byte 그대로 보존한다. 사용자 영상은 새로 받지 않았다.

## 현재 판단과 다음 순서

- 문양은 실제 core/전송·독립 검사·DMA/표시·STOP 회귀에 유효하다. OBJ0/warm mapdirty0/BG27/28group 재사용이므로 일반 게임/SMB3 성능을 대표하지 않는다.
- 고정 cold M4 수신506568→309481명령(−38.91%)은 기능/CPU 성과다. 실기 전체는+1.06% 평균·정상 구간 약24fps 유지로, 이를 큰 FPS 이득으로 승인하지 않는다.
- **이 문양60fps를 달성해야 실제 게임으로 가는 순서를 버린다.** 문양은 회귀 fixture로 남기고 게임 대표 입력과 실제 MMC3 진입을 다음 관문으로 둔다.

1. 기존 SMB3의 BG/OBJ·split/예외·bank/tag 기록을 현재 ARM/ABI와 대조해 비용·동등성을 본다. 기록 replay는 실기 게임이 아니다. 최소 고부하 NROM은 mapper 부하를 분리하는 보조 대조군이다.
2. 실제 MMC3/WRAM/IRQ·loader/PSRAM 배치·source/query/lease 교체 경계를 고정하고 동일 보드 전체 Lite 비용·입력 중 ROM 경쟁을 판정한다. 기존227의 SMB3 성공을 현재 경로의 성공으로 승계하지 않는다.
3. 구동 가능할 때 같은 조합의 SMB3 월드맵·1-1 이동·sprite/상태창·CHR 변경을 실제로 비교한다. source/display ID·누락/반복·간격/p95·입력·STOP/최종ACK/base/menu를 확인한다.
4. 새 설치본은 새 marker·파일명·원복과 묶는다. 새 후보 번호는 아직 선택하지 않았다. 동일 문양의 이름만 바꾼 반복 설치·옛 제어 미세 변경을 먼저 하지 않는다.

## 코드와 보존 경계

- `tools/analyze_nes_receive477.py`: raw 실기 누계/종료·동일 장면 비교. `tools/prepare_nes_receive476.py`, `profile_nes_receive476.py`, `check_nes_receive476.py`: 현재 수신 변경·실제 M4·오류 경계.
- 실제 ARM source는 `probes/nes-nrom418/arm476-02/src`. `src/nes/experimental471`을 전체476 source로 착각하지 않는다. [로컬 입력](REPRODUCING.ko.md) 참조.
- 현재 `cart_nrom.sv`는 고정 NROM16/H·CHR8이고 실제 loader가 다른 profile을 거부한다. SMB3는 MMC3/mapper4다. 검사만 해제하거나 ROM만 바꾸어 시험하지 않는다.
- 독립 CRC/coverage·epoch/generation/token·실제 DMA 소비·STOP/stale DONE/ACK 차단·최종ACK 뒤 commit/EA·base/DONE/SPI/token/menu 복구를 유지한다.
- export COMMIT 뒤 다음 capture는 이미 시작한다. 다음 export는 이전 표시 lease retire까지 막힌다. 이를 새 중첩 성과로 계산하거나 단일 receiver를 이전 표시 중 덮지 않는다.
- GBC164/save와 G13C44/0.9.0, 기존476/474/471/467/164 복원물을 보존한다. 실기는 사용자 ZIP 설치/TXT 반환 방식이며 PC에 SD/보드 연결을 다시 요구하지 않는다.

## 전체 예산과 미완료

FPGA14740LE/13672comb/8063FF/185824bits, nominal 관련 setup+0.081ns/hold+0.143ns. 강화 예산−0.036ns·raw reset/CDC/미제약IO는 미해결이다. 668LE 산술 잔여를 MMC3 FIT 여유로 간주하지 않는다.

ARM text202597/data10040/bss18552B, Flash 파일 후미352B. RUN frame31848B·산술 RAM4984B는 중첩 호출/IRQ 전 값이다. 476은 관련 static stack48/560B가 그대로다. 평균30fps까지8.615ms,60Hz까지25.282ms는 해당 문양의 평균 격차이며 실제 게임 예산이 아니다. full callchain/물리 WCET·연속 capture 무손실·p95·실제 게임/MMC4/5·전체 CDC/IO는 미완료다.

Quartus Lite와 기존 Starter FLOAT1좌석 순차 실행을 유지한다. 현재 확인에서는 새 build/합성/시뮬레이션을 실행하지 않았다. README는 의미 있는 진척·정정 시에만, 상세는 PR 네 항목과 [현재 계획](../../docs/nes-replan472.json)에 남긴다.
