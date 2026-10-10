# NES 현재 인계 —138 실기 ROM deadline 실패

[138 실기 결과](../../analysis/SCREEN138-HARDWARE-RESULT.ko.md) · [관측 메타](../../analysis/screen138-hardware-observation.json)

138 실기 CPU ROM deadline 오류1을 먼저 해결한다. 동일 RTL의 클록 위상·CPU/PPU 공유 요청을 좁혀 조사하고, 미재현이면 최초 실패 주소·pending·age만 관측한다. 최초 RUN 오류를 STOP 결과와 분리해 보존한 수정 후보로 화면 실기를 재개한다. 동일138·전체 저장/부품 시험은 반복하지 않는다. 정상 화면 뒤 입력·SMB3로 진행한다.

47개 진행 기록, DISPLAY_NEXT522580ms / STOP532920ms / MENU_PREPARED536040ms. 81920바이트 적재/비교 성공, first=last=stopped123028, run_passed0/rom_error1. STOP/base/menu와 사용자 복원 성공. 이번 GBC 플레이 미보고. flags3은 STOP 이후 reset1+sticky2이며 RUN 중 reset 증거가 아니다. run_error3이 앞선 오류를 덮어썼으므로 최초 ROM 오류를 따른다. 기존138 동결 근거와 ZIP을 수정하지 않는다. 새 물리 성공으로 승격하지 않는다.

추가 재현01: 선택138 기능 입력48개 그대로, SNES반주기23.280ns/위상3.5ns·이상PLL84/168MHz·70nsRAM에서 RUN100ms/전체102.161ms·184344검사 동안 ROM 오류 미재현. 실제65816 동시 실행·배선·모든 위상을 재현하지 않았다. 위상만 바꾸거나 READ16을 줄이는 수정 근거가 없다. 다음 작업은 첫 deadline의 CPU 주소/pending 주소·소유자/age 최소 관측과 MCU 최초 오류 보존을 묶어 새 실기 후보를 만드는 것이다. 이번에는 새 펌웨어/배치를 만들지 않았다.

## 138 제작 당시 기록 — 아래 실기 대기/NEXT는 위 결과로 대체


[138 결과](../../analysis/DISPLAY138-RESULT.ko.md) · [실행 안내](../../docs/nes-display138-instructions.ko.md) · [메타](../../analysis/display138-verification.json)

138은 화면용 단일 패키지다.136의 CPU RUN/메뉴/복원은 이미 실기로 통과했다. 이제 실물의 패턴 화면을 먼저 확인하며 같은 오프라인 시험을 다시 쌓지 않는다.

138 화면 실기에서 두 TXT·패턴 표시·메뉴 복귀·044 메뉴/GBC 복원을 먼저 확인한다. 실패하면 마지막 성공 단계와 실제 화면을 근거로 해당 경계만 수정한다. 통과하면 패드 입력을 연결하고 이후 SMB3 mapper4·384KiB·플레이·오디오로 진행한다. 새 실패 없이 같은 배치·전체 적재·영상·저장 시험을 반복하지 않는다.

## 사용자에게 전달한 시험

`NES138-SCREEN-and-RESTORE044.zip`의01-SCREEN138-SD-ROOT를 SD 최상위에 복사하고 `NES SCREEN 138.nh1`(0바이트)을 선택한다. 이전136 전체 약8분12초를 참고하되 새실기는미측정. 전체10분 관찰 한도, 마지막 약10초 패턴 표시 후 메뉴 복귀 목표. 회수 파일은 `nes-progress-138.txt`, `nes-screen-last-138.txt`. 화면 사진/짧은 영상과 메뉴/044 GBC 결과를 받는다. 이전136 재시험·분해·LED·PC USB 연결을 요구하지 않는다.

## 선택본과 변경 경계

fit01/arm02/armcheck01/host07/rtl01/inventory01/sta01/io01/asm01/release01. FPGA는137fit03의 SPI59→5A 두상수/observerD4→D5 한상수만변경했고 새배치를했다. ROM/atlas/다른RTL은같다. 전체픽셀137과독립counter/bus/client 결과를재사용하며RTL138은4.152ms/21검사의변경경계만확인했다. 호스트07은실제16경로, ARM과생산소스일치·NMI확인. README나복사된예전함수명run136/094/137top을후보ID로오해하지않는다.

RELEASING 정착1ms만 RESET 양레벨을허용한다. 이후DISPLAY는RESET해제,USB IRQ차단·SD비소유·공통고장없음·DONE/RDY를요구한다. 200관측×50ms대기중1ms마다검사. 종료전RESET재유지,STOPflags2/count81920필수. 공통고장뒤추가SD/UART복구없음. `run_passed`는CPU/STOP판정이며SNES영상오류를MCU가자동수집한것이아니다.

타이밍+.305/+.177ns는같은클록범위.363heldpairs/17chains조건부통과,음수reset114행은체인비동기입력. I/O는미측정PCB가정에따른정상실기시험용이며MTBF/전기승인아님. 상세수치는138결과참조.

## 다음 수정 판단

두TXT의마지막성공단계를먼저읽는다. DISPLAY_NEXT뒤멈춤은표시진입/실행/STOP범위, DISPLAY_STOPPED후는기존base/menu복귀범위. 정상TXT인데화면이없으면SNES reset/vector/ROM read/소비자부트/packet흐름으로좁힌다. 장시간traceframework나동일전체적재를먼저만들지않는다. 화면이정상이면패드입력,이어서첫목표SMB3(J) mapper4 PRG256KiB+CHR128KiB/SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 현재고정fine_x80KiB·16KiBatlas·239행만검증,일반CHR/오디오/게임호환성은별도다.

E1/E2·8µs/양클록정지CE9µs·124격리·source-lock4·GBC152/원래NES334보존. PR제목한국어, 작업목표/내용/결과/의미4항목, 사용자머지. 동결증거044–138와완료finalizer수정금지.
