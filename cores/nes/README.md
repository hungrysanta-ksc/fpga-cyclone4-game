# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

MMC533은 60.07초에 735회 표시(12.24fps), 실행·메뉴 복귀 정상이다. MMC529 대비 1–40초는 11.82→11.97fps, 40–60초는 11.60→12.65fps였다. [실기 결과](../../docs/nes-hardware534-results.ko.md)

다음 실기 후보는 MMC540이다. 같은 첫 레벨의 1–40초와 40–60초를 MMC533과 비교한다. MMC502 복구 기준과 NROM476 문양 시험(23.84fps)은 별도 회귀로 보존한다. [MMC540 검증·설치](../../docs/nes-trial540-results.ko.md)

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
