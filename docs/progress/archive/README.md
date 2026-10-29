# 과거 원문 보관

이 폴더는 당시 문서를 데이터로 보존한다. **Current/FIRST/NEXT·현재/다음·승인/보류는 당시 표현이며 새 실행 지시가 아니다.** 현재 기준은 [프로젝트 현황](../../PROJECT-STATUS.ko.md)과 [재개 안내](../../development/RESUME.ko.md)다.

## 2026-10-29 진입 문서 정리

정리 전 commit `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`의 Git blob을 그대로 저장했다. [manifest](2026-10-29/manifest.json)에 원래 경로·byte 수·SHA256이 있다.

| 원래 진입점 | 보존 원문 |
|---|---|
| 루트 README | [root-readme.txt](2026-10-29/root-readme.txt) |
| 루트 AGENTS | [agent-handoff.txt](2026-10-29/agent-handoff.txt) |
| 코어 목록 | [cores-readme.txt](2026-10-29/cores-readme.txt) |
| NES README | [nes-readme.txt](2026-10-29/nes-readme.txt) |
| NES 인계 | [nes-handoff.txt](2026-10-29/nes-handoff.txt) |
| NES 재현 안내 | [nes-reproducing.txt](2026-10-29/nes-reproducing.txt) |
| 전체 코어 등록부 | [core-registry.json](2026-10-29/core-registry.json) |
| 문서 목록 | [docs-readme.txt](2026-10-29/docs-readme.txt) |
| 과거 프로젝트 상태 | [project-status.txt](2026-10-29/project-status.txt) |
| 과거 운영·사례 | [milestone-workflow.txt](2026-10-29/milestone-workflow.txt) |

원문의 상대 링크는 **원래 파일 위치** 기준이다. 이동한 원문을 새 현재 문서로 렌더링/실행하지 않도록 txt로 보존했다. 필요한 상세 문서는 원래 경로나 고정 commit의 Git에서 찾아 읽는다.

## PR 원문 스냅샷

GitHub에서 확인한 [PR29](pull-requests/pr-029.json), [31](pull-requests/pr-031.json), [129](pull-requests/pr-129.json), [130](pull-requests/pr-130.json), [131](pull-requests/pr-131.json), [132](pull-requests/pr-132.json), [133](pull-requests/pr-133.json), [정리 전134](pull-requests/pr-134.json)의 제목·상태·본문을 별도로 보관했다. 네트워크 없이도 최근 방향 전환의 원문을 읽을 수 있다. 이 스냅샷의 상태가 영구적인 remote 상태를 뜻하지 않는다.

기존 `docs/nes-*`, `analysis/*`와 과거 history는 경로·hash를 유지하기 위해 일괄 이동하지 않았다. 새 실험은 현재 인계가 지목하는 범위에서만 시작한다.
