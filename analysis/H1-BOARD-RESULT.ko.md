# H1 실제 핀·PLL·ROM 경계034

2026-10-06. 후보 **NES-H1-BOARD-034**.

**H1을 실제 보드 핀과 PLL에 연결한 top을 구현하고 물리 배치·내부 STA를 통과했다.**
SNES 프로그램 공급과 시작·정지·세대 재시작도 추가했다. 외부 IO 및 실제 MCU 펌웨어 연결은 남아 있다.

|검증|결과|
|---|---|
|실제 Quartus 배치|1,298LE /110LAB /44M9K /824registers|
|물리 구성|135개 실제 핀,virtual pin0,PLL1개,8MHz→84MHz|
|내부 STA 최소 여유|setup+2.724ns,hold+0.161ns,recovery+6.976ns,removal+0.518ns|
|실제 RTL 시험|6조건,ROM65,536바이트·패턴8,192바이트 일치|
|실제 Mesen CPU/PPU|epoch1·2 각각7화면,총856,576화소 일치|
|호스트 C 컴파일·시험|시작·정지·오류 보호7조건,MSVC /W4 /WX 통과|

## 이번 구현

자체64KiB SNES 진단 ROM을24KiB FPGA 내부 저장소로 공급한다.
미사용 영역FF와 LoROM 미러까지 검사했으며, SRAM/게임ROM/기존 GBC 로더에 의존하지 않는다.
034 화면의 식별 제목과1/2/3 순환은 실제 Mesen 캡처에서 확인했다.
기준 화면 (로컬 비공개 자료: `local-h1-board-034/board-reference-contact.png`).

새 SPI ARM/STOP은 키·프레임 길이를 확인한다. 중복 ARM은 세대를 바꾸지 않는다.
STOP은 전송부를 초기화하고 버스를 해제하며, 다음 ARM은 새 세대를 부여한다.
SNES 프로그램은600B/600C에서 세대를 읽어031 전송 규약으로 전달한다.
PLL 잠금 해제 시 클록이 멈춰도 출력은 즉시 차단되고 재잠금만으로 자동 재시작하지 않는다.
RTL에서 세대1→2→3,읽기 중 STOP,클록 정지 중 PLL loss를 검사했다.

MCU용 C 코드는 RESET 유지→FPGA 설정→식별→ARM→새 세대 확인→RESET 해제를 구현했다.
오류는 RESET을 유지하고, ARM 이후 오류는 STOP을 시도한다.
이 코드는 **호스트 콜백 시험**까지 완료했으며 STM32 드라이버/메뉴에 연결하지 않았다.
STOP 후 메뉴 FPGA/ROM 복원도 실제 펌웨어 통합 작업으로 남아 있다.

## 완료 판정의 경계

현재 H1 전용 구성에는 NES 게임 코어가 없다.
내부 메모리는program24KiB+pattern6KiB+queue6KiB+stage3KiB=39KiB,
M9K는24+8+8+4=44개다.032 NES 공동 배치와 잔여40LAB는 별도 판단이다.
H1은 한84MHz 클록을 쓰며 NES 장기 클록 동기화 문제를 해결한 것으로 세지 않는다.

외부 타이밍은 아직 **입력38개/804경로,출력11개/933경로가 미제약**이다.
STA의 warning0과 내부 양수 여유는 물리 SNES/SPI의setup/hold/응답·버스전환 보장이 아니다.
false path/주기 완화는 적용하지 않았다. MTBF·실제 동기화 체인 검토도 남아 있다.
Quartus synchronizer 식별을 추가했으나 같은 클록 최적화 후queue_up_h 한 항목은 무시됐다.
기존async_reg 미인식과 미사용 ROM write port/메모리 핀/고정 출력 경고는 원문 보존했다.

RTL에서는84MHz와lock을 시험벤치가 주입했다. 아날로그 PLL 동작이나 실기 파형은 검증하지 않았다.
Mesen은 명시적인 MMIO 장치 모델에 실제034 RTL의3페이지를 반복 공급한다.
두 환경은 분리된 실행이며, 모델의응답 지연을 물리 FPGA 실측으로 해석하지 않는다.
65535세대/순번 경계는 구현됐지만 이번 실행은 유한한 세대1/2/3만 검사했다.
새bitstream 조립·STM32 전체빌드·SD 배포·실기는 수행하지 않았다.

## 실패 보존

- 첫 RTL 컴파일: hex literal 뒤 공백 없는삼항식과 TB예약어sequence로 실패.
  해당 원본과 로그를 보존하고 토큰·이름을 수정했다.
- 첫 실제 핀fit: NCEO와ROM_ADDR[7]의F16 충돌로 실패.
  기존 보드QSF에 있던 NCEO의일반IO 설정 누락을 복구했다. 핀 이동은 없었다.
- 수정 후 실제RTL과map/fit/STA는 통과했다. 추가seed나타이밍 완화는 사용하지 않았다.

## 다음 작업

1. 실제 SNES/SPI의입출력 시간 조건·버스해제 지연과 합성된 동기화 체인을 검토하고 제약한다.
2. 전용 MCU코드를250kHz SPI·RESET·FPGA설정·메뉴복원에 연결하고 별도 펌웨어를 빌드한다.
3. 동일후보의전체검증 뒤 H1실기 패키지·기준화면·복구절차를 제공한다.

H0의 기본 육안 실기 통과는 유지한다. 현재034는실기 시험 요청 대상이 아니다.
GBC C44/0.9.0,033생산기/031전송부,core014와upstream은 변경하지 않았다.
원시 자료는analysis/local-h1-board-034에 Git제외로 보존한다.
[검증 수치](h1-board-verification.json), [실행·인터페이스 계약](../docs/nes-h1-board-contract.md).
