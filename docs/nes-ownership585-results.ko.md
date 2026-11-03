# 585: decoder·응답·RAM 소유권의 공동 교체 예산

**다음 시험의 교체 범위와 중단 기준을 확정했다. 제품 후보는 아직 선정하지 않았다.** 584에서 늘어난 Flash를 숨기지 않고, 기존 record 해석과 plan 응답 변환까지 삭제하는 경계로 넓힌다. 두 뱅크의 전체 이력 복사 대신 기존 출력 버퍼·stale mask·별도 raw shadow를 사용하는 구조를 참조 복원으로 확인했다.

[검증 JSON](../analysis/ownership585-verification.json) · [584 비용](nes-transport584-results.ko.md) · [현재 계획](nes-retrospective579-plan.json)

## 삭제할 코드와 유지할 검사

577/584 object의 함수 symbol을 각각 읽었다. 같은 이름의 다른 파일 함수나 parent/child 크기를 합산하지 않았다.

| 실제 함수 경계 | 크기 | 다음 처리 |
|---|---:|---|
| `nes_native165_packet` | 1434B | record header·packed map·repeat·raster/raw 확장을 포함한 기존 envelope 교체. 기능을 전부 없애는 절감이 아님 |
| `logical_record` | 1112B | geometry 순서·범위·의미·META_END·required tile 열거·PREPARE/COMMIT 검사를 유지. BEGIN reset은 base 보존에 맞게 수정 |
| `require_tile` | 68B | 독립 required-tag 계산 유지 |
| 584 `read509` | 166B | 50B→기존20B 변환을 없애고 plan이 공통 필드를 직접 소비. descriptor/END/count/retire 검사는 보존 |
| 583 row 복원 | 248B | 새 비용으로 포함. packet CRC·base identity·전체 의미검사를 대신하지 않음 |
| 584 runtime `transfer` | 490B | CRC/identity/STOP까지 포함해 통째로 삭제할 수 없음. RX ownership과 copy만 재설계 |

584가 한도를 360B 넘으므로 최대 교체 예산은 **1434 + 166 − 248 − 360 = 992B**다. 이 992B 안에 새 section/control 해석, canonical CRC·base 검사, 직접 plan 소비, RX 경계와 history helper의 추가 코드가 들어가야 한다. 아직 구현·링크한 순삭제 수치가 아니다. 1112B 의미검사나 490B runtime 전체를 절감으로 세지 않는다. Flash cap은 212992B 그대로다.

## 실제 RAM 간격

ELF load segment와 compiler stack-usage를 함께 읽었다. BSS만 빼서 RAM 여유로 부르지 않았다.

| 항목 | MMC577 | 584 |
|---|---:|---:|
| RAM 시작부터 static 끝까지(data 포함) | 28744B | 28828B |
| `native_frames222` 자체 stack frame | 31864B | 31856B |
| 64KiB에서 남는 간격 | 4928B | 4852B |

마지막 행은 **상위 호출 frame·하위 호출·IRQ를 빼기 전**이다. 8948B의 두 뱅크 nonmap 이력은 그것만으로도 맞지 않는다. 584 시험의 관측 stack 1064B는 실제 RUN/IRQ 최대치가 아니며 이 표의 안전 여유로 대체하지 않는다.

### 기존 출력 버퍼를 사용하는 대안

현재 `build211`은 map 외의 버퍼를 memset하고, palette/OAM을 다시 초기화한다. 그러므로 기존 버퍼가 선언돼 있다는 이유로 그대로 이전 이력으로 쓸 수 없다. 완성된 8B 값을 먼저 계산한 뒤 이전 값과 정확 비교하고 덮어쓰도록 생산 순서를 바꿔야 한다. 임시 zero를 먼저 쓰면 stale이 과다 설정돼 이득이 사라진다.

