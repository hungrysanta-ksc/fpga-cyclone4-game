# 593 ARM 수신기 교체 결과

cold 905에서는 MMC577보다 빨라졌지만, 완성 펌웨어가 212,992 B 한도를 **148 B 초과**했다. 두 조건의 동시 판정은 실패다. 선택한 시험은 ARM04 전체 링크, test06 수신 시험, ack06 표시 소유권 시험이다. 세 결과의 ELF 해시를 대조했다. [검증 데이터](../analysis/receiver593-verification.json)

| 동일 cold 905 | MMC577 | 591 | 593 |
|---|---:|---:|---:|
| 전체 펌웨어 | 212,908 B | 214,760 B | 213,140 B |
| 실행한 ARM 명령 | 288,377 | 377,344 | 234,153 |
| 입력 I/O | 13.223 ms | 12.625 ms | 12.408 ms |
| 입력 합계, CPI 1 | 16.656 ms | 17.117 ms | 15.196 ms |
| 입력 합계, CPI 2 | 20.089 ms | 21.609 ms | 17.984 ms |

MMC577 대비 cold 입력은 CPI 2에서 약 2.105 ms 단축됐다. 이 비교에는 2.625 MHz SPI, 드라이버의 기존 opcode별 평균 비용, 84 MHz ARM에서 실제 실행한 명령 수가 들어간다. cold 593은 16패킷·58호출·3,125 wire B이며 D4 요청과 확인도 포함한다. D4의 드라이버 비용에는 기존 D3 평균을 썼다. 이 시간은 입력에 대한 모델값이며 실기 CPU cycle과 표시 FPS는 별도 측정 대상이다.

## 같은 바이너리에서 확인한 동작

- packet, logical_record, request, poll, PREPARE의 기존 구현을 교체했다. nonmap은 기존 압축 선택을 유지하는 3 B 블록 헤더를 사용한다. 단계·순번·token 검사는 packet이, D2 반환 확인과 COMMIT 공개는 poll이 맡는다. poll과 PREPARE는 응답 CRC 검사 코드를 공유한다. 기존 상세 오류 중 일부는 단계 단위 오류 코드로 합쳐졌다.
- 행 수신 단계는 정렬·길이·요청 bitmap·중복을 확인해 임시 map에 저장한다. 검증 단계에서는 최종 map 값마다 유효 비트·필수 tile·CRC를 함께 처리한다. cold 905의 ARM 메모리 읽기를 추적한 결과, map의 0~1,913번 바이트를 순서대로 정확히 한 번 읽었다. map CRC가 일치한 뒤 그 값에서 nonmap CRC를 이어간다. 실패하면 임시 tag·행 진행을 폐기하고 전체 행을 한 번 재요청한다.
- 53개 실제 입력의 geometry·raw·필수 tag/용도와 27개 수신 오류·복구 조건을 확인했다. 이전 프레임 COMMIT 뒤 warm 전송을 세 단계에서 끊고 수신기를 리셋한 뒤, 다음 cold가 모든 행을 다시 받은 것도 검사했다. 잘린 BEGIN과 손상된 COMMIT 응답은 이전 base를 재사용할 수 없게 한다.
- 같은 ELF의 실제 ARM runtime에서 cold 입력부터 SEAL·최종 ACK·EA까지 실행했다. 정상 ACK는 1화면 집계 후 IDLE로 돌아갔다. generation만 틀린 최종 ACK는 표시 0회, EA 0회였다. 정상 ACK 뒤 EA 처리 중 STOP은 이미 표시한 1화면을 집계하고 COMMITTED 상태에서 후속 입력을 차단했다. 이 시험은 source·출력 응답과 service STOP을 모델링했다. 실제 65816·VBlank·메뉴 복귀와 보드 STOP은 별도 범위다.

## Flash와 다음 판정

593 object에서 의미검사를 포함한 packet 본체는 2,500 B이고, request는 220 B, poll은 476 B, PREPARE는 136 B다. 이 밖에 공유 응답 처리 66 B와 CRC 갱신 24 B도 링크에 들어간다. 수신 상태는 9,920 B, 호출자 프레임은 31,904 B다. 하위 호출과 IRQ를 적용하기 전 RAM 간격은 4,888 B다.

591에서 실제 순삭제한 크기는 1,620 B다. 최초 링크의 초과분은 256 B였고 요청·실패 상태 통합과 절별 저장을 거쳐 132 B로 줄었다. 이전 이력이 있을 때도 잘린 BEGIN을 명시적으로 무효화하는 최종 링크는 148 B 초과다. 최종 펌웨어는 MMC577보다 232 B 크고 BSS는 18,592 B다. [592 교체 예산](nes-boundary592-results.ko.md)

다음은 전체 링크 map에서 상주가 필요한 코드와 진단 또는 로드 시점으로 분리 가능한 코드를 구분하는 일이다. 각 후보는 실제 회수 바이트에서 새 호출·로딩 비용을 차감하고, NES·GBC·메뉴·저장 복구에 필요한 코드와 경계를 확인한다. 최소 148 B의 순회수와 전체 재링크 근거가 있어야 FPGA와 두 시작 위상의 첫 BG~최종 ACK 시험으로 진행한다. 실기 기준은 MMC577이다.

재현에는 591 ARM02 전체 빌드 트리와 581 evidence01 ZIP이 필요하다. 저장소의 prepare_nes_receiver593.py로 새 트리를 생성하고 build_nes_trial577.ps1로 전체 링크한다. check_nes_receiver593.py와 check_nes_ack593.py에 같은 src 및 ZIP을 전달한다. report_nes_receiver593.py가 SHA로 두 결과를 묶고 이미지 크기를 검사한다. [수신기 생성](../tools/prepare_nes_receiver593.py) · [수신 시험](../tools/check_nes_receiver593.py) · [최종 ACK 시험](../tools/check_nes_ack593.py)
