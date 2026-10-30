# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

- MMC485: ARM485-03 / FPGA482 동일 바이트 / 엄격 SMB3(J) ROM, profile7b.
- 각60.07초: 스테이지 진입 없이 대기814최종 표시/**13.55fps**, 첫 레벨 플레이 포함494최종 표시/**8.22fps**. 모두 정상 로드·STOP/base·메뉴 복귀 확인.
- 2차 수신31.78ms / 계획·타일 공급40.31ms / SEAL·최종ACK48.33ms. 단계 안의 op/quiet는 중첩이므로 합산하지 않는다.
- 영상 표본에서1-1/이동/점프/스크롤 확인.8.22fps는 타이틀·월드맵 포함이며 레벨 전용 FPS가 아니다. 두 조건과 이전482의14.60fps를 합산하거나 직접 개선율로 비교하지 않는다.485 전체 가속은 미입증이다.
- [486 실기 분석·다음 순서](../../docs/nes-hardware486-results.ko.md) · [측정 JSON](../../analysis/hardware486-gameplay485.json) · [현재 계획](../../docs/nes-output487-plan.json). 본문 전송량과 전체 SEAL 비용을 먼저 다룬다. 이번486은 수신 분석만이며 새 전달본은 없다.
- [485 기능 계약](../../docs/nes-supply485-contract.ko.md)·[package](../../analysis/supply485-package.json)의 제작 시점 플래그는 유지한다. 현재 실기 근거는486이다.
- 문양 NROM476의23.84fps는 [별도 회귀 기준](../../analysis/receive477-hardware.json)이다.482/476/164/467 원복과 GBC/save를 보존한다.
- 60fps·전체 NES/MMC4/5·지속 capture 무손실·전체 CDC/IO 승인은 미완료다.

[487 출력 감사·개발 후보](../../docs/nes-output487-contract.ko.md)는 별도다. 실제 M4 serializer 명령20.31% 절감과 raw compact 표현을 검증했지만 전체 실기 개선은 미측정이며 새 전달본은 없다. 다음은 compact ABI의 실제 ARM·65816 연결이다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
