# 다른 PC·새 작업에서 재개하기

이 문서는 채팅 기억과 이전 PC의 Downloads 없이 현재 작업을 파악하기 위한 진입점이다. 현재 PC를 계속 사용한다. 마지막 회고499 이후의 진행을 [579 회고](../nes-retrospective579.ko.md)로 재평가했다. 실행 순서는 [579 계획](../nes-retrospective579-plan.json) 하나를 기준으로 삼으며 499/504의 오래된 NEXT를 그대로 재개하지 않는다.

## 1. 상태를 읽는다

1. [루트 README](../../README.md) → [프로젝트 현황](../PROJECT-STATUS.ko.md).
2. [NES 현재 인계](../../cores/nes/HANDOFF.ko.md) → [PR151](../progress/pr-151.md). 회고 기준은 [PR150](../progress/pr-150.md).
3. 수정할 경계의 상세 계약/검증만 연다. 과거 누적 AGENTS/HANDOFF를 처음부터 읽거나 그 안의 NEXT를 현재 지시로 쓰지 않는다.

GB/GBC는 추가·공개 완료, NES는 MMC613 실기16.20fps/5–55초15.66fps다. 실행·메뉴 복귀 정상이며 전체60Hz·capture무손실·외부IO sign-off는 미완료다. [614 실기 기록](../nes-hardware614-results.ko.md)

## 2. Git 기준을 확인한다

```text
git status --short
git remote -v
git branch --show-current
git log -5 --oneline
```

PR150 병합588fa177ed1a82056a5cc86813506c3f2024cc70 확인 뒤 `codex/nes-whole-budget-580`에서 R1을 마감하고 R2를 진행한다. [598 collector·출력 비용](../nes-boundary598-results.ko.md), [597 결합 예산·핀 전송](../nes-region597-results.ko.md), [596 페이지·회로 예산](../nes-pages596-budget.ko.md), [595 D4 FPGA 결과](../nes-region595-results.ko.md), [594 ARM 결과](../nes-report594-results.ko.md)와 [선택 manifest](../../analysis/whole580-manifest.json)를 읽는다. R1 감사 뒤 R2의 실제 ARM transport 제한 시험·전체 링크 비용을 확인했다. 594 ARM과 연결한 595 FPGA는 같은 경계의 Lite MAP 예산을 넘었다. 선택 산출물과 실측은 MMC577을 유지한다.

474 구현 고정 commit은 `06c71479e82a4fa1d76cddb810ea751b71d89880`,475 결과는 `06b4b579fc28c8aa9d750f7e772f6d146efeb2e5`다. 현재 문서 commit이 더 최신이어도 이 선택 산출물의 hash는 바뀌지 않는다. 병합 후 새 구현 작업은 사용자 지시에 따라 새 `codex/` 브랜치/PR에서 시작한다.

## 3. 환경과 자료를 나눈다

| 항목 | 준비/주의 |
|---|---|
| 문서·JSON 검사 | Python3, Git. 특정 사용자 홈 경로 불필요 |
| ARM | GNU Arm13.3.Rel1 계열·make·필수 유틸과 대상 config. 기존 빌더의 절대 경로를 먼저 확인 |
| FPGA | Quartus **Lite**를 기본 사용. 선택576 RTL/bitstream을 유지할 때 변경 없는 전체 합성을 반복하지 않음 |
| Questa | 설치된 Starter FLOAT1좌석으로 순차 실행. 해당 PC의 유효한 권한과 wrapper를 준비하며 원본 signed license는 Git에 저장하지 않음 |
| 에뮬레이터 | 필요한 경계에서만 Mesen/.NET 준비. 모델/CPU 실행과 전체 실기 시간을 구분 |
| 로컬 source/로그 | [NES 재현 범위](../../cores/nes/REPRODUCING.ko.md)의 빠진 입력을 먼저 복구. `probes`/`.tools`/Downloads가 clone에 포함된다고 가정하지 않음 |
| 실기 | 사용자가 ZIP을 SD에 복사하고 TXT를 반환한다. 보드·SD를 PC에 연결하라고 다시 요구하지 않음 |

