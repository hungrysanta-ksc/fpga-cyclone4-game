# NES215 최초 계획 상태 오류 보존

## 작업 의미

60fps용 변경 타일 출력 경로가 실제 게임에서 조기 종료되는 원인을 구분한다. 214에서50표시 후51번째 계획 완료 중 발생한 error4는 CRC, FPGA fault, 배치 수, END 상태 등 여러 조건을 합쳤다. 이번에는 그중 최초 실패 조건과 실제20바이트 E8 응답을 보존한다. 재현·원인 수정이 확인되기 전에는 수정 완료로 선언하지 않는다.

`tools/nes_plan215.py`는 동결된214 ARM 입력을 해시 검증해 새 출력 디렉터리에 복사한다. 기존200 소스와214 archive를 편집하지 않는다. 변경은 계획 오류 보존, 새 실행 시작 시 보존 정보 초기화, budget 포맷,215 식별자다. FPGA·SNES client·resident/planner/RUN 동작·기존 저장 시점은 그대로다.

## 기록과 수명

`nes_plan215`는30바이트 구조체다. 전체 ARM 정적 할당은 정렬 포함32바이트 늘어난다. 정상 poll에서는 원본 응답 복사나 추가 SPI를 하지 않는다. 최초 오류4에서만 sent/generation/보류 bytes/count/phase/reason/reply20B를 저장한다. 이후 오류·budget reset·종료 처리로 덮지 않는다. 새 부팅 진입 때만 초기화한다. `valid=0`이면 오류4 응답이 보존되지 않은 것이며 모든 종류의 오류가 없다는 뜻은 아니다.

| phase | 경계 |
|---|---|
| 1 | 보류 계획 flush 전 상태 검사 |
| 2 | END 전송 후 finish 대기 |
| 3 | 최종 표시 확인 후 retire 전 |
| 4 | retire 명령 후 재개 대기 |

| reason | 최초 실패 조건 |
|---|---|
| 1 | 헤더 D7 또는 버전4 불일치 |
| 2 | poll 예약 바이트18이0이 아님 |
| 3 | CRC8 불일치 |
| 4 | 허용하지 않은 상태 비트: 원본 byte3으로 fault/retiring 등 구분 |
| 5 | FPGA accepted와 ARM sent 불일치 |
| 6 | descriptor 존재 표시가0/1 이외 |
| 7 | descriptor 없음/retire 상태인데 예약 영역이0이 아님 |
| 8 | 보류 계획 flush 도중 예상하지 않은 END |
| 9 | retire 직전 END/accepted 조건 불일치 |
| 10 | retire 이후 재개 상태/accepted 조건 불일치 |

검사는 기존 순서를 유지한다. 여러 조건이 동시에 틀리면 최초 조건만 reason으로 기록하지만 reply 전체는 남긴다. `plan_expected_sent`는 FPGA 수락 확인치가 아니라 ARM의 예상치다. fault 비트만으로 FPGA 내부 어느 모듈이 원인인지 확정할 수는 없다. boot214 기록도 계속 유지한다.

## 검증 범위

- 실제 이전200과215 C를 함께 컴파일해 정상 및 E8 전체20바이트의 비트 변형/CRC 재계산 유무/flush·finish·retire·rearm1600조합에서 반환값·오류·송신 수·SPI 호출 수가 일치한다. 최초 기록 유지 및 budget reset 이후 보존도 검사한다. SPI와 SNES 소비 ACK는 fixture다.
- 실제 부팅 함수11조건에서 새 시도 시작 시 계획 기록 초기화, 기존 READY/실패 경로·기록 수명·포맷 경계를 검사한다.
- 실제 C 계획 서비스와 선택207 RTL의 SPI/lease/READ16/직접 출력 연결에 zero-only, 희소 슬롯, identity/비identity/교차타일/OBJ마스크, 배치 경계, generation wrap을 준다. SNES 소비·표시 ACK는 명시적 모델이며 실제 게임·PPU·물리60fps 시험이 아니다. 전체 결과는 선택한 RTL 시험 result.json을 기준으로 한다.
- 전체 ARM 링크: firmware207536B/static27868/RUN32096/IRQ508/보수적 여유4952B. budget최대2782/4096; 기존gameTXT4047 상한 유지. 실제 스택 고수위 측정은 아니다.

기존 시간 제한·CRC·accepted·수명·표시 ACK·STOP을 유지한다. 자동 재시도/캐시 해제/실행중SD쓰기/새 FIT/ASM 없음. 정상 경로 성능 향상을 주장하지 않는다. 213 시작 실패 원인은 여전히 미확정이며 실제214 정상 부팅 read flags4를 flags7로 강화하지 않는다. 저장 SRAM/GBC164/기존 배포와 완료 archive를 보존한다.

NEXT:215 실기에서 stage selection/첫레벨 진입, 세 TXT와 메뉴 복귀 확인. 실패하면 phase/reason/raw E8에 따라 해당 한 경계를 수정하고, 정상60초면 첫레벨 스크롤16.67ms 예산 측정으로 복귀한다. 동일214/044 반복이나 포괄적인 FPGA 재배선 작업부터 시작하지 않는다.
