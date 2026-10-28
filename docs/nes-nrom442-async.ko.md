# 느린 FPGA 응답을 위한 비동기 시험 중재기

441의 동기식 RPC는 전체 보드처럼 FPGA 응답이 느릴 때 Mesen 이벤트의 재진입 또는 대기 교착을 유발했다. 442는 packet 상태·payload 읽기와 12B ACK 전송을 비동기 상태로 처리하고 준비·전달 중 ready를 막는다. 제품 RTL이나 65816 명령을 변경하지 않는다.

441과 같은 실제 FPGA queue/direct RTL에서 ACK를 각 50,000 host clock 지연시켜 227 RUN·65816과 실행했다. async01은 표시와 retire에 도달했지만 종료 확인에 일시적 Lua assertion이 남아 합격으로 선택하지 않았다. 종료 조건을 수정하고 Lua 오류 부재를 검사한 async02는 packet 33개, 32B tile DMA, 표시 ACK와 EA retire 각 1회, 46,592 체크무늬 픽셀 및 Questa 0 errors/0 warnings를 통과했다. 기록 geometry와 ROM 모델이며 물리 시간이나 60fps 결과는 아니다. raw evidence probes/nes-nrom442/async01..02. 이 중재기를 실제 NES 코어가 실행되는 전체 보드 시험에 적용한다.
