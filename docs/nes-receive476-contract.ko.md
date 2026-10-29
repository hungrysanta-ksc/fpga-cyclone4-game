# NROM476: 수신 CRC와 필수 tag 순회

PR134 merge `93bb8f715914da12d46f1d5c8262d6e8b10d3362`의 master 반영을 확인하고 `codex/nes-receive-cost-476`에서 재개했다. 현재 PC의 원본을 사용하며 PC 이전 정비는 우선하지 않는다. 기준은 실기474/475의 평균23.59fps이며 **476 실기 FPS는 아직 없다.**

## 측정과 실제 교체

선택474 ELF/firmware의 PT_LOAD bytes를 대조하고, 기존 live moving 실행의 D0/D1/D2/D3를 실제 M4 `poll/prepare`에서 재생했다. SPI callback은 원본116거래의 TX/길이를 정확히 비교하고 원본 응답을 반환한다. reset 포함506568명령 중 CRC16(인라인 poll), 압축/geometry 해석,8192tag bitmap 순회가 컸다. 외부 SPI/IRQ 대기 시간은 이 명령 수에 포함되지 않는다.

- CRC16: 동일 CCITT0x1021/initffff의8bit 반복을 동등한 byte 식으로 바꿨다. 테이블·RAM을 추가하거나 수신 CRC 비교를 없애지 않았다.
- META_END: 동일2048B required bitmap을32bit 단위로 읽고, nonzero word 안의2bit tag/kind만 오름차순으로 열거한다. byte 조합으로 endian/alignment/alias를 피하고 nonzero에만 ctz를 적용한다. kind2의 홀수 bit도 pair의 시작으로 내린다.
- missing/512상한·geometry/slot/count·record 순서·CRC8·POP/retire와 실패 상태는 유지한다. 압축2232·단일 복원·BG 계획/quiet474·최종ACK/EA·FPGA471/65816은 그대로다.

## 같은 입력의 결과

| M4 고정 replay | 474 | 476 |
|---|---:|---:|
| 총 명령, reset/poll/prepare 포함 | 506568 | 309481 |
| poll 함수에 귀속된 명령, CRC16 포함 | 128656 | 20636 |
| logical_record 명령, META_END 순회 포함 | 198528 | 109461 |
| SPI 거래 / D1 packet / payload | 116 /10 /1800B | 동일 |
| 전체 receiver 상태·모든 TX | 기준 | byte 동일 |

총197087명령/38.9063% 감소다. 이는 **단일 cold 이동 입력 replay의 CPU 명령 수**이며, 실기 수신18–21ms·전체 표시 시간/FPS가39% 개선됐다는 뜻이 아니다. 초기 empty D0 비율도 실기 warm 평균과 다르다. 기존 capture/export 중첩을 새로 구현한 성과로 계산하지 않는다.

## 검증

- actual old/new C의 모든3byte CRC 입력16777216조합,0–256B 길이 및 표준 문자열을 비교했다.
- 모든8192tag×kind1/2/3,512dense/sparse,512seeded 조합·missing513/불일치/overflow 등25094건에서 전체 상태·정렬·kind·실패 결과가 같다. 합성 중간 상태 단위 시험이며 전체 정상 프레임을 대신하지 않는다.
- 실제 링크 M4의 정상 replay와 오류8종: status CRC, READ CRC/payload/transfer, 정상 CRC를 가진 잘못된 geometry, POP CRC, retire token, prepare transfer. 구/신 전체 상태·SPI 소비 개수가 같고 실패 뒤 poll/prepare/consumed가 추가 SPI·상태 변경을 만들지 않는다.
- 새476 native ARM C→같은 NES/source RTL→FPGA queue/tile→Mesen65816에서30ACK/4144VRAM bytes/1commit·독립 이동 막대 mask·최종ACK/EA·run136 STOP·observer 정지를 통과했다. 입력 geometry fixture를 host에 공급하지 않았다.

마지막 연결은 native C·모델 PSRAM/clock·65816 emulator다. 실제 M4 IRQ/동시 물리 시간·장시간 연속 capture·476 실기/60Hz 증거는 아니다. Starter FLOAT1좌석으로 단일 실행했고 새 라이선스/smoke·불변 FPGA 재합성은 하지 않았다.

## 비용과 선택

| 항목 | 474 | 476 |
|---|---:|---:|
| ARM text/data/bss | 202569/10040/18552B | 202597/10040/18552B |
| firmware 파일 | 212612B | 212640B |
| Flash 파일 후미 | 380B | 352B |
| logical_record / poll static stack | 48/560B | 동일 |
| RUN frame / 산술 잔여, 중첩·IRQ 전 | 31848/4984B | 동일 |
| FPGA LE/comb/FF/RAM bits | 14740/13672/8063/185824 | 동일471 bitstream |

ARM 변경11파일 중 실제 알고리즘 차이는 `nes_native165.c` 하나다. 새 로그/경로 identity는476이다. FPGA66개 QSF 입력을 다시 hash 대조했다. 기존 nominal 관련 setup+0.081ns/hold+0.143ns·강화 예산−0.036ns 및 raw reset/CDC/IO 한계는 남는다.

첫 SUBST sandbox 거부, Unicorn bytearray adapter 오류, sandbox GCC DLL 시작 실패는 원본을 보존했고 후보 실패/새 라이선스 문제로 해석하지 않았다. 최종 선택은 `arm476-02`, `guards02`, `live01`이다.

## 다음 판정

[설치·원복](nes-receive476-trial.ko.md)의 같은 이동 장면을 실기474와 비교한다. 수신 감소가 기존 NES capture/export·SEAL/최종ACK 일정에 흡수되는지 먼저 확인한다. 단일 receiver를 덮거나 이미 존재하는 다음 capture 중첩을 다시 만들지 않는다. 평균30fps까지9.06ms,60Hz까지25.73ms의 기존 격차를 명령 수만으로 차감하지 않는다. 세부 근거는 [verification](../analysis/receive476-verification.json)이다.
