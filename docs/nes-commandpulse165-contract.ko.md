# NES165 명령별 실행 허용과 같은 클록 오류 차단

## 목표와 변경

165 영상 경로 진척: BEGIN·DATA·END·START·STOP·CHECK READ 허용을 앞 단계에서 등록하고, STOP 처리를 상태별로 판정하는 로더와 결합했습니다. 6개 실행 허용 레지스터를 실제 배치에서 확인했다. 15055LE/963LAB/35M9K, 실제 최악 setup-0.136ns; load_begin → state.WRITE. 응답→BEGIN +0.831ns, 오류→DATA +1.592ns, 명령→사전 허용 +1.936ns. 선택 phaseguard165/map01/reproduce01, 내부 실제클록 통과=False. 전체IO/CDC·MCU 연결·실기는 미완료, 새SD 없음.

이전 [명령3단계 계약](nes-commandstage165-contract.ko.md)의 map02에서 응답 주소 확인→BEGIN에7단 LUT가 남았다. 이번에는 C1에서 BEGIN/DATA/END/START/STOP/CHECK READ의6개 허용 비트를 헤더·body 검사와 함께 등록하고, C2는 live fault와 SS 상태로 실행 펄스만 차단하도록 분리했다. C2에서 명령을 다시 비교하거나 오류 코드를 재판정하지 않는다. SPI 오류 코드·CHECK 상태·카운터·응답 소유권 처리는 그대로다. 첫 후보 map01은 응답→BEGIN을+1.430ns로 개선했지만 STOP→로더 state.WRITE의9단 경로−0.195ns가 남았다. 그래서 map02는 기존 RETIRECE map02에서 검증한 상태별 명령 판정 로더를 결합했다. RECEIVE/RUN 등의 불가능한 명령 조합을 각 상태에서 판정해 공통 command_conflict 우회 경로를 줄이는 구조다. 이전 오류 코드 소유권 변경 후보는 포함하지 않았다.

명령 완료는 C0캡처/C1판정/C2실행이다. 이전 실험보다 지연을 추가하지 않았다. 설치164 및 phaseguard 기준보다1mem_clk 늦다는 계약, 실험 응답ID0x74, load_valid=0일 때 payload 비관찰 조건을 유지한다. 이미 확인한 MCU SS high/setup2µs와2.625MHz 근거는 hash로 묶어 재사용했다. 클록 주기·SDC·false path·multicycle 예외를 변경하지 않았다. 설치용 MCU는 아직 새 식별자를 적용하지 않았으며 이번 회로는 기존0x6b 펌웨어와 자동 호환된다고 주장하지 않는다.

## 검증 범위

- 393,741개 캡처·거래 결과를 기존 기준과 비교했다. 기준 실행 후 후보를1클록 더 전진시키는 비교이며, 같은 클록 동등성 주장은 아니다. 추가 허용 레지스터6개는 매 명령마다 자동 소거하고 캡처된 명령 하나만 등록한다.
- 120개 단계별 취소 조건에서 **오류가 들어온 바로 그 클록 직후**에도 실행 펄스가0인지 확인했다. 이전 시험은 이후 클록의 지속 상태 중심이었으므로 이번 변경 경계를 위해 이 검사를 보강했다.
- 실제 SPI/boot/READ16 회로의219개 wire 프레임,100읽기·7ACK·19주소 손상·72취소·2충돌과 MISO 식별자/상태 응답, 허용 비트의 동시 중복 금지를 통과했다. 직접 주입하는 STOP fixture에도 새로운 사전 허용 비트를 맞춰 넣었다.
- SS 겹침 검사 제거, 최종 check_fault 검사 제거, BEGIN 헤더/body 검사 제거의3개 잘못된 회로가 각각 검출됐다. 동일 클록 오류의 실행 누출을 숨기지 않는 대조 시험이다.
- 구현61개 입력 중 map01은 SPI1개 변경/60개 보존, map02는 SPI·로더2개 변경/59개 보존이다. 핀·QSF·SDC와 설치164/GBC는 불변이다. 둘 다 독립 생성 바이트 재현, 실제6허용 레지스터, 지역 reset 해제4레지스터·12개 setup/hold 경로를 확인했다.
- map02의 SPI는 map01과 바이트가 같아393,741/120/3negative를 재사용했다. 로더도 이전 RETIRECE map02와 바이트가 같아294,912조건/1,056시퀀스·잘못된 STOP 시험을 hash로 연결해 재사용했다. 두 모듈을 함께 둔219wire/100READ/7ACK/19bad/72cancel/2priority 연결 시험은 새로 실행했다. 단위 시험을 다시 실행했다고 주장하지 않는다.

