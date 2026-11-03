# 584: 실제 ARM transport 교체의 비용 판정

> 587 연결 감사: 이 문서의 입력4packet source는 시험 모델이다. 고정 MMC577 RTL은256B 단일 sealed block+96bit mailbox다. 기능 결과의 범위는 유지하며 모델 생산 일정·버퍼 여유를 보드에 승계하지 않는다. [실제 연결과 다음 판정](nes-ownership587-results.ko.md)

**transport만 바꾸는 후보는 채택하지 않는다.** 링크된 MMC577 ARM 코드에서 D0/D2/E0/E8 호출을 제거했지만, 시험 전송량이 증가했고 Flash는 배포 한도를 360B 초과했다. 255–256B 입력 payload도 기존 SPI 드라이버 한도와 맞지 않는다. 실기 기준은 MMC577 그대로이며 새 ZIP은 없다.

[검증·해시·비용](../analysis/transport584-verification.json) · [현재 계획](nes-retrospective579-plan.json) · [앞선 583 조사](nes-row583-results.ko.md)

## 실제로 교체한 경계

577 전체 소스를 복사한 비배포용 ARM02에 다음 일곱 파일을 교체해 전체 링크했다. 제품 선택 소스와 FPGA는 변경하지 않았다.

- `nes_native165.c/.h`: D0 조회/D1 본문/D2 ACK/D3 준비를 DC ACK+peek, DD 본문, DE 준비, DF 마지막 입력 ACK로 교체했다. epoch·serial·generation·packet token·길이·CRC를 확인한다. **기존 record 압축/해석은 유지**했으며 583 행 codec은 포함하지 않았다.
- `nes_native_runtime165.c/.h`: E1/E9 제출 응답과 EC 조회의 공통 50B snapshot을 검사하고 window/plan에 공급한다. snapshot은 명령 수락 전 상태이며 E9 뒤에는 이전 plan-ready를 다시 쓰지 않는다. BEGIN identity 변경·EA·오류 때 cache를 무효화한다.
- `nes_sink_window184.c/.h`: E0 조회·CRC8을 제거하고 공통 accepted/retired/ACK를 소비한다. 4credit과 기존 ACK identity 검사를 유지한다.
- `nes_plan_service200.c`: E8 전송을 제거했다. 다만 공통 응답을 기존 plan/bulk 의미 필드로 변환하는 어댑터가 남아 있다.

DC/DE/DF는 36B, DD는 payload+5B다. E1/E9는 50B snapshot과 prefix 때문에 최소 52B가 된다. E1/E9의 원본 호출 버퍼 뒤까지 덮어쓰지 않도록 runtime에 261B 임시 송수신 버퍼를 두었다. 이 복사는 현재 serializer가 보존하는 E9 뒤의 미발행 suffix와 관련돼 있어 단순 제거할 수 없다.

## 실행 범위와 결과

선택은 `probes/nes-transport584/patch02`, `ARM02`, `test07`이다. 실제 링크 ELF의 M4 명령을 실행해 951/954의 입력 전체와 각각 실제 plan 7개를 통과시켰다. source 4packet ring과 출력 4credit 소비 지연은 유한 endpoint 모델이다. 서비스 지연 128/12000은 민감도 설정이며 **두 ROM 시작 위상이나 실측 시간은 아니다**.

| 입력 / 서비스 지연 | SPI 호출 577→584 | 전송 B 577→584 | 실행 M4 명령 577→584 |
|---|---:|---:|---:|
| 951 / 128 | 86→57 | 4466→5307 | 378950→332198 |
| 951 / 12000 | 118→69 | 5034→5883 | 428820→343769 |
| 954 / 128 | 88→59 | 4490→5401 | 380499→334575 |
| 954 / 12000 | 120→71 | 5058→5977 | 430120→346594 |

입력 호출은 53→33 또는 59→36회다. E0+E8의 22–49회는 EC 13–23회로 바뀌었다. 각 정상 실행에서 실제 공통 진행 함수의 cache hit는 window 8회·plan 9회였다. 나머지 조회 감소에는 더 긴 전송 동안 모델 생산/소비가 진행된 효과도 있으므로 전부 cache 절감으로 귀속하지 않는다. 전송량 증가 841–919B는 조회 횟수 감소만으로 성능 개선을 판단하면 안 되는 이유다.

입력 배열/512B raw의 byte 일치, source 최종 packet 반환이 EA보다 빠름, 선택 plan 동일성, token/sequence wrap, 4packet/4credit 포화를 확인했다. 일반 출력 시험의 최대 점유는 1이며 별도 5packet 압력 시험에서 4credit을 채우고 drain했다. **2슬롯 staging RTL 시험은 아니다.**

18개 거절 조건은 source CRC/epoch/token, header/body 뒤 STOP, 조기 COMMIT endpoint 거절, snapshot CRC/epoch/generation/sequence, 미래 credit, 잘못된 ACK, E1/E9 뒤 STOP, 불확실한 E1 완료, 최종 ACK 부재, 255/256B payload 드라이버 거절이다. 실패 뒤 endpoint의 늦은 완료가 발생해도 추가 SPI/EA를 발행하지 않았다. 조기 COMMIT은 endpoint 거절에 대한 ARM 반응이며 실제 동시 세대 중재 검증은 아니다. 최종 표시 허가는 모델에서 부여했다. 실제 65816·VBlank·화면·메뉴 복귀를 새로 검증한 결과로 쓰지 않는다.

