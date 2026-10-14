# NES174 묶음 전송 — 검증 완료, FPGA 타이밍 미해결

NES174에 타일 묶음 전송을 추가했다. SMB3 모델 장면의 패턴 요청18회→3회, 전체 요청45회→30회이며 실제 SNES 수신·229,376픽셀과 ARM 여유1040바이트를 확인했다. 실기 속도·60fps는 미확인이다. FPGA 타이밍-0.807ns와 전체 테이블 전송 비용이 남아 새 ZIP은 없다.

SELECT MCU candidate probes/nes-batch174/arm01; not installable. C c03:9 cases/62 negatives,342 pattern calls→45 total; exact plan/pattern bytes vs cross174. Per SMB3 model24/25: BG16+OBJ2→3 batches(240/16/64B), pattern320B unchanged, allrequests45→30, header+ACK420B saved/frame. This is not measured speed/FPS. Actual existing172 SNES:normal3 commits92ACK,STOP1 commit60ACK;229376pixels. C converter tests use modeledACK; separate real65816 packet producer reuses byte-identical outputs. No new emulator boot suite/Questa/FIT.

Scratch lifetime: OAM[0:239] BG15tile packets→ACK final partial→clear all544→OBJ; CGRAM[0:223] OBJ7tile packets→ACK final partial→clear all512→palette. No retained callback pointer, no secondframe/saveSRAM, no retry/SEAL onfailure. Base174 ABI1741 and exception32 unchanged, actual172 SNES bytes unchanged. Header callback contract now accepts contiguous multiples16/32 up to240; code using old single-tile callback assumptions must adapt explicitly.

ARMcheck01:static26564/foreground37312/IRQ508/margin1040; receiver18064/plan15888 unchanged. Firmware89c98add72ed3a6d983f9961c96b7ac2d7da6a889ba0fc5d5595da25dacfaa87,197988B. Keep paired candidate private until FPGA passes. Source reproduction matches. c01 sandbox DLL load error,c02 test copy missing trace header preserved;c03 passed.

FPGA174 map01 remains nominal-.807, no newFIT/RTL/timing claim. Reviewed actual path load_valid→fault:4levels,5.372ns IC vs1.052cell; X19→shared error_code gate X29→X19. Prior165 parallel fault / error single-owner trials rejected, don't blindly repeat. Next target shared fault/error physical reconvergence using current167 C0raw/C1causes/C2decode/C3accept/C4counter; preserve accept edge/error precedence/WRITE-HOLD drain or document any contract change and MCU latency. Then minimal timing/changed-boundary/IO/ARM and actualSMB3.

Fullmap4096+CGRAM512+OAM544+HDMA and perpacketACK still dominate; SNES localdeltaDMA already exists. Skipping packets requires explicit inactive-WRAM base-generation inheritance; otherwise two-generations-old bytes can leak. AV60fps→longplay/error-resetlog→heldinput, keepGBC164/saveSRAM/noRUN-SD. Same173/044/bootA-B/passed174pixel-SPI replay unnecessary unless changed. Record/audit/evidence immutable; PR110 existingOPEN, refresh before publication.

[계약](../../docs/nes-batch174-contract.ko.md) · [검증](../../analysis/batch174-verification.json)

---

# NES174 후보 — 타일 간 비트평면 검증 완료, 타이밍 미달

NES174 후보는 SMB3의 서로 다른 타일 비트평면을 보존하도록 수정했다. 모델frame24 수집과 frame24·25의114,688픽셀 비교, SPI·C 및 ARM 여유1024바이트 검증을 통과했다. FPGA 배치는 성공했지만 memory setup-0.807ns로 미채택이며 새 실기 ZIP은 없다. 실제 정지 해결·60fps는 미확인이고 반복 전송 비용도 남았다.

SELECT 없음/미배포. probes/nes-cross174 map01/unit02/replay01/c01/pixels01/spi01/arm01/armcheck03. 26frame model12..26valid, old24reject185rows→224rows. Pixels24/25 match114688; SPI phases0/3.5 each1733records47blocks12587wireB/C191calls. No physical FPS claim. Model24 != physical173generation30. C context18064/plan15888 unchanged; linked26564static/37328foreground/508IRQ/1024margin. Fit15076LE963LAB36M9K; nominalmemory-.807FAIL/host+1.483/NES+6.370/holdmin+.146. No ZIP/IOCDC174 signoff. Existing173 remains last distributed package; do not install standalone174 firmware.

New ABI: BEGIN1741,kind3 width4. Exception lowtile13/cell13(row*33+col)/highY3/lowY3;128entry limit unchanged. Both physical sources required; cross-cell unique64bit key avoids collisions. The legacy module comments about same-tile rejection do not describe174 logic: use the174 contract and generated expressions. Collector2+Creceiver/converter changed; SPIwidth/exportmagic; SNES172 bytes retained. General malformed geometry and OBJ checks remain strict.

NEXT review actual control.load_valid→loader.fault and check_failed→fault/loaded_bytes routing/fanout before a targeted structural candidate. Four logic levels,5.372ns data interconnect; not new NES collector critical path. Compare prior165 fault/counter failures first; no unchanged refit/seed/clockrelax/falsepaths. Once timing recovered, pair with changed-boundary/ARM checks then minimal actualSMB3. Do not redo passed24/25pixel/SPI tests unless their inputs change.

Throughput remainsOPEN:173build+seal203.125ms/update. Existing SNES-local deltaDMA is already present; upstream seal still sends5152B+HDMA withperpacketACK. Plan pattern batching within240B and avoid unchanged/fulltable wire traffic. Reuse candidate fields only with an explicit lifetime contract; no secondfullMCUframe or cartridge saveSRAM. This optimization is not implemented in174. AV60fps→longplay/error-resetlogs→heldinput; no same173/044/bootA-B/genericobserver expansion.

Manifest3d36ea4df09a47dfb05c5f19a89a22538e4bf6c3d513902b46ef0a45741a3303,2087 private evidencefiles frozen. record01/audit finalizers must not be rerun. unit01 wrongsandboxTEMP and armcheck01 DLLload errors are setup failures, not RTL/license failures; unit02/hostarmcheck03 selected. Original173 evidence unchanged. Tests/FLOAT/Quartus finished. PR110 existingOPEN; refresh before next publication.

[계약](../../docs/nes-cross174-contract.ko.md) · [검증](../../analysis/cross174-verification.json)

---

# NES173 실기 — 정지와 초기 처리량을 분리

NES173 실기: RUN 시작 후5.79초까지 표시 ACK16회 뒤 추가 완료가 멈췄다. 변환/패턴 전송910ms와 테이블·SEAL/ACK2340ms, 합계 회당 약203ms로 초기 처리량도60fps 목표에 크게 못 미친다. 정상60초 종료·STOP/메뉴 준비 확인. 정지 원인 미확정, 같은173 재시험 없이 타일 간 plane 표현과 반복 전송/왕복 개선으로 진행한다.

BEGIN/END/COMMIT/ACK16,ABORT0,lastgen30,ROM/sink/video0,deadline1. profile receive54170ms includes idle after freeze; build910ms/seal2340ms,lastACK5790ms relativeRUN. Means56.875/146.25/203.125ms;16/5.79=2.76 ACK/s interval average NOTTVfps. Counter sum57420 vs60000 leaves2580 outside/incomplete/quantization;do not attribute or subtract54210 idle to infer active receive. DISPLAY60060ms,menu-prepared295750ms;user same172 symptoms/no newvideo.

다음 작업: cross-tile plane/row representation preserving both sources; minimal boundary test thenSMB3. Also remove unnecessary fulltable retransmission/perpacket roundtrips: seal sends5152B map/CGRAM/OAM+HDMA,minimum26packets inclseal; pattern transfers extra. Seal2340ms NOTpureSNES DMA; existingSNESlocalcompare/deltaDMA should not be reimplemented. No fullsecondMCUframe/saveSRAM, preserveACKownership/STOP/audio/pad. Generation30 means do not fixate on27 or equate model24. NewBEGINnotreceived is not a live FPGA state observation.

No newfirmware/FPGA/ZIP, same173/044/redundantFIT/generictrace unnecessary. AV60fps→longplay/error-resetlogs→heldinput. PR110 existingOPEN. Preserve173 implementation archive. [실기 결과](../../docs/nes-game173-hardware01.ko.md) · [근거](../../analysis/game173-hardware01-verification.json).

---

# NES173 — MCU 측정판 실기 대기, 새 FPGA 관측 후보 미채택

173은 172 FPGA·SNES ROM을 바이트 그대로 유지하며 초기 화면부터 느린 비용을 수신/대기·변환/staging·SEAL/ACK로 나눠 기록한다. 마지막 표시 ACK 시각은 RUN 시작 기준이다. 시간 분해능10ms, 누적값은 실패한 미완료 단계를 제외하며 수신값에는 정지 후 대기가 들어간다. 14회 ACK나 전체 SPI 바이트를 FPS로 환산하지 않는다. 화면 정지 수정판이나60fps 달성판은 아니다.

SELECT probes/nes-admission173 arm04/profile04/armcheck03/report02/release01. 실제 C10경우·tick wrap PASS, ARM static26564/foreground37328/IRQ508/margin1024, TXT3934/4096. FPGA SHA6e9f7fc0 exact172; MCU9b137807; ZIP633b8c46. 패키지는 NES173-SMB3-VIDEO-PROFILE.zip. NES GAME 173.nh1 한 번 실행 후 두173 TXT를 받는다. 동일 증상이면 영상/044/동일 부팅 시험은 불필요하다. 실행 중 SD 쓰기·세이브 SRAM 사용 없음.

실제 ROM 확장 재현은 frame24에서 fetch pair error2 + compact error1, rows185로 전송 전 거부를 재현했다. replay02와 상세 관측 replay04의 결과·소스 해시는 analysis/profile173-verification.json을 읽는다. CPU/PPU/MMC3+70ns 모델과 배포 collector4개를 연결했지만 매 프레임 즉시 release하며 실제 MCU/fill/export/SNES 소비 속도는 없다. 모델24와 실기generation27을 동일 원인으로 단정하지 않는다. 다음은 불일치한 plane 주소/description을 근거로 필요한 표현만 수정하는 것과173의 실제 단계 비용 대조다. 일반 조건 완화나 malformed frame 허용은 금지한다.

실험 tools/nes_admission173.py의 A3 history 관측은 map03 fullFIT 후 nominal memory setup -0.077ns여서 미채택·미배포다. 기능 signoff도 아니다. 기존 FPGA 전체 재사용으로 측정을 먼저 실기로 보낸다. A3 코드를173 패키지와 혼동하거나 미달 후보를 반복FIT/clock 완화하지 않는다. 초기48B trace는 margin1016 실패,40B 최종본으로1024 회복. 해당 실패·경로 누락 replay03 등은 보존했다.

replay04 상세: frame24,line193,dot232,low_phys21e150/high21e1ff,logical0150/01ff,pending1/address_ok1/BG. 기존 같은 타일 fineY 예외로는 physical tile1e15→1e1f와fineY0→7을 표현할 수 없어 ordinary/split 모두0. ROM 데이터 비교 오류 없음. 다음 구현은 두 타일의 해당 plane/행을 보존하는 제한된 합성 패턴 또는 동등한 표현이며 high 주소만 사용/조건만 완화 금지. 정확한 $2006 트리거 및 실기 원인은 별도 미확정. 173 단계 비용 로그와 함께 다룬다.

PR110 기존 브랜치에 정리한다. 연속 AV→장기 플레이/오류·본체 리셋 로그→입력 유지 순서와 GBC·164·세이브 보호를 유지한다. 기존172 증거와 완료 archive는 불변이다. 새 결과 기록/패키지 생성기를 같은 경로에 다시 실행하지 않는다.

[실기 안내](../../docs/nes-game173-ready.ko.md) · [계약](../../docs/nes-profile173-contract.ko.md) · [검증](../../analysis/profile173-verification.json)

---

# NES172 실기 — 초기 표시 통과, 다음 영상 후보 미수신

사용자 추가 확인: 처음 표시된 구간도 뚝뚝 끊겼다. 14회 ACK는 원활한 화면의 증거가 아니다. 목표는 실제 SMB3에서 약60fps의 연속 표시이며, 정지 해소만으로 완료 처리하지 않는다. 프레임 생성·전송·SNES 반영별 진행 시간과 화면 완료 간격을 구분해 병목을 줄인다. 60fps의 프레임 간격 약16.7ms를 목표 예산으로 삼되 현재 측정치로 주장하지 않는다. 전체 SPI 바이트에는 상태 폴링이 포함되므로 영상 전송량이나 유효 FPS로 바로 환산하지 않는다.

NES172 실기에서 표시 준비와 14회 표시 완료 응답을 통과했지만 이후 화면이 멈췄다. 버튼·스테이지 음악은 계속 반응했고 정상 약60초 한도로 메뉴에 복귀했다. BEGIN/END/COMMIT 각14, ABORT0, 마지막 generation27이다.170의 수집 시간 초과와 달리 다음 BEGIN이 수신되지 않은 경계이며, 연속 화면 목표는 미달성이다.

마지막 generation27 뒤 fetch/compact/raster 결합·전송 전 허용 조건과 공통 release·exporter DRAIN/fill_busy를 우선 확인한다. 전송 전 반복 거부와 해제/수집 미진행을 구분하고, 필요할 때 해당 경계의 최소 상태만 종료 로그에 남긴다. 변경 경계 검증 후 실제 SMB3로 복귀하며 같은172/044·부팅/A-B·무변경FIT·근거 없는 시간 제한 증가는 반복하지 않는다. 연속 AV→장기 실행/오류·본체 리셋 로그→입력 유지 순서와 세이브 SRAM/GBC/164 보호를 유지한다.

[결과](../../docs/nes-game172-hardware01.ko.md) · [필드·소스 해시](../../analysis/game172-hardware01-verification.json). PR110 OPEN; no new firmware/FPGA/ZIP. DISPLAY60050ms includes boot; runtime6000ticks starts afterready. receiver21 is secondary to deadline1; trace_state4 is lastvalidatedCOMMIT snapshot, NOTliveFPGA/receiver state. ABORT0 does not cover pre-BEGIN invalidgeometry release. User AV/menu report + video samples; no independent audio/FPS claim. Keep172 build/evidence archives immutable.

---

# NES172 — 준비 확인 후 첫 표시 요청, 실기 대기

NES172는 ROM 진입·WRAM 복사 검증·표시 준비 완료를 구분하고 준비 완료 후에만 첫 화면 데이터를 전송한다.171 FIFO와 FPGA 배선은 유지하고 SNES ROM·MCU 시작 순서를 바꿨다. 실제65816 부팅4경우, C 대기9경우,6회 표시·270ACK 및 ARM 여유1024바이트·로그4020바이트 검증을 통과했다. 실기 원인 해결과 연속 화면 성공은 아직 미확인이다.

NES172-SMB3-BOOT-READY.zip을 함께 적용하고 NES GAME 172.nh1을 실행한다. 준비 실패 시 기존 로그의 stage0/1/E1/2/3으로 reset/ROM/복사/초기화/패킷 경계를 좁힌다. 첫 화면이 나오면 지속 갱신·음악·메뉴 복귀와 두 TXT를 받고 가능하면 짧은 영상을 확인한다. 같은 무화면이면 영상·171/044 재시험은 불필요하다. 준비 후60초 실행하며 총6분 관찰 상한을 둔다. 연속 AV→장기 실행/오류·리셋 로그→입력 유지 순서와 세이브 SRAM/GBC/164 보호를 유지한다.

[계약](../../docs/nes-boot172-contract.ko.md) · [검증](../../analysis/boot172-verification.json). PR110 OPEN. SELECT client01/test03/gate02/display01/arm02/armcheck03/asm01/report02/release01. No new FIT;65 routing/source files unchanged171;3163B copied/verified in4096B ROM. Boot mismatch stageE1 differs from SPC errorE1. Failure run_first_error6/native SERVICE2; preserve earlier errors. Initial inlining failed stack margin1008; noinline final1024. Ready gate before runtime begin, so60s starts after ready. No SD during RUN, no blind retry. Do not rerun completed record or alter archives.

---

# NES171 실기 — 첫 BEGIN 응답 미완료

NES171 실기에서 첫 화면 표시 전에 종료됐다. ROM393216바이트 적재·비교와 첫 영상 후보 COMMIT1은 성공했지만, 첫 BEGIN 요청이 FPGA에 보관된 채 SNES 완료 ACK 없이65536회 대기 한도에 도달했다. 표시 구간13410ms, 표시 완료0회, ROM 오류0이며 STOP·기본 FPGA·메뉴 준비는 정상이다.170의0x34 수집 시간 초과와 다르고169의 초기 응답 실패와 같은 경계다. FIFO의 연속 화면 개선 효과는 아직 실기에서 확인하지 못했다.

다음은 SNES 표시 프로그램의 실제 reset 해제→ROM 부팅→WRAM 복사→첫 패킷 읽기→ACK 게시 경계를 좁혀 수정한다. sealed1/ACK0만으로 부팅 실패나 FIFO 회귀를 확정하지 않는다. 기존 프로그램 바이트 일치·모델 부팅·무변경 FIT를 반복하거나 대기 한도만 늘리지 않는다. 변경 경계의 최소 검증 후 실제 SMB3로 돌아간다. 같은171·044 재시험이나 추가 영상은 필요하지 않다. 연속 AV→장기 실행/오류·본체 리셋 로그→입력 유지 순서와 세이브 SRAM/GBC/164 보호를 유지한다.

[결과](../../docs/nes-game171-hardware01.ko.md) · [필드·소스 해시](../../analysis/game171-hardware01-verification.json). PR110 OPEN; no new firmware/ZIP. Completed archives immutable.

---

# NES171 — CHR 선행 읽기 FIFO 실기 대기

NES171 실기 시험판을 준비했다.170의 화면 정지 원인인 그래픽 수집 전체 시간 초과를 줄이도록 FPGA에256×27비트 FIFO(M9K1개)를 추가해 읽기와 MCU 소비 대기를 분리했다. 같은 모델 조건에서 기존654바이트 중단→2048바이트 완료, 최대8192바이트도 통과했다.15014LE/959LAB/36M9K 배치와 실제 클록 기준 setup+0.024ns·hold+0.127ns, 조건부 IO·ARM 여유1024바이트를 확인했다. 시간 제한·사운드·입력·SNES169 표시는 유지하며 연속 AV 실기는 아직 대기다.

NES171-SMB3-CHR-FIFO.zip의01-GAME171-SD-ROOT를 적용하고 NES GAME 171.nh1로 SMB3 첫 레벨을 실행한다. 첫 화면 이후 지속 갱신·사운드·입력·약60초 메뉴 복귀와 두 TXT를 확인한다. 가능하면20~30초 영상, 동일 정지/무화면이면 TXT·설명만 받는다.0x34가 남으면 실제 생산/소비 진행량에 따라 경계를 좁힌다. 같은170/044·무변경FIT·범용 진단 반복 없이 연속 AV→장기 실행/오류·본체 리셋 로그→입력 유지 순서를 지킨다. 세이브 SRAM/GBC/164 보호와 CPU/PPU 우선·7에지 감시를 유지한다.

[실기 안내](../../docs/nes-game171-ready.ko.md) · [변경·검증 계약](../../docs/nes-prefetch171-contract.ko.md) · [검증 근거](../../analysis/prefetch171-verification.json). PR110 OPEN/samebranch. SELECT map02/test02/cancel02/arm01/armcheck01/report01/release01.28 RTL cases incl512tile two phases/full FIFO clear-generation-reset. 60 other FPGA inputs exact169; only fill changed, same limits. FIFO synchronous head avoids read-during-write stale data; all bytes tentative until unchanged COMMIT/display ACK. Firmware2e7dc90c / FPGAd67ad0a2 / ZIP4782ef2f. Model is not measured hardware pacing/FPS. No full IO/CDC/MTBF claim;24 legacy negative reset paths remain separately recorded. Declaration-order test01 and no-pending cancel01 fixture failures retained. Sandbox host/binutils failures are not license entitlement or RTL failures. No active jobs; completed archive/finalizers immutable.

---

# NES170 실기 — 표시 완료 후 CHR 수집 시간 초과

NES170 실기에서13회 표시 완료 ACK·음악·스타트 반응을 확인했지만 이후 화면이 멈췄다. 영상 후보21회 중13회 완료,8회 중단이며 최초·마지막 중단0x34는 CHR 수집의 전체 시간 예산 초과다. 정상60초 제한으로 종료했고 ROM/표시 통신 오류는0이다. 연속 AV 목표는 미달성이다.

다음은 CHR 수집·전송의 전체 예산 초과를 수정한다. 실제 vblank/CPU 우선 메모리 승인과 SPI 소비자 대기를 포함해 최초 중단1892바이트·0x34를 재현하고 병목을 구분한다.167에서 이미 전체 예산을8배 늘렸으므로 단순 재증가를 반복하지 않는다. 승인 기회·전송 오버헤드를 줄이거나 측정 근거로 유한한 진행/전체 예산 계약을 정하고 변경 경계만 검증한 뒤 SMB3 실기로 간다.169 첫 BEGIN 실패는 이번 미재현이며 해결 확정은 아니다. 같은170/044·무변경FIT·추가 영상은 요청하지 않는다. 연속 AV→장기 플레이/오류·리셋 로그→입력 유지 순서와 코어 우선권·PSRAM 타이밍·세이브 SRAM/GBC/164 보호를 유지한다.

[실기 결과](../../docs/nes-game170-hardware01.ko.md) · [필드·해시·대조](../../analysis/game170-hardware01-verification.json). PR110 OPEN. No new firmware/FPGA/ZIP. receiver21 is secondary to deadline; middle6 abort reasons unknown; menu visible return unreported. Completed archives immutable.

---

# NES170 — 첫 표시 통신 실패 구분판, 실기 대기

NES170 실기 시험판을 준비했다.169의 첫 BEGIN 실패를 구분하도록 MCU에 최초 통신 실패 위치·폴링 횟수·상태 응답20바이트를 추가했다. 통신 동작267개 비교와 TXT4020/4096바이트·RUN/IRQ 후1024바이트 여유를 확인했다.169의 FPGA/SNES·리셋·대기 제한은 유지하며 화면 수정 완료판은 아니다. 사용자가169 종료 시간을 약13~14초, 총 약4분으로 정정했다.

NES GAME 170.nh1을 한 번 실행하고 nes-progress-170.txt/nes-game-last-170.txt 및 화면·메뉴 복귀 여부를 받는다. 동일한 로딩 화면이면 영상·버튼 입력은 불필요하다. sink_io170 사유/수신 상태로 초기busy·상태 오류·65536회 소진을 구분한다. pending 소진과 기동 표식0이면 리셋/실제 부트 경계를 우선한다. 확인한 원인의 최소 수정 후 SMB3 실기로 간다. 같은169/044·무변경FIT를 반복하지 않고 연속 AV→장기 플레이/오류·리셋 로그→입력 유지 순서를 지킨다.

[실기 안내](../../docs/nes-game170-ready.ko.md) · [변경·검증·분기](../../docs/nes-startup170-contract.ko.md) · [근거](../../analysis/startup170-verification.json). PR110 OPEN, samebranch. SELECT arm02/armcheck02/test02/report01/romcheck01/release01. FPGA6ba98335 exact169, no newFIT/ASM. Postfit4netlists/4M9K atoms4096B exact169; NOT physicalreadback. MCU trace20B/firmware197652/static26572/RUN37320/IRQ508/margin1024;report4020. RR bit7=status received NOTCRCvalid, RX1..15, polls32. No retry/limit/reset changes, no RUN SD writes. arm01 wrong Makefile .o anchor corrected .c; sandbox subst/GCC623 retried host; failed artifacts retained. User169 timing correction supersedes ~60s; no newclock issue. Keep164/GBC/saveSRAM. Completed archives immutable.

---

# NES169 실기 — 첫 BEGIN 응답 실패, 표시 기동 경계 조사

NES169 실기는 로딩 화면 유지 후 메뉴로 복귀했다. ROM393216바이트 검증·첫 영상 COMMIT은 성공했지만 첫 BEGIN(세션1/세대12)에 유효한 ACK가 없어 표시0회로 종료했다. DISPLAY5/sink2이며 정상60초 만료나168의 E3 재발이 아니다. STOP·기본 FPGA·메뉴 복구는 정상이다. 분할 갱신과 연속 AV의 실기 목표는 미달성이다.

SNES 리셋 해제→물리 부트 ROM/WRAM 복사→초기화→첫 BEGIN ACK 경계를 우선 확인한다.169 ROM 갱신 이미지와 실제 실행 연결을 대조하고, 필요할 때만 exchange 최초 실패 위치·마지막 F6 상태를 종료 TXT에 최소 추가한다. 원인이 확인된 수정과 최소 검증 후 SMB3 실기로 복귀한다. 같은169/044·무변경FIT·추가 영상은 요청하지 않는다. 연속 AV→장기 플레이/오류·본체 리셋 로그→입력 유지 순서와 세이브 SRAM/GBC/164 보호를 유지한다.

[실기 결과](../../docs/nes-game169-hardware01.ko.md) · [원문·해시·대조](../../analysis/game169-hardware01-verification.json). PR110 OPEN. ACKvalid0 means no actual ACK, zero fields are placeholders. Request BEGIN seq0/serial1/gen12, native_frames0; stage0/flags0/SPCinvalid auxiliary, NOT definitive reset failure. Firmware DISPLAY interval13490ms versus user ~60s kept separately. Compact4096/MIF/logical32768SFC match; RBF packed decode only, NOT RBF ROM-bit readback. MCU6 critical files exact168. Next physical startup/F6 subcause, NOT more E3 budget edits. Existing169 local tests retained; no new FW/FIT/ZIP or same169 test. Completed archives immutable.

---

# NES169 — E3 큰 갱신을 비표시 VRAM에 준비, 실기 대기

NES169은168 실기의 E3 종료를 처리한다. 작은 변경은 기존 경로, 큰 변경은 비표시 SNES VRAM에 최대6청크로 준비한 뒤 최종 vblank에서 BG/OBJ/맵·색상·OAM·HDMA를 전환한다. 실제65816 검사에서21개 완료 화면1284864픽셀·이전 화면 유지·최대 크기·전송 중 STOP을 확인했다. MCU 실행과 FPGA 배치는 유지하고 SNES ROM만 갱신한 실기 시험판을 준비했다. 실기 연속 AV·FPS는 아직 미확인이다.

NES169-SMB3-BANKED-VIDEO.zip의01-GAME169-SD-ROOT를 적용하고 NES GAME 169.nh1에서 SMB3 플레이어 선택→월드맵→첫 레벨을 진행한다. 첫 화면 이후 조기 종료가 없어졌는지, 큰 갱신 중 검정/혼합 화면이 있는지, 사운드·약60초 메뉴 복귀를 확인하고 두 TXT와 가능하면 영상을 받는다. 기존 약4분 적재·검증은 유지한다. 실패하면 sink_trace 원문·native_frames·STOP 결과를 우선 분석한다. 반복168/044·무변경FIT·추가 범용진단은 하지 않는다. 연속 AV 다음 장기 플레이/오류·리셋 로그, 그다음 입력 유지를 검증한다.

[안내](../../docs/nes-game169-ready.ko.md) · [구현·경계](../../docs/nes-banked169-contract.ko.md) · [근거](../../analysis/banked169-verification.json). SELECT client01/arm01/armcheck02/verify01/asm01/release01;body3154/4096;SNES14+2metadata bytes, MCU unchanged32trace/1044margin/report3966. E2/E3 only fallback; rawstage167 routed65 files unchanged/MIF+CDB+ASM only. Maximum6x4096 then CGRAM/OAM1248+registers/HDMA;no post-reveal blank;STOP mid-copyE4. Completed archives immutable. PR110 existing open branch unless refreshed merge.

---

# NES168 실기 — E3 전송 예산 초과 확정, 다음은 큰 변경 처리

NES168 실기에서 첫 화면 후 종료 증상은 같았지만 원인은 확인됐다. 표시 완료7회 뒤8번째 영상(세대20)의 SEAL에 SNES가 E3(변경분 전송 예산 초과)를 반환했다. 순번46·세션8·세대20·서명은 모두 일치하고 불일치는 상태 코드뿐이다. ROM 오류0·STOP·기본 FPGA 복구·메뉴 준비는 통과했다. 진단 목적은 달성했으며 연속 플레이는 아직 실패다.

다음 구현은 E3를 일으키는 합법적인 큰 화면 변경을 게임 종료 없이 완료하는 경로다. 현재 변경 구간 합계+명령당96 비용과5000 상한,32명령 제한을 기준으로 최소 재현하고 유한 분할/표시 전환 방식을 결정한다. 여러 vblank로 나눌 경우 이전 표시와 갱신 중 VRAM·CGRAM·OAM·HDMA의 일관성, 변경 후보 소유권, 마지막 완료 뒤에만 ACK/세대 갱신, STOP·시간 제한·사운드/입력 서비스를 함께 보장한다. 무조건 상한 증대·검사 제거·성공 ACK 위조·무한 재시도·영구 프레임 폐기는 금지한다. 필요하면 명시적 대체 표시 정책의 시각적 영향을 문서화한다. 해당 경계의 최소 검증 후 바로 SMB3 실기로 간다.168 재시험·추가 영상·044 복원·무변경 FPGA FIT는 불필요하다. 연속 AV→장기 플레이/오류·본체 리셋 로그→입력 유지 순서와 세이브 SRAM/GBC/164 보호를 유지한다.

[실기 결과](../../docs/nes-game168-hardware01.ko.md) · [원문 해석](../../analysis/game168-hardware01-verification.json). PR110 OPEN. SEAL seq46/serial8/gen20, ACKe3/status-only01. Configured5000=sum DMA bytes+96/command; actual charge/count unknown.7display ACK/8received;3560ms NOTFPS. Existing arm02/FPGA/SNES unchanged; no new FW/FIT/ZIP. Completed archives immutable.

---

# NES168 — 최초 SNES 실패 응답 실기 확인

NES168은167의 첫 화면 이후 종료 원인을 구분하는 MCU 시험판이다. 처음 실패한 요청16바이트·응답12바이트와 불일치 항목을32바이트 상태에 보존한다. FPGA·SNES·갱신 상한은167과 같고, 영상 오류 수정 완료는 아니다. 실제 SNES의 E2/E3 거절 구분과 기존 정상 화면·안전 종료 검사를 통과해 실기 패키지를 준비했다.

NES GAME 168.nh1로 실행 후 두 TXT를 받는다. 먼저 버튼을 누르지 않아도 되고 같은 짧은 화면이면 영상은 불필요하다. ack_valid1/mismatch01이면 ACK status E0~E4를 해석하고 실제 실패 op·길이·순번·세대로 경로를 한정한다. E2/E3라면 해당 장면의 변경 범위/명령 수·전송 예산을 재현하고 한도를 해제하지 않은 유한 분할·표시 완료 처리로 수정한다. token/signature 불일치면 패킷/ACK 소유권·snapshot을 먼저 고친다. ack_valid0이면 하위 통신/guard 종료를 분석한다. 수정 후 곧바로 SMB3 실기, 이후 AV→장기 플레이/오류·리셋 로그→입력 유지 순서. 같은167/044·무변경 FPGA FIT는 반복하지 않는다.

[설치](../../docs/nes-game168-ready.ko.md) · [계약](../../docs/nes-sink168-contract.ko.md) · [검증](../../analysis/sink168-verification.json). SELECT arm02/armcheck01/test02/report01/release01. FW111a28c4/ZIP77de2a08/FPGA d1e82782 unchanged167.32B/169reportB/3966maxreport/1044stackmargin. No newFIT/Questa. Completed archives immutable.

---

# NES167 실기 — 첫 화면 확인, 8번째 영상의 ACK 검사 실패

NES167 실기에서 첫 화면이 약1~2초 보인 뒤 메뉴로 복귀했다. BEGIN/END/COMMIT 각8회·ABORT0회, SNES 표시 ACK 완료7회로 새 영상 경로의 첫 출력은 확인했다. 이후 sink 응답 내용 검사 오류3으로 조기 종료했다. ROM 검증·STOP·메뉴 복귀는 통과했고, 연속 영상·실제 사운드는 미확인이다.

실패한8번째 영상의 SNES 패킷 응답 검사를 우선 조사한다. 기존 성공7회/마지막세대22·수신세대24를 기준으로 연속 프레임의 변경량·32개 DMA 명령 상한·5000 전송 예산·길이/순번/세대 소유권을 최소 재현한다. sink 오류3만으로 SNES 거절(E0~E4)과 응답 토큰/서명 불일치를 구분할 수 없으므로 실패 패킷의 op/section/offset/length, 기대 토큰 및 실제12바이트 ACK를 안전 정지 후 기존 TXT에 기록하는 최소 보강을 우선한다. 응답 검사를 끄거나 상한을 무조건 늘리지 않는다. 필요한 수정 뒤 SMB3 실기로 복귀하며 같은167·044·무변경 FIT를 반복하지 않는다. 이후 연속 AV→장기 플레이/오류·본체 리셋 로그→입력 유지 순서를 유지한다.

