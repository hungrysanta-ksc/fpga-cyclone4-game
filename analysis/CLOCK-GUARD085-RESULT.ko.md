# NES085: 단일 클록 정지 시 PSRAM 핀 차단

## 작업 목표

CF68의 `locked=HIGH` 입력 클록 정지 반례 중 **다른 입력 클록이 계속 동작하는 경우**에 한정하여, 실제 PSRAM 핀 차단·이미지 무효화·자동 재무장 방지를 구현하고 검사한다. PR35의 병합과 master `bf29565e94fd9d63a57b013764dc4f612c710986`에서 기존 head 도달을 확인하고 새 브랜치에서 진행했다.

## 작업 내용

085는 별도 입력 클록을 이용한 단일 클록 정지 차단을 실제 진단 핀 셸에 연결했다. 디지털 GPIO4경우/정지128경우/인과 대조3개를 통과했으며 검출 최대4.374µs, CE LOW 최대3.350µs다. 두 클록 동시 정지 반례는 남는다. 새 fit/STA·실제 기준 클록 가용성·최신 MCU 쌍/전체 세션·실기는 미완료이며 설치 파일은 없다. 084 저장/화면/정상044복원·메뉴/GBC 성공은 유지한다.

새 CF85 top이 A9/SNES_SYSCLK와 CLKIN을 상호 감시하며 기존 비동기 memory reset을 사용한다. 두 영역의 각8회 변화 확인 이후에만 기존1600주기 초기 대기를 시작한다. 한쪽 클록이 처음부터 없거나 실행 중 멈추면 접근을 막고, raw lock loss/재구성 전에는 fault를 유지한다. 기존 CF68·044/GBC·084 소스와 동결 기록은 보존한다. 구현·가정·재현·인계는 [계약](../docs/nes-clock-guard085-contract.ko.md)에 기록했다.

## 작업 결과

정의한 **단일 고장의 디지털 연결 검증 목표는 달성**했다. P2 전체 및 실기 진입 목표는 아직 달성하지 않았다.

| 검사 | 결과와 한계 |
| --- | --- |
| C GPIO 적재/검사 | 20MHz 기준에서 load256byte/CHECK256byte, 추가 약21.477/22MHz load 회귀. 총130360응답 비트 일치. CHECK96KiB 사전 적재는 TB 입력으로 실제 핀에 쓴 것이며 전체 C SPI 적재 아님 |
| 단일 정지 | 4실행 × 읽기/쓰기2 × 정지 클록2 × 위상8 =128경우. 최대 검출4374.000ns, 최대 CE LOW3350.000ns. 수치는 RTL 디지털 모형 값이며 routed/실기 값 아님 |
| 기동/재개 | 기준 클록 부재, 메모리 클록 부재, 클록 재개만으로 fault가 지워지지 않음, raw lock reset 후 재초기화, 저장 SRAM 비활성, RUN 차단 통과 |
| 인과 대조 | guard 연결 제거는 SINGLE_CLOCK_HALT_NOT_CONTAINED, 같은 입력으로 reference 대체와 sticky 제거는 STARTUP_FAULT_NOT_STICKY에서 의도한 실패 |
| 공통 원인 고장 | 두 클록 정지·locked HIGH에서 CE LOW9µs 반례 유지. raw locked LOW는 클록 없이 핀 해제. 성공으로 감추지 않음 |
| 보존 | 변경 없는 CF68 생성파일13개 해시 일치. 새 top/ID/감시 회로에는 과거068 fit/STA를 재사용 승인하지 않음 |

첫 normal01은 통과했으며, 최종 normal02는 CE 시간 monitor·기동 메모리 클록 부재·C-prefix와 후속 고장쓰기 수량 분리를 추가했다. 생산 RTL은 두 실행 사이 동일하다. 실패 대조 원시 로그, 실행본과 정상 두 회차를 새 archive에 함께 보존했다. 컴파일 오류/경고0, 실제 FLOAT 실행 종료를 확인한다. 기존 별도 reference 없는068 시험의 기대값을 바꾼 것이 아니다.

새 Quartus fit/STA/ASM/ARM/사용자 실기는 수행하지 않았다. FPGA 자원 비용도 아직 산정하지 않았다. 기존 GPIO 기록은 private060 입력이므로 공개 clone 단독 재현을 주장하지 않는다. 원시 근거는 로컬 `probes/nes-clock-guard085/evidence/` 471파일, manifest `aec4aabee2f45eeaf1bec3cb353d8501c629369513482e471477a4ccf6f320d0`이며 [검증 메타데이터](clock-guard085-verification.json)와 `verify_nes_clock_guard085.py`로 감사한다.

다음 목표는 RESET-held 기준 클록의 가용성/독립성을 기존 base 측정 경로와 대조하고, CF85 동일 소스의 fit/STA·CDC·비동기 차단·외부 지연과 두 클록 동시 고장 정책을 정리하는 것이다. 그 뒤 최신 MCU 승인 ID·전체80/96KiB 세션·동일 파일 쌍·복원/실기 관측을 연결한다. 기존 저장 시험이나 부품 수집을 다시 요청하지 않는다. 준비도4완료/7부분/1미완료, `installable=false`를 유지한다.
