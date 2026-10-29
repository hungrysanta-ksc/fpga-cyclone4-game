# NES406: 고정 NROM cart 후보와 파일 배치·readback 부분 검증

PR133 후속 중간 결과다. **사용자가 요청한 실제 loader·보드의 전체 결합과 STOP·복구는 아직 완성되지 않았다.** 새 장치 FIT/STA나 실기, 새 60fps 시간 및 실제 MMC4/5 경쟁 측정도 없다. 이 문서는 부분 결과와 경계를 기록한다. production227·GBC164·saveSRAM은 변경하지 않았다.

## 실제 구현과 단위 검증

* `build_nes_nrom406.py`는 보존된 227의 실제 `cart_top` 포트 선언을 사용해 고정 mapper0 대체 후보를 만든다. PRG16의 `$8000/$C000` mirror, PRG32의 32KiB, 내부 CPU RAM mirror, CHR-ROM 8KiB 물리 `0x200000` 시작, 수평·수직 CIRAM과 `0x3000` mirror, IRQ 없음, speculative CHR hint 물리 주소를 구현한다. 16/32×수평/수직은 **빌드 시 parameter**이며 파일을 읽어 자동으로 선택하지 않는다. CHR-RAM·PRG-RAM·battery·trainer·four-screen은 범위 밖이다. CPU/PPU의 실제 bus 실행과 전체 보드 기능은 아직 미연결이다.
* `cart02`는 227의 같은 63개 포트에 입력을 명시한 실제 후보를 사용해 4 profile, CPU 65,536주소 및 전체 ROM read/write, PPU 16,384주소를 전수 대조했다. Questa에서 errors 0/warnings 0이다. `cart01`은 포트 미연결 경고 176개로 보존하고 최종 증거로 쓰지 않는다. unit oracle과 후보는 동일 인터페이스 경계를 검사하지만 완전한 NES 코어 실행은 아니다.
* `nes_nrom406_header`는 좁은 iNES1 mapper0 PRG16/32·CHR-ROM8·수평/수직과 정확한 파일 크기를 검증한다. `nes_nrom406_layout`은 기존 384KiB 물리 loader의 PRG `[0,0x40000)`·CHR `[0x40000,0x60000)`에서 NROM 파일 데이터 위치와 나머지 zero padding을 제시한다. 네 profile 전 영역 1,572,864 logical bytes 및 헤더/길이 거절을 C로 시험했다. 이 코드는 아직 실제 FatFS/SPI loader에서 호출되지 않으며 CRC 세 번·SD 변경 방지·물리 write/readback·STOP을 구현하지 않는다. Padding 선택은 시험 후보이며 최종 처리 시간이나 승인된 물리 loader가 아니다.
* `verify_test.c`는 실제 227 `nes_rom_verify.c`·SPI framing과 후보 source를 연결하고 **독립적으로 채운 합성 peer 메모리**에서 PRG16/32 전체 384KiB readback을 비교했다. PRG·padding·CHR 및 마지막 바이트의 잘못된 내용과 source 실패를 각각 검출하고 sticky fault에서 START를 막았다. peer는 실제 FPGA/PSRAM/SD가 아니다. 오류 시 `stop_ok=false`는 sticky fault가 차단한 모델 결과이며, 안전한 실제 STOP·base 복구를 입증하지 않는다.

## 같은 227 보드 소스의 Lite 전체 MAP

두 프로젝트의 전체 90 입력 해시는 `cart_nrom.sv` 하나만 다르다. 후보는 PRG16/수평 고정이고 ARM loader·NES/65816 실행·dynamic profile은 연결되지 않았다. `map-base01`과 `map-cart01`은 모두 Quartus Lite 전체 Analysis & Synthesis다.

| 값 | 기존 MMC3 cart | 고정 NROM cart | 차이 |
|---|---:|---:|---:|
| LE | 18,850 | 18,178 | −672 |
| 조합 논리 | 13,951 | 13,557 | −394 |
| FF | 8,353 | 8,029 | −324 |
| 논리 RAM bits | 256,608 | 185,824 | −70,784 |

RAM 차이의 65,536bit는 `nes_local_memory:prg_ram`이 **완전히 제거**된 것이고, 5,248bit는 `native_frame/compact`의 합성 변화다. 이는 해당 고정 입력 범위·미지원 PRG-RAM에서 생긴 변화다. mapper0 일반 지원, 기능 등가성, MMC4/5 공통 절감이나 새 장치 여유로 보지 않는다. 후보도 15,408LE보다 2,770LE 많다. MAP과 과거 227의 FIT 15,249LE는 다른 구현 단계의 수치이므로 빼서 배치 여유를 예측하지 않는다. 두 MAP 모두 같은 8개 RAM 미추론 기록을 내며 FIT/STA·배선/전기 보장은 없다. 해시·원본 로그는 [검증 JSON](../analysis/nrom406-verification.json)과 workspace `probes/nes-nrom406`에 보존한다.

## 전체 시간과 mapper 경쟁

이 부분 후보는 ARM loader·실제 SPI·IRQ·ROM 경쟁, 65816 표시/최종 ACK에 연결되지 않았다. 따라서 **새 전체 처리 시간과 후보 A/B의 동등 경계 비용은 null**이다. 기존 402의 12 ACK/917 capture 시작, 914/915 VBlank 회귀와 404의 시간 0/면적 회귀는 그대로 [405 계약](nes-hardware405-contract.ko.md)의 자료다. 227 고정 cart MAP과 402 whole MAP은 다른 구조이므로 직접 빼지 않는다.

MMC4 mapper10의 실제 latch 전후 fetch, MMC5 mapper5의 고위 tag·ExRAM·split/IRQ/audio를 이번에 구현하거나 ROM 경쟁을 측정하지 않았다. 후보의 고정 NROM CHR8/PRG-RAM 제거를 그 mapper들의 절감으로 사용하지 않는다. 기존 376의 tag8192 거절과 예외 한도 반례는 resolved input 시험이고 mapper 실경쟁은 여전히 미측정이다.

## 다음에 실제로 연결할 경계

1. 실제 227 ARM loader의 file validation/세 번의 CRC pass와 SPI write/readback/FINISH/START에 source adapter를 연결한다. 파일 크기와 mapper profile을 FPGA 선택 및 핀/physical addressing과 원자적으로 묶고, 원본 변경·truncation/CRC·padding 손상·SPI 응답 손실·STOP/fault/RESET 복구를 실제 생산 C와 FPGA loader 모델로 시험한다. 기존 227을 덮어쓰거나 별도 의미의 384KiB 이미지가 실제 NROM 파일이라고 가장하지 않는다.
2. NES 코어/보드에서 실제 PRG16/32·미러링 profile, immutable epoch, CHR hint를 연결하고 임의 profile 불일치가 START 전에 거절되는지 검증한다. SRAM·old display·late DONE·공통 STOP/menu/base 복구를 시험한다. 단위 주소 PASS로 이를 대체하지 않는다.
3. 같은 후보의 ARM·SPI·IRQ·ROM·65816 경로와 60fps A/B 비용, MMC4/5 실제 요구 표본을 계측하고 whole Lite/FIT/STA 및 resident 패키지 조건을 통과한 뒤에만 제한 실기를 검토한다. 실제 실기일이나 60fps 승인 없음.
