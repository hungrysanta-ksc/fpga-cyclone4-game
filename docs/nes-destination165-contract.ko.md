# NES165 로더 목적 상태별 전이

## 목표와 구현

165 영상 경로 진척: 로더의 공통 상태 선택을 목적 상태별 병렬 전이식으로 분리했습니다. BEGIN→상태는−0.136ns/7단에서+0.331ns/6단으로 개선됐고 실제 상태 레지스터4개를 확인했다. 전체15022LE/963LAB/35M9K, 최악−0.160ns(command[6]→pending_causes[1])로 기존 선택−0.083ns보다 나빠 미채택이다. remaining→loaded_bytes−0.123ns, byte_count→command−0.109ns, state→error_code−0.031ns도 남아 한 경로만의 문제가 아니다. 선택 phaseguard165/map01/reproduce01; 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

이전 [COMMANDPULSE map02](nes-commandpulse165-contract.ko.md)는 응답→BEGIN과 STOP 경로를 통과했지만 BEGIN→state.WRITE에7단 LUT/−0.136ns가 남았다. 이번 후보는 그 실험 회로에서 로더1개만 바꾸고 SPI 등 나머지60개 구현 입력은 그대로 유지한다. 이전 실험을 이미 채택한 기준으로 간주하지 않으며, 채택 비교는 기존 phaseguard의−0.083ns를 대상으로 한다.

RECEIVE/WRITE/HOLD/READY/RUN/FAILED/SETUP/RELEASE 각 목적 상태의 조건을 독립적으로 계산하고 마지막에4비트 코드로 조합한다. IDLE은0이며 미사용9..15 상태는 오류·명령 충돌이 없으면 기존 값을 유지한다. 오류가 이미 잠긴 WRITE/HOLD는 STOP이 함께 들어와도 쓰기 펄스를 배출한다. 새 오류가 들어오는 클록의 우선순위, timer/count/data/error_code 소유권과 외부 PSRAM 핀 동작은 바꾸지 않는다.

클록 주기·SDC·false path·multicycle 예외·핀 배치·명령 지연은 변경하지 않았다. SPI C0/C1/C2·ID0x74·valid-only payload·SS high/setup2µs 계약과 설치164/GBC/세이브 SRAM 보호를 유지한다. MCU 설치용 연결은 아직 하지 않았다.

## 검증

- 모든16개 숫자 상태 코드를 포함한294,912조건에서 기존 레지스터·출력과 같은 클록 결과를 비교했다.
- 실제 BEGIN/1바이트 쓰기 이후132개 시점에 STOP·각 명령·충돌·commands_blocked·리셋 등을 넣는1,056개 시퀀스가 통과했다.
- 오류와 STOP이 겹칠 때 배출을 막는 잘못된 회로, 미사용 상태를0으로 덮는 잘못된 회로를 각각 검출했다.
- 새 로더와 실제 SPI/boot/READ16을 함께 실행해219개 wire 프레임/1,125,909클록/100읽기·7ACK·19주소 손상·72취소·2우선순위 충돌이 통과했다.
- 변경 없는 SPI393,741거래/120취소/3negative와 실제 MCU 전송 간격의 소스 근거는 hash로 묶어 재사용했다. 로더 및 결합 시험은 이번에 새로 실행했다.
- 61개 구현 입력 중 로더1개 변경/60개 불변, 독립 생성 바이트 재현, 지역 reset 해제4레지스터/12setup·hold 경로를 확인했다.

일부 초기 상태·READY/count를 주입하는 시험이며 전체 ROM 쓰기·게임·MCU 실행·물리 SPI 계측은 아니다. 변하지 않은 전체 ROM 적재와 A/B/044 시험은 반복하지 않았다.

## 결과와 한계

|항목|결과|
|---|---|
|자원|15022LE / 963LAB / 35M9K|
|실제 최악 setup|-0.160ns|
|최소 hold|+0.147ns|
|실제4클록·3조건198행|미통과|
|BEGIN→상태|+0.331ns|
|CHECK 오류→상태|+0.009ns|
|타이머→상태|+0.212ns|
|상태→오류 코드|-0.031ns|
|배치된 상태 레지스터 수|4|
|채택|False|

BEGIN→상태는−0.136ns/7단에서+0.331ns/6단으로 개선됐고 실제 상태 레지스터4개를 확인했다. 전체15022LE/963LAB/35M9K, 최악−0.160ns(command[6]→pending_causes[1])로 기존 선택−0.083ns보다 나빠 미채택이다. remaining→loaded_bytes−0.123ns, byte_count→command−0.109ns, state→error_code−0.031ns도 남아 한 경로만의 문제가 아니다.

더 엄격한 배치 목표와 원래 실제 클록 분석은 별도로 보존했다. 전체 외부54입력/57출력·영상CDC/reset/MTBF와 MCU full-link/stack은 미완료이며 내부 타이밍 통과만으로 실기60fps를 의미하지 않는다.

## 다음 작업과 의미

선택 phaseguard165/map01/reproduce01은 유지한다. destination165/map01은 상태 경로가 개선된 구조 검토용이며 채택·배포 기준이 아니다. 이번 병렬 상태 전이와 통과한 SPI 최종 실행 허용은 재수정하지 않는다. 다음은 실패 경로3개(command→주소검사, byte_count→command, remaining→loaded_bytes)의 실제 레지스터 갱신 조건을 함께 검토한다. SPI 첫 명령 바이트 수신 시 offset 검사 종류를 함께 등록하고 명령 레지스터의 소유권/갱신 허용을 분리하는 구조, 로더 terminal 판정을 동일 클록의 next-remaining과 일치하도록 유지하는 구조를 우선 검토한다. 단순한 사전 샘플링으로 live length·ready·fault를 늦추거나 WRITE/HOLD·STOP/리셋 시점을 바꾸지 않는다. 새 보조 레지스터는 실제 SPI 및 쓰기 시퀀스에서 불변식을 확인하고, 직접 상태 주입 시험에서도 관련 값을 일치시킨다. 변경 경계 검증 후 한 번 전체 배치하고 세 실패 경로와 state→error_code를 모두 확인한다. 같은 소스 refit/seed·속성 탐색이나 최악 경로 하나만 바꾸는 반복은 생략한다. ID74/C0C1C2/valid-only payload/SS high·setup2µs 계약을 유지한다. 내부 조건이 갖춰지면 필요한 외부IO·영상CDC/reset와 MCU E6/version2 상태73·E5 관측70·E0/F6 수신·변환·ACK, 사운드·입력·STOP·시간 및 full-link/stack을 연결하고 최소 SMB3(J) 첫 레벨 실기로 간다. 설치164/GBC/세이브 SRAM 보존; 새SD 없음; 전체ROM·A/B·044 반복 생략.

연속 게임 화면을 위한 FPGA 로더 제어 회로를 완성하는 작업이다. 실기 패키지까지 필요한 경계만 확인한 뒤 SMB3(J) 첫 레벨 플레이로 판단한다. 완료된 원자료·검증 pin·finalizer는 수정하거나 반복 실행하지 않는다.
