# NES 개발 현황

2026-10-06 기준: **044 H1 진단의 제한된 실기 성공, 053 ROM 핀 적재 후 실제 코어 실행 시뮬레이션 완료**. NES는 아직 제품에 포함되지 않았으며 일반 게임 실행을 실기에서 검증한 상태가 아니다.

| 구분 | 현재 근거 | 남은 경계 |
| --- | --- | --- |
| 실기 기준 044 | 사용자 확인: LINK SCREEN 1→2→3→1, 자동 종료 없음, GBC 정상 플레이. 로그: protocol44/status03, RESET 복귀 성공 | 재진입·장시간 반복·SD 읽기 해시·전기 타이밍 |
| 실제 코어 통합 047–053 | 진단 2종, 8프레임, 491520픽셀. 최종 핀 적재 ROM으로 실행 | 제한된 BG·팔레트·불변 CHR 진단 범위. 일반 게임·소리·입력 미완료 |
| ROM 부팅 053 | 360505 검사·180226 읽기, 오류 8개 시나리오. 쓰기/읽기 핀 소유권 분리 | MCU SPI 로더, 무결성 확인, 실제 보드 클록 |
| 공동 자원 053 | 13612 LE, 929/963 LAB, 26 M9K, LAB 34개 여유 | 가상/미배치 핀·PLL 미포함. 완성 보드 fit/STA 아님 |
| 제품 | 미포함, 새 SD 이미지 없음 | SNES 런타임 소비자·프레임 마감·복구 및 실제 보드 통합 |

## 작업 진입점

- [현재 인계와 다음 작업](HANDOFF.ko.md)
- [공개 재현 시험과 로컬 의존성](REPRODUCING.ko.md)
- [단계별 진전](MILESTONES.ko.md)
- [실기 044 관측](../../analysis/H1-HARDWARE-044-RESULT.ko.md), [053 결과](../../analysis/ROM-BOOT-RESULT.ko.md), [053 계약](../../docs/nes-rom-boot-contract.md)
- [출처·고정 upstream·보류 파일](../../analysis/source-lock.json), [공개 구현 해시](publication-sources.json)
- [다른 코어에도 적용할 작업 방식](../../docs/development/MILESTONE-WORKFLOW.ko.md)

구현은 `src/nes`, 시험은 `tests/nes-functional`, 자체 SNES 진단 생성기는 `snes/video_probe`, 도구는 `tools/nes_*`·`tools/run_nes_*`에 있다. 기존 GBC 소스를 이동하거나 새 NES 작업에 맞춰 변경하지 않았다.

기존 문서에 반복 누적된 과거 상태는 [이전 README 이력](history/README-053.md)과 [이전 인계 이력](history/HANDOFF-053.ko.md)에 보존한다. 이력 속 ‘현재/다음’ 표현은 당시 기준이며, 현재 판단은 이 문서와 위 인계 문서를 따른다.
