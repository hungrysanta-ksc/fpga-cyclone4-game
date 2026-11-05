# 598 · MMC577 collector 확정 시점과 source 교체 경계

**map은 기존 collector 쓰기에서 요약할 수 있다. 그러나 이 방식으로 597 source를 축소해도 보드 여유에 들어오지 않는다.** 선택 보드의 compact RTL에 요약 생성을 연결하고, 같은 작업량에서 기존 source와 교체 source를 collector까지 포함해 다시 합성했다. 실기 기준은 MMC577이다. [측정값·프레임별 비용표](../analysis/boundary598-verification.json)

## 어느 쓰기가 최종 값인가

| MMC577 경로 | 값이 확정되는 시점 | 포트와 소유권에 미치는 영향 |
|---|---|---|
| map group | raw 대체가 없는 변경 행의 row_commit에서 그룹 번호를 배정한다. 이어지는 copy_busy 33클록의 각 쓰기에서 15비트 셀이 확정된다. | 기존 쓰기 데이터를 받아 CRC32·양 끝 값·누적 CRC16을 계산할 수 있다. 전체 행 재전송에는 여전히 map RAM과 읽기 포트가 필요하다. |
| BG row · raster row | 256픽셀 수락 뒤 row_commit에서 정상 행이나 raw 슬롯 참조를 선택한다. | 두 row RAM과 map 복사가 독립적으로 쓰인다. 같은 1쓰기 포트에 넣으려면 동시 요청을 처리할 버퍼와 최악 지연이 필요하다. |
| OBJ · exception | 같은 rank와 key를 가진 OBJ는 뒤 행에서 기존 슬롯의 mask를 덮어쓴다. 예외는 먼저 append하고 raw 판정 시 exception_count를 exception_base로 되돌린다. | 첫 쓰기를 선형 CRC나 SPI 페이지에 그대로 더하면 최종 배열과 달라질 수 있다. 프레임의 유효한 종료 시점에 최종 슬롯·개수를 읽는다. |
| palette · raw | 새 palette는 copy_busy 동안 color RAM에 나눠 쓴다. raw 픽셀 수락과 그 슬롯을 실제 표시할지의 판정도 다른 시점이다. | palette 복사 종료, patch 세대 및 슬롯 일치, fetch·compact·raster·patch 네 구성원의 유효성까지 frame201에서 확인한다. 오류가 난 캡처의 요약 공개를 금지한다. |

보드 원본의 export203은 유효한 lease의 query 응답으로 태그·index·generation·반복 값을 조립한다. native_records의 96비트 mailbox가 이를 host로 넘긴 뒤 spi165가 host 클록에서 256 B 페이지에 기록한다. D1을 끝까지 읽고 D2 token이 일치해야 페이지가 반환된다. D3 PREPARE 뒤 export203이 COMMIT을 mailbox에 넘기는 시점에는 collector를 해제할 수 있다. 표시 완료는 별도의 lease와 최종 ACK/EA에 속한다. 입력 COMMIT과 표시 이력을 합치면 안 된다.

기존 보드 FIT에서 export203 731 LE, records 220 LE, spi165 482 LE의 합은 1,433 LE다. 이 중 SPI의 선택·응답·D1/D2 보호 및 PREPARE mailbox 역할은 교체 뒤에도 필요하다. 세 블록 전체를 순삭제분으로 세지 않았다. [원래 경계의 FIT 예산](nes-source588-results.ko.md)

## collector에서 생산한 8 B 요약

원래 maps 쓰기의 `copy_column`, `previous_value`를 같은 NES 클록으로 받았다. 추가 query나 PPU stall 없이 그룹 마지막 셀에서 CRC32·첫 셀·마지막 셀을 저장한다. 독립 CRC16은 확정된 셀을 canonical little-endian 순서로 누적한다. 시작/STOP에서 누적값을 초기화하고 SRAM은 유효한 lease와 그룹 범위로 가린다. 전체 행 재요청 때는 원래 map을 다시 읽는다. 수신자가 보내는 MAP_ACCEPT 전까지 nonmap을 막는다. [요약 RTL](../rtl/nes_map_seal598.sv)

