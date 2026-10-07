# NES070 전체 CF68 C→보드 핀 검증 결과

## 작업 목표와 결과

069 실제 C의 전체80/96KiB 통신을 변경 없는068/CF68 물리 top에 연결해 적재·읽기 비교·마지막 ACK·FINISH·STOP을 확인하는 **이번 범위의 목표를 달성했다**. PR24 병합 `8528e15eb5115f16d4f44fb4deed11e3208649a1`에서 진행했다. 디지털 검증이며 실제 STM32/SD/SNES 실행이나 설치 가능한 파일 쌍은 아니다.

| 형상 | 쓰기/읽기/ACK 바이트 수 각각 | 프레임 | C가 소비한 응답 비트 |
| --- | ---: | ---: | ---: |
| fine_x80KiB | 81920 | 409616 | 22938352 |
| banks3296KiB | 98304 | 491536 | 27525872 |
| 합계 | 180224 | 901152 | 50464224 |

두 세션 모두 RAM을 미리 채우지 않고 실제 WE 핀으로 적재했다. 주소·chip·byte-write/word-read·모든 byte/tag/응답과 최종 RAM 전체가 일치했다. 각 마지막 ACK 뒤 FINISH의verified, STOP의loaded/verified 해제, PSRAM·SNES·SRAM 소유권 반환이 통과했다. START/RUN은 없었다.

## 초기 준비·클록 대조·오류 검출

locked 해제 후181µs까지 READY/PSRAM 비활성을 확인하고 모델 READY 이후 캡처를 시작했다. READY는 시뮬레이션 시각201.0625µs, locked 해제 후200.0625µs다.8MHz SPI/PSRAM은 계속 동작한다. 캡처 안의 명시2µs 전환·샘플·CS 시간은 유지했다. 실제 MCU의poll·SD시간·interrupt jitter·전원 안정 측정은 아니다. 원시 `%t` 출력의 `ready_ns=201062500`은1ps precision 값으로201062.5ns를 뜻한다.

원래84MHz/H1 클록 조건의 초기64프레임은29물리쓰기/3440응답비트, 미사용 H1 mask/legacy park의8192프레임은4093쓰기/458608비트로 통과했다. full의 초기64경계와도 같다. 이후loader6x명령·8MHzreply만 사용함을 검사한다. 미사용84MHz stub 정지는 시험의 성능 변경이며 실제 PLL·모든 보드 클록의free-running 검증이 아니다.

CF의 C 소비 응답 비트 하나를 바꾸는 대조는 `070 MCU sample mismatch frame0 opcf bit8`에서 실패했다. 최초baseline01은 복사한 testbench의 모듈명이 옛 이름이라 최적화에서top을 찾지 못했다. 모듈명과 license 이전 preflight를 수정한baseline02와 전체 시험이 통과했다. 첫 실패 원문을 보존하고 제품 RTL·라이선스 오류로 취급하지 않는다.

## 근거와 재사용 범위

생산 SV15개가068 fit03 해시와 같다. 변환한 H1 경계는 원본을 별도로 보존하고 시험 clock 표현 하나만 대조했다. 입력은 동결069의 실제 C·플랫폼·fixture·trace다.069 최종 ARM179336바이트 SHA `268bc38df477516cbcee19f17b192151b79c6e011dc801756d1ad02fc0262499`와 하위95/상위/오류 회귀는 변경 없어 재사용한다. 새 ARM·map/fit/STA/ASM은 실행하지 않았다.

068의2400LE/195LAB/1479regs/44M9K/135핀/PLL1·내부30summary/최소hold0.140ns는 같은 RTL 경계의 근거다. RAM 모형70ns/35ns/350ns는 완전한 EBLL 전기 min/max 승인이 아니다. 전원 안정·PCB/SPI/SNES 조건과 lockedHIGH 쓰기 클록 정지의CE>8µs 반례는 남는다. 전체 NES059의959LAB/4여유/마지막8프레임은 별도 근거다.

동결 **297파일**, manifest `8e03dbc0ef18b5ab9d2ba63bfde8612325b6bd9f5d32f35900b887ebe21fc00a`. [계약·재현](../docs/nes-cf68-session-contract.md)과 `tools/verify_nes_cf68_session.py`로 private 증거를 감사한다. 공개 clone은 동결 입력·로그를 제공하지 않는다. `freeze_nes070.py`를 재실행하거나044–070 동결을 수정하지 않는다. FLOAT 한 좌석의 순차 작업은 정상 종료했다.

## 미완료와 다음 목표

H10의 현재 디지털 전체 세션을 갱신했지만 준비도 **5완료/6부분/1미완료**는 유지한다. 실제 SD/base/menu 형상·독립 백업/복원·가시성/시간/재진입/GBC·외부 전기 조건은 미완료다. installable/hardware/clock_halt_safe=false다.

다음 완료 조건은 **동일068 fit의 Standard ASM/CPF→정확한 압축→실제 C의 전체 byte 복원→고정069 ARM/marker069/fpga_nl8/CF68의 쌍 manifest**다. 실제 SD 원본 호환성과 회복 조건을 확인한 뒤, 사용자가 외부 실기에서 실행하고 TXT·영상·GBC 관측을 전달할 제한 패키지를 준비한다. 기존066 도구의061/065 고정을 새 실행기로 분리하고 CF61 쌍과 섞지 않는다.
