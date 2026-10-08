# NES098: 실제 메뉴 호출 주소 수정과 복귀 분기 검증

실제 main이 전달하는 메뉴 주소0xC00000을 기존 진단 보호가 거부하던 오류를 재현·수정했다. 전체 load_rom과 main 복귀 분기를 연결한26경우·4대조 및 같은 수정의 ARM 빌드가 통과했다.

PR47의 master 병합 `1f57b10dd977e9ab26fe37dc0c48234214220002`에서 시작했다. 이번 범위인 주소 오류 수정·실제 호출 분기 연결·ARM 반영은 완료했다. 하위 주변장치/실기 준비 전체는 미완료다.

## 원인과 수정

`main.c`는 `load_rom(MENU_FILENAME, SRAM_MENU_ADDR, 0)`으로 메뉴를 요청한다. 실제 `memory.h`의 주소는 `0xC00000`이지만076에서 추가한 `load_rom` 진입 검사와 `nes_return_copy_menu`는0만 허용했다. baseline04에서 전체 함수와 실제 main 분기를 실행하자 오류16·복사0바이트·RESET 해제0회를 재현했다. 두 검사를 기존 메뉴 주소 상수와 일치시키고, 다른 주소/파일/플래그/오프셋은 계속 거부한다. 일반 GBC 코드와094 CF86 전송 코드9개는 그대로다.

097의 시험은 복사 함수에 주소0을 직접 전달하고 전체 load_rom을 생략했다. 그176경우는 기록된 함수 범위의 근거로 유지하며, 실제 메뉴 복귀 성공 증거로 확대하지 않는다. 이번 발견을 과거 사용자074/083 저장 장애의 원인으로 연결할 근거는 없다.

## 실행한 범위와 결과

| 검증 | 결과와 한계 |
| --- | --- |
| 실제 main의 pending 진입·ready부터 released까지 두 구간 | 정상RTC/잘못된RTC, CIC_PAIR/SCIC/FAIL, u16 지연, RESET 전후 SRAM 실패·SD CRC 오류 분기 실행. 부팅 전체와 이후 메뉴 게임 루프는 제외 |
| 전체 load_rom·sram_reliable | 모든 원문 분기를 컴파일하고 진단 pending 경로 실행. 실제256회 scratchpad 확인을 전후 두 번 수행. SGB 비활성·GBC disarm 및 하위 IO는 모델 |
| 실제 cfg/status/fileops | CFG/STM 직렬화, autoboot 파일 없음/있음, actual file_open/close→FatFS→native SD 연결. print_fresult/UART 출력은 모델 |
| 호스트26경우 | 성공7·거부/고장19. FAT16/SDHC80KiB 및 FAT32/SDSC96KiB. 메뉴65536바이트를0xC00000에서 전부 비교하고0주소 영역 불변 확인 |
| 오류 검출 대조4개 | 진입 주소/복사 주소를0으로 되돌리거나 prepared/postrelease 검사 제거 시 시험 실패 |
| 새 ARM | 180952바이트 SHA `31996c7cd9b2db27088cc0f455d3df49cb2c3658b765a5b619c269c2d707acf8`. host와 두 수정 C 전체 일치. 실제 main r1=0xC00000 및 두 cmp 검사를 ELF에서 확인 |

정상80KiB/없음의 SD명령1534,96KiB/autoboot있음1637. 보고native쓰기5회는 모두 RESET 해제 전이며 해제 후에는 쓰지 않는다. RESET 해제 뒤 autoboot 읽기의 CRC 고장은 오류4로 차단되고 main이 RESET을 다시 유지한다. 공유 오류 후 SD명령·에지·CF86프레임·구성 바이트가 추가되지 않는지 확인했다. 논리 SRAM 실패나 CIC_FAIL은 공유 오류 없이도 차단될 수 있다.

SRAM 바이트 저장과 읽기, SPI 응답/핀, RTC/CIC 결과, UART/시간/RESET 동작은 모델이다. actual sram_reliable 원문을 실행했어도 실제 SPI 메모리 거래·실기 전기적 동작을 증명하지 않는다. ARM은 링크/검사이며 MCU에서 실행하지 않았다. 최종 펌웨어 VERSION은 CF86-MENU098, CF86 세션/선택 marker/보고 이름은094를 유지한다. 실제 FPGA는097 ASM 파일을 재사용하며 새RTL/fit/STA/ASM/Questa/설치ZIP은 없다.

## 남은 사항과 보존

098 ARM/097 이미지를 기준으로 실제 RTC의 RSF·INITF 대기와 하위 SRAM/SPI/UART/타이머·CIC/RESET 보호를 연결한다. 완료 후 최종 파일 쌍·정확한044복원본·외부IO/공통고장·관측 가능한 제한실기 절차를 확정한다. 실제 `stm32f4xx/rtc.c`의 `read_rtc()` RSF 대기와 `set_rtc()` INITF 대기는 현재 한도가 없다. 호스트 RTC 모델은 반환하므로 이 문제를 이번 PASS로 덮지 않는다. 실제 하위 함수가 공유 오류 뒤 추가 접근하지 않는지도 다음 검증 범위다. 현재 실기가 이 지점에서 멈췄다는 주장은 아니다.

baseline01 선언 충돌, normal01의 이전097 모델 RESET 조건 실패, 이전 모델·대조 snapshot과 ARM 첫 Make 의존성 실패/정상 재시도를 보존했다. 최종 suite03/baseline04/96-02/negative02/arm01. 동결3487파일, manifest `9ba9764205f04440d5c2259256cb07b43619733eb67f2914d459e360dea93de0`. [계약과 재현](../docs/nes-menu098-contract.md). 준비도4완료/7부분/1미완료·설치false,084/092실기PASS 및 SMB3(J) mapper4 첫 목표 유지.

게시 점검에서 ARM 빌더 끝의 불필요한 빈 줄만 제거했다. 실행된 빌더와 동결 archive는 그대로 보존하고, 검증기는 끝 개행만 다른지 대조한다. 펌웨어/시험 소스·바이너리는 바뀌지 않았다.