고정 53입력에서 BG 셀·fine·raw 대체 판정으로 실제 compact collector를 구동했다. **1,537그룹**의 요약과 각 프레임 전체 map CRC가 독립 계산과 일치했다. 복사 도중 release 후 재시작, 유효 seal 이전의 조회, 범위 밖 조회, release 및 source fault 뒤 차단을 확인했다. 실제 PPU의 전체 fetch 시간과 OBJ 이벤트는 이 재구성에 포함되지 않았다. [collector 시험](../tools/check_nes_map598.py)

같은 compact collector, 594 전체 ARM, 135비트 명령 mailbox, SPI 핀에서 재순회 사용 여부만 바꾼 대조군을 실행했다. 905·906의 각 map은 957단어이며, 598은 phase 0의 957회 map query를 제거했다. cold는 요청 행 957단어를, warm 906은 요청 행 165단어를 원래 collector RAM에서 읽는다. warm은 29그룹의 요약을 사용한다. 53입력에 적용하면 기존 전체 scan 50,721단어가 교체 범위다. 53입력은 collector 단독 시험이며 두 세대만 ARM·SPI 공동 시험을 실행했다.

| 입력 | 재순회 대조군 | collector 요약 | 차이 |
|---|---:|---:|---:|
| cold 905 | 21패킷 · 105거래 · 3,704 B | 21패킷 · 94거래 · 3,616 B | D0 11회 · 88 B |
| warm 906 | 13패킷 · 75거래 · 1,994 B | 13패킷 · 65거래 · 1,914 B | D0 10회 · 80 B |

공유 SPI 2.625 MHz에서 각각 wire 점유 0.268/0.244 ms 절감이다. 원본 map RAM에서 읽은 값 하나를 변조하자 전송 CRC는 정상이어도 ARM이 29행 전부를 재요청했다(136거래·6,034 B). warm D1 부분 전송 뒤 D2는 token 32를 유지했고 STOP/reset 뒤 정상 cold와 동일한 3,616 B에 복구됐다. 정상 최종 ACK는 표시 1회와 EA 후 IDLE, 잘못된 generation은 표시·EA 0회, EA 중 STOP은 표시 1회·COMMITTED였다. map 응답과 요약은 실제 compact RTL에서, nonmap 값은 캡처 fixture에서 공급했다. ROM·표시 상대 장치는 모델이다.

## Quartus Lite · 같은 경계의 비교

| EP4CE15F17C8 지역 MAP | LE | 조합 | FF | RAM bit |
|---|---:|---:|---:|---:|
| compact collector 단독 | 2,151 | 1,183 | 1,078 | 28,000 |
| 같은 collector + 쓰기 요약 | 2,382 | 1,414 | 1,142 | 29,984 |
| collector + MMC577의 기존 source/records/SPI | 3,855 | 2,530 | 1,873 | 30,048 |
| 같은 경계 + 597 묶음·사후 재순회 | 4,739 | 3,437 | 1,930 | 30,048 |
| 같은 경계 + 598 쓰기 요약·재순회 제거 | **4,910** | **3,638** | **1,932** | **32,032** |

collector 안에서 15비트 셀 하나를 매 클록 CRC에 반영하는 비용이 있다. 32×64의 논리적 요약 저장 중 두 셀의 상위 고정 0 비트를 제외한 1,984 bit가 보고됐다. 597 대비 결합 경계는 171 LE 커졌다. 이전 source-only 상한 1,816 LE를 여기에 적용하지 않는다. 새 기준 3,855 LE에 기존 전체 보드 여유 148 LE를 모두 더한 선별 상한은 **4,003 LE**, 초과분은 **907 LE**다. 실제 적용안의 순절감과 추가 M9K 블록 수는 전체 FIT로 측정되지 않았다.

합성의 두 교체 경계는 597의 진단용 명령 CDC를 공통으로 사용했다. 안전한 CDC 제약과 전체 STA의 비용은 남는다. 기능 공동 시험은 원래 135비트 mailbox를 사용했다. 새 ARM 링크 비용은 0 B 증감(동일 594 ELF)이며 기존 Flash 여유는 928 B다. 실기의 MMC577 원본 여유는 84 B다. [합성 경계](../tools/map_nes_boundary598.py) · [ARM/핀 접속](../tools/check_nes_input598.py)

## 입력과 출력·최종 ACK를 함께 본 60 Hz 예산

