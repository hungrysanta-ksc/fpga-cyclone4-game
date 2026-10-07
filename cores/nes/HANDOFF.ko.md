# NES 다음 작업 인계 — 069 이후

현재 MCU **NES-CF68-MCU-069**, FPGA **NES-DIAG-SAFETY-068 / CF68**. PR23 병합 `4651eada3c26a464b4b27627247e5a30dca2d482`에서 `codex/nes-cf68-mcu-069`로 진행했다. [069 결과](../../analysis/CF68-MCU-RESULT.ko.md), [계약·재현](../../docs/nes-cf68-mcu-contract.md), [기계 요약](../../analysis/cf68-mcu-verification.json)을 먼저 읽는다. [068 계약](../../docs/nes-diag-safety-contract.md)과 [067 모델 전환 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md)의 보호·운영 조건은 유지한다. 역사 파일의 당시 현재/다음보다 이 인계가 우선한다.

## 이번 진전

`nes_cf68_mcu.py`가065를 새 폴더에 생성하고 진단 probe만 파생한다. checked candidate programming→bounded `nes_return_spi_ready()`→GPIO 소유권→CF68→F0A5/F144→protocol59→BEGIN 순서다. 실제 helper는 TXE와 MCU_RDY 핀,25ticks/1000000회 한도를 사용한다. READY/SPI/TIM2/shared-peripheral fault가 남으면 읽기 전용 FIL cleanup/GPIO 해제 후 RESET·USB 보호를 유지하고 추가 base/SD 복구를 하지 않는다. true=안전 메뉴 복귀 가능이며 검증 통과와 다르다.

