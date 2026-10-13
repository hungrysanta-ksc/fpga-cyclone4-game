# NES165 영상 경계와 로컬 리셋 해제

## 목표와 변경

165 영상 경로 진척: 새 영상 mailbox·SPI 수신부의 리셋을 각 클록에서 해제하도록 수정했다. 내부 setup+0.158ns/hold+0.143ns, 14977LE/961LAB/35M9K와 조건부 IO 지연 검사를 통과했다. 영상 데이터·제어부의 음수 recovery/removal 경로는 1197개에서0개로 줄었다. 선택 boundary165/map02/reproduce02. MCU 통합·full-link·새 실기는 미완료이며 새SD는 없다.

PR108의 [내부 타이밍 통과 후보](nes-directstate165-contract.ko.md)를 기준으로 새 영상 전송 경계를 점검했다. 같은 배치 DB의 별도 복사본에서 IO·CDC·리셋 지연을 측정했고, 원본 소스/배치 368개 파일의 바이트가 유지됐음을 확인했다. 내부 타이밍을 더 줄이려는 미세 조정은 하지 않았다.

`nes_native_mailbox165.sv`와 `nes_live_joint.sv` 두 파일만 변경했다. 나머지59개 합성 입력, 클록/SDC/핀, 읽기·쓰기 타이밍, 패킷 형식과 식별자74는 그대로다. 실제164 설치 파일과 GBC, 카트리지 세이브 SRAM은 수정하지 않았다.

- mailbox의 기존 sr/dr 두 단계는 공통 비동기 리셋을 받는다. 데이터·request/ACK·capture/valid 상태는 각자 클록의 두 번째 단계로 리셋을 해제한다. src_ready/dst_valid의 원래 raw-reset 차단은 유지한다.
- native SPI도 host 클록의 `nes_domain_reset124`를 거친다. 이 release 체인은 sink의 동일한 release와 합성 중 공유될 수 있다. RTL 인스턴스 이름만으로 독립 회로라고 주장하지 않는다.
- 공통 리셋이 들어오면 즉시 격리하며, 해당 클록이 멈췄으면 로컬 리셋이 계속 유지된다. 양쪽 중 하나만 리셋하는 운용은 지원하지 않는다. 초기 재개 시점은 달라졌지만 정상 전송 중 패킷/CRC/ACK 의미와 샘플 시점은 바뀌지 않았다.

## 배치 기반 계산 결과와 검증

|항목|결과|
|---|---|
|최종 후보|boundary165/map02/reproduce02|
|전체 배치|14977LE / 961LAB / 35M9K|
|실제 내부4클록·3조건|setup +0.158ns / hold +0.143ns 통과|
|영상 mailbox/SPI 데이터·제어의 음수 recovery/removal|1197 → 0|
|동기화 첫 단계 팬아웃|배치에 남은 11개 모두 다음 단계 한 곳만 연결|
|record/prepare 묶음 데이터 지연|2.165ns / 6.682ns|
|70ns PSRAM 읽기 조건부 여유|+2.935ns|
|SNES 읽기 응답 계산|77.411ns < 기존 모델270ns|
|2.625MHz SPI 응답 계산|163.821ns < 반주기190.476ns|

최종 보고서는3조건 22131행이다. PSRAM은 주소17/CE·OE16메모리 클록,70ns 접근,PCB 왕복4ns 가정으로 계산한다. SNES는 meta→sync→동기 ROM/RAM/tag의 최대3host 클록과 출력 지연에6ns를 더한다. SPI는 가장 느린 NES 관측부의2FF+에지 처리3클록, 입력/출력 지연과4ns를 더한다. 데이터 mailbox는 요청 동기화와 추가 capture 에지 동안 held가 유지되고 ACK까지 덮어쓰지 않는 계약을 확인했다. 한 수신 클록 이내 데이터 도착에2ns 추가 여유를 요구한 보수적 계산도 통과했다.

