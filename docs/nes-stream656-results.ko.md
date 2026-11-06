# NES 656 · literal·헤더·CRC·원본 복구의 순차 처리

## 교체 범위

기준은 655 walk의 단일 M9K 보드와 654 combined ARM이다. MCU 전체 링크는 212,508 B, Flash 여유는 484 B다. map의 80/84셀 블록 경계, 네 거리의 검색 순서, 65816 소비 ROM, 보드 디바이스·SDC와 초기 RAM 이미지를 고정했다.

- **stream**은 literal이 발견될 때마다 RAM에 쓰고 길이 위치로 돌아가던 처리를 없앴다. 원본 셀이 M9K에 남아 있으므로 참조 명령이나 블록 끝에서 연속 literal 범위가 확정되면 길이와 바이트를 한 번에 쓴다. 같은 주소 증가기와 읽기 상태가 원본 복구의 하위·상위 바이트도 순회한다. 그룹 시작과 길이는 마지막으로 읽은 주소에서 구한다. 셀 CRC를 헤더에 먼저 쓰고 같은 누산기를 wire CRC에 재사용한다. 별도 decoded CRC 사본, literal 길이 역기록 포인터, 헤더 전용 카운터, RAM 읽기 복귀 상태 레지스터를 제거했다.
- **ingress**는 동일한 CRC16 계산 회로로 첫 호스트 수락의 하위 바이트와 그 다음 쓰기 클록의 상위 바이트를 계산한다. 첫 셀에서 0xffff로 시작하므로 STOP 전 상태에 의존하지 않는다. 이를 헤더의 원본 CRC로 쓰고 셀 전체를 다시 읽던 CRC 순회를 없앴다. ARM은 D1 wire CRC와 실제 복원한 셀 CRC를 별도로 검사한다.
- **owner**는 일반 출력·압축 출력·원본 serializer까지 SPI의 한 쓰기 포인터를 사용한다. 원본으로 전환하면 헤더 뒤로 포인터를 되돌린다. 마지막 CRC는 ordinary와 원본 복구도 같은 RAM 순회로 계산한다. 복구 그룹을 발행할 때마다 기존 base를 4씩 진행한다.
- **fused**는 ingress에 더해 mailbox의 host 수신 레지스터를 serializer의 시프트 저장소로 공유한다. 기존 두 클록의 request/ack, 동기화, host capture edge를 유지하고, host가 단어를 사용할 수 있을 때만 다음 capture를 허가한다. 유효한 pending word와 serializer 쓰기의 충돌·정지 중 데이터 변화를 RTL에서 검사했다.
- **late**는 일반 명령의 데이터가 마지막 바이트까지 mailbox에 남도록 반환 시점을 옮겼다. 일반 명령은 이 데이터를 직접 읽고, 원본 4셀을 묶는 60비트 저장소만 둔다.
- **header**는 마지막 셀의 상위 바이트가 수락될 때 완성된 CRC·generation·start·count를 기존 원본 serializer에 넘겨 10 B 헤더를 발행한다. 원본 전환 시 같은 페이지를 재사용하며 모든 wire CRC는 최종 유효 범위를 순회해 계산한다. 헤더 발행 도중 D0가 준비를 공개하지 않도록 막았다.

## Quartus Lite 전체 보드 비용

| EP4CE15F17C8 | 전체 LE (한도 15,408) | 필요한 LAB (한도 963) | 부족 LE / LAB | 955 첫 7블록 준비 합 |
|---|---:|---:|---:|---:|
| 655 walk | 15,739 | 993 | 331 / 30 | 239.500 µs |
| stream | 15,634 | 988 | 226 / 25 | 239.560 µs |
| **ingress** | **15,508** | **980** | **100 / 17** | **211.762 µs** |
| owner | 15,577 | 986 | 169 / 23 | 211.714 µs |
| fused | 15,693 | 991 | 285 / 28 | 211.952 µs |
| late | 15,781 | 997 | 373 / 34 | 211.952 µs |
| header | 15,501 | 982 | 93 / 19 | 211.976 µs |

모든 후보에서 셀 RAM은 **simple dual-port M9K 한 개**, 보드 전체는 **56 / 56 M9K, 305,264 논리 RAM 비트**였다. 전체 컴파일은 모두 LAB 부족으로 FIT에서 중단되어 배치 후 STA·SOF가 생성되지 않았다.

