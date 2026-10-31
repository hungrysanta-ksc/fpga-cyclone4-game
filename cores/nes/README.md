# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

- **MMC509 / ARM509-03 / FPGA507 / SMB3(J) / 489 SNES**:60.08초770회 최종 표시, 평균 **12.82fps**. 사용자 확인: 실행·메뉴 복귀 정상, 체감 개선은 크지 않음.
- MMC502는60.07초636회·10.59fps였다. 다른 동선의 전체 평균이므로 관측+21.05%를 순수 수정 효과나 첫 레벨 전용FPS로 간주하지 않는다. 문양 NROM476/23.84fps는 별도 회귀다.
- 수신19.88 / 계획·공급14.30 / 출력·SEAL·최종ACK43.17ms/표시다. 계획 대기의 일부가 출력 단계로 옮겨졌고 op/quiet는 중첩된다. 조회 제외 wire 투영은16.25ms다.
- [510 실기 분석](../../docs/nes-hardware510-results.ko.md) · [측정 JSON](../../analysis/hardware510-mmc509.json) · [509 전달본](../../analysis/service509-package.json). 종료 제한에 걸린771번째 입력은 표시에서 제외했다. 보존history에 fetch/compact/raster/ROM 오류는 없으나 전체 무손실은 입증되지 않았다.
- MMC502·기존 백업·GBC/save를 보존한다. 새 시험판은 RESTORE 폴더를 넣지 않고 실행상의 STOP/base/menu 복구는 유지한다. 지속60fps·MMC4/5·전체 CDC/IO·full stack/IRQ는 미완료다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.

제한 시험판 MMC516은 section 5 소비와 최종 VBlank 대기를 줄였다. 같은 SMB3 첫 레벨에서 사용자 로그와 실제 표시를 확인하는 단계다. [516 결과](../../docs/nes-window516-results.ko.md) · [설치와 로그](../../docs/nes-mmc516-trial.ko.md)