이 수치는 실제 기판 전기 측정이 아닌 조건부 디지털 계산이다. 보고서용1000ns `set_max_delay`는 원래 미제약인 IO 경로의 지연을 보려는 도구이며, 그 slack을 통과 기준으로 사용하지 않는다. 원래 배치 SDC에는 추가하지 않았다. mixed-clock 표는 클록 쌍별·조건별 상위100개 경로 표본이며 전체CDC 목록이 아니다. 외부54입력/57출력 전체 승인·아날로그 MTBF·동시 클록 정지 시 핀 해제 시간은 완료 처리하지 않는다. reset 원시 음수 경로 24개는 native release 동기화 체인과 기존 sink_rom_fault 동기화 체인에 남아 있다. 이를 false path로 숨기지 않았다.

새 기능 시험은96비트 record와17비트 ACK 방향,6위상 조합에서450회 전달/72공통 리셋/12클록 정지를 통과했다. 요청·캡처·수신 보류 구간에서 취소 후 새 값만 도착하는지, backpressure 동안 데이터가 유지되는지, 정상 ACK 뒤 송신권이 돌아오는지, 리셋 우회 대조 회로가 실패하는지 확인했다. 취소 시험은 수신 ready를0으로 두므로 ACK 반환 전파의 모든 위치에 리셋을 주입한 시험은 아니다. 실제 native SPI는1717record/47block/12489wire bytes를2위상에서 재생해 이전 거래 기록과 바이트 단위로 일치했다. 메타안정성을 RTL 시뮬레이션으로 검증했다는 뜻은 아니다. 표의1197/0과 남은24는3조건의 보고서 행 수이며 서로 다른 물리 레지스터 수가 아니다.

첫 map01은 raw reset을 로컬 신호와 OR로 남겨 mailbox 데이터·제어에 음수 경로 333개가 남았다. 내부setup +0.024ns와 기능 시험은 통과했으나 미채택이다. map02에서 이 우회 경로만 제거했다. 전체 배치는 두 번이며 같은 소스 seed/refit 반복이 아니다. map01 실행 당시 생성기·시험 스크립트도 별도 보존했다.

최초 STA는 `get_port_info -direction`이 해당 버전에 없어 중단됐다. 이어 팬아웃 조회에 node 대신 collection을 넘겨야 하는 보고서 구성 오류도 수정했다. 실패 로그와 빈 표를 보존했으며 최종 보고서는 누락 시 실패한다. sink release 이름이 합성에서 합쳐져 선택적 inventory filter 경고가 남지만, recovery/removal은 실제 전체 sink/native 레지스터 집합으로 수집한다. 기존 state 이름을 찾는 보조 배치 목표 경고도 그대로 보존했다.

## 재현과 다음 작업

소스는 `tools/nes_boundary165.py --baseline <directstate165/map01> --out <새 ASCII 폴더>`로 생성한다. 생성 결과는61개 입력 SHA를 기록한다. 최종 `reproduce02`의 모든 입력이 바이트 단위로 일치한다. 기능 시험은 기존 FLOAT wrapper 안에서 `tools/test_nes_boundary165.py`를 실행하고, 배치 후 `tools/nes_boundary165_paths.tcl`과 `tools/check_nes_boundary165.py`로 수치와 원자료·소스 해시를 확인한다. 완료한 private record/audit/archive는 다시 실행하거나 수정하지 않는다.

boundary165/map02를 기준으로 실제164 MCU 게임 루프에 수신→PREPARED→COMMIT→영상 변환→패킷→SNES 표시 ACK→consumed를 연결한다. 식별자74/E6 version2/E5/D6/F6를 정확히 검사하고 기존 CF86·사운드·입력·STOP·메뉴 복귀를 유지한다. SPI를 잡지 않은 경계에서 시간/오류를 서비스하고 반복 횟수 대신 단조 경과 시간을 사용한다. RUN 중 SD 기록은 금지하고 안전한 STOP 뒤 기록한다. receiver18064B+video15888B와 기존 전역·스택을 실제 ARM full-link로 확인한다. 필요한 새 경계 시험 후 SMB3(J) 첫 레벨 실기로 진행하며 기존 ROM 쓰기·부팅·A/B·044 반복 및 무변경 refit를 추가하지 않는다. 기존 전기적 E1/E2·MTBF·클록 정지 한계는 조건부 위험으로 계속 명시한다.

이 작업은 실제 연속 화면용 FPGA 배선의 리셋 안정성을 갖추는 단계다. 별도 진단 기능을 늘리는 작업이 아니며, 게임 속도 개선·60fps·실기 플레이 성공을 입증한 단계도 아니다.