다음 비교 기준은 **ingress**로 둔다. 655 대비 **231 LE와 13 LAB**를 회수했다. 955 첫 7블록의 584셀(1,168 B)을 봉인 후 다시 읽는 CRC 순회를 제거해, 준비 시간 합을 27.738 µs 줄였다. header는 ingress보다 7 LE 적게 쓰지만 배치에 2 LAB를 더 요구한다. fused는 655보다 레지스터 161개를 줄였지만 전체 보드에서 회수한 면적은 46 LE와 2 LAB였다. 수신 레지스터를 공유하자 쓰기 데이터 선택과 점유 제어 비용이 들어갔다. 이 결과는 각 후보를 같은 전체 보드로 컴파일한 값이다.

## 검증 경계

실제 exporter·mailbox·host SPI·RAM을 거친 905–957의 901개 D1 payload와 wire CRC를 655 walk 및 독립 packer와 대조했다. 53화면의 D1 블록 합(wire CRC 포함)은 79,392 B이고 955 첫 7블록은 500 B다. 후보별 RAM 준비 클록을 **각 후보의** 두 연속 일정에 반영했다. 같은 시작 master clock 7,288,416 / 7,467,100과 ARM CPI 2, IRQ, 공유 SPI 드라이버 비용, ROM 공급 달력, 두 staging 슬롯과 실제 65816을 사용한다. 이는 실기 FPS 또는 배치 후 STA 측정과 구분한다.

원본 99셀과 3셀 tail, 네 참조 거리·동률·32셀 상한, 마지막 19셀, 16비트 token wrap, 준비 중 D0, 부분 D1, stale D2, D3 CRC·길이·인자 오류, 8셀 상태의 lease 취소/E002를 확인했다. 검색·literal 쓰기·헤더·원본 4셀 출력·최종 CRC의 중간 STOP 후 D0 길이·token·읽기 소유권을 확인하고, 다른 map의 80셀을 cold로 다시 읽어 바이트와 CRC를 대조했다. 동일한 ARM에서 독립 decode·END 보류 중 STOP·최종 ACK·메뉴 및 base 정상 복구·네 실패 차단을 검증했다.

## 연속 표시 일정

| 656 ingress | 위상 1 | 위상 2 |
|---|---:|---:|
| 951–955 표시 간격 (VBlank) | 3 / 4 / 3 / 3 / 3 | 3 / 4 / 3 / 3 / 3 |
| 954 SEAL 여유 (953 표시 기준, 648 마감 대비) | 1.658 ms | 1.592 ms |
| 951 공개선 / 957 최종 추가 대기 | 239선 / 0회 | 239선 / 0회 |
| 밀집 평균 표시 간격 | 53.281 ms | 53.249 ms |
| 957 마지막 ACK (master clock) | 68,589,578 | 68,589,458 |
| MMC643 대비 957 마지막 ACK 단축 | 116.616 ms | 133.081 ms |

여섯 후보 모두 두 위상의 954·955, 954 SEAL 마감, 951 공개선과 957 최종 대기 검사를 통과했다. 655 walk와 마지막 ACK는 각 위상에서 정확히 같은 클록이었다. 준비 순회를 줄여 얻은 시간은 이 연속 일정에서 다음 표시 VBlank를 더 앞당기지 않았다.

## 재현

1. `prepare_nes_stream656.py <655 walk 보드> <새 출력> stream|ingress|owner|fused|late|header`로 실제 인스턴스를 교체하고 Quartus Lite 25.1의 `quartus_sh --flow compile board`를 실행한다.
2. 한 좌석 FLOAT에서 `check_nes_stream656.py`를 일반/추가 검사(`--directed`)로 각각 새 디렉터리에서 실행한다. fused에는 `--fused`, header에는 `--header`를 준다. 기존 배선을 쓰는 후보의 일반 53세대 실행은 `check_nes_serial654.py`와 같다.
3. 654 combined ELF와 각 RTL의 `sender.json`을 `test_nes_direct653.py --geometry650 --commit-pop-bound --keep-run`에 연결해 두 위상을 독립 재생한다. `check_nes_direct653_arm.py`로 실제 RAW D1 복구를 대조한다. `analyze_nes_stream656.py`로 FIT 보고서·ARM 해시·실제 블록 준비·최종 ACK를 묶는다. [검증 수치와 원시 추적 해시](../analysis/stream656-verification.json) · [655 기준](nes-search655-results.ko.md)
