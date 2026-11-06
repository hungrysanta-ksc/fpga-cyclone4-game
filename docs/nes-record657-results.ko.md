# NES 657 · source record의 생성부터 SPI 수락까지

**다음 비교 기준은 657 port다.** 656 ingress보다 전체 보드에서 83 LE·3 LAB를 회수했다. EP4CE15F17C8에 배치하려면 **17 LE·14 LAB**를 더 줄여야 한다. 실기 기준은 MMC643이다.

## 어느 제어를 삭제했나

905–957에서 NES가 발행하고 host SPI가 수락한 96비트 record 53,603개를 대조했다. map 셀이 50,721개(94.62%), 헤더가 53개, 그 밖의 일반·제어 record가 2,829개였다. 656과 657 lanes·port는 각 발행·수락 edge의 96비트 값과 시각이 모두 같았다. 이어진 958의 STOP에서는 82번째 발행이 CDC 안에서 취소됐고 host 수락은 81개였다.

| 경계 | 656 ingress | 657 port에 남긴 소유자와 삭제한 제어 |
|---|---|---|
| NES record 생성 | 8비트 raster·palette와 6비트 patch를 별도로 이동, 헤더와 두 누계를 저장 | 바이트 이동 경로 한 개와 오래된 sextet 2개(12비트)를 사용한다. 헤더는 수락한 lease 정보에서 조립한다. 수락된 query 값마다 12비트 누계를 한 번 올린다. 최대 3,616개이며 재조회·실패는 제외한다. END의 raw 길이는 끝까지 처리한 patch의 개수×256이다. 별도 raw 누계와 16비트 묶음 가산을 삭제했다. |
| NES→host CDC | 96비트 송신 보관, 두 클록의 REQ/ACK 동기화, 추가 host edge에서 96비트 캡처 | 두 96비트 보관 경계와 prepared 역방향 17비트 mailbox를 유지했다. 취소 중에도 이미 수락한 word를 덮어쓰지 않는다. |
| SPI 수락·D0/D2 | 상태 응답 48비트 shift, 유효 D2의 SS 해제에서만 token 증가 | command 수신 시 바뀔 수 있는 길이 9비트와 상태 3비트만 고정한다. 같은 CS 안에서 token은 불변이므로 직접 읽는다. 부분 읽기·token·CRC·최종 D2 수락 검사는 유지한다. |
| RAM | 호스트 read 주소와 cell·serializer·codec write 주소가 별도 | 한 클록에서 cell 저장, 출력, codec 쓰기 또는 읽기 중 하나가 주소를 소유한다. 쓰는 동안 read 출력을 유지한다. Quartus 추론은 512×8 simple dual-port M9K 1개, 단일 클록이다. NES용 둘째 물리 포트를 확보했다는 뜻은 아니다. |

## 전체 보드 FIT

Quartus Lite 25.1, 같은 디바이스·보드 설정·654 combined ARM·65816을 사용했다. LE 한도 15,408, LAB 한도 963, M9K 56/56이다. 표의 LE와 LAB는 실패한 전체 Fitter 보고서에서 읽었다.

| 후보 | 검증한 교체 범위 | 전체 LE | 전체 LAB | 부족 LE / LAB |
|---|---|---:|---:|---:|
| 656 ingress | 기준 | 15,508 | 980 | 100 / 17 |
| field | generation을 헤더·COMMIT·ABORT로 한정한 80비트 word와 SPI 복원 | 15,546 | 984 | 138 / 21 |
| staged | 80비트 word, 헤더·누계를 NES query 저장소에서 발행 | 15,607 | 986 | 199 / 23 |
| split | 42비트 CDC, map·ABORT는 1회, 일반 record는 prefix·suffix 2회 | 15,868 | 1,000 | 460 / 37 |
| direct | 80비트 중 payload 64비트를 NES exporter FF에서 직접 캡처, 대기 중 취소를 보존 | 15,572 | 986 | 164 / 23 |
| count | 96비트, source 계수·헤더 조립과 SPI 상태 수락을 교체 | 15,518 | 980 | 110 / 17 |
| lanes | count에 raster·palette·patch 공통 바이트 저장을 연결 | 15,448 | 978 | 40 / 15 |
| **port** | lanes와 RAM 주소·읽기·쓰기 소유권을 통합 | **15,425** | **977** | **17 / 14** |

선택한 port에서 exporter의 지역 조합 논리는 702→587, SPI는 617→602였다. 전체 보드 조합 논리는 14,737→14,614, FF는 8,607→8,547이었다. 직접 캡처는 전체 FF를 8,435까지 줄였지만, 취소·보관과 조립 제어가 추가되어 더 많은 LAB를 요구했다. 모든 후보에서 FIT가 배치 전에 중단돼 STA·SOF·신규 실기 전달본은 없다.

## 같은 시작 시각의 표시와 복구

각 후보에서 실제 exporter·mailbox·SPI·RAM의 901개 D1 payload와 wire CRC를 독립적으로 검사했다. 총 payload는 79,392 B, 별도 wire CRC는 블록당 2 B다. 준비 클록·codec 클록·payload 전체가 동일한 field·staged·count·lanes·port는 같은 두 위상 재생을 공유했다. split·direct는 준비 시각이 달라 각각 두 위상을 별도 실행했다. ARM은 212,508 B로 Flash 여유 484 B다. 연결 일정은 실제 ARM 명령과 65816, 공유 SPI·IRQ·두 슬롯·ROM 허용 달력을 사용하며 실기 FPS와 구분한다.

