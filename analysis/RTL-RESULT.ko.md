# NES 실제 RTL 진단 — NES-P2-RTL-006

2026-10-05. SPDX-License-Identifier: MIT.

**기존 무료 FLOAT 라이선스 경로를 연결한 뒤, 자체 NROM을 실제 Questa RTL에서
120.02ms 실행했다. RAM·입력·오디오·CPU 주기 검사를 통과했고, 출력의 256×240 전체
61,440화소가 독립 기준과 일치했다.** 최소 NROM 기능 검증이며 MMC3나 제품 완료는 아니다.

[검증 수치](rtl-verification.json), [소스·증거 해시](rtl-artifacts.json),
[Questa 실행 규칙](../docs/questa-execution.md), [이전 Mesen FETCH-005](FETCH-RESULT.ko.md).

## 재발 방지

사용자 전역 AGENTS.md와 이 checkout의 AGENTS.md에 이미 검증된 Starter FLOAT 실행
규칙을 기록했다. `tools/run_nes_functional.ps1`은 기존 승인된 wrapper를 RunOnly로
호출하고, 절대 경로의 실제 작업을 실행한다. 매번 별도 라이선스 smoke를 하지 않는다.

Python runner도 파일형 기본 라이선스를 받으면 빌드 디렉터리 생성 전에 거부한다.
이 차단을 실제 호출로 확인했다. 임시 서버와 환경변수는 자식 프로세스에 한정되며
종료 후 서버 프로세스와 18000–18002 listener가 0개인 것을 확인했다. 원본 라이선스와
영구 설정은 수정하지 않았다. 잘못된 실행 경로를 라이선스 부족으로 보고하지 않는다.

## 실행하면서 발견하고 고친 문제

고정 upstream 원본은 보존하고, ignored 로컬 사본에만 다음 수정을 적용했다.

1. T65의 Mode/BCD 상수를 각각 2bit/1bit로 명시했다. 주소 출력은 24bit로 받고
   NES 주소는 하위 16bit를 사용한다. 미사용 active-low 입력도 비활성 값으로 연결했다.
2. 초기화되지 않은 cpu_tick_count 때문에 CPU가 매 16 master clocks마다 진행했다.
   첫 1ms의 검사에서 간격 오류 1,207개를 검출했다. reset 시 해당 카운터와
   de-jitter 임시 상태를 초기화하여 12 master clocks 간격을 복구했다.
3. cold_reset이 PPU에 연결되지 않았고 sprite-zero-hit 상태가 첫 pre-render 전까지
   미정값이었다. CPU의 $2002 읽기에서 이를 검출했다. cold_reset을 연결하고 이 상태를
   cold boot에서만 0으로 초기화했다. warm reset의 기존 동작은 바꾸지 않았다.
   이는 Mesen 참조 소스의 cold-boot status 초기 상태와도 일치한다.
4. 기존 NES 옵션에서 de-jitter padding을 끄고 원래 NTSC 타이밍을 사용했다.
   사용하지 않는 cheat 경로는 비활성화/reset하고 APU ultrasonic 확장 입력은 0으로 연결했다.

선언 순서 정리와 위 기능 수정은 서로 구분한다. 변환 diff·입출력 해시·실패 로그는
`analysis/local-rtl-006/`에 보존했다. 개별 HDL 출처/라이선스 채택 보류는 해소된 것이 아니다.

## 최종 결과

| 검사 | 결과 |
| --- | --- |
| 자체 진단 ROM | 원래 MIT checkerboard NROM, 원본 해시 동일 |
| 실제 RTL 실행 시간 | 120.02ms |
| CPU 검사 구간 | 0.1ms 이후 214,634개 CPU enable 관측 |
| CPU 간격 | 12 master clocks, 오류 0 |
| CPU 주소·read/write·data 미정값 | 검사 구간 0 |
| RAM heartbeat / 입력 1 응답 | 각각 49,375 / 17,895 write 관측 |
| 화면 | 256×240, 61,440 indexed-color 화소 차이 0 |
| 펄스 출력 | 약 440.4Hz 설정, 관측 구간의 amplitude edge 53개 |
| 펄스 edge 간격 | 24,384 master clocks, 오류 0 |
| 오디오 미정값 | 관측 구간 0 |
| 독립 비교기의 실패 검출 | 1화소 오염·1화소 누락 모두 거부 |
| Questa 종료 | Errors=0, Warnings=42 |

RAM write 관측 수는 외부 메모리 strobe가 유지되는 master-clock 단위 집계다.
고유 CPU 명령 수나 서로 다른 입력 횟수로 해석하지 않는다. 입력 값은 60.02ms에
0→1로 바꾸고 ROM이 RAM 1에 이를 반영하는지 검사했다.

PPU의 color_pipe[0]은 pixel 계산 뒤 한 dot 지연된다. 소스의 ClockGen 증가와
색 레지스터를 근거로 pixel x를 cycle=x+2에서 읽었다. cycle 2..257을 받아 x=0..255를
모두 보존했으며 화면에 맞춰 offset을 탐색하거나 crop하지 않았다. 별도 Python 비교기는
원래 CHR bitplane과 ROM의 tile-zero nametable/팔레트에서 기대 색을 계산했다.

초기 초안의 `audio_changes >= 100`은 ROM 설정과 맞지 않았다. $4000=$BF,
$4002=$FD, $4003=$08은 50% duty와 timer 253이므로 한 amplitude edge는
8×254 CPU cycles, 즉 24,384 master clocks다. 60.02ms 관측 구간에 가능한
52..54개로 교정하고 간격도 별도로 검사했다. 처음의 40개 결과는 CPU 16-clocks
오류와 함께 실패로 보존한다. 기준을 낮춰 그 실패를 통과시키지 않았다.

SV clock은 half-period 23.280423ns를 선언하지만 1ps 해상도에서 23.280ns로
양자화된다. 보고한 master-clock 간격은 이 시뮬레이션 클록 기준이다.

## 남은 범위

42개 경고는 선택 포트 미연결·일부 폭/범위 차이·시간 0의 VHDL 초기 미정값 경고를
포함한다. 숨기거나 억제하지 않았으며 warning-free signoff는 아니다. CPU 버스는
reset 뒤 지정 검사 구간, 오디오는 60ms 이후 구간에서 미정값 0을 확인했다.

이 테스트는 이상적인 동기 메모리와 단일 cold boot의 NROM 검사다. warm reset,
전체 CPU/APU/PPU 적합성, 실제 메모리 지연, MMC3/A12/IRQ, NES→SNES 통합,
full-fit/STA, 지정 일본판 SMB3 및 실기는 남아 있다. NES 240줄의 캡처 성공은
SNES 239줄 출력 정책의 해결이 아니다. 다음은 이 실행 경로에서 주소가 구분되는
CHR 진단과 자체 MMC3 입력을 확장하여 물리 fetch/IRQ 기준을 대조하는 것이다.

GBC 152개 기준 소스와 이전 P1/STREAM/CACHE/RESIDENT의 47개 소스 항목은 그대로다.
FETCH-005에서 바뀐 driver/testbench 원본도 보존했다. 공통 MCU/FPGA·상용 ROM·SD·
릴리스 자산은 수정하지 않았다.
