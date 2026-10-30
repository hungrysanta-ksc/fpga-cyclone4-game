# NES485 — 첫 BG 발행과 bulk 소비/ACK 소유권

> 후속 실기 수신: [486 분석](nes-hardware486-results.ko.md). 대기13.55fps/첫 레벨 플레이 포함8.22fps, 정상 메뉴 복귀 확인. 아래 미실기/대기 표현은 제작 시점 기록이며 전체 가속은 미입증이다. ZIP·구성 JSON은 제작 당시 그대로 보존했다.

기준은 [484 ARM](nes-game484-planner.ko.md)과 실기에서 동작한 FPGA482/profile7b다. [485 검증](../analysis/supply485-verification.json)·[실기 비교 안내](nes-mmc485-trial.ko.md)를 함께 본다. FPGA/wire/65816 ABI는 바꾸지 않았다. **485의 실제 전체 시간·FPS 개선은 아직 미측정**이며 기존482의14.60fps가 현재 기준이다.

## 연결한 경로

1. RAW/zero 계획 뒤 첫 BG 계획을 넣으면 기존248B buffer를 즉시 flush한다. 이후 계획은 같은 buffer에 모으며, 각 emit 기회에 E8 상태를 한 번 확인한다. 계산 중 busy 상태를 반복해서 기다리지 않는다.
2. E8 descriptor는 기존 generation·kind·length·offset·token 검사와 CRC를 거친다. 새 `nes_sink195_submit`은 op7을 기존4credit window에 복사하고 반환한다. 소프트웨어 내부 selector23은 packet 생성 전에7로 바뀌며, wire에 새 명령23을 보내지 않는다. 기존 blocking `nes_sink195_bulk` API도 유지한다.
3. ARM은 마지막 descriptor12B와 pending 상태를 보유한다. 같은 token/동일 descriptor는 재발행하지 않는다. 같은 token의 필드 변조와 이전 token은 실패한다. 다음 descriptor 제출 전 이전 op7의 실제 matching ACK를 drain한다.
4. finish는 END와 producer 완료뿐 아니라 마지막 bulk의 실제 ACK까지 확인해야 성공한다. 그 뒤 기존 독립 manifest/coverage·SEAL/표시 ACK·resident commit·EA/재시작 순서를 따른다. display ACK 전에 retire할 수 없으며, retire가 확인된 뒤에만 early/descriptor 문맥을 지운다.
5. 실패·STOP·불확실한 전송은 terminal이다. 재시도하거나 미완료 ACK를 성공으로 만들지 않는다. 기존 공통 STOP/reset과 base/menu 복구가 소유권을 닫는다. staging은 FPGA의 실제 SNES consume/token 경로가 해제한다.

## 반복 대기를 함께 바꾼 이유

초기 candidate01/ARM01·라벨만 바꾼ARM02는 기능/픽셀 시험을 통과했지만, instant-host-C 시험에서 E8가23회였던 이전 기록에 비해221회로 늘었다.197회가 descriptor 없는 busy였다. 먼저 보낸 작은 packet 뒤, 다음 packet을 채운 호스트가 ROM 생산 완료를 빠르게 재조회한 것이다. 이 버전은 전달하지 않는다.

최종 candidate03/ARM03은 실제로 credit/생산 완료를 기다리는 flush·finish 반복에 기존 window의 **128µs guard 대기**를 재사용한다. 각 확인/진행/완료 판단은 유지한다. IRQ·fault·deadline 서비스는 대기 중에도 실행한다. 계산 중 emit의 기회성 확인에는 이 대기를 넣지 않는다. 기존 CREDIT quiet counter에 plan 대기도 포함되므로 수신 로그 해석에서 구분 없이 별도 시간으로 더하지 않는다.

이 대기를 넣은 C 결합 시험에서는 실제 DWT가 없으므로128µs를 RTL 시간으로 명시적으로 전진시킨다. 이는 ARM/IRQ 실행 시간을 흉내 낸 결과가 아니다. 이전 host 시험과 polling 횟수를 물리 성능 개선율로 비교하지 않는다.

최종 live02의 E8는96회·E0는63회·E9는3회다. 이전480의 instant-C 기록23/90/2회와 달리 이번에는 quiet 시간을 모델에 넣었고 실제 M4 계산 시간은 양쪽 모두 반영되지 않았다. E8가 초기 연결안221회보다는 줄었지만 **전체 전송/시간이 기존보다 좋아졌다는 근거는 아니다.** 계산을 진행하는 동안 ROM 생산을 얼마나 숨기는지는 실기 DWT로 판정한다.

## 실제로 확인한 범위

