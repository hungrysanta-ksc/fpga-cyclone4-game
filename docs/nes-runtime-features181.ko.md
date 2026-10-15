# NES 추가 기능과 화면 전송의 경계

2026-10-15 현재 소스 검토. GBC와 같은 사용자 기능을 NES에도 제공할 계획이지만, GBC 코드나 원본 NES 코어의 기능 유무만으로 현재 포팅본에서 동작한다고 판단하지 않는다. 아래 기능은 아직 구현·실기 승인되지 않았다.

| 기능 | 현재 확인 | 구현할 경계 |
|---|---|---|
| 프레임스킵 | 현재 bounded native 수집/전송이며 사용자 설정 경로 없음 | CPU/PPU/APU·매퍼 IRQ·패드 시간은 계속 진행하고 **표시 대상 수집/전송만** 생략. core PPU rendering 자체를 끄지 않음 |
| 강제 세이브/로드 | `nes_probe.sv`의 save/load 요청·외부 상태 메모리 응답 미연결. `cart_nrom.sv`의 MMC3 SaveStateBus 입력0, `has_savestate=0`, 출력 상태 미사용 | 기존 helper 존재만으로 구현 완료가 아님. 매퍼 포함 전체 상태 버스·RAM·SD 저장·복원 동기화 작업 필요 |
| 사운드 뮤트 | APU→필터→CDC→직렬 DAC 경로는 있으나 `nes_dac162`에 사용자 mute 입력 없음 | APU/DMC/IRQ·확장 음원은 실행 유지. 최종 mix 이후 출력 레벨만 차단하고 DAC 클록·CDC ACK 유지 |

근거는 `analysis/replyjoin181-verification.json`의 고정 보드 소스 `nes_probe.sv`, `cart_nrom.sv`, `nes_dac162.sv`와 현재 `src/nes/firmware/nes_native_runtime165.c`다. GBC 구현을 변경하거나 사용자 기능이 이미 이식되었다고 주장하지 않는다.

## 지금 설계에 반영할 사항

프레임스킵은 사용자가 선택할 부가 기능이다. 기본값은 끔이며 **실제 약60fps 목표를 충족하지 못한 상태를 감추는 수단으로 쓰지 않는다**. 모든 PPU fetch를 관측해야 하는 매퍼와 충돌하지 않도록 출력 생략을 코어 실행과 분리한다. 전송 시작 전 선택하지 않은 frame을 폐기하고, 이미 BEGIN한 frame은 계약에 맞게 끝내거나 ABORT/해제한다. 중간에 chunk를 버리고 ACK 완료로 처리하면 안 된다.

차분은 직전 NES frame이 아니라 **실제 대상 bank에 존재하는 기준 세대**에 대해 계산한다. 생략한 frame을 기준으로 삼지 않는다. source frame, 제출 frame, 실제 표시 frame 번호를 구분한다. 전송 압축은 무손실 처리로 유지하고, skip 정책은 별도 호출 경계로 둔다.

강제 세이브는 게임의 배터리 세이브와 다른 snapshot 파일이다. CPU/PPU/APU 내부 상태, IRQ/DMC/DMA 진행, CPU RAM/CIRAM/OAM/palette, CHR RAM/PRG RAM, 매퍼 latch/IRQ/ExRAM/확장 음원, 패드 shift 상태 등 **실제 이어 실행하는 데 필요한 상태**의 목록과 폭을 연결부별로 작성해야 한다. 기존 OAM 등 일부 state 경계가 남아 있어도 전체가 복구 가능한 것은 아니다. 원본 state helper의 기존 라이선스/채택 보류도 별도로 유지한다.

저장 시에는 game-state 시간을 일관된 지점에서 정지하고, 진행 중인 메모리 응답/CDC를 drain 또는 명시적으로 보존한 뒤 제한된 버퍼로 SD에 순차 저장한다. FPGA를 reset해서 멈추면 저장할 상태가 사라지므로 STOP/종료와 **비파괴 pause**를 분리한다. snapshot 파일에는 ROM 식별·mapper/submapper·core/state-format 버전·길이·검증값을 기록한다. 복원 전 전체 파일을 검증하고, 적용 중 실패하면 반쪽 상태로 실행하지 않는다. 검증 후 두 번째 읽기에서 I/O 실패할 가능성도 포함한다.

로드 후에는 게임의 원래 시점 상태를 복구하되, 호스트의 전송 serial/ACK를 과거 값으로 되돌리지 않는다. 미완료 packet·캐시·VRAM 기준·CDC 요청을 새 session으로 무효화하고 첫 화면은 완전 갱신한다. MCU의 현실 시간 deadline을 게임 저장 시점으로 되돌리지 않는다. 화면은 재생성 가능한 파생 상태이므로 기존 FPGA→MCU/MCU→SNES queue 전체를 snapshot에 넣는 것을 기본안으로 삼지 않는다. pause 중 DAC 출력을 조용히 하고 재개 시 pop 억제/필터 상태 처리를 별도로 정의한다.

뮤트는 최종 출력 경계에서 적용하고 좌우 sample을 같은 시점에 전환한다. 필터/직렬 출력 중간에 클록을 끄거나 APU 채널을 disable하면 게임 상태·IRQ 등에 영향을 줄 수 있으므로 그런 방식으로 구현하지 않는다. 향후 MMC5 확장 음원도 최종 mute 대상에 포함한다. 사용자의 음량·mute·skip 설정을 게임 snapshot이 임의로 덮어쓰지 않게 설정과 게임 상태를 분리한다.

## 자원과 순서

snapshot 전체를 ARM RAM에 복제하지 않고 정지 상태에서 bounded block 전송을 우선 검토한다. 단, 상태 read/write mux·비파괴 pause·CDC·state loader에는 FPGA 논리가 필요하므로 [매퍼 확장 자원 예산](nes-mapper-headroom181.ko.md)의 여유를 공유한다. 현재97LAB/8M9K/ARM4KiB 잠정 목표가 세 기능까지 충분하다고 보장하지 않는다. state 목록/주소폭/포트 합성 뒤 재산정한다. 기존 카트리지 세이브SRAM은 영상이나 snapshot 임시 저장소로 사용하지 않는다.

당장은 사용자 메뉴나 snapshot 엔진을 만들지 않는다. 화면 전송의 bank 기준 세대·취소·재시작·소유권을 위 기능과 모순 없이 구현한다. 영상 약60fps+음성 → 장기 플레이/오류·리셋 로그 → 입력 유지 품질을 먼저 확보하고, 그 뒤 사용자 frameskip/mute 및 전체 강제 세이브/로드를 구현·실기 검증한다. 기존 게임 저장 데이터와 정상 GBC 경로는 보존한다.
