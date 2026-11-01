# 543. map 발행 뒤 기존 큐 완료 확인

[542 비용 분리](nes-dma542-results.ko.md)에서 실제 DMA보다 VBlank 대기가 크며, raw 행 진행 절감만으로 밀집 구간이 줄지 않는 것을 확인했다. MMC540의 ARM·65816을 기준으로 첫 BG 공급 정책과 패킷 바이트를 보존하고, 최종 map 발행 뒤 palette/OAM/HDMA 패킷 앞에 기존 `nes_window184_drain`을 한 번 연결했다.

## 변경 범위

map 변경이 있는 화면에만 적용한다. 기존 accepted/retired counter·CRC·최종 identity 검사와 STOP·deadline 경로를 그대로 사용한다. 큐가 비었다는 응답은 DMA 완료를 뜻하지 않는다. 65816은 실제 선행 DMA 직전 새 head·STOP을 확인하고 기존 비활성 뱅크와 246행 규칙을 지킨다. 새 wire 명령·타이머 sleep·credit 임의 반환·새 RAM을 추가하지 않는다.

ARM은 [541 집계](../analysis/windows541-verification.json)를 기반으로 링크했다. Flash는 212,428→212,460B(+32), 여유 532B, BSS 18,592B로 동일하다. SNES는 MMC540의 538 client04를 그대로 사용한다. 542의 행 진행 후보를 함께 넣지 않아 효과를 분리한다. 아직 전달 이름을 바꾸거나 ZIP을 만들지 않았다.

## 검증 상태

[실제 ARM 경계 시험](../tools/check_nes_drain543.py)은 정상·16비트 counter wrap·변경 map 없음과 CRC/identity/status/counter 오류·STOP·poll 한도 9건을 통과했다. 이 단위 시험은 map 발행을 fixture로 설정하고 첫 palette 준비에서 중단한다. 정상 drain 이후에만 후속 코드에 도달하며 거부 시 최종 확정을 하지 않는 것을 검증한다. 실제 패킷과 표시의 증명은 별도의 연속 실행에서 수행한다.

[집계 경계 검사](../tools/check_nes_windows518.py)는 linked ARM에서 [5,40), [40,55), 초기/종료 제외, 미완료 제외, reset 및 기존 bin 보존을 통과했다. 집계 코드도 ARM 실행 위상에 영향을 줄 수 있으므로 기존 MMC540, 집계만 적용한 대조군, 같은 집계의 drain 후보를 분리한다. 후자의 두 구성은 각각 시작 3,000,000 / 3,178,684에서 905–957을 실행 중이다.

[준비기](../tools/prepare_nes_drain543.py)와 [분석기](../tools/analyze_nes_drain543.py)를 사용한다. 53 RGB·canonical payload·map/tile·ROM 읽기·전체 DMA가 같아야 하며, E0/SPI 증가·ARM 명령·IRQ·map 수락 뒤 비어 있는 구간·선행 DMA·SEAL 잔여 전송·최종 ACK를 기록한다. 실기 승격 조건은 두 위상에서 밀집 구간의 VBlank 수와 마지막 ACK가 모두 줄고 첫 BG ROM 구간 및 952·954 최종 대기 0회가 유지되는 것이다.
