# 134 최소 RUN 물리 결선과 SPI 관측 회로

PR79 병합 `91fa3f0551827cadef7e62b982608d609a2f48d7`에서 시작했다. **95개 실제 핀을 사용하는 최소 RUN 회로와 CPU 진행 관측을 구현했다. 기능 시험·배치는 성공했지만 같은 클록 타이밍 −0.330ns 때문에 설치용 패키지는 만들지 않았다.**

## 작업 목표

131/133의 가상 포트 기반 코어를 실제 보드에 연결하고, 화면 없이도 MCU가 내부 NES CPU의 동작과 오류를 읽을 경로를 마련한다. SNES 소비자에 대한 기존 구현을 확인해 최소 RUN 실기와 전체 화면 통합을 구분한다.

## 작업 내용

`fxpak_nes_run134_top`은 보드 CLKIN(M2), SNES_SYSCLK(A9), PSRAM, MCU SPI(P2/M1/R1/P3), MCU_RDY(H2)를 연결한다. 기존 `src/fpga/pin.qsf`의 핀 위치·IO 설정을 추출하고 실제 Fitter pin 보고서95개를 하나씩 대조했다. 가상 핀은0개다. 사용하지 않는 SRAM 쓰기/활성 신호를 비활성으로, SNES 데이터와 SRAM 데이터를 고임피던스로, DAC/IRQ를0으로 둔다. 나머지 패키지 핀은 입력으로 예약한다. QSF는 input tri-stated를 지정했으나 **실제 Fitter 보고는 weak pull-up 포함**이다. 출력 ground 예약은 없으며 이를 pull-up 없는 입력이라고 기록하지 않는다.

기존131 core는 초기값 없는 선언4개 이동 및 관측 출력3개 추가 외에 기능식을 바꾸지 않았다. core reset, 유효 CPU ROM 샘플, 메모리 사용 준비를 밖으로 보낸다. 전원 초기화4단은8MHz CLKIN으로 진행하고 관측 회로 reset 해제는 별도2단 NES 도메인 체인을 거친다. STOP은 관측 기록을 지우지 않으며 FPGA 재구성이 새 세션을 만든다.

**SNES 소비자 조사:** 기존 H1 보드는24KiB 내부 프로그램 ROM, LoROM 읽기, `$00600B/C` epoch 및 NCR1 transport에 의존한다. 현재 live top에는 그 프로그램 ROM/버스 중재가 없다. 따라서 H1 소비자를 단순히 물리 핀에 연결해 화면 실행을 주장할 수 없다. 이번 최소 RUN 셸은 `arm=0`·SNES bus idle이고 MCU가 실제 SNES RESET을 계속 잡는 계약이다. NES CPU는 별도 FPGA 내부에서 동작한다. 화면·입력·소리·mapper4를 포함한 게임 코어 배치로 이 자원 결과를 사용하지 않는다.

### SPI 관측 계약

mode0, 최대250kHz, CS setup/hold 각1µs 이상. 기존 로더60..6A 명령은 그대로다. 추가한 읽기 전용 `70 00 00 00 00 00 00 00`의 첫 수신 바이트는 미정/고임피던스이며 버리고, 이후7바이트를 읽는다.

| 응답 위치 | 의미 |
|---|---|
| 1 | `D4` 관측 규격 식별값 |
| 2 | bit0 core reset 유지, bit1 첫 ROM 서비스 오류 기록 존재; 나머지0 |
| 3 | 최초 ROM 오류 코드, 하위4비트 |
| 4..7 | 유효 CPU ROM 샘플 누적32비트, big endian, 최대값에서 포화 |

샘플은 캐시 hit를 포함한 실제 CPU ROM sample event다. 명령 수·프레임 수·PSRAM 물리 읽기 횟수와 같지 않다. 명령 바이트를 수신한 순간 전체56비트를 저장하므로 전송 중 CPU가 진행해도 응답이 섞이지 않는다. 오류와 count는 STOP 뒤 남는다. 두 SPI slave가 동시에 선택되면 MISO는 고임피던스로 처리하고 raw SS 상승 시 즉시 해제한다. 낯선 명령과 잘린 관측 읽기는 로더를 시작/중단하지 않는다.

이 관측 프로토콜은 CRC/전체 오류 분류를 추가하지 않는다. ROM 서비스 오류만 보관하고 boot/SPI 오류는 기존65 응답에서 읽는다. MCU_RDY는 guard/startup으로 정한 메모리 사용 가능 상태이며 RUN·게임 성공·오류 없음 표시가 아니다. 소스 클록 정지 시 관측 slave도 진행하지 못한다. 향후 MCU는 bit마다 기존 shared fault/RDY/예산을 검사하고, 정지 시 재시도·SD/UART 복구 없이 기존 fail-stop 계약을 지켜야 한다. 읽기만으로 이 복구 구현이 끝난 것은 아니다.

## 작업 결과

최종 **test02/fit02**. 실제 core/loader/SPI/PSRAM 핀 모델을 새 물리 셸에 연결했다. 이상적인 PLL,70ns RAM, 합성 JMP `$8000` 이미지, 적재 수/검증 완료 초기값을 사용했다. 실제 BEGIN/END/START/STOP을 SPI로 전달했고 전체 적재/CHECK는 반복하지 않았다.

