# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

- **MMC489 / ARM489-02 / FPGA489 / SMB3(J) / ABI4891·profile7b**:60.08초577회 최종 표시, **평균9.60fps**. 실행·첫 레벨 플레이·메뉴 복귀 정상,첫 레벨 체감 개선은 작았다는 사용자 보고다.
- 수신30.06ms / 계획·타일 공급34.29ms / SEAL·최종ACK38.65ms. op/quiet는 단계에 중첩된다. 반복 D0/E0/E8 조회가 wire의44.73%이며 실제 소비·검사 일정을 다음으로 다룬다.
- 이전485는 플레이 포함8.22fps/대기13.55fps다. 장면·입력이 달라 인과적 개선율·레벨 전용 FPS를 주장하지 않는다. 문양 NROM476의23.84fps는 별도 회귀다.
- [490 실기 분석](../../docs/nes-hardware490-results.ko.md) · [측정 JSON](../../analysis/hardware490-mmc489.json) · [현재 계획](../../docs/nes-output487-plan.json). 종료 guard2→video14와 마지막 미완료 프레임 제외를 검증했다.
- [489 구현](../../docs/nes-output489-contract.ko.md)·[설치/원복](../../docs/nes-mmc489-trial.ko.md)을 유지한다. 제작 시점 package/model 스냅샷을 덮거나 분석만으로 새 ZIP/합성을 만들지 않는다.
- 60fps·전체 NES/MMC4/5·지속 capture 무손실·전체 CDC/IO·full stack/IRQ 승인은 미완료다.485/482/476/164/467 원복·GBC/save를 보존한다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
