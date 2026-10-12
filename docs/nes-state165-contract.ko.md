# NES165 로더 상태 전환 분리

165 영상 경로 진척: 로더 상태 전환을 오류·데이터 처리에서 분리하고 294912조건·1056쓰기/중단 시나리오를 비교했습니다. 새 후보를 다음 구현 기준으로 채택했습니다. 선택 구현 state165/map01/reproduce01. 15077LE/963LAB/35M9K, 실제 클록 setup-0.092ns. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

[검증 수치](../analysis/state165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 문제와 구현

release165/map01은 공유 리셋 해제→영상 SPI 경로를 해결했지만, load_begin→로더 fault 판정→WRITE/HOLD 상태 전환이7단 논리로 이어져−0.583ns였다. 이번에는 상태 레지스터를 독립된 always 블록 하나에서만 갱신하고, 기존 블록에는 오류 코드·데이터 갱신만 남겼다.

기존 fail/advance_phase와 분기에서 상태 대입만 제거했다. 나머지 부수 효과의 우선순위를 보존하려고 상태 전환만 하던 자리에 빈 문장/빈 task가 남는다. 실제 상태 전환과 쓰기 마무리는 새 독립 블록이 맡으며 제거된 것이 아니다. 이전 compare165의 drain 분기 재배치만 반복한 변경과 구분한다.

WRITE/HOLD에서 새 오류 명령은 그 사이클의 상태 전환을 보류한다. 다음 사이클부터 이미 저장된 fault에 따라 쓰기를 마무리한다. 타이머·CE/OE/WE·데이터·오류 코드·STOP 우선순위와 리셋 해제 주기를 보존했다. READY 판정·요청 태그·reader 마지막 사이클·4개 mailbox 해제 병합 방지 설정은 release165 후보와 같다. QSF·SDC·클록은 변경하지 않았다.

## 검증 범위

- 기존 회로와 실제 레지스터·출력 핀을 비교했다. 모든16상태 코드, 명령64조합, 명령 차단, fault, 모드,6개 길이 경계, remaining 0/1/2/22/64/127에서 총294912조건을 확인했다. 상태·카운터·count_complete·오류·주소·데이터·CE/WE 등이 같았다.
- 실제 BEGIN과1바이트 입력 후132개 위치에서 STOP/BEGIN/END/START/명령 충돌/차단 명령/리셋/추가 데이터의8동작, 총1056시나리오를 연속 실행했다. 매 클록과 비동기 리셋 때 상태·메모리 핀이 같았다.
- STOP 시 WRITE/HOLD를 즉시 FAILED로 바꾸는 잘못된 후보가 비교 시험에서 검출됐다.
- 이는 초기 상태를 주입한 조건 비교와1바이트 연속 시험이다. 전체 상태 형식 증명·전체 ROM 적재·새 게임 부팅·MCU/SNES 실기 시험이 아니다. 변경되지 않은 SPI/reader의 기존 근거는 재사용했다.
- 총61개 배치 입력 중 로더 RTL만 변경했고 나머지60개는 바이트가 같다. 독립 재생성과 실제 배치 입력도 일치한다. 이번 배치의 mailbox 해제4개 레지스터/첫단계 fanout1/두 체인12개 setup·hold 경로도 확인했다.

## 배치 결과

|항목|결과|
|---|---:|
|전체 FIT/ROUTE|통과|
|LE / LAB / M9K|15077 / 963 / 35|
|실제 클록 최악 setup|-0.092ns|
|실제 클록 최소 hold|+0.151ns|
|로드 시작→로더 상태 최소 setup|+0.101ns|
|영상 해제→SPI held 최소 setup|+6.258ns|
|추가 배치 목표 최악 setup|-0.369ns|

실제4클록·3조건 setup/hold 통과 여부는 **False**다. **새 후보를 다음 구현 기준으로 채택했습니다.** 추가 배치 목표와 실제 클록 분석은 구분한다. 외부 입력54개/출력57개 미제약, 혼합 클록 및 전체 reset·CDC·MTBF와 MCU 실행 연결은 계속 별도 미완료다. 이 결과만으로 SD 설치를 승인하지 않는다.

종전 선택 기준 predecode165의−0.153ns보다 전체 최악값이−0.092ns로 개선되어 개발 기준을 옮겼다. 직전 release165 후보의−0.583ns와도 구분한다. NES/host/board 클록은 각각+8.126/+1.372/+122.589ns다. 남은 최악 경로는 start→fault~3→phase_step~0→Selector9~0→state~60/61→SETUP이며5단 논리·데이터 지연5.967ns 중 배선4.035ns(68%)다. READY→WRITE/RECEIVE도−0.001ns로 남았다. START 명령이 정상적으로 SETUP에 진입시킨다는 뜻이 아니라, SETUP 상태 비트의 유지·전환 조건에 영향을 주는 경로라는 뜻이다.

## 다음 작업과 의미

SELECT state165/map01/reproduce01;state165map01 nominal -0.092ns, worst nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|start -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|state.SETUP. Actual path start->fault~3->phase_step~0->Selector9~0->state~60/61->SETUP:5levels,68percent routing. Also READY->WRITE/RECEIVE -.001ns. Preserve new single-state-owner contract; inspect shared command/timed-phase guard for SETUP hold/entry and those near-zero paths, without assuming START is a legal SETUP entry. No unchanged fit or old compare165 drain/phase/counter repeats, no clock/SDC relaxation. Preserve fault/STOP/write drain and four local release QSF assignments with fresh hierarchy checks. Then minimum IO/CDC/reset+MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and SMB3(J) hardware;no unchanged fullwrites/OAM/A-B/044/saveSRAM.

연속 화면을 위한 FPGA 배선·상태 제어 구현이다. 일반 디버그 기능 확대보다 동작 속도와 필요한 MCU 연결을 해결하고 최소한의 안정성 확보 후 SMB3 첫 레벨 실기로 진행한다. 원본 GBC·설치164 사운드/입력/메뉴와 세이브 SRAM은 보존한다.
