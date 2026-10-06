# H1 041 — 정확한 frontend 오류 조건 계측

사용자는040 재시험에서도 실패했고, 이번에는 화면이 다 나타나기 전에 자동 복귀했다고 보고했다.
**040은 실기 해결에 실패했다. 041은 원인 분리용 진단 후보이며 해결 완료로 간주하지 않는다.**
[실기 안내](../docs/nes-h1-edge-test.ko.md), [검증 기록](h1-edge-verification.json).

## 새 실기 증거

새 첨부 nes-h1-last-039 (1).txt를 원시 바이트로 보존했다.
F2_STATUS/07,start/stop0,base복구1,polls31,elapsed460ms.
스냅샷 a53907871000e08040defb2a0002는 frontend1,stage0,producer0,flags87,
ROMSEL낮음,주소40:80E0,published2다. 이전039 로그의 ROMSEL높음/011800과 다르다.
주소와 제어 신호는 오류 레지스터를 관측한 뒤의 캡처값이므로 이 정보만으로 어느 검사가 발동했는지 확정할 수 없다.
40:80E0만으로 정확히224바이트를 성공적으로 읽었다고 단정하지 않는다.

사용자는040 설치 안내 뒤 재시험했다. 다만 로그 프로토콜0x39/MCU039는039·040 FPGA를 구분하지 못하고 SD 파일 해시는 회수하지 않았다.
실기 기록은 보고된040 재시험으로 보존하되 실제 FPGA 해시 확인 여부는 false로 남긴다.
040의 정상 ROMSEL 종료 오검출은 RTL에서 증명된 결함이지만 이번 실기 해결에는 충분하지 않았다.
같은 집계 오류 비트가 나왔다고 이전 재현 파형이 실기 원인으로 확정됐다고 주장하지 않는다.

##041 계측 계약

[파생 코드](../tools/nes_h1_edge.py)는040 frontend 동작을 그대로 유지하며 첫 오류 조건을 발생 클록에 별도로 저장한다.
SPI D0…DF에16바이트를 추가하고 F0…FF의039 aggregate 형식은 유지한다. F1 프로토콜은0x41로 구분한다.
MCU041은30바이트를 STOP 전에 읽고 base복구 후 nes-h1-last-041.txt에 기록한다. 이전0x39 FPGA는 초기 세션 검사에서 거부한다.

|바이트|내용|
|---|---|
|D0|원인 bit0 활성 읽기 주소변경,bit1 응답 pending 중 RD 해제,bit2 pending 중 WR 활성,bit3 활성 payload ROMSEL 해제,bit4 RD/WR충돌,bit5 순서/ready위반,bit6 응답부재|
|D1|bit7 output_valid,6 payload_pending,5 local_pending,4 rd_previous,3:2 rd_sync,1:0 pending|
|D2|bit7 ready,6 busy,5 fault,4 reg_rvalid,3 data_valid,2 ROMSEL_n,1 RD_n,0 WR_n|
|D3…D5|오류 조건 평가 시 raw 주소,리틀엔디언|
|D6…D8|기존 래치 read_address,리틀엔디언|
|D9…DA|그 클록 이전 position,16비트 리틀엔디언|
|DB…DE|현재low count,직전low count,현재high count,직전high count|
|DF|유효 캡처 태그0x41,캡처 없으면0|

카운터는 해당 host_clk 상승에지 직전 레지스터값이며255에서 포화된다. 명목84MHz 샘플 개수로,아날로그 펄스 폭·메타안정성 측정값이 아니다.
이 새 기록은 기존 지연된 aggregate snapshot과 독립적이다. 첫 원인은 이후 오류로 덮어쓰지 않고 STOP/reset에 지워진다.
FPGA 설치 버전은 새 프로토콜과 MCU의0x41 검사로 구분된다. 초기진입 실패 시에는 정상 실행으로 간주하지 않는다.

## 검증

- 전체 ARM STM32 빌드 통과,컴파일 warning/error0. 소스와 실제 firmware.stm 보존.
- 생산 MCU 바인딩의 MISO 읽기만 계측한 호스트15조건 통과. FAT/GPIO는 mock이며 물리MCU 시험이 아니다.
- 실제 Questa FLOAT:정상156,비정상84조건(7원인×12위상),기존031 오검출120 유지,041/040 데이터·오류·OE/DIR·data_read를 매 에지 비교해 동일.
- 원인별 주소/position/pending 검증,최초값 보존과reset검증. 알려진12클록low→8클록high→10클록low 자극을 정확히 기록하고255포화를 확인.
- 전체 보드9조건:64KiB ROM,8192 payload,3화면 전달,STOP/재진입,PLL 상실,집계 및 신규SPI 원인/주소/태그 읽기,reset clear 통과.
- 생산 MCU GPIO 파형704샘플,명령/dummy 제외 응답328비트,2952행을 이번 RTL에 입력해 통과.
- 실제 map/fit/STA/ASM:1627LE/130LAB/44M9K/1101register/135pin/PLL1. 내부 최소setup2.243ns/hold0.159ns 이상.
- 외부38입력831경로/11출력895경로 미제약 유지. 계측 추가에 따른 배치가 달라졌으며 RTL 비교가 실기 타이밍 동일성 증명은 아니다.
- RBF218719바이트/BI3165981바이트,실제MCU rle_file_getc로 전체와EOF 일치. encoder원출력·증명된끝FF중복 처리 보존.
- 로그decoder 합성10조건,실제039/041 MCU·040/041 FPGA를 사용한 설치·복원8조건 통과. 물리SD 쓰기 없음.
- 첫 테스트 생성기에서 Python 문자열 구문 오류가 발생했다. 실패 생성물은 raw에 보존했고 수정 후 다시 실제 RTL 실행했다. 실행 wrapper가 가져오는 계측 모듈도 라이선스 시작 전에 구문 검사하도록 보완했다.

## 전달 및 후속 판단

새 MCU와 FPGA 두 파일을 함께 설치한다. 기존039 MCU·040 FPGA를 별도 백업하고 복원 경로를 유지한다.
실행표식 NES H1 037.nh1,화면 제목034와 ROM은 그대로다. 기준 그림은 실제034 에뮬레이터 캡처를 재사용했다.
한 번 재현한 뒤 새 nes-h1-last-041.txt를 회수한다. 정확한 cause/pending/read_address/position/count로
주소 전환 감시 오류·응답 전에 끝난 읽기·실제 선택 해제를 구분한 다음 해당 경로만 수정한다.
이번에는 모호한 집계 비트만을 근거로 추가 타이밍 수정이나 오류 무시를 하지 않는다.

040 증거228항목과 상태8파일 사본, GBC152해시,비NES registry,H0,원본frontend/upstream 보존.
041 실기 미실행. 실제NES producer/메모리/렌더러 통합과032 코어40LAB 여유·DMC 과제는 별도로 남는다.
