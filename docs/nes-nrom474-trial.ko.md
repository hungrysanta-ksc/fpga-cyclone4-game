# NROM474 설치·비교 시험

471에서 정상 동작한 **동일한 이동 ROM과 동일한 FPGA bitstream**을 사용한다. ARM의 반복 BG 계획과 진행 없는 상태 조회 비용을 줄인 후보다. 이번에도 약60초 RUN 뒤 STOP·base 복구·메뉴 복귀를 확인한다. 적재/readback의 몇 분은 RUN 성능 시간과 별도다.

## 설치와 확인

1. 전원을 끄고 기존 SD와 저장 자료를 PC에 백업한다.
2. `01-NROM474-MOVING-SD-ROOT` 안의 내용을 SD 루트에 덮어쓴다. firmware와 함께 **fpga_nrom474.bi3**, nes/nrom474.nes를 복사한다. FPGA 내용은471과 같지만 새 firmware가 찾는 파일명은474다.
3. **NES NROM 474.nh1**을 실행한다. 기존471/227 항목과 구별한다.
4. 이전처럼 막대 이동, A 누름의 붉은색 유지와 해제 후 파란색, 약60초 자동 메뉴 복귀를 본다. 가능하면 메뉴 복귀 후 같은 항목을 한 번 더 실행한다.
5. 오류·정지가 있으면 경과 시간과 마지막 화면을 기록한다. BLOCKED_RESET_HELD를 강제로 해제하지 않는다.

## 가져올 로그

- sd2snes/nes-progress-nrom474.txt
- sd2snes/nes-budget-nrom474.txt
- sd2snes/nes-game-last-nrom474.txt

가능하면 동작 영상을 함께 보내준다. 같은 이름은 재실행 시 갱신되므로 실행별로 PC의 moving-1/moving-2 폴더 등에 보관한다. 이번 기본 ROM은471과 byte 동일, CRC32 `0fddf31c`이므로 이전 평균19.61fps/정상 구간 약20fps와 같은 장면으로 비교할 수 있다. 새 FPS는 이번 실기로 판정하며30/60fps를 미리 선언하지 않는다.

정적 기준도 시험하려면 이동 로그를 먼저 PC에 보관하고 `03-STATIC-COMPARE-SD-ROOT`의 ROM만 덮어쓴다. 이 ROM은 기존428과 byte 동일하며 CRC32 `6ce6835a`다. 실행 항목과 로그 이름은474로 유지한다. 이동 장면 복원은01의 ROM만 다시 복사하면 된다.

## 바뀐 부분과 계측

동일 프레임 안의 완전히 같은33열 BG 그룹은 이미 검증·배정한 슬롯을 재사용한다. 예외 raster는 기존 경로를 쓰고, 서로 다른 첫4그룹에서 재사용이 없으면 비교를 중단한다. 이전 프레임을 추측해 재사용하거나 독립 검사를 생략하지 않는다.

E0의 첫 조회와 완료 검사는 즉시 수행한다. 진행 없는 응답 뒤에는 nominal128us 동안 기존 fault/deadline/service guard를 계속 확인하고 재조회한다. IRQ/service 때문에 실제 간격은 더 길 수 있으며 실제 누적·최대 cycle을 로그에 기록한다. credit 반환과 최종 표시 ACK의 의미는 유지한다. DWT가 사용 불가하면 기존 즉시 조회로 돌아간다.

`cost_schema=474`에서 E1/E9 opcode를 전송 전에 저장하므로 이전 OTHER 합산 오류를 수정했다. `cost_poll_order=CREDIT,DRAIN,FINAL_ACK`의 valid 응답·진행/완료·quiet 대기와 group 재사용 수도 추가했다. phase·opcode·quiet 시간은 중첩되므로 서로 더하지 않는다. `cost_counter_available=0`일 때 cycle을 시간으로 해석하지 않는다.

## 복원

전원을 끄고 **02-RESTORE471-SD-ROOT** 내용을 SD 루트에 복사하면 직전 실기 정상 조합471로 돌아간다. 그때 실행 항목은 NES NROM 471.nh1이다. 04는 보존164, 05는 이전467 복원물이며 필요할 때만 사용한다. 상용 ROM·사용자 저장 파일은 전달본에 포함하지 않았다.

## 결과의 범위

실제 링크된 M4에서 정적·이동 입력의 계획 명령 수와 슬롯 계획·bank 상태를 비교했다. 반복 그룹의 계획 명령은 약69~72% 줄었고, 독립 renderer129장면·credit4/ACK/CRC/STOP·회복 및 실제 NES/source→ARM C→65816 DMA/VBlank→최종ACK→STOP 회귀를 확인했다. 명령 수와 모델 polling 감소는 전체 실기 FPS가 아니다.

FPGA는471 bitstream 그대로14740LE/13672comb/8063FF/185824bits다. 실제 nominal 관련 clock setup+0.081ns/hold+0.143ns, 강화 예산−0.036ns와 raw CDC/미제약IO의 한계도 그대로다. 새 Quartus 합성 결과나 장시간/전체 IO signoff로 표현하지 않는다.
