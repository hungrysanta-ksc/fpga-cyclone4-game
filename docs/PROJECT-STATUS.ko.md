# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. PR136 병합 뒤 PR137에서 개발한다. 현재 실기는 MMC485이며, 두 다른 장면의 결과를 분리해 판정한다. [NES 인계](../cores/nes/HANDOFF.ko.md) · [PR별 경과](progress/README.md).

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC485 실제 SMB3 첫 레벨 플레이 포함8.22fps/대기13.55fps, STOP·메뉴 복귀 정상;60fps 미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은 FXPAK Pro/Mk.III, EP4CE15F17C8, STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 다른 보드/전체 IO 승인을 뜻하지 않는다.

## 최신 게임 실기

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

## 현재 비용과 남은 목표

| 항목 | 현재 값/판정 |
|---|---|
| FPGA | 실기 선택482:15254LE/14049comb/8392FF/256608bits、154LE 잔여;488 후보는 아래 별도 |
| Timing | 관련 setup+0.133ns/hold+0.132ns; 전체 reset/CDC/IO 미승인 |
| ARM485 | text202717/data10040/BSS18572B、firmware212760B·Flash232B 잔여 |
| RAM/stack | RUN31848B 유지、full stack/IRQ 증명 미완료 |
| 2차 평균60Hz 격차 | 104.93ms/표시; 異장면482와 직접 개선율 비교 금지 |
| SPI 본문 투영 | 6728.50B/표시→2.625Mbps에서20.51ms, framing/query 별도 |
| 게임/매퍼 범위 | SMB3 첫 레벨 기능 실기 확인; 전 MMC3/MMC4/5·60fps·제품 공개 미완료 |
| 지속성 | capture 누락/반복·frame p95·NES 실시간 속도·정확 VBlank/ROM 위상 미측정 |

[487 출력 감사](nes-output487-contract.ko.md)와 packet 동일 scan 다음으로 [488 compact 실제 연결](nes-compact488-contract.ko.md)을 검증했다. raw2 프레임당 ordinary/SEAL E1 1797B를 줄였고 실제 ARM/65816 검사·DMA·STOP를 통과했지만, 같은12개 최종 표시823.806→823.797ms로 거의 같았다. 후보 whole Lite15287LE/51M9K는 들어가나 관련 setup-0.101ns로 실패했다. ARM Flash140B 잔여·새 global0B, SNES body4233B/program8KiB·새 persistent0B다. **후보를 실기 선택으로 올리지 않았고 새 ZIP은 없다.**

다음은 loader check_failed→byte_hold 제어 경계와 raw 복원+VRAM DMA/ROM 배치를 함께 비교한다. 선택 구조의 성능을 먼저 확인한 뒤 한 번의 whole FIT/관련 timing을 통과해야 전달한다. [현재 순서](nes-output487-plan.json) · [488 검증](../analysis/compact488-verification.json). 실제485의 시간/FPS와 위 표는 그대로이며 MCU_RDY는 source-ready IRQ가 아니다.

[484 계산 절감](nes-game484-planner.ko.md)·[485 소유권 연결](nes-supply485-contract.ko.md)은 기능 검증 근거로 보존한다. [485 package](../analysis/supply485-package.json)의 hardware_verified=false는 제작 시점 스냅샷이다. 현재 실기 근거는486이며 ZIP/FPGA를 다시 만들지 않았다. 문양 NROM476의23.84fps와482/476/164/467 원복·GBC/save를 보존한다.

과거 원문은 [archive](progress/archive/README.md), 로컬 의존성은 [재개 안내](development/RESUME.ko.md)에 둔다. README는 의미 있는 변화 때만 갱신하고 PR은 목표·작업내용·성과·후속작업을 유지한다.
