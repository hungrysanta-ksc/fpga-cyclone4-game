# NES 다음 작업 인계 — 057 이후

현재 후보는 **NES-ROM-GEOMETRY-057**. [결과](../../analysis/ROM-GEOMETRY-RESULT.ko.md)와 [재현 계약](../../docs/nes-rom-geometry-contract.md)을 먼저 읽는다. 실기 기준044, MCU 적재 전용056은 유지하며 새 SD 이미지는 없다.

## 완료한 경계

- 057은 로더가 승인한 기존 chr32 레지스터 하나를 길이와 코어 CHR mask에 연결한다. 독립 ext_chr_32k 입력은 제거했다. SPI의 수신 인자 latch는 거부된 BEGIN에서도 바뀔 수 있어 직접 사용하면 안 된다. 잘못 연결한 대조가 정확히 실패한다.
- 단위360484형상/로더 검사,180224바이트. 실제 코어2종8프레임491520픽셀과16064패킷 바이트/전체 이벤트가055와 시각까지 동일하다. BEGIN 뒤 기존 fixture 인자를 반대로 바꾼 조건이다.
- 새 공동 fit13976LE/954LAB/5158레지스터/26M9K. **9LAB 여유**다. 레지스터 추가 없이도 패킹 차이로054보다6LAB 늘었다. 옛15LAB을 현재 값으로 사용하지 않는다. 물리 보드 fit/STA가 아니다.
- 056은 SD/GPIO/USB 보호와 적재·복구 바인딩을 host/RTL/ARM link로 검증했으며 실제 STM32/SD 실행은 아니다. END→STOP→기본 FPGA 복구로 ROM을 폐기한다. START나 새 메뉴 hook은 없다.

## 다음 구현 순서

1. [물리 readback 후속 설계](../../docs/nes-rom-readback-plan.md)에 따라 기존052 reader를 실행 전 CHECK 소유권에서 MCU가 사용하는 최소 경로를 구현/공동 fit한다. FPGA CRC 회로·두 번째 reader를 먼저 추가하지 않는다. read_reset이 현재 !RUN 및 core reset에 묶여 있으므로 요청 명령만 추가하면 읽을 수 없다. MCU는 실제 응답의 주소·데이터와 전체 길이를 비교해야 한다.
2. readback 성공 후 reader의 양쪽 도메인과 outstanding 요청을 안전하게 비우고 기존049 scrub/RUN으로 연결한다. 단일 byte 손상·주소/chip/lane 오류·응답 유실·STOP/common reset/PLL loss·stale completion 거부와 실제 MCU GPIO 파형을 먼저 시험한다. CRC8/입력CRC32/loaded/057형상 연결을 물리 readback 성공으로 표시하지 않는다.
3. 남은9LAB 안에서 보드 클록/소비자·프레임 마감/복구를 공동 측정한다. 초과 시 동등성 회귀를 동반한 최적화를 먼저 한다. SNES_SYSCLK/PIN_A9는 아직 주파수·지역·라우팅 미확인 후보다.
4. 보드 경계와 전체 핀/PLL fit·CDC/외부 IO/STA가 갖춰진 후 별도 RUN/메뉴 진입점·진행 표시·종료 결과와 복구 가능한 실기 쌍을 준비한다.056 true 반환은 메뉴 재로딩 안전성이고 적재/실행 성공이 아니다. 복구 실패에서 RESET과 USB 보호를 풀지 않는다.

044의 실제 순환/RESET/GBC 보고와041 실패,043/044 SDF 실패,050/051 지연 대조,055/056 시험 기대 오류를 보존한다. 원본053/054 및056 소스·과거 원시 근거는 수정하지 않는다.057은 새 폴더에 생성한 배선 변형이며 MCU 프로토콜은054 그대로다. [과거 주의사항](history/AGENTS-053.md), [재현 범위](REPRODUCING.ko.md), [주요 진전 관리](../../docs/development/MILESTONE-WORKFLOW.ko.md)를 따른다.
