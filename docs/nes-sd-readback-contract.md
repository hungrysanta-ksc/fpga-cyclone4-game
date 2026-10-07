# NES060 — SD 원본과 PSRAM 읽기 비교 연결

SPDX-License-Identifier: MIT.

`nes_sd_readback_probe()`는 검증된044+056 C 소스 뒤에 붙는 독립 진입점이다. 기존056 함수를 바꾸지 않고059의59 프로토콜로 적재·읽기 비교·STOP·기본 FPGA 복구를 연결한다. 아직 메뉴 호출과 실기용 FPGA 이미지가 없다.

## 승인과 복구 순서

1. USB IRQ를 보호하고 콘솔 RESET을 유지한다.056과 같은 자체 MMC3 진단 두 종만 허용한다. 최초 SD 읽기의 정확한 iNES1 헤더·전체 크기·CRC를 검사한다.
2. 승인된 이미지로 설정하고044 식별자와59 프로토콜을 확인한다. 두 번째 SD 읽기에서256바이트씩 DATA를 전송한다. 헤더·전체 CRC·크기와 close까지 성공한 뒤 END를 보낸다. 응답이 불확실한 DATA를 재전송하지 않는다.
3. 파일을 다시 열어 헤더·크기를 확인하고,256바이트 버퍼를 사용하는 source callback을059 비교기에 넘긴다. READ/query/실제 바이트 비교/ACK는059 코드 그대로다. 세 번째 읽기의 마지막 callback은 전체 CRC·최종 크기·close를 검사한 뒤에만 바이트를 반환한다. 따라서 FINISH 전에 입력 검증과 close가 끝나야 한다.
4. 검증이 끝나도 START를 보내지 않는다. STOP 뒤 GPIO 상태를 복원하고 기본 FPGA 설정과 token을 검사한다. 복구 실패 시 RESET/USB 보호를 풀지 않는다.

`true` 반환은 메뉴를 다시 읽을 수 있다는 뜻이다. ROM 검사 성공은 `report.verified`와 `report.load.result`로 따로 판단한다. 검증은 성공했지만 STOP이 확인되지 않은 경우도 있을 수 있으므로 `stop_ok`, `base_restored`, `recovery_attempted`를 각각 남긴다. 이때 기본 재설정까지 성공해야 안전 복귀다. 소스 오류는 load 결과에, tag/data/timeout 오류는 verify 결과에 기록된다.

CRC는 두 자체 진단의 우발적 변경 식별이며 인증이 아니다. 플랫폼 `fpga_pgm`의 기존 panic 동작에 새 timeout을 추가한 것은 아니다. 동기 메뉴 소유권 안에서만 호출할 수 있으며 ISR·재진입 API가 아니다. 내부 API는 콘솔 RESET을 직접 해제하지 않는다.

## 실행 근거와 재현

```powershell
python -B tools/nes_sd_readback.py --gcc $HOST_GCC --out $FRESH_HOST
python -B tools/nes_sd_readback.py --gcc $HOST_GCC --out $FRESH_CRC --mutation crc
python -B tools/nes_sd_readback.py --gcc $HOST_GCC --out $FRESH_CLOSE --mutation close
./tools/run_nes_sd_readback_wave.ps1 -Python $PYTHON -FloatWrapper $FLOAT_WRAPPER -QuestaBin $QUESTA -Out $FRESH_WAVE -HostRun $FRESH_HOST
python -B tools/prepare_nes_sd_readback_arm.py --baseline $PRIVATE_059_ARM --out $FRESH_ARM
```

host는 실제 생성된 C와 FatFS/GPIO/FPGA 설정 모형을 사용한다.80/96KiB 전체 경로와 기존 실패·세 번째 SD 읽기 오류·메모리 손상·주소 오류·timeout·응답 유실·복구 실패를 검사한다. CRC/close 검사를 제거한 mutation의 예상 실패를 정상 통과와 구분한다.

두 C GPIO 파형을044+059 디지털 RTL에 재생한다. load 파형은 실제256바이트 SPI 적재 뒤 두 번째 SD 읽기 실패→STOP이다. check 파형은 전체 C host 실행 중 세 번째 파일 열기에서 기록을 시작해256바이트 읽기 비교/ACK 뒤 SD 읽기 실패→STOP을 포함한다. CHECK용96KiB는 testbench가 loader 입력을 구동해 실제 핀에 써서 준비하며, 전체96KiB C 적재 파형을 RTL에 재생한 것은 아니다. 두 모드 모두044 식별자 공존·PLL loss·RUN 없음도 검사한다.

ARM 전체 링크는 private059 준비 트리와 기존 도구·검증한 mini 이미지를 사용한다. `build_nes_sd_readback_arm.ps1`이1068바이트의 새 진입 함수를 유지하지만 메뉴에서는 호출하지 않는다. 함수 크기는 하위 helper 전체 크기와 다르며 결과는 설치용이 아니다.

이번 변경은 MCU 연결이다. SPI/메모리5개 생성 RTL은059 fit와 해시가 같으며959LAB fit와 마지막8프레임 근거는059를 재사용한다. 새 공동 fit/코어 회귀·물리 보드/STA를 수행했다고 부르지 않는다. 다음은 자체 load/verify/STOP 진단의 실제 핀·클록·타이밍·복구 및 진행/결과 표시를 검증한 MCU/FPGA 쌍이다.044와 GBC는 유지한다.
