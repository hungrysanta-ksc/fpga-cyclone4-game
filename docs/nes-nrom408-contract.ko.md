# NES408: 실제 227 loader 전체 함수와 FatFS 결합

PR133 후속이다. 407의 고정 NROM16/수평 후보를 대상으로 **실제 생성된 227 loader 함수 전체**와 227의 바이트가 같은 FatFS 코드를 합성 FAT16 디스크에 연결했다. SPI·PSRAM·RUN/표시·base 하드웨어는 C 모델이다. FPGA RTL 시험은 별도로 수행했으며, 두 시험은 아직 하나의 동시 실행이 아니다. 실제 보드 시험·새 FIT/STA·60fps·MMC4/5 시간/면적은 미완료다.

## 전체 loader + 실제 FatFS 시험

`fatfs02`는 생성 407 `nes_menu_sd_probe` 함수와 `sd_query`, `sd_command`, `sd_source`, `load_crc`, `load_read`, 실제 `nes_rom_verify`·SPI framing 및 원본과 해시가 같은 227 `ff.c`/`ff.h`를 실행한다. 실제 FatFS가 합성 FAT16의 NROM 파일을 열고 읽고 재탐색/close한다. 디스크 블록, FPGA SPI와 PSRAM·보드 ID·base programming은 C 모델이며 표시 RUN과 STOP helper도 모델이다. `nes_diag_active`는 false인 모델이므로 실제 SD 핀 및 진단 IO guard까지 통합한 시험은 아니다.

정상 case에서 세 pass CRC, 384KiB data와 zero padding, 독립 readback/FINISH, checked START, 모델 STOP, base 구성/토큰·IRQ 복구까지 이어졌다. 9 case는 정상, 수직 header 거절, 옛 `74` ID 거절, 두 번째/세 번째 pass의 파일 변경, SPI DATA 실패, readback 손상, STOP 실패, base 구성 실패다. 오류 후 새 START/IRQ 해제 또는 verified 승인이 잘못 일어나지 않는 것을 검사한다. 잘못된 header는 FPGA 설정 전에 종료한다. fault 후 base 재설정이 실행됐다고 모두 주장하지 않는다. **이것은 합성 peer에서의 control 검증이지 실제 카드·FPGA·보드 복구 결과가 아니다.**

`full04`는 같은 전체 loader를 단순 파일 모델로도 반복했다. `fatfs01`의 문자 변환 소스 경로 누락, `full01` compile 경고, `full02` test stub 링크 오류는 보존했다. 선택 시험 `fatfs02`와 `full04`의 전체 loader와 testcase hash가 일치한다.

## 실제 FPGA 경계의 별도 시험

`rtl03`은 407의 실제 FPGA SPI 제어와 227의 `nes_rom_boot`, `nes_rom_loader`, `nes_rom_physical` RTL을 PSRAM 응답 모델에 연결하고 2.625MHz 직렬 교환을 실행했다. 222 frames/14,208 wire bits, 100 read 요청 중 7개 ACK, 19개 주소 손상, STOP·fault·reset 취소 72개 및 동시 충돌 2개를 검사했다. 검증 전 START 거절, 검증된 RUN 진입 뒤 STOP도 통과했으며 오류·경고 0이다.

이 시험은 긴 초기 전송을 생략하려고 **loader READY/길이와 verified를 testbench에서 설정**했다. 즉 전체 384KiB FPGA 쓰기·readback을 통해 verified가 만들어지는 과정이나 ARM 코드와 RTL의 동시 실행이 아니다. `rtl01`의 미연결 출력 14개 경고는 `rtl02/03`에서 명시 연결했으며 실패·중간 로그를 보존한다.

## 실제 Cortex-M4 전체 링크와 전체 보드 합성

