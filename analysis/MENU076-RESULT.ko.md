# 076 — 확인된 SRTC 메뉴의 제한적 복귀 경로

## 결과와 수정 범위

075에서 재현한 **사용자 메뉴의 carttype55 거부를 수정했다.** active NES 진단 복귀에 한해 받은 64KiB SRTC 메뉴 프로필을 허용한다. 일반 게임/GBC의 기존 `smc_id`·`sgb_id` 분류는 그대로이며 active 경로는 범용 분류기를 호출하지 않는다.

고정069에서 별도 `NES-MENU076-CF68` ARM 후보를 만들었다. 이번 목표인 제한 프로필 구현·호스트 오류 검증·실제 ARM 호출 연결은 완료했다. 실제 화면 복귀와 SD 0바이트 TXT 해결은 미완료다. 새 설치 ZIP이나 실기 재시험 요청은 없다. 기존071 쌍에076 MCU를 섞어 설치하지 않는다.

## 허용 조건과 오류 처리

- 전체 길이65536바이트, 전체 CRC32 c014b571, header0xffb0/map31/carttype55/ROM지수6/SRAM지수3/확장RAM지수0/resetff02/opcode78을 확인한다. 256바이트씩 읽으며 seek/read 결과와 정확한 길이, 공유 오류, IO 예산을 검사한다.
- 성공 시 모든 props를 초기화한 뒤 mapper0, ROM65536, SRAM8192, FEAT_SRTC와 base FPGA 경로만 구성한다. 다른 copro/추가 FPGA/일반 게임 승인을 넓히지 않았다. 이 CRC는 알려진 파일의 동일성·우발적 손상 확인용이며 보안 인증이 아니다.
- 실제 복사도 주소0/오프셋0/65536바이트로 제한한다. PSRAM 전체 readback에 더해 소스 CRC를 다시 확인하여 분류 후 파일 변경도 거부한다. close 실패를 성공으로 보고하지 않는다.
- native 공유 오류가 발생하면 추가 read/seek/close/SRAM 접근을 차단한다. 분류 실패 시 읽기 전용 열린 파일을 유지한 채 기존 RESET-held 차단 경로로 반환하며 재시도하지 않는다. 기존 유한 대기·RESET/USB·START 금지를 보존한다.
- 다른 버전의 메뉴/헤더가 있는 메뉴/일반 LoROM 메뉴는 이 active 복귀 경로에서 지원하지 않는다. 지원 프로필 확장은 실제 사본과 별도 검증이 있어야 한다. 평상시 메뉴/GBC 경로의 파일 지원을 줄인 변경은 아니다.

## 검증

실제 생성 C의 분류기·복사기·memory.c active 호출 구간을 호스트에서 실행했다. 받은 실제 메뉴의 분류/65536바이트 복사/전체 RAM 대조와 **853검사**를 통과했다. 이 중768개는 분류의256 읽기 위치 각각에서 짧은 읽기·read 오류·공유 오류를 주입한 경우다. seek/크기/close/전체CRC/분류 후 변경/예산/기존 fault/SRAM 대조 및 open/seek/close가 성공을 반환해도 공유 오류가 생기는 경우를 포함한다. FatFS와 SRAM은 모형이며 전체 `load_rom`의 모든 실행 분기를 호스트 실행한 것은 아니다.

분류 CRC 또는 복사 CRC 검사를 각각 제거한2대조는 해당 손상 거부 assertion에서 실패했다. 검사 제거 대조를 정상 성공 횟수에 넣지 않는다.

최종 STM32 전체 링크: firmware180108바이트, SHA `1af4cc50de3a3c71e57d328007c301f3cc5da3fded16e989955414d640296762`, STM3 길이/본문CRC/076 ID 통과. ELF에서 load_rom→새 분류/승인/복사 및 양쪽 CRC/IO 예산 호출을 확인했다. 기존 builder의 manual marker3/shared run1+branch2, READY/CF68/메뉴 준비·해제 호출 검사도 통과했다. builder/OBJDIR의069 명칭은 재사용 도구 이름이며 이 출력은076 compile-only다.

고정069 입력275개 중 변경은 memory.c/nes_menu_return.c/Makefile3개,272개는 동일하다. 새 helper2개와 VERSION 변경은 별도로 기록했다. **SD native/FatFS/SPI/타이머/main/기존 분류기·GBC 소스는 변경하지 않았다.** 같은 RTL이므로 새 Questa/Quartus/ASM은 실행하지 않았다. 기존 전체 SPI 모형/fit는 과거 근거이며 이번 MCU의 새 물리 성공으로 표시하지 않는다.

최초 호스트 컴파일의 Windows SHORT/SIZE 이름 충돌, mini 자기 복사 빌드 준비 실패, 검사기에서 Makefile 변경을 누락한 첫 실패를 보존했다. 별도 초기 후보와 최종 후보를 구분한다. ARM 원시 로그에는 clean-tree dependency 생성 후 재시도가 포함된다.

## 재현과 다음 단계

고정069 비공개 소스/manifest, 사용자 메뉴 사본과 지정 컴파일러가 필요하다. 공개 clone만으로 사용자 입력을 만들 수는 없다.

```text
python tools/nes_menu076_prepare.py --mcu-root <069-source-root> --mcu-evidence <frozen069> --out <new076-source>
python tools/test_nes_menu076.py --src <076-source/src> --menu <received-m3nu.bin> --gcc <gcc.exe> --out <new-test-output>
```

같은 도구에 `--mutation class-crc` 또는 `--mutation copy-crc`를 각각 새 출력으로 지정한다. ARM은 `tools/build_nes_cf68_mcu_arm.ps1`에076 source와 별도 경로의 해시 확인된 mini를 지정한다. 실제 작업의 host-03/mutation 디렉터리와 arm-02.log가 있는 evidence 작업 폴더에 `tools/check_nes_menu076.py --source-root ... --tests ... --objdump ...`를 실행했다. 동결 검증은 `tools/verify_nes_menu076.py --evidence ...`로 한다.

다음은 SD DATA CRC 상태 샘플·busy/할당·보고서 예산 인과 대조다. SDINFO073/074는 메뉴를 호출하지 않으므로 이 수정으로 TXT 실패가 해결됐다고 주장하지 않는다. 실제 TXT와 메뉴 복귀를 관측할 수 있는 경로가 준비된 후에만 새 실기 패키지를 만든다. 원본044 복원/메뉴·GBC 재진입/베이스 FPGA 실제 호환성과 외부 IO gate가 남아 있으며071 설치 보류, 준비도5완료6부분1미완료를 유지한다.
