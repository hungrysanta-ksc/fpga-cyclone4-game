# 저장소 작업 지침

## 먼저 읽을 문서

1. `README.md`: 프로젝트 목표·코어별 현재 상태.
2. `docs/PROJECT-STATUS.ko.md`: 현재 실기 기준과 미완료 항목.
3. `docs/development/RESUME.ko.md`: 새 PC·새 작업의 재개 절차.
4. 해당 코어의 README와 HANDOFF, 관련 `docs/progress/pr-NNN.md`만 추가로 읽는다.

과거 누적 README/AGENTS/HANDOFF는 `docs/progress/archive/`에 보존했다. 그 안의 Current/FIRST/NEXT·예전 승인 상태를 현재 지시로 실행하지 않는다. 실험 번호와 PR 번호를 혼동하지 않는다.

## 현재 작업 범위

- 현재 개발·실기 기준은 MMC690이며 MMC666 대조군을 보존한다. `analysis/hardware691-mmc690.json`과 `cores/nes/HANDOFF.ko.md`를 먼저 확인한다. PR154는 master `3f8292795b8a5e53d6cf250fcc568223e748a3d6`에 병합됐다.
- PR155 병합 기준은 `c5a25a448e856ce9eddeb86d90965d2ae804a966`, 현재 `codex/nes-output-longrun-692` / PR156. [698 재현](docs/nes-bonus698-results.ko.md)과579 current_followup부터 읽는다. 698: 실제 SMB3(J) RAM0075/0079의 한 번 좌표 변경 후 정상 A 입력으로 스페이드 회전 게임 진입. 선택696 PPU/MMC3/70ns reader의 24경계 중 늦은 CHR bank 전환12조건에서 실기와 ROM·PPU 문맥64bit 전체 일치. 옛 bank 읽기의 선행 수락이 새 주소 마감을 소모하며 tile 경쟁 없이 재현된다. STOP24조건 통과; 실제 CPU 전체·14분 이력 재생이나 생산 수정·새 FIT/실기는 아니다. sprite 주소 확정·mapper preview·옛 CHR 요청 수락을 묶는 최소 수정부터 검토한다. 실제 CPU 쓰기 안정 구간·plan 경쟁을 추가 연결하고 유효/dummy sprite, bank 유지/변경, STOP 전후에 물리 tag·독립 sample 마감을 유지한다. 검사 생략/무조건 읽기 취소/timeout 완화는 채택하지 않는다. 24경계 회귀 후 최종 ACK·메뉴 복귀·두 위상 표시·전체 Lite 비용을 검증한다. 안정성 수정 후692 출력 병목을 재개하며60초/장시간 별도 파일·RESTORE 제외를 유지한다.
- 반복 탐색만 줄이면 map 선행 DMA가 감소할 수 있다. 일괄 map drain은 911의 업로드 VBlank 회귀를 만들었다. 같은 단독 탐색/drain/위상별 고정 지연 변형은 새 근거 전까지 보류한다.
- 670에서669 계획의 거래·복원·소유권·삭제 예산표를 작성했다. `docs/nes-supply670-results.ko.md`와 `analysis/supply670-budget.json`을 읽는다. 실제plan slot으로106개 map 참조복원 일치, descriptor 가정의 밀집 E1절감1417.2B(4.319ms wire)이나 새 target 시간은 미검증이다. D1/E0 삭제0, 순삭제0B/0LE. COMMIT 뒤 collector 재읽기A0는 기각, 별도snapshot은tile RAM을 공짜로 쓸 수 없어 미선택이다.
- 671 B 제한 시험은 실제 비용 실패로 기각했다. `docs/nes-supply671-results.ko.md`·`analysis/supply671-verification.json`을 읽는다. 전체링크 ARM 생산기/509개65816 command/45개소유권 모델 검사 통과지만 source DMA·CRC42.58ms,954/955 행복원·검사88.99/85.17ms로 wire절감3.21/3.24ms를 초과한다. ARM 자원링크212748B/free244,새문맥300B미할당. 새RTL/종단일정/FIT/ZIP 없음. 후속672 수락 범위 비교도 시간 게이트에서 기각됐다. 같은 LUT/CRC 미세조정은 보류한다.
- 현재689는 `docs/nes-status689-results.ko.md`·`analysis/status689-verification.json`을 읽는다. 689D는 688의 ARM·685의 65816 바이너리를 그대로 유지하면서 6 LAB 부족을 해소했다. 전체 Quartus Lite FIT는 15295 LE·963/963 LAB·56/56 M9K로 통과했고, 기존 제약의 최악 setup/hold/recovery/removal은 +0.104/+0.137/+1.460/+0.488ns다. 같은 두 위상106화면 재생은 688과 클록 단위로 일치했다. MMC690 실기2회는691에서 분석했다. `docs/nes-hardware691-results.ko.md`·`analysis/hardware691-mmc690.json`을 먼저 읽는다. 1차stage0 timeout/2차20.71fps·5–55초19.80fps,두실행메뉴복귀성공이며MMC666대조군을보존한다.579 current_followup을 따른다.
- 실기 평균 출력·최종 ACK26.84ms를 고정 재생의 비율로 나누지 않는다. 실제 링크 M4·65816, CPI/IRQ/SPI 모델, 반복 ROM 달력과 실기 로그의 범위를 구분한다.
- 이전 Current/FIRST/NEXT 누적은 [664 시작 전 원문](docs/progress/archive/AGENTS-before664.md)에 바이트 그대로 보존했다. 그 안의 '현재'는 당시 기록이며 새 실행 지시가 아니다.
- 검증된 GBC와 사용자 세이브·백업을 보존한다. 새 실기 전달 전에는 MMC662·MMC666 파일을 덮지 않는다.

