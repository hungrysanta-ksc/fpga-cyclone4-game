# 586: section 수신·공통 응답·shared RX의 실제 ARM 결합

> 587 연결 감사: 이 문서의 입력4packet source는 시험 모델이다. 고정 MMC577 RTL은256B 단일 sealed block+96bit mailbox다. 기능 결과의 범위는 유지하며 모델 생산 일정·버퍼 여유를 보드에 승계하지 않는다. [실제 연결과 다음 판정](nes-ownership587-results.ko.md)

**이 결합안은 채택하지 않는다.** 585에서 정한 필수 경계를 실제 ARM에 연결했지만 최종 펌웨어가 213852B로 212992B 한도를 **860B 초과**했다. 출력 이력·planner 변경·retained-bank 손상 검사를 추가하기 전의 결과다. 이 나머지 작업과 FPGA/전체 FIT로 확대하지 않고 585의 비용 중단 기준을 적용한다.

[검증·비용 JSON](../analysis/combined586-verification.json) · [585 교체 예산](nes-ownership585-results.ko.md) · [현재 계획](nes-retrospective579-plan.json)

## 실제 구현

577을 기반으로 일곱 ARM 파일을 교체했다. `patch02/ARM02/test03`이 선택된 **비배포 시험 산출물**이다.

- 기존 record packet 해석을 section/row block으로 교체했다. BEGIN의 epoch/serial/base/count, block 순서/범위/형식, META_END/END의 canonical 길이·개수·CRC, PREPARE/COMMIT을 검사한다.
- 583 row 복원을 연결했다. BEGIN에서 map/row만 보존하고 나머지 receiver 상태·required bitmap을 초기화한다. inherited 값까지 기존 geometry 의미검사와 required-tag 열거를 거치고 canonical CRC에 포함한다. 실패하면 base 유효성을 취소한다.
- payload 상한을 254B로 제한해 header 36B와 body 최대 259B를 기존 driver 한도에 맞췄다. 새 RX pointer와 NULL callback 거절도 보존했다.
- plan이 공통 50B snapshot의 count/flags/descriptor를 직접 소비하게 바꿔 기존20B 응답 변환을 제거했다. bulk token·count·END·최종 ACK/EA 조건을 유지한다.
- runtime에 259B RX를 하나 두고 input body와 출력 응답이 공유한다. E1/E9는 원래 TX를 유지하며 RX를 별도 영역에 쓴다. E9의 선언 payload 뒤 dummy clock은 무시하는 새 계약이다. 미발행 suffix와 trailer가 겹치는 기존4B 보존은 유지한다.

FPGA에는 이 프로토콜이 구현되지 않았다. 현재577 profile과 호환되는 펌웨어가 아니므로 설치하지 않는다. GPIO/SPI/DMA driver 본체·clock-fault·STOP 종료 대기는 그대로이며 시험에서는 물리 callback을 모델로 대체했다.

## 기능 검증

실제 전체 링크 ELF의 M4 명령을 실행했다.

| 검사 | 결과와 범위 |
|---|---|
| 905–957 연속 입력 | 53개 전부 geometry/raw byte 일치. token wrap 및 이전 map/row 재사용 포함 |
| parser 거절 | 15조건: BEGIN/version/count/epoch/serial/base, block count/index/value, META/END CRC, 조기 COMMIT, 중복 token, 초과 길이, inherited map 손상 |
| 실제 수신 함수 + 출력 slice | 951/954 × 서비스 지연2값 =4사례. 실제 prepare 함수·4packet source·각7개 실제 plan·모델 소비/최종 ACK/EA |
| 전송·취소 | 기존584의18조건. 255/256B는 이제 header에서 거절하며 driver까지 보내지 않음 |
| API 인자 | poll NULL callback/NULL RX owner, prepare NULL callback 3조건에서 추가 SPI 없이 거절 |
| E9 suffix | 실제 ARM append/flush의 cut1–7에서15개 OBJ 순서와 미발행 suffix 보존 |
| queue 포화 |5packet pressure에서4credit 제한·drain, 최종 표시 허가 없이 EA하지 않음 |

53개 direct packet 시험은 END 뒤 PREPARE 상태를 시험 도구에서 부여한다. 실제 source prepare를 실행하는 네 slice와 구분한다. source의 canonical CRC 기대값은 fixture 생산자가 계산하며 새 FPGA가 실제로 생산한 값은 아니다. inherited map을 손상시킨 경우 META CRC로 거절되는 것을 확인했지만 이것이 출력 bank 이력 검사 구현을 뜻하지 않는다.

출력 slice의 소비·표시 허가는 endpoint 모델이다. actual65816·IRQ·ROM·2슬롯 RTL·VBlank·메뉴를 새로 실행한 시험이 아니다. user MMC577의 실기 결과를 이 후보에 승계하지 않는다.

## 전체 비용

| 항목 | MMC577 | 584 | 586 최종 |
|---|---:|---:|---:|
| firmware.stm | 212908B | 213352B | **213852B** |
| 배포 한도 대비 |84B 여유 |360B 초과 |**860B 초과** |
| BSS |18592B |18676B |18940B |
| slice 관측 stack |808B |1064B |832B |

