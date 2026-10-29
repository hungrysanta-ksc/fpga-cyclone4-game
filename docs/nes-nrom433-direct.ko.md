# 실제 227 plan SPI와 타일 소비

430의 실제 planner 출력 두 개를 byte-identical 227 plan service로 직렬화해 END 포함 E9 batch 하나를 만들었다. E8 응답은 직렬화 host 시험에서 모델이다. 그 동일 batch를 419 보드의 direct206·plan SPI/decoder·source/tile·bulk·lease RTL에 2.625MHz SPI로 전달했다. ROM은 428 자체 ROM pin 모델, 캡처 lease는 시험 fixture다.

FPGA는 두 연속 타일을 32바이트 descriptor 하나로 묶었다. 수동 SNES 버스가 descriptor·32바이트를 순차 읽고 token 1을 소비한 뒤, E8 END 상태, EA retire, lease 반환과 STOP 시 bus 비활성을 확인했다. 최종 표시 ACK는 시험기가 선행 조건을 모델로 제공했고 실제 65816은 이 실행에 연결하지 않았다. 같은 바이트를 431의 독립 65816 표시 시험과 432의 실제 tile RTL이 각각 확인했지만, 이 세 실행의 시간을 합쳐 라이브 경로나 60fps로 주장할 수 없다.

03은 시험기가 16바이트 descriptor 2개라고 잘못 가정해 실패했고, 05는 순간 end_sealed pulse를 놓쳐 실패했다. 06은 실제 ARM과 같은 E8 상태 확인으로 통과했다. 04는 긴 대기 진단을 의도적으로 중단했다. 결과는 probes/nes-nrom433/direct06 및 serializer03, 0 errors. 다음은 실제 ARM plan·SNES 65816 및 RTL 버스를 한 실행으로 결합하고 final ACK 후 EA, STOP·base 복구를 확인하는 것이다.
