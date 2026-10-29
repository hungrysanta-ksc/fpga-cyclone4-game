# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** 현재 PC에서474/475 기준 성능 개발을 재개했다. [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

- MMC482: ARM482-01 / FPGA482-01 / 엄격 SMB3(J) ROM, profile7b.
- 1회60.06초·최종 표시877회, **평균14.60fps**. 시작50ms READY, 입력 변화 관측·STOP/base·메뉴 복귀 정상이다.
- 전체 수신17.16ms / 계획·타일 공급32.32ms / SEAL·최종ACK18.44ms가 관측됐다. 단계 안의 op/quiet는 중첩이므로 합산하지 않는다.
- 이번483은 결과 분석 번호이며 새 펌웨어·합성·전달본은 만들지 않았다. [실기 분석](../../docs/nes-mmc483-hardware.ko.md) · [근거](../../analysis/mmc483-hardware482.json) · [다음 계획](../../docs/nes-mmc483-next-plan.json).
- 문양 NROM476의23.84fps/정상 약24fps는 별도 회귀 기준으로 보존한다. 장면이 다르므로 게임 FPS의 개선·퇴보율로 계산하지 않는다. [NROM 근거](../../analysis/receive477-hardware.json).
- 60fps·전체 NES/MMC4/5·지속 capture 무손실·전체 CDC/IO 승인은 미완료다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES 관련 소스: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`의 파일을 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md): 최근129–135와 전체 병합 색인.
- [이전 문서 원문](../../docs/progress/archive/README.md): 과거 Current/NEXT는 당시 기록이다.

재개 시에는 수신·CRC 비용과 이미 존재하는 capture/export/표시 중첩 일정을 먼저 확인한다. 자세한 예산·보존 조건·완료 조건은 현재 인계에서 관리한다.

현재 선택은 실기 성공482다.480 실패·481 기각은 보존했으며 이 한 번의 성공으로480의 물리 실패 원인을 단독 확정하지 않는다. 다음은 실제 M4 planner와 E8의 공급/대기를 분리하고 같은482 RTL에서 전체 시간을 줄이는 후보를 검토한다.