586은577보다944B,584보다500B 크다. compiler executable section에서584 대비 native +652B, runtime −30B, plan −98B, window 0B다. 전체 code 증가524B와 최종 firmware 증가500B는 별개이며 최종 이미지 크기로 gate를 판정했다. object 함수 크기를 순삭제로 부르지 않는다.

RAM 시작부터 static 끝까지29092B, `native_frames222` 자체 stack31872B다. 나머지4572B에는 상하위 호출/IRQ가 들어가야 한다. 여기에585의2297B raw shadow·140B stale·scratch·독립 검사 상태를 아직 추가하지 않았다. shared RX는 이미 BSS에 포함했으므로2708B 전체를 다시 더하지 않는다. 이번832B 관측치는 전체 RUN/IRQ 최대 stack 증명이 아니다.

다음은 **cold source + 선택된7plan slice**의 비교다. 연속 warm 입력은 위53개 direct 수신 검사에서 다뤘으며 아래 종단 일정에 연결하지 않았다.

| 입력 / 모델 서비스 지연 | SPI 호출577→586 | wire B577→586 | M4 명령577→586 |
|---|---:|---:|---:|
|951 /128 |86→55 |4466→4592 |378950→442707 |
|951 /12000 |118→67 |5034→5168 |428820→453291 |
|954 /128 |88→57 |4490→4686 |380499→444525 |
|954 /12000 |120→69 |5058→5262 |430120→455339 |

SPI 호출은 줄지만 wire는126–204B 늘고 ARM 명령도 늘었다. canonical CRC·추가 수락 검사 비용을 포함한 결과다. 모델 생산자는 ARM 실행 중에도 진행하므로 호출 감소 일부에는 CPU가 더 오래 실행되는 효과도 있다. 명령 수는 실제 MCU cycle/표시 시간/FPS가 아니다. 두 서비스 지연은 두 ROM 시작 위상이 아니다.

## 무엇이 예산을 소모했는가

585의992B는 추가 코드의 **산술 상한**이었다. 실제로는 새 section parser1530B·row 복원246B·값 적용/CRC208B가 필요했고, 기존 `logical_record`도1136B로 남았다. 이전1434B record envelope를 제거했어도 새 layer가 더 작아지지 않았다.

현재 BEGIN은 새32B field를 검증한 뒤 기존64bit BEGIN 표현을 만들어 기존 함수를 다시 호출한다. 새 block admission의 순서/개수 검사 뒤에도 기존 per-value generation/index/phase 검사가 반복된다. 이는 geometry/CRC를 없애도 된다는 뜻이 아니라 **독립 검사 조건과 과거 record 표현을 같은 것으로 취급하면 교체 효과가 제한된다**는 증거다.

공통 응답 직접 소비는 plan 전체98B, shared RX 변경은 runtime 전체30B를 줄였다. RX stack은 개선됐지만 영구 RAM으로 비용이 이동했다. 이 작은 절감만으로 전체 판정을 뒤집을 수 없다.

## 중단과 다음 판단

586의 같은 adapter 조합에 history를 계속 추가하거나 packet/padding/opcode/로그 크기를 바꾸는 실험은 중단한다. **출력 history 구현을 끝냈다고 보고하지 않는다.** 현재 필수 구현부터 한도를 넘었으므로 나머지를 더한 전체 C안의 통과 근거가 없다. 다른 구현 전체가 수학적으로 불가능하다고도 주장하지 않는다.

다음 R2는 구현 반복이 아니라 **검사 소유권의 결정**이다. 기존 record 표현/`logical_record` 실행기를 실제 삭제하고 section 단위 수락 + 값별 의미/required-tag + canonical CRC를 하나의 ARM 실행기로 둘 수 있는지, 모든 유지 검사와 source expected 생산 비용을 대응표로 확정한다. old encoded BEGIN 재구성·중복 phase/count 검사를 남기는 안은 제외한다. 검사 삭제나 단순히1112B 전체를 공짜 절감으로 세는 안도 제외한다.

그 범위에서도 history·손상 검사·실제 stack·wire/조회·FPGA LE/M9K를 함께 맞출 근거가 없으면 C와 역할/지원 범위를 재선택한다. 현재 record protocol로 되돌리면 비용 문제가 저절로 해결되거나60Hz가 된다고 가정하지 않는다. 불변 전체 FIT와 또 다른 국소 ACK/codec 최적화는 재개하지 않는다.

제품은 MMC577을 유지한다. README·GBC/save·선택 RTL/SDC·설치 ZIP은 변경하지 않는다. PR151은 목표/작업내용/성과/후속작업 양식을 유지한다.

## 재현·실패 기록

`prepare_nes_combined586.py` → 기존 `build_nes_mmc479_arm.ps1` → `check_nes_combined586.py` → `analyze_nes_combined586.py` 순서다. 각 도구의 `--help`와 공개 JSON의 source/tool/fixture 해시를 사용한다. 원본 geometry/packet/ROM 본문은 공개하지 않는다.

ARM01은213840B였고, 최종 ARM02는 callback/RX 인자 검사 복구로12B 증가했다. 성능 변형 반복이 아니다. test01은 짧은 malformed 단일 packet을 COMMIT으로 잘못 취급한 도구 오류로 중단했고, 이를 실제 COMMIT tag 조건으로 고친 test02가 통과했다. API guard를 추가한 test03이 최종이다. 중간 빌드·실패 로그를 보존한다.