- 실제 링크된 M4 plan/window/packet/CRC 코드를 실행해 RAW→첫 BG의 선행 E9, 계산 중 bulk 제출, 중복 descriptor 억제와 지연 ACK를 확인한다. 두 generation의 owner 재시작과 최종 표시 grant 전 retire 차단도 검사한다.
- 잘못된 E8 CRC/generation, 같은 token 변조·이전 token, ACK/accepted counter 오류, E9 후 STOP·bulk 후 STOP·불확실한 E1 전송을 거부한다. 시험 endpoint와 DWT 시계는 모델이며 실제 IRQ/ROM 타이밍 증명이 아니다.
- 전체 C runtime은 실제482 board/NES·SPI bit 전송·70ns PSRAM 모델·ROM 중재와 연결한다. 실제65816이34개 ACK·bulk2개 소비·VRAM4416B·최종 표시·STOP을 완료하는지 검사한다. NES PPU 원본57344픽셀과 SNES 표시를 전부 비교한다.
- Lua의 VBlank 공개·표시 후 DMA·최종 ACK 위치 검사를 유지한다. cold1회 표시의 기능 증명이며 지속60Hz·warm 한 VBlank 처리량·capture 무손실의 증명은 아니다.

## 예산과 남은 판단

484 대비 ARM text+400B·BSS+20B, data10040B/RUN31848B는 유지하며 새 payload buffer는 없다. 소유권 state20B는 무료 RAM으로 처리하지 않는다. 기존384B 후보 예산을16B 넘었으며,64B가 추가된 guard 대기는 발견한 busy-spin을 없애는 데 필요했다. 실제 Flash는232B 남는다. 전체 stack/IRQ 상한은 미증명이다.

FPGA는482 bitstream 그대로다. 기존 whole Lite15254/15408LE·14049comb·8392FF·256608bits,154LE 잔여를 재사용한다. 회로/PLL/SDC를 바꾸지 않았으므로 같은 합성을 반복하지 않는다. raw reset/CDC/IO의 기존 미완료 항목은 그대로다.

호스트 C와 Mesen/RTL은 실제 M4·IRQ의 공통 물리 시계로 실행되지 않는다. 따라서 이번 기능 결합의 시뮬레이션 종료 시각이나 M4 명령 수에서 새 FPS를 만들지 않는다. **요청한 실제 ARM·SPI·IRQ·ROM 경쟁을 포함한 전체 시간의 최종 판정은 MMC485 실기 로그가 필요**하다. 기존 DWT schema474가 수신/계획·공급/SEAL·최종 ACK와 실제 driver/IRQ/guard 대기를 기록한다.232B Flash 여유 안에서 새 계측을 늘리지 않았다.

현재482의68.4835ms/표시·60Hz까지51.8168ms 차이는 새 측정 전까지 그대로다. 다음 순서는485의 완료 프레임/전체 시간/단계 비용/전송량·STOP/메뉴 복귀를 먼저 비교하고, 그 결과로 수신17.16ms와SEAL18.44ms 병목을 다시 정하는 것이다. 입력·장면과 종료 미완료분 차이를 함께 보고, 계획 단계의 시간 이동만 성과로 계산하지 않는다.

## 선택·재현

공개 recipe는 `tools/prepare_nes_supply485.py`, 실제 M4 검사는 `check_nes_supply485_arm.py`, 기능 결합은 `test_nes_supply485_live.py`, 결과 집계는 `analyze_nes_supply485.py`, 실기 수신 분석은 `analyze_nes_supply485_hardware.py`다. 빌드는 기존 `build_nes_mmc479_arm.ps1`을 사용한다.

로컬 선택은 `probes/nes-supply485/candidate03`, `ARM03`, `armguard07`, `executed/live02`, `pixels02.json`, `trial02`이다. trial01은 같은 firmware의 JSON 줄끝 정규화 전 package로 보존했다. 처음의 함수/픽셀 통과와 polling 악화 기록은 `executed/live01`, 누락 DWARF/DWT mapping 등 harness 실패는 armguard01/05에 보존한다. 원본 firmware·ROM·source/trace·로그·라이선스를 Git에 추가하지 않는다. 단일 Questa FLOAT 좌석을 순차 사용한다.

실기 설치본은 새 파일명 MMC485, 정상482와476/164/467 원복을 포함하며 원복·FPGA는 기존 바이트와 대조한다. 아직485가 빨라졌다거나 메뉴 복귀까지 확인됐다고 표시하지 않는다. 사용자 설치 방식은 [실기 안내](nes-mmc485-trial.ko.md)를 따른다.
