# NES163 결과 — 본체 사운드 초기화와 결과 로그

PR104 머지 `23e41b59a227d17b459cabe73d01fdc022ff7d0a`를 확인했다.162 실기에서 첫 레벨·정상 복귀는 통과했지만 무음이었다.163은 빠져 있던 본체 SPC/DSP 초기화를 추가하고 결과를 TXT에 남긴다. **구현·최소 검증·실기판 준비를 완료했으며 실제 음악·효과음은 아직 미확인이다.**

[실기 안내](../docs/nes-game163-instructions.ko.md) · [검증 수치](game163-verification.json) · [162 실기](GAME162-HARDWARE-RESULT.ko.md)

## 변경과 결과 해석

- GBC 기반 `g9_snes_io.py`의89바이트 SPC 코드를 재사용했다. 내부 음성과 echo는 끄고 DSP FLG0x20을 설정한 뒤 읽어 확인한다. 업로드는 NES 클라이언트의 native A8/X·Y16/DBR0/DP0에 맞춘 작은 루프로 구현했다. WRAM DP10을 전용 사용하며89바이트 payload는 클라이언트와 함께 WRAM으로 복사한다. 최종 본문670바이트·내장 ROM2048바이트다.
- IPL·시작 응답·각 바이트 응답·완료 응답 대기는 각각65535회로 제한한다. 실패하면 게임 화면 경로로 진행한다. 한 번만 쓰는 결과는 A9=FLG20 확인, E1=IPL, E2=업로드 시작, E3=바이트, E4=완료 토큰 시간초과, E5=FLG 불일치다.
- 기존 `$7001`의 첫 비영값 보존 바이트를 초기화 결과에 사용한다. 로그에 `spc_init_status_hex`, `spc_init_status_valid`, `spc_unmute_confirmed`와 필드 역할을 추가했다. **163의 screen_error=169(A9)는 성공 코드**이며 게임 오류는 run_error/run_rom_error로 판정한다. A9는 본체 상태 읽기 확인을 뜻하며 음악 청취·APU 샘플·아날로그 출력 증명이 아니다. 실패 시 실제 잘못된 FLG 값 자체는 별도로 남기지 않는다.
- FPGA RTL·클록·핀·배치는162 그대로다. 따라서6B/E5 식별도 의도적으로 유지하며 허용 ID 범위를 늘리지 않았다. 파일명·펌웨어·내장 SNES 프로그램은163이다. 이전162 FPGA를 잘못 적용하면 초기화 상태0으로 남아 성공으로 처리하지 않는다.

## 최소 검증

실제 SNES CPU/SPC를 실행하는 Mesen에서 정상 A9와 주입한5개 실패 E1~E5를 확인했다. 정상 응답은 master clock106020, 실패 대기 경로는 화면 프레임18~20에서 결과를 냈다. 이는 모델 관측이지 실기 제한시간 측정은 아니다. 각 경우 기존2개 RGB 화면114688픽셀과14회 입력 전달이 유지됐다. 새 전송 프로토콜 전체나 실제 컨트롤러·아날로그 소리·warm reset을 검증한 것은 아니다.

정확한162 상태 RTL에 A9/E1~E5×3위상×3늦은 데이터 조건=54사례를 적용해 SPI 읽기·STOP 뒤 보존·잘못된 후속 쓰기 무시·reset 초기화를 확인했다. MCU의 기존 회수13사례·입력256마스크 포맷과 새 상태값256개×유효성2종=512판정도 통과했다. ARM188824바이트, 강한NMI 연결·15stores/0calls·기존 GPIO/STOP 회수를 유지했다.

## 재배치 없이 FPGA 메모리 갱신

162의 동결 배치 DB를 복제하고 내장 프로그램만 변경했다. `quartus_cdb --update_mif`는 원본 readmemh HEX 대신 합성된 `db/board.ram0_nes_game_bus151_c083f7f7.hdl.mif`를 읽는다. 첫 시도에서 HEX만 바꿔 RBF가 그대로인 것을 검사에서 거부했다. 최종 방식은 기존 MIF2048바이트가162 HEX와 일치함을 확인하고163 데이터로 교체한 뒤 update_mif→ASM→CPF를 실행한다. 생성 MIF와 입력 HEX를 다시 비교하고 새 RBF 및 압축 왕복을 확인했다. 새 MAP/FIT/STA는 실행하지 않았다.

47개 RTL·QSF·SDC·배치/타이밍 보고서 등의 해시가162와 같다. 자원14711LE/5572regs/960·963LAB/56·56M9K/1PLL과 setup+0.121ns/hold+0.177ns 등은 **동일 배치 재사용 근거**다. 새 배치 성과로 계산하지 않는다. 전체IO·MTBF·PCB2ns·reset recovery의 기존 한계도 유지한다.

초기 client01의 상대 경로와 client02의 Lua Unicode escape 오류, asm01의 미반영 거부, asm02의 CRLF 해시 표현 오류를 별도 보존했다. 마지막 오류는 원본 바이트가 일치하는데 LF 표현으로 비교해서 발생했고, 실제 MIF 교체 전 멈췄다. 실행 코드 실패나 라이선스 문제로 분류하지 않는다.

## 재현과 다음 실기

도구는 `build_nes_game163.py`/`test_nes_game163_client.py` → `nes_game163.py`(ARM·배치 복제) → `assemble_nes_game163.py` 순서다. ARM은 기존 `build_nes_run136_arm.ps1` 및163 ARM/host 검사, 상태 RTL은163 status 검사와 기존 FLOAT wrapper를 사용한다. 패키지 게이트는 `release_nes_game163.py`, 동결 무결성은 `verify_nes_game163.py --baseline <로컬 probes>`다. 실패 출력 디렉터리와 완료된 finalizer는 덮어쓰지 않는다.

동결 2510파일, manifest `d8626eade5547e594de623d7077d153eeff5482b2cdea59940a499785209bfc5`. ZIP `52100ec7dcb7347c09d7d9fe830d44cc41f2c95dba02632bcc90b32f3eceffa7` (943415바이트),12항목. ROM·base/menu·044복원 파일은 이전 패키지와 같으며 비공개 로컬에만 보관한다.

실제 SMB3에서 음악·효과음, 첫 레벨 플레이, 두163 TXT와 메뉴 복귀를 확인한다. 소리가 없더라도163 초기화 상태를 먼저 보고 다음 수정 범위를 정한다. 사운드 확인 후 연속 화면을 개선하며, 그 뒤60초 해제·오류/본체 리셋 로그·장시간 입력 유지 순서를 지킨다. 화면은 전체DMA·강제소거·hold6이며 DOWN 문제와 AV 지연 보정도 미해결이다. 동일162/044/GBC/전체 적재 반복은 하지 않는다.
