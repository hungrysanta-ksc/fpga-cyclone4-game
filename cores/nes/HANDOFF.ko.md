# NES 현재 인계 — 150 실기 게임 표시 실패, 적재·복귀 통과

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
