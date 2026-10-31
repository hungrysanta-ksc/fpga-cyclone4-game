# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. **성능 개발은 재개했으며 현재 PC를 계속 사용한다.** PC 이전 작업을 우선하지 않고[감사499](../nes-audit499.ko.md)와[새 계획 A1–A4](../nes-audit499-plan.json)를 따른다. 502 수집 수정의 첫 실기 성공을 기준으로 A2 전송·DMA 예산부터 진행하며 기존498 NEXT를 그대로 재개하지 않는다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR140](../progress/pr-140.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC만 추가·공개 완료다. 현재 NES 게임 기준은 MMC502 60.07초636최종표시/10.59fps이며 실행·메뉴 복귀 정상과 체감 개선을 확인했다. 이전4939.57fps와 동선이 달라 인과적 개선율·레벨별FPS는 미확정이다. [503 근거](../nes-hardware503-results.ko.md)를 따른다. 다음 NES 시험판부터 RESTORE 폴더는 생략하며 사용자 백업과 기존 ZIP은 보존한다.60fps·전게임/매퍼·capture/전체CDC/IO 승인은 미완료다.

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

먼저 로컬 변경을 보존한다. PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`와head의master도달·tree일치를확인했다. 현재 `codex/nes-bandwidth-dma-budget-504`/PR140이며 [507 계약](../nes-fault507-contract.ko.md)을 읽는다. 506 입력 압축을 유지하면서 SPI 오류 전달을 같은 클록의 비트 식으로 바꾸어 관련 setup +0.078ns/hold +0.139ns를 확보했다. 다음은 END 뒤 일반 출력의 제한된 선행 공급과 bulk 완료 watermark다. 실기 기준은 MMC502이며 전체 reset/CDC/IO·실제 arbiter trace·새 실기 시험은 미완료다. 505의 첫 frame 이득을 지속 warm 개선으로 재해석하지 않는다. 새PC에서무조건master로바꾸거나reset/pull로덮지않는다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 현재489 RTL/bitstream을 유지할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 저장소만으로 전체 NES474 재빌드가 가능한 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. [507 계약](../nes-fault507-contract.ko.md)의 완료 소유권과 예산을 따른다. `complete485`의 마지막 opcode 검사를 단순 삭제하지 않는다.
2. 검증된 retired counter로 bulk watermark를 확인하고, 준비된 bulk·credit을 일반 packet보다 우선한다. runtime 추가 최대 8B, Flash 순증 최대 140B 안에서 기존 blocking 제어를 교체한다.
3. 독립 검사·STOP·세대/sequence wrap·미래 완료 거부·최종 ACK·EA·VBlank를 검증한다. 실제 arbiter trace와 긴 연속 일정으로 추가 이득을 확인한다.
4. 변경된 소스와 일치한 Quartus Lite 전체 비용/관련 timing을 확인한다. 전체 reset·CDC·IO 미승인과 조건부 모델 시간을 구분한다.
5. 실기 전달 후보를 선정하면 고유 번호·marker·로그 파일명을 사용한다. RESTORE 폴더는 포함하지 않는다. 사용자가 설치해 실행·플레이·메뉴 복귀를 확인하는 절차를 유지한다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
