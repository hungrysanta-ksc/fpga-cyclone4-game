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

1. **실기480 실패 분석 완료.** [481 시작 분석](../../docs/nes-mmc481-startup.ko.md)·[실기 JSON](../../analysis/mmc481-hardware480.json)을 먼저 읽는다. 사용자 ROM 해시 일치, 전체384KiB 적재/비교·START·NES observer·STOP/base/메뉴 복귀 정상이다. SNES boot214가5초 stage0/flags0으로 종료해 게임 FPS는 미측정이다.
2. **추가 기능 검사 완료·실물 원인 미확정.** 전달480 BI3의 실제 C 복원·MIF/프로그램 일치와 실제 RTL4100ROM read/status/STOP을 확인했다.480 Mesen은 로컬 SFC에서 시작하고 console startup은 모델이었다. 이 간극을 기록하며 물리 버스 부팅 증명으로 승격하지 않는다.
3. **481 진단 후보 구현·전달 보류.** profile7a/status3, 기존 snapshot의 raw 핀을 ARM에서 누적한다. 실제 parser256종/거부·누적과 전체 RTL4100read/STOP PASS. candidate03/FIT15264LE의 관련 setup−0.228ns로 diagnostic_trial_ready=false다. candidate01/02도 기각·보존했으며 현재 선택 SDC/seed는479와 같다. [후보 JSON](../../analysis/mmc481-verification.json).
4. **다음 작업:** 해당 JSON의 check_failed→loader.error_code[1] 경로를 먼저 검토해 최소 진단 경계와 타이밍 조건을 확정한다. 추가 계측/seed 탐색/범용 FSM 교체·FIT 반복을 다음 목표로 삼지 않는다. 미달 산출물·481 ZIP은 전달하지 않았다.
5. 준비 조건을 통과한 새 번호·marker·로그·원복 ZIP으로 사용자 설치/시작·메뉴 복귀를 확인한 뒤 실제 게임 수신·계획·표시/FPS 분석을 진행한다. ROM은 같은 원본을 쓴다.480 재시험·보드/SD의 PC 연결은 요구하지 않는다.

## 게임 진입 관문478 결과

[478 보고](../../docs/nes-game478-feasibility.ko.md)·[해시/비용](../../analysis/game478-feasibility.json). 기존 SMB3 기록71개를 실제474/476 M4에서 처리해 활성 canonical·전체 상태/출력 plan이 같음을 확인했다. 수신 절감 중앙48.22% 유지, 계획은799681명령 중앙값으로 문양 warm의4.63배다. host2232 encoder·SPI/plan 완료 모델이며 실기 게임/FPGA byte-stream proof는 아니다.

기존 MMC3 cart를 복원한 whole Lite FIT은15266/15408LE(잔여142),14069comb/8387FF/256608bits다. 관련 setup+0.187ns/hold+0.146ns지만 raw setup−6.499ns/recovery−9.140ns·reset/CDC/IO는 미완료다. 자동 CIRAM/HEX와 transitive cdc181.sdc까지69파일을 고정했다. 원래66 QSF 항목만으로 입력이 완결된다고 가정하지 않는다.

478 당시 진단은ID78/NROM loader로 실기 사용 금지였으며 이는 그대로다. 현재 전용 후보는 아래479/480 결과를 따른다. `probes/nes-game478/mmc03`에 source/보고서를 보존했다. seed/제약 완화 없이 올바른 의존성을 갖춘map03/fit03을 선택했다.

## 479 현재 개발 후보

전용ID79·엄격 CRC5a04eed7/393232B loader를 복원했다. 실제 FatFS/programmer/run136 host20건 PASS(보드 IO/native 모델). ARM479-03 firmware212356B(−284B)/text202313·data10040·BSS18552, 후미636B. 변경 없는73object의 ALLOC영역이476과 같다. whole Lite FIT15260LE(148잔여)/14069comb/8387FF/256608bits, implementation 관련 setup+0.235/hold+0.154ns; raw reset/CDC/IO 미완료.