- 두 source 위상0/3.5ns: 관측14회, 실제 CPU ROM sample6,712회. 별도 포화 경계 초기값·주입8회는 CPU 실행 통계에서 제외했다.
- RUN 중 증가, STOP 뒤 유지, 최초 오류 유지, 포화, 낯선 명령/부분 읽기 격리, raw CS MISO 해제, SNES/SRAM 버스 비구동 통과.
- 오류 입력 강제 주입은 **관측 레지스터의 보존 시험**이며 ROM fault 검출기의 새로운 증명이 아니다.
- 응답 마지막 바이트를 저장값 대신 실시간 count로 바꾼 부정 대조는 두 번째 관측에서 `coherent snapshot` 오류를 검출했다.
- 최초test01/fit01에는 observer reset 도메인 해제가 없었다. 최종test02/fit02에서2단 해제를 추가했다. test02 이후 QSF unused-pin 선언만 추가했으며 시뮬레이션 회로와 최종 배치 회로의 해시는 같다. 초기 결과도 보존한다.

| 최종 배치/타이밍 | 결과 |
|---|---|
| 소자/실제 핀/가상 핀 | EP4CE15F17C8 /95 /0 |
| LE / LAB /register /M9K /PLL | 12,001 /893 /4,087 /12 /1 |
| NES 같은 클록 setup 최솟값 | +7.445ns |
| memory168 같은 클록 setup 최솟값 | **−0.330ns, 미통과** |
| 전체 같은 클록 hold 최솟값 | +0.179ns |
| raw setup 최솟값 | −6.173ns, CHR 설정→reader 경로 포함 |
| IO 미제약 | 입력19 /출력44 |

실패한 같은 클록 경로는 `diagnostic_release.release_reset[1]`에서 `loader_boot.control.pending_body_error[2]`까지다. fit02의 `same134-8_slow_1200mv_85c-setup-2.rpt`에 상세 경로를 남겼다.131의 +0.041ns를 이 새로운 물리 배치의 결과로 상속하지 않는다. 호스트84MHz의 화면 경로와 transport 등이 상수화/제거되어 자원이 줄었으며, 이 여유를 전체 영상·MMC3 여유로 계산하지 않는다.

CDC/reset/IO/MTBF를 새 배치에서 승인하지 않았고 false path/클록 완화도 추가하지 않았다. 합성84 warnings 및 PLL 보상/IO 인터페이스/OE 관련 Fitter 경고, 초기 시각 미정값 시뮬레이션 경고를 원본 로그에 보존했다. 정상 시뮬레이션 오류0. 새ARM/ASM/SD 패키지/실기 실행은 없다.

## 작업 의미

실기 코어 동작을 위한 **보드 결선 구현과 디버깅 기반**이 진전했다. 가상 핀을 실제 보드 신호로 바꾸고 내부 CPU 진행을 MCU가 읽을 회로를 마련했다. 화면·게임 호환성 완성이 아니다. 타이밍 실패를 발견했으므로 최소 실기 RUN 목표는 부분 달성이다.

다음: 134fit02의 diagnostic_release -> SPI pending_body_error[2] 같은 클록 -0.330ns 경로를 상세 보고서로 수정한다. 변경 경계 시험과 새 배치의 reader/guard/reset/외부IO만 확인한 뒤 MCU70/D4 관측·유한 RUN·STOP·진행TXT·메뉴/044복원을 연결해 최소 실기 패키지로 간다. 전체 화면 소비자·MMC3는 별도이며 무변경 전체 적재/부품/저장/131배치를 반복하지 않는다.

119 전체80KiB 적재/검증/STOP/메뉴·044 복원, 기존 GBC 증거, SMB3(J)/mapper4 첫 게임 목표를 유지한다. 제한 진단 준비도6완료/5부분/1미완료는 게임 완성률이 아니다. E1/E2·외부 전기 조건·MTBF·8µs·양클록 정지 lockedHIGH CE9µs 반례는 미해결이다.

## 재현/보존

`run_nes_board134.ps1`에 기존 FLOAT wrapper/Python/Questa/새 ASCII 출력/인접 baseline을 전달한다. `nes_board134_fit.py`로 새 물리 배치를 생성하고 완료 후 그 디렉터리에서 `quartus_sta -t nes_board134_timing.tcl`을 실행한다. `verify_nes_board134.py --evidence <frozen134>`는 원본131을 포함한 입력/실행 소스/실제 핀/관측 결과와 **타이밍 실패 상태**를 검증한다.

동결873파일, manifest `304db3427a50dbcf59dd7d3975d27dc0e37427b1a993c72024af4c05038469a8`. archive044–134 및 완료 finalizer 수정 금지.124 격리된 manifest 문제를 다시 사용하거나 복구하지 않았다. 네트워크 sandbox fetch 실패 뒤 허용된 host fetch로 병합을 확인했다. 라이선스 오류·승인 거부는 없었다.
