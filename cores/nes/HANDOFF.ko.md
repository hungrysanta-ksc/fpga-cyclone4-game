# NES 현재 인계 — 145 검정·고정 그림·메뉴 실기 통과

[145 결과](../../analysis/SCREEN145-RESULT.ko.md) · [실행 안내](../../docs/nes-screen145-instructions.ko.md) · [144 실기](../../analysis/SCREEN144-HARDWARE-RESULT.ko.md)

## 현재 실기 판정과 다음 행동

145 영상67.47초에서 검정13구간 약1.4~1.5초와 완전한 그림13구간 약3.0~3.1초, 안정된 A/B와 실제 메뉴 복귀를 확인했다(10Hz 보조 측정,0.1초 해상도). 첫 그림은 촬영 시작으로 잘렸고 마지막 검정에는 복구가 포함된다. 확인 표본에서 고정 중 부분 변화·지속 A/B 혼합은 보이지 않았다. 픽셀 정확성이나144 원인 해결까지 확정하지 않는다.

로그80KiB 적재/대조·RUN/STOP/ROM오류0/base복원 PASS. DISPLAY521120→584510ms=63.390초, 메뉴준비587780ms. stage53/frames1/mask0은 telemetry_trusted0이므로 실제 프레임 수나FPS로 해석하지 않는다. 영상에는 여러 번 표시됐으며 관측 표식만 고치려고 재시험하지 않는다.

사용자 요청에 따라 이번에는 결과·PR만 기록하고 구현은 진행하지 않았다. PR89를 사용자가머지한다. 다음 작업은145를 실기 기준으로 보존하고 긴 블랭크를 줄인 연속 표시·패드·게임으로 전진한다. 같은145/144/044/GBC를 반복하지 않는다. 로딩 단축은 계속 미완료다. [145 실기 결과](../../analysis/SCREEN145-HARDWARE-RESULT.ko.md)를 먼저 읽는다.

## 고정 범위와 재사용

NES 전체 fixture와 코어, loader GPIO SPI·전량 대조·CRC·식별5E/D9는144 그대로다. SNES 소비자의90/180프레임 대기와 MCU600→1200관측만 실제 동작 변화다. 명목60초 후RESET→STOP→로그/base/menu 순서, RUN 중SD쓰기 금지는 유지된다. ASM/MIF만 갱신하며142/144 routing/STA/조건부IO를 재사용했다. 오래된 공개 소스와 동결144는 수정하지 않는다.

실제 SNES 모형 정상/혼합 각3개 그림의 고정9장+검정3장, 길이/헤더 오류2개, MCU21사례·ARM NMI·버스65536주소 통과. 전체 보드 동시 시뮬레이션은 아니다. 이후145 제한 실기는 위 범위로 통과했다. 선택 client01/host02/arm01/armcheck03/normal04/mixed01/bad_length01/bad_header01/rom01/asm01/bus01/reference01/release01. 초기 실행 환경·검사기 오타·Lua 종료 오류는 보존했다.145의 completed freezer/기존 archive를 다시 실행·수정하지 않는다.

## 후속 우선순위

1. 145 고정 표시 통과를 유지하며 긴 블랭크를 줄인 연속 표시·실제 패드/게임으로 진행한다.
2. 로딩 단축:144 실측 LOAD207.660초+CHECK311.310초. 현 방식 그대로면 매번 반복되며 미완료다. 하드웨어SPI/묶음전송/FPGA측검증을 실제 소유권·오류 차단·검증 완료 START 조건과 함께 설계한다. 검사를 그냥 생략하지 않는다.
3. SMB3(J) mapper4 PRG256KiB+CHR128KiB, 입력·오디오·호환성. SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 현재80KiB진단만 통과했다고 게임 지원으로 쓰지 않는다.

## 공통 보존

보드는 FXPAK Pro Mk.III Rev.D/2022-05-02, STM32F401RCT6, EP4CE15F17C8N, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 기존 FLOAT wrapper1seat를 재사용하고 새 유료 라이선스/부품/PC연결을 다시 요구하지 않는다. GBC152·원래NES334·모든 과거 public pin 유지. 전체IO/MTBF, ACK16ns 실패, E1/E2·8µs·양 클록 정지CE9µs·source-lock4·124격리 유지. 공개에는ROM/바이너리/사용자영상/라이선스/개인경로 금지. PR한국어4절과 사용자머지 원칙. PR89가 열려 있어145를 같은PR에 갱신하며 다음작업 전에 실제상태를 확인한다.
