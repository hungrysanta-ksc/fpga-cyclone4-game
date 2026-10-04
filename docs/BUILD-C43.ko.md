> Historical C43 preparation record. Current: [C44 release](RELEASE-C44.ko.md), [user guide](USER-GUIDE.ko.md), [build](BUILD-C44.ko.md).

# C43 소스와 재현 빌드

## 기준

- sd2snes: `cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1`
- Gameboy_MiSTer: `7a5ff50528cd9c1d13ffb675e7df8506bffaa078`
- Quartus Prime Lite **25.1std.0 Build 1129**, Cyclone IV E EP4CE15F17C8, seed 1.
- Arm GNU Toolchain **13.3.Rel1**, 호스트 GCC 7.4.0, GNU Make, awk 및 Git Unix 유틸리티.
- Python 3.11 이상. RTC 검사는 Icarus Verilog의 iverilog/vvp.
- MCU 빌드는 Windows PowerShell에서 검증합니다. FPGA는 ASCII 경로를 사용합니다. 도구는 별도 설치하며 설치본을 배포하지 않습니다.

## 화면 출력

```text
python tools/build_renderer.py --out build/renderer
```

출력 폴더는 새 경로여야 합니다. C15 기반 생성 → C26 로딩 화면 → C40 메뉴 순으로 C43에서 사용한 `gbc_snes.bin`을 생성합니다. 외부 게임·BIOS를 입력받지 않습니다. 원본 생성기의 MCU 헤더 쓰기 부작용만 제거했습니다. 출력 SHA256이 성공본과 다르면 실패합니다. 각 생성기의 전체 출력은 빌드 폴더의 로그에 보존합니다.

## MCU

```text
python tools/prepare_firmware.py --out build/firmware
```

고정 upstream Git 객체를 가져온 뒤 변경 파일 29개를 덮습니다. 기존 clone이 있다면 `--upstream PATH`를 사용할 수 있습니다. 그 clone의 변경된 작업 파일은 사용하지 않습니다. `src/VERSION`은 성공본처럼 1.11.2로 고정합니다.

```powershell
./tools/build_firmware.ps1 -SourceRoot build/firmware -ArmBin C:/tools/arm/bin -HostGcc C:/tools/host/bin/gcc.exe -Make C:/tools/make.exe -UnixBin C:/tools/git/usr/bin -QuartusBin C:/intelFPGA/quartus/bin64
```

자신의 도구 경로로 바꿉니다. W:와 V:를 임시 사용하며 이미 사용 중이면 중단합니다. `-Drive`, `-ArmDrive`로 변경 가능합니다. mini FPGA도 pinned upstream에서 빌드합니다. 이미 검증한 mini 이미지는 `-MiniImage PATH`로 지정할 수 있으며 해시가 일치해야 합니다.

필수 컴파일 플래그는 스크립트에 고정합니다. 이름에 DIAGNOSTIC이 있는 플래그도 현재 실행·저장·진단 경로의 빌드 조건이므로 임의로 빼지 않습니다. 소스 정리 단계에서는 동작을 바꾸지 않았습니다.

upstream `genhdr`는 빌드 시각으로 헤더 4~7바이트의 버전 ID를 만듭니다. 스크립트는 **그 4바이트를 제외한 파일 전체가 C43과 일치하는지 먼저 검증**하고, 별도 `build/firmware/firmware.stm`에 C43 ID를 고정합니다. 원래 빌드 산출물은 `src/obj-g13p3/firmware.stm`에 보존합니다. 코드나 나머지 헤더가 다르면 고정하지 않고 실패합니다.

## GBC FPGA

```text
python tools/build_fpga.py --out C:/build/c43-fpga --quartus-bin C:/intelFPGA/quartus/bin64 --rle C:/build/firmware/utils/rle.exe
```

`src/fpga` 전체를 새 출력 경로로 복사하고 map → fit → sta → asm을 실행합니다. QSF·SDC를 변경하지 않습니다. 부트 초기값 누락, 음수 constrained slack, 압축 왕복 실패를 검사합니다. 결과 bitstream이 실기 성공본과 다르면 자동 대체하지 않고 실패합니다.

CGB 부트 초기값은 MiSTer의 SameBoy MIT 구현입니다. `cgb_boot_packed.mif`는 CGB에서 도달하는 2,048바이트를 압축 주소 배치로 옮긴 것입니다. 원본 MIF·고정 upstream 소스와 해시를 함께 기록합니다. FPGA 빌드에 상용 BIOS는 필요하지 않습니다. 부트 소스를 수정하려면 pinned upstream의 BootROMs/Makefile과 RGBDS/srecord 도구가 추가로 필요합니다.

## RTC 검사 및 배포 묶음

```text
python tools/test_rtc.py --out build/rtc
python tools/verify_sources.py
python tools/package_release.py --payload PATH_TO_TESTED_SD2SNES --out build/C43-rc1
```

RTC 테스트는 공개 가능한 자작 자극만 사용합니다. 상용 게임의 시뮬레이션이나 실기 대체 검사가 아닙니다. 패키저는 정확한 C43 해시의 4개 파일만 받아 업데이트 ZIP을 생성합니다. ROM·SGB 파일·세이브·원본 실험 로그를 포함하지 않습니다.
