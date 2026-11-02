# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

MMC551은 비슷한 첫 레벨 동선의 성공 실행에서 60.08초에 822회 표시(13.68fps)했다. 5–40초는 13.09fps, 40–55초는 14.27fps, 합계 5–55초는 13.44fps였다. 별도 실행에서는 첫 표시 전 SNES 준비 대기가 만료됐고 두 실행 모두 메뉴 복귀는 정상이었다. [실기 결과](../../docs/nes-hardware552-results.ko.md)

실기 비교 기준은 완료 시각 5–40초·40–55초다. 시작 실패 로그는 따로 쌓고 NROM476 문양 시험(23.84fps)은 별도 회귀로 보존한다. [MMC551 설치](../../docs/nes-mmc551-trial.ko.md)

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
