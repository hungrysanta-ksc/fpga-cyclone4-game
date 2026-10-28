# 실행 중 NES 코어의 두 프레임 표시

443 공동 실행을 확장해 하나의 227 RUN session 안에서 실제 NES core/board RTL이 생성한 generation 4와 5를 순차 수신했다. 두 프레임은 각각 D1 블록 25개·5,764B이며 모든 블록 CRC16을 독립 재검사했다. 첫 geometry SHA는 `eaae16835aece4b0785a0a759e8522bddc6f3f62db86ed11cc89dc874f2b0136`, 둘째는 `82182c63a35f3e7ce3c72784eee6af542fc454a94803c08a0ec81ce059ad8198`이다. 입력 token은 0→50, FPGA queue packet ACK는 66회다.

실제 FPGA queue/tile RTL과 65816 에뮬레이터가 양쪽 프레임을 표시하고 최종 ACK·EA lease retire를 각각 2회 완료했다. VRAM 총 8,256B, 두 화면의 46,592 체크무늬 픽셀은 모두 일치했다. 두 번째 표시 뒤 board SPI STOP·core reset·bus 해제도 통과했다. Questa 0 errors 및 기존 84 warnings. raw evidence probes/nes-nrom445/two01, 독립 결과 analysis/nrom445-two.json.

두 generation이 이어진 것은 확인했지만 실제 NES 프레임 전부를 캡처했는지, 두 캡처가 실제 표시와 겹치는지 또는 60fps인지 증명하지 않는다. PSRAM/loader verified는 시드, ARM은 host C, 실행기 간 시간은 RPC 모델이다. 실제 ARM/IRQ, mapper, 실기 및 base 재설정·menu 복구도 미검증이다.
