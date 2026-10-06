# NES-P2-MMC3-INTEGRATED-009 — CPU/PPU/MMC3 통합 진단

2026-10-05. 자체 Mapper4 ROM을 실제 Questa CPU/PPU/MMC3에서 실행하고 동일 ROM의 Mesen 기록과 비교했다. **화면·주소·프레임 처리·IRQ service의 기능 검증을 통과했다. 정확한 IRQ 해제 위상 비교는 미해결이다.**

| 관측 | 결과 |
|---|---|
| 실제 RTL 실행 | 140.02ms, 최종 Errors 0 / Warnings 42 |
| 완전한 화면 | 4 × 256×240 = 245,760화소, Mesen/독립 oracle 차이 0 |
| 배경 fetch | 65,552건 검사, 화소 사용 61,440건 주소·값 차이 0 |
| PRG/CHR banking | CPU R6 marker 0/1 및 고정 R7=3 확인, CHR physical group 0/8192 반복 전환 |
| NMI/CPU | 연속 frame counter 진행, CPU 주기/버스 미정값/PRG 검사 오류 0 |
| 실제 PPU A12 | 캡처 4프레임 상승 7,712건의 주기 검사 |
| IRQ | 전체 실행 중 CPU service 6회; 캡처 각 프레임 scanline62/cycle261 assert, RAM increment 및 E000 ack 확인 |
| 반복 | 최종 RTL 두 실행 frame/fetch/control/edge bytes 동일, Mesen 두 실행 frame/trace 동일 |
| 실패 검출 | pixel/bank/fetch 5종 + IRQ/A12/handler 3종 거부 |

최종 ROM SHA256: `8b380949760320c993fd35a2a48af29a6afe2516f353d048f65f49fa1dd38ba9`. 색 변환은 기존 고정 Mesen 팔레트를 사용했다. 화소 hash는 group0 `c9b1d2f3430bcaf491c7c05fd6d46c599a58abfbb713bd652f8ef7ac30bf6800`, group8192 `03e5301a3f3a486f699e4e23c4ad305b2ec44a3a65165895d60808d338562f09`다.

초기 polling ROM은 Mesen frame8에서 counter가 중복돼 연속 frame 작업을 놓쳤다. 정확한 원인을 확정하지 않았으며, 이 초기 실행을 최종 성공으로 세지 않는다. 원본 builder/ROM/양쪽 로그를 보존한 뒤 NMI flag 방식으로 고쳤다. 수정 ROM은 양쪽에서 매 프레임 처리되고 반복 실행도 동일했다. run-02의 추가 wrapper 상수 폭 경고 2개를 정리한 run-03은 기존 전체 코어 경고 42개만 남았다. 기존 mapper/CPU/PPU 로직을 새로 고친 것은 아니다.

공통 ROM counter3..5에서 E000 ack 관측은 RTL dot328/330/331, Mesen dot332/334/335로 4 PPU dot 차이다. IRQ의 발생 줄과 handler 동작은 맞지만 **관측 위상과 실제 CPU interrupt latency를 아직 분리하지 않았다.** 다음 작업에서 기준점을 맞추고 원인을 확인해야 한다. 이 차이를 허용 오차로 숨기거나 IRQ cycle 정확성 완료로 해석하지 않는다.

[검증 JSON](mmc3-integrated-verification.json), [해시 목록](mmc3-integrated-artifacts.json), [계약·재현](../docs/nes-mmc3-integrated-contract.md).
원시 증거는 ignored `analysis/local-mmc3-integrated-009/`의 rtl-01..03, mesen-01..03, rom-01..02, baseline/ 및 baseline-status/에 있다. 임시 license server는 종료했고 프로세스/listener는 0이었다.

이 결과는 BG/zero-scroll/사전 상주 CHR/ideal memory/표준 MMC3의 자체 진단이다. 일반 게임, 여러 MMC3 revision, sprite 복합 동작, 외부 메모리 stall/cache miss, NES→SNES 통합, 전체 P1/P2·fit/STA·SMB3·실기는 미완료다. 240→239줄 crop 승인은 없다. 개별 파일 license hold와 upstream 원본, GBC C44/0.9.0을 유지했다. GBC 152개 소스/Quartus 입력/2048 부트 도달 바이트 검증도 통과했다.
