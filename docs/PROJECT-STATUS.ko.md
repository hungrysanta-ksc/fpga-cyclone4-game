# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. PR136에서 개발한다. 실기 기준은482, 현재 전달 후보는485다. 시간 개선 여부는 새 실기 로그를 기다린다. 현재 판단과 다음 순서는 [NES 인계](../cores/nes/HANDOFF.ko.md), PR별 경과는 [progress](progress/README.md)를 따른다.

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC482 실제 SMB3 평균14.60fps; NROM476 약24fps는 별도 회귀.30·60fps 미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은 FXPAK Pro/Mk.III, EP4CE15F17C8, STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 다른 보드/전체 IO 승인을 뜻하지 않는다.

## 최신 게임 실기

**MMC482 / ARM482-01 / FPGA482-01 / 실제 SMB3(J)** 의1회 결과다. 사용자가 실행 성공과 정상 메뉴 복귀를 보고했으며 새 영상은 없다.

| 항목 | 결과 |
|---|---|
| 관측 / 최종 완료 | 60.06초 /877회、평균 **14.60fps** |
| SNES 시작 | 50ms READY, profile7b·원본 CRC/readback 일치 |
| 입력·복귀 | 버튼 변화18건 관측, STOP·base·메뉴 복귀 정상 |
| 수신 포함 | 17.16ms/표시 |
| 계획·타일 공급 포함 | 32.32ms/표시; 거친 계산14.22ms·finish16.03ms |
| SEAL·최종ACK 포함 | 18.44ms/표시 |

단계 안의 op/quiet는 중첩이므로 합산하지 않는다. 마지막 미완료1프레임은877에 포함하지 않았다. 원래480 시작 실패의 물리 원인은 이번 성공만으로 단독 확정하지 않는다. [현재 실기 분석](nes-mmc483-hardware.ko.md) · [재계산 JSON](../analysis/mmc483-hardware482.json) · [다음 순서](nes-mmc483-next-plan.json).

문양 NROM476의60.07초/1432회·평균23.84fps/정상 약24fps는 [별도 회귀 기준](nes-receive477-hardware.ko.md)이다. 게임은 group 재사용8.52%로 문양96.43%와 다르므로 FPS 개선·퇴보율을 직접 비교하지 않는다.

## 현재 비용과 남은 목표

| 항목 | 현재 값/판정 |
|---|---|
| FPGA | 15254LE/14049comb/8392FF/256608bits、154LE 잔여 |
| Timing | 관련 setup+0.133ns/hold+0.132ns; 전체 reset/CDC/IO 미승인 |
| ARM | text202313/data10040/BSS18552B、firmware212356B·Flash636B 잔여 |
| RAM/stack | RUN31848B 유지、full stack/IRQ 증명 미완료 |
| 현재 게임 평균 격차 | 30fps까지35.15ms、60Hz까지51.82ms/표시 |
| 게임/매퍼 범위 | SMB3 한 실행 성공、전 MMC3/MMC4/5·60fps·제품 공개 미완료 |
| 지속성 | capture 누락/반복·frame p95·NES 실시간 속도·정확 VBlank/ROM 위상 미측정 |

[484 계산 절감](nes-game484-planner.ko.md)에 [485 선행 BG/bulk ACK](nes-supply485-contract.ko.md)를 연결했다. M4 소유권·RTL/65816의 VBlank/ACK/픽셀/STOP을 통과했고 새 이름의 [실기 비교본](nes-mmc485-trial.ko.md)을 준비했다. 전체 시간 감소는 미확정이다.485는484 대비 Flash400B·상태20B 추가, Flash232B/FPGA154LE 잔여다. 먼저 실제 ARM/IRQ/SPI/ROM의485 DWT 로그를 비교하고, 그 뒤 입력17ms·SEAL18ms 후속을 정한다. [진행 순서](nes-game484-next-plan.json)를 따른다.

과거 원문은 [archive](progress/archive/README.md), 다른 PC의 입력 의존성은 [재개 안내](development/RESUME.ko.md)에 둔다. README는 의미 있는 변화 때만 갱신하고 PR은 목표·작업내용·성과·후속작업을 유지한다.
