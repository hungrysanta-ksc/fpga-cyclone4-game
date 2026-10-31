# 저장소 작업 지침

## 먼저 읽을 문서

1. `README.md`: 프로젝트 목표·코어별 현재 상태.
2. `docs/PROJECT-STATUS.ko.md`: 현재 실기 기준과 미완료 항목.
3. `docs/development/RESUME.ko.md`: 새 PC·새 작업의 재개 절차.
4. 해당 코어의 README와 HANDOFF, 관련 `docs/progress/pr-NNN.md`만 추가로 읽는다.

과거 누적 README/AGENTS/HANDOFF는 `docs/progress/archive/`에 보존했다. 그 안의 Current/FIRST/NEXT·예전 승인 상태를 현재 지시로 실행하지 않는다. 실험 번호와 PR 번호를 혼동하지 않는다.

## 현재 작업 범위

- 현재509: FIRST docs/nes-service509-contract.ko.md + analysis/service509-verification.json + analysis/service509-package.json. PR140동일branch/실기MMC50210.59fps유지. E8공유34+40guards/12RGB PASS;508시간이득유지/FW212956 Flash36 BSS18576(+4vs502),stack24B회복. 실제bootCPU·PPU·MMC3 20frame 무선행/포화2386reads·선택4화면동일/STOPguardPASS. 8window재생은첫레벨폐루프아님.507 Lite15164LE51M9K setup+.078 hold+.139재사용/새FIT없음. MMC509 trial01 ZIP/ARM03은ARM01의784함수동일,label만509;ROM/save/RESTORE없음. NEXT 사용자실기3로그/같은동선502비교→수신·계획·SEAL/capture분석→A2본문예산. E8/phase/seed미세조정동결;fullCDCIO/IRQstack/60fps미완료.
- PR139 merge46c0cc962397b3e757c838164b70b75fe73090a6 및head afbd887의origin/master도달·tree일치를확인했다. 현재새브랜치 codex/nes-bandwidth-dma-budget-504 / PR140. 504 이력은 docs/nes-budget504-contract.ko.md + docs/nes-budget504-plan.json + analysis/budget504-verification.json. 실기502/503는유지. A2전체60Hz gate는미통과;수집정확성수정을되돌리거나기존498을자동승격하지않는다.
- 504 보존 기록(현재 경계·NEXT는506으로 대체): unchanged65816 PC계측으로cold502/과거12연속fixture의pixel·최종ACK시각동일. 연속평균SEAL→upload2.24ms/upload→ACK23.65ms,실기warm시간아님. 조회제외5911.51B/표시,12ms예산까지1974.01B부족. 공통generation Python332record17→15packet/604payloadB·642wireB차이/5반례;RTL·ARM미구현. 전체7533B이력cache최소7M9K>잔여5기각. NEXT packet완료뒤불변dirty-prefix만비차단inactiveVRAM DMA;mutable tail·부분VBlank·STOP이력무효화·최종검사/ACK유지. 목표추가SNES≤512B/WRAM≤8B/newM9K·ARM·FPGA제어0,실측아님. cold01/sequence01 raw근거probes/nes-budget504/evidence. 새FW/FIT/Questa/ZIP없음;RESTORE미포함정책유지.
- 현재 실기502/분석503: docs/nes-hardware503-results.ko.md + analysis/hardware503-mmc502.json FIRST.60.07초636최종표시10.59fps/94.45ms;실행·메뉴정상·사용자체감개선.4939.57 대비관측+10.61%,동일장면인과율아님.수신22.14/계획31.32/SEAL40.27ms;중첩op/quiet합산금지.보존history8전이fetch오류0,mask0거부4/회복4;전체capture건강·거부율미증명.실제502linked guard deadline1/window2/sink2·4조건/16반례,마지막637번째미완료제외.새FW/ZIP/FIT/Questa없음.비용50215287LE/121LE여유/Flash148B유지. NEXT A2본문·framing·늦은DMA예산;조회제외wire18.02ms,단순polling/FSM재개금지. 이전제작snapshot는불변.
- 현재500 A1 원인 분리: 실제493 PPU/collector9파일과179 PPUMASK/2006 기록으로24조건,정상15/거부9·01/04/06 재현·raw11776pixel 일치. 이전행pending과재개load/read 불일치가전체frame 거부로전파됨. 실제CPU/MMC3/PSRAM/게임/실기원인전체증명아님. test01 library누락/test02 fixture ALE/data-valid오배선 제외;선택test03/trace01/phase01. NEXT 행identity+완전raw coverage 뒤에만불완전fetch 회복,실제주소/data-valid/ROM fault/누락pixel/capacity/STOP 유지. 제품RTL수정·A1완료·새Lite/ZIP/FPS 없음.
- 이전 정상 실기493:60.07초575최종 표시9.57fps/부팅50ms·메뉴 정상,첫 레벨 차이 작음.4899.60fps와 다른 입력이라 지속 가속 미확인. 정상489 FPGA/SNES byte동일+491 ARMquery만 유지,Flash148B/whole15272LE51M9K. 마지막SEAL result1/window3/sink2는실제linked493 postguard/IO구분+16negative로검증;미완료1건은표시제외. 새SNESword/492FPGA보류·단일부팅원인미확정,493·489원복/GBC/save보존.
- 최신498: docs/nes-prefetch498-contract.ko.md + analysis/prefetch498-verification.json. END 수락+drain은IDLE 시작만,진행은lease/END로유지;ARM 최종ACK 대기중next input COMPLETE까지만수신,old video identity/EA뒤새COMMIT. linkedM4정상+5negative/728B callback stack,실제END/lease/exporter4mutant,고정MMC3 C/RTL/old65816 2표시68ACK4bulk/STOP·ACK12→EA12→COMMIT13 PASS;공통M4/IRQ 시간·게임FPS증명아님. 최초continuous-drain 취소결함검출/수정. Lite15132LE14105comb8394FF51M9K/잔여276LE/관련setup+.084hold+.147ns,Flash8B;loader WRITE late blocked선택512조합+mutant동등성. live보드와cost보드는이조건식만다르며hash/동등성고정. 실기4939.57fps/README/원복유지·새ZIP없음. 현재 NEXT는499 A1: 실기 fetch01/04/06의 low/high·PPUMASK·주소/load 짝과 raw-row 경계를 재현한다. 수집 거부를 성능 분석에서 누락하지 않는다. status/word/FSM 미세조정은499의 재개조건 전까지 보류.
- 직전497: docs/nes-bulk497-contract.ko.md + analysis/bulk497-verification.json. linked493 M4 12frame×3 소비지연/9negative PASS,219plan→32chunk/2bank;FINISH all-consumed/표시ACK 없는 retire 거부. instructionclock 모델이며실제65816/IRQ/ROM 공통시간은미완료. reader_drained=arb_idle은END 아님:다음export는generation-bound END 수락+drain,새COMMIT은old 최종ACK/EA뒤. 소유권조건확정후공동연결;실기493/합성비용유지·새ZIP없음.
- 직전496: docs/nes-schedule496-contract.ko.md + analysis/schedule496-verification.json.219 plans→32기존RTL묶음/3824B·583→396packet 모델교정,12동일픽셀/4조건PASS;657.420ms는새성능성과아님. 실제lease RTL은다음capture허용/export는old retire까지차단,stale/STOP+early-export mutant거부. ARM-only prefetch불가. S9 진행중:실제M4 complete485 단일bulkPending/E8/E0·ROM/IRQ 공통시간미연결;다음export시작과COMMIT 분리+oldidentity/guard소유권부터검토. 실기493유지/새합성ZIP없음.
- 실험495(cb09b33):EB8B 진행응답/마지막E0 fullACK+ROM request 중복gate삭제. M4 12기존/6negative·queue3x3949·ROM2위상/4096fault·C/RTL/old65816 1표시34ACK/STOP 통과. Lite15121LE14097comb8394FF51M9K(LE-151은packing,comb+19)/관련setup+.046hold+.164ns,Flash96B/RAM동일. 같은12frame .002794ms 절감/4ms위상 .013316ms 회귀:실제M4 busy-poll/IRQ/sourceROM·coalesced chunk가없어전체가속미증명. 실기493유지/새ZIP없음. NEXT 실제M4 polling+tile_bulk206 묶음+65816 공통event ledger;표시대기중receiver재사용은old identity·retire/STOP·재진입 없는SPI 소유권부터검토,추가작은opcode/seed루프금지.
- 개발 후보491:local plan append 중복 E8 제거+seed2B/64B bounded word DMA·MVN.71 actualCPU 표시3903.397->3620.517ms(7.25%),12/4ms시작/reset·108단위·M4 12guard/8burst/71state·joint/5124bus PASS. Whole Lite15272LE/51M9K·관련setup/hold+0.183/+0.168ns 동일,ARM Flash148B/emit stack16B. 물리 ARM/IRQ/ROM 공통시간 미증명. 492 부팅 실패로 새 FPGA/SNES 선택은 보류하며,493 부팅 회복 확인 뒤 전체 일정/D0를 검토한다. 현재9.57fps와이전489 실측을보존한다.
- 현재 개발 선택은489 실기 동작 경로다. loader inactive payload 선행 저장은 실제 쓰기/오류/STOP/drain 허용과 분리했으며 owned pins/control 동등성+3negative 통과. raw는 plane/row-major 전송과 실제 strided VRAM DMA,2B implicit-pattern cache+6B frame context를 사용한다. 인증은 변경 전 무효화하고 성공 표시 commit에서 확정한 뒤 ACK를 발행한다. 동일12개823.806->757.253ms,71개4234.845->3903.397ms는 실제65816+wire 모델이며 물리 FPS가 아니다.
- Whole Lite1회15272LE/14078comb/8392FF/264800logicalbits/51M9K;136LE·5M9K 여유. 관련 setup+0.183/hold+0.168ns,nominal+0.224/+0.168ns.5KiB ROM이3M9K를 회수한 것은 아니다. ARM493 Flash148B(이전489124B)/새 global0B/RUN31848B/full stack·IRQ 미증명, SNES body4311B/문맥8B. 새 false-path/seed loop 없음, 전체 reset/CDC/IO 미승인 유지.
- MMC489-RAWDMA.zip은 probes/nes-output489/trial02;현재FPGAboard02/ARM02/client04(시험03과동일) 선택, marker NES MMC3 489.nh1/ROM mmc489.nes/로그 *-mmc489.txt. 수신490에서 실행·메뉴 복귀/60.08초577회9.60fps 확인,첫 레벨 체감 개선 작음. 먼저 docs/nes-hardware490-results.ko.md + analysis/hardware490-mmc489.json을 읽는다. NEXT E8공급/E0소비credit·ACK/65816검사 일정 공동 추적,그다음D0 source/ROM.485 대기13.55/플레이8.22와 동일 장면 가속은 미입증. C/RTL boot join은 raw0,raw71 CPU시험과 공통 물리 시계로 합치지 않는다. MCU_RDY는 external_memory_ready이지 source-ready IRQ가 아니다.
- 추가·공개 완료는 GB/GBC G13C44/0.9.0뿐이다. NES60fps는 미완료이며 문양476의23.84fps는 별도 회귀다.
- 현재 실기 근거는 `analysis/hardware503-mmc502.json`,이전493은 `analysis/hardware494-mmc493.json`,이전489는 `analysis/hardware490-mmc489.json`,이전485는 `analysis/hardware486-gameplay485.json`, 문양 회귀는 `analysis/receive477-hardware.json`, 인계는 `cores/nes/HANDOFF.ko.md`다.2차 video_error13의 deadline/emit 전파는 슬롯1/128 실제 M4 시험으로 검증했으며 진짜 capacity 실패를 포괄 허용하지 않는다.
- `src/fpga`, `src/firmware-overlay`, `src/renderer`의 검증된 GBC와 사용자 저장·복원물을 보존한다.

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
