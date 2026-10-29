# 같은 geometry의 연속 두 번 표시

437의 실제 227 RUN·FPGA E0/E1 queue·plan/tile/lease RTL·65816 공동 실행에서 동일한 429 geometry를 generation 4와 5로 순차 재생했다. 첫 화면의 최종 ACK와 lease retire 뒤 두 번째 capture lease fixture를 시작한다. FPGA queue, resident bank, token 상태는 리셋하지 않았다.

RUN 52 step·SPI 377회, packet ACK 66회, 표시 ACK와 EA retire 각 2회, input token 0→50을 확인했다. 65816이 VRAM 8,256B를 기록했고 두 화면 모두 46,592개 체크무늬 픽셀이 동일하다. Questa 0 errors/0 warnings. 이는 두 개의 기록 재생이며 다음 NES capture가 이전 표시와 겹치는 일정이나 누락 없는 60fps가 아니다. ROM·loader·capture 및 실행기 간 시간은 모델이다. raw evidence probes/nes-nrom439/two01.
