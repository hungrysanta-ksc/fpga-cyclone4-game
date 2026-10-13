# NES165 명령 수신과 적재 카운터 갱신 구조

## 목표와 구현

165 영상 경로 진척: SPI 명령 종류를 수신 시 저장하고 로더 종료 판정을 카운터와 같은 클록에 갱신하도록 분리했습니다. 명령 수신+1.458ns·명령 종류→주소검사+3.821ns·종료비트→적재카운터+1.603ns로 세 목표 경로는 통과했다. 그러나 최악 경로는 state[0]→state[2] −0.597ns로 이동했다. 상태 해석→destination 재인코딩→상태 갱신의5논리단계/6.472ns 중 배선4.111ns(64%)이며, 같은 상태 피드백의 실패 전이 경로도7단계/−0.520ns다. 별도로 READ16 read_last→data_hold enable은1논리단계지만5.048ns 배선(80%)/−0.429ns여서 상태 한 경로만 수정해서 끝날 상황이 아니다. 기존 채택 기준 phaseguard−0.083ns보다 나쁘므로 후보를 채택하지 않는다. 선택 phaseguard165/map01/reproduce01; 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

이전 [DESTINATION 후보](nes-destination165-contract.ko.md)는 BEGIN→상태를 통과했지만 명령→주소검사−0.160ns, 타이머→적재카운터−0.123ns, 수신카운터→명령−0.109ns가 남았다. 이번에는 세 경로를 함께 검토해 SPI·로더2개를 변경하고59개 구현 입력을 보존했다. 채택 비교는 기존 phaseguard의−0.083ns이며, 실험용 destination 후보를 이미 채택한 기준으로 간주하지 않는다.

- SPI command 레지스터의 갱신을 별도 always 블록으로 분리했다. 첫 바이트를 받는 바로 그 클록에 offset=0 검사 명령/offset=loaded_bytes 검사 명령의2비트를 함께 저장한다. SS high와 reset에서 command와 함께 지운다.
- 명령 종류만 저장하며 offset·live length·ready·fault는 원래 시점에 검사한다. 기존 C0/C1/C2 실행 지연을 추가하지 않는다.
- 로더 terminal 비트는 언제나 remaining==1과 일치한다. 감소 시에는 현재 remaining==2로 다음 값을 만들고, SETUP/WRITE/HOLD 상수 재적재·정지·오류 배출·reset도 remaining과 같은 always 블록에서 처리한다. state/count 전이의 equality를 이 비트로 대체했다.
- 명령·카운터 갱신 구조와 오류 코드 처리는 유지했다. 클록·SDC·false path·multicycle·핀·PSRAM 쓰기 시간은 바꾸지 않는다. ID74/valid-only payload/SS high·setup2µs와 설치164/GBC/saveSRAM 보호도 유지한다.

## 검증과 실행 이력

새 로더는294,912조건/1,056쓰기사이클·명령·STOP·리셋 시퀀스에서 기존 회로와 같은 클록 결과를 비교했다. 직접 remaining을 주입하는 fixture는 terminal도 일치시킨다. 각 갱신 후 불변식을 검사하고 잘못된 종료 예측을 검출했다.

새 SPI는393,741거래/120취소를 비교하고, 명령 종류도 직접 command 주입값과 일치시켰다. 실제SPI/boot/READ16 결합219wire/1,125,909클록/100READ·7ACK·19주소손상·72취소·2충돌에서 명령 종류와 terminal 불변식을 검사했다. 기존 SS 겹침·같은클록 fault·BEGIN header 검사 제거와 새 잘못된 명령 종류의4가지 회로를 대조 시험에서 검출했다. SPI 거래 결과 비교는 원래 phaseguard보다1클록 늦는 C0/C1/C2 계약이며 같은 클록 동등성 주장이 아니다. MCU 간격의 기존 소스 근거만 재사용했다.

