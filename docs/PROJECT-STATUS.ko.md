# 프로젝트 현황

목표는 sd2snes Cyclone IV 멀티 코어 확장이다. NES의 최신 실기는 MMC516이며 MMC509를 비교 기준으로 보존한다. [NES 인계](../cores/nes/HANDOFF.ko.md)

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44/sd2snesHST0.9.0,[기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC516 실제 SMB3 전체 평균 10.99fps, MMC509 12.82fps(다른 동선). 실행·메뉴 복귀 정상 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은FXPAK Pro/Mk.III,EP4CE15F17C8,STM32F401RCT6,PSRAM IS66WVE4M16EBLL-70BLI 두개다. 다른보드/전체IO승인을뜻하지않는다.

## 최신 게임 실기

MMC516은 60.07초·660회 표시, 사용자 확인으로 실행·메뉴 복귀 정상이다. 45~50초는 30회였고, END 추가·flush와 출력 시간이 함께 늘었다. MMC509는 60.08초·770회였다. 서로 다른 플레이이므로 이 수치로 같은 장면의 가속률을 산출하지 않는다. [MMC516 수신](nes-hardware517-results.ko.md) · [MMC509 수신](nes-hardware510-results.ko.md)

## 현재 비용과 다음 목표

| 항목 | 값과 판정 |
|---|---|
| FPGA507 | 15164LE/14172comb/8394FF/264816bits/51M9K, 잔여244LE·5M9K |
| 관련 timing | setup+0.078ns/hold+0.139ns; 전체 reset/CDC/IO 미승인 |
| ARM509 | firmware212956B/Flash36B/BSS18576B; 전체 IRQ stack 미증명 |
| MMC516의 60Hz 평균 격차 | 91.02−16.67=74.35ms/표시 |
| MMC516 단계 평균 | 수신 19.85 / 계획·공급 16.45 / 출력·최종 ACK 54.10ms/표시 |
| 다음 작업 | 같은 SMB3 구간에서 OBJ 공급·END 대기와 출력 지연을 분리한다. [측정](nes-hardware517-results.ko.md) |
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
