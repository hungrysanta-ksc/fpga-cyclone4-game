# NROM449: 전체 보드 RTL과 loader 접합

사용자 지정 자체 NROM 시각 ROM을 실제 227 loader·FatFS host C, 227 전체 보드 RTL 및 448의 전체 크기 PSRAM 핀 모델에 연결했다. 의도적으로 256바이트에서 전송을 중단하고 모델에 기록된 바이트 전부를 원본 ROM과 비교했다. 쓰기 256회, RUN 비활성 및 fail-closed 통과; Questa 0 errors와 기존 초기화/포트 경고 84개다. 원시 로그는 `probes/nes-nrom449/prefix02`, 결과는 `analysis/nrom449-prefix.json`이다. 첫 실행 `prefix01`은 host용 설정 헤더 대신 제품 헤더를 선택해 컴파일에 실패했으며 보존했다.

이 시험은 전체 384KiB 적재·독립 readback·표시를 하나의 실행으로 증명하지 않는다. 411은 전체 적재·readback을 축소된 RTL 경계에서, 447은 시드한 적재 상태의 전체 보드 표시·STOP을 별도로 확인했다. 449 전체 보드의 256바이트 시험 시뮬레이션에 47초가 걸렸으므로 같은 속도라는 단순 가정에서 쓰기만 약 20시간이며 readback과 RUN 비용은 포함되지 않는다. 실제 총 시간은 측정되지 않았다. 사용자의 지시에 따라 중복 장시간 시뮬레이션을 실기 진입의 필수 조건으로 만들지 않고, 산출물·복구 및 timing/IO를 먼저 정리한다.

ARM 명령어·IRQ, 물리 PSRAM, FPGA 재구성·base/menu 복구, 연속 capture와 60fps는 여전히 미검증이다.
