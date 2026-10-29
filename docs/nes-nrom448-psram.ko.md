# NROM448: 전체 적재를 위한 PSRAM 시험 모델

447의 표시 시험 모델은 PRG 64KiB와 CHR 32KiB만 저장하므로 227 loader의 고정 PRG 256KiB·CHR 128KiB 쓰기 및 독립 readback과 한 실행으로 연결할 수 없었다. 제품 RTL은 변경하지 않고 시험 모델을 해당 전체 주소 범위로 확장했다. loader의 물리 주소 배치에 따라 PRG 0x000000–0x03ffff와 CHR 0x200000–0x21ffff를 서로 독립 저장한다.

단일 Questa Starter seat에서 각 범위 시작·기존 모델 경계 너머·끝과 양쪽 바이트 레인에 서로 다른 값을 기록하고 다시 읽었다. 10회 쓰기, 0 errors/0 warnings로 통과했다. 첫 실행은 시험 bench의 초기 reset이 비활성이어서 시각 0의 초기 신호 이벤트를 실제 쓰기로 잘못 취급해 실패했고, reset을 먼저 활성화한 재시험이 통과했다. 원본 로그는 probes/nes-nrom448/model01 및 model02에 보존한다.

이 결과는 시험 메모리 모델의 경계 확인이다. 전체 loader 또는 NES core 연결, 물리 PSRAM, 60fps와 실기 검증을 뜻하지 않는다. 다음 통합에서는 시드하지 않고 실제 loader가 이 모델을 채우고 독립 readback을 완료한 상태로 447 START·표시·STOP에 넘겨야 한다.
