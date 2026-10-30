# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. PR137 병합 뒤 PR138에서 개발한다. 현재 실기는 MMC489이며, 이전485와 다른 장면의 결과를 분리해 판정한다. [NES 인계](../cores/nes/HANDOFF.ko.md) · [PR별 경과](progress/README.md).

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC489 실제 SMB3 첫 레벨 플레이 포함9.60fps,이전485 플레이8.22fps/대기13.55fps, STOP·메뉴 복귀 정상;60fps 미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은 FXPAK Pro/Mk.III, EP4CE15F17C8, STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 다른 보드/전체 IO 승인을 뜻하지 않는다.

## 최신 게임 실기

**MMC489**:60.08초577최종 표시/**9.60fps**,실행·첫 레벨 플레이·메뉴 복귀 정상. 수신30.06ms/계획·타일34.29ms/SEAL·최종ACK38.65ms다. 첫 레벨 체감 개선은 작았으며 정확한 장면별 FPS/동일 입력 가속은 미입증이다. 반복 조회는 wire44.73%이고 다음은 E8/E0 실제 소비·검사 일정을 함께 다룬다. [490 분석](nes-hardware490-results.ko.md) · [측정 JSON](../analysis/hardware490-mmc489.json).

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

## 현재 비용과 남은 목표

| 항목 | 현재 값/판정 |
|---|---|
| FPGA | 실기 선택489:15272LE/14078comb/8392FF/264800bits/51M9K、136LE·5M9K 잔여 |
| Timing | 관련 setup+0.183ns/hold+0.168ns; 전체 reset/CDC/IO 미승인 |
| ARM489 | text202825/data10040/BSS18572B、firmware212868B·Flash124B 잔여 |
| RAM/stack | RUN31848B 유지、full stack/IRQ 증명 미완료 |
| 489 평균60Hz 격차 | 87.46ms/표시; 異장면482와 직접 개선율 비교 금지 |
| SPI 본문 투영 | 489 본문5099.14B/표시→15.54ms,framing/query 별도;전체driver wire32.03ms |
| 게임/매퍼 범위 | SMB3 첫 레벨 기능 실기 확인; 전 MMC3/MMC4/5·60fps·제품 공개 미완료 |
| 지속성 | capture 누락/반복·frame p95·NES 실시간 속도·정확 VBlank/ROM 위상 미측정 |

[489 구현](nes-output489-contract.ko.md)은 같은71개 모델7.83% 감소·관련timing 통과 뒤 이번 실기에서 실행·메뉴 복귀까지 확인했다. 모델 개선율을 실기 FPS에 곱하지 않는다. [기존 설치·원복](nes-mmc489-trial.ko.md) · [개발 검증](../analysis/output489-verification.json) · [제작 manifest](../analysis/output489-package.json) · [현재 순서](nes-output487-plan.json). 제작 스냅샷은 유지하며 새로운 실기 근거는490에 둔다. 이번에는 새 합성/전달본이 없다.

[491 개발 후보](nes-consume491-contract.ko.md)의 word 복원·plan 조회 통합을 [MMC492 전체 일정 비교본](nes-mmc492-trial.ko.md)으로 준비했다. 실제 ARM/IRQ·SPI·ROM 경쟁·65816 최종ACK의 전체 시간을 기존 DWT/elapsed로 판정한다.781 linked함수가491과 같고 whole15272LE/51M9K·관련timing·programmer 전송을 확인했다. **492 실측 FPS·단축·메뉴 복귀는 아직 미확인,위489 실측은 유지한다.** [연결 검증](../analysis/schedule492-verification.json)·[492 manifest](../analysis/schedule492-package.json)·[PR138](progress/pr-138.md).

[484 계산 절감](nes-game484-planner.ko.md)·[485 소유권 연결](nes-supply485-contract.ko.md)은 기능 검증 근거로 보존한다. [485 package](../analysis/supply485-package.json)의 hardware_verified=false는 제작 시점 스냅샷이다. 485 실기 근거는486,현재489 수신 근거는490이며 ZIP/FPGA를 다시 만들지 않았다. 문양 NROM476의23.84fps와482/476/164/467 원복·GBC/save를 보존한다.

과거 원문은 [archive](progress/archive/README.md), 로컬 의존성은 [재개 안내](development/RESUME.ko.md)에 둔다. README는 의미 있는 변화 때만 갱신하고 PR은 목표·작업내용·성과·후속작업을 유지한다.