[실기 결과](../../docs/nes-game167-hardware01.ko.md) · [근거](../../analysis/game167-hardware01-verification.json). PR109 OPEN. No new RTL/FW/FIT/ZIP. Previous archives immutable.

---

# NES167 — 새 영상 수집 시험판 실기 대기

NES167 실기 시험판을 준비했다. 원시 자격 캡처와 명령 판정을 분리하고 적재 카운터 산술 분리를 결합해 내부 setup+0.245ns/hold+0.126ns,14944LE/956LAB/35M9K를 통과했다. 조건부 외부 연결·영상 리셋 검사를 통과해167 MCU와 새 FPGA를 패키징했다. 화면 복구·속도·사운드는 새 실기 결과로 확인해야 한다.

NES167-SMB3-FILL-WAIT.zip의01-GAME167-SD-ROOT 내용을 SD 루트에 적용하고 NES GAME 167.nh1로 SMB3(J) 첫 레벨의 화면·사운드·약60초 메뉴 복귀를 확인한다. nes-progress-167.txt/nes-game-last-167.txt와 화면이 나오면20~30초 영상을 받는다. 검정이면 촬영 불필요. 결과 전에는 새 범용 진단·무변경 FIT/부팅·166/044 반복 시험을 추가하지 않는다. 실패하면 최초 fill 세부 사유와 BEGIN/END/ABORT/COMMIT/native_frames에 따라 실제 경로만 고친다. 이후 연속 AV 품질→장기 플레이/오류·본체 리셋 로그→입력 유지 순서를 지킨다.

[설치 안내](../../docs/nes-game167-ready.ko.md) · [계약](../../docs/nes-rawstage167-contract.ko.md) · [검증](../../analysis/rawstage167-verification.json). PR109 OPEN. SELECT rawstage167/map01 + pacing167/arm01/armcheck03 + release01. C0raw/C1causes/C2decode/C3accept/C4counter, NOTsameedge. 369165+180+24+219SPI14016bits/3negativePASS;loader exactreuse294912/1056/524288.61reproduced/59unchanged;FIT14944LE956LAB35M9K setup+.245/hold+.126;IOconditionalPASS/payloadreset0/24syncpathsremain. Package99f9cf59/fw783a3c83/FPGAd1e82782;164restoreexact/privateROMnotGit. test01 reservedtaskword preserved/test02 PASS. Alljobsfinished; do not rerun completedrecord/audit or unchangedhardware166/044/fit.

---

# NES167 C2/C3 — CHECK 개선, 전체 타이밍 미달

NES167 CHECK의 오류 판정(C2)과 카운터 반영(C3)을 분리해 카운터 경로+1.011ns·판정+0.699ns를 확보했다. 기능·SPI 응답은 통과했으나 전체 setup은 로더 fault→명령 자격-0.190ns, 적재 카운터-0.041ns여서 후보는 미채택이다. 새 실기 ZIP은 없고 승인 FPGA는boundary165/map02를 유지한다.

CHECK 카운터는 더 작은 식으로 반복 배치하지 않는다. commitstage167/map01은 후속 구조 연구용이며 승인/최선 전체 타이밍 기준은 아니다. 남은 fault→run_enable→check_active→body_causes→pending_causes의5단계(배선70%)를 대상으로, SS 캡처 C0에서 원시 자격을 저장하고 이후 단계에서 명령 원인·오류를 판정하는 명시적 파이프라인을 설계한다. C0 관측 값, live fault 차단, STOP/write drain, 단계별 SS 겹침/reset, 실제2us 간격 및 응답 snapshot 호환성을 먼저 검증한다. 기존 loadcount167의 적재 산술 분리 결과는 재사용하되 새 SPI와 결합 경계는 검증한다. 그 구조 변경 뒤 한 번 FIT하고 실제 클록·조건부 IO/reset이 통과하면 기존167 MCU/영상 근거를 재사용해 패키지와 SMB3 실기로 간다.166·044·무변경 부팅·seed 순회는 반복하지 않는다.

[계약](../../docs/nes-commitstage167-contract.ko.md) · [검증](../../analysis/commitstage167-verification.json). PR109 OPEN. C2 acceptance/C3 counter NOT same-edge; latefault preserves accepted metadata/reset cancels. 1048576+24+219SPI14016bits/3negativePASS. Initial inconsistent-carry fixture preserved; use test02. 60inputs unchanged; oneFIT; no newIO/ASM/SD. Completed record/audit/archives immutable.

---

# NES167 후속 — 기능 통과, 두 배치 미채택

NES167 정상 대기 수정은 기능 검증을 통과했으나 실기 ZIP은 여전히 보류다. CHECK 갱신 펄스화는 해당 경로를+0.581ns로 개선했지만 적재 카운터가-0.349ns였다. 적재 카운터 갱신·산술 분리 후 해당 경로는+0.338ns, CHECK는-0.144ns여서 두 후보 모두 미채택이다. 승인 FPGA는boundary165/map02, 다음 분석 기준은pacing167/map04(-0.003ns)를 유지한다.

같은 클록 카운터 식·seed·설정으로 전체 FIT를 다시 반복하지 않는다. MCU의 기존2us SS 간격 안에서 오류 판정(C2)과 CHECK 카운터 반영(C3)을 분리할 수 있는지 먼저 계약을 정한다. fault/STOP/reset 우선순위, 응답과 명령 겹침, 주소·상태 snapshot이 관측 가능한 edge, SPI ID/MCU 호환성을 명시한다. 같은 edge 등가로 주장하거나 false path로 완화하지 않는다. 가능하면 변경 경계만 검증한 뒤 한 번 배치한다. 불가하면 근거와 함께 영역 배치 보존을 검토한다. 내부 타이밍과 조건부 IO/reset 통과 후167 MCU·미변경 SNES 근거를 재사용해 패키지와 SMB3 실기로 간다.166·044 재시험은 요청하지 않는다.

[계약](../../docs/nes-counterpulse167-contract.ko.md) · [검증](../../analysis/counterpulse167-verification.json). SamePR109 OPEN. Two fits only; archives immutable. Do not rerun completed record/audit. Next define explicit C2/C3 response-fault/counter commitment, not same-edge claim. No SD.

---

# NES167 — 기능 수정 통과, 타이밍 미달로 배포 보류

NES167 정상 대기 분리·취소 세부 이유 수정은 기능 검증을 통과했다. 그러나 FPGA 실제 클록 setup은 최선map04도-0.003ns로 미달이어서 실기 ZIP을 보류했다. 기존 승인 FPGA는 유지하며 ROM CHECK 경로를 직접 개선한 뒤 실기로 진행한다.

실기 ZIP은 보류한다. 기능 수정은 유지하고 map04(Standard Fit, placement multiplier1.0)의 실제168MHz ROM CHECK 경로 check_response_address[8]→check_next[13] 경로(-0.003ns)를 직접 분석한다. 기존 compare165의 기각된 비교식/설정과 map01~05를 반복하지 않는다. 해당 제어 영역의 배치 보존·국소 제어/팬아웃 개선을 먼저 검토하고 필요한 경계만 검증한다. 클록/false-path 완화·seed 순회 금지. 실제 클록 setup/hold와 새 배치의 조건부 IO/reset이 통과하면 기존167 MCU·미변경 SNES 결과를 재사용해 ASM/ZIP 후 SMB3 실기로 간다. 같은166·044·무변경 부팅은 요청하지 않는다.

[계약](../../docs/nes-pacing167-contract.ko.md) · [검증](../../analysis/pacing167-verification.json). SamePR109 OPEN. Approved baseline remains boundary165/map02; candidate map04 NOTadopted. Reproduce with --standard-fit only. map05 placement2 rejected-.837. Wide-policy test02 12joint+32fill cases, narrow equiv02 18cases/22outputs incl400000cycle wrap, ARM01/check03 margin1076,16rawABORTnibblesPASS. No newIO/ASM/SDpackage or hardware result. All failed candidates and source-pin addendum preserved. Next avoid tiny counter/seed/refit loop; target CHECK region.

---

# NES166 실기01 — 반복 fill 취소 구간 확인

NES166도 무영상 증상은 동일했으나, BEGIN383/ABORT383/END0/COMMIT0으로 프레임 완성 전 반복 취소를 확인했다. 첫·마지막 취소 이유4는 CHR fill 실패 요약이며 세부 오류는 미확정이다. 첫 프레임은 총1508개 데이터 레코드 중 CHR36바이트를 받았다. ROM 오류0, RUN60010ms, STOP·기본 코어 복구·메뉴 준비는 로그상 완료됐다.

실기 결과가 가리킨 fill/arbiter의 vblank 사용권 대기와 MCU 소비 지연을 선택된 설정으로 재현한다. 사용권 획득 전 대기·획득 후 응답 watchdog·전송 대기를 구분하고, CPU/PPU 우선순위와 전체 유한 상한·취소 drain을 보존해 필요한 경로만 수정한다. 세부 fill 오류는 기존 ABORT 경로에 최소한으로 전달한다. 일괄 timeout 확대나 별도 범용 진단 대신 수정된 SMB3 실기로 복귀한다. 같은166·044·무변경 FIT는 반복하지 않는다. 이후 AV 품질→장기 플레이/물리 리셋 로그→입력 유지 순서를 유지한다.

[결과](../../docs/nes-game166-hardware01.ko.md) · [근거](../../analysis/game166-hardware01-verification.json). PR109 OPEN/same branch. First/last export4 != proven fill4 timeout; intermediate reasons unknown. First1508 includes36CHR (1472geometry). 130ms host BEGIN→ABORT is not fill-only elapsed. SNES display not reached; no newFW/RTL/package this result turn. Prior166 archives remain immutable.

---

# NES166 — 최소 영상 수신 기록 실기 대기

NES166 시험판을 준비했다.165와 동일한 FPGA에서 영상 시작·완성·취소·승인과 첫 취소 이유를 기록한다. WRAM 잔존 데이터 상태에서도 첫 SNES 화면은 정상이며, 느린 진행의 기존 대기 제한 취소는 모델로 재현했다. 실기 원인은 아직 미확정이고 영상 복구판은 아니다.

NES GAME 166.nh1 실기 실행 후 nes-progress-166.txt/nes-game-last-166.txt로 BEGIN 부재·반복 ABORT·승인/표시 정체를 구분한다. 검정 화면이면 촬영·조작 불필요. 새 범용 진단·임의 timeout 확대·CPU 우선순위 변경·044 반복 대신 확인된 경로만 고쳐 SMB3 AV로 복귀한다.

[계약](../../docs/nes-trace166-contract.ko.md) · [검증](../../analysis/trace166-verification.json). SamePR109 OPEN. SELECT arm02/armcheck04/test03/wait02/release02;48Btrace/static26520/free38904/RUN37320/IRQ508/margin1076. Original165 FPGA exact ca2b3bfe, newFW b520a229, package cebf7987. WRAM128KiB dirty first image61184pixels/45ACK/BEGIN-END-COMMIT1 ABORT0. Slowwait models prove possibleabort NOT hardwarecause. Firstreason1 combineslease/enable/total;reason4 fillsummaryonly. No clock/FPGA/timeoutchanges;noSDwritesduringRUN. Failed sandboxDLL/hostID and Unicodewait01 preserved;wait02/test03 actualPASS. armcheck02 relocation fingerprint failure reviewed13bodies;armcheck03PASS. Completed archives immutable.

---

# NES165 실기01 — 영상 미출력 분석

NES165 첫 실기에서 사운드·60초 종료·메뉴 복귀는 통과했으나 영상은 출력되지 않았다. 표시 완료0, ROM 오류0, native_result=1이다. 수신 오류21은 시간 만료의 부수 결과일 수 있다. 긴 정상 대기가 fill/export 취소로 이어지는지와 취소 이유 누락을 우선 조사한다.

[실기 결과](../../docs/nes-game165-hardware01.ko.md) · [근거](../../analysis/game165-hardware01-verification.json). PR109 OPEN, same branch. RUN60020ms/tick, ROM393216checked, STOP/base/menu pass. Finalflags1 is postSTOP, not RUNstall. Receiver21 is false-transfer/status wrapper and runtime first cause deadline1. ABORT reason currently discarded; not yet proven why no COMMIT. Primary hypothesis WAIT131072 (~6.1ms) includes legal outside-vblank/host stalls. No newfirmware/FIT/SD this result turn; preserve previous evidence.

같은165 재시험 대신, vblank만 허용하는 CHR fill의 WAIT131072와 MCU backpressure를 재현한다. BEGIN/END/ABORT/COMMIT 횟수·첫 취소 이유를 보존해 수신 단계와 취소 원인을 구분한 뒤 필요한 경로만 고치고 SMB3 실기로 확인한다. 상한 무조건 확대·CPU/PPU 우선순위 해제·044 반복은 하지 않는다. 영상 복구 후 AV 품질→장기 플레이/물리 리셋 로그→입력 유지 순서를 유지한다.

---

# NES 현재 인계 — 새 영상 경로 실기 시험 대기

PR109 OPEN / codex/nes-native-runtime-165. [계약](../../docs/nes-coupled165-contract.ko.md) · [실기 안내](../../docs/nes-game165-instructions.ko.md) · [결과](../../analysis/coupled165-verification.json).

NES165 SMB3 실기 시험판을 준비했다. 새 영상 경로의 MCU→실제 SNES 표시 ACK 결합을 통과했고, RUN 전용 버퍼로 메뉴·GBC의 RAM 여유를 회복했다. 전체 ARM 링크와 RUN/IRQ 스택 검토·기존 FPGA 배치의 ASM을 완료했다. 화면 속도·사운드·메뉴 복귀의 새 실기 결과는 아직 미확인이다.

SELECT FPGA boundary165/map02 unchanged + coupled165/asm01; MCU coupled165/arm01 / armcheck02; coupled test05; release02. RUN-only noinline workspace33952B, stack bound37320+IRQ508/free38952/margin1124, static26472. save_report4864 restored outside RUN. Scalar errors survive, receiver/video/io NULL before return. 86 reachable functions/callback and reviewed library/IRQ fingerprints; not all menu formal proof or measured highwater. Exact45SNES ACK x2/61184pixels each; normal1frame, deadline-at-SEAL0frames despite visible image. Filebus/native191capture model, NOTphysical. Test01 DLL/02dotnet/03Unicode invalid;04pass;05final. No newFIT/FLOAT. ASM/CPF preserves selected baseline/archive. Package702ca2f7, firmware0093c48e, FPGAca2b3bfe. PrivateROMnoGit,164rollbackexact,saveSRAMreserved. Conditional external IO/MTBF24syncreset remains.

새 NES165-SMB3-NATIVE-VIDEO 시험판으로 제목→월드맵→첫 레벨 이동·점프·사운드·화면 속도와 메뉴 복귀를 확인한다. nes-progress-165.txt/nes-game-last-165.txt 및20~30초 영상을 받기 전에는 또 다른 범용 진단이나 무변경 FPGA FIT/전체 부팅을 반복하지 않는다. 실패하면 최초native_result/receiver/sink/video/ROM 오류에 따라 실제 경로만 수정한다. AV가 확인되면 장기 플레이와 오류/물리 리셋 로그, 입력 유지 품질 순서로 진행한다. 044 복원 시험은 반복하지 않고 필요시 동봉164로 복원한다.

Do not use old runtime165/arm02 (permanent34KB allocation) for the SD pair. Newmaterializer wraps it then replaces adapter/log lifetime; preparation-runlease165.json is final. Newchecker pins actual compiler/platform; code/compiler/binding changes require fresh review, not automatic margin reuse. Long-play/physicalresetlogs deferred untilAV hardware outcome. Completed evidence/finalizers immutable.

---

# NES 현재 인계 — MCU native 영상 루프 전체 링크

PR109 OPEN, 같은 codex/nes-native-runtime-165 브랜치. [계약](../../docs/nes-runtime165-contract.ko.md) · [결과](../../analysis/runtime165-verification.json).

165 새 영상 경로를 실제 MCU 게임 루프에 연결하고 전체 ARM 링크를 통과했다. 수신→변환→SNES 표시 ACK 후 다음 프레임을 처리한다. 로그 스택은4864→768바이트로 줄였고, 정적RAM60424/65424바이트·여유5000바이트다. 명시적 RUN 호출 경로의 스택 합계3120바이트는 전체 IRQ/메뉴 경로 승인이 아니다. FPGA는boundary165/map02 그대로이며 새SD·실기·60fps는 아직 미확인이다.

SELECT FPGA boundary165/map02/reproduce02 unchanged;MCU runtime165/arm02. Full ARM196052B; RAM includes ahbram=60424/65424/free5000. Native receiver18064/video15888 union log4096/runtime100. save_report4864->768;listed foreground3120 is NOT whole-program/IRQ bound. New runtime10cases+invalidarg, native191transactions + synthetic sink45ACK, no retry. No new actualSNES/physical/FLOAT/FIT. Source1393copied/7changed/13added. Strict74/E6v2/E5/D6/F6;clocktick6000;RUN noSD;existing reset-beforeSTOP/CF86 failclosed.

runtime165/arm02의 실제 RUN/오류/STOP/메뉴 복귀와 SysTick·라이브러리·일반 메뉴/GBC를 포함한 스택 여유를 먼저 확인한다. 필요하면 수명이 겹치지 않는 MCU 버퍼 공유로 해결하며 세이브 SRAM은 사용하지 않는다. 이어 실제 SNES ACK와 MCU 시간/오류 서비스의 최소 결합 시험만 수행하고, 선택 boundary165/map02와 쌍을 이룬 SMB3(J) 첫 레벨 시험판을 만든다. 변경 없는 FPGA 재배치·전체 ROM/부팅/A-B/044 반복은 하지 않는다. 60초는 tick 기준6000이며 장기 플레이/물리 리셋 로그는 AV 실기 확인 후 진행한다.

Actual run adapter src/nes/firmware/nes_runtime_board165.inc; materializer tools/nes_runtime165.py uses private164 evidence ARM, not old public generic include. Native synchronous conversion callbacks upload patterns and call guard between transactions. Never call observer SPI recursively inside SPI engine. video/log union only after runtime terminates; use copied error scalars. Stop/report paths and other cores still need stack/IRQ review. Do not substitute timing-loop counts for ticks, or mark ID/ACK model as physical execution. Keep 164/GBC/saveSRAM. test01/armcheck01 environment;armcheck02 CRLF;armcheck03 excludes ahbram INVALID;use armcheck04/test04. Completed archives/finalizers immutable.

---

# NES 현재 인계 — 영상 IO·CDC 리셋 경계

PR108 merged6073122. 새 브랜치 codex/nes-native-runtime-165. [계약](../../docs/nes-boundary165-contract.ko.md) · [검증](../../analysis/boundary165-verification.json).

165 영상 경로 진척: 새 영상 mailbox·SPI 수신부의 리셋을 각 클록에서 해제하도록 수정했다. 내부 setup+0.158ns/hold+0.143ns, 14977LE/961LAB/35M9K와 조건부 IO 지연 검사를 통과했다. 영상 데이터·제어부의 음수 recovery/removal 경로는 1197개에서0개로 줄었다. 선택 boundary165/map02/reproduce02. MCU 통합·full-link·새 실기는 미완료이며 새SD는 없다.

SELECT boundary165/map02/reproduce02. Two RTL/59unchanged;2FIT;map01 raw-resetOR rejected, map02 purelocal release adopted. NEW450deliveries72resets12halt/6phases+wrongreset negative;SPI1717records/47blocks/12489wireB x2 exact. Firstfanout11;native payload rawnegative1197->0;remaining24 release/fault sync paths explicitly OPEN, not falsepathed. PSRAM conditional+2.935ns/SNES77.411ns/SPI163.821ns. Not fullIO/MTBF/MCU/60fps/hardware. Original routed copy exact;archives immutable.

NEXT boundary165/map02를 기준으로 실제164 MCU 게임 루프에 수신→PREPARED→COMMIT→영상 변환→패킷→SNES 표시 ACK→consumed를 연결한다. 식별자74/E6 version2/E5/D6/F6를 정확히 검사하고 기존 CF86·사운드·입력·STOP·메뉴 복귀를 유지한다. SPI를 잡지 않은 경계에서 시간/오류를 서비스하고 반복 횟수 대신 단조 경과 시간을 사용한다. RUN 중 SD 기록은 금지하고 안전한 STOP 뒤 기록한다. receiver18064B+video15888B와 기존 전역·스택을 실제 ARM full-link로 확인한다. 필요한 새 경계 시험 후 SMB3(J) 첫 레벨 실기로 진행하며 기존 ROM 쓰기·부팅·A/B·044 반복 및 무변경 refit를 추가하지 않는다. 기존 전기적 E1/E2·MTBF·클록 정지 한계는 조건부 위험으로 계속 명시한다.

MCU code map: src/nes/firmware/nes_native165 (receiver), nes_native_video165 (conversion), nes_native_sink165 (packet/ACK), nes_sink_spi165 (E0/E1), tools/nes_native_spi165.py::bulk_engine (bounded1..259B SPI). Actual164 RUN baseline is probes/nes-game164/evidence/arm/src/nes_run136.inc, not the older public generic include. Keep one caller-owned receiver+video; no duplicate full candidate/table readback and no cartridge SRAM. A synchronous build/seal must call guard/time/STOP between transactions; do not invoke SPI service recursively while SPI ownership is held. ID mismatch/CRC/ambiguous ACK -> STOP/reset, no blind retry. Final consumed only after display ACK. Full ARM link/stack must replace estimates before packaging.

Keep164/GBC/saveSRAM. No SD created; completed record/audit/archive immutable.

---

# NES 현재 인계 — 상태 직접 저장·읽기 캡처

PR108 OPEN. [계약](../../docs/nes-directstate165-contract.ko.md) · [검증](../../analysis/directstate165-verification.json).

165 영상 경로 진척: 로더 상태를 직접 저장하고 ROM 읽기의 데이터 캡처 허용을 분리했습니다. 실제 내부4클록·3조건의 setup/hold가 모두 통과했다. 최악 setup+0.094ns, hold+0.120ns,15010LE/959LAB/35M9K이며 다음 연결 작업의 기준으로 채택한다. 선택 directstate165/map01/reproduce01. 외부IO·영상CDC/reset·MCU 연결·실기는 미완료이며 새SD는 없습니다.

직전 상태 피드백−0.597ns는+1.380ns, ROM 읽기 캡처−0.429ns는+1.324ns로 개선됐다. 새 capture 예측 경로도+1.499ns다. 실제 상태 레지스터는0/1/2/3/4/5/7/8의8개이며 숫자 state와 출력에 기여하지 않는FAILED 비트 및 도달 불가9..15 비트는 최적화됐다. capture_low/high2개는 독립 레지스터로 남았다. 전체 최악 경로는 CHECK 응답 주소→SPI 오류 코드+0.094ns로 여유가 작지만 실제 주기에서 setup/hold를 만족한다. 더 엄격한5.5ns 배치 목표는−0.358ns로 여전히 미달이며 실제 주기5.952ns 통과와 구분한다. 원래 클록을 늦추거나 false path를 추가한 결과가 아니다. 전체IO/CDC 및 실기는 아직 승인하지 않았다.

NEW loader294912/1056/all16codes/onehot+terminal/STOP+unused negatives;reader120reads126cancel5stoppedreset;READ16pins16phase70ns/110ns+noHOLDnegative;actualSPI219wire1125909edges100READ7ACK19bad72cancel2priorityPASS.59inputs exact/reproduce01/localrelease4/12PASS;oneFIT. UnchangedSPI393741/120 andMCUgap reused. Fixture01 wrongrefdut identifier/joint01 missingreference compile preserved;loader02/reader01/joint02/pins01 final. SELECT directstate165/map01/reproduce01;adopted=True;nominalpass=True.

NEXT 선택 기준을 directstate165/map01/reproduce01로 변경한다. 양수 여유를 더 늘리기 위한 미세 논리·seed·무변경 refit는 중단한다. 먼저 동일 배치에서 외부54입력/57출력과 혼합 클록 경로를 PSRAM70ns/SNES/MCU-SPI/영상 mailbox/reset으로 분류하고 기존 보드 근거를 재사용할 수 있는 범위를 확인한다. 실제 새 경계의 요청/응답 데이터 안정성·ACK 소유권·공통 reset/STOP 회수 및 필요한 지연 제약을 점검한다. 그 다음 MCU에 실험 SPI0x74와 E6/version2 상태73·E5관측70·E0/F6 패킷 수신/변환/SNES ACK를 연결하고, 기존 사운드·입력·경과시간·STOP 서비스를 유지한다. full-link/stack과 최소 변경 경계 검증 후 SMB3(J) 첫 레벨 실기 패키지로 넘어간다. 새로운 일반 진단체계나 전체 ROM/A-B/044 반복을 선행 조건으로 추가하지 않는다. 변경으로 배치가 달라질 때만 해당 완성 후보의 전체 타이밍을 다시 확인한다. 내부 통과만으로60fps·실기 안전성·장시간 입력 유지를 완료 처리하지 않는다. 설치164/GBC/세이브 SRAM은 보존한다.

완료 archive/finalizer/public pins 불변. 설치164/GBC/saveSRAM 보존; 새SD 없음.

---

# NES 현재 인계 — 명령·카운터 갱신

PR108 OPEN. [계약](../../docs/nes-update165-contract.ko.md) · [검증](../../analysis/update165-verification.json).

165 영상 경로 진척: SPI 명령 종류를 수신 시 저장하고 로더 종료 판정을 카운터와 같은 클록에 갱신하도록 분리했습니다. 명령 수신+1.458ns·명령 종류→주소검사+3.821ns·종료비트→적재카운터+1.603ns로 세 목표 경로는 통과했다. 그러나 최악 경로는 state[0]→state[2] −0.597ns로 이동했다. 상태 해석→destination 재인코딩→상태 갱신의5논리단계/6.472ns 중 배선4.111ns(64%)이며, 같은 상태 피드백의 실패 전이 경로도7단계/−0.520ns다. 별도로 READ16 read_last→data_hold enable은1논리단계지만5.048ns 배선(80%)/−0.429ns여서 상태 한 경로만 수정해서 끝날 상황이 아니다. 기존 채택 기준 phaseguard−0.083ns보다 나쁘므로 후보를 채택하지 않는다. 선택 phaseguard165/map01/reproduce01; 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

NEW loader294912/1056/all16codes/terminal invariant+negative;NEW SPI393741/120/4negatives+219wire1125909edges100READ7ACK19bad72cancel2priority/invariantsPASS.59otherinputs exact/reproduce03/localrelease4/12PASS. map01 generatorguard/map02 declaration failure preserved;map03 final/onlyoneFIT. MCUgap reused;no new latency over destination/ID74/C0C1C2/valid-onlypayload/SS2us. SELECT phaseguard165/map01/reproduce01;adopted=False;nominalpass=False.

NEXT 이번에 통과한 SPI 명령 수신·명령 종류·terminal 경로를 다시 미세 조정하지 않는다. 다음에는 실제 state→Equal→destination→state 경로를 기준으로 상태 판정의 등록/상태 표현 변경을 검토한다. 단순 ONE_HOT 옵션 재시도 대신 중복 decode와 실패 전이의 공유를 줄이는 RTL 후보의 논리 깊이·추가 FF·모든16개 상태 코드의 의미를 먼저 명시하고, STOP/오류 코드/쓰기 배출/reset의 같은 클록 동작을 유지한다. READ16 read_last→data_hold enable의 긴 배선도 동시에 검토하며, 필요하면 같은 값을 유지하는 지역 복제 레지스터를 후보에 포함하되 읽기 샘플 시점은 바꾸지 않는다. 기능·전체 배치·모든 내부 클록 setup/hold를 통과한 뒤 필요한 외부IO·영상CDC/reset 및 MCU RUN/시간/사운드/입력/STOP/full-link/stack을 연결하고 최소 SMB3(J) 첫 레벨 실기로 넘어간다. 새 SD 패키지는 아직 만들지 않는다.

완료 archive/finalizer/public pins 불변. 설치164/GBC/saveSRAM 보존; 새SD 없음.

---

# NES 현재 인계 — 목적 상태별 전이

PR108 OPEN. [계약](../../docs/nes-destination165-contract.ko.md) · [검증](../../analysis/destination165-verification.json).

165 영상 경로 진척: 로더의 공통 상태 선택을 목적 상태별 병렬 전이식으로 분리했습니다. BEGIN→상태는−0.136ns/7단에서+0.331ns/6단으로 개선됐고 실제 상태 레지스터4개를 확인했다. 전체15022LE/963LAB/35M9K, 최악−0.160ns(command[6]→pending_causes[1])로 기존 선택−0.083ns보다 나빠 미채택이다. remaining→loaded_bytes−0.123ns, byte_count→command−0.109ns, state→error_code−0.031ns도 남아 한 경로만의 문제가 아니다. 선택 phaseguard165/map01/reproduce01; 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

NEW loader294912states/1056sequences/all16codes/STOP+unused negatives;NEW joint219wire1125909edges100READ7ACK19bad72cancel2priorityPASS. Unchanged SPI393741/120/3negatives and MCUgap reused.60otherinputs exact/independent reproduction/localrelease4/12PASS. No latency/clock/SDC change over pulsejoint, ID74/C0C1C2/valid-onlypayload/SS2us retained. SELECT phaseguard165/map01/reproduce01;adopted=False;nominalpass=False.

NEXT 선택 phaseguard165/map01/reproduce01은 유지한다. destination165/map01은 상태 경로가 개선된 구조 검토용이며 채택·배포 기준이 아니다. 이번 병렬 상태 전이와 통과한 SPI 최종 실행 허용은 재수정하지 않는다. 다음은 실패 경로3개(command→주소검사, byte_count→command, remaining→loaded_bytes)의 실제 레지스터 갱신 조건을 함께 검토한다. SPI 첫 명령 바이트 수신 시 offset 검사 종류를 함께 등록하고 명령 레지스터의 소유권/갱신 허용을 분리하는 구조, 로더 terminal 판정을 동일 클록의 next-remaining과 일치하도록 유지하는 구조를 우선 검토한다. 단순한 사전 샘플링으로 live length·ready·fault를 늦추거나 WRITE/HOLD·STOP/리셋 시점을 바꾸지 않는다. 새 보조 레지스터는 실제 SPI 및 쓰기 시퀀스에서 불변식을 확인하고, 직접 상태 주입 시험에서도 관련 값을 일치시킨다. 변경 경계 검증 후 한 번 전체 배치하고 세 실패 경로와 state→error_code를 모두 확인한다. 같은 소스 refit/seed·속성 탐색이나 최악 경로 하나만 바꾸는 반복은 생략한다. ID74/C0C1C2/valid-only payload/SS high·setup2µs 계약을 유지한다. 내부 조건이 갖춰지면 필요한 외부IO·영상CDC/reset와 MCU E6/version2 상태73·E5 관측70·E0/F6 수신·변환·ACK, 사운드·입력·STOP·시간 및 full-link/stack을 연결하고 최소 SMB3(J) 첫 레벨 실기로 간다. 설치164/GBC/세이브 SRAM 보존; 새SD 없음; 전체ROM·A/B·044 반복 생략.

완료 archive/finalizer/public pins 불변. 설치164/GBC/saveSRAM 보존; 새SD 없음.

---

# NES 현재 인계 — 명령별 실행 허용

PR108 OPEN. [계약](../../docs/nes-commandpulse165-contract.ko.md) · [검증](../../analysis/commandpulse165-verification.json).

165 영상 경로 진척: BEGIN·DATA·END·START·STOP·CHECK READ 허용을 앞 단계에서 등록하고, STOP 처리를 상태별로 판정하는 로더와 결합했습니다. 6개 실행 허용 레지스터를 실제 배치에서 확인했다. 15055LE/963LAB/35M9K, 실제 최악 setup-0.136ns; load_begin → state.WRITE. 응답→BEGIN +0.831ns, 오류→DATA +1.592ns, 명령→사전 허용 +1.936ns. 선택 phaseguard165/map01/reproduce01, 내부 실제클록 통과=False. 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

6pulse approvals registered C1, live fault gated C2; no additional latency over commandstage. Experimental74/valid-only payload/SS2us contract retained.393741result+120boundary includes immediate fault-edge pulse assertion;219wire/100read/7ACK/19bad/72cancel/2priority;3wrongRTL rejected. Same-edge equivalence to phaseguard NOTclaimed. map01 60unchanged/map02 59unchanged/independent reproduce/6routedFF/localrelease4/12PASS. map02 SPI393741/120/3negatives reuse map01;guardloader294912/1056 reuse RETIRECE02;NEW combined219wire1125909edgesPASS. MCUgap prior evidence reused;no new game/fullMCU/IOCDC approval. SELECT phaseguard165/map01/reproduce01;adopted=False;nominalpass=False.

