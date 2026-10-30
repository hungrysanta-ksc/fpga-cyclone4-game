# 프로젝트 현황

목표는 **sd2snes Cyclone IV 멀티 코어 확장**이다. PR139에서수집경계를수정한MMC502의첫실기성공을확인했다. [NES 인계](../cores/nes/HANDOFF.ko.md) · [PR별 경과](progress/README.md).

## 코어별 판정

| 코어 | 판정 | 근거·한계 |
|---|---|---|
| GB/GBC | 추가 성공·제품 공개 | G13C44/sd2snesHST0.9.0,[기준선](../cores/gbc/README.md)·[호환성](COMPATIBILITY.ko.md) |
| NES | 개발 중·제품 미포함 | MMC502실제SMB3 전체평균10.59fps/실행·메뉴정상·체감개선보고;60fps미완료 |
| PC Engine | 조사 대기 | 구현·실기 성공 없음 |

대상은FXPAK Pro/Mk.III,EP4CE15F17C8,STM32F401RCT6,PSRAM IS66WVE4M16EBLL-70BLI 두개다. 다른보드/전체IO승인을뜻하지않는다.

## 최신 게임 실기

**MMC502**:60.07초636최종표시/**10.59fps**. 이전493575회/9.57fps보다관측평균10.61%높고사용자는확실한개선을보고했다. 서로다른동선이므로인과적가속률·레벨전용FPS는미입증이다. [503 분석](nes-hardware503-results.ko.md) · [측정JSON](../analysis/hardware503-mmc502.json). 수신22.14/계획·타일31.32/SEAL·최종ACK40.27ms다. 실제502 linked종료guard와반례16개로미완료637번째를표시수에서제외했다. STOP/base복구·메뉴는정상이다.

보존된수집history에서fetch01/04/06이사라졌다. 남은mask0거부4/회복4는전체원인·빈도·손실시간을확정할자료가아니다. [감사499](nes-audit499.ko.md)의A1 bounded수정과첫실기성공을기준으로[계획A2](nes-audit499-plan.json)의전송량·늦은DMA구조예산으로진행한다. 전체capture무손실승인은아니다.

## 현재 비용과 다음 목표

| 항목 | 현재 값/판정 |
|---|---|
| FPGA502 | 15287LE/14135comb/8399FF/264816bits/51M9K;121LE·5M9K여유 |
| 관련Timing | setup+.353ns/hold+.142ns;전체reset/CDC/IO미승인 |
| ARM502 | 493함수동일/firmware212844B·Flash148B/RUN31848B;fullstack·IRQ미증명 |
| 60Hz평균격차 | 94.45−16.67=77.78ms/표시 |
| SPI투영 | 전체29.99ms/조회제외18.02ms/본문15.84ms;중첩합산금지 |
| 다음작업 | 본문·framing·실제65816 DMA/최종표시일정을공동예산화;status/FSM미세조정은보류 |
| 미완료 | 지속60fps·장면별/p95·NES실시간속도·capture무손실·MMC4/5·제품공개 |

[502 전달본](../analysis/capture502-package.json)과[제작검증](../analysis/capture502-release-verification.json)은불변스냅샷이다. 사용자별도백업에따라 **다음NES시험판부터RESTORE폴더는생략**한다. 기존ZIP/GBC/save는보존하고실행상의STOP/base/menu복구는계속유지한다. 이번수신분석으로새ZIP/합성은만들지않았다.

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