상위41실행/18입력 거부/16메뉴에 이전 CF61/67 추가2 및 READY fault1·native 보호2를 확인했다. 하위95검사와 상위3/하위4 인과 대조가 통과했다. 최종 ARM은179336bytes SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`. 실제3 marker, shared run1+branch2, checked programming2, READY-before-GPIO, CF68 비교와 fault guard가 있다. 두 빌드는 offset4..7의 genhdr timestamp version magic만 다르고 코드·나머지 바이트는 같다. 헤더를 임의 수정하지 않는다.

새069 C의 bounded GPIO→068 물리 top 재생72320응답 비트가 통과했다. load256 pin bytes, TB96KiB 준비 후 CHECK256 bytes, START 두 장벽·초기 차단·PLL loss/복구다. GPIO 밖 READY helper는 별도 register model 검사이며 실제 STM32 실행이 아니다. 전체 C80/96KiB180224bytes/901152frames를 새로 캡처했다.065와 프레임별 비교에서 첫 CF 응답61→68만 달라진다. READY mock이 ns를 전진시키지 않아 실제 대기 시간의 증명은 아니며 전체 보드 SPI 재생도 아직 아니다.

생산 SV는068 fit03 해시와 일치해 2400LE/195LAB/1479regs/44M9K/135핀/PLL1·내부30summary/최소hold0.140ns 근거만 재사용한다. 새 Quartus/ASM은 실행하지 않았다. FPGA startup1600완전간격(8MHz200µs/10MHz160µs), 등록형 reading_active,3168routed PSRAM경로·조건부 PCB예산은068 근거다. 전원이 reset 해제 전에 안정되고 클록<=10MHz라는 가정은 미측정이다. lockedHIGH인 WRITE 클록 정지의 CE>8µs 반례도 남는다.

## 다음 작업과 완료 기준

1. `tools/nes_board_session_replay.py`의 새 파생 실행기로069 `session02` 캡처를068 materializer에 연결한다. CF68, startup-ready 뒤 시작, 세션의 모든 byte/tag/response, 마지막 ACK/FINISH/status/STOP을 두 geometry에서 확인한다. 전체 성공 전 bounded replay나065/063 성공을 새 전체 SPI 승인으로 사용하지 않는다. 별도 reset-held H1 clock 표현과 미사용84MHz park의 이전 가정을 읽고,8MHz SPI/PSRAM은 계속 free-running으로 유지한다. 현재 실행기는061/062 고정이므로 그대로 호출하지 않는다.
2. 최종068 fit의 Standard ASM/CPF와066 수정 encoder 규칙,069 ARM을 같은 manifest로 묶는다. 압축의 모든 byte를 실제 C programmer로 복원하고 marker069 / `fpga_nl8.bi3` / expectedCF68 / 로그069를 대조한다.065/066 CF61 쌍과 섞지 않는다.
3. 실제 SD 원본/base/menu 형상·독립 백업/복원 조건과 외부 전압/PCB·SPI/SNES·클록 고장 정책의 미확인을 정리한다. 타이밍 변경이 필요하면 새 후보/관련 pin·wave·fit를 재검증한다. blanket false-path, 같은 입력의 PLL clock을 독립 차단으로 취급하지 않는다.
4. 준비된 회복 가능한 제한 패키지를 사용자가 외부 실기에서 실행해 SD TXT·화면·메뉴 재진입·GBC 관측을 전달한다. 실제 SD 경로/원본 백업은 아직 없다. PC USB 연결이나 추가 분해를 전제하지 않는다.

## 파일·동결 근거

069 도구는 `nes_cf68_mcu.py`, `nes_cf68_mcu_host.py`, `nes_cf68_mcu_checks.py`, `nes_cf68_mcu_wave.py`, `run_nes_cf68_mcu_wave.ps1`, `build_nes_cf68_mcu_arm.ps1`, `verify_nes_cf68_mcu.py`다. 절대 경로 명령과 private062 baseline 요구는 계약에 있다. 전체 새 캡처와 진단 fixture는 로컬 `probes/nes-cf68-mcu-069/evidence-complete/session/`에 있다. 다음 전체 재생은 이 manifest·C 해시부터 확인한다.

최종965파일 manifest `b5d50d8a5f7590a43f33b8ebe4d5166ff2f2ae0ba9bbebf953984959d6d026ae`. 초기942/중간945파일의 Makefile/trace 수집 누락과 생성기 구문·mock header·marker 기대·trace_frames 치환 오류, Make3.81 첫 dependency 실패·재시도를 보존했다. `freeze_nes069.py`, `freeze_nes069_final.py`, `freeze_nes069_complete.py`를 재실행하거나 세 archive 및044–068 동결을 수정하지 않는다. 최종069 verifier는068 evidence-final을 함께 요구하며 통과했다. FLOAT 한 seat를 순차 사용하고 정상 종료했다. license smoke/상속 uncounted/전역 서비스·환경 변경은 금지다.

## 실물·보호·공정 상태

FXPAK Pro Mk.III Rev.D / STM32F401RCT6 / EP4CE15F17C8N / IS66WVE4M16EBLL-70BLI×2 / IS62WV5128EBLL-45HLI는 실물 확인 완료다. 제품/부품 재질문·사진·분해는 필요 없다.044 LINK SCREEN 순환·GBC 정상 사용자 보고를 보존한다. GBC152/originalNES334 해시를 유지하고 전체NES059959LAB/4여유·마지막8프레임을 진단 fit로 대체하지 않는다.

준비도 **5완료/6부분/1미완료**는 노력·일정 비율이 아니다. H06 외부 승인 미완료, H08/H09 물리 관측·시간, H11 새 파일 쌍, H12 실제 백업/복원이 남는다. installable=false / full_board_SPI=false / hardware=false / clock_halt_safe=false. 이번 ARM 연결 성공으로 설치 승인하지 않는다. 불확실 DATA/ACK 재시도 금지, native/shared fault의 RESET·USB 보호 및 SD 금지를 유지한다. 주요 진전에서 commit/push/한국어 PR(작업 목표→작업 내용→작업 결과)을 만들며 사용자 병합 보고 후 PR 상태를 새로 확인한다.
