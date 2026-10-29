# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. **성능 개발은 재개했으며 현재 PC를 계속 사용한다.** PC 이전·이식성 작업을 우선하지 않고476/477 실기와 게임 대표 입력·MMC3 예산 관문부터 진행한다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR135](../progress/pr-135.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC만 추가·공개 완료다. NES476은 같은 이동 NROM의1회 실기에서평균23.84fps/정상 구간 약24fps이며,474 2회23.59fps 대비 정상 cadence 개선은 입증되지 않았다. 목표60Hz,30fps 중간 목표와 일반 게임/매퍼 확장은 아직 미완료다.

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

먼저 로컬 변경을 보존한다. 필요할 때 remote를 fetch하고 PR134의 실제 병합 상태·base·merge commit과 master 도달 관계를 확인한다. PR134는93bb8f715914da12d46f1d5c8262d6e8b10d3362로 master에 병합됐으며, 현재 브랜치는 `codex/nes-receive-cost-476`이다. 새 PC에서 무조건 master로 바꾸거나 reset/pull로 덮지 않는다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 현재471 bitstream을 재사용할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 저장소만으로 전체 NES474 재빌드가 가능한 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. 476/477을 기준으로 상태·입력을 고정한다. 설치 source와 연구 후보를 섞지 않는다.
2. 문양은 회귀용으로 유지한다. [실기480 실패/481 보류](../nes-mmc481-startup.ko.md)를 먼저 읽는다. ROM/적재·START/STOP·메뉴 복귀는 정상이나 SNES 표시 시작에서5초 timeout이다.481의 기능 시험은 통과했지만 타이밍 조건 미달로 ZIP 미전달이다. 실제 실패 경로와 최소 진단 경계를 먼저 검토하고, 준비 조건을 통과한 새 전달본의 실기 부팅 뒤 게임 비용/FPS 최적화를 재개한다.
3. Flash352B/산술 RAM4984B 등 전체 예산을 포함해 이득이 있는 후보만 선택한다. 새 계측만 늘리는 전달본을 반복하지 않는다.
4. 독립 검사·STOP·최종 ACK·메뉴 복귀와 동일 ROM 비교를 유지한다. RTL 변경 때만 같은 source의 Lite 전체 비용/관련 timing을 다시 확인한다.
5. 새 전달본은 번호·marker·로그·원복을 함께 갱신한다. 성공 기준476은 보존하고480의 반복 재설치는 요구하지 않는다.481 후보는 아직 전달 금지이며 실제 게임 FPS도 미측정이다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
