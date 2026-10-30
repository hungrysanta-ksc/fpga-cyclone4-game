# NES 개발 현황

**NES는 진행 중이며 추가 완료 코어가 아니다.** [전체 현황](../../docs/PROJECT-STATUS.ko.md) · [현재 인계](HANDOFF.ko.md) · [새 PC 재개](../../docs/development/RESUME.ko.md)

## 현재 게임 실기 기준

- **MMC502 / ARM502-01(493 함수 동일) / FPGA502 board01 / SMB3(J) / ABI4891·profile7b**:60.07초636회 최종 표시, **평균10.59fps**. 실행·메뉴 복귀 정상이며 사용자가 확실한 프레임 개선을 보고했다.
- 수신22.14ms / 계획·타일31.32ms / SEAL·최종ACK40.27ms. op/quiet는 단계 내부 비용이다. 조회를 제외한 관측wire도18.02ms이므로 A2에서 본문 전송·framing·늦은DMA를 함께 검토한다.
- 이전4939.57fps와 다른 동선이므로 관측+10.61%를 인과적 가속률로 주장하지 않는다. 이번 장면별 시각·영상은 없으며 첫 레벨 전용FPS가 아니다. 문양476의23.84fps는 별도 회귀다.
- [503 실기 분석](../../docs/nes-hardware503-results.ko.md) · [측정 JSON](../../analysis/hardware503-mmc502.json) · [현재 계획](../../docs/nes-audit499-plan.json). 60초 마지막 SEAL guard 제한과 미완료1건 제외를 실제linked502로 확인했다.
- [502 구성](../../docs/nes-capture502-contract.ko.md)·[전달본](../../analysis/capture502-package.json)은 불변 스냅샷이다. 다음 시험판부터는 사용자 백업 정책에 따라 RESTORE 폴더를 넣지 않는다. 기존ZIP/백업·GBC/save와 실행상의 STOP/base/menu 복구는 유지한다.
- 보존history에서 fetch오류0,mask0 거부4/회복4다. 전체 NES/MMC4/5·60fps·capture 무손실·전체 CDC/IO·full stack/IRQ는 미완료다.

## 소스와 기록

- 연결 RTL/firmware: `src/nes`, SNES: `snes/video_probe`, 생성/분석 도구: `tools`.
- 실제 선택 소스와 로컬 입력은 [재현 범위](REPRODUCING.ko.md)에 구분한다. `src/nes`를 임의로 모아 현재 보드 이미지를 만들지 않는다.
- [PR별 진척](../../docs/progress/README.md) · [이전 문서 원문](../../docs/progress/archive/README.md). 과거 Current/NEXT는 당시 기록이다.

재개 시 수신·출력/SEAL의 실제 바이트와 이미 존재하는 capture/export/표시 중첩을 확인한다. MCU_RDY를 source-ready IRQ로 가정하지 않는다. 자세한 예산·보존·완료 조건은 현재 인계에서 관리한다.
