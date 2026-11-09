# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

PR155 병합 후 개발 기준은 MMC690이며, 다음 수치는 보존 대조군 MMC666의 기록이다. 실기에서 60.32초에 1,221화면(20.24fps)을 표시하고 메뉴로 복귀했다. 5–40초 19.63fps, 40–55초 19.33fps, 5–55초 19.54fps다. MMC662보다 초반은 소폭 상승하고 후반은 하락했으나 map·OBJ 작업량이 크게 달라 구현만의 개선·회귀를 확정하지 않는다. [실기 비교](../../docs/nes-hardware667-results.ko.md)

실기 비교 기준은 완료 시각 5–40초·40–55초다. 시작 실패 로그는 따로 쌓고 NROM476 문양 시험(23.84fps)은 별도 회귀로 보존한다. [MMC666 설치](../../docs/nes-mmc666-trial.ko.md)

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
