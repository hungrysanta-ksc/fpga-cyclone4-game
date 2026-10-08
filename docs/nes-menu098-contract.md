# NES098 메뉴 주소와 실제 호출 계약

주소는 `memory.h`의 SRAM_MENU_ADDR=0xC00000만 허용한다. offset0/flags0,정확한 메뉴 경로와076 전체 CRC/64KiB 형상 조건은 유지한다. 범용 주소 범위를 넓히거나 main을0주소로 바꾸지 않는다. 새 adapter는 고정094 사본에 두 C 검사만 바꾸고, ARM 준비는 VERSION만 추가 변경한다. 기존076 materializer와044–097 동결 데이터는 편집하지 않는다.

다음 명령의 입력은 비공개094/097 동결 자료다. 공개 clone만으로 실행할 수 있는 시험이라고 표현하지 않는다. 각 출력 디렉터리는 새 경로여야 한다. Python은 `-B -X utf8` 권장이다.

```text
python tools/test_nes_menu098.py --evidence094 <094> --evidence097 <097> --out <new> --gcc <gcc.exe> --baseline
python tools/test_nes_menu098.py --evidence094 <094> --evidence097 <097> --out <new> --gcc <gcc.exe> --suite
python tools/test_nes_menu098.py --evidence094 <094> --evidence097 <097> --out <new> --gcc <gcc.exe> --geometry96 --scenario 13
python tools/test_nes_menu098.py --evidence094 <094> --evidence097 <097> --out <new> --gcc <gcc.exe> --geometry96 --scenario 14
python tools/prepare_nes_menu098_arm.py --evidence094 <094> --out <new-arm>
```

대조는 `--mutation entry-address`, `copy-address`, `prepared --scenario 10`, `postrelease --scenario 11`이다. 준비된 ARM은 `build_nes_menu098_arm.ps1`에 SourceRoot/ArmBin/HostGcc/Make/UnixBin/MiniImage 인자를 준다. MiniImage는 기존094의 동일 해시 파일을 재사용한다. `check_nes_menu098_arm.py --arm <arm> --host <final-host> --evidence094 <094> --objdump <objdump.exe> --out <json>`으로 두 C 전체 동일성, 기존094 보존 파일, ELF 호출 인자를 확인한다. 동결 확인은 `verify_nes_menu098.py --evidence <098>`이다.

실행된 main 범위는 pending if 문과 nes_return_menu_ready부터 첫 메뉴 루프 직전까지 두 원문 구간이다. 처음 부팅/card 초기화/사용자 게임 선택·화면 자체는 실행하지 않는다. firstboot=false,base 구성 완료,pending=true,USB IRQ차단,RESET유지에서 진입한다. 네이티브 SD/구성/CF86 session은097의 실제 코드/이미지 연결을 재사용한다. 메뉴 시작에60초 예산을 시작하며 전체 ROM의115/138초 모형 전송에 소급하지 않는다. RTC/CIC/타이머/MMIO/SRAM/SPI/UART 모형과 실제 원문 함수 실행을 혼동하지 않는다.

시나리오0–3/12–13 정상,4진입CICFAIL,5메뉴CRC,6메뉴readback,7CFG쓰기,8해제후CICFAIL,9해제후상태쓰기,10/11전후scratchpad128번째불일치,14해제후SDCRC.20–25잘못된 load_rom 주소/경로/플래그,26–28복사주소/offset 거부다. 실제 sram_reliable은256회 읽기를 모두 수행한다. 최초 공유오류 뒤 추가 SD/프레임/구성 접근 금지와pending/IRQ/RESET 보호를 검사한다. 하위SPI/UART/RTC 실제 보호 증명은 후속이다.

이번 ELF는 CF86-MENU098이며 선택 marker와 세션/TXT 이름은094다. 후보 식별자/프로토콜/빌드버전을 분리해 기록한다. 실기 설치 패키지로 배포하지 않는다. 새 FPGA 합성이나 ASM을 반복할 필요가 없다. 다음에는 RTC RSF/INITF 무한대기부터 실제 낮은 층 보호를 연결하고 최종 이미지/044복원쌍·외부조건·관측절차를 검토한다.
