# 65816 시험 중재기의 느린 ACK 재진입

440 전체 보드 공동 시험의 첫 두 실행은 같은 패킷을 두 번 ACK하거나 오류 ACK가 추가되어 실패했다. 65816이 사용한 packet 바이트는 통과한 437 기록과 같았다. 파일 RPC와 Mesen 이벤트의 느린 ACK 중에 시험기 상태가 재진입할 수 있으므로, packet 준비와 ACK publish 중에는 65816에 ready를 보이지 않고, ACK 전달 중 frame event가 재전달하지 않도록 임시 소유권을 두었다. 이는 테스트 연결기 수정이며 제품 RTL·65816 코드는 변경하지 않았다.

441은 437의 실제 FPGA queue/direct RTL과 65816 공동 시험에서 각 ACK 전 50,000 host clock 지연을 추가한다. ack01은 타일 준비 전에 CPU가 접근했고 ack02는 blocking wait의 재진입으로 교착되어 의도적으로 중단했다. 비차단 중재를 사용한 ack03은 패킷 33개, 최종 표시 ACK·EA retire, 체크무늬 46,592픽셀과 0 errors/0 warnings로 통과했다. raw evidence probes/nes-nrom441/ack01..03. 440 전체 보드 재시험 결과는 별도이며 이 단위 시험으로 실제 보드나 60fps를 입증하지 않는다.
