# 프로젝트 현황

목표는 sd2snes Cyclone IV 멀티 코어 확장이다. NES 실기 측정 기준은 MMC613이다. 새 MMC639 전달본의 사용자 실행·메뉴 복귀와 두 구간 로그를 기다린다. [MMC639 설치 안내](nes-mmc639-trial.ko.md) [NES 인계](../cores/nes/HANDOFF.ko.md)

시작 실패는 성능 집계에서 제외하고 자연 재발 시 두 실행의 로그 서명을 비교한다.

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44/sd2snesHST0.9.0,[기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC613 SMB3 16.20fps, 5–55초 15.66fps · 실행·메뉴 복귀 성공 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은FXPAK Pro/Mk.III,EP4CE15F17C8,STM32F401RCT6,PSRAM IS66WVE4M16EBLL-70BLI 두개다. 다른보드/전체IO승인을뜻하지않는다.

## 최신 게임 실기

MMC613 실기에서 60.08초에 973화면을 표시했고 실행과 메뉴 복귀를 확인했다. MMC577 대비 5–40초는 13.77→15.97fps, 40–55초는 14.07→14.93fps였다. 두 구간을 합치면 13.86→15.66fps다. [실기 비교](nes-hardware614-results.ko.md)

## 현재 비용과 다음 목표

| 항목 | 값과 판정 |
|---|---|
| MMC613 전체 보드 | 15,332 LE, 조합 논리 14,359, FF 8,474, M9K 56/56. 여유 76 LE |
| 전체 STA 최소 slack | setup +0.487 / hold +0.163 / recovery +1.652 / removal +0.490 ns. 외부 IO 검증 진행 중 |
| MMC639 시험판 | 638 결합·선두 map ROM. 15,351 LE, 57 LE 여유, ARM Flash 212,932 B, 60 B 여유. [검증](nes-trial639-results.ko.md) |
| ARM613 전달본 | Flash 212,992 B, 여유 0 B, BSS 18,592 B |
| 60Hz 평균 격차 | 61.75 − 16.67 ≈ 45.08 ms/표시 |
| MMC613 단계 평균 | 수신 18.82 / 계획·공급 10.65 / 출력·최종 ACK 31.63 ms/표시 |
| 다음 작업 | 같은 작업량에서 출력 발행·DMA·최종 VBlank 대기 분리 |
| 미완료 | 지속60fps·장면별/p95·NES 실시간 속도·capture 무손실·MMC4/5·제품 공개 |

[509 전달본](../analysis/service509-package.json)은 ROM/save/RESTORE 없이 제작한 불변 스냅샷이다. 이번 수신 분석에서 새 firmware·ZIP·합성은 만들지 않았다. [MMC502 실기10.59fps](nes-hardware503-results.ko.md)는 복구·비교 기준으로 보존한다.

## 이전493·489

493은60.07초575회9.57fps/489는60.08초577회9.60fps다.493은정상489 FPGA·표시와ARMquery변경만사용해492부팅실패에서회복했다.492단일원인은미확정이며word경로/495–498후보는502에섞지않았다. [494 분석](nes-hardware494-results.ko.md)·[490 분석](nes-hardware490-results.ko.md). 서로다른장면의최저비용을합쳐새성과로계산하지않는다.

## 이전485 두 조건

**MMC485 / ARM485-03 / 기존 FPGA482 동일 바이트 / 실제 SMB3(J)**. 각60.07초이며 사용자가 두 번 모두 정상 로드·메뉴 복귀를 확인했다.

| 항목 | 1차: 스테이지 진입 없이 대기 | 2차: 첫 레벨 플레이 포함 |
|---|---:|---:|
| 최종 완료 / 평균 FPS | 814 / **13.55** | 494 / **8.22** |
| 전체 평균 ms/표시 | 73.80 | 121.60 |
| 수신 포함 | 17.13 | 31.78 |
| 계획·타일 공급 포함 | 30.19 | 40.31 |
| SEAL·최종 ACK 포함 | 25.89 | 48.33 |

2차는 타이틀·월드맵도 포함하므로 레벨 구간만의 FPS가 아니다. 영상 표본에서1-1·이동·점프·스크롤을 확인했다. 두 실행과 이전482(14.60fps)는 입력/장면이 달라 합산하거나 인과적 개선율로 비교하지 않는다.485의 전체 가속은 미입증이다. op/quiet는 단계에 중첩되므로 합산하지 않는다. 마지막 미완료 입력은 표시 수에 넣지 않는다.

2차 종료의 video_error13은 deadline1→emit guard2→OBJ callback 실패 전파와 일치한다. 실제 M4에서 슬롯1/128 상태로 같은13을 재현했고5개 오분류 반례를 거부했다. 물리 종료 순간을 그대로 재생한 증명은 아니다. [실기 분석486](nes-hardware486-results.ko.md) · [측정 JSON](../analysis/hardware486-gameplay485.json) · [진행 순서](nes-output487-plan.json).

과거 원문은 [archive](progress/archive/README.md), 로컬 재현 의존성은 [재개 안내](development/RESUME.ko.md)에 둔다. README는 의미 있는 변화 때만 갱신하며 PR은 목표·작업내용·성과·후속작업을 유지한다.