## 전체 링크와 저장 비용

| 항목 | MMC577 | 584 | 차이 |
|---|---:|---:|---:|
| firmware.stm | 212908B | 213352B | +444B |
| 배포 한도 212992B 대비 | 84B 여유 | 360B 초과 | 부적합 |
| ELF BSS | 18592B | 18676B | +84B |
| 시험 관측 stack | 808B | 1064B | +256B |

실행 section 합으로 `native` −40B, `runtime` +542B, `window` −102B, `plan` +44B이며 합계 +444B가 실제 펌웨어 증가와 일치한다. 호출·CRC8 삭제 효과보다 identity/cache/버퍼/어댑터 비용이 크다. 링크 성공은 설치 용량 통과를 뜻하지 않는다. linker의 영역이나 배포 cap을 늘리지 않았다.

시험 workspace에는 실제 전역 runtime 외에 별도 시험용 runtime·palette·송신 fixture가 있다. 남은 시험 stack gap 3056→2648B는 전체 RUN/IRQ stack 여유가 아니다. 실제 IRQ·ROM 경쟁·GPIO/SPI/DMA 드라이버 명령은 실행하지 않았다.

### 실제 드라이버의 259B 경계

변경하지 않은 `nes_native165_bulk.inc`는 `count>259`를 거절한다. 951/954 정상 시험의 최대 전송은 259B이며, 시험 callback에도 이 한도를 적용했다. 그러나 새 parser는 payload 256B까지 허용해 DD 260/261B가 필요한 255/256B payload를 받으면 실패한다. 해당 두 조건의 안전한 거절을 확인했지만 **호환성 통과가 아니다**. 그 두 값이 현재 source에서 도달하지 않는다는 전체 producer 증명도 하지 않았다. 드라이버 한도만 늘려 해결한 것으로 처리하지 않는다.

## 일정 해석의 정정

현재 선택 577의 `nes_runtime165_step`은 입력→계획·출력→SEAL/최종 ACK→EA→consumed 뒤 다음 입력 poll을 실행한다. 마지막 입력 ACK 이후 source capture는 진행할 수 있으나 ARM이 표시 대기 중 다음 입력을 받는 구조는 현재 경로에 없다. 과거 498의 입력 선행 구조를 현재 기능으로 가정하지 않는다.

source input-COMMIT의 base identity와 최종 표시 ACK의 bank history는 별개다. 다음 세대의 동시 수신·COMMIT을 도입하려면 old EA 이후 새 COMMIT, STOP drain과 늦은 완료 차단을 다시 실제 경계에서 증명해야 한다.

## 판정과 다음 단일 gate

R2는 구조 재검토 상태이며 R3는 선정하지 않는다. 이번 실패로 필요한 범위가 명확해졌다. transport를 기존 parser/plan 변환에 덧대는 대신 **section/row 본문 해석, 공통 진행 필드의 직접 소비, SPI RX 버퍼 소유권을 함께 교체**해야 한다.

다음 순서는 아래와 같다.

1. 현재 native decoder와 plan 응답 변환에서 실제 삭제할 함수·필드, source base/producer 이력과 독립 검사 보존 범위를 고정한다. 본문 codec과 transport를 합친 순 Flash 증가를 84B 이내로 제한한다. 기존 583 커널 248B를 공짜로 계산하지 않는다.
2. 259B driver, E9 suffix, 4credit, source ring, 실제 2슬롯 staging, epoch/serial/ACK 소유권의 포트·버퍼 표를 작성한다. RAM/stack 및 C안 producer nonmap 이력 최악 8948B·retained integrity 비용을 포함한다. 저장 구조가 맞지 않으면 역할·지원 범위를 수정한다.
3. 삭제·바이트·저장 예산이 성립한 한 후보만 실제 ARM 전체 링크로 연결한다. 실제 IRQ/ROM/65816 및 두 시작 위상은 그 후보에 연결해 검증한다. 현재처럼 전송량 증가·Flash 초과인 안에 FPGA/전체 FIT를 먼저 반복하지 않는다.

기존 record codec을 유지한 584의 padding/poll 크기 변형이나 Flash 로그 축소는 다음 작업으로 삼지 않는다. MMC577·독립 검사·STOP·최종 ACK·VBlank·메뉴 복귀·GBC/save의 선택 산출물은 유지한다.

## 재현과 보존

`prepare_nes_transport584.py --src <ARM577/src> --out <새 patch>` → `build_nes_mmc479_arm.ps1 -Base <ARM577> -Patch <patch> -Out <새 ARM>` → `check_nes_transport584.py` → `analyze_nes_transport584.py` 순서다. 마지막 두 도구의 `--help`에 입력 경로 인수가 있으며 기존 581 봉인 fixture와 489 plan을 사용한다. 공개 JSON에는 해시·계수·비용만 넣고 ROM에서 유래한 본문·packet은 공개하지 않는다.

ARM01의 미사용 crc8 컴파일 실패, test01의 951 BG 존재 가정 오류, test02의 Python bytes 변환, test03의 임의 workspace 상한 오류 및 중간 test04–06을 보존한다. test07은 실제 259B 한도와 18거절을 적용한 최종 검사다. analyzer 최초 실행의 라이브러리 경로 오류는 기존 bootstrap import로 수정했다. 제품용 FPGA/profile과 호환되지 않는 ARM02는 설치하지 않는다.
