# NES 056 — STM32 SD 적재와 실패 복구 연결

2026-10-06 후보 **NES-MCU-LOADER-056**. 기존054 C 전송기를 materialized044의 실제 GPIO/SPI 소유권 안에 연결했다. SD 파일 검증·적재·STOP·기본 FPGA 복구를 수행하는 내부 진입점이며, 메뉴 호출과 START는 아직 없다.

| 근거 | 결과 |
| --- | --- |
| 호스트 lifecycle | 정상4경우(80/96KiB × USB IRQ 원래 enable/disable) + 오류22경우 통과 |
| 입력 거부 | 헤더16바이트 각각 변조, 파일 크기 ±1의18경우. FPGA 변경 없이 거부 |
| STM32 GPIO→RTL | 실제 생성 C 파형33184샘플 중 응답29024비트 일치,256바이트 핀 쓰기 후 SD 오류→STOP, RUN 없음 |
| 기존 경계 | A5/44 식별6회, PLL 상실 차단 검사 통과 |
| ARM | 실제 STM32F401 헤더로 컴파일 및 전체 firmware 링크 통과. 미호출 `nes_mcu_load_probe` 심볼920바이트 유지 확인 |
| 보호 기준 | GBC152파일·기존 NES334파일 해시 동일. 제품 RTL 변경 없음, 새 fit/STA 없음 |

호스트 시험은 파일 open·header·content·short read·read error·seek·configure·DONE·SPI busy·ID·protocol·응답 유실·두 번째 패스의 변경·close와 기본 FPGA 복구 실패를 주입했다. DATA 응답 유실 때 재전송하지 않고 실제 STATUS count로 STOP한다. sticky protocol 오류에서는 STOP 성공을 주장하지 않고 기본 FPGA를 재설정한다. 기본 FPGA 설정/SPI busy/TXE/token 중 하나라도 실패하면 RESET을 유지하고 USB IRQ를 복원하지 않는다. 전체 적재 성공 시에도 END 뒤 STOP·기본 FPGA 복구를 수행하며, 적재한 코어를 실행하지 않는다.

파일은 읽기 전용 로컬 FIL로 처리한다. 정확한 두 진단 파일을 전체 CRC32로 확인하고, 적재 중 다시 읽은 헤더·CRC 및 close 성공을 END 전에 확인한다. CRC32를 보안 서명·PSRAM readback으로 취급하지 않는다. 진단 형상 선택은 SPI BEGIN까지 연결했으며 실제 코어 CHR mask와 묶는 보드 설정은 남았다.

첫 파형 재생에서는 적재·응답·STOP 검사가 끝난 뒤 보조 legacy query가 실패했다. 시험은 SCK가 LOW라고 가정했지만 실제 `slow_end`는 저장했던 HIGH 출력 latch를 정상 복원했다. 새 독립 mode0 query가 자신의 LOW idle을 설정하도록 시험만 수정했다. 실패한 실행 소스/로그와 수정 후 PASS를 따로 보존했다. 펌웨어 파형은 바꾸지 않았다.

Make3.81의 깨끗한 트리 첫 dependency 생성에서 `cdcuser.o` 규칙을 찾지 못한 중단도 보존했다. 기존 재실행 절차로 전체 링크가 완료되었고, ELF에 새 함수를 강제로 유지해 코드가 제거된 빌드를 통과로 세지 않았다. 결과 바이너리는 **compile-only**이며 배포하거나 SD에 복사하지 않는다.

호스트 FatFS·NVIC·레지스터·FPGA 설정 함수는 모형이다. RTL 재생은250kHz/+2µs 시각의256바이트 실패 경로이며 실제 STM32/SD 전기 동작이 아니다. 전체 ROM→실제 코어8프레임은055의 별도 근거로 유지하고 이번에 재실행하지 않았다. FPGA 회로를 바꾸지 않아 기존054의948LAB/15LAB 여유를 참고하며 새 보드 fit 통과로 표시하지 않는다.

다음은 승인된 형상을 코어 mask와 함께 고정하고 물리 무결성·실제 클록/소비자를 공동 예산 안에 연결하는 일이다. 이후 메뉴의 진행·결과 표시, 보드 fit/STA와 복구 가능한 실기 후보를 준비한다. **실기 기준044, GBC, SD 설치 상태는 그대로다.**

[계약과 재현](../docs/nes-mcu-loader-contract.md) · [소스/실행 해시](mcu-loader-verification.json) · [다음 작업](../cores/nes/HANDOFF.ko.md).