70ns ROM·seeded loaded/verified core/source에서 부팅 blank 거부 후generation12의15packet/3206B·END/COMMIT·STOP PASS. 같은 실제 packet의 linked476/479 M4 상태·40B tile plan18개가 같다. 수신288231/계획330833명령은 cycles/FPS가 아니다. live ARM·tile ROM·65816 표시·실기 게임은 아직 미통과다. private 선택 source는 `probes/nes-mmc479`와 그 안 execution-location.json을 따른다. 기존476 선택은 그대로 유지한다.

## 480 현재 비공개 실기 후보

실제 source15packet/3206B → selected ARM C/plan·실제 tile ROM → staging → 실제65816 DMA/독립 검사/최종ACK·EA·run136 STOP을 한 실행에 연결했다. ACK34/commit1/retire2/VRAM4416B. 별도 관찰 NES PPU와 SNES 화면57344픽셀 모두 동일(고정 Mesen239 여백7/8 반영). 실제 M4/IRQ 공통 시간·실기 FPS는 아니다. linked480 M4의 해당 live 입력 복원/plan도 동등하다.

ARM480은479에서 menu/checkpoint label만 변경(75object ALLOC 동일); firmware212356B/후미636B. 같은479 FIT15260LE/148잔여 DB의 ASM/CPF/BI3 roundtrip만 수행했고 새 MAP/FIT는 안 했다. [480 package](../../analysis/mmc480-package.json). 원본 source/trace/PPU/RGB는 `probes/nes-mmc480/executed`에 비공개 보존했다. 제품 공개/전체 CDC·IO·실기 승인은 아직 없다.

## 코드와 보존 경계

- `tools/analyze_nes_receive477.py`: raw 실기 누계/종료·동일 장면 비교. `tools/prepare_nes_receive476.py`, `profile_nes_receive476.py`, `check_nes_receive476.py`: 현재 수신 변경·실제 M4·오류 경계.
- 실제 ARM source는 `probes/nes-nrom418/arm476-02/src`. `src/nes/experimental471`을 전체476 source로 착각하지 않는다. [로컬 입력](REPRODUCING.ko.md) 참조.
- 실기476의 `cart_nrom.sv`는 고정 NROM16/H·CHR8이고 해당 loader는 다른 profile을 거부한다. 479는 별도MMC3/ID79 구성이다. SMB3는 MMC3/mapper4다. 검사만 해제하거나 ROM만 바꾸어 시험하지 않는다.
- 독립 CRC/coverage·epoch/generation/token·실제 DMA 소비·STOP/stale DONE/ACK 차단·최종ACK 뒤 commit/EA·base/DONE/SPI/token/menu 복구를 유지한다.
- export COMMIT 뒤 다음 capture는 이미 시작한다. 다음 export는 이전 표시 lease retire까지 막힌다. 이를 새 중첩 성과로 계산하거나 단일 receiver를 이전 표시 중 덮지 않는다.
- GBC164/save와 G13C44/0.9.0, 기존476/474/471/467/164 복원물을 보존한다. 실기는 사용자 ZIP 설치/TXT 반환 방식이며 PC에 SD/보드 연결을 다시 요구하지 않는다.

## 전체 예산과 미완료

FPGA14740LE/13672comb/8063FF/185824bits, nominal 관련 setup+0.081ns/hold+0.143ns. 강화 예산−0.036ns·raw reset/CDC/미제약IO는 미해결이다. 668LE 산술 잔여를 MMC3 FIT 여유로 간주하지 않는다.

ARM text202597/data10040/bss18552B, Flash 파일 후미352B. RUN frame31848B·산술 RAM4984B는 중첩 호출/IRQ 전 값이다. 476은 관련 static stack48/560B가 그대로다. 평균30fps까지8.615ms,60Hz까지25.282ms는 해당 문양의 평균 격차이며 실제 게임 예산이 아니다. full callchain/물리 WCET·연속 capture 무손실·p95·실제 게임/MMC4/5·전체 CDC/IO는 미완료다.

Quartus Lite와 기존 Starter FLOAT1좌석 순차 실행을 유지한다. 479에서 실제 ARM build·Lite MAP/FIT/STA·단일 core/source Questa 시험을 실행했다. README는 의미 있는 진척·정정 시에만, 상세는 PR 네 항목과 [현재 계획](../../docs/nes-replan472.json)에 남긴다.
