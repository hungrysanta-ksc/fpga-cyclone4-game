# NES107 보드 자료·클록 고장 경로 조사

이번 목표인 기존 자료의 적용 가능성 조사와 대안 구체화는 완료했다. **실기 진입 조건 E1/E2는 해결하지 못했고 계속 미결이다.** 현재 조합은 설치 미승인 상태다(installable=false). 새 펌웨어·FPGA·패키지를 만들지 않았다.

## 확인된 사실

| 근거 | 확인 내용 | 사용할 수 없는 주장 |
|---|---|---|
| 공식 upstream cf7e21d7의 KiCad tree 192개 blob | 공개 Rev.F는 2014년 LPC1754·XC3S400-PQ208·MIC23250-S4YMT 회로 | 사용자 STM32F401·Cyclone IV Pro Rev.D의 레일·배선·풀업 상한 |
| 같은 tree의 RevD 폴더 | 2011년, 시트 내부 Rev C, LPC1754·Spartan-3 | 폴더명이 D이므로 2022 Pro Rev.D와 같다는 판단 |
| 고정104 clock.c/autoconf.h | SYSCLK는 HSE→PLL, FPGA 출력은 HSE→MCO1 PA8. CPU 설정84MHz | MCU TIM2를 별도 독립 발진기로 취급 |
| 고정104 startup.S/기존 ELF symbol dump | NMI_Handler와 __unhandled_exception이 모두0x0800c60e의 루프 | CSS를 켜면 이미 구현된 복구 처리가 실행된다는 판단 |
| 고정086 fit03 QSF와 board.pin | CLKIN=M2, ROM_1CE=G16, ROM_2CE=J16, SNES_SYSCLK=A9 | 핀 설정을 실제 전압·PCB 전파지연·CE 풀업 측정으로 취급 |

공개 회로도는 [공식 고정 커밋의 Rev.F](https://github.com/mrehkopf/sd2snes/tree/cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1/pcb/kicad/RevF) 및 [RevD 폴더](https://github.com/mrehkopf/sd2snes/tree/cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1/pcb/kicad/RevD)와 대조했다. 원격 KiCad tree는 truncated=false이며 192개 파일의 Git blob을 로컬 Git 객체와 모두 비교했다. 소스14개는 해시로 고정했다. 조사한 tree와 [Krikzz 제품 페이지](https://krikzz.com/our-products/cartridges/fxpak-pro.html)에서 해당 Pro Rev.D의 전기적 상한을 확보하지 못했다. 인터넷 전체에 회로도가 없거나 비공개라고 단정하는 결론은 아니다.

104의 clock_init에는 CSS 활성화 코드가 없다. 이 소스 사실을 부트로더 실행 후 실제 RCC_CR 값 측정으로 확대하지 않는다. ELF 해시는 기존104와 대조했으며 NMI symbol dump를 재사용했다. 새 ARM 실행이나 디스어셈블은 수행하지 않았다.

## 대안 판정

[ST RM0368 Rev6 §6.2.7, p.99](https://www.st.com/resource/en/reference_manual/rm0368-stm32f401xbc-and-stm32f401xde-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)는 CSS의 HSE 고장 감지, HSI 전환, NMI 및 TIM1 break 전달을 설명한다. CSS 플래그 처리가 필요하다. 이는 검토 가능한 구제 경로지만, 현재104에 구현돼 있지 않다. HSE가 살아 있는 FPGA 내부 고장이나 전원·CPU·GPIO 고장까지 검출·보호하는 기능으로 확장하지 않는다.

[Intel Cyclone IV 핀 연결 지침의 nCONFIG 항목](https://cdrdv2-public.intel.com/654618/pcg-01008.pdf)에 따르면 LOW 입력은 설정을 지우고 I/O를 high-Z로 만든다. **High-Z는 PSRAM CE가 곧바로 유효 HIGH라는 뜻이 아니다.** 실제 풀업·부하·전압과 상승 지연이 필요하다. PA1의 PROG_B 제어를 nCONFIG 종료 경로 후보로 삼되, 보드 전기적 연결과 지연은 별도 검증한다.

| 대안 | 이번 판단 | 남은 조건 |
|---|---|---|
| 현재 TIM2에 watchdog 추가 | HSE 공통 고장을 위한 독립 보호로 채택하지 않음 | 클록 소스 분리 없이는 동일 의존성 |
| 진단 중 CSS + NMI에서 nCONFIG 종료 | 다음 구현 후보로 선택. HSE 고장 이후 추가 동작 차단 목적 | 감지/예외 진입/레지스터 접근/패드 해제/CE 상승 최악 지연. 정상 세션·GBC 보존 |
| HSI 기반 별도 감시/하드웨어 timer 출력 | 예비 설계 후보, 현재 적용하지 않음 | 핀 mux·배선 확인, 타이밍 재설정, 타이머 소유권, MCU/전원 공통 고장 제외 |
| 외부 독립 회로로 CE 강제 비활성 | 보드 변경이 필요한 대안, 사용자에게 개조 지시하지 않음 | 정확한 회로도, 전압 호환, 출력 충돌 방지, 전원 상실 상태와 최악 지연 |
| 정상 전원·클록의 제한 실험 | 설계 승인과 구분되는 선택지이며 이번에 승인하지 않음 | 남는 고장 범위와 전기적 가정의 명시적 판단. 성공해도 E1/E2 전체 해소 아님 |

## 검증과 제한

이번 PASS는 원격/로컬 Git 객체와 고정 소스·핀·심볼의 일치 검사다. 새로운 RTL·fit·STA·ARM 빌드·Questa·실기 검증은 없다. 첫 조사에서 Windows checkout 줄바꿈을 Git blob과 직접 비교해 실패했다. 해당 기록을 보존하고 Git 객체 원본 바이트를 비교해 완료했다. 제품 오류나 회로 실험 실패가 아니다. pyelftools 미설치로 신규 ELF 파서를 사용하지 않았고 기존104의 symbol 근거를 재사용했다.

보존한 private evidence는 probes/nes-board107/evidence이며 [검증 메타데이터](board107-verification.json)의 manifest로 식별한다. 공식 tree 목록·192개 blob 해시·14개 입력·실행 조사 스크립트가 포함된다. 공개 clone만으로 private evidence를 재현했다고 주장하지 않는다.

## 다음 작업과 작업 의미

다음은 진단 세션에 한정한 CSS/NMI 고장 종료 경로의 구현·호스트/ARM 검증이다. 정상 GBC 경로와 공유 fault를 보존하고, HSI 전환 후 SD/UART/메뉴 복구를 시도하지 않도록 한다. 이 기능의 고장 범위와 nCONFIG→패드 비활성→CE HIGH 지연을 분리해 기록한다. E1의 보드 전압·부하·배선 근거와 E2의 8µs 상한은 별도 미결이며, CSS 추가만으로 시험을 승인하지 않는다.

실기 디버깅 기반의 설계 검토다. 잘못된 회로도나 MCU 타이머를 독립 보호 근거로 사용하는 경로를 배제했다. 코어 배선·게임 기능·새 실기 성공을 추가한 작업은 아니다.

정확한 후속 구현 경계와 필요한 계측 결과는 [107 후속 작업 계약](../docs/nes-board107-actions.ko.md)을 따른다. 105 파일 쌍/104 ARM/097 ASM/044 복원 및084·092 실기 근거를 재사용한다. 두 클록 정지·locked HIGH에서 CE9µs 반례는 그대로다. 준비도4완료/7부분/1미완료, SMB3(J) mapper4/384KiB 첫 목표는 변하지 않는다.
