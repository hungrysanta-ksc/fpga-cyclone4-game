# NES069 CF68 MCU 연결 계약

MCU 후보 **NES-CF68-MCU-069**는 FPGA **NES-DIAG-SAFETY-068 / CF68**용이다. PR23 병합 `4651eada3c26a464b4b27627247e5a30dca2d482`에서 파생했다.065 생성기와 원본 C,068 RTL·fit를 보존한다. 설치 쌍은 아직 없다.

## 실행 경계

`nes_cf68_mcu.py`는065를 생성한 뒤 진단 SD probe만 바꾼다. checked FPGA programming 성공 후 `nes_return_spi_ready()`를 호출하고, 성공해야 GPIO 소유권→CF68→F0A5/F144→protocol59→BEGIN 순서로 진행한다. 기존 READY helper의 25ticks(100Hz에서250ms) 및1000000회 반복 한도를 재사용한다. 이 한도는 물리 MCU 실행 시간을 측정한 값이 아니다. TXE와 실제 MCU_RDY 핀을 확인하며, tick 정지·wrap·늦은 READY 대조를 실행했다. CF61/67/60/44/0 및 다른 정체성/형상은 BEGIN 전에 거부한다.

READY/SPI/TIM2 등 `nes_return_failed()` 또는 native SD 오류가 남으면 cleanup에서 읽기 전용 FIL close와 GPIO 해제를 수행한 뒤 보호 상태로 반환한다. 추가 base 설정/SD 복구와 USB 해제를 하지 않는다. 기존 native SD 보호에 shared-peripheral fault를 추가했다. READY 오류 제거 대조에서는 이 보호가 사라져 지정 assertion이 실패한다. 초기 준비 대기는 WRITE 중 클록 정지의 tCEM 보호를 해결하지 않는다.

성공·검증 실패 후 base 복구 가능·복구 불가를 구분한다. true는 안전한 메뉴 복귀 가능 여부다. START 전송과 boot 실행은 여전히 없다. 메뉴 준비/RESET 해제 후 안정화까지 보호를 유지하며 optional logical log 실패와 native fault를 구분한다. 최근/즐겨찾기0, cfg_save 생략 등의065 제한 복귀 조건도 유지한다.

## 파일 이름

| 역할 | 새 후보 |
| --- | --- |
| marker | `NES VERIFY 069 80.nh1`, `NES VERIFY 069 96.nh1` |
| 진단 FPGA 경로 | `/sd2snes/fpga_nl8.bi3` |
| 로그 | `/sd2snes/nes-verify-last-069.txt` |
| 승인 원본 | `/sd2snes/nes/fine_x.nes`, `/sd2snes/nes/banks32.nes` |

fpga_nl8는 향후 패키지의 경로 계약이며 현재 설치 가능한 파일을 제공한 것이 아니다.065 marker/fpga_nlv/CF61 쌍과 혼합하지 않는다. log에는 MCU069와 expected68/observed board를 구분해 기록한다.

## 검증 범위

- 실제 상위 C41실행/18입력 거부/16메뉴, 추가 구형 ID2·READY fault1·native 보호2. 하위 C95검사(copy20/wait14/log24/SD16/FatFS7/actual-main-finish14). 상위3·하위4 인과 대조가 지정 assertion으로 실패했다.
- 실제069 C GPIO를068 물리 top에 재생했다. load256 pin bytes, TB96KiB 준비 후 CHECK256 bytes,72320응답 비트, CF68 및 START 두 장벽·초기 접근 차단·PLL 상실/복구를 확인했다. GPIO 이외 READY helper 자체는 별도 register-side-effect 모델에서 검사했고 실제 STM32 실행은 아니다.
- 전체 C80/96KiB 전송 캡처는180224bytes/901152frames다.065와 모든 프레임의 시간·TX·RX를 대조하면 첫 CF 응답61→68만 다르다. READY mock은 ns를 전진시키지 않으므로 실제 READY 대기의 지연 측정이 아니며,068 RTL의 전체 SPI 재생도 아직 아니다.
- 전체 ARM 링크에 manual marker3 / shared run1+branch2 / candidate·base checked programming2 / READY와 fault 보호 / CF68 비교 / READY-before-GPIO가 있다. 최종179336bytes SHA는 공개 기계 요약에 고정한다. 두 빌드 차이는 offset4..7의 timestamp 기반 genhdr version magic뿐이며 코드·나머지 바이트는 같다. 헤더를 임의 정규화하지 않는다.
- production SV는068 fit03와 일치한다. 새 map/fit/STA/ASM은 실행하지 않았고068의2400LE/195LAB/44M9K/135핀·내부 최소hold0.140ns를 이 경계에서 재사용한다. 외부 IO·클록 정지·실기 승인은 없다.

## 재현

```powershell
& $Python -B -X utf8 ./tools/nes_cf68_mcu.py --baseline $Pinned062Platform --out $Fresh069Platform
& $Python -B -X utf8 ./tools/nes_cf68_mcu_host.py --out $FreshHost --gcc $HostGcc
# 상위 실패 대조: --mutation candidate / ready / fault-release
& $Python -B -X utf8 ./tools/nes_cf68_mcu_checks.py --platform $Fresh069Platform/src --out $FreshHelpers --gcc $HostGcc
# 하위 실패 대조: --mutation menu-compare / log-release / sd-crc / fatfs-budget
& $Python -B -X utf8 ./tools/nes_cf68_mcu_host.py --out $FreshSession --gcc $HostGcc --session
& ./tools/run_nes_cf68_mcu_wave.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshASCIIWave -HostRun $FreshHost
& ./tools/build_nes_cf68_mcu_arm.ps1 -SourceRoot $Fresh069Platform -ArmBin $ArmBin -HostGcc $HostGcc -Make $Make -UnixBin $UnixBin -MiniImage $PinnedMini
& $Python -B -X utf8 ./tools/verify_nes_cf68_mcu.py --evidence $Frozen069Complete --fpga-evidence $Frozen068Final
```

모든 변수는 절대 경로다. 기존 Starter FLOAT 한 seat로 순차 실행한다. 공개 clone만으로 host 검사와 모형 생성은 가능하지만, prepare/ARM은 pinned private062 플랫폼·mini가 필요하고 frozen verifier는 private 증거를 요구한다. 실행 snapshot과 raw 실패는 로컬에만 보존한다.

최종 `probes/nes-cf68-mcu-069/evidence-complete/`965파일 manifest `b5d50d8a5f7590a43f33b8ebe4d5166ff2f2ae0ba9bbebf953984959d6d026ae`. 초기942/중간945파일 수집은 각각 Makefile·trace 누락으로 감사 실패했으며 수정하지 않고 보존했다. 생성기 문자열/헤더/marker 기대/trace_frames 치환 실패, Make3.81 첫 dependency 실패와 재시도도 남긴다. 세 freeze 스크립트와044–068 동결을 다시 실행/수정하지 않는다.

다음 완료 조건은 최종069 C 전체80/96KiB를068 물리 핀에 재생해 모든byte/tag/응답·마지막 ACK/FINISH/status/STOP을 확인하는 것이다. 이후 같은068 fit의 Standard ASM/압축 C roundtrip과069 ARM 쌍, 실제 SD 원본/base/menu·독립 백업·복원 조건을 확보한다. 외부 실기에는 회복 가능한 패키지→사용자 TXT·화면·GBC 관측 방식으로 전달한다. installable=false를 유지한다.