| 측정 | 위상 1 | 위상 2 |
|---|---:|---:|
| 951–955 표시 간격 (VBlank) | 3 / 4 / 3 / 3 / 3 | 3 / 4 / 3 / 3 / 3 |
| 954 SEAL 마감 여유 (953 표시 기준, 648과 비교) | 1.658 ms | 1.592 ms |
| 밀집 평균 표시 간격 | 53.281 ms | 53.249 ms |
| 951 공개선 / 957 최종 추가 대기 | 239선 / 0회 | 239선 / 0회 |
| 957 마지막 ACK master clock | 68,589,578 | 68,589,458 |
| MMC643 대비 957 마지막 ACK 단축 | 116.616 ms | 133.081 ms |

일곱 후보가 두 위상의 표에 같은 결과를 냈다. 955 첫 7블록의 준비 합은 656과 port가 211.762 µs, split이 211.988 µs, direct가 292.500 µs였다. 세 일정 모두 957 ACK는 656과 같은 클록에 도달했다.

- 폭을 줄인 후보는 남은 각 데이터 비트의 max-delay와 hold 쌍을 검사했다. direct는 64개 출발점을 exporter FF로 옮겼다. port는 기존 96쌍을 그대로 쓰며 87개 11.904 ns·9개 23.808 ns 제약이다. 배치 후 물리 CDC 타이밍은 미확정이다.
- 656 source와 port source를 같은 자극에서 매 NES 클록 대조했다. 최대 3,616개, patch 0·1·7개, generation wrap, 무작위 backpressure, query miss와 enable 해제에서 모든 query·유효 record·오류·해제 시각이 일치했다. 네 END와 두 ABORT를 확인했다.
- 실제 SPI에서 처음 헤더보다 앞선 ABORT의 generation, 부분 D1 뒤 D2 거부, 오래된 token, 잘못된 D3, 부분 map 취소와 STOP 뒤 cold 재시작을 검사했다. split은 prefix 하나를 보낸 직후 취소했고, direct는 host 클록을 멈춘 동안 lease를 취소한 뒤 순서대로 헤더와 ABORT를 수락했다.
- 각 후보의 실제 원본 복구 D1을 같은 ARM으로 해석했다. 99셀과 부분 tail을 복원했고 start·generation·개수·중복·잘린 블록을 거부한 뒤 cold로 다시 수신했다. 최종 ACK까지의 재생은 905–957 연속 일정이다. 메뉴·base 복귀에는 656에서 검증한 동일 ARM을 쓴다.

## 다음 삭제 예산

현재 부족분은 **최소 17 LE이며 동시에 14 LAB**다. 현재 이용 밀도(15,425 / 977)를 그대로 적용하면 14 LAB는 약 221 LE 규모다. 221은 구조 후보를 거르기 위한 추정치다. 실제 합격선은 전체 Fitter의 두 한도다.

다음 후보는 수신한 96비트 word를 여러 레지스터에 복사하는 대신, 원본 셀 페이지가 쓰는 M9K의 여유 주소에 NES가 한 record를 기록하고 host가 읽는 방식이다. host 공통 주소 경로를 시작점으로 삼되, 실제 dual-clock RAM의 두 포트 추론, 쓰기 완료 toggle, host의 마지막 읽기 뒤 반환, STOP 시 세대 폐기까지 한 경계로 계산한다. 절약 후보는 송·수신 데이터 FF 두 묶음(총 192비트)과 SPI 직렬화 선택 경로다. 직접 캡처의 실측상 FF 삭제만으로는 LAB 예산을 충족하지 못했다.

map당 4 B, 나머지 record당 12 B를 임시 RAM에 쓴다고 가정하면 53화면 237,468 B, 954·955 각각 4,680 B, 최다 4,692 B다. 1 B/NES 클록이면 이 쓰기 횟수 외에 host 읽기·주소 중재와 CDC 왕복이 든다. 이를 656 일정에 일괄 가산하거나 SPI 전송 절감으로 계산하지 않는다. 954 SEAL과 957 ACK가 있는 같은 연속 일정에 실제 포트 지연을 넣고, 전체 FIT가 성공한 경우 배치 후 STA를 진행한다.

## 재현

1. 656 ingress 보드를 기준으로 `prepare_nes_record657.py BASE OUT`을 실행한다. field는 기본값이고 다른 후보는 `--staged`, `--split`, `--direct`, `--count`, `--lanes`, `--port` 중 하나를 쓴다. 각 출력에서 `quartus_sh --flow compile board`를 실행한다.
2. Starter FLOAT 한 좌석에서 `check_nes_record657.py`의 일반·`--guards`를 순차 실행한다. split/direct는 동명 스위치, 96비트 세 후보는 `--count`를 사용한다. `--count --audit`는 양 끝의 발행·수락을 기록한다. 최대 계수·취소 대조는 `check_nes_record657_limits.py`, 원본 복구 ARM 검사는 `check_nes_direct653_arm.py`다.
3. 서로 다른 sender 입력마다 `test_nes_direct653.py`로 654 combined ELF와 시작 클록 7,288,416 / 7,467,100을 연결한다. `analyze_nes_record657.py`로 소스 해시, 제약, 레코드 추적, 전체 FIT와 마지막 ACK를 대조한다. [측정값·원시 추적 해시](../analysis/record657-verification.json) · [656 기준](nes-stream656-results.ko.md)