## 문서와 PR

- 사용자 백업 정책(502 수신): 다음 NES 시험판부터 RESTORE 폴더/이전 버전 복구본을 새 전달 ZIP에 넣지 않는다. 기존 ZIP·백업은 삭제하지 않고 실행상의 STOP/base/menu 복구는 유지한다.

- PR 본문과 `docs/progress/pr-NNN.md`는 반드시 **목표 → 작업내용 → 성과 → 후속작업** 네 절을 사용한다. `.github/PULL_REQUEST_TEMPLATE.md`와 운영 규칙도 같은 이름이다.
- README는 의미 있는 진척 변화나 정정이 필요할 때만 갱신한다. 작은 작업마다 수정하거나 PR별 요약을 누적하지 않는다. 일상 진행·PR별 결정은 progress 폴더에 기록한다.
- 새 결과는 후보·구성·장면·조건·근거를 함께 연결한다. 실기 FPS, 모델 시간, 명령 수, MAP, FIT/STA를 섞지 않는다.
- 미구현·기각 후보를 현재 제품으로 표시하지 않는다. 다른 구성의 최소 시간/면적을 합친 성공을 만들지 않는다.
- 같은 근거를 여러 곳에 새 원문으로 복사하지 말고 검증 JSON·계약으로 연결한다. 현재 등록부는 짧게 유지한다.
- 사용자가 PR/문서 정리만 요청하면 그 범위만 처리한다. 공개 PR 병합·릴리스·장치 설치는 자동 실행하지 않는다.

## 개발·검증

- 작업 브랜치 접두사는 `codex/`. 사용자 병합 보고 뒤 실제 master 도달 관계를 확인한다. 기존 작업을 reset/rebase로 버리지 않는다.
- 변경 경계에 필요한 최소 검증을 한다. 변경 없는 전체 적재·합성·기존 복원/GBC 시험을 반복하지 않는다.
- NES에서는 독립 CRC/coverage, 4credit와 실제 소비의 구분, STOP·stale DONE/ACK 차단, 최종 표시 ACK 뒤 commit/EA retire, base/menu 복구를 유지한다.
- 현재 회로는 export COMMIT 뒤 다음 capture를 이미 시작한다. 중첩을 새 성과로 계산하거나 이전 표시 중 ARM receiver를 덮지 않는다.
- 남은 수신/CRC와 capture/export/표시 시각을 먼저 분리한다. 근거 없이 범용 실행기·queue 수·작은 FSM을 반복 교체하지 않는다.
- Quartus는 **Lite**를 기본으로 사용한다. Standard 구매/평가 재시도는 자동 진행하지 않는다.
- Questa는 설치된 Starter FLOAT **1좌석으로 순차 실행**한다. 기존 허가된 wrapper를 사용하고 점유 포트/다른 작업 서버를 침범하지 않는다. 새 실제 오류가 없으면 라이선스 smoke를 반복하지 않는다.
- 라이선스 파일·signed FEATURE/INCREMENT·host ID·서버 로그는 Git에 넣지 않는다. 다른 PC에서는 해당 PC의 정당한 도구/권한을 준비한다.

## 파일·보고

- 검색은 `rg`를 우선한다. RTK가 있으면 큰 읽기 요약에 활용하되 ROM/ASM/정확한 diff·hash·실패 원시 로그는 필터링하지 않는다.
- 개인 절대 경로·채팅·Downloads에만 있는 정보에 의존하지 않는다. 로컬 자료 의존성과 실행 범위를 재개 안내에 명시한다.
- allowlist를 지킨다. `git add .`/`git add -f` 대신 검토한 경로만 등록한다. 상용 자산·save/dump·키·도구 캐시는 제외한다.
- 기존 원시 실패와 동결 산출물을 덮지 않는다. 새 전달본은 번호·marker·로그·설치/원복을 함께 갱신한다.
- 실기는 사용자가 설치 ZIP을 SD에 복사하고 로그를 돌려주는 방식이다. 알려진 보드나 SD/USB 연결을 다시 요구하지 않는다.
- 단계 완료·큰 변경·중요한 결과 위주로 간결하게 보고한다. 자세한 진행은 문서에 남기며 이미 허가된 범위의 작업을 반복 확인하지 않는다.

- 단순 NROM은 회귀 fixture이며 게임60fps의 선행 조건이 아니다.480의 공동 기능/픽셀 근거는 실물 SNES 부팅 증명이 아니다. 현재 게임 실기485 및 이전482와 문양476 약24fps 원복을 보존한다.481은 기각이며482 한 회 성공으로480 물리 실패 원인을 단독 확정하지 않는다. 같은480 재시험·계측만 늘리는 전달·근거 없는 FSM/seed/FIT 반복을 피한다.
