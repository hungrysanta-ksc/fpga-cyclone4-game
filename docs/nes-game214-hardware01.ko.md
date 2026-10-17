# NES214 실기: 시작 성공, 51번째 프레임 계획 처리 중 종료

사용자는 게임 실행 후 스테이지 선택 진입 시 종료됐으며 메뉴 복귀는 정상이라고 보고했다. 세 TXT 원본은 `probes/nes-game214-hardware01/raw`에 SHA256과 함께 보존했다. [분석 결과](../analysis/game214-hardware01-verification.json). 기존214 빌드와 패키지는 변경하지 않았다.

## 확인된 결과

| 항목 | 결과 |
|---|---|
| ROM 적재·전체 비교 | 393216바이트 일치, ROM 오류 0 |
| 시작 | boot_reason=READY, 430 polls, 5 ticks(약50ms) |
| 마지막 부팅 상태 | valid=1, read flags=4, SPC=A9, stage=3 |
| 실행 구간 | DISPLAY_NEXT→DISPLAY_STOPPED 9090ms; 마지막 표시 시각8.85초 |
| 화면 완료 | 50회 표시 ACK, 마지막 generation68 |
| 다음 프레임 | generation69, geometry BEGIN/END/COMMIT 51회, ABORT0 |
| 종료 오류 | native_result=5(DISPLAY), run_first_error=4, plan_error=4 |
| 계획 진행 | locally sent batch1, plan_end=0 |
| 종료 처리 | STOP/base/menu 준비 정상, 사용자도 실제 메뉴 복귀 확인 |

**60초 제한에 도달한 종료가 아니다.** 실제 생산 RUN의 순서를 대조하면 51번째 프레임의 계획 finish/flush/상태 검증 구간에서 실패했다. 이 프레임의 SEAL·최종 표시 ACK·retire 전이다. receiver/video/sink/window 오류는 모두0이며 window sent/retired는912로 같다. 따라서 ROM 오류나 최종 SNES 표시 ACK 불일치로 판정하지 않는다.

이번 실제 정상 부팅은 read flags=4이며 리셋 벡터 관찰 bit0/1이 없다. flags=7을 정상 부팅 필수 조건으로 추가하면 안 된다. 첫 상태0도 이번에는 정상적으로 READY로 진행했다. **214는 시작 원인을 기록한 판이며, 213의 시작 실패 원인이 해결됐다고 단정하지 않는다.**

## 아직 구분할 수 없는 원인

`nes_plan_service200.c`의 오류4는 E8 응답의 헤더·버전·CRC·예약 필드, fault/retiring 상태, 수락 배치 수, descriptor 형식, flush 중 예상하지 않은 END 등을 함께 나타낸다. 최초 실패한20바이트 응답과 세부 판정 분기가 저장되지 않아 이 중 하나를 확정할 수 없다. callback 전송 실패0은 물리 전송 무결성 증명이 아니다. plan_sent=1도 ARM의 송신 기록이며 FPGA 수락1의 증명이 아니다.

버튼 기록에는 START 두 번, SELECT 두 번, A 한 번과 각각의 해제가 있다. 다른 버튼도 NES에 전달됐지만 TV 장면과 정확한 시각 대응은 없다. PPU 거절 generation49는56에서 복구됐으며 최종69 실패보다 앞선다. 이 기록만으로 화면 전환 부하, 사운드, MMC3 또는 과거 거절을 이번 원인으로 지목하지 않는다. SPC 초기화 A9는 확인되나 이번 사용자 보고에는 실제 소리 확인이 없다.

## 성능 기록의 범위

완료 구간 누적 receive2.55초/plan4.83초/seal1.49초, 전체 SPI clocked bytes808805, 최대 완료 화면 간격400ms다. budget의50완료 수와 바이트 합계는 game 로그와 일치한다. 마지막 미완료 프레임 전송도 바이트에 포함되고 실패한 finish 시간은 완료 단계 누적에 포함되지 않는다. slot_hits5594는 횟수이며 절약 바이트·실게임 캐시 적중률이 아니다. 시험이 짧고 장면이210과 달라 60fps 달성 또는 개선율을 판정하지 않는다.

## 작업 의미와 다음 순서

이번 결과는 **60fps용 슬롯 유지·변경 범위 출력 경로가 실제 게임에서50번 표시까지 진행했으며, 다음 계획 처리 경계에서 중단됐음을 확인한 작업**이다. 성능 최적화를 폐기할 근거는 없지만 60초 안정성은 아직 통과하지 못했다.

1. 기존 budget 로그에 최초 실패한 E8 응답20바이트, 세부 판정 조건과 finish/flush 단계를 보존한다.
2. 실제213 C와 선택207 RTL로 짧은 한 배치·희소 갱신, generation/END/accepted 전환을 우선 확인한다. 재현되면 원인을 수정하고 최소 결합 검증 후 다음 실기판으로 간다.
3. CRC·수락 수·내용 수명·최종 표시 검사는 유지한다. 무조건 재시도, 시간 제한 확대, 캐시 비활성화, 새 FIT 반복으로 우회하지 않는다.

동일214/044 재시험이나 추가 영상은 지금 필요하지 않다. 이번 커밋은 결과 분석과 인계이며 새 firmware/FIT/ZIP은 없다. 저장 SRAM/GBC164/기존 배포와 완료 archive를 보존한다.
