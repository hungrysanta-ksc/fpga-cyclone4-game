# 현재 NES 인계

PR136 merge2d4543ef2442bc798bcec128a4a108fdfc4d5287의 master 도달 확인 뒤 `codex/nes-output-budget-487` / [PR137](../../docs/progress/pr-137.md)에서 진행한다. 먼저 [488 연결·보류 판정](../../docs/nes-compact488-contract.ko.md)·[현재 계획](../../docs/nes-output487-plan.json)을 읽는다. 실제 하드웨어 기준은 아래485 그대로다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | MMC485, source commit3188344f37568eef56e514c27a586d82dc45734f |
| ARM | ARM485-03, SHA256 eec710fab1c045ff00ade979dfbfd21dc9c3a19ca391b14b7cca79153a8e0c05 |
| FPGA | FPGA482 동일 바이트, BI3 SHA256 2ddc943069789fa84b78f746f61e4b54f04fe2780819bbef38dfe991c8ed069b |
| ROM/ABI | 원래 SMB3(J), CRC5a04eed7 / profile7b / status3 / input2232 / client2271 /4credit |
| 실기486 수신 | 각60.07초; 대기814회/13.55fps, 첫 레벨 플레이 포함494회/**8.22fps**; 로드·STOP/base·메뉴 복귀 정상 |
| 2차 전체 단계 | 입력31.78ms / 계획·타일 공급40.31ms / SEAL·최종ACK48.33ms, op/quiet 중복 합산 금지 |
| FPGA 비용 | Lite15254LE/14049comb/8392FF/256608bits,154LE 잔여; 관련 setup/hold+0.133/+0.132ns, 전체 CDC/IO 미승인 |
| ARM 비용 | text202717/data10040/BSS18572B, firmware212760B·Flash232B 잔여, RUN31848B·full stack/IRQ 미증명 |

[측정 JSON](../../analysis/hardware486-gameplay485.json)은 2차만 selected runs에 두고1차는 other_runs로 분리한다. 입력/장면이 달라 두 결과나 이전482의14.60fps를 합산·인과적 개선율 비교하지 않는다. 영상은14개 표본에서1-1/이동/점프/스크롤 확인, 카메라29.96fps는 게임 FPS가 아니다. 선택 표본에는 복귀 메뉴가 없으며 정상 복귀는 사용자 보고와 로그 근거다. 로그에 firmware 바이너리 해시는 없으므로 전달본과 label/profile로 연계한다.

## 완료한 작업과 종료 경계

- 484 실제 M4/게임71입력: 명령21.38% 절감,598개 계획/전체 상태 일치. 명령 절감은 전체 시간 개선 증명이 아니다.
- 485 선행 BG E9·비동기 op7 bulk·descriptor12B pending/tombstone·matching ACK drain 연결. 선택 candidate03/ARM03/armguard07/executed/live02/trial02. 실제 M4 12사례·RTL/65816 34ACK/VBlank/57344픽셀·STOP 통과. 모델의 ARM/IRQ는 공통 물리 시계가 아니다.
- 두 실기는60초 deadline1로 끝나며 마지막 미완료 입력을 표시 수에 더하지 않는다. 2차 video_error13은 emit guard2→OBJ callback 실패의 전파와 일치한다. 실제 linked485 M4에서 슬롯1/128로13 재현·5개 오분류 반례 거부; 실물 종료 순간 재생은 아니다.
- 1차 window sent11712/retired11711은 불확실1건이다. software sent/retired 일치만으로 물리 queue 공백을 단정하지 않는다. 독립 검사·실제 ACK·메뉴 복귀를 유지한다.

## 다음 순서와 예산

1. **487 감사 완료.** 기존71입력의 actual M4 serializer와 독립 byte expander가 전체 테이블/두 bank를 대조했다. raw2행인데 CHR2048B 전송이 컸으며 map stale 확장은 유지가 필요했다. [487 근거](../../analysis/output487-verification.json).
2. **bounded-scan 후보 검증 완료.** 상태·계획·전체 packet71개 동일, serializer 명령20.31% 절감·소유권12사례 통과. ARM+12B/Flash220B·새 상태/버퍼0B, FPGA/SNES ABI 그대로다. 전체 시간/FPS는 미측정이며 이 변경만으로 전달하지 않는다.
3. **488 연결 검증 완료·전달 보류.** [488 계약](../../docs/nes-compact488-contract.ko.md)·[검증](../../analysis/compact488-verification.json). raw1/2 compact→canonical WRAM→독립 검사/기존 DMA를 실제로 연결했다. raw2 E1 1797B/frame 절감·serializer 명령53.57% 감소지만12개 최종 표시823.806→823.797ms로 거의 같다. actual C/RTL/65816 boot은 raw0, raw2 별도12개 검사와 공통 시계로 합치지 않는다.
4. 후보 비용은 ARM Flash140B 잔여/새 global0B/SEAL static304B, SNES body4233B/program8KiB/새 persistent0B, whole Lite15287LE/51M9K/121LE·5M9K 여유다. 관련 setup-0.101ns로 실패했다. 최악 check_failed→byte_hold[7]의 loader reset/control 경계를 증명하고 raw 복원+VRAM DMA/ROM 배치를 함께 비교한 뒤 한 번의 selected-source FIT/STA로 재판정한다. false-path/seed 반복은 하지 않는다.
5. 의미 있는 최종 표시 시간 개선과 timing을 모두 통과해야 새 번호/marker/로그/원복 전달본을 만든다. 지금 새 ZIP/실기 요청은 없다. 현재 플레이 포함8.22fps/평균121.60ms,60fps·capture/p95·full stack/IRQ·MMC4/5는 미완료다.

## 소스·보존·재현

- 실제 배포 ARM source는 로컬 `probes/nes-supply485/ARM03/src`, FPGA는 `probes/nes-mmc482/candidate01/board`다. 상세는 [485 계약](../../docs/nes-supply485-contract.ko.md)·[구성 검증](../../analysis/supply485-verification.json)·[package](../../analysis/supply485-package.json)·[재현 범위](REPRODUCING.ko.md)를 따른다. 제작 시점 hardware_verified=false는486 수신 결과로 덮지 않는다.
- 원시6TXT/receipt/종료 M4 시험/영상 표본은 로컬 `probes/nes-hardware486`에 보존했다. 원본 영상·ROM·원시 로그·도구는 Git에 포함하지 않는다. public JSON은 파일명/크기/해시와 재계산 결과를 제공한다.
- 487 후보 source는 `probes/nes-output487/ARM01/src`; `audit03`·`candidate-audit01`·`guards01`과 초기 DWARF 실패를 보존했다. 현재 선택 package를 덮지 않는다. recipe/명령은487 계약을 따른다.
- 분석: `tools/analyze_nes_supply485_hardware.py`, `tools/analyze_nes_hardware486.py`; 종료 전파 검증: `tools/check_nes_hardware486_termination.py`. 개인 의존성은 [재개 안내](../../docs/development/RESUME.ko.md)를 따른다.
- 이전 [482 실기](../../analysis/mmc483-hardware482.json)·[문양476 원복](../../analysis/receive476-package.json)과23.84fps,480 실패·481 기각, 초기485 busy-spin/harness 실패를 보존한다.
- GBC164/save와 G13C44/0.9.0,482/476/474/471/467/164 복원물 보존. 상용 ROM을 새로 포함하지 않는다. 사용자 ZIP 설치/TXT 반환 방식이며 SD/보드 연결을 다시 요구하지 않는다.
- 독립 CRC/coverage·epoch/generation/token·실제 DMA 소비·STOP/stale DONE/ACK 차단·최종ACK 뒤 commit/EA·base/menu 복구를 유지한다. export COMMIT 뒤 다음 capture는 이미 시작하며 이전 표시 중 receiver를 덮지 않는다.
- 전체 NES/MMC4/5·지속 capture 무손실·p95/NES 실시간 속도·full stack/IRQ·전체 reset/CDC/IO·60fps는 미완료다. RTL 변경 시만 Lite whole 비용을 재확인하며 Questa Starter FLOAT1좌석 순차 실행을 유지한다.