연결 시험은 일부 READY/count와 CHECK counter를 주입하며, 전체 ROM 적재·MCU 실행·게임·물리 SPI 계측은 아니다. 이전 테스트/빌드/공개 소스 pin은 수정하지 않았다.

## 결과

첫 후보 map01은15019LE/962LAB/35M9K, 최악−0.195ns로 미채택이다. 응답→BEGIN은+1.430ns지만 STOP→state.WRITE가 남았다. 결합 map02는 STOP→상태를+0.083ns, 응답→BEGIN을+0.831ns로 통과했지만 BEGIN→state.WRITE −0.136ns가 남았다. 따라서 이번 두 후보 모두 미채택이다.

|항목|map02 결합 결과|
|---|---|
|자원|15055LE / 963LAB / 35M9K|
|실제 최악 setup|-0.136ns|
|전체 최소 hold|+0.150ns|
|실제4클록·3조건198행|미통과|
|응답 주소→BEGIN|+0.831ns|
|CHECK 오류→DATA|+1.592ns|
|명령→사전 허용|+1.936ns|
|선택|phaseguard165/map01/reproduce01|

6개 실행 허용 레지스터를 실제 배치에서 확인했다. 15055LE/963LAB/35M9K, 실제 최악 setup-0.136ns; load_begin → state.WRITE. 응답→BEGIN +0.831ns, 오류→DATA +1.592ns, 명령→사전 허용 +1.936ns.

기존 선택 기준−0.083ns보다 전체 타이밍이 나아지지 않아 미채택이다. 더 엄격한 추가 배치 목표와 실제 클록 결과는 별도 보존한다. 전체 외부54입력/57출력·영상CDC/reset·MTBF와 MCU full-link/stack은 미완료다. 내부 타이밍 판단만으로 실기60fps나 새 SD 배포를 승인하지 않는다.

## 다음 작업과 의미

기준 phaseguard165/map01/reproduce01을 유지한다. 이번 map02는 후속 구조 검토용이며 채택한 배포 기준이 아니다. 잔여 load_begin → state.WRITE (-0.136ns)은7단 LUT이며 data delay6.013ns 중 배선4.030ns(67%)다. 응답 주소→실행 허용과 STOP은 통과했으므로 다시 손대지 않는다. 다음은 로더의 공통 다음 상태 선택망을 WRITE/RECEIVE 등 목적 상태별 전이식으로 분리하는 한 후보를 검토한다. WRITE/HOLD drain·STOP·같은클록 오류·미사용4비트 상태의 기존 결과를 보존하고 변경 경계 비교 및 결합SPI 시험을 통과한 뒤 한 번 배치한다. 자동 상태 인코딩이나 속성만 바꿔 우연히 좋아지기를 기대하는 무변경 refit는 하지 않는다. 실험ID74/C0캡처-C1판정-C2실행/valid=0 payload 비관찰/SS high·setup2µs 계약과 같은클록 fault 우선순위를 보존한다. 후속 MCU는 정확한 식별자를 검사하고 E6/version2 상태73·E5 관측70·E0/F6 수신/변환/ACK, 사운드·입력·STOP·경과시간과 full-link/stack을 연결한다. 최소 조건을 갖추면 SMB3(J) 첫 레벨 실기로 진행한다. 설치164·GBC·세이브 SRAM 보존; 전체 ROM 쓰기·A/B·044 반복 생략.

연속 게임 화면을 위한 FPGA 제어 회로의 처리 속도를 확보하는 작업이다. 디버그 표시를 늘리는 작업이 아니다. 변경 경계만 검사하고 최소한의 연결 조건을 갖춘 뒤 실제 SMB3로 판단한다.