NEXT 기준 phaseguard165/map01/reproduce01을 유지한다. 이번 map02는 후속 구조 검토용이며 채택한 배포 기준이 아니다. 잔여 load_begin → state.WRITE (-0.136ns)은7단 LUT이며 data delay6.013ns 중 배선4.030ns(67%)다. 응답 주소→실행 허용과 STOP은 통과했으므로 다시 손대지 않는다. 다음은 로더의 공통 다음 상태 선택망을 WRITE/RECEIVE 등 목적 상태별 전이식으로 분리하는 한 후보를 검토한다. WRITE/HOLD drain·STOP·같은클록 오류·미사용4비트 상태의 기존 결과를 보존하고 변경 경계 비교 및 결합SPI 시험을 통과한 뒤 한 번 배치한다. 자동 상태 인코딩이나 속성만 바꿔 우연히 좋아지기를 기대하는 무변경 refit는 하지 않는다. 실험ID74/C0캡처-C1판정-C2실행/valid=0 payload 비관찰/SS high·setup2µs 계약과 같은클록 fault 우선순위를 보존한다. 후속 MCU는 정확한 식별자를 검사하고 E6/version2 상태73·E5 관측70·E0/F6 수신/변환/ACK, 사운드·입력·STOP·경과시간과 full-link/stack을 연결한다. 최소 조건을 갖추면 SMB3(J) 첫 레벨 실기로 진행한다. 설치164·GBC·세이브 SRAM 보존; 전체 ROM 쓰기·A/B·044 반복 생략.

완료 archive/finalizer/public pins는 불변이다. 설치164/GBC/saveSRAM 보존.

---

# NES 현재 인계 — 명령3단계와 데이터 선준비

PR108 OPEN. [계약](../../docs/nes-commandstage165-contract.ko.md) · [검증](../../analysis/commandstage165-verification.json).

165 영상 경로 진척: 실제164 MCU의 SPI 전송 간격을 확인하고 명령 캡처·판정·실행을3단계로 분리했습니다. FPGA1클록 추가, 두 후보의 기능·실제SPI 상태 응답 검증 통과. map01은 길이→원인 +0.672ns/원인→오류 +2.970ns/원인→카운터 자격 +2.628ns를 확보했지만 응답 주소→load_data -0.332ns가 남았다. map02는 데이터 선준비로 쓰기 허용 경로와 분리했다. 마지막 결과 15009LE/962LAB/35M9K, 전체 최악 -0.204ns; check_request_tag[6] → load_begin. 선택 phaseguard165/map01/reproduce01, 내부 실제클록 통과=False. 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

SPI1클록 지연 변경/응답 실험ID74. map01 test03, map02 test04;각393741 거래결과+120취소+219wire/100READ/7ACK/19bad/72cancel/2priority. 같은edge 동등성 아님. map02는 valid=0 payload 관찰 금지;actual loader consumes accepted_valid only. 60입력 불변, 독립재현/지역release4/12PASS. test01 negative fixture 결함과 test02 수정 소스·로그 보존. 기존 loader/counter 근거 재사용, 전체 게임/MCU/IOCDC 승인 아님. SELECT phaseguard165/map01/reproduce01;adopted=False;nominalpass=False.

NEXT 선택 phaseguard165/map01은 유지한다. 명령3단계의 외부 지연 허용 가능성은 확인됐으므로 같은 MCU 간격 조사를 반복하지 않는다. 다음은 실제 잔여 경로 check_request_tag[6] → load_begin (-0.204ns)의7단 LUT 경로를 기준으로 C1에서 명령별 실행 허용 비트를 각각 등록하고 C2의 공통 오류 차단 뒤 최종 명령 재디코딩3단을 제거하는 후보 한 개를 검증한다. 오류 우선순위를 다음 클록으로 미루거나 응답 검사를 생략하지 않는다. 같은 두 후보의 무변경 배치나 작은 조합식 탐색은 반복하지 않는다. 실험 SPI 식별자74는 아직 설치용으로 승인하지 않았다. 후속 MCU는 기존6b를 묵인하지 말고 정확한 후보 식별자를 확인하고 SS high/setup 2µs 계약을 유지해야 한다. E6/version2 상태73·E5 관측70·E0/F6 수신/변환/ACK, 사운드·입력·STOP·경과시간, full-link/stack을 연결한 뒤 SMB3(J) 첫 레벨 실기로 간다. 설치164·GBC·세이브 SRAM 보존; 새SD 없음; 전체 ROM 쓰기·A/B·044 반복 생략.

완료 archive/finalizer/public pins는 불변이다. 설치164/GBC/saveSRAM 보존.

---

# NES 현재 인계 — CHECK 갱신 허용 입력

PR108 OPEN. [계약](../../docs/nes-retirece165-contract.ko.md) · [검증](../../analysis/retirece165-verification.json).

165 영상 경로 진척: CHECK 카운터의 오류 차단을 전용 갱신 허용 입력으로 분리하고 로더 상태별 명령 판정과 결합했습니다. 전체 타이밍 개선이 없어 기존 개발 기준을 유지합니다. 선택 phaseguard165/map01/reproduce01; 마지막 후보 15048LE/962LAB/35M9K, 실제 클록 최악 setup-1.974ns. 전체IO·CDC·MCU·실기는 미완료, 설치164와 세이브 SRAM 보존, 새SD 없음.

map01은 오류→카운터+1.364ns와 길이 비교+0.209ns를 달성했지만 load_valid→상태−0.336ns가 남았다. map02는 오류→카운터+0.922ns, 길이+0.467ns, STOP→상태+0.723ns로 세 경로를 통과했고14999LE/960LAB을 사용했으나 상태→오류 코드−0.265ns가 최악이었다. map03은 그 오류 코드 경로도+0.665ns로 개선했지만 SPI fault→pending_causes[2]가−1.974ns로 악화됐고15048LE/962LAB을 썼다. 세 후보 모두 기존 전체 최악−0.083ns보다 좋지 않아 미채택이다. 기능 비교와 세 번의 결합 SPI 시험은 통과했지만 전체 타이밍 개선은 달성하지 못했다. map03 추가 경로 보고서의 최초 호출은 작업 디렉터리가 잘못되어 스크립트를 찾지 못했다. 실패 로그를 보존하고 올바른 경로로 STA 보고서만 실행했으며 RTL·배치를 재실행하거나 바꾸지 않았다.

SELECT phaseguard165/map01/reproduce01;adopted=False;nominalpass=False. SPI786432counter+393741capture/faultnegative;three candidates actualSPI100reads7ACK19bad72cancel2overlap. map02loader exactreuse294912/1056;map03error-code owner NEW294912/1056+STOP/code negatives;newcombinedSPI confirmed. Counter19ON/19routedena;explicit IMPLEMENT hint absentMAP, don't claim applied. Original60unchanged map01/59map02-03;local4release12pathsPASS. Preserve164/GBC/saveSRAM;no newSD/fullIOCDCreset/MCU approval. Completed archives/finalizers/publicpins immutable.

NEXT 선택 phaseguard165/map01/reproduce01을 유지한다. 개별 조합식 수정→전체 재배치만 반복하는 방식은 중단한다. 다음에는 실제 MCU SPI 프레임 간격과 SS/SCK 겹침·응답·ACK·STOP/reset 계약을 먼저 확인해, 명령 캡처와 실행 자격 판정을 명시적인 여러 클록 단계로 나눌 수 있는지 검토한다. 이것은 기존 같은 클록 처리 계약을 바꾸는 설계이므로 단순한 동등성 주장이나 false path로 넘기지 않는다. 외부 응답 지연 한도, queued 명령 중 오류·STOP 우선순위, 새 프레임의 fail-closed 처리와 식별 버전/MCU 호환성을 정의하고 변경 경계 시험을 통과한 구조만 한 번 배치한다. 추가 지연을 허용할 수 없다는 근거가 나오면 그 결과를 남기고 공통 오류 신호의 지역화 대안을 선택한다. 이번3후보·이전 length165/STOP 분리·무변경 fit/전체ROM 쓰기는 반복하지 않는다. 내부 타이밍 이후 필요한 외부IO/영상CDC/reset와 MCU E6/version2 상태73·E5 관측70·E0/F6 수신/변환/ACK·사운드·입력·STOP·경과시간을 연결해 SMB3 첫 레벨 실기로 진행한다. 설치164/GBC와 세이브 SRAM은 보존한다.

---

# NES 현재 인계 — 적재 길이 비교 구조 개선

PR108 OPEN. [계약](../../docs/nes-length165-contract.ko.md) · [검증](../../analysis/length165-verification.json).

165 영상 경로 진척: 적재 길이 비교와 STOP 상태 판정을 개선하는 세 후보를 검증했습니다. 전체 타이밍 개선을 확인하지 못해 채택하지 않았습니다. 선택 구현 phaseguard165/map01/reproduce01의 기존 최악 setup−0.083ns를 유지합니다. 마지막 후보 15042LE/960LAB/35M9K, 실제 클록 setup-0.410ns. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

map01(15039LE/960LAB)은 기존과 같은−0.083ns였다. map02(15029LE/963LAB)는 numeric keep 적용으로 길이 비교가5단/+0.258ns가 됐지만 STOP→state가−1.010ns로 악화됐다. map03(15042LE/960LAB)은 상태별 명령 판정으로 STOP→state를−0.115ns로 회복했고 길이 비교는+0.444ns였으나 check_failed→check_next[17]가−0.410ns로 최악이 됐다. 세 후보 모두 기존 전체 최악−0.083ns보다 좋지 않아 채택하지 않았다. 숫자 keep의 적용과 특정 경로 개선은 확인했지만 전체 타이밍 해결이나 프레임 속도 개선을 달성했다는 뜻은 아니다. map03 검사기의 설명문만 잘못 상속된 것을 수정하고 같은 결과를 재검증했으며, 수정 전 검사기·결과도 별도 보존했다. 기능 및 배치 재실행은 하지 않았다.

SELECT phaseguard165/map01/reproduce01; adopted=False;candidate_nominal_same_clock_pass=False. Live combinational equality/no added latency;393741capture-retirement+actualSPI100reads7ACK19bad72cancel2overlap PASS/uppergroupnegative. map03 state-only command factoring NEW294912+1056/wrongSTOPnegativePASS;SPI component evidence reused by exact attribute normalization. NO new combined map03 replay.60otherinputs exact perstep/59vsoriginal/local4release12pathsPASS. Quartus keep uses numeric1: verify all14nodes inMAP settings and routednames;stringtrue map01 had no such assignments, do not assume sourceattribute honored. All3candidates NOTadopted; baseline-.083 retained. No full-ROM/game/MCU/SD/fullIOCDCreset approval. Preserve164/GBC/saveSRAM and completedarchives/finalizers/publicpins.

NEXT 선택 phaseguard165/map01을 기준으로 진행한다. 이번 numeric keep의 비교 경계 효과와 map03의 상태별 판정은 실험 근거로만 재사용한다. 다음에는 check_failed의 CHECK 카운터·상태·오류 처리 팬아웃과 START/STOP 우선순위를 함께 읽고, 명령 완료 시점과 오류 대응을 바꾸지 않는 공통 자격 신호/다음 상태 구조를 설계한 뒤 변경 경계 동등성 시험과 한 번의 배치로 평가한다. 같은 세 후보의 무변경 재배치, 이전 STOP 저장 레지스터 분리, 클록 완화·false path 추가는 반복하지 않는다. 내부 타이밍 통과 후 필요한 외부IO/CDC와 E6/version2 상태73·E5 관측70, E0/F6 수신·변환 ACK 및 사운드·입력·STOP·경과시간 MCU 연결을 마무리해 SMB3 첫 레벨 실기로 간다. 불필요한 전체 ROM 쓰기와044 복원 반복은 생략한다.

---

# NES 현재 인계 — 타이머 상태의 명령 조건 단순화

PR108 OPEN. [계약](../../docs/nes-phaseguard165-contract.ko.md) · [검증](../../analysis/phaseguard165-verification.json).

165 영상 경로 진척: 로더 SETUP·RELEASE의 중복 명령 충돌 조건을 제거하고 동작을 비교했습니다. 새 개발 기준으로 채택했습니다. 선택 구현 phaseguard165/map01/reproduce01. 후보 15039LE/960LAB/35M9K, 실제 클록 setup-0.083ns. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

첫 후보 map01은 START→상태 최소 setup을 -0.092에서 +0.805ns로 개선했다. 전체 최악 setup은 -0.083ns, 최소 hold는 +0.130ns이며 15039LE/960LAB/35M9K다. 메모리 이외 host/NES/board setup은 +1.139/+8.144/+121.793ns다. 종전 state165의 -0.092ns/963LAB보다 좋아 map01을 채택한다. 남은 최악 경로는 loaded_bytes[6]→pending_counter_clear이며 equality4단과 자격 결합2단, 데이터 지연5.956ns다. SPI STOP 조건을 별도 저장한 map02는 기능 비교·연결 시험과 FIT를 통과하고15001LE/960LAB을 썼지만, 요청 태그→CHECK 카운터 경로가 -0.449ns로 악화되어 채택하지 않는다. 실기 배포나 전체 타이밍 통과는 아니다.

SELECT phaseguard165/map01/reproduce01; adopted=True; nominal_same_clock_pass=False. Timed-state redundant conflict removal only; fault/error/data/timer and WRITE/HOLD drain unchanged. All16state codes/294912conditions/1056one-byte sequences+STOPnegative PASS.60other inputs exact state165map01. Local4release registers/12setup-hold paths PASS. No full-ROM/game/MCU/SD/fullIOCDCreset approval. Preserve164/GBC/saveSRAM and completed archives/finalizers/publicpins.

