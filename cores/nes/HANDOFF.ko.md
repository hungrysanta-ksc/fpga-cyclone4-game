# NES 현재 인계 — 실제 구성·메뉴 함수097

동일086 fit03에서 ASM/CPF로 실제 CF86 파일을 만들고, 최종094 코드로 CF86·사용자 base 구성과 메뉴64KiB 분류/복사/보고 수명주기를 연결했다. 호스트176경우와 대조5개가 통과했다.

PR46 병합 `a005137040bf77e9d18a79971eb2c84adcbb2117`, 브랜치 `codex/nes-config-images-097`. [097 결과](../../analysis/CONFIG097-RESULT.ko.md)와 [계약/명령](../../docs/nes-config097-contract.md)이 현재 기준이다. 사용자만 PR을 병합한다. 한국어 제목과 작업 목표/작업 내용/작업 결과 세 섹션을 유지한다.

## 다음 작업과 완료 조건

1. 현재097 실제 파일을 그대로 사용해 main pending-menu의 RTC·설정·상태·CIC·SRAM/SPI/UART/타이머 호출과 RESET 해제 전후 오류 처리를 연결한다. 그 뒤 동일 최종 ARM/FPGA/정확한044 복원 쌍과 외부 IO·공통 클록 고장 조건을 확정한다. `arm04/src/main.c`의 pending reload(149행), `nes_return_menu_ready`(208행), prepared/reset(272행), postrelease(302행)를 기준으로 실제 하위 호출을 연결한다.097의 `menu_flow097()`은 이 전체 코드를 실행한 것이 아니다. `memory.c` 전체 load_rom도 미실행이며 active 분류/복사 함수만 확인했다. firstboot=false·base 구성 완료·pending·IRQ 차단·RESET 유지 상태를 명시한다.
2. 메뉴 UI 복구에 필요한 RTC/cfg/status/SRAM 함수와 UART/시간 호출은 실패해도 상위 코드가 계속 호출할 수 있다. 실제 lower IO가 오류 뒤 접근하지 않는지와 prepared/reset 전후 차단을 확인한다.096/097의 stub/메모리 모델을 실제 낮은 층의 검증으로 표현하지 않는다. main60초 window는 메뉴 작업부터 시작한다. 최초 오류·SD/USB 소유권·FAILED/메뉴pending 보호를 지킨다.
3. 같은 파일로 필요한 main 통합만 추가하고 이미 통과한176경우/fit/ASM을 이유 없이 반복하지 않는다. 생산 변경 시 새 ARM와 관련 파형 근거를 만든다. 최종 ARM/CF86/base/menu/정확한044restore 각각의 해시와 marker를 함께 고정하고 외부 IO/두클록 고장 정책·화면 단계·종료/복원 조건을 확인한 뒤 설치 시험을 준비한다.

## 재사용할 완료 근거

- 동결086 fit03 전체 db/incremental_db를 복사해 새 ASM/CPF만 실행했다. RBF510856 SHA `6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1`; `fpga_n86.bi3`219453 SHA `6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805`.071 encoder 사용,089 terminalFF 추가 금지. base168440→214981은 사용자 원본/padding 그대로이며 base HDL 출처 일치 미증명.
- FAT16/SDHC80KiB와 FAT32/SDSC96KiB 각88, 총176(성공6/고장170/SD표본132)+대조5. 실제 C의 구성 출력 전체/ROM 전체/메뉴65536 byte 비교·보고 저장·prepared/released 확인. 메뉴 순서·SRAM/reset·핀·SPI응답·시간은 모델. 정상 product SD명령1532/1634, 별도 harness readback3제외, 보고native5쓰기. SD 파일에는 PREPARED_RESET_HELD, 해제 상태는UART만이다.
- 실제 native20/FatFS/checkedconfig/READY 및094 C9/ARM 그대로.094 ARM180928 SHA `70aa72fa1a70a90d501bac386ff4d159f46a12a48e15f0880c95f6fd78d208da`. 새생산C/RTL/ARM/fit/STA/Questa/실기/설치ZIP 없음.096·095·093 결과는 각각의 범위를 유지한다.095 조건부 guard 반복 재생을097 실제클록/닫힌 C-RTL 검증으로 승격하지 않는다.
- 최종 asm01/suite03/fat32-96-01, negative-config01/crc01/class01/copy01/report01. 동결 1025파일 manifest `7b60fe8e4240f46073d12a16fc2a32bb9fb807c25346d7a3f65cf0fd5e4f3e40`, verifier PASS. normal01 종료 후 harness legacy readback 실패와 suite02 CMD24에 readCRC 주입 오류를 보존했다. 이는 생산 수정이 아니다. finalizer 재실행/044–097 archive 편집 금지.

## 실기와 제품 목표

084 저장/재읽기/화면/정상044복원·메뉴/GBC,092 클록 활동/TXT/복원 PASS는 유지한다.092는 절대Hz 증거가 아니다. 이미 알려진 FXPAK Pro/Mk.III Rev.D/부품과 사용자 base/menu/044 파일을 다시 묻지 않는다. 저장/복원/LED/분해/PC USB 시험을 반복 요구하지 않는다. 실기는 외부에서 사용자가 패키지 실행 후 로그를 보내는 방식이다.

설치false, 준비도4완료/7부분/1미완료.086 fit03 2446LE/191LAB/44M9K/min0.158ns, 외부IO/공통고장 미완료 및 두클록 정지+lockHIGH CE9µs 반례 유지. 전체NES4LAB 여유·DMC·IRQ/영상/입력/음향은 [개발 계획](../../docs/nes-development-plan.json)에 남아 있다. 첫 게임은 SMB3(J), mapper4·PRG256KiB/CHR128KiB,393232바이트 SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다. 진단80/96KiB를384KiB 게임 지원으로 표현하지 않는다. ROM/바이너리/사적 증거는 Git에 넣지 않는다.
