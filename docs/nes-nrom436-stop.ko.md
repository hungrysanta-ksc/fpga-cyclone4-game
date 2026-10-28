# 실제 227 RUN의 plan 중간 취소

435 공동 실행에서 첫 E9 batch를 절반만 전송하고 SPI transaction을 닫은 뒤 RUN을 중지했다. 실제 direct RTL은 잘린 입력을 fault 처리하고 lease와 bus 출력을 해제했으며 227 RUN은 IO 오류로 정지하고 resident candidate를 취소했다. 동시 65816은 BEGIN 1개만 ACK했고 DMA·표시·최종 ACK·retire는 모두 0회였다. Questa 0 errors/0 warnings.

이것은 트랜잭션 RPC와 기록 geometry, 모델 ROM·loader·E0/E1 queue를 사용한 하나의 취소 지점이다. 실제 장치 전원·base menu 복구, 모든 타이밍의 STOP 또는 실기 60fps 증거는 아니다. 결과는 probes/nes-nrom436/stop01.
