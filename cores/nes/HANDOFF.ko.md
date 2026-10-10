# NES 현재 인계 — 143 실기 통과, 144 읽기 쉬운 그림 대기

[144 결과](../../analysis/SCREEN144-RESULT.ko.md) · [실행 안내](../../docs/nes-screen144-instructions.ko.md) · [검증](../../analysis/screen144-verification.json) · [143 실기](../../analysis/SCREEN143-HARDWARE-RESULT.ko.md)

## 다음 작업

144 두 TXT, 읽을 수 있는 `NES 144` 글자·테두리와 A/B 관찰, 자동 메뉴 복귀를 받는다. 같은143/044/GBC를 반복하지 않는다. 읽을 수 있는 영상 통과 후 패드 연결, SMB3(J) mapper4·384KiB 플레이·오디오로 진행한다. 기존 약9분 적재가 남아 있고 표시 약30초, 전체 관찰 기준 최대10분이다.

143은 사용자 사진·설명으로 A/B/C/D 순서와 자동 메뉴 복귀까지 확인됐다. 적재·대조81,920바이트, RUN/STOP·base·기록 오류0. 마지막 단계 표식은112/mask8로 기대99/15와 다르므로 신뢰하지 않는다. frames122는 정상 TV 프레임 수가 아니다. 정상 진단 자체가 잡음형이었던 과거 오류 해석을 반복하지 않는다.

## 구현 및 증거

- 144는 NES PRG·헤더를 그대로 두고 CHR만 글자·테두리로 바꿨다. 기존 MMC3 뱅크0/8과 순차 타일맵이 A/B 그림을 만든다. SNES의 단색 비교는 생략하고 실제 NES 패킷을 표시한다.
- FPGA RTL·배치·5E/D9 식별은143/142 그대로다. 새 ROM/MIF24,576바이트와 ASM, 새144 MCU/CRC/파일 조합이다. 변경 없는 MAP/FIT/STA를 반복하지 않는다. RUN 중 SD 쓰기를 추가하지 않았다.
- `screen_telemetry_trusted=0`이며 원시 값은 보존한다. 기존 관측기가 늦게 도착한 데이터 대신 이전0x70을 잡는 가설을80ns 주입 시험으로 재현했다. 보드 실측·정확한 실기 원인·수정 완료는 아니다. 이 문제만으로 표시 통과를 되돌리거나 재배치를 반복하지 않는다.
- 현재 CPU/PPU/service/reader RTL 4프레임245,760픽셀과 독립 글자 기준, 수송8,032바이트, 실제 SNES CPU/PPU/DMA3프레임183,552픽셀 및 오류2사례, MCU21사례, ARM NMI, ROM버스65,536주소와 패키지 검증이 통과했다. 모형 연결 범위는144 결과를 따른다. 실기144는 아직 없다.
- 선택 fixture02/client02/rom01/asm01/arm01/armcheck01/host01/core01/normal/bad_length/bad_header/bus01/status01/reference01/release02. 초기 fixture01은 뱅크 묶음 오류로 폐기했고 보존했다. core01 RTL은 최초 실행 통과; 느린 Python 후처리만 중단·수정해 저장 결과를 재검사했다. wrapper 종료1을 RTL 실패로 오해하지 않는다.
- 최종 보관은 `evidence-final`/`release02`다. 최초 공개 해시 검사에서 CRLF와 Git의 LF 변환 차이를 발견해 다섯 텍스트 파일의 개행만 통일했다. 초기 동결본은 유지했고 RTL·ARM·픽셀 검사를 반복하지 않았다.
- 동결144 manifest와 모든 과거 public pin을 유지한다. core 검사는124 테스트벤치에 현재143/142 핵심 소스를 적용한 한 위상이다. 전체 FPGA/MCU/SNES 동시 시뮬레이션이나 전체 외부 IO·MTBF 승인이 아니다.
- 141 ACK16ns 실패, E1/E2·8µs·양 클록 정지 CE9µs·source-lock4·124 격리를 보존한다. 제품 정보나 새 라이선스를 다시 묻지 않는다.

## 공통 규칙

SMB3(J) SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. GBC152/원래NES334 및 모든 과거 public pin 보존. 부품은 사용자 사진의 FXPAK Pro Mk.III Rev.D/2022-05-02,STM32F401RCT6,EP4CE15F17C8N,PSRAM IS66WVE4M16EBLL-70BLI 두 개를 기준으로 한다. 다시 제품명/속도를 묻지 않는다.

Questa는 기존 FLOAT wrapper와1seat를 재사용한다. uncounted Terminal Services 실패경로/새 유료 라이선스 요구를 반복하지 않는다. 한 번에 한 작업. Git에는 ROM/펌웨어/FPGA 바이너리/미디어/라이선스/개인경로를 넣지 않는다. PR은 한국어 제목과 작업 목표·작업 내용·작업 결과·작업 의미4절, 사용자가머지한다.
