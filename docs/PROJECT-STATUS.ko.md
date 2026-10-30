# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. PR138 병합 뒤 PR139에서 A1 수집 정확성을 검토한다. 현재 실기는 MMC493이며 이전489/485와 다른 장면의 결과를 분리해 판정한다. [NES 인계](../cores/nes/HANDOFF.ko.md) · [PR별 경과](progress/README.md).

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44 / sd2snesHST0.9.0, [기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC493 실제SMB3 첫 레벨 플레이 포함9.57fps/부팅·메뉴정상;이전4899.60fps와지속가속미확인,60fps미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은 FXPAK Pro/Mk.III, EP4CE15F17C8, STM32F401RCT6, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 다른 보드/전체 IO 승인을 뜻하지 않는다.

## 최신 게임 실기

**MMC493**:60.07초575최종 표시/**9.57fps**,부팅50ms·실행·첫 레벨·메뉴 복귀 정상. 수신28.97ms/계획·타일33.05ms/SEAL·최종ACK41.33ms다. 이전48960.08초577회/9.60fps와 전체평균이비슷하고첫레벨체감차이도작았다. 장면·입력이달라개선/회귀율이나레벨전용FPS는미입증이다. [494 분석](nes-hardware494-results.ko.md)·[측정JSON](../analysis/hardware494-mmc493.json),이전[490](nes-hardware490-results.ko.md). 마지막SEAL의deadline signature를실제linked493과16개반례로검증했으며미완료입력은표시수에서제외한다.

## 감사499에서 정정한 다음 목표

실기493의 마지막16개 history 전이에는 fetch01/04/06 거부8episode와회복8episode가 있다. 메뉴 정상과capture 건강은 별도다. 전체거부율/손실시간은 이 표본으로 계산하지 않는다. [감사499](nes-audit499.ko.md)·[새 계획](nes-audit499-plan.json)에 따라 수집 경계 재현을 먼저 하고, 반복전송과 늦은VRAM DMA를 구조적으로 줄인다. 기존487/S9보다 이 계획이 우선하며 실기493·9.57fps는 그대로다.

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
| FPGA | 실기493(489 FPGA동일):15272LE/14078comb/8392FF/264800bits/51M9K、136LE·5M9K 잔여 |
| Timing | 관련 setup+0.183ns/hold+0.168ns; 전체 reset/CDC/IO 미승인 |
| ARM493 | text202801/data10040/BSS18572B、firmware212844B·Flash148B 잔여 |
| RAM/stack | RUN31848B 유지、full stack/IRQ 증명 미완료 |
| 493 평균60Hz 격차 | 87.80ms/표시; 異장면489와 인과적 개선율 비교 금지 |
| SPI 투영 | 493 본문wire15.79ms;조회 제외관측wire17.96ms;전체driver wire32.20ms,중첩합산금지 |
| 게임/매퍼 범위 | SMB3 첫 레벨 기능 실기 확인; 전 MMC3/MMC4/5·60fps·제품 공개 미완료 |
| 지속성 | capture 누락/반복·frame p95·NES 실시간 속도·정확 VBlank/ROM 위상 미측정 |

[489 구현](nes-output489-contract.ko.md)은 같은71개 모델7.83% 감소·관련timing 통과 뒤 이전490 수신에서 실행·메뉴 복귀까지 확인했다. 모델 개선율을 실기 FPS에 곱하지 않는다. [기존 설치·원복](nes-mmc489-trial.ko.md) · [개발 검증](../analysis/output489-verification.json) · [제작 manifest](../analysis/output489-package.json) · [현재 순서](nes-output487-plan.json). 489 제작·모델 스냅샷은 유지하고 기존 실기는490,현재493 수신은494에 둔다.

**실기는493을 유지하고 실험495는 전달을 보류한다.** [495 계약](nes-status495-contract.ko.md)·[검증](../analysis/status495-verification.json). EB8B 진행응답/마지막E0 fullACK·ROM요청 중복gate 제거는 기능·관련timing을 통과했다. 후보15121LE/14097comb/8394FF/51M9K·Flash96B이며 LE감소151개는packing 결과,comb는19개 증가했다. 같은12frame0.002794ms 단축/4ms위상0.013316ms 회귀로 전체이득은 미확인이다. 실제ARM polling·IRQ/sourceROM과 실제tile묶음의 공통소비일정이 다음이다. 새ZIP/BI3는없고492단일원인·word경로보류는유지한다. [493 제작검증](../analysis/boot493-verification.json)·[manifest](../analysis/boot493-package.json)는스냅샷으로보존하고현재실기는494를따른다. [PR138](progress/pr-138.md).

[484 계산 절감](nes-game484-planner.ko.md)·[485 소유권 연결](nes-supply485-contract.ko.md)은 기능 검증 근거로 보존한다. [485 package](../analysis/supply485-package.json)의 hardware_verified=false는 제작 시점 스냅샷이다. 485 실기 근거는486,이전489는490,현재493은494이며 ZIP/FPGA를 다시 만들지 않았다. 문양 NROM476의23.84fps와482/476/164/467 원복·GBC/save를 보존한다.

과거 원문은 [archive](progress/archive/README.md), 로컬 의존성은 [재개 안내](development/RESUME.ko.md)에 둔다. README는 의미 있는 변화 때만 갱신하고 PR은 목표·작업내용·성과·후속작업을 유지한다.
