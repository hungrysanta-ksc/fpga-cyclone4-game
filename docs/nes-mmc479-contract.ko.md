# NES479: MMC3 전용 로더·부팅·실제 source 입력

**게임 진입의 첫 관문을 구현·검증했다.** 전용 ID79, 엄격 SMB3 로더, 실제 MMC3/source 부팅과 현재 ARM 입력·계획까지 확인했다. 새 게임 설치본·SNES 게임 화면·실기 FPS 승인은 아직 없다. 기존 NROM476/477 실기 평균23.84fps는 그대로다. [해시·수치](../analysis/mmc479-verification.json).

## 교체 경계

- ARM476의 수신·계획·출력·독립 검사 코드는 유지했다. 원래227의 엄격 SMB3(J) 로더를 복원하고 NROM layout 함수를 실행 대상에서 제거했다. source/query·공통 실행기를 근거 없이 다시 설계하지 않았다.
- 전용 보드 ID는 **79**다. 로더 상태·readback·START 검사, run136 식별, FPGA 응답 두 곳과 보고 ID를 일치시켰다. NROM78·이전 MMC3/74 응답은 거부한다. 현재 진단을 NROM 실기 파일 위에 덮어 쓰지 않는다.
- ROM은 mapper4, PRG256KiB/CHR128KiB, 정확한16B header·전체393232B, CRC32 `5a04eed7`로 제한한다. PRG는 payload0..0x3ffff, CHR는 payload0x40000..0x5ffff에 직접 배치한다. CRC는 우연한 변경 검출이지 인증이 아니다.
- 원본 `.nes`가 현재 작업 공간에 없어 기존 private147의 PRG/CHR hex와 원래 header로 복구했다. 전체 기존 SHA256 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`와 CRC가 일치한다. ROM 코드·데이터를 변경하지 않았고 Git/전달본에 넣지 않았다.
- 파일명은 `NES MMC3 479.nh1`, `mmc479.nes`, `fpga_mmc479.bi3`, `nes-progress-mmc479.txt`, `nes-game-last-mmc479.txt`, `nes-budget-mmc479.txt`로 분리했다. 실제 설치 파일은 아직 만들지 않았다.

## 확인한 단계

| 단계 | 결과 | 정확한 범위 |
|---|---|---|
| 실제 C 로더·FatFS·programmer·verify·run136 | 정상+19오류,20건 PASS | synthetic FAT16·FPGA config, GPIO/SPI/PSRAM·native/observer 모델 |
| 전체 적재·검사 | 384KiB 전달·readback·3회 파일 CRC 후 START/STOP/base PASS | 실제 FPGA와 한 실행의 전체 적재는 아님 |
| 실제 전체 ARM 빌드 | text202313/data10040/BSS18552B | firmware212356B,476 대비−284B, Flash 산술 후미636B |
| 변경 없는 object | 73개의 SHF_ALLOC 영역 동일 | loader/menu/checkpoint/verify4개만 변경, debug 영역 제외 |
| 실제 MMC3/core/source RTL | ID79·START·유효 source15packet·CRC·retire·END/COMMIT·STOP PASS | ROM·loaded/verified 상태는 seed, D3는 수신 허가 모델; PSRAM70ns |
| 실제 source → linked476/479 M4 | 3206payloadB·15packet·generation12, 전체 상태/40B plan 동일 | SPI peer·plan 완료는 모델; 동시 IRQ·실제 tile 공급/DMA 아님 |

M4는 이 캡처에서 수신288231명령·계획330833명령,40B tile plan18개를 생산했다. counts는 map990/row224/OBJ2/exception2/raster224/palette32다. 이는 부팅 초기 한 캡처이며478의 플레이 구간71개보다 가볍다. 명령 수를 실제 ARM cycles/FPS로 환산하지 않는다. isolated unit RAM128KiB를 사용했으므로 물리64KiB stack 승인도 아니다.

부팅 초반 강제 blank 프레임에서는 patch 용량 거부와 export error2가 관측됐다. 검사를 해제하지 않고 다음 유효 캡처를 기다렸다. generation12에서 valid·export error0으로 정상 출력했고13번째 관측 프레임까지 진행했다. 이 부팅 거부를 표시 성공·연속 capture 무손실로 세지 않는다. 첫 유효 입력까지의 ARM deadline/IRQ·표시 일정은 다음 연결에서 확인한다.

20건에는 잘못된 header/CRC/길이·mirroring·trainer·CHR·NES2/reserved·기대 profile, 보드78/74, 두 번째/세 번째 파일 변경, SPI 쓰기 실패·readback 손상·stale tag, STOP/base 실패가 포함된다. 적재·검증 중 오류에서는 START하지 않으며 STOP/base 실패 시 안전한 메뉴 복귀로 오인하지 않는다. native 처리와 GPIO 완료 모델을 실제 보드 성공으로 승격하지 않는다.

## 같은 소스의 Quartus Lite 비용

| 비용 | 진단478,ID78 | 전용479,ID79 |
|---|---:|---:|
| MAP LE/comb/FF | 18923/14016/8383 | 18928/14017/8387 |
| FIT LE/comb/FF | 15266/14069/8387 | **15260/14069/8387** |
| RAM bits | 256608 | 256608 |
| 장치15408LE 대비 잔여 | 142 | **148** |
| implementation 관련 setup/hold | +0.187/+0.146ns | **+0.235/+0.154ns** |
| nominal 관련 setup/hold | +0.187/+0.146ns | +0.404/+0.154ns |

동일 Lite25.1·device·seed1·원래 제약, ID 응답 상수만 두 곳 바꿨다. −6LE는 그 배치 결과이며 구조적 제어 삭제 성과로 주장하지 않는다. raw setup−6.482ns/recovery−8.794ns와 전체 reset/CDC/IO 승인은 여전히 미완료다. 관련 경로 양수만으로 전체 signoff/실기 승인을 하지 않는다.

## 보존과 다음 순서

ARM01의 sandbox subst 거부, ARM02의 생성 header 전 implicit-rule 검색 실패, loader01의 sandbox MinGW DLL 오류를 보존했다. 새 ARM03은 header bootstrap 뒤 전체 build, loader02는 같은 시험을 정상 호스트에서 실행했다. 회로·라이선스 실패나 장치 용량 초과로 기록하지 않는다. Questa는 기존 FLOAT1좌석으로 부팅/source 시험 한 건만 순차 실행했다.

478 문서의 ‘16B plan’은 **40B**로 정정했다. 현재 C struct·DWARF와 저장된 plan hex를 대조했다. 기존71개 plan byte 동일성 판정은 바뀌지 않는다.

1. **현재479 조합의 live ARM/tile plan·query·ROM 공급·staging 연결**: 실제 shared SPI/IRQ·MMC3 bank/IRQ·부팅 blank 거부 후 첫 유효 입력과 deadline을 확인한다. 기록 재생과 seed 적재를 실제 전체 경로로 오인하지 않는다.
2. **paired65816 게임 프레임**: 실제 DMA·독립 CRC/coverage·receipt·최종ACK/EA·VBlank와 STOP/base/menu를 연결한다. 현재 SNES 게임 출력 관문은 미통과다.
3. 같은 source/FIT/제약·marker·원복을 묶은 새 게임 시험본을 만든다. ROM은 사용자 고정본을 사용하며 배포하지 않는다. 이전476 전달본은 그대로 보존한다.
4. 사용자 실기로 게임 장면·입력·메뉴 복귀와 실제 표시 cadence를 측정한 뒤 병목을 정한다. 문양24fps나 부팅 한 캡처로 SMB3/60fps·MMC4/5를 예측하지 않는다.

도구: `prepare_nes_mmc479.py`, `build_nes_mmc479_arm.ps1`, `test_nes_mmc479_loader.py`, `test_nes_mmc479_core.py`, `check_nes_mmc479_arm.py`, `analyze_nes_mmc479.py`. private source/원문은 `probes/nes-mmc479`에, 실제 실행은 ARM03/loader02/core01/board01에 보존한다. [재현 범위](../cores/nes/REPRODUCING.ko.md)의 로컬 자료 의존성은 계속 적용된다.
