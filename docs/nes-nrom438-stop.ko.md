# 실제 FPGA queue를 포함한 중간 STOP

437의 실제 227 RUN·E0/E1 queue·plan/tile/lease RTL·65816 공동 실행에서 첫 E9 전송을 절반만 보낸 뒤 RUN을 중지했다. 선행 BEGIN ACK가 완료된 뒤 의도적으로 잘린 SPI 전송을 넣었다. 실제 FPGA는 오류와 취소를 확인하고 lease·bus 출력을 해제했고, RUN은 IO 오류로 끝나 resident candidate를 취소했다. 65816은 1개 BEGIN만 ACK했으며 tile DMA·표시·최종 ACK·retire는 0회였다. Questa 0 errors/0 warnings.

이는 특정 취소 지점의 트랜잭션 RPC 시험이다. 실제 기계어 ARM, 모든 STOP 시점, ROM loader와 base menu의 물리 복구 및 60fps는 범위 밖이다. raw evidence probes/nes-nrom438/stop01.
