# NES 056 STM32 적재 전용 진단 계약

SPDX-License-Identifier: MIT.

`nes_mcu_load_probe(path, image, report)`는 materialized044의 `slow_begin/slow_end`와 GPIO 소유권을 공유한다. `tools/nes_mcu_loader.py`가044 C 전체 뒤에 새 `.inc`를 붙인다. 기존044 진입점·세션·원본 파일은 수정하지 않는다. 호출은 동기 메뉴 소유권 안에서만 가능하며 ISR·재진입 API가 아니다. 메뉴 호출은 아직 추가하지 않았다.

입력은 로컬 `FIL`, `FA_READ`로만 연다. 두 자체 MMC3 진단의 정확한 iNES1 헤더, PRG64KiB, CHR16/32KiB, 전체 크기와 CRC32를 적재 전에 확인한다. trainer·battery·NES2·추가 플래그/데이터·다른 내용은 거부한다. CRC32는 우발적 변경 식별이며 보안 서명이나 물리 PSRAM 무결성 검사가 아니다.

| 진단 | 전체 파일 SHA256 | 전체 파일 CRC32 |
| --- | --- | --- |
| fine_x | `3daf26c8e2d0002c288efdf2ff694cdc14f0266b9cb32bb3efda8b9bf5d173df` | `5a226793` |
| banks32 | `22427da4f719a0bce2b4d8417b35a45a347e76dbcab2cbc22427ace29aa1279b` | `7a5a55c1` |

1. 기존 USB IRQ enable 상태를 저장하고 해당 IRQ만 차단한 뒤 SNES RESET을 유지한다. 다른 IRQ/전역 설정은 변경하지 않는다.
2. SD 첫 패스를 검증하고 rewind한다. 거부 시 FPGA를 재설정하지 않고 파일을 닫는다.
3. 호출자가 명시한 승인된 이미지로 설정하고 GPIO를 인수한다. A5/44 식별과054 로더의 비실행 초기 상태를 요구한다. stock044 이미지는054 ROM 프로토콜을 제공하지 않는다.
4. BEGIN 뒤256바이트씩 읽어 각 DATA를 한 번만 보내고 별도 STATUS로 확인한다. 응답 유실 시 DATA를 재전송하지 않는다. 같은 파일의 두 번째 헤더·CRC와 close까지 확인한 뒤에만 END를 보낸다.
5. **START를 보내지 않는다.** STOP 후 GPIO 레지스터를 원상 복구하고 기본 FPGA를 다시 설정·검사한다. 적재 진단 결과는 남지만 ROM 적재 상태는 폐기한다. 미래 RUN API가 아니다.
6. 기본 FPGA의 설정·SPI 상태·test token 확인에 실패하면 `false`를 반환하고 RESET/USB 보호를 유지한다. 성공한 경우에만 원래 USB IRQ enable 상태를 복원한다. 반환 `true`는 메뉴 재로딩이 안전하다는 뜻이다. 적재 성공은 `report.result`, `end_accepted`로 따로 확인한다. 호출자는 복구 실패 시 일반 메뉴로 진행하면 안 된다.

실제 FatFS·SD 장치·FPGA 설정은 플랫폼 함수에 의존한다. 기존 `fpga_pgm`은 하드웨어 오류에서 panic할 수 있으며056이 별도 복구 timeout을 추가한 것은 아니다. 파일 내용을 2회 읽지만 FAT 메타데이터의 동시 외부 변경이나 고의 CRC 충돌을 방어하는 파일 인증 기능은 아니다. GPIO 모드/출력/SPI CR1은044 방식 그대로 보존한다.

250kHz 전송의 바이트당 DATA+STATUS는 최소556µs다. 80KiB 약45.5초,96KiB 약54.7초에 SD/소프트웨어 시간이 추가된다. 진행 UI는 실제 메뉴 연결 때 구현해야 한다.

## 재현

호스트 시험과 GPIO 파형 재생은 공개 소스·자체 생성 진단만 사용한다. ASCII 새 출력 폴더를 사용한다.

```powershell
& $PY -B -X utf8 tools/nes_mcu_loader.py --out $HOST_OUT --gcc $GCC
& tools/run_nes_mcu_loader_wave.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Out $WAVE_OUT -HostRun $HOST_OUT
& $PY -B -X utf8 tools/nes_mcu_loader.py --out $ARM_OUT --upstream $PINNED_SD2SNES
& tools/build_nes_mcu_loader.ps1 -SourceRoot $ARM_OUT -ArmBin $ARM_BIN -HostGcc $GCC -Make $MAKE -UnixBin $UNIX_BIN -MiniImage $VERIFIED_MINI
```

Questa는 기존 승인된 Starter FLOAT wrapper를 RunOnly로 사용한다. ARM은13.3.Rel1, 기존 pinned sd2snes export와 보호된 GBC overlay를 사용한다. mini 이미지가 없으면 `-MiniImage` 대신 `-QuartusBin`으로 생성할 수 있다. 정확한 해시는 빌드 스크립트가 검사한다. Make3.81의 첫 dependency 생성 중단은 원시 로그에 보존하고 기존 절차처럼 한 번 재실행한다.

ARM 전체 링크는 `--undefined=nes_mcu_load_probe`로 미호출 함수를 유지하고 ELF 심볼까지 확인한다. 실행 진입점이 없는 compile-only 바이너리이며 SD 설치 대상으로 제공하지 않는다. 별도 저장한 원시 자료는 `verify_nes_mcu_loader.py --evidence <private056>`로 감사한다. 이 감사 명령은 새 시험을 실행하는 명령이 아니다.

호스트 모델은 전체80/96KiB와26 lifecycle 경우·18 헤더/크기 거부를 검사한다. 모델은 FatFS/레지스터/NVIC/설정 함수를 대체한다. RTL은 실제 생성된 C GPIO 쓰기와 +2µs 샘플 시각을 재생한다. 시간 비용을 제한하기 위해256바이트 뒤 SD 오류→STOP 경로를 사용한다. 전체 ROM→코어 근거는 별도의055 시험이며056에서 다시 실행한 것으로 계산하지 않는다.

현재 미완료: 하나의 승인된 설정에서 CHR 형상을 SPI BEGIN과 코어 mask에 연결, 물리 readback, 실제 클록/소비자/프레임 마감, 공동 보드 fit/STA, 메뉴 진행·결과 표시와 새 실기 쌍. 실기 기준044를 유지한다.