580의 두 위상에서 951–955를 같은 generation끼리 연결했다. 아래 시간은 기존 ARM·SPI·IRQ·ROM/65816 일정의 평균이다. 598 재배치 후의 전체 시간을 추정해 끼워 넣지 않았다.

| 중복 없는 기존 일정 · ms | 위상 1 | 위상 2 |
|---|---:|---:|
| 이전 ACK → 입력 시작 | 0.552 | 0.621 |
| 입력 시작 → planner 진입 | 23.174 | 23.132 |
| planner → 출력 진입 | 17.686 | 17.686 |
| 출력 진입 → SEAL 수락 | 27.589 | 27.326 |
| SEAL 수락 → 최종 ACK | 14.155 | 14.356 |
| ACK 간격 | 83.157 | 83.121 |
| 입력 항만 제외한 잔여 | **59.983** | **59.989** |

53개 캡처의 행·nonmap을 복원하고 596의 6페이지 묶음, 기존 D4 횟수 및 D1/D2·반환 확인·D3의 필수 거래를 더했다. 여기에 같은 generation의 580 E1/E9/EA wire를 합쳤다. 추가 ready 조회·출력 조회·ROM·driver gap을 제외한 조건부 바이트다. 비교용 582 출력은 기존 map 패킷을 8 B 단위 변경 패킷과 manifest로 교체하고, 재사용을 선언할 때의 바이트까지 포함한다.

| 입력+출력 wire B · 두 위상 공통 | 밀집 평균 | 952 | 954 |
|---|---:|---:|---:|
| 묶음 입력의 필수 거래 + 기존 출력 | 5,293.6 | 5,812 | 6,230 |
| 기존 입력의 관측 D0–D3 전부 + 582 참조 출력 | 5,127.2 | 5,173 | 5,290 |
| 묶음 입력의 필수 거래 + 582 참조 출력 | 3,203.8 | 3,405 | 4,008 |

기존 출력이면 952·954는 **wire만으로도** 2.625 MHz에서 한 프레임의 5,468.75 B를 넘는다. 밀집 평균의 기존 출력 E1/E9/EA는 3,466.2 B, 582 참조 출력은 1,376.4 B다. 이 2,089.8 B 차이에는 비용이 따른다. 582의 이력 재사용 조건에서 독립 검사가 부담할 상속 바이트는 평균 2,435.8 B다. 954는 결합 참조조차 잠정 12 ms wire 예산(3,937.5 B)보다 70.5 B 크다. 두 참조 형식을 한 제품에 안전하게 연결했거나 그 시간에 표시를 마쳤다는 결과는 아니다. [582 참조 조건](nes-abi582-results.ko.md)

**다음 단일 판정은 출력 952·954다.** MMC577 입력을 대조군으로 고정하고, 582의 대상 뱅크 8 B 변경 묶음과 palette/OAM/HDMA 재사용 선언을 같은 ARM 발행·실제 65816 검사/DMA 코드에 놓는다. 현재 출력과 변경 출력의 wire·호출 수, 상속 검사 2,551/2,359 B, ARM Flash·스택, 두 위상의 SEAL·최종 ACK를 비교한다. raw/부분 DMA 또는 STOP 뒤 이력을 폐기하고, 새 이력은 올바른 bank·generation의 최종 ACK에만 공개한다. 598 요약기와 597 진단 CDC는 제품 후보에서 제외한다. 입력과 출력이 모두 개선되는지 확인하기 전 전체 FIT·실기 전달 단계로 넘어가지 않는다.

재현은 먼저 `check_nes_map598.py map|sim`으로 compact를 검증하고 `map_nes_boundary598.py`로 동일 포트의 세 구성을 합성한다. `check_nes_input598.py`와 `--rescan` 대조군을 단일 FLOAT 래퍼에서 차례로 실행한 뒤 `analyze_nes_boundary598.py`로 580·581·582의 동일 generation, 소스 및 ELF 해시를 대조한다. 로컬 캡처·보드 소스와 594 ARM 트리가 필요하다. 최초 공동 시험의 SystemVerilog 선언 순서를 수정하고 최종 캐시 경계만 재합성했다. [결합 분석기](../tools/analyze_nes_boundary598.py)