setup01은 command 문자열 검사에 pending_command도 포함되어 생성 전 assertion에서 중단됐다. 식별자 경계를 고친 map02는 로더 시험을 통과했지만 SPI 레지스터 선언이 사용 위치 뒤에 있어 컴파일이 실패했다. 선언을 앞으로 옮긴 map03이 최종 후보이며 독립 reproduce03과 바이트가 일치한다. map02/map03 로더 바이트는 동일하다. 최초 소스·실패 로그를 보존했고 map03에서 전체 기능 시험을 다시 완료했다. 라이선스 실패가 아니며 전체 FPGA 배치는 map03에 한 번만 수행했다.

기존 destination 분석 스크립트는 remaining→state 경로가 terminal로 대체되어 해당 경로를 찾지 못하고 중단됐다. 이 오류 로그를 보존하고, 새 update 경로 스크립트로 실제 terminal 및 보조 레지스터·상태 레지스터를 다시 조회했다. analyze02는 이미 완료한 배치의 보고서만 생성했으며 추가 FIT가 아니다.

지역 reset 해제4레지스터/12setup·hold 경로와 새 보조 레지스터3개를 실제 배치에서 확인했다. 일부 READY/count를 주입하는 모델이므로 전체 ROM 적재·MCU 실행·게임·실기 신호 계측 통과는 아니다.

## 결과

|항목|결과|
|---|---|
|자원|15045LE / 962LAB / 35M9K|
|실제 최악 setup|-0.597ns|
|최소 hold|+0.153ns|
|실제4클록·3조건198행|미통과|
|수신카운터→명령|+1.458ns|
|명령 종류→주소검사|+3.821ns|
|종료비트→적재카운터|+1.603ns|
|상태→오류 코드|-0.248ns|
|BEGIN→상태|-0.062ns|
|CHECK 오류→상태|-0.222ns|
|채택|False|

명령 수신+1.458ns·명령 종류→주소검사+3.821ns·종료비트→적재카운터+1.603ns로 세 목표 경로는 통과했다. 그러나 최악 경로는 state[0]→state[2] −0.597ns로 이동했다. 상태 해석→destination 재인코딩→상태 갱신의5논리단계/6.472ns 중 배선4.111ns(64%)이며, 같은 상태 피드백의 실패 전이 경로도7단계/−0.520ns다. 별도로 READ16 read_last→data_hold enable은1논리단계지만5.048ns 배선(80%)/−0.429ns여서 상태 한 경로만 수정해서 끝날 상황이 아니다. 기존 채택 기준 phaseguard−0.083ns보다 나쁘므로 후보를 채택하지 않는다.

더 엄격한 배치 목표와 원래 실제 클록 보고서는 별도 보존한다. 외부54입력/57출력·영상CDC/reset/MTBF 및 MCU full-link/stack은 미완료이며, 내부 타이밍만으로 실기60fps를 주장하지 않는다.

## 다음 작업과 의미

이번에 통과한 SPI 명령 수신·명령 종류·terminal 경로를 다시 미세 조정하지 않는다. 다음에는 실제 state→Equal→destination→state 경로를 기준으로 상태 판정의 등록/상태 표현 변경을 검토한다. 단순 ONE_HOT 옵션 재시도 대신 중복 decode와 실패 전이의 공유를 줄이는 RTL 후보의 논리 깊이·추가 FF·모든16개 상태 코드의 의미를 먼저 명시하고, STOP/오류 코드/쓰기 배출/reset의 같은 클록 동작을 유지한다. READ16 read_last→data_hold enable의 긴 배선도 동시에 검토하며, 필요하면 같은 값을 유지하는 지역 복제 레지스터를 후보에 포함하되 읽기 샘플 시점은 바꾸지 않는다. 기능·전체 배치·모든 내부 클록 setup/hold를 통과한 뒤 필요한 외부IO·영상CDC/reset 및 MCU RUN/시간/사운드/입력/STOP/full-link/stack을 연결하고 최소 SMB3(J) 첫 레벨 실기로 넘어간다. 새 SD 패키지는 아직 만들지 않는다.

연속 게임 화면을 위한 FPGA 제어 회로의 타이밍을 확보하는 작업이다. 최소 연결 조건이 갖춰지면 SMB3(J) 첫 레벨 실기로 판단한다. 완료된 원자료·검증 pin·finalizer는 불변이다.