- palette 512B, OAM 544B, scroll 1121B는 기존 video 배열에 마지막 생산 값을 보존한다. layout/길이 변경과 새로 활성화된 범위는 dirty로 처리한다.
- raw CHR·modeA/modeB/enable·길이는 BG key union과 수명이 겹친다. 기존 union을 영구 이력으로 쓰지 않고 **최대 2297B shadow**를 따로 예약한다. 현재 53개 fixture의 사용량은 633B지만 최대 예산을 633B로 축소하지 않는다.
- 4474B를 section별 8B 그룹으로 나누면 560그룹이다. 두 대상 뱅크의 stale mask는 **140B**다. 새 값이 직전 값과 다르면 두 뱅크에 stale을 설정한다. 실제 대상 뱅크의 동일 identity 최종 ACK 이후에만 해당 그룹을 clear한다. STOP/부분 실패 시 둘 다 무효화한다.
- 단일 shared RX 259B와 최종 chunk scratch 8B를 포함해 4B 정렬 예약 합계는 **2708B**다. 584의 간격에서 2144B가 남지만, 여기에 상하위 호출·IRQ·identity/길이/독립 검사 상태가 아직 들어가야 한다. RAM 통과 판정은 아니다.

현재는 ARM 다음 입력 poll이 표시 ACK/EA 뒤에 실행된다. 이 순서를 유지하는 후보다. 입력 수신·planner·ordinary가 서로 다른 프레임의 같은 버퍼를 동시에 사용하도록 확장하지 않는다.

## 참조 복원에서 이득을 얼마나 유지하는가

두 기존 위상의 53개 packet trace 각각에서 생략한 packet의 모든 바이트가 실제 target-bank oracle과 일치하는지 확인했다. bank oracle은 시험용이며 제품 RAM 비용으로 빠뜨린 cache가 아니다. 검사는 기존 582 전체 이력 계산과 생략 가능 바이트가 일치하는 것도 대조한다.

밀집 951–955 평균이며 두 기존 trace에서 같은 값이다. packet을 부분 분할하지 않고 기존 whole packet만 생략했다.

| 이력 방식 | 생략 wire | 범위 선언 | 순 wire 절감 |
|---|---:|---:|---:|
| 기존 exact 두 뱅크 참조 | 767.8B | 60.6B | 707.2B |
| 기존 버퍼 + raw shadow + stale mask | 730B | 55B | **675B** |
| raw shadow 없이 기존 prefix만 | 409B | 48B | 361B |

stale mask는 값이 A→B→A로 돌아온 경우에도 보수적으로 전송할 수 있어 exact 이력보다 32.2B 덜 줄였다. 대신 8948B의 full-history 의존성을 줄일 경계를 찾았다. 이 수치는 새 ARM 일정·FPS 개선이 아니다.

잘못된 serial/bank/layout 또는 final이 아닌 ACK 네 조건이 mask를 clear하지 않으며, STOP/부분 전송 뒤 cold와 layout 변경 시 전체 전송을 확인했다. 참조 모델의 취소 epoch가 바뀐 뒤 늦은 이전 ACK도 거절했다. 이는 새 namespace 계약의 참조 검사이며 실제 하드웨어 STOP/drain 검증은 아니다. **은행 RAM만 손상시키면 mask는 이를 검출하지 못한다는 반례도 재현했다.** 최종 ACK 때 확정한 독립 expected/coverage/CRC와 retained-data 손상 검사를 없앨 수 없다. ARM history 자체의 손상·유효성 검사 역시 추가 예산 항이다.

## SPI 포트와 버퍼 소유권

