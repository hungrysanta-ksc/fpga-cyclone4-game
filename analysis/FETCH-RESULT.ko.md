# NES 실제 CHR fetch 관측 — NES-P2-FETCH-005

2026-10-05. SPDX-License-Identifier: MIT.

**최소 NES RTL의 컴파일·최적화는 통과했다. Questa 실행은 현재 Windows 세션의
라이선스 제한으로 시작되지 않았다. 별도로 자체 NROM을 Mesen에서 실행하여
8프레임의 CHR 접근과 256×240 전체 화소를 검증했고, 재실행 결과도 같았다.**
P2 조사 항목을 추가한 것이며 P1 영상 성립성이나 P2 RTL 기능 검증 완료는 아니다.
제품 목표는 지정 일본판 SMB3 Mapper4/MMC3, Rev.D / NTSC 그대로다.

[재현·관측 계약](../docs/nes-fetch-contract.md), [기계 판독 결과](fetch-verification.json),
[소스·로컬 증거 해시](fetch-artifacts.json), [이전 RESIDENT-004](RESIDENT-RESULT.ko.md).

## RTL 컴파일에서 달라진 점

고정 NES_MiSTer 커밋 `49a0a662e244469ca77b2155746a066df704ffae`에서 NROM의
CPU/PPU/APU·savestate 의존성만 명시적으로 선택했다. 전체 플랫폼·특수 매퍼·OPLL은
이 컴파일에 넣지 않았다. 원본 checkout은 수정하지 않았다.

로컬 사본에서 모듈 선언 순서, net 초기화의 continuous assign 표현, 절차적으로
구동되는 변수의 wire/reg 선언, CODES의 포트 폭 parameter 위치를 정리했다.
클록·cycle 수식·메모리 응답 지연을 바꾸지 않았다. 정확한 변환 diff와 입력/출력
해시는 ignored 증거에 있다. 컴파일 가능성이 기능 동등성을 증명하지는 않는다.

Questa의 VHDL 7개 단계, 최소 SV, 원래 checkerboard 진단 testbench 컴파일은
모두 종료 코드 0이다. vsim 내부 최적화는 Errors=0 / Warnings=28까지 진행했다.
이후 `intelqsimstarter` 라이선스가 Windows Terminal Services guest session을
거부하여 종료 코드 12로 끝났다. RTL 진단 assertion은 실행되지 않았다.
라이선스나 세션 감지 설정을 바꾸지 않았다.

28개 경고에는 PPU cold_reset, APU/Squ2 allow_us, clockgen_pause의 미연결 포트
등이 포함된다. 실행 가능한 환경에서 초기값·기본값·reset 의미를 확인해야 한다.
현재의 ideal synchronous memory testbench도 실제 외부 메모리 검증을 대체하지 않는다.
기존 소스별 라이선스 보류는 유지하며, 변환 HDL·upstream 사본·diff는 공개 대상에서 제외했다.

## 실제 NES 에뮬레이터 관측

자체 제작 NROM은 512개의 서로 다른 CHR 타일, 반복 tile 0..255 nametable,
동일한 4색 BG 팔레트, 스크롤 0, BG 표시를 사용한다. CPU가 VBlank마다 $2000의
BG pattern-table bit를 바꾼다. **MMC3 bank write가 아니다.** Sprite 표시는 껐지만
PPU가 하는 dummy sprite fetch는 따로 관측했다. 관측 Lua는 메모리나 반환 값을 바꾸지 않는다.

| 항목 | 결과 |
| --- | --- |
| 정상 실행 | 8 연속 프레임, 독립 재실행 동일 |
| 화소 비교 | 매 프레임 256×240, 차이 0, crop 없음 |
| 프레임 간격 | NTSC 357,364 / 357,368 oscillator counter ticks 교대 |
| CHR read | 프레임당 20,244 |
| BG pipeline read | 16,388 |
| sprite dummy read | 3,856 |
| 실제 화면 화소에 기여하는 CHR read | 15,360 = 240×32×2 |
| 실제 화면에서 사용한 타일 | 256개 = 원본 2bpp 4,096B |
| 물리 주소·CHR 값·화면용 fetch 주소·읽기 cadence | 모두 기준 일치 |
| $2000 write → 첫 BG fetch counter 차 | 27,052~27,124 |
| $2000 write → 첫 화면용 fetch counter 차 | 28,332~28,404 |
| 실패 검출 | 읽기 누락 / 잘못된 CHR byte / 화소 오염 / 프레임 누락 모두 거부 |

시간 값은 NES `ppu.masterClock` 관측 차다. 4 ticks/PPU dot이며 SNES 전송 시간과
직접 같은 스케줄로 취급하지 않는다. PPU read callback은 Exec 내부의 counter 증가 전,
CPU write callback은 Run 뒤에서 관측되므로 한 dot의 callback 위상 차가 있다.
정밀 CPU φ2 write 시각을 입증한 값이 아니다. Mesen의 sprite fetch는 두 plane을
같은 dot에서 읽는 근사가 있어 MMC3 A12 실기 타이밍의 증거로도 쓰지 않는다.

## 영상 경로에 주는 의미와 남은 범위

RESIDENT-004의 “미래 데이터가 8프레임 전에 주어진다”는 가정과 달리, 이 입력의
선택 레지스터는 화면 직전 VBlank에서 바뀐다. 그러나 **전체 8KB CHR 자체는 실행 전부터
존재하며 두 테이블을 모두 상주시킬 수 있다.** 이 시험은 실제 게임의 캐시 miss,
미래 CHR 데이터 가용성, 예고 없는 Mapper4 전환의 해결 또는 불가능 증명이 아니다.

다음은 자체 MMC3 입력에서 $8000/$8001 write, 물리 CHR mapping, IRQ/A12 근거를
수집하고 캐시 resident/miss를 구분하는 일이다. RTL과 비교할 때는 현재 라이선스
실행 제한과 경고 의미를 먼저 해소해야 한다. SNES 239줄 출력의 240번째 줄 처리,
실제 NES→SNES 통합·외부 메모리·전체 fit/STA·SMB3·실기는 여전히 미검증이다.
기존 239줄 합성 재생 결과를 이번 240줄 NES 관측으로 대체하거나 확장하지 않았다.

이전 P1/STREAM/CACHE/RESIDENT 소스 해시 47개 항목과 원래 초안 3개가 유지됐다.
GBC 기준 152개 소스·Quartus 입력·2,048개 reachable boot byte 검사도 통과했다.
상용 ROM, 공통 MCU/FPGA, SD, 릴리스 자산은 변경하지 않았다.
