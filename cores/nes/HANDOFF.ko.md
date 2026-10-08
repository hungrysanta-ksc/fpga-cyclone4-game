# NES 현재 인계 — 메뉴 호출 주소098

실제 main이 전달하는 메뉴 주소0xC00000을 기존 진단 보호가 거부하던 오류를 재현·수정했다. 전체 load_rom과 main 복귀 분기를 연결한26경우·4대조 및 같은 수정의 ARM 빌드가 통과했다.

PR47 병합 `1f57b10dd977e9ab26fe37dc0c48234214220002`, 현재 `codex/nes-menu-boundary-098`. [098 결과](../../analysis/MENU098-RESULT.ko.md), [계약/명령](../../docs/nes-menu098-contract.md)를 먼저 읽는다. 사용자만 병합한다. 한국어 제목/작업 목표·작업 내용·작업 결과 세 섹션 유지.

## 다음 작업

1. 098 ARM/097 이미지를 기준으로 실제 RTC의 RSF·INITF 대기와 하위 SRAM/SPI/UART/타이머·CIC/RESET 보호를 연결한다. 완료 후 최종 파일 쌍·정확한044복원본·외부IO/공통고장·관측 가능한 제한실기 절차를 확정한다. 실제 RTC `read_rtc()`의 RSF 대기와 `set_rtc()`의 INITF 대기는 unbounded다. source=`094 arm04/src/stm32f4xx/rtc.c`;098 ARM에서는 그대로다. 정상/무효RTC/정지상태/정지tick의 종료·최초 오류 전달을 검증하되 GBC 정상 경로를 보존한다. main 상위 timeout이 내부 루프를 중단시킬 수 없음을 잊지 않는다.
2. 실제 memory SRAM 함수→fpga_spi→stm32 SPI와 UART/printf/timer/CIC/reset GPIO를 기존 실제 main/load_rom에 연결한다.098 SRAM/CIC/RTC/RESET/UART/시간은 모델이다. SGB 비활성/disarm도 모델이며 실제 메뉴 렌더러/부팅/main loop는 제외다. 모델이 공급한 보호를 하위 실제 보호라고 쓰지 않는다. 공유fault 후 CFG/status 호출이 남아 있으므로 실제 lower IO 차단을 확인한다.
3. 이번 실제 main spans는 변경 없이 재사용하고 새 main 조립을 만들지 않는다. address는0xC00000이며097 모델처럼0을 넣으면 안 된다. firstboot=false/base복원/pending/IRQ차단/RESET유지에서 시작한다. main은 해제 후에도 autoboot를 읽으므로 IRQ차단·진단보호는 postrelease 안정화까지 유지한다. prepared TXT 저장이 완료돼도 해제후실패 가능하다.
4. 이후같은098이상ARM/097CF86/base/menu/정확한044restorepair,외부IO와두클록 공통고장 정책,관측절차를 묶는다. 현재 설치false이며 아직 실기 패키지를 보내지 않는다. 불필요한 fit/ASM/스토리지·클록 실기 반복 금지.

## 완료와 재사용

- 오류:076 진입/copy가0주소만 허용, 실제main은0xC00000. 원본baseline04오류16/복사0/해제0. 수정은 memory.c/nes_menu_return.c 두 검사만,VERSIONCF86-MENU098. native/CF86 C9/GBC 기존 경로 원문 보존.
- 최종suite03 24+96정상/SDCRC2=26(7정상19거부·고장),대조4. wholeload_rom·sram_reliable256회·main2구간·cfg/status/fileops 실행. 최종baseline04/96-02/negative02. 최초공유오류 후 추가SD명령/에지/CF86프레임/구성바이트없음. report5쓰기전부해제전. 준비검사·해제검사별논리오류는 sharedfault를 반드시 만들지는않음.
- ARM01 180952 SHA `31996c7cd9b2db27088cc0f455d3df49cb2c3658b765a5b619c269c2d707acf8`, ELF `419deaa8d2ef8d12ebaa50936e1bad8d3db5e20d48bb5cf478ee0b3c0fc3e108`. main인자와진입/copycmp=0xC00000확인. 실제host/ARM두C전체일치. marker `NES VERIFY 094 80.nh1`/96,보고파일094유지. 새버전펌웨어와구형094혼동금지.
- 097동일086fit03 ASM RBF510856 SHA6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1, packed219453 SHA6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805.071encoder,no089terminalFF. 사용자base168440→214981의legacyEOFpadding/HDL출처미증명유지. 메뉴65536원본동일.
- private098 동결3487파일 manifest `9ba9764205f04440d5c2259256cb07b43619733eb67f2914d459e360dea93de0`. baseline01선언컴파일오류/normal01호스트RESET전용조건오류/이전suite·대조/ARM첫Make의존성실패후재시도 보존. finalizer재실행/044–098archive수정금지.097176+5는그함수범위의근거로유지하며main성공으로표현하지않음.

## 실기·제품 목표

084저장/재읽기/화면/044복원·메뉴/GBC,092클록활동/TXT/복원PASS 유지. 추가LED/분해/부품/PC연결/이미알려진파일질문을 반복하지 않는다. 외부기기에는 사용자가 제공받은패키지를실행하고로그를보내는방식이다.

준비도4완료/7부분/1미완료·설치false.086 fit2446LE/191LAB/44M9K/min0.158ns와외부IO미완료,두클록정지+lockedHIGH CE9us반례유지. 전체NES4LAB여유/DMC/IRQ/영상/입력/음향 별개. 첫게임 SMB3(J) mapper4,PRG256KiB/CHR128KiB,393232bytes SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.80/96KiB진단을384KiB게임지원으로쓰지않는다. ROM/개인자료/바이너리/라이선스는Git에넣지않는다.