기존 PC의 경로와 라이선스를 다른 PC에서 그대로 사용할 수 있다는 뜻이 아니다. 라이선스 키/host ID/서버 로그, ROM·개인 save·영상은 별도 관리한다. 현재 선택 MMC577의 clean-clone 전체 재빌드가 완료된 것은 아니며, **현재 판단/다음 순서와 그 이식성 부채를 저장소에 남긴 상태**다.

## 4. 개발 재개 후 순서

1. [579 계획](../nes-retrospective579-plan.json)의 R1은580 전체비용표와 [581 제한 조사](../nes-body581-results.ko.md)로 마감했다. 원본278개는로컬 `probes/nes-body581/evidence01.zip`, 공개 Git에는 해시·비용·순서만 있다. 물리 ROM/capture/입력 지연·대표장면·clean-clone 전체실행 결측을 유지하고 같은 분석/FIT를 반복하지 않는다.
2. [594 ARM 결과](../nes-report594-results.ko.md). 594 전체 ARM이 212,064 B로 링크돼 928 B가 남았다. 같은 ELF에서 cold 905는 17.984 ms(CPI 2), 53입력·27수신 조건·3표시 ACK 조건을 통과했다. 종료 보고 때만 서식을 복원하며 기존 로그와 바이트가 같다. 595에서 이 ARM과 FPGA를 연결했다. 596의 한 페이지 예약 방식은 입력당 26페이지·고정 78거래·546 B를 줄인다. 결합 진단 MAP은 2,708 LE로 892 LE와 새 제어 비용이 남았다. 597은 595 핀 경로에서 묶음 전송으로 905·906 각각 97거래·698 B를 줄였다. 결합 진단은 2,625 LE로 809 LE 초과, 외부 생산 비용을 0으로 둬도 1,909 LE다. 598의 collector 요약은 53입력·1,537그룹에서 일치하고 905/906의 D0를 11/10회 줄였다. 결합 MAP은 4,910 LE로 새 경계 상한보다 907 LE 크다. [599 출력 실측](../nes-output599-results.ko.md)에서 상속 CRC만으로 두 위상의 기준 최종 ACK보다 12.077–15.995 ms 늦었다. [600 실제 SPI·ROM 비용](../nes-wire600-results.ko.md)에서 562/558 B를 줄였지만 필수 조회를 포함한 wire 하한은 16.808/17.030 ms였다. 601에서 현재 PPU 캡처를 재사용해 952·954의 208/272개 요청을 모두 충족했다. 두 위상의 낙관 표시 간격은 31.443–31.900 ms다. [601 검증](../nes-snoop601-results.ko.md) 602의 4 B D2는 두 장면에서 60 B를 절감했다. 한 슬롯의 D1 중첩은 0이고 두 슬롯을 가정해도 표시 전 5.144–5.587 ms가 더 필요하다. [602 검증](../nes-overlap602-results.ko.md) 603의 compact palette는 290 B를 줄이지만 65816 복원·검사가 12.014 ms로 기존 palette ACK보다 8.585–8.708 ms 늦다. [603 검증](../nes-palette603-results.ko.md) 604에서 실제 행 압축·ARM 복원으로 278 B와 첫 BG 1.668 ms를 줄였으나 두 위상의 첫 ROM 허용 시각은 같았다. [604 측정](../nes-rows604-results.ko.md) 605에서 직전 표시 뱅크 이력으로 첫 BG 48 B를 골랐다. 전체 ROM 읽기 단축은 두 위상에서 0.121–0.145 ms였고 954의 60 Hz 마감 전 ROM 공급 상한은 8/272 B였다. [605 근거](../nes-prefix605-results.ko.md) 606에서 954의 현재 캡처가 272/272 B를 보존했다. 이전 ACK 대기에 입력 6블록을 옮겨도 첫 E9는 EA 뒤 16.852 ms다. 입력을 전부 숨긴 조합에서도 필수 드라이버 비용까지 16.162 ms가 걸렸다. [606 검증](../nes-overlap606-results.ko.md) 607의 MMC577 ARM 후보는 최근 두 슬롯을 재사용해 Flash 16 B를 남겼다. 두 위상 53화면에서 밀집 25→24 VBlank, 마지막 ACK −17.799/−50.809 ms였다. 952·954의 SPI 거래는 증가했고 957 최종 대기는 0→1회여서 실기 기준은 MMC577이다. [607 검증](../nes-planner607-results.ko.md) 608에서 팔레트 DMA만 바꾸면 957의 최종 대기가 두 위상 모두 1→0회이고 밀집 구간 24 VBlank를 유지한다. ARM 조회까지 결합하면 24 / 25 VBlank로 위상 2가 회귀한다. 실기 기준은 MMC577을 유지한다. [608 검증](../nes-quiet608-results.ko.md) 609의 두 캡처 뱅크가 OBJ 96 B를 모두 공급해 마지막 OBJ 응답은 약 26 / 15 ms 앞당겨졌다. 선행 DMA가 줄어 952 표시는 두 위상 모두 한 VBlank 늦어졌고 957 최종 대기는 0회를 유지했다. 공유 포트 RTL은 229 LE·38,400 bit로 단독 추가 예산은 81 LE 부족하다. MMC577을 유지한다. [609 검증](../nes-obj609-results.ko.md) 610에서 OBJ bulk 뒤에만 map을 겹치면 두 위상 모두 952는 6→5 VBlank, 밀집 합계는 24→23, 마지막 ACK는 −49.917 / −16.670 ms이며 957 최종 대기는 0회를 유지했다. 실제 source는 1,244→1,073 LE, 산술 여유 319 LE·M9K 0개다. ARM Flash는 212,992 B로 여유가 없다. 기존 BG 적중 48회와 보드 lifecycle은 아직 함께 검증하지 않았으므로 MMC577을 유지한다. [610 검증](../nes-pace610-results.ko.md) 610의 OBJ 조건 ARM과 608 팔레트 단독을 유지한다. 기존 BG 한 줄 이력을 보존하는 실제 보드 캡처·해제·source 경계를 연결하고, 추가 319 LE·M9K 0개 예산과 912·931·939의 기존 적중을 포함한 두 위상 대조를 먼저 통과시킨다. 952·957 표시·최종 ACK·STOP 조건까지 통과한 RTL에 전체 Lite FIT·STA를 한 번 적용한다. 단순 발행 간격·위상 상수 조절은 보류한다.
3. R4는 의미 있는 후보만 실기 전달한다. 5–40/40–55초 완료 집계와 독립 검사·STOP·최종ACK·VBlank·메뉴복귀를 유지하며 시작 실패는 별도 보존한다.
4. 각 단계 완료 때 579 계획의 상태·증거·예산·다음 한 단계를 함께 갱신한다. 오래된 계획의 미완료 상태를 방치하지 않는다.

## 5. 기록을 남긴다

- 현재 판정은 PROJECT-STATUS/코어 인계/registry에서 교체한다. README는 의미 있는 진척·정정 시에만 갱신한다.
- 이번 PR의 목표·작업내용·성과·후속작업은 `docs/progress/pr-NNN.md` 한 파일에 정리한다.
- 근거는 기존 `analysis/`/상세 계약에 연결한다. 루트 README에 PR 요약을 덧붙이지 않는다.
- `.github/PULL_REQUEST_TEMPLATE.md`를 사용하고 게시된 PR도 네 항목인지 확인한다.
- `python tools/check_repository_docs.py`로 진입 문서의 링크·형식·등록부·보존물을 검사한다. 이는 하드웨어 회귀가 아니다.
