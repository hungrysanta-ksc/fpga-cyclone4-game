# 현재 NES 인계

PR137 merge29815faa3887a035091e3169ffa0f751dda3de44의 master 도달 확인 뒤 `codex/nes-consume-schedule-491` / [PR138](../../docs/progress/pr-138.md)에서 진행한다. 개발은 [491 경계](../../docs/nes-consume491-contract.ko.md)·[검증](../../analysis/consume491-verification.json)을 먼저 읽는다. 먼저 [489 연결·실기 비교 준비](../../docs/nes-output489-contract.ko.md)·[현재 계획](../../docs/nes-output487-plan.json)을 읽는다. 현재 실기 판정은 [수신490](../../docs/nes-hardware490-results.ko.md)·[측정](../../analysis/hardware490-mmc489.json)을 먼저 읽는다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | MMC489,source commitdc61756153cbaa78159be15860084260530dd3ed |
| ARM | ARM489-02,SHA256 dbeb479a7f8a2ec3906a3f76effc9069796c3b6144bde5345f59396642de9b65 |
| FPGA | FPGA489 board02,BI3 SHA256 257b9686fa68ab11712b443728dc24c6ea7b561674a7ad2905ecb36f63349119 |
| ROM/ABI | 원래 SMB3(J),CRC5a04eed7/profile7b/status3/client4891/4credit |
| 실기490 수신 | 60.08초577최종 표시/**9.60fps**,실행·첫 레벨·메뉴 복귀 정상,레벨 체감 차이 작음 |
| 전체 단계 | 수신30.06ms/계획·타일34.29ms/SEAL·최종ACK38.65ms,op/quiet 중복 합산 금지 |
| FPGA 비용 | Lite15272LE/14078comb/8392FF/264800bits/51M9K,136LE·5M9K 잔여;관련 setup/hold+0.183/+0.168ns |
| ARM 비용 | text202825/data10040/BSS18572B,firmware212868B·Flash124B,RUN31848B/full stack·IRQ 미증명 |

이전485는 각60.07초 대기814회/13.55fps와 플레이 포함494회/8.22fps다.489와 장면·입력이 달라 합산·인과적 개선율 비교를 하지 않는다. 정확한 레벨 전용 FPS/p95/capture 무손실/NES 실시간 속도는 미측정이다. 로그에 binary hash가 없어 전달본 label/profile과 연계한다. 독립 검사·STOP·최종ACK·VBlank·메뉴 복귀를 유지하며 GBC/save/485 원복을 보존한다.

## 완료한 작업과 종료 경계

- 484 실제 M4/게임71입력: 명령21.38% 절감,598개 계획/전체 상태 일치. 명령 절감은 전체 시간 개선 증명이 아니다.
- 485 선행 BG E9·비동기 op7 bulk·descriptor12B pending/tombstone·matching ACK drain 연결. 선택 candidate03/ARM03/armguard07/executed/live02/trial02. 실제 M4 12사례·RTL/65816 34ACK/VBlank/57344픽셀·STOP 통과. 모델의 ARM/IRQ는 공통 물리 시계가 아니다.
- 두 실기는60초 deadline1로 끝나며 마지막 미완료 입력을 표시 수에 더하지 않는다. 2차 video_error13은 emit guard2→OBJ callback 실패의 전파와 일치한다. 실제 linked485 M4에서 슬롯1/128로13 재현·5개 오분류 반례 거부; 실물 종료 순간 재생은 아니다.
- 1차 window sent11712/retired11711은 불확실1건이다. software sent/retired 일치만으로 물리 queue 공백을 단정하지 않는다. 독립 검사·실제 ACK·메뉴 복귀를 유지한다.

## 완료한 개발과 다음 순서

1. **487 감사 완료.** 기존71입력의 actual M4 serializer와 독립 byte expander가 전체 테이블/두 bank를 대조했다. raw2행인데 CHR2048B 전송이 컸으며 map stale 확장은 유지가 필요했다. [487 근거](../../analysis/output487-verification.json).
2. **bounded-scan 후보 검증 완료.** 상태·계획·전체 packet71개 동일, serializer 명령20.31% 절감·소유권12사례 통과. ARM+12B/Flash220B·새 상태/버퍼0B, FPGA/SNES ABI 그대로다. 전체 시간/FPS는 미측정이며 이 변경만으로 전달하지 않는다.
3. **488 기각 원인 해결·489 제한 시험 준비.** [489 계약](../../docs/nes-output489-contract.ko.md)·[검증](../../analysis/output489-verification.json)·[설치/원복](../../docs/nes-mmc489-trial.ko.md). loader의 무허용 payload 저장과 실제 쓰기 제어를 분리했다. raw는 중간 복사를 없애고 실제 VRAM DMA 순서로 생산·소비하며2B 암묵패턴 cache를 수정 전 무효화한다. 표시 완료 후 ACK를 발행하는 구간에서 확정한다.
4. 동일12개823.806→757.253ms,71개4234.845→3903.397ms,reset부터도5.78% 개선은 실제65816+wire 모델이다. whole Lite15272LE/51M9K/136LE·5M9K 여유,관련 setup+0.183/hold+0.168ns 통과. ARM Flash124B/새 global0B/SEAL static304B,RUN31848B;SNES program5KiB/body4311B·문맥8B. 논리 RAM 감소를 M9K3개 회수로 계산하지 않는다. full stack/IRQ/reset/CDC/IO는 미완료다.
5. 새 MMC489-RAWDMA.zip은 로컬 probes/nes-output489/trial02. marker/ROM/로그를489로 바꾸고485/482/476/164/467 원복을 보존했다. 수신490에서 실행·메뉴 복귀/9.60fps를 확인했다. E1 wire2233.34B/표시,조회D0/E0/E8는전체wire44.73%다. 다음은 E8 공급/E0 소비credit·ACK와65816 수신/CRC/manifest/VBlank 일정을 함께 추적·교체하고 그다음D0 source/ROM 대기를 다룬다. Flash124B/136LE 예산과 전체 최종 표시 시간으로 판단하며 분석만을 위한 새 ZIP/합성은 없다.

## 491 개발 후보·다음 관문

[검증](../../analysis/consume491-verification.json):71 CPU/전송 모델7.25% 개선,108word/bank/STOP·M4 12ownership/8burst·71 canonical 상태/계획·공동 C/RTL/65816 첫 화면/34ACK/STOP·5124bus 통과. Source closure는 ROM 내용만 달라졌다. Whole Lite15272LE/51M9K/관련+0.183/+0.168ns 동일,ARM Flash148B/새 global0B·emit stack16B,SNES body4425B/새 RAM0B다.

새 설치본은 없다. 실제 M4/IRQ/source ROM과 공통 시계의 전체 이득이 남아 있어489 설치본/9.60fps를 유지한다. 다음은 E8/E0 trace·source/ROM grant·65816 소비 시각을 한 일정에 연결하고 D0 대기를 비교한다. endpoint query 감소율을 CPU7.25%와 합치지 않는다. 로컬선택 `probes/nes-consume491` candidate01/ARM01/client02/audit01/arm-bursts01,ASCII board01/snes05/units04/phase01/cold01/live01/bootbus01. 재현 의존성과 native DLL 보존은491 계약을 따른다.

## 소스·보존·재현

- 이전485 배포 ARM source는 로컬 `probes/nes-supply485/ARM03/src`, FPGA는 `probes/nes-mmc482/candidate01/board`다. 상세는 [485 계약](../../docs/nes-supply485-contract.ko.md)·[구성 검증](../../analysis/supply485-verification.json)·[package](../../analysis/supply485-package.json)·[재현 범위](REPRODUCING.ko.md)를 따른다. 제작 시점 hardware_verified=false는486 수신 결과로 덮지 않는다.
- 원시6TXT/receipt/종료 M4 시험/영상 표본은 로컬 `probes/nes-hardware486`에 보존했다. 원본 영상·ROM·원시 로그·도구는 Git에 포함하지 않는다. public JSON은 파일명/크기/해시와 재계산 결과를 제공한다.
- 489 로컬 선택은 probes/nes-output489의 candidate03/ARM02/audit01/client04/assembly01/trial02 및 ASCII board02/loader01/live01/bootbus01이다. 공개 recipe/test/분석으로 경계를 재현하되 원본487 ARM/482 board와 입력·도구 의존성은 아직 별도다.
- 487 후보 source는 `probes/nes-output487/ARM01/src`; `audit03`·`candidate-audit01`·`guards01`과 초기 DWARF 실패를 보존했다. 현재 선택 package를 덮지 않는다. recipe/명령은487 계약을 따른다.
- 현재490 raw는 로컬 `probes/nes-hardware490/run01`/receipt,종료linked시험termination03·12negative 보존. 분석 `tools/analyze_nes_hardware490.py`,종료 `tools/check_nes_hardware490_termination.py`.
- 이전 분석: `tools/analyze_nes_supply485_hardware.py`, `tools/analyze_nes_hardware486.py`; 종료 전파 검증: `tools/check_nes_hardware486_termination.py`. 개인 의존성은 [재개 안내](../../docs/development/RESUME.ko.md)를 따른다.
- 이전 [482 실기](../../analysis/mmc483-hardware482.json)·[문양476 원복](../../analysis/receive476-package.json)과23.84fps,480 실패·481 기각, 초기485 busy-spin/harness 실패를 보존한다.
- GBC164/save와 G13C44/0.9.0,482/476/474/471/467/164 복원물 보존. 상용 ROM을 새로 포함하지 않는다. 사용자 ZIP 설치/TXT 반환 방식이며 SD/보드 연결을 다시 요구하지 않는다.
- 독립 CRC/coverage·epoch/generation/token·실제 DMA 소비·STOP/stale DONE/ACK 차단·최종ACK 뒤 commit/EA·base/menu 복구를 유지한다. export COMMIT 뒤 다음 capture는 이미 시작하며 이전 표시 중 receiver를 덮지 않는다.
- 전체 NES/MMC4/5·지속 capture 무손실·p95/NES 실시간 속도·full stack/IRQ·전체 reset/CDC/IO·60fps는 미완료다. RTL 변경 시만 Lite whole 비용을 재확인하며 Questa Starter FLOAT1좌석 순차 실행을 유지한다.
