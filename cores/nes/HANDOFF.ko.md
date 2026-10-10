# NES 현재 인계 — 143 비교 시험 대기

[143 결과](../../analysis/SCREEN143-RESULT.ko.md) · [실행 안내](../../docs/nes-screen143-instructions.ko.md) · [검증](../../analysis/screen143-verification.json)

## 다음 작업

143 한 번으로 A 파랑/B 직접 만든 빨강·청록 타일/C ROM atlas/D 기존 NES 화면을 기준 PNG와 비교한다. 두 TXT와 관찰한 단계, 자동 메뉴 복귀 여부를 받는다. 기존 약 9분 적재 후 약 30초 표시이며 전체 관찰 기준은 최대 10분이다. 동일 142/044/GBC 시험은 반복하지 않는다.

**141/142 사진 외형만으로 정상 영상 실패를 확정한 판단은 철회했다.** 정확한 진단 ROM의 정상 에뮬레이터 출력 자체가 잡음형이다. 143 D의 3프레임은 동결 142 RGB와 바이트 단위로 동일하다. 사용자의 글리치·느린 변화 관측은 유지한다. 실기 픽셀 정상도 아직 확정하지 않는다. 다음 작업자는 잡음 모양만으로 디버그 반복을 재개하지 말고 먼저 동봉 기준과 비교한다.

A/B가 정상이고 C/D가 기준과 비슷하면 명확한 NES 패턴·입력/게임 연결로 전진한다. 차이가 있으면 처음 갈라지는 경계만 수정한다. `screen_phase_mask=15`는 단계 도달 관측이고, `screen_frames`는 소프트웨어 전송 완료 횟수다. 실제 TV FPS나 올바른 VRAM 전체 내용은 보증하지 않는다. `MENU_PREPARED`도 실제 메뉴 표시와 구분한다.

## 구현·검증 인계

- 같은 142 FPGA 회로·배치·ID 5E/D9를 유지한다. 143은 새 프로그램 ROM·MCU 펌웨어·파일명 조합으로 구분한다. ID를 임의 변경하거나 여러 ID를 무조건 허용하지 않는다.
- A/B/C 각 180수직귀선 후 D로 진행한다. MCU는 600×50ms 동안 기존 SPI73으로 단계 비트를 누적한다. SD 쓰기는 STOP 이후다. 적재 전 표시를 위해 검증된 RUN 조건이나 reset 보호를 우회하지 않았다.
- 선택 결과는 rom01/asm01/arm01/armcheck01/host04/reply01/mesen01/bad_length/bad_header/bus01/reference01/release01이다. 최종 동결은 `evidence-final`이며 manifest는 검증 JSON을 따른다. 부분 `evidence`는 최초 동결 목록 검사 실패 자료로 보존했다.
- A/B/C 독립 RGB 대조, D 기존 RGB 3프레임 일치, 길이·헤더 오류, 실제 MCU 호스트 21사례, decoder 12사례, ROM 버스 65,536주소, ARM NMI 검사와 패키지 해시가 통과했다. 실제 하드웨어 결과는 아직 없다.
- armcheck01은 host03 공통 소스로 검사했고, 최종 host04 공통 MCU 소스 해시가 동일함을 확인했다. 초기 host01~03 실패는 옛 모형의 명령 범위·10초 기대값 때문이다. 실제 MCU 실패로 기록하지 않는다.
- 새 프로그램 HEX와 생성 MIF 24,576바이트를 함께 대조했다. ASM만 실행했고 142 타이밍을 재사용한다. 변경 없는 MAP/FIT/STA/전체 적재 검증을 반복하지 않는다. 전체 외부 IO·MTBF 승인으로 확대하지 않는다.
- 141 ACK16ns 실패, E1/E2·8µs·양 클록 정지 CE9µs·source-lock4·124 격리를 유지한다. 동결 finalizer와 과거 증거·public pin은 수정하지 않는다.

## 장기 목표와 공통 규칙

SMB3(J) SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. GBC152/원래NES334 및 모든 과거 public pin 보존. 부품은 사용자 사진의 FXPAK Pro Mk.III Rev.D/2022-05-02,STM32F401RCT6,EP4CE15F17C8N,PSRAM IS66WVE4M16EBLL-70BLI 두 개를 기준으로 한다. 다시 제품명/속도를 묻지 않는다.

Questa는 기존 FLOAT wrapper와1seat를 재사용한다. uncounted Terminal Services 실패경로/새 유료 라이선스 요구를 반복하지 않는다. 한 번에 한 작업. Git에는 ROM/펌웨어/FPGA 바이너리/미디어/라이선스/개인경로를 넣지 않는다. PR은 한국어 제목과 작업 목표·작업 내용·작업 결과·작업 의미4절, 사용자가머지한다.
