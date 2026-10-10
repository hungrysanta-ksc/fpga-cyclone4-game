# NES 현재 인계 — 145 검정·고정 그림 실기 대기

[145 결과](../../analysis/SCREEN145-RESULT.ko.md) · [실행 안내](../../docs/nes-screen145-instructions.ko.md) · [144 실기](../../analysis/SCREEN144-HARDWARE-RESULT.ko.md)

## 다음 행동

145 한 번으로 표시 시작부터 메뉴까지 영상과 두 TXT를 받는다. 적재는 기존 약9분, 표시는 약60초다. 검정90 TV프레임→받은 그림180프레임 고정 반복. 화면 글자 NES144는 의도된 ROM 재사용이며 설치·로그145와 혼동하지 않는다. A/B 순서를 강제하지 않는다. 고정 중 변화/혼합 고정을 구분하되 실제 원인은 미확정이다. 같은144/044/GBC 재시험이나 무변경 전체 적재·배치·정밀 디버그만 반복하지 않는다.

144는 육안 문자와 메뉴 복귀 PASS지만 부분 갱신이 확실히 보고됐다. 짧은 forceblank 미관측을 미실행으로 단정하지 않는다. 대각선 카메라/CRT 띠만 제외하고 육안 혼합은 남긴다. raw stage112/frames161/mask8은 telemetry_trusted0으로 FPS나 완성 화면 수가 아니다.

## 고정 범위와 재사용

NES 전체 fixture와 코어, loader GPIO SPI·전량 대조·CRC·식별5E/D9는144 그대로다. SNES 소비자의90/180프레임 대기와 MCU600→1200관측만 실제 동작 변화다. 명목60초 후RESET→STOP→로그/base/menu 순서, RUN 중SD쓰기 금지는 유지된다. ASM/MIF만 갱신하며142/144 routing/STA/조건부IO를 재사용했다. 오래된 공개 소스와 동결144는 수정하지 않는다.

실제 SNES 모형 정상/혼합 각3개 그림의 고정9장+검정3장, 길이/헤더 오류2개, MCU21사례·ARM NMI·버스65536주소 통과. 전체 보드 동시실행이나145 실기 성공은 아직 아니다. 선택 client01/host02/arm01/armcheck03/normal04/mixed01/bad_length01/bad_header01/rom01/asm01/bus01/reference01/release01. 초기 실행 환경·검사기 오타·Lua 종료 오류는 보존했다.145의 completed freezer/기존 archive를 다시 실행·수정하지 않는다.

## 후속 우선순위

1. 영상 결과로 처음 갈라지는 경계만 수정하고 실제 패드/게임으로 진행한다.
2. 로딩 단축:144 실측 LOAD207.660초+CHECK311.310초. 현 방식 그대로면 매번 반복되며 미완료다. 하드웨어SPI/묶음전송/FPGA측검증을 실제 소유권·오류 차단·검증 완료 START 조건과 함께 설계한다. 검사를 그냥 생략하지 않는다.
3. SMB3(J) mapper4 PRG256KiB+CHR128KiB, 입력·오디오·호환성. SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 현재80KiB진단만 통과했다고 게임 지원으로 쓰지 않는다.

## 공통 보존

보드는 FXPAK Pro Mk.III Rev.D/2022-05-02, STM32F401RCT6, EP4CE15F17C8N, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 기존 FLOAT wrapper1seat를 재사용하고 새 유료 라이선스/부품/PC연결을 다시 요구하지 않는다. GBC152·원래NES334·모든 과거 public pin 유지. 전체IO/MTBF, ACK16ns 실패, E1/E2·8µs·양 클록 정지CE9µs·source-lock4·124격리 유지. 공개에는ROM/바이너리/사용자영상/라이선스/개인경로 금지. PR한국어4절과 사용자머지 원칙. PR89가 열려 있어145를 같은PR에 갱신하며 다음작업 전에 실제상태를 확인한다.
