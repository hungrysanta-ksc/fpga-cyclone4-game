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

1. **479의 새 ID79·정확 SMB3 loader·host20건·전체 ARM build/FIT·core/source 부팅·실제 패킷 M4 재생은 완료**했다. [479 계약](../../docs/nes-mmc479-contract.ko.md)과 [검증](../../analysis/mmc479-verification.json)을 읽는다. 새 게임 실기 설치본은 아직 없다.
2. **479 live ARM/tile plan·query/ROM·staging을 연결**한다. core/source smoke와 실제15packet→linked M4는 통과했다. 동시 shared SPI/IRQ·MMC3 bank/IRQ·첫 유효 입력/표시 deadline은 별도로 검증한다.
3. **paired65816 게임 표시·복구를 확인**한다. 실제 입력→DMA·독립 검사→최종ACK/EA→observer STOP/base/menu, 새 소스의 비용/timing을 연결한다.
4. 같은 조합의 게임 장면·소스/원복을 고정한 뒤 전달한다. 월드맵·1-1·sprite/CHR/상태창·음악/효과음·capture cadence를 비교한다. 새 설치본은 아직 없다.

## 게임 진입 관문478 결과

[478 보고](../../docs/nes-game478-feasibility.ko.md)·[해시/비용](../../analysis/game478-feasibility.json). 기존 SMB3 기록71개를 실제474/476 M4에서 처리해 활성 canonical·전체 상태/출력 plan이 같음을 확인했다. 수신 절감 중앙48.22% 유지, 계획은799681명령 중앙값으로 문양 warm의4.63배다. host2232 encoder·SPI/plan 완료 모델이며 실기 게임/FPGA byte-stream proof는 아니다.

기존 MMC3 cart를 복원한 whole Lite FIT은15266/15408LE(잔여142),14069comb/8387FF/256608bits다. 관련 setup+0.187ns/hold+0.146ns지만 raw setup−6.499ns/recovery−9.140ns·reset/CDC/IO는 미완료다. 자동 CIRAM/HEX와 transitive cdc181.sdc까지69파일을 고정했다. 원래66 QSF 항목만으로 입력이 완결된다고 가정하지 않는다.

**다음은 새 profile identity+정확 SMB3 loader·실제 core/source/ROM 경쟁+paired65816/STOP/base/menu 연결이다.** 현재 진단은ID78/NROM loader이고 실기 사용 금지다. 새 game firmware/bitstream/ZIP는 아직 없다. `probes/nes-game478/mmc03`에 source/보고서를 보존했다. seed/제약 완화 없이 올바른 의존성을 갖춘map03/fit03을 선택했다.

## 479 현재 개발 후보

전용ID79·엄격 CRC5a04eed7/393232B loader를 복원했다. 실제 FatFS/programmer/run136 host20건 PASS(보드 IO/native 모델). ARM479-03 firmware212356B(−284B)/text202313·data10040·BSS18552, 후미636B. 변경 없는73object의 ALLOC영역이476과 같다. whole Lite FIT15260LE(148잔여)/14069comb/8387FF/256608bits, implementation 관련 setup+0.235/hold+0.154ns; raw reset/CDC/IO 미완료.

70ns ROM·seeded loaded/verified core/source에서 부팅 blank 거부 후generation12의15packet/3206B·END/COMMIT·STOP PASS. 같은 실제 packet의 linked476/479 M4 상태·40B tile plan18개가 같다. 수신288231/계획330833명령은 cycles/FPS가 아니다. live ARM·tile ROM·65816 표시·실기 게임은 아직 미통과다. private 선택 source는 `probes/nes-mmc479`와 그 안 execution-location.json을 따른다. 기존476 선택은 그대로 유지한다.

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
