# 저장소 작업 지침

## 먼저 읽을 문서

1. `README.md`: 프로젝트 목표·코어별 현재 상태.
2. `docs/PROJECT-STATUS.ko.md`: 현재 실기 기준과 미완료 항목.
3. `docs/development/RESUME.ko.md`: 새 PC·새 작업의 재개 절차.
4. 해당 코어의 README와 HANDOFF, 관련 `docs/progress/pr-NNN.md`만 추가로 읽는다.

과거 누적 README/AGENTS/HANDOFF는 `docs/progress/archive/`에 보존했다. 그 안의 Current/FIRST/NEXT·예전 승인 상태를 현재 지시로 실행하지 않는다. 실험 번호와 PR 번호를 혼동하지 않는다.

## 현재 작업 범위

- PR136 merge2d4543ef2442bc798bcec128a4a108fdfc4d5287 확인 뒤 PR137/codex/nes-output-budget-487에서 진행한다. 먼저 docs/nes-output489-contract.ko.md + analysis/output489-verification.json + docs/nes-output487-plan.json을 읽는다.487/488 근거와 기각 후보를 보존한다.
- 현재 개발 선택은489 제한 실기 비교본이다. loader inactive payload 선행 저장은 실제 쓰기/오류/STOP/drain 허용과 분리했으며 owned pins/control 동등성+3negative 통과. raw는 plane/row-major 전송과 실제 strided VRAM DMA,2B implicit-pattern cache+6B frame context를 사용한다. 인증은 변경 전 무효화하고 성공 표시 commit에서 확정한 뒤 ACK를 발행한다. 동일12개823.806->757.253ms,71개4234.845->3903.397ms는 실제65816+wire 모델이며 물리 FPS가 아니다.
- Whole Lite1회15272LE/14078comb/8392FF/264800logicalbits/51M9K;136LE·5M9K 여유. 관련 setup+0.183/hold+0.168ns,nominal+0.224/+0.168ns.5KiB ROM이3M9K를 회수한 것은 아니다. ARM Flash124B/새 global0B/RUN31848B/full stack·IRQ 미증명, SNES body4311B/문맥8B. 새 false-path/seed loop 없음, 전체 reset/CDC/IO 미승인 유지.
- MMC489-RAWDMA.zip은 probes/nes-output489/trial02;현재FPGAboard02/ARM02/client04(시험03과동일) 선택, marker NES MMC3 489.nh1/ROM mmc489.nes/로그 *-mmc489.txt. NEXT 사용자 설치 후 동일 대기/플레이의3로그와 화면·메뉴 복귀 분석. 실제 기준485 대기13.55/플레이 포함8.22fps는 아직 대체하지 않는다. C/RTL boot join은 raw0,raw71 CPU시험과 공통 물리 시계로 합치지 않는다. MCU_RDY는 external_memory_ready이지 source-ready IRQ가 아니다.
- 추가·공개 완료는 GB/GBC G13C44/0.9.0뿐이다. NES60fps는 미완료이며 문양476의23.84fps는 별도 회귀다.
- 현재 실기 근거는 `analysis/hardware486-gameplay485.json`, 문양 회귀는 `analysis/receive477-hardware.json`, 인계는 `cores/nes/HANDOFF.ko.md`다.2차 video_error13의 deadline/emit 전파는 슬롯1/128 실제 M4 시험으로 검증했으며 진짜 capacity 실패를 포괄 허용하지 않는다.
- `src/fpga`, `src/firmware-overlay`, `src/renderer`의 검증된 GBC와 사용자 저장·복원물을 보존한다.

## 문서와 PR

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
