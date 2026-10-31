# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

MMC516은 60.07초 동안 660회 표시(10.99fps), 실기 실행·메뉴 복귀가 확인됐다. MMC509는 다른 동선에서 60.08초 770회(12.82fps)였다. 516의 45~50초에 OBJ 타일 작업이 표시당 30.07건으로 늘고 표시율은 약 6fps였다. 다음 비교에서는 동일 장면의 OBJ 공급과 표시 간격을 분리한다. [517 실기 결과](../../docs/nes-hardware517-results.ko.md) · [509 실기 기준](../../docs/nes-hardware510-results.ko.md)

실기 비교는 MMC509, 복구 기준은 MMC502를 보존한다. NROM476의 문양 시험(23.84fps)은 별도 회귀다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