227 소스 사본의 변경된 loader·verify·layout을 ARM 전체 firmware로 링크했다. 링크된 `nes_menu_sd_probe`에서 `nes_nrom406_header`, `nes_nrom406_layout`, `nes_rom_verify`, `sd_source`에서 layout 호출을 disassembly로 확인했다. 기존 ELF text **199,785B → 200,061B (+276B)**, data 10,040B·BSS 18,076B는 동일하다. `.stm` **209,828 → 210,104B (+276B)**다. 기존 object 재사용이 있는 증분 링크이며 전체 stack/IRQ worst-case, 물리 cycles 또는 실행 증명은 아니다. 기존 227의 menu/image 이름은 아직 NROM 전용으로 연결되지 않았으므로 결과를 사용자 SD에 설치하지 않는다.

후보와 기준의 같은 90개 227 board 입력 중 cart·SPI ID만 바꾼 Lite 전체 MAP은 각각 **18,178LE/13,557C/8,029FF/185,824bits**와 **18,850LE/13,951C/8,353FF/256,608bits**다. 65,536bit의 PRG-RAM 제거와 5,248bit compact 변화가 포함된다. 이는 고정 NROM·PRG-RAM 미지원의 구조 결과로 실제 전체 기능 동등성이나 FIT/STA가 아니다. loader C는 FPGA MAP에 포함되지 않는다. ARM·SPI·IRQ·ROM 경쟁을 연결한 새로운 실제 처리 시간은 없다.

## 60fps와 MMC4/5 비교의 경계

402 공동 실행 후보 A는 기존 실제 연결 모델에서 12 ACK와 917 capture **시작**을 기록했으나 914·915 VBlank를 놓쳤고 전체 MAP 20,199LE/16,508C였다. ARM DMA job 후보 B의 같은 경계 새 전체 구현·시간·면적은 없다. 408의 227 고정 NROM MAP을 402 전체에서 빼거나 A/B의 절감으로 더하지 않는다. 384KiB padding DATA+STATUS의 약 19.174초 wire 하한은 부팅 적재의 계산이고 게임 1프레임 비용이 아니다.

MMC4(mapper10)의 실제 fetch/latch와 MMC5(mapper5)의 고위 tag·ExRAM/split/IRQ/audio를 위 CPU/PPU·ROM arbiter 일정에 결합하지 않았다. 376의 tag8192 거절 및 특정 split overflow는 실제 mapper 경쟁 시간이 아니다. 두 mapper의 추가 ARM/SPI/IRQ·ROM 지연과 whole area는 **null**이다. 같은 캡처·ROM 위상과 실제 core request, 2-slot, VBlank·독립 검사·STOP·최종 ACK를 포함해 계측해야 한다.

## 다음 작업

1. 실제 227 FatFS/loader C와 실제 FPGA SPI·loader·PSRAM 모델을 **같은 실행**에 결합한다. 긴 초기 384KiB 경로에 대해 속도를 가정해 cycle을 생략하지 말고, 기능 가속 시험과 실제 clock/전송시간 모델을 구별한다. 3-pass CRC/readback, START, RUN 중 STOP, late DONE, fail-closed와 base/menu 복구를 확인한다.
2. 고정 NROM profile과 image ID를 실제 menu 선택·NES core·SNES 출력에 연결하고 새 matched FPGA/ARM/65816 version과 source hashes를 고정한다. 전체 firmware 링크를 제품 package로 취급하지 않는다. 16/32·mirroring의 범위 확장은 해당 profile별 identity와 loader 검사를 연결한 다음에만 승인한다.
3. 실제 ARM/IRQ/SPI/ROM 경쟁과 다음 캡처·VBlank, mapper workload 및 전체 Lite FIT/STA·CDC/IO를 같은 구현에서 측정한다. 기존 production227/GBC164/saveSRAM을 보존하고 자동 배포·구매·머지하지 않는다.

재현 근거는 [검증 JSON](../analysis/nrom408-verification.json), [전체 loader 모델 시험](../tools/test_nes_nrom408_fatfs.py), [실제 FPGA 경계 시험](../tools/test_nes_nrom408_rtl.py)과 로컬 `probes/nes-nrom408`에 있다.
