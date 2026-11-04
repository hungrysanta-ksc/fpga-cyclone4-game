# 595 · 594 ARM과 D4 FPGA 입력 경계

594의 전체 ARM ELF(Flash 212,064 B, 여유 928 B)를 그대로 실행해 실제 D0–D4 SPI 핀에 연결했다. 595의 입력 회로는 Cyclone IV E에서 3,041 LE로 합성됐다. 같은 경계의 기준 1,668 LE에 실기 보드 여유 148 LE를 전부 허용해도 선별 상한을 1,225 LE 넘는다. 실기 기준은 MMC577이다. [검증 데이터](../analysis/region595-verification.json)

## 전송과 완료 소유권

ARM은 cold에서 모든 행을 받고, warm에서는 FPGA가 보낸 8 B 행 요약(CRC32와 양 끝 값)으로 행 재사용을 판단한다. FPGA는 D4 bitmap의 행을 원래 순서로 공급한다. ARM이 복원한 전체 map의 CRC16과 FPGA가 고정된 원본 lease에서 계산한 CRC16이 다르면, ARM이 전체 행 bitmap으로 REPAIR를 한 번 요청한다. FPGA는 MAP_ACCEPT 전까지 nonmap 발행을 막는다. [NES source RTL](../rtl/nes_region595.sv)

NES 쪽이 256 B 페이지를 채우고 봉인하면 host 쪽이 D1으로 읽는다. 올바른 길이의 D1과 같은 token의 D2가 모두 끝나야 NES가 페이지를 다시 쓸 수 있다. raw END 뒤 D3 PREPARE와 입력 COMMIT 페이지 수락까지 가야 collector lease를 놓는다. ARM의 표시 완료는 별도로 SEAL의 최종 ACK와 EA를 따른다. [host SPI RTL](../rtl/nes_spi595.sv)

## 공동 실행 결과

선택 실행은 test04와 map01이다. cold 905에서 시작해 warm 906으로 넘어가며 ARM이 복원한 map·행·OBJ·예외·raster·palette·raw와 필요한 tile tag 순서를 캡처에서 얻은 원본과 대조했다.

| 주입한 조건 | 관측 결과 |
|---|---|
| 첫 map 전송에서 한 값의 비트를 반전 | D1 wire CRC는 정상, ARM map CRC가 불일치했다. D4 HELLO → REPAIR → MAP_ACCEPT 순서로 29행 모두를 다시 읽고 원본과 일치했다. 6,820 B·244거래로 정상 cold보다 2,418 B·42거래 증가했다. |
| warm D1을 3 B에서 끊고 같은 token으로 D2 시도 | host fault, token 58과 lease 유지. 공통 STOP 및 ARM reset 뒤 이전 이력을 폐기하고 905 전체를 4,402 B에 cold 복구했다. |
| 올바른 최종 ACK | 표시 1회, EA를 마친 뒤 ARM 수신기 IDLE. |
| generation이 다른 최종 ACK, 응답 CRC는 정상 | 표시 0회, EA 발행 차단. |
| 정상 ACK 뒤 EA 처리 중 STOP | 표시 1회, 두 번째 표시 없이 수신기는 COMMITTED에 머물렀다. |

53개 연속 입력을 시도한 test03은 SPI 시뮬레이터 응답 시간 초과로 끝났다. 최종 기록에서 확인할 수 있는 연속 범위는 test04의 905–906이다. test01의 RTL 선언 오류와 test02의 Tcl 숫자 진법 오류를 수정한 뒤 실행했다. [실행 결과와 해시](../analysis/region595-verification.json)

## 비용

| Quartus Lite 25.1 지역 MAP · EP4CE15F17C8 | 기준 | 595 | 차이 |
|---|---:|---:|---:|
| LE | 1,668 | 3,041 | +1,373 |
| 조합 함수 | 1,311 | 2,308 | +997 |
| 전용 레지스터 | 794 | 1,278 | +484 |
| RAM bit | 2,048 | 2,048 | 0 |

NES source 자체가 조합 1,798개·레지스터 611개, SPI가 494개·355개를 사용한다. 135비트 명령 CDC만으로 레지스터 286개를 쓴다. RAM은 단일 dual-clock 페이지로 추론됐다. 합성기는 두 클록이 같은 주소를 동시에 읽고 쓸 때 값을 보장하지 않는다. 봉인·반납으로 유효한 host 읽기와 NES 쓰기를 분리했다. 지역 MAP 차이는 전체 보드의 배치 결과와 구분한다. [동일 경계 기준](../analysis/source589-verification.json)

| 입력 | 594 상대 장치 모델 | 595 SPI 핀 공동 실행 |
|---|---:|---:|
| cold 905 | 16패킷 · 58거래 · 3,125 B | 47패킷 · 202거래 · 4,402 B |
| warm 906 | 8패킷 · 37거래 · 1,468 B | 39패킷 · 172거래 · 2,692 B |

595는 nonmap을 최대 32항목 단위로 검사한 뒤 블록마다 한 패킷을 봉인한다. 이때 늘어난 D1/D2와 페이지 생산 중의 D0 조회가 실제 wire에 포함된다. 따라서 594 상대 장치 모델에서 계산한 cold 17.984 ms를 595의 시간으로 사용할 수 없다. 이번 판정에는 두 시작 위상의 첫 BG·마지막 ACK 시간, 전체 FIT/STA, 실기 프레임 수치가 없다.

## 재현과 다음 판정

594 ARM 트리와 581의 해시 고정 캡처가 필요하다. 실제 Cortex-M4 ELF는 Unicorn에서 실행하며, 입력은 Questa Starter FLOAT 한 좌석에서 두 RTL 클록과 2.625 MHz SPI로 시험한다. collector query는 캡처에서 순서에 맞게 응답한다. ROM 공급·출력 ACK 상대 장치는 기존 모델이다. 전체 65816·VBlank·실기 메뉴 복귀는 MMC577 측정과 구분한다. [공동 실행기](../tools/check_nes_region595.py) · [테스트벤치](../tools/nes_region595_tb.sv)

1. 기존 FLOAT 래퍼의 작업 스크립트에서 `check_nes_region595.py sim --arm <594 ARM01/src> --archive <581 evidence01.zip> --out <새 sim 디렉터리> --last 906`를 실행한다.
2. `check_nes_region595.py map --out <새 MAP 디렉터리>`로 같은 대상의 Quartus Lite 보고서를 만든다.
3. `analyze_nes_region595.py <sim> <MAP> <결과 JSON>`으로 ELF·RTL 해시, 검증 결과와 회로 비용을 결합한다.

다음 판정에서는 135비트 명령 복제분과 NES의 주소·CRC 선택 회로 중 실제로 지울 부분을 먼저 센다. 같은 한 페이지에 여러 nonmap 블록을 묶었을 때의 D1/D2·조회 횟수도 함께 예산화한다. CDC만 줄여서는 1,225 LE 차이를 설명할 수 없다. STOP·부분 전송·재전송에서 페이지와 표시 이력을 누가 보유하는지 명시하고 나서 회로 후보를 선택한다.