NEXT SELECT phaseguard165/map01/reproduce01, not rejectedmap02. Reuse294912loader conditions/1056sequences and exact unchangedSPI/reader evidence. Remaining nominal -0.083ns loaded_bytes[6] -> pending_counter_clear: inspect offset=={5'd0,loaded_bytes} equality depth/partition and static clear eligibility on SAME capture edge. Do not pre-sample loaded_bytes: loader may advance while SPI frame is arriving. Do not repeat rejected STOP operand split map02 (-0.449 tag->check_next), compare165 response-mask/phase/drain variants, unchanged fits/fullwrites/OAM/A-B/044. Preserve state single owner/error priorities/WRITE-HOLD drain, local4release QSF, exact clocks/SDC. After same-clock closure, check necessary native-video held-data/control/reset/externalIO on selected hierarchy; connect MCU E6/version2 status73, E5 observer70, E0/F6 receive-convert-ACK/audio/input/STOP/elapsed-time/full-link/stack then minimal SMB3(J) first-level hardware. Save SRAM remains reserved; no broad debug expansion. Both candidate builds/FLOAT finished. SPI01 connected elaboration failed because old test force targeted a now-wire predicate; SPI02 targets equivalent captured operands and passes, not a hardware/license fault. Preserve failedSPI01 and completedarchives/finalizers/publicpins.

---

# NES 현재 인계 — 로더 상태 전환 분리

PR108 OPEN. [계약](../../docs/nes-state165-contract.ko.md) · [검증](../../analysis/state165-verification.json).

165 영상 경로 진척: 로더 상태 전환을 오류·데이터 처리에서 분리하고 294912조건·1056쓰기/중단 시나리오를 비교했습니다. 새 후보를 다음 구현 기준으로 채택했습니다. 선택 구현 state165/map01/reproduce01. 15077LE/963LAB/35M9K, 실제 클록 setup-0.092ns. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

SELECT state165/map01/reproduce01;adopted=True;nominal_same_clock_pass=False. Single state-owner always;original fault/error/data priority and timer preserved. Empty original state-only branches/tasks intentional. WRITE/HOLD bad command holds current edge then existing fault drains;no pulse shortening. State165test01 all16codes/294912conditions/1056actual single-byte sequences+wrongSTOP negative PASS.60other inputs exact release165map01. Existing4hostrelease QSF assignments/newchain topology PASS. No full-ROM/newgame/MCU/SD or fullIOCDCreset approval. Preserve164/GBC/saveSRAM and completed archives/finalizers/publicpins.

NEXT SELECT state165/map01/reproduce01;state165map01 nominal -0.092ns, worst nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|start -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|state.SETUP. Actual path start->fault~3->phase_step~0->Selector9~0->state~60/61->SETUP:5levels,68percent routing. Also READY->WRITE/RECEIVE -.001ns. Preserve new single-state-owner contract; inspect shared command/timed-phase guard for SETUP hold/entry and those near-zero paths, without assuming START is a legal SETUP entry. No unchanged fit or old compare165 drain/phase/counter repeats, no clock/SDC relaxation. Preserve fault/STOP/write drain and four local release QSF assignments with fresh hierarchy checks. Then minimum IO/CDC/reset+MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and SMB3(J) hardware;no unchanged fullwrites/OAM/A-B/044/saveSRAM.

---

# NES 현재 인계 — 영상 mailbox 리셋 해제 분리

PR108 OPEN. [계약](../../docs/nes-release165-contract.ko.md) · [검증](../../analysis/release165-verification.json).

165 영상 경로 진척: 영상 mailbox 리셋 해제 레지스터4개의 병합을 방지해 지역별 분리를 확인했습니다. 이번 후보는 기존 기준보다 전체 타이밍이 나빠 채택하지 않았습니다. 선택 구현 predecode165/map03/reproduce03final. 후보 15073LE/963LAB/35M9K, 실제 클록 setup-0.583ns. RTL·클록·SDC는 이전 후보와 같으며 기능 시험은 재사용했습니다. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

Only four DONT_MERGE_REGISTER ON assignments to native_records.dr[0:1]/native_prepared.sr[0:1]. All60 other files exact eligibility165map02. QSF readback ON/local4regs/firstfanout1/stage12setuphold PASS. Reuse prior RTL functional evidence;no newFLOAT/game/MCU/SD. Selected predecode165/map03/reproduce03final;adopted=False;whole IO/CDC/reset/MTBF approval still OPEN. Completed archives/finalizers/publicpins immutable. Preserve164/audio/input/saveSRAM.

NEXT SELECT predecode165/map03/reproduce03final;retain release165map01 as isolated-host experiment, not installable. QSF four-release-register isolation verified; nominal -0.583ns worst nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|load_begin -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|state.WRITE. This is a 7-level same-clock load_begin->fault~2->state~43/44/45/52/53/73->WRITE/HOLD path, not the old reader predicate or host release. Inspect independent state-transition equations versus shared fault/error task, preserving exact WRITE/HOLD pulse drain and command conflict/STOP priority. Do not repeat compare165.drain (already rejected), old phase/counter variants, blind refits or global dont_merge/preserve. Reuse four local-release assignments only with new hierarchy timing evidence. Then necessary native-video IO/CDC/reset and MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack, minimum SMB3(J) hardware. No unchanged CHECK/OAM/full writes/A-B/044;saveSRAM reserved.

---

# NES 현재 인계 — 로더 READY 직접 판정

PR108 OPEN. [계약](../../docs/nes-eligibility165-contract.ko.md) · [검증](../../analysis/eligibility165-verification.json).

165 영상 경로 진척: 로더 READY 판정을 단순화하고 reader 마지막 사이클 판정을 미리 계산해 실제 SPI/boot/reader 동등성을 검증했습니다. 전체 타이밍 이득이 없어 새 후보를 채택하지 않았습니다. 선택 구현 predecode165/map03/reproduce03final. 후보 15017LE/963LAB/35M9K, 실제 클록 setup-1.994ns. 외부IO·CDC·MCU 연결과 실기 확인은 남아 있으며 설치164·세이브 SRAM을 보존합니다. 새SD 없음.

SELECT predecode165/map03/reproduce03final;adopted=False. map01 fault path+.919 but reader remaining->data_hold-.856 rejected. map02 adds read_last==(remaining==1) during ACTIVE, prior remaining==2 predicts terminal;sample/CE/OE/ACK/HOLD/RELEASE unchanged. Reader old-register/pin equivalence120reads/126cancel/5stoppedreset at counts1/2/3/16 and two board-count phases;wrongterminal rejected. Loader direct !active_reset&&!fault&&READY equals loaded&&!loader_run&&!boot_fault, used by check_active/check_failed. No new latency or changed write state machine. SPI tag02 executable text reused (one stale comment corrected). New connected sequential PASS TAG165 edges=1271681 reads=124 acks=7 corruptions=19 cancels=72 overlaps=2;1024eligibility combinations +26loader fault points;negative missingfault rejected. Prior conditional1409024/393216 reused,NOTformal/unconditionalproof.57inputs unchanged. No newSD/MCU/game/SNES/IOCDC approval;completedarchivesimmutable.

NEXT SELECT predecode165/map03/reproduce03final. Rejected eligibility165 map02 nominal -1.994ns, worst nes_dac162:audio|dac_release[1] -> nes_live_joint:core|nes_native_spi165:native_spi|held[13]. Mapping explicitly merges native_records.dr[1],native_prepared.sr[1],pad.host_release[1] into audio.dac_release[1]; this is shared reset-release fanout, NOT an audio sample defect. Inspect split/local preserved release and SPI held enable fanout with same-edge handshake/reset/cancel semantics, then check all clocks including memory -.203ns. Reuse READY/reader-terminal/CHECK tests; do not repeat compare165 equations/SPEED, tag165 guarded capture, or unmodified fits. Then necessary native-video IO/CDC/reset + MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and minimum SMB3(J) hardware. No unchanged CHECK/OAM/full writes/A-B/044 or cartridge save SRAM.

User merges; Korean4sections; personalGitHub only. No unchanged CHECK/OAM/fullwrites/A-B/044;saveSRAM reserved.

---

# NES 현재 인계 — CHECK 요청 주소 계약과 배치 결과

PR108 OPEN. [계약](../../docs/nes-tag165-contract.ko.md) · [검증](../../analysis/tag165-verification.json).

165 영상 경로 진척: CHECK 요청 주소를 별도 저장하는 구조와 실제 SPI/reader 중단 경계를 검증했습니다. 전체 타이밍이 기존보다 나빠 새 후보를 채택하지 않았다. 선택 구현 predecode165/map03/reproduce03final. 새 후보 15068LE/962LAB/35M9K, 실제 클록 setup-0.616ns. 외부IO·CDC·MCU 실행 연결은 미완료이며 설치164·세이브 SRAM 보존, 새SD 없음.

map01 guarded tag capture REJECT -0.678ns overall/-0.335 tag feedback. map02 independent capture -0.616ns;adopted=False. SELECT predecode165/map03/reproduce03final. Tag invariant only whilebusy; rejected READ may refresh inactive tag, never launches. Same response-edge address comparison, no early-address stability assumption. Actual SPI/boot/READ16 100reads/7ACK/19corrupt/72cancel/2priority,1026691edges;wrongcapture+missingbit negatives PASS. Conditional1409024state+393216capture are NOTunconditional all-state equivalence/formal proof.60other inputs unchanged. No SD/newgame/ARM/MCU/IOCDC approval. Completed archives/public pins immutable.

NEXT SELECT predecode165/map03/reproduce03final. Tag trial map02 nominal -0.616ns: nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|fault -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|pending_causes[2]. Preserve the established CHECK request-tag invariant and same-edge response rejection. Inspect this actual worst path and all-clock minima before another structural change; do not repeat compare165 local equations/SPEED or tag165 map01 guarded capture. Keep request-tag capture separate from dynamic response errors. Existing129/130/131 rejected phase-counter variants are not a new rationale. Only changed-boundary tests and justified fit, then minimum native-video IO/CDC + MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and SMB3(J). No repeated CHECK/OAM/full writes/A-B/044 or save SRAM.

User merges; Korean4PRsections; personalGitHub only. Keep164/audio/input/saveSRAM. No unchangedfullwrites/OAM/A-B/044.

---

# NES 현재 인계 — 타이밍 후보 미채택, 기존 기준 유지

PR108 OPEN. [후보 비교](../../docs/nes-compare165-contract.ko.md) · [검증](../../analysis/compare165-verification.json).

165 영상 경로 진척: 추가 회로 후보4개와 모듈별 SPEED 설정을 검증했지만 전체 타이밍 개선은 없어 모두 미채택했습니다. 기존 predecode165/map03의15,040LE/963LAB/35M9K, 실제 클록 setup−0.153ns 기준을 유지합니다. 외부IO·CDC·MCU 실행 연결은 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

SELECT remains predecode165 map03/reproduce03final, NOT any compare165 candidate. REJECT map01guardedcompare nominal-.222, map02+drain-.300, map03+splitcauses-.367, map04+parallelfault-.560. All functional/fullfit PASS but overall timing worse. map06 baselineRTL+two SPEED assignments readback accepted/noignored, same15040LE963LAB/nominal-.153;no benefit,notadopted. map05 braces were literal invalidnode warnings;excluded. Do NOT confuse targeted counter+.453 with overall PASS. All clocks/SDC unchanged; no newSD/MCU/ARM or gameboot.

Experiments:1409024counterstates+438272capture AND retirement/Boolean1048576;loader3342336all128timers;actualSPI98/8writes6reads6negative. Negativecontrols wrongaddressbit/missingREADcause/wrongSTOPtransition/missingSTOPfault. Newcause2regs belong rejectedmap03/04 only. Completedfrozen/publicpins immutable; oldbaseline retained exactly.

NEXT Retain predecode165 map03/reproduce03final (-0.153ns); no new RTL/SD selected. Do not repeat compare165 map01-04 or per-instance SPEED map06 (same result), and reject map05 invalid braced-node assignments. Before another full fit, derive a sequential ownership contract for CHECK request tag/counter/response: exactly which registers are stable from request acceptance through response and ACK. Use that contract to remove the response-address comparison from the counter feedback path, or precompute ownership validity where the tag is already stable. Preserve wrong-address, STOP/reset, fault and command retirement edges; do not simply waive arbitrary-state failures without proving reachability. Test only the changed boundary, then one full fit with counter/capture/loader and all-clock minima. Once safe, connect necessary native-video IO/CDC/reset and MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack to minimum SMB3(J) hardware. Keep installed164/GBC/save SRAM; no repeated full writes/OAM/A-B/044.

사용자머지/개인GitHub/한국어4PR절. 다음턴PR상태확인. 국소식변경/무변경fit/일반진단확장반복금지.

---

# NES 현재 인계 — 명령 사전 판별과 적재 완료 상태

PR108 OPEN. [계약](../../docs/nes-predecode165-contract.ko.md) · [검증](../../analysis/predecode165-verification.json).

165 영상 경로 진척: CHECK 명령 사전 판별·로더 완료 플래그로 제어 경로를 개선했습니다. 전체 배치15,040LE/963LAB/35M9K, 명령·카운터1179648사례/로더628736사례/SPI98검사 통과. 실제 같은 클록 setup 미달이 남음(-0.153ns). 외부IO·CDC·MCU 연결은 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

SELECT predecode165 map03/reproduce03final; retire165map02기준2RTL SPI/loader만변경59입력불변. pending counter clear/inc를기존SS상승캡처edge에저장, 명령별조건전개;동적하드fault/응답/충돌은원래retirementedge검사. loader count_complete는loaded_bytes와동일edge갱신. clocklatency/6B/audio/pad/saveSRAM불변. SPI786432+capture393216/negative2 PASS,loader628736/negative1 PASS,actualSPI98/8writes6reads6negative PASS. lengthfixture refdut치환오류/oldcountseed불일치 path02/03 보존;어댑터2주입만보정.새fullboot아님.

FIT15040LE/963LAB35M9K/8332reg122physical0virtual1PLL. unchangedbudget-0.605 vs exact155nominal-0.153;sameclocknominalpass=False;hold+0.155. rawmixed-15.504/IO54in57outOPEN. targetedcounter/capture/address각각은검증JSON참조. 최악행만보고하위미달누락금지. noSD/ARM/새MCU완료/전체timing승인.

NEXT Reuse selected map03: fix measured nominal -0.153ns path nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|check_next[0] -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|check_next[17] without moving retirement/fault edges or relaxing clocks. Routed path crosses response-address comparison -> counter_retire_ok -> final counter mux, not the carry increment itself; inspect comparator factoring/fanout or stable-tag capture contract before another fit. Inspect counter/capture/loader groups together, not only first worst row. Then necessary IO/video CDC and MCU RUN receive-convert-ACK/audio/input/STOP/time/full-link/stack, minimum SMB3(J) hardware. Keep save SRAM reserved/installed164/GBC. Do not repeat unchanged OAM/full writes/A-B/044 or rejected generic-body predecode/masked-XOR map04; preserve failed fixtures and completed archives.

이전frozen/publicpins/record/audit불변. 사용자머지/한국어4PR절/개인GitHub. 다음턴PR상태먼저확인.

---

# NES 현재 인계 — SPI 응답 개선, 실제 CHECK 타이밍은 미완료

PR108 OPEN. [계약](../../docs/nes-retire165-contract.ko.md) · [검증](../../analysis/retire165-verification.json).

165 영상 경로 진척: 로더 명령 차단과 SPI 응답 직렬화를 개선했습니다. 전체 배치15,053LE/963LAB/35M9K, 로더52,224상태·SPI15,680비트·실제 경로98검사 통과. 실제 클록 기준 CHECK setup−0.217ns는 아직 미달이며 host여유+0.021ns입니다. 외부IO·CDC·MCU 연결 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

SELECT retire165 map02/reproduce02 variant=serial. baseline check165map03대비 loader/boot/SPI3입력변경,58입력byteexact. loader공통inhibit factoring+SPI56bit snapshot shift. completionedge/STOP/오류우선순위/6B 식별불변. loader52224state/wrong-inhibit, serial256frame15680bit1347840edge/wrongbit, actualSPI98checks8writes6reads6negative PASS. no새전체boot/MCU/SD. generator후속variant추가는실행RTLbyteexact로재사용;옛실행generator보존.

기존SDC동일:3corner198행 memory−.426(5.5target),host+.021,NES+5.344,holdmin+.159. Exact155 clock-only별도STA nominal−.217(check_failed->check_next15),367소스/설정/routed파일불변. falsepath/clock완화없고둘다FAIL. rawmixed−15.982/IO54in57outOPEN. FIT15053LE963LAB35M9K8329reg122physical0virtual1PLL. LAB여유0/host여유작음. 이전baseline−.488는그대로보존.

REJECT retiremap03 explicit counter_clear/inc XOR식:786432states+wrongfaultgate+actualSPI PASS지만memorybudget−1.454/nominal−1.002로악화. check_next3->check_next18 feedback. 15049LE961LAB. 선택candidate로오해하지말것. 첫STA cwd/path실패와미실행선언위치초안보존;license문제아님.

NEXT Selected retire165 map02/reproduce02: fix boot check_failed -> control check_next nominal -0.217ns (5.952ns period) using measured cone, preserve hard-fault precedence and retirement edge. Host margin +0.021ns and963/963LAB require whole-fit checks after any RTL change. Rejected parallel counter-clear/XOR map03 worsened feedback to nominal -1.002ns; do not repeat. Investigate predecoding stable pending command/header/body predicates at their existing capture edge before dynamic hard-fault gating; this is a proposal, not implemented. Keep stricter5.5/5.3ns budget misses separate; no clock/falsepath relaxation. Then necessary external IO/video CDC, MCU receive-convert-ACK/audio/input/STOP/time and full-link/stack, minimum SMB3 first-level hardware. Preserve save SRAM and installed164; no unchanged OAM/fullboot/A-B/044 repeats.

완료archive/record/audit 및 이전pins불변. 사용자머지/개인GitHub/한국어4PR절. 다음턴PR상태먼저확인. 실기목표SMB3(J),설치164/GBC/세이브SRAM보존.

---

# NES 현재 인계 — CHECK 경로 수정

같은 PR108 OPEN. [계약](../../docs/nes-check165-contract.ko.md) · [검증](../../analysis/check165-verification.json).

165 영상 경로 진척: CHECK 카운터·레지스터 제어를 개선해 최악 setup을−1.218ns에서-0.488ns로 바꿨고 같은 클록 setup 부족이 남았습니다. 전체 배치15,015LE/961LAB/35M9K,786432상태 비교·SPI98검사 통과. 외부IO·CDC와 MCU 연결은 아직 미완료입니다. 설치164·세이브 SRAM 보존, 새SD 없음.

SELECTcheck map03/reproduce03: secondarymap03대비nes_rom_spi.sv만변경,나머지60입력byteexact. low8/high11증가를bitXOR/prefix로,load_data8bit AUTO_CE OFF,check_next19bit ALLOW_SYNCH_CTRL OFF. 다음값/오류우선순위/SPI식별6B/CE/retirementedge불변;OAM/audio/pad/saveSRAM불변. test01 524288counter+262144priority=786432상태/모든reg 비교+wrongcarry negative PASS. path02 master상승edge98checks8writes6reads6negative/ACK롤오버/finish/START PASS. map03두속성만제거하면test01/path02실행RTL과byteexact. 증거재사용은속성한정이며새배치는새STA. 전체코어는실제FIT,새게임boot아님.

map01mem-.552/load_dataENA;map02mem-.536/check_nextSCLR;map03mem-0.488. sameclock_pass=False;최악 nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|state.RECEIVE. rawmixed-12.665/IO54in57outOPEN. nominal-only재분석/SDC완화없음. 전체timing승인아님.

path01와unmodifiedbaseline path-base01은둘다78번째옛5F기대에서실패. current6B맞춘별도path02 PASS;원래149pinned파일불변. no새license문제. 완료archive/record/audit/pins수정금지.

NEXT Use selected CHECK map03: repair measured boot check_failed -> loader state.RECEIVE (-0.488ns at nominal5.952ns), byte_count -> miso_hold (-0.332ns at5.3ns target), and check_next -> check_busy (-0.174ns at5.5ns target); no uncontrolled latency/SDC relaxation or repeated attribute-only fits. Then necessary external IO/video CDC and MCU RUN receive/convert/ACK with existing audio/input/STOP/elapsed time, whole firmware link/stack, SMB3 first-level hardware. Preserve save SRAM and164; no unchanged OAM/boot/A-B/044 repeat.

사용자머지/개인GitHub/한국어4PR절. 설치164와SMB3(J)우선. no새SD/MCU완성/60fps주장. 다음턴PR상태부터확인.

---

# NES 현재 인계 — 전체 FPGA 배치 성공, CHECK 타이밍 수정이 다음

같은 PR108 OPEN. [계약](../../docs/nes-oam-secondary165-contract.ko.md) · [검증](../../analysis/oam-secondary165-verification.json). 설치164/원본GBC/세이브 SRAM 보존. 새SD없음.

SELECT secondary map03/reproduce: board03+AREA+range4address+secondary valid-mask. 무효 바이트는FF; reset/clear는valid만0, fresh write와valid1이같은edge; copy는masked값. 내부raw저장만다르고외부CE/latency/우선순위불변. primary변화없고extra기능보존; RAM블록변환아님. 기타59입력byteexact. MAP19421estimatedLE13998comb8316reg197104bits122physical0virtual1PLL. 실제FIT/ROUTE15052LE963/963LAB35/56M9K PASS. 이전13928comb8284reg/964LAB보다논리70·reg32증가하지만reset/control구성으로배치가능. LAB여유0. Fitter내부첫net실패후자동재시도성공원시로그보존.

test03 everyedge216362/2426copy3111CPU10473SS2012collisions, primary256/secondary64/state/native/output PASS. valid01 row0..15/1024byte/stale37주입/wrong-valid row0byte32검출 PASS. functional시나리오이지formal/새SMB3boot아님;기존board/SPIstub범위그대로. 전체core는실제MAP/FIT. 재생성모든입력byteexact. REJECT map01factored13939comb, map02/test02상수주소함수의전역mem sensitivity로36ns비교실패;최종map03모든읽기explicitternary통과. 실패보존,license문제아님.

STA3corners198sameclockrows: setupNES8.479/host1.937/board119.620/mem-1.218ns;holdmin+.155. 메모리최악reader check_response_address15->SPIcontrol check_next7,7logic levels,5.500nsmaxdelay. 기존SDC그대로이며nominal-only재분석안함. mixedraw-12.396/입력54출력57미제약OPEN. FIT성공은timing/IO/CDC/실기승인아님.

NEXT 실제routed CHECK비교->다음주소/데이터갱신경로를줄이고 valid/address/error/command완료순서보존. 추가논리가LAB초과를재발시키지않게변경경계검증+FIT/STA. 이어필요외부IO/CDC, MCU RUN수신변환ACK+기존audio/input/STOP/실제시간/full-link/중첩stack,SMB3첫레벨. 임의SDC완화/세이브SRAM사용/오디오입력삭제금지. 이전실패OAM옵션/무변경MAP/FIT/boot/A-B/044반복금지. E6/2status/E5observer/F6sink/RAMidle동일. 완료record/audit/archives/pins불변. 다음턴PR108상태확인,개인GitHub,한국어4PR절,사용자가머지.

---

# NES 현재 인계 — OAM 주소 명시로1719개 절감, LAB1개 초과

같은 PR108 OPEN. [계약](../../docs/nes-oam-port165-contract.ko.md) · [검증](../../analysis/oam-port165-verification.json). 설치164/원본GBC/세이브 SRAM 보존. 새SD없음.

SELECT map02/reproduce: board03 + AREA + secondary extra OAM 주소4곳만수정. row_ex<8 guard아래 {row_ex,low2}+32 -> {1'b1,row_ex[2:0],low2}. 기존주소도32..63이지만명시후사용하지않는extra하류를더제거. 기능/CE/latency/쓰기priority변화없음,기능삭제/RAM사전읽기아님.59기타입력byteexact. 전체19351estimatedLE/13928comb/8284reg/197104bits/122physical0virtual1PLL;OAM5663->3939. 실제FIT14983LE/35M9K,964/963LAB error170012/171000. 실패중간자원일뿐배치완료아님;STA없음. AREA대비1719/board03대비2513comb절감.

test02 actual banked reference 216362edges/2426copy/3111CPU/10473SS/2012collisions PASS;native+allprimary256/secondary64/state/output. range01 row0..15 accepted8/reject8/all1024byte PASS,wrong-bank대조row0byte0검출.32guardedindex계산전수대조.전체formalproof/새SMB3boot아님.소비시점불변이라기존fullgame/board/SPI결과범위재사용.최종generator재생성입력과선택map02byteexact.후속생성옵션수정은실행모듈본문별도비교.

REJECT map01 shared-read15665comb(기능PASS),fit03physical-areaON/fit04MinimizeArea설정실제적용확인했지만둘다964LAB,동일MAP DB재사용;map05bankCErecognitionOFF15761comb초과.이설정들은선택map02에없음.기존onehot/rowwriter실패도반복금지.초기checker가옛board03Balanced까지Area요구한검사오류보존/수정;RTL실패아님.

NEXT remaining primary OAM rowcopy/storage/LAB control grouping축소.비동기RAM변환이필요하면PPUCE사이사전읽기/CPU즉시주소/rowcopy/SS동시쓰기소비edge먼저정의;추가지연무조건삽입/CE속도변경금지.변경부분필수검증->전체fit->같은배치setuphold/PSRAM/SPI/SNES최소타이밍->realMCURUN수신변환ACK+실제경과시간audioinputSTOP/full-link중첩stack->SMB3첫레벨실기.1LAB여유만으로timing보장아님.세이브SRAM/오디오입력삭제/SDC완화금지.E6/2status/E5observer/F6sink/RAMidle동일.실기우선,unchangedboot/A-B/044반복금지.

새 probes/nes-oam-port165 record/audit와기존archives/pins완료후불변.다음턴PR상태갱신/사용자머지/개인GitHub/한국어4PR절.

---

# NES 현재 인계 — AREA794 감소, 실제 OAM 저장·읽기 구조 축소 필요

같은 PR108 OPEN. [계약](../../docs/nes-oam-select165-contract.ko.md) · [검증](../../analysis/oam-select165-verification.json). 설치164/원본GBC/세이브 SRAM 보존. 새SD없음.

선택 map07/reproduce: nes_oam_select165.py 기본area는board03 RTL/SDC/ROM 등60파일byteexact, QSF CYCLONEII_OPTIMIZATION_TECHNIQUE AREA만추가. 실제report Area확인. 글로벌 OPTIMIZATION_TECHNIQUE는이장치에적용안돼map06Balanced;재시도금지. 현재공개generator재생성자료reproduce와map07입력전체일치. 21070estimatedLE/15647comb/8294reg/197104bits/122physical0virtual1PLL. 기존21442/16441에서794comb절감. 실제FIT170011/171000:15647>15408. 239개감소만으로최종fit보장아님/STA없음.

REJECT map02 onehotread16440comb/OAM5664;map04 rowwriter16441/OAM5664. test01/02 각각216362edges/2426copies/3111CPUwrites/10473SSwrites/2012collisions동일. Nativeobserver/primary256+secondary64/state/output매edge비교. 두변형의기능성공은자원개선아님;활성RTL에는채택하지않음. map01자동탐색CIRAM누락/map03explicitgenerate/prepare05줄바꿈검사실패/map06잘못된설정이름 보존. 원본testTB불변. activeareaRTL동일로이전boardtest04와SMB3자료재사용,전체부팅추가안함.

NEXT OAM5663의실제memory/readports/rowcopy비용축소. 단순onehot/행쓰기/동일AREA재배치반복금지. 내부RAM사전읽기검토시CPU/PPUCE와소비edge계약먼저정의;읽기1clock추가를무작정dropin금지/CE속도변경금지. 원래rowcopy/CPU/SSwrite priority보존. changedboundaries+시점바뀌면actualSMB3비교->전체fit/타이밍->realMCURUNguard/time/audio/input/sinkACK/full-link/stack->SMB3실기. 외부세이브SRAM/오디오삭제/SDC완화금지. 기존E6/2status,E5observer,F6sink/RAMidle동일. min안전후실기우선/generic진단·boot/A-B/044반복금지.

완료 probes/nes-oam-select165 record/audit와기존archives/pins불변. 다음턴PR상태갱신;사용자머지/개인GitHub/한국어4PR절.

---

# NES 현재 인계 — 실제 보드 연결 완료, 논리 자원 축소 필요

기존 PR108 열린 상태에서 후속 작업. [계약](../../docs/nes-sink-board165-contract.ko.md) · [검증](../../analysis/sink-board165-verification.json). 설치164/원본GBC/사용자세이브 보존. 새SD없음.

선택 board03/test04. actual164 top + native producer + sink bridge, 기존38M9K/frame150/bus151 제거. 공통reset/active,ROMfault2FF/nativeSPIfault STOP,패드CDC,4그룹MISO배타 연결. 실제122핀/SDC동일. audio/pad/observer원본동일. RAM_ADDR0/OE1/WE1/DATAZ. status73 E6/version2,observer70 E5(옛D4주석틀림),sinkE0 F6. 구형E5/version1 MCU실행금지. boot/native 내부중재유지. realMCUguard/시간/오디오입력/오류로그와전체링크아직미완료.

새materializer tools/nes_sink_board165.py + nes_native_ram_board165.py 사용. 기존공개RTL직접수정하지않음. board01 uninferred13/registeroverflow;동기읽기/출력mux분리로large8배열RAM추론(6M9K/2rasterAUTO). compact4/raster2/requiredtile1/SPIbuffer1,latency보존. board02/03 map21442estimatedLE/16441comb/8294reg/197104memorybits/PLL1. board03 actualFIT170011/171000:16441comb >15408. 배치실패/STA미실행. 164map16362->fit14711이었으므로estimatedLE와최종fit혼동금지. 1033comb줄여도전체fit보장아님.

최대localcomb OAMEval5664(164도5662),compact1359/raster637/nativeSPI494/sink489. 새관측만으로OAM이커진것아님. 다음은실제비용기반OAM비동기읽기·행복사·쓰기선택/compact구조축소. 기존OAM일괄삭제/CE변경/오디오제거/세이브SRAM차용/무근거SDC완화금지. 구조변경경계와짧은SMB3실자료확인후전체fit;무변경배치반복금지. 자원해결후realMCURUN→전체링크/스택/최소타이밍→SMB3실기. generic진단증설/boot/A-B/044반복금지.

test04 FRAMELEASE1740checks9scenes7rejects;실제SMB3기록3(frame12/15mode0+12mode2)dump/events/old exact;SPI1717records/47blocks191requests두위상0/3.5기존전송exact. actualtopperipherals13checks/DAC5593edges,CPU/loaderlifecycle만stub. 새게임부팅/소리품질/물리타이밍시험아님. test01stub생성빈포트/test02선언순서/test03D4기대값오류보존. 최종observer250kHz/E5,기타SPI2.625MHz. checker초기rasterAUTO를M9K라단정한오류수정. board03/test04최종sources해시일치.

완료 probes/nes-sink-board165 및 이전 record/audit/finalizer 재실행금지. 기존pins/archives불변. 개인GitHub/한국어4PR절/사용자머지. 새RTL은이PR108후속커밋이며별도PR생성하지않음.

---

# NES 현재 인계 — FPGA 패킷·SNES 응답 접속부

PR107 머지019a92ef 이후 새 브랜치 codex/nes-sink-fpga-165. [계약](../../docs/nes-sink-bridge165-contract.ko.md) · [검증](../../analysis/sink-bridge165-verification.json). 설치164/사운드·입력·STOP·메뉴/원본GBC 그대로,카트리지 SRAM·세이브·복구 영역 사용금지. 새SD없음.

선택 bridge03 + map02. SPI E0/F6 status16/CRC8, E1 command+packet16..256+CRC16BE(max259). 단일256B RAM,길이/CRC완료후게시·소유중덮어쓰기차단,12B ACK전부쓰기+601C=A5때원자retire. snapshot중ACK게시안찢어짐,불완전전송/ACK는공통reset까지fault. SNES6000ready/6001STOP-or-fault/6004..5length/400000..FFpacket/6010..1BACK/6002..3pad. 4KiBROM해석 body8000..8FBF/vectorFFC0..FFFF/holesFF. rawRD/reset/active는버스구동취소. 이전sink클라이언트2651B/4096ROM재사용;카트리지 SRAM포트없음.

이전실제C/SNES sink01 normal137+stop90의227packet/ACK를RTL SPI+SNES버스로재생. 두위상0/3.5ns각35741bytechecks/42766wireB/908transactions,actualC adapter도동일TX/RX와17오류검사PASS. ACK는이번TB버스쓰기재생이며동시65816/실기/FPS시험아님. ROM4KiB전부/늦은쓰기/연속RD/소유권/reset/STOP확인. bridge01한글경로QuestaDB실패보존;02PASS+map01무시async_reg/폭경고발견->Quartus속성+명시8bit선택의03최종. FLOAT sandbox호스트식별불일치후기존허가host래퍼성공,새라이선스문제아님.

ARM adaptercontext16/text426/directstack544+status12,상위packet304+callback/IRQ중첩별도. Cguard필수/poll1..65536은시간아님;첫E0F6확인후E1,유한E0poll;legacyD6/E5허용금지. 부모sender가ACKop/seq/serial/gen/65/9A검사하며모호오류는FAULT공통reset,재시도금지. actualMCURUN service/time/STOP아직콜백미연결.

map02 EP4CE15F17C8 단독synthesis1082LE/581reg/34816bits,4096x8ROM+256x8dualport M9K추론;ROMMIF4096bytes일치. ROM쓰지않는write입력0의10030경고3. Fitter/전체자원/물리핀/IO/CDC/MTBF미승인,새속성도승인대체아님.

NEXT 실제최상위에서기존framebuffer버스/38M9K를새bridge로교체. 기존boot/native/sink SPI MISO배타,commonreset/active/STOP/fault/pad연결+164audio보존. 현재모듈은부모미인스턴스화,구버스와동시활성금지. MCU실제RUN에수신→변환→sink/guard시간·오류·STOP·오디오입력서비스연결;긴poll로서비스막지않기. 전체SRAM/중첩stack·client공간·fit·변경IO최소확인뒤SMB3첫레벨실기. SPI39.59ms/비교29.7ms/60fps열림. 같은boot/A-B/044나generic진단증설금지. 사용가능화면후60초제한/오류·본체reset로그/DOWN유지순서.

기존pins/archives불변. 완료 probes/nes-sink-bridge165 record/audit 및이전finalizer재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — C와 SNES 수신·표시 응답 왕복

PR107 같은 브랜치. [계약](../../docs/nes-native-sink165-contract.ko.md) · [검증](../../analysis/native-sink165-verification.json). 설치164 유지. 카트리지 SRAM/세이브/복구 영역 사용금지, 기존 GBC/164 사운드·입력·STOP 코드 무변경. 새SD없음.

sink01: C producer와 실제SNES65816/SPC/WRAM/PPU 동시 실행, 파일 mailbox로227packet/ACK 왕복. ACK는실제SNES쓰기이며호스트주입아님. 실제SPI/FPGA/MMIO/MCU게임루프는미연결. 기존변환된frame12/15재사용, converter 재실행/새boot없음. normal137packets/3commits(두장면+noop)/18727packetB+1644ACKB, stop90/1commit/12462B+1080B. 4캡처229376activepixels 일치(고유2장면114688). 실제compare6/2/0명령,5493/18/0B. 정상끝invalidsectionE0;두번째비교STOP E4/새DMA게시없음. C IOfail/staleserial/gen/sequence/badACK5거부;BUSY재진입금지. SPC A9/visiblevblank/forcedblank없음/모델DOWNsample150/94,물리소리·입력유지증명아님.

새 C sink24B ARM(호스트32),text704B,직접stack packet304/seal88/pattern24+callback중첩. 이전stage460B 대신쓸경로, old/new표읽기없음. nominal60340/65424차이5084 NOTfull-link/heap/stack승인. SNES body2651B/ROM4096B로기존2048decode와호환안됨. 기존164에client만설치금지. 헤더/상태1200..1239,수신량1080..108B,local의1000/1100/DP40..6F 유지,body7E2000. 정확한ABI는계약필독.

packet16Bheader+최대240data,BEGIN1/DATA2/SEAL3. serial32정확+1,seq16장면내+1,gen16;DATA section0..5연속offset/상한/SEAL실제길이 확인. ACK12B(status/op/seq/serial/gen/65/9A),status1은표시완료뿐. 게시전C BUSY,응답모호/오류는FAULT공통reset필수/재시도금지. 이전stage의미게시실패재시작규칙을그대로상속금지. SNES badheader는ACK없이quiet;adaptertimeguard필수. STOP은comparison반환후DMA전검사(물리최대지연/메뉴복귀검증아님).

NEXT **SPI packet/ACK 하드웨어와 SNES bus/4KiBROM decode** 구현. ready6000/STOP6001/length6004..5,packet400000..4000FF,ACK6010..1B/publish601C=A5,pad6002..3. packet완전CRC/길이검사후immutable게시;ACK원자retire;공통reset. 기존164 framebuffer40뱅크/6000와동시활성금지. 새paired식별을명시하고기존6B/E5무조건허용금지. Cexchange callback에유한guard/time/STOP 연결하고긴wait가mainloop오디오/입력/로그를막지않게한다. 이후38M9K교체/full-link/fit변경경계검사후SMB3첫레벨실기. 새generic진단/같은boot/A-B/044반복금지. SPI39.59ms/compare29.7ms/60fps는미해결. 테스트의파일폴링/캡처ACK지연시간을전송성능으로쓰지않는다.

기존publicpins/archives보존. 완료probes/nes-native-sink165 record/audit/publish재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — SNES 내부 비교 완료, 실제 전송 연결 우선

PR107 같은 브랜치, 아직 실기165 패키지는 없다. [새 계약](../../docs/nes-native-local165-contract.ko.md) · [검증](../../analysis/native-local165-verification.json). 설치164 사운드/입력/STOP/메뉴·GBC 저장 무변경. 카트리지 SRAM·세이브/복구 영역 사용금지. SNES WRAM7F 주소를 MCU sram_*에 연결금지.

local03: 실제65816 비교938B+동적업로더288B, SNES7F 두32KiB 후보. 기존video03 두장면만 재사용, CPU가 만든6/2명령과114688픽셀 일치. 최초5493logical/5472PPUDMA,다음18B. 9사례:2장면/역방향무변경/주소/크기/64B경계병합/예산/32명령/oddHDMA. visible데이터쓰기vblank. local01/02도 보존;03 fixture WRAM초기화로MVN미초기화읽기 제거. 일반NES코어부팅/FLOAT 반복없음.

성능: 두 번째 비교2595110→693782→638300masterticks(약120.8→32.3→29.7ms), 무변경564700(26.3ms),명령초과1356928(63.2ms,초기보다느림). 모델이고송수신/표시대기/MCU변환 제외,60fps아님. 두후보전체MCU재독출10986B174calls를 대체할 수 있는 코드지만 실제호출부/왕복은아직교체안함. SPI39.59ms와후보5493B공급 남음. 미세최적화만계속하지말고실제연결의병목측정우선.

ABI: nativeA/X16 DBR/DP0,DP40..6F;길이1000/1010,base1020/1022,display1024,status1025,count1026,charged1028,payload102A,scroll102C/102E,budget1030,list1100..11FF,uploadscratch1070. status3는로컬완료이며물리ACK아님. 비교중및게시목록/후보소유권불변,serial/gen완료게시필수. 서비스callback은scratch보존;시험padpolling은실기입력/사운드연속증명아님. HDMA포인터는무변경에도새후보로전환.

NEXT 실제 MCU→SNES WRAM 수신+localcompare호출+표시ACK를 묶어서 연결. 긴 비교에도입력/STOP/수신 살아있게 스케줄. 실제client 공간(시험ROM2964B는배치승인아님)/MCU전체link·heap·중첩stack/38M9K교체·fit 변경경계 검사후 SMB3첫레벨실기. 기존C stage460B는참고소유권모델이며그대로전체표재독출연결금지. 같은boot/A-B/044 재검사하지않음. 이후60초제한/오류·reset로그/DOWN유지. 기존모든pins/archives보존;완료probes/nes-native-local165 record/audit재실행금지.

---

# NES 현재 인계 — 세이브 SRAM 보호와 WRAM 차분

PR107 같은 브랜치. [새 계약](../../docs/nes-native-stage165-contract.ko.md) · [검증](../../analysis/native-stage165-verification.json). 사용자 지적에 따라 U511 카트리지 SRAM을 영상 저장소로 쓰겠다는 제안을 철회했다. 로컬 SA-1/GSU는 E00000–E7FFFF를 별도 RAM으로 보내며 IS_SAVERAM 쓰기도 연결한다. 모든 코어의 물리 저장 위치가 같다는 뜻은 아니다. 기존 GBC E20000 snapshot/복구 영역까지 보호. **카트리지 SRAM·세이브/복구 영역을 영상용으로 전용하지 않는다.** 기존164 RAM_WE=1/데이터Z와 원본 저장 코드 무변경, 실기 쓰기 없음.

stage02: SNES WRAM bank7F의 두32KiB 후보, 단일 MCU 관리 구조 ARM460B. C 차분/순차 pattern staging/64B step/최대32명령/serial32+gen16 ACK. 미게시 실패만 폐기·재시작, 게시 전 arm하고 모호한 실패/실패ACK는FAULT 유지·commonreset 필수. 오래된 ACK 무시/무변경도 ACK. 9거부+경계병합/축소재확장/소유권 검사PASS. stage01 CPU HDMA복사 PASS도 보존하고 stage02 직접bank7F HDMA 선택. 매 commit마다 HDMA포인터를 새 후보로 변경, 바이트동일/0명령이어도 생략금지. WRAM->WRAM DMA 금지.

기존video03 두 장면 재사용. C 생성5493논리B6명령(HDMA21제외 초기PPUDMA5472)/다음18B2명령, 실제SNES WRAM DMA/PPU114688픽셀 일치/vblank226. C의ACK는host 주입; ROM fixture로 WRAM 공급한 모델이며 MCU mailbox/물리 왕복은 미구현. 새로운 코어boot/FLOAT 없음.

**성능 주의:** 18B는 PPU 갱신뿐. 새후보5493B쓰기+10986B/174회읽기를 그대로 MCU로 왕복시키면 병목. bank7F는SNES주소이며 기존MCU sram_*에연결금지. 다음에는SNES 내부비교 또는 묶음 결과를 실제client/mailbox/표시ACK에연결하여 전체표 MCU재독출을피한다. 기존SPI39.59ms도미해결. 새 일반진단을 늘리지 않는다.

ARMtext1290/step직접stack168. 단순합계60776/링커65424차이4648은전체link/heap/중첩callback/IRQ승인아님. 관리구조2개/전체MCUshadow금지. 실제 RUN 스케줄/전체링크/38M9K교체/fit 뒤 SMB3첫레벨실기로간다. 사운드·입력·STOP메뉴/설치164 유지. 새165SD 없음. 사용가능화면뒤60초제한/오류·reset로그/DOWN유지. old pins/archive 불변, probes/nes-native-stage165 완료record/audit재실행금지.

---

# NES 현재 인계 — 유한 C 표시 변환과 SNES 픽셀 일치

PR107 같은 브랜치. [새 계약](../../docs/nes-native-video165-contract.ko.md) · [검증](../../analysis/native-video165-verification.json). C수신기 COMMITTED 장면→SNES BG/OBJ/맵/OAM/CGRAM/HDMA 변환기를 구현했다. 선택video03: 서로 다른 실제SMB3 frame12/15를 재사용,114688픽셀을 실제SNES CPU/DMA/PPU 모델에서 원본과 일치시켰다. 새boot/RTL/FLOAT없음. PC가업로드명령과차분을조립하므로 MCU루프/실기전송은아직미완료.

stage callback은BG16/OBJ32바이트를외부임시저장소에만쓰기;직접표시VRAM금지. 완성전실패시후보전체폐기/재시도없음. C valid≠SNES표시ACK. BG는정확한61비트physical+plane-mapping키(해시아님),OBJ tag/mask키. rank정렬/실제mask/팔레트경계분할/행32개평가한도/1023BG·128OBJ패턴상한. 후보별키재할당,장면간캐시는아님. 6거부각2사례+복구PASS. 초기5493B6명령/다음18B2명령/vblank226. 작은부팅표본차이이며FPS/첫레벨부하아님.

메모리 중요:02패턴전체보관27662B는baseline26364+receiver18064=72090B로64KB초과여서미채택.03은패턴stream/키만보관하여candidate15888B;합계60316B/링커RAM65424B 차이5108B는heap/stack/정렬/새bus미반영 단순합계. ARMobject2216B/directstack704B. 두candidate/64KBshadow 추가금지. 실제전체링크와callback/인터럽트stack확인필수. harness의pattern전체배열은PC staging모델뿐.

**NEXT:** 외부staging 버스와 SNES vblank 소비자/완료ACK를 구현하고 MCU RUN 수신·변환·업로드 스케줄을 연결한다. 기존50ms대기를그대로두면수신기한불가,1200회카운트를새작업과합쳐실제60초로오인금지. 오류/CF86/STOP·사운드/입력보존. 단일candidate/외부staging,전체SRAM링크,기존38M9K프레임버퍼제거교체,FPGAfit/타이밍/직렬39.59ms예산을확인뒤SMB3첫레벨실기. 현재56/56M9K에단순추가금지. 같은boot/A-B/044반복금지. 사용가능영상뒤60초제한/오류·본체reset로그/DOWN유지.

01컴파일들여쓰기경고/02픽셀PASS이나메모리초과설계보존.03선택,기존archive/pin수정없음. probes/nes-native-video165 완료record/audit재실행금지. 설치164/개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — SPI 접속부와 유한 C 수신기

PR107 같은 브랜치. [새 계약](../../docs/nes-native-spi165-contract.ko.md) · [검증](../../analysis/native-spi165-verification.json). 실제 SPI D0~D3/256바이트 버퍼, 기존 host84MHz mailbox 연결, 기존149 가드 엔진의1~259바이트 생성 변형, 유한 C 수신기를 구현했다. **MCU 게임 루프/SNES 명령 소비자/38M9K 교체/fit/실기 미완료.** ARM 오브젝트 컴파일을 실기 성공으로 해석하지 않는다. 설치164 유지.

선택spi04 RTL + c05 C. 이전host02 frame12의1717레코드 재사용, 새boot없음. 두 위상0/3.5ns에서47블록/191요청 모두 C 요청과 일치,1714데이터 레코드/15타일240바이트 동일. packed11196B/wire12489B/CS간격 포함39.59ms: 이 직렬 구간만으로60fps 불가, 최종FPS 아님. CHR한바이트당레코드 유지, 타일묶기/차분전송 미구현. bulk1355가드/오류사례 PASS. C저장18064B/ARMtext2176B/poll직접stack560B; 실제전체SRAM링크필요.

STATUS D6+flags/token/len/CRC8, READ payload+CRC16, 전체READ후token POP. POP/D3응답은명령반영전이므로후속STATUS필수. C는COMMIT후POP확인유실도FAILED/게시금지. PREPARED≠SNES표시완료. prepare(false)/IOfail은현재세션failstop,정상ABORT는IDLE. commonreset때C도reset;독립endpointreset금지/무조건재시도금지. 부모boot/native MISO 배타연결COMPILE만;물리CDC/타이밍미검증. 새SPI결선만exportMAX4194304/fillMAX2097152/WAIT131072 정책,기존기본값불변. source와serial을연결한기한시험아직없음/512타일처리보장아님.

**다음:** C receiver + bulk callback을실제게임루프에연결하고기존SNES참조를유한C명령/vblank소비자로이식한다. 기존38M9K프레임버퍼를교체하며현재56/56M9K에단순추가금지. STOP/error/reset/사운드·입력스케줄과합산SRAM·배치·타이밍확인뒤SMB3첫레벨실기. generic진단/같은boot/A-B/044반복금지. 현재40ms전송병목은계측근거로줄이되SPI속도무근거상향금지. 사용가능화면뒤60초제한/오류·본체reset로그/DOWN유지.

초기01폴더중복/02wire선언/03MinGW출력형식/04bulk누적poll상한실패보존.04RTL/C통과재사용하고05는시험누적상한수정+terminalIO음성검사만재실행.05sandbox DLL오류뒤host실행통과,라이선스오류아님. oldarchive/publicpins불변. probes/nes-native-spi165 완료record/audit재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — 장면 전송·호스트 클록 경계·PREPARED/COMMIT

PR107 동일 브랜치. [새 계약](../../docs/nes-native-host165-contract.ko.md) · [검증](../../analysis/native-host165-verification.json). 기존 공유 reader를 유지하고 공통 장면 query/fill을96비트 레코드로 전송하는 exporter, 순방향96/역방향17비트 mailbox를 연결했다. 부모 전체는 컴파일만 했고 host포트는논리ready/valid다. **실제SPI/MMIO·MCU·SNES업로드/표시완료·fit·새SD는미완료.** PC수신기를펌웨어로오인하지않는다.

BEGIN→query0..5→fill바이트→END→호스트PREPARED/REJECT→COMMIT/ABORT. END는표시허가아님. 같은generation ACK시에원본lease를다시검사하고COMMIT만표시후보로승인한다. 잘못된세대ACK무시. timeout/실패시원본해제+ABORT,이미넘긴임시레코드는회수하지않는다. host멈춰ABORT미수락이면새장면시작금지. 기본전체1048576NES클록,시험262144;fill65536wait/262144total유지. 공통reset양쪽필수/수신임시데이터도flush.2FFtoggle+수신추가1edge/helddata,실제CDC STA/MTBF미검증.

host02 11사례: 이전실제SMB3봉인frame12/14/16/18/20재생+실제fill/export/CDC,backend는ROM바이트지연모델. 기존memory01공유reader/CPU기한근거재사용,새boot없음. 정상5phase/역압력/호스트clockpause/옛ACKPASS. querymiss/REJECT/ACKtimeout/END후lease취소4ABORT0COMMIT. 추가로host정지중다음generation이이미봉인된경우이전ABORT후다음장면COMMIT복구. 전송중commonreset후65535세대만COMMIT. verify02 PC수신5거부,정상286720+reset57344+취소복구57344픽셀일치. 기존SNES명령참조연결:첫5493B6명령/이후0,5부팅영상동일이라움직임·첫레벨·FPS아님. 새SNES실행없음.

레코드kind3/gen16/index13/data64. 정상1717레코드=원시20604B,기존2226B압축위치량과혼동금지. query6전체8192는host로안보낸다. **다음:** 실제SPI/MMIO접속부+유한MCU수신/검사/PREPARED/COMMIT을연결하고유효폭·타일단위패킹/실제전송예산확정. SNES명령/vblank완료와38M9K교체를묶는다. 현재56/56M9K에추가만금지. 변경경로최소검사/실제fit뒤SMB3첫레벨실기. generic진단확장·같은boot/planes/A-B/044반복금지.164사운드/STOP메뉴유지;사용가능영상뒤60초제한/오류·본체reset로그/입력유지.

최종선택host02/verify02. 초기host01/verify01도보존. 최종리뷰에서ABORT대기중다음generation이봉인되면DRAIN이멈추는조건을수정했고11번째사례로복구검증. 이전archive/pin불변. 완료record/audit재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — 장면 전송·호스트 클록 경계·PREPARED/COMMIT

PR107 동일 브랜치. [새 계약](../../docs/nes-native-host165-contract.ko.md) · [검증](../../analysis/native-host165-verification.json). 기존 공유 reader를 유지하고 공통 장면 query/fill을96비트 레코드로 전송하는 exporter, 순방향96/역방향17비트 mailbox를 연결했다. 부모 전체는 컴파일만 했고 host포트는논리ready/valid다. **실제SPI/MMIO·MCU·SNES업로드/표시완료·fit·새SD는미완료.** PC수신기를펌웨어로오인하지않는다.

BEGIN→query0..5→fill바이트→END→호스트PREPARED/REJECT→COMMIT/ABORT. END는표시허가아님. 같은generation ACK시에원본lease를다시검사하고COMMIT만표시후보로승인한다. 잘못된세대ACK무시. timeout/실패시원본해제+ABORT,이미넘긴임시레코드는회수하지않는다. host멈춰ABORT미수락이면새장면시작금지. 기본전체1048576NES클록,시험262144;fill65536wait/262144total유지. 공통reset양쪽필수/수신임시데이터도flush.2FFtoggle+수신추가1edge/helddata,실제CDC STA/MTBF미검증.

host01 10사례: 이전실제SMB3봉인frame12/14/16/18/20재생+실제fill/export/CDC,backend는ROM바이트지연모델. 기존memory01공유reader/CPU기한근거재사용,새boot없음. 정상5phase/역압력/호스트clockpause/옛ACKPASS. querymiss/REJECT/ACKtimeout/END후lease취소4ABORT0COMMIT. 전송중commonreset후65535세대만COMMIT. verify01 PC수신5거부,정상286720+reset57344픽셀일치. 기존SNES명령참조연결:첫5493B6명령/이후0,5부팅영상동일이라움직임·첫레벨·FPS아님. 새SNES실행없음.

레코드kind3/gen16/index13/data64. 정상1717레코드=원시20604B,기존2226B압축위치량과혼동금지. query6전체8192는host로안보낸다. **다음:** 실제SPI/MMIO접속부+유한MCU수신/검사/PREPARED/COMMIT을연결하고유효폭·타일단위패킹/실제전송예산확정. SNES명령/vblank완료와38M9K교체를묶는다. 현재56/56M9K에추가만금지. 변경경로최소검사/실제fit뒤SMB3첫레벨실기. generic진단확장·같은boot/planes/A-B/044반복금지.164사운드/STOP메뉴유지;사용가능영상뒤60초제한/오류·본체reset로그/입력유지.

이번선택host01/verify01,실패실행없음. 이전archive/pin불변. 완료record/audit재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — 기존 ROM reader를 공유하는 CHR 보충

PR107 동일 브랜치. [연결 계약](../../docs/nes-native-memory165-contract.ko.md) · [검증 결과](../../analysis/native-memory165-verification.json). 아래 과거 인계의 PSRAM arbiter 미연결 상태를 갱신한다.

**완료:** memory01 실제 SMB3 CPU/PPU/MMC3+70ns PSRAM 모델에 공통 장면→fill→arbiter→기존 READ16 reader를 연결했다.20프레임 CPU/PPU 바이트·기한 검사 통과, 기존20출력 동일. frame12/14/16/18/20에15타일240바이트씩 총1200바이트 정확; 실제 받은 CHR로286720픽셀 일치. generation은12~16으로 frame과 다르다. 보충 뒤 전체8192 필요 비트를 진단 덤프하여 다음 프레임 수집을 건너뛴다. 제품 FPS나60fps 증명이 아니다. reader 원본 해시 유지, CPU/PPU CE/캐시 동작 무변경. 부모 joint는 동일 생성물 컴파일만 했으며 MCU/SPI/SNES 전체 실행은 아니다.

안전 구간은 NTSC/MMC3 전용: div_cpu3, PPU242<=line<260, 현재 상위ROM읽기 캐시 hit, CPU/PPU/prefetch 대기 없음, reset/pause/DMA/DMC 없음, reader준비/core새요청없음. core 우선. 응답 조건7NES클록/실제최대5; 배치STA/MTBF/모든클록·매퍼 보장 아님. arbiter01 8위상1352검사: 우선순위/금지구간/응답분리/취소배출/공통reset/메모리클록정지·회복/잘못된주소·오류 PASS. 취소·timeout으로readerreset하거나소유권풀지않는다. 공통reset은reader도함께. 보충시작/진행중hostquery차단;fill_idle은옛보충응답없음. 기존fill기본1024는유지하고이결선만wait65536,total262144,max512tiles/8192B. success는hostACK아님;임시바이트는실패시폐기.

**다음:** 같은generation의 위치/행/보충바이트를hostCDC·수신저장·업로드ACK로연결하고SNES명령소비자와38M9K픽셀버퍼교체를묶는다. 현재56/56M9K에단순추가금지. 시험의8192전체재조회는제품경로에넣지않는다. 최소변경검사/실제자원·타이밍뒤SMB3첫레벨실기. 같은20boot/planes/합성A-B/044무변경반복금지. 첫레벨·버튼·장시간부하는이번미검증. 설치후보164/163사운드/STOP메뉴유지;새SD없음. 화면·사운드확보뒤60초제한·오류/본체reset로그·입력유지.

선택memory01/arbiter01/verify01. 이번실행실패없음;이전archive/pin불변. probes/nes-native-memory165의완료record/audit재실행금지. 개인GitHub/한국어4PR절/사용자머지.

---

# NES 현재 인계 — 실제 코어의 공통 장면과 유한 CHR 보충

PR107에 추가했다. [계약·재현·다음 연결](../../docs/nes-native-frame165-contract.ko.md) · [검증 요약](../../analysis/native-frame165-verification.json).

**완료:** 새 `nes_native_frame165`가 planes/compact와 새 raster_frame을 같은 NES 클록·generation·release로 연결한다. 이전 CIRAM/OAM 스냅샷의 무변경 조건은 중복 요구하지 않는다. 실제 CPU/PPU/MMC3에 동일 BINDING을 연결한 frame03에서20프레임을 실행했고 이전 픽셀20개는 동일했다. 표시1~11은 거부,12~20은 모두224행/30BG묶음/2OBJ/2예외/7401이벤트/2226위치바이트다. 공통 조회 포트의 데이터로516096픽셀이 원본과 완전히 일치했다. 필요 물리 타일은 이 부팅 표본에서15개/240바이트다. 첫 레벨·60fps 증명이 아니다.

`geometry_valid`는 타일 바이트/호스트/SNES 준비 완료가 아니다. mask1e/연속 팔레트2버전/동일 배경색을 요구한다. 행 중간 fineX·팔레트·mode·mask 변경은 거부한다. v/t 접근은 scroll_seen으로 기록하되 전체 실제 fetch/압축/행 완성이 함께 있어야 한다. 다른 raster 오류를 무조건 무시하지 않는다. 공통 generation은 required-set의16비트 번호만 사용하며 공유 release가 모두 취소한다. 첫 raster 행 이전 ROMfault로 PPUCE가 멈춰도 실패를 반환한다. query kind0..6/범위/generation 검사, error24=ROM/23:16raster/15:8compact/7:0fetch. 조회는 NES 클록 전용이다.

새 `nes_native_fill165`는 최대512물리타일/8192바이트·총262144클록·단계1024클록으로 제한한 보충 인터페이스다. 한 번에 한 요청·한 바이트만 보관하고 실제 tag/lane 주소를 쓴다. 캐시 hit 최적화는 아직 없으며 필요한 타일의16바이트 전체를 공급한다. source generation/valid, 조회, 응답 주소/번호/오류, grant·응답·sink대기와 총 예산을 검사한다. 완료 전 바이트는 임시이며 실패하면 폐기한다. 완료 뒤 lease가 취소되어도 success를 막는다. pending 취소/reset은 quarantine과 mem_abort를 거치며 **mem_idle은 미래의 옛 응답이 없다는 flush ACK**여야 한다. 단순 버스 유휴를 연결하면 안 된다. start 수락 조건과 done/clear는 계약 문서를 따른다.

선택 lease04:1740검사/9합성장면/7거부, 실제 공통조회→fill 직접 연결33타일528모델바이트 PASS. 선택 fill03:9실제필요집합+15경계/오류/취소사례 PASS, 각 정상240ROM바이트 정확. lookup와메모리backend는 모델이며 **실제 PSRAM arbiter 연결은 아직 없다.** frame03은 실제 코어 결선, 부모 전체는 컴파일만 했다. verify01은 공통query→독립픽셀 참조다. 새 SNES 모델/fit/ARM/SD는 이번에 실행하지 않았다. 기존 SNES 플레인 소비자 검증은 재사용한다.

**NEXT 최우선:** 기존 ROM서비스의 CPU/PPU 기한을 보존하는 grant/응답/flush adapter를 실제 메모리 경로에 연결한다. 무조건 보충읽기/새독립PSRAM소유자/CPU정지는 금지. 이어 같은 장면의 hostCDC·업로드ACK·SNES명령 소비자와38M9K픽셀버퍼 교체를 묶어 구현한다. 현재56/56M9K에단순추가금지;PC전체이벤트/VRAM그래프를그대로이식하지않는다. 최소변경검사/실제fit뒤 SMB3첫레벨실기로간다. 이미 통과한 같은20프레임/플레인관측/합성A-B/044는 무변경 반복하지 않는다.

164 사운드·STOP메뉴/설치후보 유지. 실기 영상이 사용 가능해진 뒤60초 제한·오류/본체리셋 로그·장시간입력유지. 개인GitHub/한국어4PR절/사용자머지. 과거archive/pin/완료record 불변. 실패보존:frame01/02는선언컴파일,lease01은합성행간격을줄여33복사클록위반,fill01은signed -1비교 검사기오류. lease02/03·fill02통과도보존했고완료뒤취소조건을보강한최종04/03선택. FLOAT 라이선스 문제 없음. 모델의fill클록수/기본예산은물리WCET/속도증명이아니다.

---

# NES 현재 인계 — 분할 경계 타일 누락 해결

PR107에 이어서 기록했다. [계약·재현·다음 구현](../../docs/nes-native-planes165-contract.ko.md) · [검증 요약](../../analysis/native-planes165-verification.json).

**원인 확정:** 원본 PPU는 같은 BG 타일에서 저·고 플레인을 서로 다른 fine Y로 읽는다. NES 193행의 dot216에서는 1→0(표시185행28열), dot232에서는 0→1(30열)이다. 실제 BgPainter 66,528쌍의 입력·로드 레지스터를 대조했다. 기존 7개 거부의 직접 원인은 수집기의 동일 행 강제 조건이었다. 특정 CPU 쓰기 명령의 인과까지 추적하지는 않았다.

새 `nes_native_planes165.sv`는 같은 물리/논리 타일·속성·위치의 BG만 허용하고 bit56(혼합 표시), bit55:53(저 fine Y)을 추가한다. 고 fine Y는 bit15:13을 유지한다. 다른 타일/은행과 혼합 OBJ는 거부한다. 새 `nes_native_compact_planes165.sv`의 예외 표는 20비트×최대128개다. 첫 열·128/129개 경계·형식 거부 시험을 통과했다. 논리 RAM은 28,384비트(+384)이며 실제 M9K/LAB/타이밍은 미확인이다. 기존 pinned fetch/compact/raster/164는 보존했다. 이전 소비자는 확장 비트를 모르므로 그대로 연결하지 않는다.

`pair01`은 실제 20프레임 관측이다. `planes01`은 같은 에지·간격을 재생해 새 fetch→compact를 직접 연결했다. **새 생산자를 실제 게임 인스턴스에 직접 결선한 시험은 아니다.** 표시12~20프레임 전부 7,401이벤트/30 BG묶음/2 OBJ/2 예외/2,226 위치바이트를 보존했고 원본516,096픽셀과 일치했다. 기존 수집기를 함께 재생하면 이전 7개 오류04가 재현되며 정상 이벤트는 전부 동일하다. 6개 오류 주입과 `limits01`의 6개 새 형식 사례도 통과했다. 완성 CHR는 PC ROM이 공급했으며 기판 보충은 미구현이다.

`snes01`은 서로 다른12→15번째 화면114,688픽셀이 일치했다. 처음5,493바이트/6명령, 변경22바이트/2명령이며 vblank226행에 완료했다. 추가 blank는 없었다. 부팅 표본이므로 애니메이션 최악량/FPS/첫 레벨 증명으로 확대하지 않는다. 이전 `stream02`의 전체20프레임 픽셀·이벤트·행 상태·판정은 정확히 재현됐다. 관측 스크립트 문자열만 정리하고 Python AST 동일성을 확인했다. RTL 실행 후 기능 변경은 없다. 원시 로그/실행 소스/판독값은 비공개 보존했다.

**NEXT:** 혼합 셀 문제는 닫고 수정 수집기·압축기·raster를 같은 세대의 게시 경로로 연결한다. 접근 자체를 거부하는 raster 오류10은 실제 셀/행 표현 계약에 맞춰 연결하며 모든 경우에 무시하지 않는다. 유한 물리 CHR 보충 → host CDC/업로드 ACK/실제 SNES 소비자 → 기존38M9K 픽셀 버퍼 교체/최소 fit → 실제 SMB3 첫 레벨 순서다. 현재56/56M9K에 단순 추가할 수 없다. 이번 PC 가공과 완성 CHR 공급을 실기 구현으로 오해하지 않는다. 같은 부팅/타일 관측/합성 A-B/044를 변경 없이 반복하지 않는다.

164 사운드·STOP/메뉴·설치 후보를 유지하며165 패키지는 없다. 이후60초 제한·오류/본체 리셋 로그·장시간 입력 유지를 다룬다. 개인 GitHub·한국어4개 PR 항목·사용자 머지를 유지한다. 완료된 private record를 재실행하거나 과거 archive를 수정하지 않는다. 첫 실행은 샌드박스 호스트 식별 차이로 중단되어 기존 FLOAT를 호스트에서 실행했다. 새 라이선스는 필요하지 않았다. 테스트 컴파일 오류는 없고 의도적 거부는 통과 조건이다. 기록 도중 LF 정규화 해시와 원본 CRLF 해시를 혼동한 검사기는 구분 필드를 추가해 바로잡았으며 실제 시험 결과에는 영향이 없다.

---

# NES 현재 인계 — 온라인 압축과 실제 분할 경계 확인

PR107에 추가했다. [계약·검증·다음 순서](../../docs/nes-native-compact165-contract.ko.md) · [검증 자료](../../analysis/native-compact165-verification.json).

온라인 생산자는33BG셀 비교/최대32행그룹,128OBJ조각,128fine Y예외만 저장한다. 데이터RAM28000비트는 논리량이며 실제M9K/LAB/타이밍은 아직 모른다. 같은 행을 재사용하고 평가순위별 OBJ를 합치므로 전체 이벤트 버퍼/정렬 그래프는 없다. 변경 BG행을33클록 복사하는 동안 새 BG가 오면 보류한다. 소유권·범위조회·release/새 빈 세대·시작 오류·용량 초과를 포함한10사례 PASS. 실제 게임 이벤트 간격 재생이며 게임 인스턴스에 새 압축기를 직접 결선한 실행은 아니다.

실제 SMB3 부팅20프레임에서1~11은 표시 비활성,12~20은mask1e였다.13·17의7401이벤트는30BG그룹/2OBJ/2fineY예외로2226바이트 위치정보가 됐다. 원본 PPU와 완전 일치했고 PC RowConsumer→실제SNES 모델 두 화면114688픽셀도 일치했다. 두 화면은 서로 같아서 첫5493바이트/6명령 후0바이트다. 움직임 대역폭/FPS로 확대하지 않는다. 첫 레벨이나 버튼 입력은 이번 대상이 아니다. 완성 CHR는PC가ROM에서 공급했으며 기판 보충 구현이 아니다.

실제185행(NES193행)에서 일부 셀만fineY가 달라 기존 참조의 행 전체 동일 조건이 실패했다. 새 예외 RAM과파생패턴2개로 보존한다. 기존 rastererror10은 접근 자체 거부라PC참조에서만 별도로 해석했고 다른 오류는 거부했다. 이전 pinnedraster/보드 게시게이트는 그대로다. 실제 gate를 완화하기 전 per-cell데이터와행상태가 함께 완전하다는 계약을 연결해야 한다.

**NEXT 최우선:**12/14/16/18/20프레임의185행28열,15/19의185행30열에서fetch오류04로BG1셀이 빠진다. 첫 거부의 실제 저/고 물리·논리주소/설명자와 실제 PPU 플레인을 관측해 원인을 확정하고 합법적 혼합이라면 제한된 예외로 표현한다. 분할 VRAM변경과 관련된 것으로 추정하지만 어느 pair 비교가 실패했는지는 아직 모른다. 오류04 무시/이전타일 대체 금지. 이 수집 문제를 남긴 채 다른 진단·보충부터 늘리지 않는다.

이후 온라인 생산자 직접 결선·raster 표현 계약→물리 CHR유한보충/hostCDC/ACK/SNES소비자→기존38M9K픽셀버퍼교체/최소fit→실제SMB3 첫 레벨 순서다. 이미 평가된 fetch를 쓴다면 이전CIRAM/OAM 스냅샷의 무변경 조건을 중복필수화하지 않는다. 현재56/56M9K에단순추가금지.164사운드·STOP메뉴/설치후보유지;새SD패키지없음. 그 뒤60초 제한·오류/본체리셋로그·장시간입력유지.

stream01 선언컴파일/compact01 cell예약어/rows01 동일화면0예산거부를기대한검사기실패 보존;각02선택. 완료된 record/finalizer 재실행금지. 라이선스실패없고 FLOAT종료. 한국어4PR절/개인GitHub/사용자머지/공개pin유지.

---

# NES 현재 인계 — SNES 갱신 명령과 픽셀 대조 통과

PR107 열린 상태에 후속 구현을 추가했다. [계약·재현·한계](../../docs/nes-native-commands165-contract.ko.md) · [검증](../../analysis/native-commands165-verification.json).

`nes_native_commands165.py`는 개발 PC의 참조 소비자다. 앞선 fetch165 비트 형식과 물리 태그를 그대로 사용하여 BG행 묶음·스프라이트 평가 행 마스크/순서·패턴 슬롯·VRAM/OAM/CGRAM/HDMA 바이트를 만든다. 실제 FPGA/MCU 생산자에 연결한 것은 아니다. 전체 원시 이벤트/64KiB shadow VRAM/정렬 그래프는 PC 편의를 위한 것이며 기판에 그대로 구현하지 않는다.

선택 시험02는 실제 SNES CPU/DMA/PPU 모델에서 두 합성 장면114688픽셀이 원본 이벤트의 독립 기준과 완전 일치했다. 초기5755바이트/6명령은 blank 중 적재했고, 수평·수직 스크롤/타일/OBJ 변화는573바이트/4명령으로 vblank의230행까지 완료했다. 공개 후 추가 forced blank 없음. 변화 없는 장면은0명령.13가지 거부는 이전 게시 상태를 보존한다. 실제 SMB3 이벤트/실기 FPS/최악 전송시간 증명은 아니다. 시험01의 고정 스크롤 대조도 PASS이며 두 원시 결과를 보존했다.

BG2bpp16KiB+OBJ4bpp16KiB+64×32맵4KiB=36KiB. 이전 이중맵40KiB 제안과 달리 한 vblank에 끝나는 묶음만 받아 맵 하나를 갱신한다. `payload+96*commands<=5000`,32명령은 정책 한도이며 WCET가 아니다. 초기만 예외로 blank 적재한다. 실제 업로드 ACK 후에만 commit/슬롯 상태를 전진시켜야 한다.

제한: mask1e만,224행×33BG셀 완비,32BG행묶음/1023BG타일,128OBJ조각/512OBJ패턴/한 행32객체,팔레트2묶음/공통 배경색. 평가는 행별 실제8개에서 가져오며 OBJ순서에 순환이 생기면 거부한다. 미지원 래스터/클리핑/강조/용량 초과를 조용히 틀리게 출력하지 않는다. 원래snapshot_valid는 여전히 전체frame-ready가 아니다.

NEXT: 이 참조를 기준으로 실제 fetch/raster의 온라인 제한 생산자·물리 타일 보충을 연결하고 같은 게임 실행에서 SMB3의 지원 범위/working set/전송량을 함께 확인한다. 전체부팅만 따로 반복하거나 합성 진단 장면을 계속 늘리지 않는다. 이후 hostCDC/전송ACK/실제SNES소비자와38M9K픽셀버퍼 교체를 묶는다. 현56/56M9K에 단순 추가 금지. 최소 변경 검사·자원/타이밍 통과 후 실제 첫 레벨로 간다. 정상 사운드·STOP/메뉴를 유지하고, 이후60초 제한·오류/본체리셋 로그·장시간 입력 유지 순서다.

설치 후보164 유지, 새165 SD패키지 없음. registry 최상위에 남아 있던162후보/160실기 요약은 보관된164결과에 맞춰 정정했다. 기존 RTL/공개pin/Questa/전체적재/044복원은 변경 없이 재검사하지 않았다. 한국어4PR절/개인GitHub/사용자머지/기존FLOAT 유지.

---

# NES 현재 인계 — 실제 패턴 읽기·물리 타일·표시 위치

PR107 열린 상태에 이어서 구현했다. [계약과 다음 구현](../../docs/nes-native-fetch165-contract.ko.md) · [검증](../../analysis/native-fetch165-verification.json).

실제 BgPainter/SpriteAddressGen 적재 시점과 같은 클록의 실제 물리 CHR 주소를 묶었다. 별도 MMC3 레지스터 모사는 없다. BG는 이전 행 미리읽기 두 타일과 표시 중 뒤따르는 타일의 열 번호를 기록하고, OBJ는 실제 평가 순서/X/속성/반전이 반영된 주소를 기록한다. 물리8192타일별 BG/OBJ2비트 집합은 같은 논리 슬롯의 여러 물리 뱅크도 보존한다. 저/고 비트플레인 사이 뱅크/행/위치가 다르면 거부한다.

수집 시작은7행 dot257이다. 앞선 미리읽기 시작을 놓친 경우8행 상태/메모리 수집도 막는다. 오류가8행 이전에 나고 PPU CE가 멈춰도 공통 owned를 반환하고 조회는 차단한다. 정상은 필요 목록·기존 CHR/raster/메모리 봉인을 함께 기다린다. 기존 frozen 소스는 바꾸지 않고 시작 허용 입력을 추가한 scene 생성본을 사용한다. 공통 세대는 필요 목록의16비트 번호이며 release 후8192클록 scrub/다음7행 시작을 기다린다.

test02:26755검사·54패턴 쌍·2048실제 BgPainter픽셀(fine X0~7)·6거부시나리오 PASS. 실제 MMC3 뱅크 쓰기/반전, 실제 SpriteAddressGen8×8/8×16/flip/속성/X, 전8192타일 조회·동결·재초기화를 확인했다. 생성된 두 인스턴스 배선을 그대로 추출한 연결 시험13검사도 PASS. 전체 부모는 생성·컴파일만 했으며 연결 시험은 합성 행 일정/메모리0이다. 컴파일 오류·경고0, 시뮬레이션 오류0/미연결 시험 포트 경고44+27. test01도 통과했고 연결 검사를 추가한02를 선택했다. 앞선 실제 게임20프레임 부팅 등 변경 없는 검증은 재사용했다.

**실제 게임 속도는 아직 개선하지 못했다.** snapshot_valid는 타일 바이트와 표시 명령의 준비 완료가 아니다.64비트 fetch 이벤트는 아직 저장/소비하지 않는다. 필요 집합은 클리핑/표시 비활성 때문에 안 보이는 적재도 포함할 수 있는 보수적 집합이다. 원시 이벤트 최대9184개를 통째로 저장하면73472바이트이므로 그 버퍼나 전송을 만들지 않는다.

NEXT 실사용할 제한된 BG타일맵·OBJ·행 명령 소비자로 이벤트를 줄이고, 물리 태그별 타일 할당/부족 바이트 보충을 연결한다. 현재 논리슬롯 캐시는 여러 물리 버전이나 부분 타일을 모두 보관할 수 없으므로 hit만으로 게시하지 않는다. PSRAM 기한/기존 CPU·PPU 우선순위를 보존하는 유한 보충 예산이 필요하다. host CDC/SNES 출력과38M9K 픽셀 버퍼 교체를 함께 진행한다. 실제 자원·타이밍과 최소 변경 경계 검사 후 SMB3 첫 레벨 실기로 넘어간다. 필요 목록·좌표·메모리 수집을 다시 구현/전체 부팅 재시험하지 않는다.

설치후보164·사운드·STOP메뉴 유지. 새165 패키지 없음. 이후60초 제한·오류/본체리셋 로그·장시간 입력 유지 순서. 한국어4PR절/개인GitHub/사용자머지/기존FLOAT/기존소스pin 유지.

---

# NES 현재 인계 — CIRAM·OAM과 공통 화면 데이터 소유권

PR107 열린 상태에 후속 구현을 추가한다. [메모리/소유권 계약](../../docs/nes-native-scene165-contract.ko.md) · [검증](../../analysis/native-scene165-verification.json).

실제 CIRAM에 독립 읽기 포트를 추가하고 실제 OAMEval 배열을 조회한다. CPU 쓰기를 별도 모사하지 않아 속성 마스크·렌더링 시작8바이트 복사·렌더링 중 무시되는 쓰기를 원본대로 구분한다. NES8행 dot1부터2KB CIRAM+256B OAM을2305클록으로 복사하고,232행 dot1/ROM 오류에서 기존 CHR캐시를 동결한다. CHR 메타데이터 마무리와 기존 행 상태 봉인을 기다린 뒤 공통 owned를 올린다. 수집 중 또는 종료 경계의 메모리 변경/미완료 복사는 거부하며, 소유 중 다음 원본 변경은 고정 버퍼를 덮어쓰지 않는다. 공통 release/reset이 세 조회와 복사를 취소한다.

test02 합성7프레임6991검사/거부5시나리오 PASS. 원본 local-memory CPU/PPU/init_done을53634클록 대조했고 OAM 적재 뒤 원본과 같은 주소의 바이트도 비교했다. 두 세대2304바이트 전수 조회, 실제 OAM CPU마스크/시드한 행 복사, 무시되는 렌더링 쓰기, 비CIRAM활동, 부분CHRmiss, 실패 후 최신 바이트 재수집까지 확인했다. 컴파일 오류·경고0, 시뮬레이션 오류0/경고18(시험의 미사용 OAM 출력). test01도통과했고 추가검사한02를선택했다. 부모 보드는 생성·컴파일만 했고 실제 게임 실행/전체 기능 동등성은 아니다. 기존 CHR/행 상태RTL/앞선20프레임 게임 검증은 그대로 유지한다.

**snapshot_valid는 전체 프레임 ready가 아니다.** 일부 CHR가미완성인 valid묶음에서 실제miss를확인했다. 물리CIRAM2KB를NES논리4KB/SNES맵으로오인하지않는다. 원시Loopy·주OAM은프리페치/미러링/행별sprite평가와연결해야한다. 특히7행fetch→8행표시경계, 같은논리슬롯의여러물리뱅크·부족바이트와필요타일집합이남았다. 모든제어/조회는NES클록;host신호직결금지. 원본에없는OAM초기값도새로가정하지않는다.

NEXT 실제 BG/OBJ fetch에서 필요한 물리타일과 좌표·mapper버전을 정하고 부분CHR보충/게시조건을 연결한다. 이미 구현한 메모리관측·공통소유권·캐시·팔레트를다시만들지않는다. 이어hostCDC/SNES갱신명령으로연결하고38M9K픽셀버퍼를대체한다. 상태전체3904~4896바이트를매프레임전송하기로결정한것은아니다. 실제자원/타이밍확인과최소변경검사후실제SMB3로간다. 현56/56M9K에단순추가/무제한PSRAM읽기/기한완화금지.

설치후보164·사운드·STOP메뉴유지. 새165패키지/실기속도증명없음. 영상·음성다음60초제한해제/오류·본체리셋로그/장시간입력유지. 한국어4PR절/개인GitHub/사용자머지/기존FLOAT 유지. 완료finalizer나무변경전체부팅·적재·044/GBC재시험은반복하지않는다.

---

# NES 현재 인계 — 행별 표시 상태와 팔레트 묶음

PR107을 열어두고 같은 PR에 구현을 추가했다. [계약/패킷 형식](../../docs/nes-native-raster165-contract.ko.md) · [검증](../../analysis/native-raster165-verification.json).

실제 PPU의 Loopy v/t/fine X, 표시 마스크/패턴 모드, 실제 PaletteRam32색과 지연2006/2007 적용을 노출했다. 생성된 nes_live_joint에는 새 상태 수집기를 배선했으며 전체 코어/연결부 컴파일을 확인했다. test05는 합성9프레임1336검사/오류8시나리오, 실제 PaletteRam 쓰기·별칭·corruption 및 시드한 실제 PPU 관측 포트를 검증했다. 새로운 SMB3 실행이나 전체 보드 시뮬레이션은 아니다. 앞선 실제 부팅20프레임/CHR 수신 근거는 그대로 유지한다.

224개 행(각7바이트)과 최대32회 팔레트 버전(각32바이트)을 수집·봉인한다. 팔레트는 먼저192비트 래치한 뒤32NES클록으로 직렬 저장한다. 소유 중 원본 변경은 덮어쓰지 않고 release/reset은 조회를 취소한다. 행 누락/복사 충돌/버전 초과/수평 변경을 거부한다. ROM 오류는 PPU CE가 멈춰도 NES클록에서 실패 묶음으로 즉시 닫는다. 16비트 세대는 순환하며 무한 고유 번호가 아니다.

**state valid는 전 화면 ready가 아니다.** v/t는 원시 Loopy 값이며 프리페치 진행분을 보정하지 않은 SNES 스크롤로 사용하면 안 된다. CHR와 상태 lease는 아직 독립이다. OAM/타일맵·MMC3 뱅크 버전·부분CHR·실제 픽셀 파이프라인·host CDC/SNES 소비자는 미완료다. 상태 데이터1600~2592바이트는 다른 화면 데이터와 전송 비용을 제외한 값이며 FPS/합성 메모리 증명이 아니다.

NEXT 실제 OAM/타일맵·BG/OBJ 필요집합과 CHR/state 공통 세대를 구현한다. 이미 된 팔레트/행 수집·캐시·부팅을 무변경 반복하지 않는다. 필요한 부족바이트/같은 슬롯 뱅크 버전을 해결하고 host전달/SNES 표시로 연결, 기존38M9K 픽셀 버퍼 대체 후 최소 검증·실제SMB3로 간다. 56/56M9K에 단순 추가하거나 무제한 PSRAM 읽기/CPU·PPU 기한 완화는 하지 않는다. 수평 변경 거부가 SMB3의 필요한 분할을 막는지는 실제 fetch와 함께 확인해야 한다.

설치 후보164/사운드/STOP메뉴 유지, 새165패키지 없음. 정상 영상·음성 다음60초 제한/오류·본체리셋 안전로그, 장시간 입력 유지 순서 유지. attempt01/02 생성기 선언 형식 실패와04의 복합오류를 하나만 기대한 검사 실패를 보존했다. 최종05 컴파일 오류·경고0/시뮬레이션 오류0·경고39(원본3+시험의 미사용 출력36). 기존 FLOAT 사용, 불필요한 라이선스/전체적재/044/GBC 반복 금지. 한국어 PR4절·개인계정·사용자 머지 원칙 유지.

---

# NES 현재 인계 — 실제 PPU와 CHR 캐시 연결

PR107을 열어둔 채 같은 PR에 후속 구현을 추가한다. [연결 계약](../../docs/nes-native-tap165-contract.ko.md) · [정확한 결과](../../analysis/native-tap165-verification.json).

test03 실제164 CPU/PPU/MMC3/70ns 모델로 SMB3 부팅20프레임을 실행했다. 강제 PPU 일정 대신 같은 에지 논리주소·물리주소·수신바이트·valid를 캐시에 연결하고 모든512슬롯의 BG16/OBJ32 응답을 검사했다. 캐시를 동결해 읽는 동안에도 게임은 계속 실행한다. 원본 ROM 수신값과 비교했고, 기존 코드 보존은 추가관측의 역변환 검사로 확인했다. 수신 비활성 전체재실행은 하지 않았다. MCU 적재/버튼/첫 레벨 플레이/실기 시험은 아니다.

관측 포트를 추가한 NES/probe와 캐시 연결문을 실행 검증했다. nes_live_joint도 같은 연결문으로 생성/컴파일했지만 전체 보드 PLL/SPI/호스트와 함께 실행하지는 않았다. 원본164 파일은 변경하지 않았고 추가 부분을 제거하면 원래 바이트로 복원된다. 기존 독립캐시165 소스/검증은 그대로 재사용했다. 새165 설치 패키지는 없다.

NEXT 배경·스프라이트 필요타일/팔레트32색/OAM/스크롤·래스터를 같은 화면 세대로 묶고, 부분타일·한 슬롯의 여러 뱅크 사용을 해결한다. 전 화면 준비를 단순 캐시 완성 슬롯 수로 판정하지 않는다. 그 후 hostCDC/전송세대/SNES 소비자를 연결하고38M9K픽셀버퍼를 대체한다. 무제한 PSRAM읽기·CPU/PPU 기한완화·현56M9K에 단순추가는 금지. 최소 변경 검사 후 실제SMB3로 이동한다. 목표는 실기 화면 끊김 개선이며 캐시 진단 자체의 확대가 아니다.

설치 후보164/사운드/STOP메뉴 유지. 조작 가능한 영상·음성 다음60초 제한 해제·오류/본체리셋 안전로그, 그 다음 장시간 입력 유지. test01 선언순서 컴파일 실패, test02의24프레임/24576조회 통과 후 부당한 뱅크교체/완성타일 필수조건 실패도 보존했다. test03은 실제 읽힌 타일의 완성/부분/미사용 수를 측정하며 특정 게임 구간에 뱅크교체를 강요하지 않는다. 기존 FLOAT 사용, 새 라이선스/무변경 전체 적재/GBC/044 검사를 반복하지 않는다.

---

# NES 현재 인계 — 165 CHR 재사용 캐시 부품 검증 통과

사용자가 PR107을 열어둔 채 계속하도록 요청해 같은 PR에 구현을 추가한다. [부품 계약/다음 연결](../../docs/nes-native-chr165-contract.ko.md) · [검증](../../analysis/native-chr165-verification.json).

관측 전용 CHR 캐시를 구현했다. PPU 정상 수신 바이트를512논리슬롯에 보관하고 물리태그18비트/바이트완성마스크16비트로 은행전환·미완성 데이터를 거부한다. 이전 메타데이터 쓰기 완료 뒤동결, 연속쓰기우회/해제중조회취소/리셋512클록소거, SNES BG2/OBJ4 변환 포함. 추가ROM요청/게임대기 출력은 없다.

test01 실제SMB3 CHR131072바이트/8192타일,401432조회/8218음성조건 PASS. 합성 PPU샘플 일정이며 실제 CPU/PPU/mapper 실행은 아님. 같은NES클록 인터페이스만 검증. 호스트CDC/현재164연결/합성배치/SNES실행/실기판은 미완료. 일부만 보이는 타일은 관측만으로 완성되지 않으므로 필요한집합+부족바이트보충을 해결해야 한다.

NEXT 실제 샘플의 논리chr_addr·같은에지 물리주소/데이터/valid 연결(지연된 debug out_ppumem_addr 금지), 팔레트/OAM/래스터·필요타일집합·부족데이터 경로, 호스트동결세대/CDC/SNES소비를 최소로 연결한다. 무제한 PSRAM읽기나 CPU/PPU기한완화 금지.38M9K픽셀버퍼 대체로 자원을 회수할 후보이며 현56/56에 단순추가하지 않는다. 최소변경 검사 후SMB3 이동/점프/스크롤.

설치 후보는164 유지, 새165펌웨어/패키지 없음. 사운드/STOP메뉴·동결근거 보존. 기존FLOAT래퍼로한번실행 완료,라이선스스모크반복없음. unusable영상 개선 다음60초제한/오류·리셋로그/입력유지 순서. 사용자머지·한국어4PR절·개인GitHub 유지.

---

## 이전 조사/형식 프로토타입 기록

# NES 현재 인계 — 사용자 참고 자료 반영과 CHR 형식/용량 프로토타입

PR107은 아직 미머지이며 이번 결과를 같은 PR에 추가한다. [후속 설계](../../docs/nes-native-video-feasibility.ko.md) · [검증 범위/출처](../../analysis/nes-native-video-feasibility.json).

Nested는 PC 패키징과 SNES 런타임을 분리해 참고한다. 우선 참고는 PocketNES/NesDS이며 FCEUX는 XBuf/전체 텍스처 출력과 CPU 비용 대조다. 사용자 PDF2쪽은 타일 재사용/가장자리 갱신 원칙에 반영했고, NES 기법을 SNES 전송 성능으로 오인하지 않는다. 기존 OAM DMA/scroll/IRQ를 다시 만들지 않는다.

실제 목표 ROM CHR8192타일/바이트고유5529. 2bpp만88464바이트라 전체 상주 불가. BG2bpp/OBJ4bpp 배치 변환1048576픽셀 비교와 잘못된 순서 대조군 통과. 후보VRAM40KiB/가정트래픽1056·4128·13344바이트는 정적 계산, 실제 작업집합/FPS/FPGA fit/SNES 실행 증명 아님.047tap은 스프라이트off·scroll0 진단이며164에는arm0, 기존 palette tap은BG16색뿐이다.

NEXT 실제 상태/물리CHR 식별·캐시 세대와 읽기 경로를 정해 최소 관측/소비 구현으로 간다. CHR 적재 시 변환 가능성을 검토하되 PSRAM 추가읽기가 CPU/PPU 기한과 충돌하지 않게 한다. 38M9K 픽셀 버퍼 대체의 회수 가능성과 두 구조 동시 유지 불가를 구분한다. NES8×16→SNES OBJ 변환/행별 선택·우선순위/MMC3분할/맵240↔256 래핑을 누락하지 않는다. 필요한 변경 검사 후 실제SMB3, 범용 재작성/새 장기 진단 없음.

새165 RTL/펌웨어/빌드/패키지 없음. 기술 후보164, 사운드/STOP메뉴/동결근거·971공개핀 보존. usable AV 다음60초 제한/오류·본체리셋 안전로그/장시간 입력 유지. 한국어4PR절·개인GitHub·사용자머지 유지.

---

## 아래는 앞선 조사 기록

# NES 현재 인계 — 164 이후 화면 전송 조사와 방향 결정

PR106 머지 `a467be7e1e2dc15f2e9fb83dce71330917188d5c` 확인. [공개 구현 비교·결정](../../docs/nes-video-transfer-research.ko.md) · [고정 출처와 계산](../../analysis/nes-video-transfer-research.json).

사용자 요청으로 변경 타일 구현 전에 조사했다. 완성 픽셀의 고정 좌표 차분만으로 연속 화면을 해결하는 안은 채택하지 않는다. 기존 청크에 순수 데이터88/896타일만 들어가며, 스크롤하면 넓은 영역이 바뀔 수 있다. 실제 변경률은 미측정. Project Nested/PocketNES/NesDS의 CHR·맵·스크롤·OAM 갱신 방식을 참고해 **SNES 그래픽 기능을 활용하는 최소 SMB3 경로의 적용 가능성을 다음에 확인한다.** retro-go의 LCD 차분/프레임 스킵이나 MiSTer 직접 영상 출력은 SNES 대역폭 증명이 아니다.

NEXT: 현재 PPU/매퍼의 실제 상태/패턴을 관측·전달할 경계, MMC3 상태창/CHR 전환, SNES 배경/스프라이트 모드·VRAM·RAM/LAB·수직공백 예산을 좁은 범위로 설계한다. 기존 CPU/PPU/APU/MMC3 실행 의미와163SPC/162오디오/STOP메뉴를 유지한다. 최소 갱신 묶음/오버플로/전송기한 검사 후 실제 SMB3 이동·점프·스크롤로 확인한다. 프레임 끝 레지스터 하나로 중간 전환을 대신하거나 타이틀 절감률로60fps를 주장하지 않는다. 수용 불가라면 구체적인 제약을 남기고 픽셀 스크롤 재사용/차분을 비교한다. 모든 매퍼·범용 진단을 새 선행조건으로 만들지 않는다.

조사/문서만 변경. 새165 RTL·펌웨어·빌드·실기 패키지 없음, 기술 후보는164 유지. native 표시의 자원/호환성/속도는 미확정.164 끊김·DOWN 유지 미시험·60초 제한 상태 그대로. 화면/사운드 다음은60초 해제와 오류/본체리셋 안전로그, 이어 장시간 입력 유지. 동일164/044/GBC/사운드전용/무변경적재 반복 없음. 동결 근거·공개핀·완료finalizer 보존, 사용자 머지/한국어4PR절/개인계정 유지.

---

## 아래164 당시 NEXT는 위 조사 결정으로 대체

# NES 현재 인계 — 164 검정 구간 제거 통과, 갱신 지연으로 플레이 불가

[164 실기 결과](../../analysis/GAME164-HARDWARE-RESULT.ko.md) · [로그 분석](../../analysis/game164-hardware-verification.json)

사용자: 반복 검정 구간 없어짐, 소리는 정상 같음, 심한 끊김으로 정상 플레이 불가. 기본 조작은 정상 같으나 DOWN 유지는 이번 미시험. 영상: 첫 레벨 이동·점프, 끝 파일 메뉴 확인. 6B/E5·393216바이트 적재/비교·100연속레코드, run/ROM/first/stop 오류0, A9/FLG20 성공. 펌웨어 실행60.650초, 정지→메뉴준비3.140초. 정상 예산 종료이며 실제 메뉴 복귀도 영상 확인. screen281신뢰0/카메라29.97은 게임FPS 아님. pad127중16/111덮어쓰기, DOWN/NONE으로 유지 판정 금지.

**NEXT PR106 머지 후 영상 전송량·전체 화면 갱신 지연 개선.** 11수직공백/57344바이트+준비대기 병목은 그대로라 검정 제거만으로 연속 화면 완료가 아니다. 기존 GBC 표시 경로·메모리/전송 예산을 비교하고 최소 변경 검증 뒤 실제 SMB3. 수직공백을 넘는 청크 확대나 무근거 전체이중버퍼 금지(LAB3/M9K0). 163SPC/162audio·STOP/menu 보존. 화면 개선 후60초 제한 해제·오류/본체리셋 안전로그, 이어 장시간 입력 유지. 같은164/044/GBC/사운드전용/무변경적재 재시험 없음. 새165 구현은 이번 결과 커밋에 섞지 않는다.

결과만 기록, 새 빌드/패키지 없음. frozen1642148파일 manifest fe8ba3b92fb4c410c12db75e3528c3f440692ad6e8d817f578c717c1b038ca8b 및 공개핀 불변. 완료finalizer 재실행 금지. 사용자머지·한국어4PR절·개인GitHub 유지.

---

## 아래는 제작 당시 기록 — 실기 대기 상태는 위 결과로 대체

# NES 현재 인계 — 164 반복 점멸 제거 실기판

[164 결과](../../analysis/GAME164-RESULT.ko.md) · [실기 안내](../../docs/nes-game164-instructions.ko.md) · [검증](../../analysis/game164-verification.json)

PR105 머지 확인.163 사용자 사운드·플레이 성공 유지.164는 최초 전체DMA/검정 초기화만 유지하고 이후 화면을 켠 채5632×10+1024를11번의 수직 공백에 전송한다. 끝까지 읽은 뒤에만 동결 프레임을 해제한다. 매 수직 공백마다 패드를 읽고, 새 프레임 대기 중에도 계속한다. 전체 화면 동시 교체·60fps 아님; 부분 갱신/지연 남고 전체 갱신은 더 빨라졌다고 주장하지 않는다. DOWN 유지 해결 미확인.

최종 client05: NTSC 실제SNES CPU/SPC, ready3/17지연, 각2개RGB 완전일치(캔버스256×239 총244736픽셀/활성229376), 모든 가시DMA·VRAM쓰기는수직공백/최종읽기259줄, 매프레임pad17/31, SPC A9.163대조군재소거거부. MCU1393입력 동일/이름치환으로163 host13/status54 재사용;새ARM188828/NMI15stores0calls. ROM809/2048바이트만 갱신,47로직/배치보고서 불변;MAP/FIT/STA 없음.6B/E5/A9 고유164식별아님: 반드시firmware/FPGA함께적용.162 setup.121/hold.177/960LAB56M9K/전체IO 등한계 그대로.

NEXT 실제164 SMB3 첫 레벨에서 반복검정구간·사운드·이동점프·메뉴, 두TXT+짧은영상. 실기 결과 뒤 전송량 감소를 통한 전체 갱신 지연 개선; 이후60초 해제·오류/본체리셋 로그 → 장시간 입력 유지. 디버그 확장/무변경전체적재/사운드전용/044GBC 반복 없음. 현재60초·리셋로그미구현·부분갱신 명시. 검사용239/224캔버스오인·메모리callback 종료/ARM DLL623 실패 및client04편집중실행 보존;최종05만출처고정. 기존동결/공개핀/완료finalizer 불변. 사용자머지·한국어4PR절·개인계정 유지.

---

## 이전163 결과 — 다음 작업은 위164 시험으로 대체

# NES 현재 인계 — 163 사운드·플레이 통과, 다음은 연속 화면

[163 실기 결과](../../analysis/GAME163-HARDWARE-RESULT.ko.md) · [로그 분석](../../analysis/game163-hardware-verification.json)

사용자 직접 청취: 사운드 정상, 플레이 정상. 영상 표본: 첫 레벨 진입·이동·점프 확인. 6B/E5,393216바이트 적재·비교,104레코드, run/ROM/first/stop 오류0. SPC A9/FLG20 읽기 확인1; screen_error169는 성공. 펌웨어 실행60.650초, STOP 뒤메뉴준비3.130초. 로그상 STOP/base/menu 준비 성공; 영상 끝은 월드맵으로 실제 파일메뉴 복귀는 이번 세션 별도 미확인. 기침은 외부음으로 제외, 독립 청취·전체음질 측정 아님.

**NEXT PR105 머지 후 연속 화면 개선.** 사운드 무음 목표는 이번 실기 통과했으므로 사운드 전용 진단을 더 늘리지 않는다.163 SPC/FLG 초기화·162 음성 경로를 보존하고 전체57344 DMA 강제블랭크/hold6의 화면 갱신 경로를 개선한다. LAB3/M9K0, 최소 변경검증 후 실제 SMB3. hold0만으로 완료 판정 금지. 그다음60초 제한 해제·오류/본체리셋 안전 로그 → 장시간 입력 유지 평가. DOWN 유지/연속 화면 아직 미해결, 현재60초 유지/리셋로그 미구현. pad306 마지막16/290덮어쓰기, screen405신뢰0으로 FPS 아님. 무변경163사운드/044/GBC/전체적재 재시험 없음.

이번은 결과만 기록, 새 빌드/패키지 없음. frozen163 2510파일 manifest d8626eade5547e594de623d7077d153eeff5482b2cdea59940a499785209bfc5 및 공개핀/완료finalizer 불변. 사용자머지·한국어4PR절·개인GitHub 유지.

---

## 아래는 제작 당시 기록 — 실기 대기 상태는 위 결과로 대체

# NES 현재 인계 — 163 본체 사운드 초기화 실기판

[163 결과](../../analysis/GAME163-RESULT.ko.md) · [실기 안내](../../docs/nes-game163-instructions.ko.md) · [검증](../../analysis/game163-verification.json)

PR104 머지 확인.162 첫 레벨·복귀 성공/무음에 대해163은 본체 SPC/DSP 유한 초기화·FLG20 확인을 추가했다. GBC89바이트 payload, NES native ABI/DP10, 본문670/ROM2048. FPGA 로직·배치 불변, generatedMIF만 검증교체/update_mif/ASM으로 갱신한다. 원본HEX만 바꾸면 반영되지 않아 RBF 동일 검사가 거부했던 실패도 보존.6B/E5는162 로직 재사용에 따른 의도된 ID이며 무조건 여러ID 허용 아님.

실기 로그 A9와spc_unmute_confirmed1은 FLG20 읽기 확인, 실제 청취 성공 아님. E1~E5 실패에도 화면 진행. 기존 screen_error는163에서 초기화 상태로 재사용하므로169를 게임 오류로 해석하지 않는다.0/미지값은 미확인; 이전162 잘못 적용도 성공 처리 안 함. 실패FLG 원시값/아날로그활동은 아직 미관측.

Mesen 실제CPU/SPC 정상+5주입 실패/각2정확RGB+14패드; 상태RTL54위상·늦은쓰기/SPI/STOP/reset; MCU13회수/256입력/512상태판정; ARM188824/NMI15stores0calls 통과.47개 로직·배치보고서 정확재사용, 새MAP/FIT/STA없음.14711LE/960LAB/56M9K, setup+.121/hold+.177 및 전체IO/MTBF/PCB/reset 한계 유지. client01/02 경로 오류·asm01 반영누락/asm02 CRLF검사실패 보존.

NEXT 실제163 음악·효과음/첫 레벨/두TXT/메뉴 확인. 소리가 없으면 초기화 결과부터 분기하고 최소 APU/DAC 활동만 필요시 관측. 이후 연속 화면 → AV 확인 뒤60초 해제·오류/본체 리셋 로그 → 장시간 입력 품질. 현재 화면·60초·DOWN 문제 그대로, warm reset·아날로그 소리 미검증. 동결163과 이전 자료/공개핀/044 불변, 완료finalizer재실행 금지. 사용자머지/한국어4PR절/개인GitHub, 동일162/044/GBC/무변경 전체부팅 반복 없음.

---

## 이전162 실기 결과 — 다음 구현은 위163으로 진행됨

# NES 현재 인계 — 162 플레이·복귀 통과, 무음 수정 우선

[162 실기 결과](../../analysis/GAME162-HARDWARE-RESULT.ko.md) · [로그 분석](../../analysis/game162-hardware-verification.json)

사용자 확인: 첫 레벨 진입·정상 플레이·60초 뒤 메뉴 복귀, **소리는 나지 않음**. 6B/E5, 적재·비교393216,104레코드, run/ROM/first/stop 오류0. 실행60.660초·정지후메뉴준비3.240초. APU 차단 해제에 따른 이번 세션 회귀는 없으나 사운드 목표는 미달성. apu_channel_writes_blocked=0은 설정 상수이지 실제 음원 측정값이 아니다.

다음은 PR104 머지 후 **본체 SPC/DSP 초기화 누락부터 확인**한다.162의game-program.hex는161과 동일하며 생성기에 SPC 포트 접근이 없다. GBC base/g9_snes_io.py는 유한 업로드·FLG0x20·읽기 확인을 가진다. 원본 WRAM/ABI 그대로 붙이지 말고 NES용으로 적응하고 결과를 종료 로그에 연결한다. 실제 음소거 상태는 미측정으로 원인 확정 아님. 필요시 최소 APU/DAC 활동을 확인한다. 기존 별도 APU/DAC 모델 시험은 게임부터 본체 출력까지 검증하지 않았음을 명시한다.

이후 실제 SMB3 사운드·플레이·복귀 확인 → 연속 화면 → 사운드/화면 확인 뒤60초 해제·오류/본체 리셋 로그 → 장시간 입력 품질 순서. DOWN 유지·연속 화면 미해결, 동일162/044/GBC 무변경 재시험 없음. 현재60초 유지/리셋로그 미구현. LAB3/M9K0, frozen162·이전 핀·완료finalizer 불변. 이번은 결과만 기록; 새 빌드/패키지 없음. 사용자머지·한국어4PR절·개인GitHub 유지.

---

## 아래는 제작 당시 기록 — 실기 대기 및 다음 단계는 위 결과로 대체

# NES 현재 인계 — 162 사운드 실기판 준비, 연속 화면은 다음 구현

[162 결과](../../analysis/GAME162-RESULT.ko.md) · [실기 안내](../../docs/nes-game162-instructions.ko.md) · [검증](../../analysis/game162-verification.json)

PR103 머지 확인.161 첫 레벨 성공을 보존하며 APU 전체 쓰기(DMC 포함)와 실제 mono DAC 출력을 연결했다. 기능 시험과 새 실제 배치가 통과해162/6B/E5 패키지를 준비했다. **실제 음악·효과음은 아직 미확인**이다. 다음은 사용자 실기로 소리/첫 레벨 진행/두162TXT/메뉴 복귀를 확인하고, 이어 연속 화면 전송을 구현한다. 입력 문제만 별도 확장하는 이전 계획으로 돌아가지 않는다.

APU32주소/OAM256+256/DMC17, DAC 평균/DC제거/CDC38회/핀파형 두조건/STOP무음·재시작과 기존159/160 경계 통과.161 ROM service·frame·pad·client·PPU·mapper·reader·클록 정확재사용. 단일배치14711LE5572regs960/963LAB56/56M9K122실핀0가상1PLL. 추가지침/명목setup+.121hold+.177,조건부PSRAM+2.341/SNES199.003<270. 새음원데이터16쌍3코너max1.287ns/DAC출력5.220ns. 전체IO/MTBF/PCB2ns/reset회복 미완료. ARM188604/NMI15stores0calls/host13cases256masks. 원시 자료와 환경 실패도 동결 기록에 보존한다.

화면은 여전히161의57344전체DMA/강제소거/hold6이다. 소리만 구현한 것을 사운드·연속 화면 전체 완료로 보지 않는다. 연속 화면에 쓸 자원은 LAB3/M9K0만 남으므로 임시 관측 회로 축소와 기존 GBC 전송 구조를 우선 검토한다. hold0만으로 개선했다고 주장하지 않는다. 표시면 지연이 정해지기 전 고정 오디오 지연RAM부터 추가하지 않는다.

사운드·화면 확인 후60초 자동종료 해제와 오류/본체 리셋 시 상태보존→안전STOP→TXT닫기→메뉴를 구현하고, 장시간 실제 게임에서 DOWN유지·이동·점프·대시·동시입력을 검증한다. 현재162는60초 유지/리셋로그 미구현/DOWN미해결이다. 상세 우선순위와 리셋 저장 조건은 아래 사용자 계획을 따른다.

동결162·161이전 근거·공개핀·ROM·044복원본은 보존. 이미 완료된finalizer 재실행 금지. 같은161/044/GBC/A-B/무변경 전체부팅 반복 없음. 사용자머지/한국어4PR절/개인GitHub.

---

# NES 현재 우선순위 — 사운드·연속 화면, 이후 장시간 플레이

PR103 머지 확인: `a5da39ef5020d381f1e02eb7d1b148b6abd5264e`. 아래 계획은161 결과 인계의 **입력 유지 조사부터 시작** 지시를 대체한다.161 첫 레벨 플레이·정상 복귀 성공과 DOWN/NONE 미해결 근거는 그대로 보존한다.

1. **사운드와 연속 화면을 최우선으로 구현·실기 확인한다.** APU 채널 차단 해제만으로 음원 출력 완료라고 보지 않는다. 실제 APU 생성·보드 출력·화면과의 시간 관계를 확인한다. 화면은 hold6을0으로 바꾸는 것만으로 완료하지 않고, 전체 DMA 강제 소거와 전송 대기 때문에 생기는 끊김을 줄이는 경로를 구현한다. 기존 GBC 출력 경로와 NES 코어의 음원 출력을 먼저 대조하고, 현재56/56 M9K 안에서 가능한 방식과 필요한 임시 이력 축소를 판단한다. 사운드/화면 사이의 세부 구현 순서는 공유 자원·전송 의존성을 확인한 뒤 정하되 둘 다 입력 품질 판정보다 앞선다.
2. **사운드·화면 확인 후60초 자동 종료를 해제하고 장시간 플레이 경로를 갖춘다.** 현재 실행은1200회×50ms 관찰 후 종료한다. 이를 단순히 큰 상수로 늘리는 데 그치지 않고 오류/본체 리셋/명시적 종료로 끝나는 실행으로 변경한다. 오류·클록·통신 감시의 유한 타임아웃은 유지한다. 실행 시간과 순환 입력 이력의 overflow/덮어쓰기 표기도 장시간에 맞게 확인한다.
3. **오류 또는 본체 리셋을 계기로 로그를 저장한다.** MCU가 살아 있는 상태에서 오류/리셋을 검출하고 최초 원인·최근 입력·경과 시간을 보존한 다음, SNES/FPGA 버스를 안전하게 정지하고 TXT를 닫은 후 메뉴로 복귀한다. 정상 사용자 리셋과 오류 종료를 구분해 기록한다. 기존 로딩 진행 로그는 유지하되 정상 플레이 중 매 프레임 SD 쓰기는 추가하지 않는다. 현재 RUN 중 SD 금지 계약을 유지하고 안전 정지 후 저장한다. 본체 리셋 감지 함수가 있다는 사실만으로 NES 실행 중 보존·저장 성공을 승인하지 않는다. 리셋이 관측값을 지우기 전에 보존할 수 있는지, MCU·FPGA 클록/리셋 영향 및 리셋 해제 대기를 확인한다. MCU/저장 경로 자체가 완전히 멎거나 전원이 차단된 경우 즉시 최종 TXT 저장은 보장할 수 없으며, 필요하면 다음 부팅 복구 방식은 별도로 설계한다. 이 구분을 실기 안내에 명시한다.
4. **위 환경에서 조작 품질과 입력 유지를 충분히 실기 확인한다.** 실제 SMB3의 앉기 지속·방향 이동·점프·대시·동시 입력을 게임 화면과 소리로 판단한다. DOWN/NONE 반복 문제는 해결된 것으로 처리하지 않는다. 화면/음원 구현 중 같은 입력 경계를 만나는 경우 함께 수정할 수 있지만, 별도 입력 진단만 확장하며 출력 구현을 뒤로 미루지 않는다.

각 변경의 최소 안정성 검증 후 실제 게임 ROM으로 판단한다. 범용 디버그 확장·무변경 전체 부팅·동일044/GBC/A-B 재시험은 생략한다. 고정60초 제한 제거와 안전 감시 제거는 다른 작업이다.161 캐시/159 실제읽기/160 재개, 정상 STOP/base/menu, 이전 동결 증거·패키지·공개 핀은 보존한다. 오디오·연속 표시·장시간 플레이·리셋 로그는 현재 **계획이며 아직 구현되지 않았다**.

이번 변경은 우선순위와 인계 갱신뿐이다. 새 실기판이나 빌드 없이 다음 구현 변경과 함께 공개할 수 있도록 작업 브랜치에 남긴다.

---

## 이전161 결과 인계 — 다음 작업 순서는 위 계획으로 대체

# NES 현재 인계 — 161 첫 레벨 플레이 통과·지속 입력 조사 대기

[실기 결과](../../analysis/GAME161-HARDWARE-RESULT.ko.md) · [수치·입력 이력](../../analysis/game161-hardware-verification.json)

첫 레벨 진입·이동·점프·메뉴 복귀가 영상과 사용자 보고로 확인되었다. 대시도 사용자 확인. 실행 구간60.660초는 제목·선택·월드맵 포함이며 레벨 안에서만60초를 의미하지 않는다. 적재·비교393216바이트/104레코드/6A-E4/실행·ROM·STOP 오류0. 정상 예산 종료 후3.190초에 메뉴 준비, 영상에서 실제 복귀 확인. 오류 문맥0, historyflags1은 정상 말단 이력이다. screen_frames365는 telemetryuntrusted로 FPS로 쓰지 않는다.

사용자가 DOWN 유지 중 일어남을 보고했다. 완료된8비트 읽기 변화250건 중 마지막16개에 DOWN/NONE 반복3회가 있지만 물리 버튼과 원본 입력값은 미관측이다. 원인은 미확정. 다음은 PR103 머지 후 `$4212` busy/`$4218-$4219` 스냅샷 → `$6002-$6003` commit → CDC/current_buttons → NES strobe/read를 연결해 지속 입력이 끊기는 경계를 찾고 최소 수정 후 실기 SMB3로 확인한다.152 매hold-vblank 폴링은 이미 있고 current_buttons는 새값/reset까지 보존하므로 같은 개선을 반복하거나 폴링 공백만 원인으로 단정하지 않는다. 임의 debounce부터 넣지 않는다.

이번 요청은 결과 기록만: 새 코드/빌드/실기판 없음. 캐시161·rawread159·restart160·유한STOP/base/menu, APU 차단을 보존한다. M9K56/56과 기존 전체IO/MTBF/PCB/reset 미완료도 유지. 전체 호환성·지속 입력·연속 표시·속도·오디오·저장은 완료 아님. 사용자 머지 전 다음 구현 금지. 동결161과 이전 공개핀/ZIP/완료finalizer 불변;같은161/044/GBC/A-B/무변경 전체부팅 반복 없음.

---

## 아래는 제작 당시 인계 — 실기 대기 상태는 위 결과로 대체

# NES 현재 인계 — 161 현재 그래픽 데이터 보존·표시 대기6프레임

[161 결과](../../analysis/GAME161-RESULT.ko.md) · [실기 안내](../../docs/nes-game161-instructions.ko.md) · [검증](../../analysis/game161-verification.json) · [160 실기](../../analysis/GAME160-HARDWARE-RESULT.ko.md)

PR102 머지3100e5c78286ff93ea68168ff587512adb58b1b6 확인.160에서205FF0valid가미래217FF8응답뒤사라졌음.161은이전캐시슬롯이현재CHR주소면그슬롯보존,새응답은다른슬롯에입력. 실제수요우선/샘플기한/태그/reader변경없음. pendingPPU와같은힌트는응답클록포함중복요청억제,다른주소는허용.159rawread/160renderrestart/실제PPU/매퍼IRQ/클록모두유지. 내부태그실기미관측으로물리원인확정아님.

cache01 actualservice:정상요청응답으로초기캐시형성(내부force없음),old160 eviction+duplicate+fault2재현,new15검사PASS.8회미래fill동안현재바이트보존/다른hint응답클록허용/실제수요우선/샘플응답우회/reset/PPUCPU기한오류유지. 백엔드시각주입모델이지전체게임아님. regression01 새service와실제PPU/READ16으로16012재개정상12대조및15939정상39대조중18오류기존통계보존.

사용자화면요청:152의hold30→6만수정+161title/checksum. 매holdvblank패드수집기존유지,전체57344DMA/강제소거/반환동일. 모델두RGB화면114688픽셀동일/hold중6회씩+표시전2회=14패드전달. 의도대기60Hz약.5→.1초일뿐전송/캡처추가로10fps/60fps아님. DMAwait입력공백/강제소거점멸남음. 덜끊기는지·점멸심해지는지짧은실기영상으로판단. 기존152패드개선성과중복계산금지.

fit01/asm01 13755LE5005regs56/56M9K122pins0virtualPLL1. 추가5.5/5.3배치지침-.074FAIL보존;같은배치정확155명목SDC setup+.061hold+.159/조건부PSRAM+5.193/SNES202.028<270PASS. 실클록/falsepath/multicycle완화·재배치반복없음. PCB2ns/reset음수recovery/전체IO/MTBF미완료. host13/256;ARM188604/NMI15stores0calls;6A/E4. armcheck01구형DLL623sandbox실패,host02PASS;FLOAT정상완료. 임시이력RAM56/56으로새여유없음. APU채널차단유지.

NEXT 161폴더전체적용→NES GAME 161.nh1→첫Start/1PLAYERStart놓기→월드맵첫레벨A→이동점프. 두161TXT/메뉴복귀/짧은영상. 이전적재약3분50초참고/실행약60초상한/전체7분무반응이면중단기록. 같은160/044/GBC/A-B/무변경전체부팅반복없음. 실패시최초요구주소/응답/캐시유효비교;통과시실제이동스크롤우선후이력축소·음원복구. 첫레벨/연속표시/속도/오디오/저장미완료.

frozen161이전자료·공개핀·ZIP불변,완료finish.py재실행금지. ROM/media/binary/license/privatepaths Git금지. 한국어4PR절/개인hungrysanta-ksc/사용자머지.

---

## 이전 작업 인계

# NES 현재 인계 — 160 첫 레벨 전환 실패, 데이터 교체와 표시 지연

[160 실기 결과](../../analysis/GAME160-HARDWARE-RESULT.ko.md) · [원본 해시·16클록](../../analysis/game160-hardware-verification.json)

실기160은첫레벨A에서오류2/메뉴복귀.16.440초로시간제한아님.159dot336217000과다르게line193dot6actual205FF0/pending217FF8age1. 현재205FF0이-7~-2까지valid1,미래217FF8응답(-2)뒤같은주소가-1에valid0,0샘플오류. 기존2슬롯FIFO응답교체가현재사용중인두번째슬롯을버리는경계가우선후보;내부태그미관측이므로확정금지. 같은응답클록의217FF8중복요청도별도검토. 첫레벨플레이미완료. 마지막A포함16입력기록/전체적재대조/STOP/base/메뉴준비정상.

사용자요청:프레임끊김때문에입력타이밍을판단하기어려우니가능하면해제. 실제160game-program.hex와152생성바이트완전일치확인.30vblank화면유지/게임계속실행;입력은152부터매holdvblank전달,단DMA/프레임대기공백유지.151코드만보고입력이0.5초마다라고오판하지말것. 대기는오류검출필수아닌57344바이트전체forcedblank전송점멸완화. 단순해제는150점멸위험/60fps아님으로이번패키지는유지. 표시지연개선은후속구현범위로명시하고기존152입력개선을반복하지않는다.

NEXT actualservice에서현재205FF0이previous슬롯인경우미래217FF8fill/동시중복request를짧게재현. 현재필요바이트보존/처리중hint중복억제의근거를확인해최소수정,정상샘플기한유지후실제SMB3첫레벨. 표시보유시간·전송대기를분리하고가독성·입력유지하며화면나이줄이기;무조건hold0/blank제거금지. 동일160/044/GBC/A-B/무변경전체부팅반복불필요. APU차단유지. 연속화면/첫레벨/속도/오디오/저장미완료.

이번PR102결과기록만,새펌웨어없음. frozen160/ZIP/공개핀/완료finalizer불변. 제작시physicalfalse는역사기록,현재상태는이실기기록우선. 한국어4PR절/개인계정/사용자머지.

---

## 이전 제작 기록

# NES 현재 인계 — 160 렌더링 재개 주소 예측 실기판

[160 결과](../../analysis/GAME160-RESULT.ko.md) · [실기 안내](../../docs/nes-game160-instructions.ko.md) · [검증](../../analysis/game160-verification.json) · [159 실기](../../analysis/GAME159-HARDWARE-RESULT.ko.md)

PR101 머지7f93ac599a958d9073eb571468cc7dd8d6459ed3 확인.159 월드맵 진입·방향키 이동은 실기 통과. 첫 레벨 A전환은26.240초 뒤 line193/dot336/217000 PPU오류2이며60초 제한이 아니다. CPU03F86E 응답 뒤 reader가 빈 구간에도 현재PPUvalid0이 힌트를 막았고 실제217000 요청은 샘플3클록 전이었다.

160은 실제PPU2001 쓰기→re_sr 재개→ALE/하위래치 경계에서 같은 실패를 재현했다. 직전 ALE가 없는 짝수 패턴 읽기에 옛 하위래치가 남아 일반예측217078/70과 실제217000이 달라진다. re_sr[1]&&!re_sr[2]의 제한된 재개 구간만 보존된 하위래치와 다음상위주소를 한PPU주기 미리 예측하고 현재valid 조건을 우회한다. 가시줄/비스프라이트/지정패턴위상/빈PPUDATA pipeline으로 제한. 실제PPU주소·상태·매퍼/IRQ·서비스/reader/캐시/기한/클록·159raw CPU/DMA읽기 조건은 유지.159의 이전re_sr가 로그에 없어 실기원인 확정은 아니다.

선택test05 실제PPU결선+70ns모델:dot334/336×래치00/5A×위상0/3.5/5.5ns=12수정PASS/12예측차단대조오류2.159회귀39PASS/39대조중18오류 유지. 실제8CE초기화 뒤 unknown거부. 초기PPU위치/name/scroll/latch와CPU출력버스는 설정한 값이므로 전체게임/CPU명령/전체DMA/모든PPUDATA겹침 검증은 아니다. test01잘못된신호명 elaboration실패,02구판재현/03단일수정 탐색,04초기pipelineX발견으로 최종근거제외.05만 선택하고 이전시도보존.

fit01 명목setup-.170FAIL로배포제외. fit02 byte_count→miso_hold 및 loader state→loaded_bytes 두경로에 더엄격한5.3ns배치지침 추가. 추가예산+.076,정확155명목SDC setup+.207/hold+.138,조건부PSRAM+3.026/SNES199.984<270ns. 실제클록/falsepath/multicycle완화없음.13725LE/5005regs/122pins/virtual0/PLL1/56M9K. PCB2ns/reset release음수recovery/전체IO/MTBF한계 유지. test05와최종ASM RTLhash일치;배치만달라 기능반복불필요. ARM188604/NMI15stores0calls/host13회수256마스크. strict69/E3;APU채널차단156 유지.

NEXT:160전체SD폴더 적용→NES GAME 160.nh1→첫Start→1PLAYER Start놓기→월드맵 첫레벨에서A→레벨내 이동·점프. 두160TXT·메뉴복귀·플레이되면짧은영상. 기존적재약3분50초는참고치;60초실행상한 내 월드맵에서지체하지않는다. 044/GBC/159/A-B/무변경전체부팅 반복하지않는다. 실패하면 최초오류·16클록이 재개모델과맞는지 우선비교;추측으로캐시/중재확대금지. 통과하면 실제조작·스크롤 우선후 임시이력RAM축소·음원복구. 오디오/속도/저장/첫레벨플레이 아직미완료.

이전frozen자료·공개핀·ZIP불변,완료finish.py재실행금지. ROM/media/binaries/licenses/privatepaths Git금지. 한국어4PR절(목표/내용/결과/의미),개인hungrysanta-ksc만사용,사용자머지.

---

## 이전 작업 인계

# NES 현재 인계 — 159 월드맵 진입·이동 통과, 첫 레벨 전환 미완료

[159 실기 결과](../../analysis/GAME159-HARDWARE-RESULT.ko.md) · [해시·패드·16클록](../../analysis/game159-hardware-verification.json)

사용자 및 영상: Start로월드맵진입/방향키이동성공. A첫레벨진입의화면축소뒤오류종료/메뉴복귀. 실제레벨플레이미통과. 31.90s영상1fps전체/23~26s4fps표본,음성/모든프레임미분석. 60초제한이아님:run_first_error1/run_rom_error2,DISPLAY232680→258920=26.240s,menu262110. 펌웨어구간/영상/CPU관측카운터/FPS구분. full393216loadcompare/verified1/104records/68E2/STOPcounter75239400유지/stoperror0/baseTXT메뉴PASS. Pad33중last16,방향/SELECT/START/A+release,처음17덮어씀,마지막A/NONE. 물리클릭시각/전체입력완료아님.

다른오류:158line193dot8/217A18→159line193dot336/217000. context e70142e0:00217000 CPUvalid1/PPUvalid0/age2/busyPPU1. CPU03F86E요청-11/응답-6;reader-5/-4비었음;현재217B00→217000변경및즉시요청-3;sample0까지응답없음. 따라서CPU점유만탓하거나시간연장부터하지않는다.

중요: historyhint_valid는rawPPU힌트가아닌 nes_live_joint의 rawhint&&(rom_ppu_valid||local3A0000..3A07FF) 결과다. 마지막16클록모두0;현재CHR217B00invalid로결합조건차단됨. rawhint존재자체는미관측. 힌트비트217078→217070은actual217000과다름. faultsnapshotrender1/sprite0/ALE0/read2007write2007pipeline0/vram0078/latch00이지만이전pipeline/render/ALE전이는알수없음. 레벨전환렌더재개/PPUDATA/ALE외부하위래치와earlyaddress를우선비교. 원인확정아님.

NEXT 실제PPU/latch/service로dot333~336·빈reader·무효217078hint·새217000요청3클록전경계를짧게재현. 159rawread조건과정상CPU/DMA/PPU기한유지,안전한주소/유효시점을검토하고최소수정후같은SMB3첫레벨/A이동점프실기. 힌트단순무조건허용/전역PPU우선/샘플기한해제/무근거캐시확대금지. 부족한관측만필요시추가. 이번은PR101결과기록만,새펌웨어없음. 같은159재시험·044/GBC복원·A/B·전체부팅반복불필요. 임시M9K56/56이력축소는원인해결뒤. APU차단유지/오디오속도저장미완료.

frozen159/완료finalizer/ZIP/publicpins불변;제작당시메타physicalfalse는동결시점이고현재결과는GAME159-HARDWARE가우선. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc.

---

## 이전 제작 기록

# NES 현재 인계 — 159 매퍼 쓰기 중 ROM 읽기 차단 실기판

[159 결과](../../analysis/GAME159-RESULT.ko.md) · [실기 안내](../../docs/nes-game159-instructions.ko.md) · [검증](../../analysis/game159-verification.json) · [158 실기 이력](../../analysis/GAME158-HARDWARE-RESULT.ko.md)

PR100 머지3ef0a0714fd803bdfdfeb0c7208b4f8a84a127c5 확인.158은 새 CHR주소를 일찍 예측했지만 낮은 비트면 응답 뒤CPU03C001→옛205A18→새217A18 순서로 늦어 오류2.159는 실제raw쓰기 중 cart_pre 이전에 prg_allow가1인 구간의 불필요한 조기CPU읽기를 차단한다. rom_cpu_address_valid에 mr_int 하나 추가. 현재MMC3 prg_conflict0이며 다른매퍼 버스충돌까지 검증한 것은 아니다. pendingMMC3hint/actualmapper/IRQ/PPU/service/reader/cache/clock/consumer/pad/fault 모두158동일. 나머지FPGA/ARM은159/68/E2식별만. APU채널 쓰기 차단156 유지.

선택test04: CPU/DMA출력버스·분주위상·PPU위치를 구동하되 rawmux/쓰기/allow/earlyvalid/read/sample 결선은 실제것.12쓰기위상+초기ready/캐시를 설정한158관측경계 ×3메모리위상=39수정통과, 대조39모두불필요읽기1회/18오류2.각실행48자격조건+CPU6/DMA6정상샘플,6실행. 실제CPU명령/전체DMA재생이 아니다. 관측경계19CPU03C001→24옛205A18→29새217A18→31오류가,수정판19새217A18→24응답보관→26새주소유효→31정상으로 바뀐다.158실기rawR/W미관측이므로 물리원인 확정 아님. 오래된낮은캐시/초기busy형성은 기록창이전미확정.

test01은 reset동안분주1고정으로cpu_ce를막은시험대watchdog;test02기본위상PASS/test03초기경계추가PASS지만CPU000001;test04 PRGbank6=1E로03C001및뒤의정상읽기까지맞춤. 예전시도 보존,최종통계와혼합금지. host01 13회수/256format, reuse01식한곳+ID정확비교, ARM188604NMI15stores0calls. 기존FLOAT사용,새라이선스불필요.

fit01/asm01 LE13670/5005regs/56M9K/122pins/virtual0/PLL1. 추가5.5ns배치예산-.036FAIL. 같은배치·정확155명목SDC로setup+.095/hold+.160,조건부PSRAM+3.035/SNES202.2<270ns통과. SDC59dbe240...기존과같고실제클록/falsepath/multicycle변경없음. 추가예산실패와명목통과둘다기록. 재배치불필요. PCB2ns/비동기reset recovery음수/전체IO/MTBF한계유지. M9K56/56임시이력축소는원인해결뒤.

NEXT:159전체SD폴더 적용→NES GAME 159.nh1→첫Start→1PLAYER Start한번떼기→진행되면방향키/A/B. 두159TXT와메뉴복귀결과. 플레이되면짧은영상,같은실패영상불필요. 기존적재약3분50초참고/실행약60초상한/오류조기종료,전체7분무반응이면중단기록.044/GBC복원·158재시험·A/B·무변경전체부팅을선행조건으로반복하지않는다. 실패하면실제요청순서와최초오류를비교하고정당한CPU읽기와충돌하는지먼저확인,관측없는캐시/중재확대금지. 진행되면조작/스크롤후음원차단해제.

실기성공·정상오디오·속도·저장미완료. frozen159와이전공개핀/ZIP불변,완료finish.py재실행금지. ROM/media/binary/privatepaths/licenses Git금지. 한국어4PR절/개인hungrysanta-ksc/사용자머지. 포팅참고가이드는158에서기록한고정upstream/기존검증재사용원칙유지.

---

## 이전 작업 인계

# NES 현재 인계 — 158 예측 이후 읽기 발행 지연 확인

[158 실기 결과](../../analysis/GAME158-HARDWARE-RESULT.ko.md) · [해시·16클록 해석](../../analysis/game158-hardware-verification.json)

사용자 Start 스테이지 진입 실패/메뉴 복귀 확인. 영상14.83초 표본도 선택화면 뒤 메뉴를 확인하며 실제 스테이지 플레이는 보이지 않는다. 전체393216바이트 적재·비교,104진행기록,Start/해제2구간,STOP/TXT/base/메뉴 PASS. 같은158 재시험·추가 영상·044복원 불필요. 실기 게임은 미완료다.

핵심: 새217A18 hint가-15..-8 유효하지만 -12 이전205A10응답 때 CPU03C001이 선택된다. -11..-8 use_prefetch1/ready0. -8 낮은 비트면 정상샘플. -7 CPU응답 때 hint_valid0이고 현재PPU205A18이어서 그옛주소 요청. -5 실제PPU217A18전환, -2 옛응답 뒤 새217A18요청, 0샘플미스. 단순 예측생성실패가아니다. line193dot8/PPU상태는157과같지만문맥은e200c2f4:30217a18/CPUvalid0/age1로달라졌다. 응답+요청 행 주소는새요청임.

NEXT 최우선은 source상 불필요CPUread 자격: rom_cpu_address_valid=prg_addr[15]&&prg_allow, prg_write=mw_int&&cart_pre, MMC3 ROMallow=!prg_write. rawwrite/pre0 구간에도 allow1이라 speculative read 가능,선택mapper4 conflict0. 이경로를 실제결선으로 짧게재현하고 확인되면 rawread로정당화된요청만남기는최소수정을한다. 실제이번03C001이해당쓰기였는지는 rawRW/PC없어서미확정. cpumem_read와 busconflict/CPU-DMA sample 계약도같이검토,다른mapper까지일괄변경금지.

기존158TB는 cpumem_addr/read/address_valid를강제하고cpu_sample0, 고정writelead9클록으로실제쓰기자격결선을우회했다. 같은합성72PASS만반복하지말고실기관측lowplane->CPU->hint만료->oldbank순서를회귀사례로넣는다. 정상CPU/DMA와PPUlow/high기한 유지. 이작은수정후에도정당한읽기충돌이남으면hint보관/기한중재검토. 무조건PPU우선/옛뱅크대입/기한해제/무근거캐시확대금지. 최소변경검증뒤같은SMB3실기. M9K56/56 임시이력은원인확인뒤축소. APU차단유지/오디오미완료.

이번PR100은실기결과추가만. frozen158/ZIP/publicpins불변,완료finish.py재실행금지. game158-verification.json의physical_test=false는제작당시동결기록이고현재판정은GAME158-HARDWARE. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc/사용자머지 유지.

---

## 이전158 제작 기록

# NES 현재 인계 — 158 MMC3 변경 전 그래픽 읽기 실기 시험판

[158 결과](../../analysis/GAME158-RESULT.ko.md) · [실기 안내](../../docs/nes-game158-instructions.ko.md) · [검증](../../analysis/game158-verification.json) · [이식 참고 자료](../../docs/nes-porting-reference-guide.ko.md)

PR99 머지289674a14407459a0823b154ab425e9f731f62c9 확인.157 실기의 확정 사실은 dot8 샘플 한 클록 전 물리 CHR주소205A18→217A18 변경, 즉시 승인됐지만 응답이 늦어 오류2로 종료한 것이다. MMC3 쓰기인지 PPU 논리주소 변경인지는 로그에 없어 미확정이다. CPU 점유만 원인으로 단정하지 않는다.

158은 CPU의 mw_int/주소/데이터를 실제 cart_ce보다 먼저 관측해 MMC3 선행 조회에만 예정된8000 CHR모드/8001 CHR뱅크 값을 적용한다. 실제 mapper 레지스터·주소·IRQ·PPU·service·reader·physical-tag·샘플 기한·클록은 그대로다. ARM은 식별/이름만158로 변경.67/E1 엄격검사.156 APU채널 쓰기 차단과 기존 버튼/직전16클록 이력은 유지한다. 실기 수정 성공·오디오 완료로 표시하지 않는다.

선택 test03/host02/reuse03/arm01+armcheck02/fit02+asm01/release01.72개의 뱅크 쓰기 충돌 모델은 정상 CHR 수신,108개 preview-off는 오류2,36개 늦은 논리주소 변경은 여전히 오류2.536 commit에서 정상주소 조기변경·취소·선택/정렬·모드 검사. 실제 CPU 게임 대신 버스/strobe를 구동했고 write lead9클록 고정, 이전 CPU읽기 시작12종/메모리위상3종이다. 전체 위상/게임 성공으로 확대하지 않는다. mapperTB/로그는 별도 해시 고정(result.sources에 누락된 범위를 숨기지 않는다). test01/02도 PASS인 이전 범위. 초기 materializer/정규화 실패와 샌드박스 도구실행 제한은 별도 보존, 라이선스 교체 불필요.

새 배치13731LE/5005regs/56M9K/122physical/0virtual/1PLL. setup+.099ns,hold+.171ns,조건부PSRAM+2.997ns; 추가5.5ns 배치예산도+.099PASS. 동일155SDC를 유지하고 명목 재검사했으며 무변경 재배치는 하지 않았다. PCB2ns 가정/비동기reset recovery 음수/전체IO/MTBF 제한은 기존대로. 임시 이력 포함M9K56/56이므로 여유로 계산하지 말고 원인 확인 후 축소한다.

NEXT:158 전체 SD폴더 적용 → NES GAME 158.nh1 → 첫 Start → 1PLAYER Start 한 번 후 떼기 → 진행되면 이동/A·B. nes-progress-158.txt와nes-game-last-158.txt,메뉴복귀 여부. 게임이 진행되면 짧은 영상; 같은 실패 영상은 불필요. 이전 로딩 약3분50초는 참고치이며158 실측이 아니다. 전체7분 무반응이면 중단/기록.044/GBC 복원·157 재시험·고정뱅크·무변경 전체부팅을 선행조건으로 반복하지 않는다.

실패 시158 decoder로 최초 오류와 마지막16클록을157과 비교한다. 매퍼 쓰기와 논리주소 전환 구분이 필요하면 최소 관측만 추가한다. 예측 예외를 계속 덧대기 전에 원본 MiSTer SDRAM의 PPU/CPU 채널과 우리 PSRAM 공유 서비스의 시간 계약을 검토한다. 진행되면 조작·스크롤 먼저, 이후 음원 차단 해제. 고정 MiSTer/Mesen2 MMC3/NESTang/NESdev 자료의 확인 범위와 채택 순서는 참고 가이드에 기록했다. 다른 코어도 기존 검증 재사용→플랫폼 연결 차이→최소 검사→실제 목표ROM 순서다.

frozen158/이전 source pins/배포ZIP 불변. 완료finish.py 재실행 금지. ROM/media/binary/private paths/licenses Git 금지. PR 한국어4절/개인hungrysanta-ksc/사용자 머지. 과거157 메타데이터의hardware_pending은 동결 시점 기록이며157의 현재 실기 사실은GAME157-HARDWARE가 우선한다.

---

## 이전 작업 인계

# NES 현재 인계 — 157 주소 전환 직후 PPU 기한 오류 확인

[157 실기 결과](../../analysis/GAME157-HARDWARE-RESULT.ko.md) · [원본 해시·16클록 해석](../../analysis/game157-hardware-verification.json)

게임 진입 실패/자동 메뉴 복귀는 사용자 확인. 전체393216바이트 적재·비교,104진행기록,패드5건(NONE/START/NONE/START/NONE),16클록 이력,STOP/TXT/base가 통과했다. 게임 플레이·다른 버튼·오디오는 미완료다. 동일157 재시험·추가 영상은 불필요하다.

가장 중요한 새 근거: 상대-13에205A18 선행 요청, -8에그응답과새CPU03C001요청, -3에CPU응답, -2에busy0/ready1/PPU205A18유효1. -1에실제PPU205A18→217A18/예측205A10→217A10이함께바뀌고즉시새요청, 0에PPU샘플/응답0/유효0으로fault2. 응답+새요청동시행의transaction_address는새요청이며이전응답주소는앞선pending에서판독한다. 선행읽기누락/직전CPU점유가이번즉시원인이라는설명과맞지않는다.

line193/dot8/PPU상태60820800:28606060은156과같지만오류문맥은e30042f4:30217a18(CPUvalid1/age0)로156CPUvalid0/age1과다르다. 과거논리PPU주소/매퍼쓰기주소·값/CPU PC는없다. 같은레지스터조합매핑의소스와두물리주소의상위부분동시변경은MMC3매핑전환을유력하게하지만특정bankwrite확정아니다. 논리주소상위변경도대조한다. 사운드채널차단유지;CPU사운드드라이버영향까지배제금지.

NEXT: 실제MMC3/PPU/서비스/reader로dot8직전bank-data,bank-select/invert전환과논리주소변경대조군을짧게재현한다. 새물리주소발생부터샘플까지데이터확보를수정하고NES매퍼동작의미를보존한다. 오래된뱅크데이터대입/기한검사삭제/맹목캐시확대금지. 변경경계최소검증뒤SMB3스테이지/이동/점프실기로간다. 원인해결뒤임시3M9K관측축소·제거(현재56/56). 새대형진단틀·무변경전체부팅·同157/044/GBC/A-B반복금지.

이번PR99는결과추가만. frozen157/배포ZIP/공개pins불변;완료finish.py/publish.py재실행금지. 빌드당시game157-verification.json의physical_test=false는동결기록이며현재판정은GAME157-HARDWARE가우선. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc/사용자머지규칙유지.

---

## 이전157 시험판 준비 기록

# NES 현재 인계 — 157 실제 게임 정지 직전 이력 시험판

[157 결과](../../analysis/GAME157-RESULT.ko.md) · [실기 안내](../../docs/nes-game157-instructions.ko.md) · [검증](../../analysis/game157-verification.json)

PR98 머지5b82510 확인 후157 준비.156 Select 성공/Start 동일PPU오류는 유지된 사실이며 수정 완료가 아니다. 실제서비스에 CPU선점 대 늦은PPU주소 두 합성경로를 주면 같은156 최초오류 문맥이 나온다. 새16클록 이력은 둘을 구분하지만 실제원인재현은 아니다. 기존 스냅샷만으로 하나를 고르지 않는다.

157은 직전16 NES클록의 line/dot,상태12,전송주소,예측주소,실제PPU주소96비트를 남긴다. 오류클록 포함 후 정지;SPI77헤더/A0-BF 두48비트페이지;MCU STOP 뒤 회수해 TXT추가. fault_seen일 때만 마지막행=최초오류. 응답+새요청동시에는전송주소가새요청이며 이전응답주소는앞선기록과대조한다. 창이전/CPU PC/매퍼레지스터/응답데이터는없다. 게임/서비스/기한/패드/화면/156APU차단 기능은유지,관측제거소스정규화PASS. 새valid0도STOP/복귀계속.16x96은임시3M9K추가하여56/56가득찬상태;원인확인뒤축소/제거. 향후오디오메모리여유로계산금지.

선택test04/host02/reuse01/ARM02+armcheck02/fit02+asm01/release01. test02예약어compile/test03CPU캐시상태모델단언실패보존. fit01/arm01materializer단언수정;초기호스트샌드박스실행제한은기존호스트권한으로해결,새라이선스요구없음. nominalsetup+.055hold+.128/PSRAM조건부+3.763. 추가5.5ns배치예산-.042미달은별도보존. 클록/예외완화없음. 전체IO/MTBF미완료.

NEXT실기: NES GAME157 첫Start→1PLAYER에서Start한번누르고떼기→진행되면이동점프. Select반복불필요. nes-progress-157/nes-game-last-157와메뉴복귀여부. 같은실패영상생략가능. 새이력으로BGdot5~8예측/주소변경/CPU점유/승인/응답/캐시 첫실패경계를선택하고최소수정검증뒤같은게임으로복귀. 같은156/044/GBC/A-B/무변경장시간전체부팅금지. 이번은PPU수정판아님을명시한다.

frozen157/기존공개pins/배포ZIP불변;완료finish.py/publish.py재실행금지. ROM/media/binary/privatepaths/licensesGit금지. PR한국어4절/개인hungrysanta-ksc/사용자머지. 과거156progress.json의hardware_pending은동결당시기록이며현재156결과는GAME156-HARDWARE가우선한다.

---

## 이전156 실기 결과

# NES 현재 인계 — 156 Select 성공, Start 이후 같은 PPU 오류

[156 실기 결과](../../analysis/GAME156-HARDWARE-RESULT.ko.md) · [해시·버튼·진행 기록](../../analysis/game156-hardware-verification.json)

실제 Select 커서 이동과 메뉴 복귀는 사용자 확인. 완료된 패드 읽기15건에 SELECT04/해제4쌍과 마지막 START08/해제가 있다. 초기 START는 두 수신 구간으로 나타나지만 물리 클릭 횟수나 중복 버그는 미확정이다. A/B·이동·점프는 미확인. 입력 전체 고장 가설보다 PPU 경계 수정을 우선한다.

채널 쓰기 차단 상태에서도155와 정확히 같은 PPUerror2, e200c2f4:30217a18,60820800:28606060(line193/dot8,217A18,age1,응답·유효0)이 남았다. 음원만을 유일 원인으로 삼지 않는다. Select 통과의 원인이 음원 차단인지 APU상태/게임 분기/새 배치인지 미확정이며 CPU 사운드 코드는 계속 돈다. 진단 음원 차단을 정상 오디오 수정으로 승격하지 않는다.

NEXT: 일반 BG 상위 비트면 dot5~8의 예측·MMC3물리태그·공유서비스 승인·캐시·응답·샘플을 기존 근거로 좁힌다. 직전 점유/매퍼변경/응답지연을 구분할 수 없을 때만 최소 직전 이력을 추가한다. 원인에 맞춘 변경 검증 뒤 같은SMB3 Start→스테이지→이동·점프 실기로 돌아간다. 기한검사삭제/맹목캐시확대/음원전체재설계/모든버튼진단을 선행조건으로 삼지 않는다. 동일156/044/GBC/A-B/무변경장시간부팅 반복 금지.

이번PR98은 결과만 추가. frozen156/기존publicpins/배포ZIP 불변, 완료finish.py/publish.py 재실행 금지. 원본2TXT는 로컬 nes-game156-hardware에 별도 보관. 기존 GAME156-RESULT/검증의 physical_pending은 빌드 당시 동결 기록이며 현재 실기 판정은 위 결과가 우선한다. 새 패키지는 없다. 사용자 머지 후 다음 구현을 시작한다.

---

## 이전156 시험판 준비 기록

# NES 현재 인계 — 156 음원 차단·버튼 이력, 실제 SMB3 비교 대기

[156 결과](../../analysis/GAME156-RESULT.ko.md) · [실기 안내](../../docs/nes-game156-instructions.ko.md) · [검증](../../analysis/game156-verification.json)

155 실제 Select에서도 PPUerror2가 나고 메뉴로 복귀했다. 사용자가 사운드 시작과 겹침을 제안했다.155 외부DAC는0이지만 내부APU/DMC는활성이다. Mesen240프레임3비교에서Select는pulse1쓰기/2PLAYER변경,4015DMCenable없음;Start는이후DMCenable4회다. 참조일뿐FPGA활동·원인확정아니다. DMC만으로양쪽실패를단정하지않는다.

156은APU.CS에서읽기/4017쓰기만허용해음원채널/DMC쓰기를차단한다.전체APUreset/클록변경/ROM패치없음. OAM DMAget/put·PPU·mapper·서비스·기한·입력전달·화면전송유지. 음원상태가달라져게임분기가바뀔수있어최종수정아니다. CPU사운드드라이버는계속실행되므로실패해도그코드의ROM접근영향을배제못한다.

새패드관측은8비트완독후변화만최근16건+NESmasterticks(256tick내림)에저장한다. 맨처음완독은기준상태로기록;중복held는생략;부분/추가읽기는새완독으로기록하지않음. 사용자물리클릭/모든입력증거아니다. 오류/STOP후RAM불변,MCU76/80..8F로읽고최종TXT버튼이름/비트/시각/total을저장한다. SD쓰기RUN중금지. badauxvalid0은새gamefault가아니며기존보호·STOP는유지한다.

짧은actualAPU/DMA와실제gate추출시험,원본pad와256mask,ring260,last16,partial/overread/duplicate/STOP/SPI,actualC13recoverycases/256formatmasks,linkedARM을확인했다. 긴실제ROM부팅/155합성충돌반복없음. 초기test01필수parameter/02packageimport/03강제입력의net전파오류는test04수정;fit02setup-.437거부후ring640비트레지스터를M9K+2clockresponse로바꾸고test05통과;fit03-.093/fit04-.038/fit05-.614거부후512비트1M9K/256tick양자화test08/fit06setup-.092PSRAM-.096거부후CHECK5.5ns/activeIO12ns배치예산fit07배치선택;추가5.5ns목표-.010은미달보존,동일155실제clockSDC기준nominal07setup+.246/hold+.153/PSRAM+4.571PASS. ARM01들여쓰기Werror->ARM02수정. DLL623 sandbox호스트실행은권한부여실행으로통과,라이선스오류아님.

다음은한번156실기:첫Start선택->Select. 통과하면Select로1P복귀->Start->이동점프. nes-progress-156/nes-game-last-156와실제메뉴/장면을받는다. 같은실패는영상생략. 버튼로그로Start/Select정상완독·해제·동시입력부터확인하고PPU오류와대조한다. 정상진행해도APU원인확정/사운드완성으로승격금지. 같은155/044/GBC/A-B재시험금지.

개인용ZIP/ROM/media/licenses는Git금지. frozen156과옛publicpins는불변. 완료freezer재실행금지. 한국어PR4절(목표/내용/결과/의미),hungrysanta-ksc만,사용자머지. 표시속도·DMA입력공백·오디오·저장·외부IO/MTBF는미완료.

---

## 이전155 실기 기록

# NES 현재 인계 — 155 Select에서도 PPU 오류, 입력 이후 경계 재조사

[155 실기 결과](../../analysis/GAME155-HARDWARE-RESULT.ko.md) · [원본 해시·해석](../../analysis/game155-hardware-verification.json)

**155는 실제 정지를 해결하지 못했다.** 첫Start로선택화면,Select입력에서화살표이동대신오류후메뉴복귀.154두번째Start/스테이지전환과다른트리거다. 모든두번째버튼실패/Select비트정상수신/스테이지플레이를확정하지않는다. 사용자관찰상Select에서도실패하므로스테이지진입만재현대상으로삼지않는다. 추가영상/같은155/044/GBC/A-B재시험불필요.

실제로그64/DE/393216loadcomparePASS. ROMerror2/PPUdeadline,contexte200c2f4:30217a18:actual=pending217a18/age1/busyPPU1/readyresponsevalid0. PPU60820800:28606060:line193/dot8/render1/sprite0/bgtable0/logical0A18/latchpins18/readwrite2007=0/ALEhintaddrvalid0. dot8은BG상위비트면,normal155는dot3~6만켜므로hint0자체정상.154는dot6/0A10/217A10이나사용자트리거가다르므로lowplane해결·2dot개선으로승격금지. 이전2007영향·매퍼변경·직전점유·예측발행·캐시교체는현재스냅샷만으로미확인.

STOPcount14220446유지/stop_error0/base/safe1/최종TXT741바이트/사용자실제메뉴PASS. 104x512seq0..103;DISPLAY_NEXT232670->STOPPED237640=4970ms/MENU240800까지3160ms. 입력시각/FPS아님;screenframes9/trusted0. 기존회수경로는수용하고게임실패와분리한다.

NEXT:선택화면Start대Select에서실제패드바이트/strobe/read/shift를대조하고BGdot5~8의예측논리주소/실제주소/같은MMC3뱅크물리태그/요청승인/응답/캐시교체이력을연결한다. 패드가직접ROMerror2를생성하지않지만입력오류가게임경로를바꿀가능성은열어둔다. 주기적CPU점유/고정뱅크/강제PPU타일모델만다시통과시키지않는다. 기존소스·증거로좁힌뒤부족할때만최소직전이력. 실제게임을우선하고긴전체부팅/무조건캐시확대/기한삭제를피한다.

이번PR97에는결과·인계만추가한다.155펌웨어/FPGA/ZIP/frozen2359/manifest485444c85297c1cf610d4d2db6e77d4959827c3a51b0b7334aa6079c9f9ff654불변. 새로운구현·빌드·패키지없음. 다음구현은사용자머지후진행. 원본TXT는privateprobes/nes-game155-hardware. 한국어PR4절/개인GitHub/usermerges유지.

---

## 이전155 준비 기록

# NES 현재 인계 — 155 일반 배경 선행 읽기, 다음 SMB3 실기

[155 결과](../../analysis/GAME155-RESULT.ko.md) · [실기 안내](../../docs/nes-game155-instructions.ko.md) · [고정값](../../analysis/game155-verification.json)

PR96 머지4639d4b4e5ac2e054ebdb429b8ca410782095b56에서 시작. 다음은 NES GAME 155.nh1 한 번이다. 첫 Start로 선택 화면, 버튼을 뗀 뒤 다음 Start로 전환한다. 같은 지점에서 종료되는지, 진행된다면 방향/A/B가 동작하는지 확인한다. twoTXT nes-progress-155/nes-game-last-155와 실제 메뉴 복귀 여부를 받는다. 같은 증상이면 영상 생략 가능.154/044/GBC/A-B/변경 없는 전체 부팅을 다시 요구하지 않는다.

155는 실기154의 일반 BG line193/dot6 기한 실패를 겨냥한 선행 읽기 후보다. dot2 뒤 타일 이름이 확정된 구간에서 low/high plane 예측을 순서대로 준비한다. 실제 MMC3 lookup을 재사용하며 old PPUDATA overlap이 우선한다. 서비스의 demand priority/physical tags/READ16/샘플기한/클록/캐시크기/IRQ 입력/표시/패드 동작은 유지했다. 오류 검사를 지우거나 코어를 늦추지 않았다. 기존64비트 상태의 hint는 이제 일반 선행 읽기도 포함한다.

선택 collision01은 actual155 PPU/MMC3/service/READ16/70ns에 합성된4타일과12개 CPU상대시점을 넣어 메모리3위상,후보36조건 모두정확바이트/기한통과. 같은소스normal155만0으로강제한대조는각위상PPUerror2. 정확한154요청이력·실기원인확정·전체게임PASS 아님. 초기탐색의X는 내부reset_noSS해제전시작한모델설정문제였고 선택시험은해제대기+unknown거부를포함한다. 오래걸린154core05/초기30프레임을재실행하지않았다.

MCU155는154에서ID63/DD→64/DE와표식·경로·버전만변경. 모든소스와SPI관측기는정규화비교통과.154의실제C/FatFS/menu회수및관측기시험재사용;새host/observer전체시험을실행했다고쓰지않는다.155실제C해독960정상10비정상/ARM187124/NMI15stores0calls통과. fit01 setup+.015ns/hold+.178ns,조건부PSRAM+2.736ns/SNES203.311<270ns. 여유작음/전체IO·MTBF미완료. selectedasm01/reuse02/decoder01/armcheck01;재사용검사01의0x64전역치환실패는검사기오류다.

실기실패시새최종로그의주소/line/dot/age/2007/힌트를154와비교하고변경경계만좁힌다. successfulRUN이라도이동·점프는사용자화면으로판정. 로딩/held30vblank/DMA입력공백/무음/저장은그대로미완료다. 초기파일과동결155·옛publicpin은보존한다. 완료freezer재실행금지. ROM/ZIP/바이너리/라이선스/개인경로를Git에올리지않는다. 한국어PR4절/개인hungrysanta-ksc만/사용자머지를유지한다.

---

## 이전154 기록

# NES 현재 인계 — 154 PPU 상태 실기 회수, 일반 배경 읽기 기한 수정으로 진행

[154 실기 결과](../../analysis/GAME154-HARDWARE-RESULT.ko.md) · [실제 로그 해석](../../analysis/game154-hardware-verification.json)

154 추가 관측은 실기 수용 완료다. ROM393216바이트 적재·비교, 오류2 문맥·추가 PPU 상태 TXT, STOP/기본 FPGA/실제 메뉴 복귀가 통과했다. 게임은 실패했다. 사용자의 첫 Start는 선택 화면, 두 번째 Start는 다음 장면 진입 후 정지·복귀다. 선택 화면 기준 한 번과 전체 흐름 두 번은 모순이 아니며 중복 입력 결함으로 분류하지 않는다. 다른 버튼과 실제 스테이지 플레이는 미확인이다.

실제 오류 문맥 `e200c2f4:20217a10`은153과 같다. actual=pending0x217A10,age1,busy/PPUsample1,ready/response/valid0. 새 상태 `60818800:28404040`은 line193/dot6,render1,sprite0,bgtable0,VRAM0x0A10,latch/pins0x10,read2007/write2007파이프0,ALE/hint/address_valid0이다. dot6은 일반 배경 패턴 읽기다. 현재 ALE/address_valid/hint0은 해당 단계에서 예상되므로 곧바로 결함으로 판정하지 않는다. `$2007` 겹침 전용 힌트 확장만을 해법으로 가정하지 않는다. 파이프0으로 더 앞선2007영향까지 배제하지도 않는다.

NEXT:일반 배경 dot5→6의 논리/물리주소 유효화→공유서비스 승인→응답→샘플을 짧게 재현한다. 직전 CPU/PPU 요청 점유, 샘플 직전 MMC3 주소 변경, 백엔드 응답 위상을 구분하여 처음 어긋난 경계를 고친다. 현재 관측에는 직전 이력이 없어 이들은 가설이다. 필요한 실제 PPU/서비스 결선을 사용하되 인위적 조건 통과를 실기 원인 확정으로 올리지 않는다. 원인 없이 큰 캐시/클록 변경·기한 검사 삭제·전체110/240프레임 재시작을 하지 않는다. 최소 수정 검증 뒤 같은 SMB3 실기로 돌아간다. 추가 일반화 진단 체계나 같은154/044/GBC/A-B 시험을 요구하지 않는다.

진행104기록seq0..103,DISPLAY232670→STOPPED242030=9360ms,메뉴준비245210ms. 사용자 메뉴복귀 확인. screen_frames17/trusted0은 FPS가 아니다. 실제 PPU 상태를154 합성 모델 값60b6a800:484043fe 또는153주입문맥30217a19와 혼동하지 않는다. 이번 영상 없음; 장면 독립 확인이 아닌 사용자 관찰로 보존한다.

이번 PR96 업데이트는 결과·인계만이다. firmware/FPGA/ZIP/frozen2330/공개 도구 pin은 불변이다. 원본두TXT는private probes/nes-game154-hardware. 구현·시험판은 다음 작업이며 PR은 사용자가 머지한다. 한국어4절/개인계정 정책 유지.

---

## 이전154 준비 기록

# NES 현재 인계 — 154 PPU 오류 순간 상태 수집, 실기 대기

[154 결과](../../analysis/GAME154-RESULT.ko.md) · [설치](../../docs/nes-game154-instructions.ko.md) · [검증](../../analysis/game154-verification.json)

153은 실제 PPU 오류2 뒤 STOP·TXT·자동 메뉴 복귀에 성공했다. Start 중복이 없었고 다른 버튼은 미확인이다. 실제 문맥은 `e200c2f4:20217a10`: 요구=대기주소0x217a10/age1이며 응답·유효값이 없다. 원인은 아직 미확정이다.154는 오류 순간64비트 PPU 상태만 추가한 시험판이며 게임 정지 수정이나 플레이 성공으로 계산하지 않는다.

다음은 같은 SMB3(J)의 실기 한 번이다. `NES GAME 154.nh1` 실행 후 선택 화면에서 Start 한 번으로 WORLD1 쪽으로 간다. 사용자가 현재 선택 화면의 진입 방법을 확인했다. 초기 타이틀 연출의 입력과 구분하며 무조건 두 번 연타시키지 않는다. 두 TXT와 메뉴 복귀 여부를 받는다. 같은 증상이면 영상 생략 가능, 진행되면 방향/A/B를 확인한다. 원격 실기이므로 PC 연결을 요구하지 않는다. 같은153/044/GBC/A-B 시험이나 변경 없는30프레임을 반복하지 않는다.

154의 SPI74/75는 최초 오류 에지의 line/dot, 배경패턴/스프라이트/렌더링/ALE, read/write2007파이프, vram주소/래치/핀, hint/address-valid를 보존한다. 기존 주소 문맥과 같은 에지다. MCU는 기존 STOP와 상태 유지 검사를 통과한 뒤 읽고 보조 응답 형식 불일치는valid0으로만 남긴다. 전송/클록 보호는 유지한다. `tools/decode_nes_game154.py`로 최종 TXT를 해독한다. 상태는 요청 이력이 아니므로 이전 요청 점유나 PSRAM 정상 여부까지 단정하지 않는다.

FPGA·MCU는 새63/DD 조합이다. ROM서비스/캐시/샘플기한/매퍼/게임 입력·전송 결정은152와 같고153 복귀 수정은 유지했다. 실제보드 정보는 기존확정 Rev.D/STM32F401RCT6/EP4CE15F17C8N/IS66WVE4M16EBLL-70BLI×2를 재사용한다. 새배치 setup+.084/hold+.173,조건부PSRAM3.257ns. 전체IO/MTBF 완료아님. ARM187124/NMI/수신960정상10음성/실제C-FatFS메뉴 모델의 정상보조·잘못된ID 모두통과. 합성주입값을실제153관측값으로인용하지않는다.

실제152코어와 같은 ROM으로 Start 경로를 조사했으며 최종 범위는 검증JSON/core_investigation을 따른다. 추상5NESedge백엔드는 실제PSRAM/CDC/MCU/SNES가 아니다. 참조 Mesen의 두입력30/90은 WORLD1까지가지만 FPGA검증이아니다. 초기core01 선언순서실패,core02~04 조사설정변경을 위한 의도적중단은 제품실패·라이선스오류로분류하지 않는다. 최신 core05 결과와 이전 중단 증거는동결 investigation에 있다.

실기로그가오면 read2007파이프와 dot/렌더링/주소래치로 실패경계를선택해 최소재현·수정→같은게임으로진행한다. 추가일반화관측/무조건캐시확대/기한검사삭제는하지않는다. 스테이지플레이,표시속도,입력DMA공백,소리,저장은미완료다. 동결154와옛공개pin/ROM/GBC는보존한다. ROM/ZIP/바이너리/영상/라이선스/개인경로를Git에올리지않는다. 한국어PR4절,사용자가머지,GitHub는hungrysanta-ksc만사용한다.

---

## 이전153 기록

# NES 현재 인계 — 153 오류 회수 실기 통과, PPU 기한 원인 수정으로 진행

[153 실기 결과](../../analysis/GAME153-HARDWARE-RESULT.ko.md) · [원시 기록·해석](../../analysis/game153-hardware-verification.json)

153의오류문맥수신·TXT·STOP·기본FPGA·자동메뉴복귀를실기로수용했다. loaded/compared393216,verified1,stop_ok/base_restored1,stop_error0. RUN은실패:run_rom_error2,first_error1. **실제**문맥e200c2f4:20217a10,bit63PPUtag1,actual=pending0x217a10,age1,busy/pendingPPU1,ready/response/cpu_sample/cpu_valid/ppu_valid0,ppu_sample1. 모델주입값e200c2f4:30217a19와혼동금지.151pending0x217a18과8바이트차이지만151actual없어동일원인확정금지.

104개512byte진행기록seq0..103. LOAD완료95290/CHECK233010/DISPLAY_NEXT233020/DISPLAY_STOPPED242230/BASE243090/MENU_PREPARED245380ms. RUN구간9.210s,STOP표시→메뉴준비3.150s는MCU시각이며정확한실제화면/오류시각아님. count26415116STOP후유지. 최종PREPARED_RESET_HELD는저장시점이며사용자가후속실제메뉴복귀확인. 화면stage6/frames17/trusted0은FPS나화면정상증거아님.

사용자는이전과같은스테이지시작지점에서멈춘듯한뒤바로메뉴복귀,이번Start중복없음을확인. 다른버튼미확인. 새영상없음;정확한장면독립확인이나실제스테이지플레이PASS로승격금지. 같은153영상/실행/044복원요구불필요.

NEXT:실제SMB3Start이후0x217a10주변요청/응답/PPU샘플순서를좁힌다. 오류순간주소는맞고busyage1인데유효데이터/응답없음. 늦은요청발행,직전요청점유,선행읽기·캐시교체,백엔드응답전달을구분한다. addr일치만으로PSRAM정상/고장·prefetch원인확정금지. 현재로그엔직전이력/PPUscanline/cycle/mapperregs없음. 초기30프레임만무변경반복금지;실기진입에필요한변경경계검증후같은게임으로진행. 재현부족할때만최소추가관측. 오류검사삭제/무조건캐시확대/클록늘이기로PASS만들지않음. Start중복은이번없으므로입력수정을먼저추가하지않고PPU해결후방향/A/B를확인.

이번PR95는실기결과/인계업데이트만.153firmware/FPGA/ZIP/frozen1845/공개sourcepin불변. 원본두TXT는private probes/nes-game153-hardware. 새RTL/ARM/Questa/FIT/패키지없음. 이전153수정목표달성,정상게임플레이·표시속도·DMA입력공백·소리·저장·기존IO/MTBF는미완료. 다음구현은사용자머지후새PR;한국어4절/개인계정만사용.

---

## 이전153 준비 기록 — 현재 실기 결과는 위를 따른다

# NES 현재 인계 — 153 오류 회수 수정판, 실기 결과 대기

[153 결과](../../analysis/GAME153-RESULT.ko.md) · [설치](../../docs/nes-game153-instructions.ko.md) · [검증](../../analysis/game153-verification.json)

PR94 머지 b01e7cf5926b9e637987c49cb4e135ae65416970에서 시작. 153의 다음 행동은 **SMB3(J) 한 번의 실기 실행**이다. `NES GAME 153.nh1`, `nes-progress-153.txt`/`nes-game-last-153.txt`, 화면 이후 영상·누른 버튼·첫 화면/메뉴 시각을 받는다. 사용자는 원격 실기이며 PC 직접 연결은 하지 않는다.151 첫 화면 실측 약3분50초, RUN 최대약60초/오류시조기종료, 전체7분은 사용자 관찰 상한. 기존044/GBC 반복 보고는 요구하지 않는다.

153에서 `context146()`의 `(hi[3]&0x80u)` 거부만 제거했다. 이 비트는152의PPU주소표식이다. 양쪽DC식별·유효성·오류일치/비영·버전1은 그대로. 변경4파일은run136/include,메뉴표식·파일이름,checkpoint이름,VERSION. 새하드웨어ID를 추가하지 않았고62/DC를엄격히유지한다. `fpga_n153.bi3`는152선택FPGA와바이트동일. 이수정때MAP/FIT/Questa/SNES/core반복없음. 생산자비트변경시실제수신→STOP→TXT→메뉴를확인하는공통규칙도추가했다.

선택 arm02/armcheck01/host04/context01/release01. 실제153 C+FatFS+메뉴 모델에서384KiB적재/비교와합성PPUerror2→문맥e200c2f4:30217a19→STOP→기본FPGA→TXT쓰기/읽기→64KiB메뉴→RESET해제통과. 이전비트거부조건만복원하면STOP/BASE/MENU미도달 재현. 정상문맥30/잘못된응답10통과. 전송만이전bitbang어댑터이며SPI149엔진/GPIO/시간/SD/FPGA응답은모델: 실제ARM/전기증거아님. unchanged149SPI검증재사용. ARM186852/NMI15stores0calls3DSB2ISB검사. 초기arm01문자열개수/host01-03소스위치·헤더실패보존,제품오류·라이선스아님.

**게임최초정지원인과복귀결함을분리한다.** 151은실제PPUdeadline2였지만152에는최종TXT가없어실제오류코드·문맥미확인.153은복귀결함만수정,PPU원인/Start중복입력수정완료아님. 새로그bit63=1이면low25는PPU실제요구주소(상위3비트0),0이면CPU물리주소. pending는bits46:25,age54:47. 표식은오류종류가아님. 실제와pending주소및error/age/busy/ready/response/valid를대조하고특정경계만재현한다. 주소일치/불일치만으로PSRAM원인단정금지. 모델에주입한주소를실기관측값으로인용금지.

성공수용은실제오류문맥TXT+자동메뉴복귀. 게임이WORLD1에서같이멈춰도새문맥이남으면다음원인수정으로넘어간다. 무복귀가남으면가장늦은checkpoint와컨텍스트검사/guard/STOP/base/menu중새실패경계를좁힌다. 같은152/044/A-B/변경없는전체부팅/배치반복금지. 30vblank표시/입력DMA대기공백/오디오·emphasis·저장/기존IO·MTBF제한은유지한다.

동결153 manifest와소스pin은검증JSON에있다. 완료freezer/옛증거를재실행·수정하지않는다. 새실기결과는별도hardware폴더/결과JSON에보존. ROM/ZIP/바이너리/영상/라이선스/개인경로는Git에올리지않는다. PR은한국어제목과작업목표·작업내용·작업결과·작업의미4절;사용자가머지한다. GitHub는hungrysanta-ksc만사용하고musinsa선택금지.

---

## 이전152 기록 — 현재 작업은 위153을 따른다

# NES 현재 인계 — 152 오류 문맥 수신 결함, 복귀·최종로그 실패

[152 실기 결과](../../analysis/GAME152-HARDWARE-RESULT.ko.md) · [원시 로그·재현](../../analysis/game152-hardware-verification.json)

현재152 재시험하지 않는다.83행 seq0..82,마지막DISPLAY_NEXT232740ms;LOAD/CHECK393216완료경로. 실제RUN 코드는START직전 기록,그 이후SD금지이므로 마지막행이멈춘위치라는뜻아님. 최종nes-game-last없음.94.13초영상14~15제목→16초WORLD1/MARIO×4 시작안내월드맵,이후90초대까지동일. 실제스테이지플레이미확인. 사용자프리즈후60초이상대기/메뉴FAIL/본체RESET메뉴FAIL/전원재인가메뉴PASS.14초Start1회보고;중복입력은미확정(30vblank표시샘플/held상태의다중단계소비가능). 다른버튼은정지후이므로판정불가.

확정결함:152서비스새context bit63=1(PPUactual주소) vs배포MCU context146의 `(hi[3]&0x80u)` 거부. 실제run136/context146 C를사용한host시험에서taggedPPU오류→contextfalse→fail094→leave/STOP/DISPLAY_STOPPED각0을재현. 거부한조건제거대조는각1/문맥정상,기존형식·invalidID/valid/error3개거부유지. 실제152 faultcode/context는없으므로실기관측이오류2였다고단정하지않는다. 잠재경로fail094는SNESRESET유지/cleanupbase건너뜀/finalpersistfalse로증상과부합. 게임최초정지원인과복귀실패를분리한다.

NEXT153: 기존152/frozen/패키지는그대로보존하고 MCU수신에bit63형식반영. 소스함수실제연결로 taggedPPU error→context→STOP→최종TXT·메뉴복귀 검증,잘못된응답/guard거부는유지. 같은FPGA와배치를재사용할수있으니단순MCU수정때MAP/FIT/30프레임/fullwrite/A-B/044반복금지. 이후한번의SMB3실기로actualPPU주소확보. 수신기호환시험은비트정의변경의필수경계;FPGA단위/ARM링크별개PASS로대체금지. 오류를숨기거나느슨한응답허용으로우회금지.

이번은PR94에결과/인계/공개재현도구추가만. 새firmware/RTL/ZIP없음. 공개도구 tools/reproduce_nes_game152_context.py --baseline <probes> --out <freshASCII> --gcc <hostgcc>;현재GCC는sandbox DLL WinError623일수있어허용host실행필요,라이선스아님. private probes/nes-game152-hardware에원본/188프레임/접촉시트/재현보존. 모든152 pin/manifest/ZIP불변.

---

## 이전152 제작 기록 — 위 실기 결과가 우선

# NES 현재 인계 — 152 입력 개선판 준비, PPU 원인 미해결

[152 결과](../../analysis/GAME152-RESULT.ko.md) · [설치](../../docs/nes-game152-instructions.ko.md) · [검증](../../analysis/game152-verification.json)

PR93 merged9b26d7b6a8375ff2cc10e8a6774bf5cced39d2d2.152는62/DC 조합. 사용자에게 NES GAME 152.nh1 한 번 실행, nes-progress-152.txt/nes-game-last-152.txt와 화면 이후 영상·버튼 이름·첫 화면/메뉴 시각을 받는다. 같은SMB3 ROM/384KiB 적재·대조·최대60초RUN·오류STOP/base/menu. 로딩 가속은 변경하지 않았다.151 실측 약3분50초, 실행총7분 관찰 상한이다.

**PPU 오류 수정은 미완료. 실제151 오류를 모델에서 재현한 것이 아니다.** 같은 서비스 동작을 유지하며 fault_context bit63=1일 때 low25에 실제PPU 요구주소(상위3비트0)를 기록한다.0이면 기존CPU물리주소. pending주소는bits46:25,age는54:47. bit63은주소형식표식이지오류원인아님;backenderror가동시에있으면기존우선순위가우선. 다음로그에서pending과actual을비교한다. 같으면요청기한/백엔드점유/응답,다르면주소변경·선행읽기·캐시 경계를 우선검토하되주소만으로원인확정금지. 부족할경우에만해당경계의최소추적추가.

입력은30vblank 화면유지루프에서매vblank수집. 실제SNES모델62회/8개버튼1프레임펄스PASS,기존1512회/0개;2RGB114688픽셀동일. 전체DMA/프레임대기공백의frame34펄스는여전히누락. 처음검증기가이펄스까지기대해실패한client01보존,제한을명시한client02+old01선택. 실제버튼/게임소비확인아님. 약0.2~0.5초누르고떼며제목→맵→스테이지를확인한다. 표시자체는30vblank유지이고NES로직은계속실행;60fps/음성/저장미완료.

선택asm01에fit01전체DB/소스/보고서포함.13648LE927LAB4989reg52M9K1PLL122physical0virtual;setup+.102hold+.179,조건부PSRAM+1.725ns/SNES200.273<270ns. 기존151서비스에서context배선외코드일치.6문맥경계/32768ROM주소/ARM186860 strongNMI/압축복원·패키지PASS. 전체IO/MTBF/전기실측아님. 변경없는부팅30프레임/19초전체핀모델/전량적재/044/A-B반복안함. 이번범위는입력개선+빠진오류주소,원인수정완료라고승격금지.151자료및이전공개pin보존,freezer/완료시험재실행금지.

---

## 이전151 인계 — 현재 다음 작업은 위152를 따른다

# 151 화면 성공, PPU 읽기 오류 기록

[151 실기 결과](../../analysis/GAME151-HARDWARE-RESULT.ko.md) · [원시 로그·문맥](../../analysis/game151-hardware-verification.json)

151 실제 SMB3 제목·캐릭터·갱신 및393216바이트 적재/대조/STOP/base/메뉴 복귀 PASS. 정상60초RUN은 FAIL이다. run_rom_error2(PPU 샘플 기한),first_error1(MCU 관측오류),context6200c2f4:3003f887. pendingPPU 물리0x217a18/age1/busy1/ppu_sample1/valid0/response0/ready0. cpumem_addr0x3f887은PC아님. 실제요구ppumem_addr/scanline/cycle은기존문맥에없다. pending주소가요구주소와같다고가정금지.

NEXT 같은SMB3의 제목/Start이후 PPU요청·중재·선행읽기·캐시 경계를 실제 오류 문맥에 맞춰 재현한다. 초기30프레임만무변경반복하거나기한검사를없애지않는다. 재현추적에서 부족한 PPU요구주소/시점을 확보하고 필요시에만최소실기관측추가. 이어패드수집을0.5초화면유지와분리해짧은눌림누락을줄인다. 사용자Start반응보고는보존하되자동제목전환과구분불가,다른버튼/맵/스테이지미확인. 입력전체정상/고장단정금지. 같은151/A-B/044재시험요구없음.

로그ENTRY→DISPLAY233.010초(사용자약230초와부합),RUN19.270초,MENU255.510초. 영상23.90초/약20초메뉴. 사용자35~40초는추정으로별도보존;60초타이머오류가아니라검출오류조기종료. stage6/frames34는그럴듯하나trusted0유지,원본FPS아님. flags3은STOP후reset+sticky,처음부터reset주장금지. 이번에는결과/PR93만갱신,코드·패키지·frozen151불변. 새구현은다음작업.

---

## 151 제작 시점 기록 — 위 실기 결과가 대체

[151 결과](../../analysis/GAME151-RESULT.ko.md) · [실기 안내](../../docs/nes-game151-instructions.ko.md)

## 다음 작업

사용자의151 실기 두TXT·게임 화면 영상·메뉴 복귀·실측 시간을 받는다. 표식 NES GAME 151.nh1,결과 nes-game-last-151.txt,진행 nes-progress-151.txt. 패키지 식별61/DB.150의5~6분 체감은 사용자가 철회했으므로 원인·성능 근거에서 제외한다. 다음에는 표식 실행→첫 화면 변화→메뉴 복귀를 초시계로 측정한다.

기존 소비자는 쓰기 초반 stale data를 확정할 수 있었다. 늦은 데이터 모델에서150의 A5 반환 누락·초기A5 오인식·stage0x70을 재현했고151은 /WR 종료 직전 tuple로36검사·18인과 대조를 통과했다. 실기 버스 파형을 측정한 것은 아니므로 물리 원인 확정으로 쓰지 않는다. 상태 표식은 같은 방식으로 고쳤지만 MCU의 trusted=0은 유지한다. stage/frames는 FPS가 아니다.

실제 게임 화면을30vblank(약0.5초) 유지한다. 게임 CPU/PPU는 계속 실행하며 지난 프레임은 버린다. 거친 표시·짧은 DMA 검정 구간은 예상되므로 이번에는 그림과 조작을 먼저 본다. 패드도 화면마다 수집하므로 Start/방향/A/B를 약1초 유지한다. 같은 SMB3 ROM이다. 새로운 A/B 패턴,변경 없는30프레임/전량쓰기/044복원 시험 금지.151에서도 그림이 없으면 원본PPU/고정버퍼/물리SNES수신의 최소 요약을 비교한다.

fit01:13644LE/916LAB/4986reg/52M9K/1PLL/122핀,같은클록setup+0.021/hold+0.174ns. 조건부PSRAM+3.387ns,SNES읽기201.566<270ns,배선/MTBF 미실측. 선택test01:늦은쓰기36/인과18,픽셀57344/패드80/ROM32768;client01:2프레임114688RGB. ARM01/검사02:186860바이트,61/DB명칭만변경,NMI15store0call3DSB2ISB. SPI명령60·크기0x60000/적재·비교·60초RUN/STOP/base/menu 유지. CPU/PPU/MMC3/PSRAMreader/loader/frameRAM 기존소스 재사용. ASM01/release01만사용.

실행환경 실패도 보존: FLOAT 선검사 호스트조회·objdump DLL은 sandbox실패 후 기존승인 호스트 실행으로 통과;로그 취합UTF16 인코딩 오류는 같은원문 재처리. 재시험으로 기능실패를 덮은 것이 아니다. 완료151freeze/이전archive변경 금지. verify_nes_game151.py는해시검사용. ROM·미디어·라이선스·개인경로를Git에넣지않는다. 개인hungrysanta-ksc만사용. 한국어PR4절,사용자머지.

---

## 이전150 기록 — 다음 계획은 위151이 대체

[150 실기 결과](../../analysis/GAME150-HARDWARE-RESULT.ko.md) · [검증 메타데이터](../../analysis/game150-hardware-verification.json)

## 지금 바로 할 일 — 아래의 실기 대기 기록을 대체

150의 384KiB 적재·전량 대조, 약60초 RUN 활동·관측 오류0, STOP/base/실제 메뉴 복귀는 통과했다. 게임 그림은 밝고 거의 균일한 점멸로 표시되지 않았고 조작은 미확인이다. `run_passed=1`을 게임 성공으로 해석하지 않는다. stage112/frames47/mask8은 trusted=0이며 FPS·DMA 완료 근거가 아니다.

다음은 같은 SMB3의 PPU 원본→고정 프레임→물리 SNES 읽기/DMA 결과를 최소 요약으로 구분해 첫 차단 지점을 고친다. 필요하면 실제 게임 한 프레임을 유지해 내용을 확인한다. 기존 모델은 저장된 초기30번 프레임 재생과 모델 바이트를 받은 SNES 표시를 별도로 검증했으며, 물리 동시 연결/60초 게임 정답은 검증하지 않았다. 270ns 버스 샘플 가정을 실제 DMA 구간과 대조한다. 점멸은 forced-blank 전체DMA의 영향일 수 있지만 게임 그림 부재까지 정상이라고 단정하지 않는다. 원인 확정 전 클록·맵퍼를 무작정 바꾸지 않는다.

104개 진행 기록: LOAD92.230초, CHECK137.590초, ENTRY→표시232.740초, 표시 구간60.650초, MENU_PREPARED296.550초. 사용자 체감5~6분은 별도 보존한다. 전송 대기 개선은 필요하나 현재 게임 화면의 차단 원인과 구분한다. RUN 중 SD 쓰기 추가 금지, 필요한 요약은 안전한 STOP 후 저장. 같은150 재시험·A/B·변경 없는30프레임/전체쓰기·044복원을 다시 요구하지 않는다. 다음 수정에 필요한 경계 검사 후 곧바로 실제 ROM 실기로 간다.

이번에는 결과 기록과 PR92 갱신만 수행했다. 기존150 frozen4235/패키지/공개 소스 pin 불변, 새 펌웨어 없음. 사용자 머지. 한국어 PR4절과 개인 GitHub 계정 규칙 유지.

---

## 150 패키지 제작 시점 기록 — 아래 실기 대기 문구는 위 결과로 대체

[150 결과](../../analysis/GAME150-RESULT.ko.md) · [실기 안내](../../docs/nes-game150-instructions.ko.md) · [149 적재](../../analysis/GAME149-RESULT.ko.md) · [148 코어](../../analysis/GAME148-RESULT.ko.md)

## 지금 바로 할 일

**150 패키지의 실제 SMB3 화면·Start/방향/A·B·메뉴 복귀와 두TXT/영상 확인이 다음 작업이다.** PR91은9f97bb7ae4c6a96b57d19ac2b250679edd3d3a0b로 머지됐다. 이번 별도PR은150이다. 추가A/B,동일30프레임,무변경 전량 적재,044복원 보고를 요구하지 않는다. 모든 코어는 최소 필수 경계를 확인한 뒤 실제 목표 ROM 실기를 우선한다.

표식 `NES GAME 150.nh1`,진행 `nes-progress-150.txt`,결과 `nes-game-last-150.txt`. 패키지 안의 firmware와fpga_n150은 **60/DA**만 허용한다.149의5F/D9나146과 혼용 금지.60초 유한 RUN·오류 조기 종료·STOP/base/menu·강한NMI를 재사용한다. 실기PC연결·추가부품·새라이선스를 요구하지 않는다. 사용자 제공 ROM을 포함한ZIP은 로컬전용이며GitHub에 올리지 않는다.

## 이번에 완성된 연결과 제한

최종 PPU6비트 픽셀 → 38개의512×18 RAM → SNES8bpp DMA.256×224(위아래8줄제외),한 프레임 고정·release후다음완성프레임,게임CPU/PPU는 계속 실행. 스프라이트·스크롤·CHR은행변화는 PPU의 실제 합성 결과를 사용한다. 패드 snapshot/ACK + CPU읽기 하강후 직렬이동을 연결했다.

**전체57344바이트 복사 중 forced blank이므로 검정 구간·낮은 화면갱신률이 예상된다.** 60fps/부드러운마리오 완료가 아니다. 실기에서 게임·입력 경로를 먼저 확인하고 전송량·표시 속도를 후속 개선한다. 오디오0,emphasis무시,저장지속성없음. stage/frames는 소프트웨어 표식으로 TV정상/FPS 근거가 아니다. 새로딩시간은 미측정이며5분 관찰상한 후 로그회수를 안내했다.

## 재사용할 선택 근거

video02 전체57344바이트/패드80 + 동시 덮어쓰기차단/release/recapture/reset PASS.rom01 32768주소2KiB미러·벡터·rawownership PASS.client03 실제SNES CPU/DMA/PPU에서 실제게임스냅샷+64색2프레임 RGB전부 일치. 새 CPU30프레임은 돌리지 않았고148의30프레임/CPU1425678/PPU384638/mapper468/오류0 근거를 재사용한다. 독립게임정답·실기 구동 확인은 여전히 아니다.

선택fit02:13590LE923LAB4937reg52M9K1PLL122physical0virtual.setup+0.010/hold+0.179ns.원래rawCDC/reset음수는 보존.새 호스트reset은 local2FF.패드 held-data6.516ns/2단계동기화.14hostcycle+배선가정 SNES201.355ns<270ns.ROMreader 주소17클록/CE·OE16클록 단계별 계산으로 PSRAM조건부+5.088/+0.780ns. 작고 미측정인 여유이며 전체IO/MTBF승인 아니다. 기존8µs/양클록정지CE9µs/E1E2/ACK16/124격리/source-lock4 제한 유지.

ARM02 186860bytes SHA94aa2def9f8a03fa6f297160b443308c2eed2dae1364436b66f053c71eb8ab19.149하드웨어SPI·헤더/CRC/전량대조/FINISH후START동작 유지,식별/파일명만변경.강한NMI15store0call3DSB2ISB.선택asm01 압축복원,release01 ZIP12개내부해시 PASS.펌웨어 단독검사 installable=false는 단독범위 표시이고 최종 조합만normal_trial_ready다.

## 실패 보존·다음 판단

fit01 -2.816ns 주소계산 미채택 → 32항목상수열조회+행/열합산분리.동일fit02의 초기PSRAM계산 -0.864는 주소와CE를같은16클록으로 합친보수식;동일경로표에서실제17/16구분.원래실패JSON보존,데이터시트70ns/배선여유를 줄이지 않음.초기Quartus중단/잘못된Mesen실행위치/239행RGB검사기/MCU준비역치환오류는150결과문서에 명시했다.

다음은 실제결과가 나오면 최초막힌단계를 고친다.적재/대조성공과게임화면을구분하고,물리ROM오류가있으면first-fault문맥/PSRAM경로를우선한다.게임과입력성공이면전송갱신/검정시간개선으로간다.새진단체계완성을구동조건으로추가하지않는다.

이전146~149 및150 frozen은 불변.완료freezer/전체build재실행금지.검증은verify_nes_game150.py로해시확인.공개Git에는ROM/바이너리/미디어/라이선스/개인경로없음.GBC152/NES334/기존public pin보존.한국어PR4절(작업목표/내용/결과/의미),사용자머지.개인hungrysanta-ksc만사용하며구회사계정·대화형인증fallback금지.

보드:FXPAK Pro Mk.III Rev.D/2022-05-02,STM32F401RCT6,EP4CE15F17C8N,IS66WVE4M16EBLL-70BLI×2.목표SMB3(J) SHA256 dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49,mapper4,PRG256KiB+CHR128KiB.기존StarterFLOAT1seat 래퍼와개인GitHub설정을사용한다.
