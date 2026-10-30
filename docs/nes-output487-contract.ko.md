# NES487 — 출력 본문 감사와 bounded RLE 탐색

PR136 merge `2d4543ef2442bc798bcec128a4a108fdfc4d5287`의 master 도달을 확인하고 `codex/nes-output-budget-487`에서 진행했다. [실기486](nes-hardware486-results.ko.md)은 그대로 두며, [487 검증](../analysis/output487-verification.json)·[다음 관문](nes-output487-plan.json)을 따른다. 새 실기 전달본은 없다.

## 실제 실행한 범위

배포485의 linked M4 수신/계획과 실제 `nes_sink212_seal`을 기존 SMB3905..975 입력71개에서 실행했다. 전체 수신/표시/상주 상태와598개 계획은 기존 기준과 일치한다. serializer의 모든 패킷을 저장하고 별도 byte expander로 두 bank의 map·CGRAM·OAM·전체 HDMA3418B를 원래 M4 테이블과 비교했다. ACK는 즉시 성공하는 모델이며 window CRC/E0·IRQ·ROM·실제65816 공통 일정은 이 명령 계측에 포함하지 않는다.

이는 사용자가 플레이한494프레임의 재생이 아니다. 실제 로그에는 section payload나 raw 행 수가 없어 그 장면에 아래 절감량을 그대로 적용할 수 없다. 원시 packet/geometry/raw/ELF는 로컬 `probes/nes-output487`에 보존하며 Git에는 해시와 통계만 넣는다.

## 기존 전송의 원인

| SEAL section | 71개 총 body B | 패킷 수 |
|---|---:|---:|
| map | 120900 | 688 |
| CGRAM | 19028 | 284 |
| OAM | 4370 | 213 |
| HDMA/raw 묶음 | **164436** | 1065 |
| manifest | 11928 | 71 |

HDMA라는 이름에 scroll만 있는 것이 아니다. 매 프레임 body2316B = scroll/zero padding23B + **raw CHR2048B** + mode/enable/length245B다. 이 입력71개는 raw 행이 모두2개인데도32개 tile의8행·8plane 고정 공간을 전송했다. 각64B tile 안의 짧은 zero 구간은 기존64B 반복 탐색 임계치에 걸리지 않아 raw CHR는9개 literal packet으로 그대로 나갔다.

map 변경 granule은1082개, 실제 목적지 갱신은1891개다. 처음 두 cold를 뺀69개는 변경1011/갱신1763이다. 마지막 표시와 비교한 변경을 두 목적지 bank에 전파하는 현재 의미에 부합한다. 이 차이를 중복으로 간주해 제거하면 inactive bank가 오래된 상태로 표시될 수 있다.

raw CHR와 scroll은 이전 목적지와71개 모두 달랐다. mode/enable/length만 warm69개에서 이전 목적지와 같았다. 따라서 raw 전체의 단순 bank 재사용으로 큰 전송 비용을 없앨 근거는 없다. mode 재사용도 현재 독립 coverage/소유권을 바꿔야 하며 지금 생략하지 않았다.

## 구현한 탐색 후보

`span_piece`는 다음 반복 구간을 찾을 때 길이64 이상인지 알기만 하면 되지만, 남은 길이 전체를 읽고 있었다. 이 predicate를 최대64B 비교로 제한하고64B 미만 tail의 불필요한 호출을 건너뛰었다. 처음 run의 실제 길이 측정·cost 선택·CRC/ACK·STOP·최종 표시 소유권은 바꾸지 않았다.

| 검증/비용 | 결과 |
|---|---|
| 실제 M4 serializer 명령 | 17,275,495→13,767,406, **20.31% 절감** |
| 상태·계획·전체 출력 패킷 | 71개에서 byte 동일; 독립 table 확장 일치 |
| 소유권 guard | 12사례 통과: delayed ACK/두 frame/잘못된 CRC·identity·token/STOP/불확실 E1 |
| ARM | text202729/data10040/BSS18572, firmware212772B |
| 485 대비 | Flash+12B, 잔여220B; 새 상태/버퍼0B |
| FPGA/SNES ABI | 그대로, 새 합성 없음; 기존15254LE/154LE 여유 |
| 전체 시간·FPS | 미측정; 명령 절감을48.33ms·8.22fps에 곱하지 않음 |

이 후보는 전송량을 줄이지 않는다. 실제 병목의 일부만 개선하므로 이 변경만으로 사용자에게 새 시험을 요구하지 않는다. 선택 로컬은 baseline `audit03`, candidate `candidate01/ARM01/candidate-audit01`, `guards01`이다. `audit01` DWARF offset 해석 실패와 smoke `audit02`도 보존했다.

## 전송량을 줄일 다음 구조

raw 색상은0..63이고 CHR 생성 시64를 더하므로 plane6은 사용 행에서1, plane7은0이다. 사용하지 않은 행도0이다. 실제 쓰는 행의 plane0..5만 보내면 필요한 body는 **192×raw_count B**다. raw_count2의 이번 입력은2048→384B이며 독립 prototype decoder가 원래2048B와 정확히 일치했다.1..7개 행의 추가 생성 벡터도 통과하고 count8·짧은 payload·암묵 bit 위반·미사용 행 변조4개를 거부했다.

기존240B packet/19B framing을 유지하는 projection은 raw CHR9→2packet, **1797B/프레임·5.4766ms@2.625Mbps** 절감이다. 실제 ARM pack·65816 확장/검사 시간은 아직 없다. CRC는 새로 전송한 compact bytes에 적용하고, SNES는 canonical CHR를 재구성한 뒤 기존 독립 검사·DMA·최종 ACK 조건을 유지해야 한다. 이것은 현재 ABI에 연결된 성과가 아닌 다음 후보의 손실 없는 표현 검증이다.

현재 SNES program 배치의 body 여유는224B다. 이는 SNES ROM 최대 크기가 아니라 기존4096B 배치/boot 예약의 예산이며, 넘으면 배치 확장과 전체 영향도 함께 검토한다. ARM220B와 함께 pack/확장 code의 실제 순증가를 먼저 측정한다. 일반 queue/header가 새 길이/버전을 그대로 전달하는지 실제 보드 경로에서 확인하기 전 FPGA 무변경을 보장하지 않는다.

## 다음 작업 순서

1. **compact raw ABI를 실제 ARM·65816로 연결**한다. 초기에는 map/순서/기존 bulk와 bank lease를 유지한다. 버전·길이·raw_count·무효/중간 STOP·독립 검사·최종 ACK를 먼저 고정하고 Flash/stack/SNES code budget을 측정한다.
2. 실제 queue·공유 SPI·ROM/tile·65816 DMA/VBlank 경로에서 검증한다. 실기 SEAL48.33ms의 원인을 ACK 대기 하나로 보지 않으며, 즉시 ACK 모델의 명령 수와 합치지 않는다.
3. compact ABI와 현재 전송 속도/검증 가능한 SPI 여유를 전체 비용으로 비교한다. SPI 속도 변경은 아직 없다. source D0 준비 대기/MCU_RDY 소유권은 그 다음이다.
4. 의미 있는 결합 후보가 확인된 뒤 새 번호/로그/원복으로 전달하고 같은 장면·입력에서 비교한다. 현재 실제 기준은 여전히485의 대기13.55fps/플레이 포함8.22fps다. GBC/save·정상485/482/476/164/467을 보존한다.
