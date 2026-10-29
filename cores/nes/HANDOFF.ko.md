# 현재 NES 인계

사용자 지시로 개발 재개. PR134 merge93bb8f715914da12d46f1d5c8262d6e8b10d3362의 master 도달을 확인했고 `codex/nes-receive-cost-476` / [PR135](../../docs/progress/pr-135.md)에서 진행한다. 현재 PC를 유지한다. 먼저 [프로젝트 현황](../../docs/PROJECT-STATUS.ko.md)·[게임 실기483](../../docs/nes-mmc483-hardware.ko.md)을 읽는다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | MMC482, source commit24cb658d7e6d0e9b5382da9b154026b26d12631f |
| ARM | ARM482-01, SHA256 e201b95928e5891293449b202dacf9e16a9894a49e1513b0877a14ee883c47c8 |
| FPGA | FPGA482-01, BI3 SHA256 2ddc943069789fa84b78f746f61e4b54f04fe2780819bbef38dfe991c8ed069b |
| ROM/ABI | 원래 SMB3(J), CRC5a04eed7 / profile7b / status3 / input2232 / client2271 /4credit |
| 실기 결과483 | 60.06초·877최종 표시, **평균14.60fps**,50ms READY·STOP/base/메뉴 복귀 정상 |
| 전체 단계 | 입력17.16ms / 계획·타일 공급32.32ms / SEAL·최종ACK18.44ms, 중첩 op/quiet 합산 금지 |
| 제약 | Lite15254LE/14049comb/8392FF/256608bits,154LE 잔여; 관련 setup/hold+0.133/+0.132ns, 전체 CDC/IO 미승인 |

[분석483](../../docs/nes-mmc483-hardware.ko.md)·[측정 JSON](../../analysis/mmc483-hardware482.json)·[다음 계획](../../docs/nes-mmc483-next-plan.json)·[구현482](../../analysis/mmc482-verification.json)·[package](../../analysis/mmc482-package.json)를 따른다. 원문3TXT는 `probes/nes-mmc483/hardware482-01`, 설치 ZIP은 `probes/nes-mmc482/trial02/MMC482-BOOTDIAG.zip`이다.483은 수신 분석 번호이며 새 빌드/합성은 없다.

문양 회귀 기준NROM476/실기477의23.84fps와 [원복](../../analysis/receive476-package.json)은 보존한다. 다른 입력/장면의 개선율로 비교하지 않는다. 480 실패·481 기각도 덮지 않았고 이번482 성공만으로480의 물리 원인을 확정하지 않는다.

## 현재 판단과 다음 순서

1. **게임 실기 진입 완료.** 정확 ROM/전체readback·START·입력 관측·877최종ACK/EA·STOP·사용자 메뉴 복귀를 확인했다. legacy screen_frames0/phase_mask0와 SPC A9를 표시 실패로 재분류하지 않는다.
2. **종료 경계 확인.** input COMMIT878 중 마지막 generation899는 deadline으로 미완료다. E1전송12710과 software sent/retired12709의 차이는 post-transfer guard에서 종료된1건이다. 마지막 물리 수신/표시는 미확정이며877에 더하지 않는다.
3. **다음 G1:** 실제 M4 planner의 함수별 비용과 E8 busy/descriptor/credit/finish 공급을 기존 게임 입력·같은482 RTL로 분리한다. 거친 pure planner14.22ms·finish16.03ms 양쪽을 함께 본다. 계측만 늘린 실기 전달을 반복하지 않는다.
4. G2/G3에서 planner 계산·tile 공급·E8/E0 반복·128µs quiet·입력17ms·ROM/IRQ/VBlank의 전체 시간을 비교한다. 지연을 다른 단계로 이동한 후보를 성공으로 세지 않는다. Flash636B/RUN31848B/154LE 여유와 독립 검사·4credit·STOP·최종ACK를 보존한다.
5. 의미 있는 변경이 검증된 뒤 새 번호/로그/원복으로 동일 ROM·입력 조건의 실기를 비교한다. 이번14.60fps는 상호작용1회이며 capture 누락/p95/NES 실시간 속도·MMC4/5·지속60fps는 미완료다.

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
