# NES165 타이머 상태의 명령 조건 단순화

165 영상 경로 진척: 로더 SETUP·RELEASE의 중복 명령 충돌 조건을 제거하고 동작을 비교했습니다. 새 개발 기준으로 채택했습니다. 선택 구현 phaseguard165/map01/reproduce01. 후보 15039LE/960LAB/35M9K, 실제 클록 setup-0.083ns. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

[검증 수치](../analysis/phaseguard165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 변경 근거

선택 기준 state165/map01의 최악 경로는 START→SETUP 상태 비트−0.092ns였다. SETUP·RELEASE에서 command_conflict는 반드시 승인된 BEGIN·END·START 중 하나를 포함한다. 이 세 명령은 각각 단독으로도 FAILED 전환 조건이다. 따라서 fault 또는 이 세 명령을 먼저 판정하면 별도의 command_conflict 우선순위 단계를 제거할 수 있다. STOP과 함께 들어온 충돌도 FAILED가 우선이며, STOP 단독은 IDLE로 간다. 차단된 명령은 승인되지 않는다.

오류 코드 생성 블록·타이머·쓰기 데이터·핀과 WRITE/HOLD 마무리는 그대로다. 동일 상태 레지스터 소유권을 유지하며 클록·SDC·4개 지역 리셋 해제 QSF 설정은 바꾸지 않았다. 이전 drain 분기 재배치나 무변경 재배치 시험이 아니다.

첫 후보의 최악 경로가 loaded_bytes→pending_counter_clear로 이동해 두 번째 후보도 시험했다. STOP의 헤더/명령/인수 자격과 offset==loaded_bytes 비교를 같은 SS 상승 클록에서 각각 저장하고, 기존 처리 클록에서 결합했다. 적재 길이를 한 클록 먼저 읽거나 명령 처리 지연을 늘리지 않는다. BEGIN/CHECK_BEGIN의 초기화 자격은 별도 저장한다. 두 번째 후보의 채택 여부는 아래 전체 결과를 따른다.

## 검증 범위

- 기준 회로와294912개 초기 상태/명령/길이/타이머 조건에서 실제 상태·오류·카운터·주소·핀을 비교했다. 모든16상태 코드와 명령 차단도 포함한다.
- 실제 BEGIN·1바이트 쓰기 후132위치×8동작, 총1056개의 연속 명령·리셋 시나리오가 통과했다. STOP으로 쓰기를 즉시 끊는 잘못된 후보도 검출했다.
- 초기 상태를 주입한 비교와1바이트 연속 시험이며, 전체 상태 형식 증명·전체 ROM 적재·게임/MCU/SNES 실행 시험은 아니다. 변경되지 않은 SPI/reader 근거는 재사용한다.
- 61개 배치 입력 중 로더 RTL만 변경했다. 나머지60개 입력과 독립 재생성 결과가 일치한다. 새 배치의 지역 리셋 해제4레지스터/첫단계 fanout1/12개 setup·hold 경로도 확인했다.
- 두 번째 후보는 첫 후보에서 SPI RTL만 변경했다. state165 대비로는 로더와 SPI 두 파일을 변경했고59개 입력이 같다. STOP 저장·처리393741조건(24개 offset 비트 반전과 길이 경계 포함), 저장 후 live length 변경, SPI+boot+READ16 연결 회귀를 실행했다. 주소 검사 누락 후보도 검출했다. 최초 연결 시험은 옛 레지스터 직접 주입이 새 wire와 맞지 않아 최적화 단계에서 실패했다. 새 내부 저장 레지스터에 같은 STOP 조건을 주입하도록 시험 코드만 수정한 뒤 통과했으며 실패 로그도 보존했다.

## 배치 결과

|항목|결과|
|---|---:|
|전체 FIT/ROUTE|통과|
|LE / LAB / M9K|15039 / 960 / 35|
|실제 클록 최악 setup|-0.083ns|
|실제 클록 최소 hold|+0.130ns|
|START→로더 상태 최소 setup|+0.805ns|
|영상 해제→SPI held 최소 setup|+5.177ns|
|추가 배치 목표 최악 setup|-0.197ns|

실제4클록·3조건 setup/hold 통과 여부는 **False**다. 첫 후보 map01은 START→상태 최소 setup을 -0.092에서 +0.805ns로 개선했다. 전체 최악 setup은 -0.083ns, 최소 hold는 +0.130ns이며 15039LE/960LAB/35M9K다. 메모리 이외 host/NES/board setup은 +1.139/+8.144/+121.793ns다. 종전 state165의 -0.092ns/963LAB보다 좋아 map01을 채택한다. 남은 최악 경로는 loaded_bytes[6]→pending_counter_clear이며 equality4단과 자격 결합2단, 데이터 지연5.956ns다. SPI STOP 조건을 별도 저장한 map02는 기능 비교·연결 시험과 FIT를 통과하고15001LE/960LAB을 썼지만, 요청 태그→CHECK 카운터 경로가 -0.449ns로 악화되어 채택하지 않는다. 실기 배포나 전체 타이밍 통과는 아니다.

추가 배치 목표와 실제 클록은 구분한다. 외부 입력54개/출력57개, 혼합 클록·전체 reset/CDC·MTBF와 MCU 연결은 별도 미완료다. 이 결과만으로 SD 설치나60fps를 승인하지 않는다.

## 다음 작업과 의미

SELECT phaseguard165/map01/reproduce01, not rejectedmap02. Reuse294912loader conditions/1056sequences and exact unchangedSPI/reader evidence. Remaining nominal -0.083ns loaded_bytes[6] -> pending_counter_clear: inspect offset=={5'd0,loaded_bytes} equality depth/partition and static clear eligibility on SAME capture edge. Do not pre-sample loaded_bytes: loader may advance while SPI frame is arriving. Do not repeat rejected STOP operand split map02 (-0.449 tag->check_next), compare165 response-mask/phase/drain variants, unchanged fits/fullwrites/OAM/A-B/044. Preserve state single owner/error priorities/WRITE-HOLD drain, local4release QSF, exact clocks/SDC. After same-clock closure, check necessary native-video held-data/control/reset/externalIO on selected hierarchy; connect MCU E6/version2 status73, E5 observer70, E0/F6 receive-convert-ACK/audio/input/STOP/elapsed-time/full-link/stack then minimal SMB3(J) first-level hardware. Save SRAM remains reserved; no broad debug expansion. Both candidate builds/FLOAT finished. SPI01 connected elaboration failed because old test force targeted a now-wire predicate; SPI02 targets equivalent captured operands and passes, not a hardware/license fault. Preserve failedSPI01 and completedarchives/finalizers/publicpins.

연속 게임 화면을 위한 FPGA 상태 제어와 동작 속도 확보 작업이다. 설치164의 사운드·입력·메뉴, 원본 GBC와 세이브 SRAM을 보존하고, 필요한 연결과 검증 후 SMB3 첫 레벨 실기로 간다.