| 단계 | 소유자/살아 있어야 할 데이터 | 고정할 규칙 |
|---|---|---|
| source header/body | ingress identity + sealed packet, shared RX | header 검사 결과를 고정한 뒤 body 수신. CRC/의미검사 완료 전 ACK 금지. body 소비 중 RX 재사용 금지 |
| E1 | window의 259B TX + 호출자의 원본 packet | 전송 뒤 원본에서 last identity를 저장하므로 원본을 RX로 덮어쓰지 않음 |
| E9 | plan의 248B TX와 미발행 OBJ suffix | RX는 별도 259B. trailer가 덮는 suffix 4B 보존은 계속 필요. 부족한 응답 clock의 TX dummy는 parser가 선언 길이 뒤를 무시하는 새 계약 필요 |
| 공통 응답 | RX 앞의 snapshot→검증된 50B 상태 | physical transfer 종료 후 한 번 CRC/epoch/serial/sequence 검사. 다음 RX 전에 필요한 snapshot 복사. E9 ready 재사용 금지 |
| observer/service | 자체 local buffer, transaction 사이만 SPI 사용 | 기존 `inside_transfer`·clock-fault guard 유지. nested callback이 shared RX를 재사용하지 않음 |
| DMA 종료/STOP | driver가 TX/RX 소유 | 두 DMA stream EN 해제와 SPI 요청 중지까지 buffer 수명 유지. clock-fault·stuck 경로 삭제 금지 |
| tile/map staging | FPGA/65816의 기존 두 슬롯 | ARM shared RX와 무관. plan-ready·bulk consume·queue credit·최종 ACK를 한 상태로 합치지 않음 |

실제 E9 suffix cut 1–7을 모사했다. 기존 방식과 별도 RX는 모두 suffix를 보존했고, 무작정 52B로 늘린 in-place RX는 cut 1–5에서 기존 4B 보존 밖의 데이터를 손상했다. 이는 584의 임시 buffer를 단순 삭제할 수 없는 구체적인 이유다. shared RX의 새 실제 driver 경로를 실행한 시험은 아니다.

## 결합 입력 ABI의 한도

583 행 block과 582 BEGIN/META_END/END/COMMIT를 유지하되 새 결합 ABI의 payload를 **254B 이하**로 고정한다. 36B header와 payload+5B body, 마지막 36B 확인을 모두 계산한다. 255/256B는 이 ABI의 유효 payload가 아니다. source packetizer와 ARM header가 같은 상한을 검사해야 한다.

53개 입력의 재구성이 같고 DD 전송이 모두 259B 이하다. 밀집 입력은 6/6/6/7/6 packet, 성공 전송 평균 1111B다. 583의 38B/packet 가정 대신 실제 584 형식의 41B/packet을 반영했으며 cold를 포함해 packet 수는 해당 583 참조와 같았다. 이 비교에는 BUSY 비용이 없다.

위 hybrid 이력과 새 header 비용을 넣은 조회 3회 가정의 밀집 wire는 9.081/9.091ms다. 이것은 **낙관적 바이트 예산**이고 driver·ARM·IRQ·ROM·65816·DMA·VBlank가 빠져 있다. 584에서 관측한 실제 조회 수로 동작한다는 보장이 없고, cold 두 화면의 wire 평균은 약29.37ms다. 60Hz 달성/선정 근거로 사용하지 않는다.

## 다음 작업과 중단 기준

R2의 다음 한 번은 이 범위의 **bounded ARM 전체 링크 비용 시험**이다. 새 section/row parser를 실제 의미검사에 연결하고 plan의 공통 응답 직접 소비 및 RX ownership을 함께 바꾼다. 이력의 final-chunk 비교·raw shadow·독립 검사 코드를 포함해 Flash 순증가 84B 이내, 위 2708B 예약과 실제 caller/IRQ stack에 들어가는지 확인한다. 992B는 목표 코드 상한이며 이미 확보한 절감이 아니다.

한도를 넘거나 독립 검사/소유권을 만족하지 못하면 padding·opcode·로그 축소로 우회하지 않고 C의 역할 또는 지원 범위를 다시 판단한다. IRQ/ROM/65816 두 위상 및 FPGA 전체 FIT는 그 뒤다. FPGA source base 2336B의 3M9K, 남은 LE148/M9K5, CDC/query/STOP 비용은 여전히 미검증이며 ARM 계산만으로 회로 여유를 주장하지 않는다.

MMC577·GBC/save·선택 FW/RTL·README는 유지한다. 새 설치 파일은 없다. `analysis05`를 선택하며 `analysis01`의 unnamed DWARF union 처리 실패와 중간 `analysis02–04`를 보존한다. 재현은 `tools/analyze_nes_ownership585.py --help`의 base/prototype/traces/data/out 경로를 지정한다. 공개 JSON은 원본의 해시와 계수만 담는다.
