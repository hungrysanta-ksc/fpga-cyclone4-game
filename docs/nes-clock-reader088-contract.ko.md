# CF87 MCU reader088 계약과 다음 통합

088은087 관측 회로를 읽는 실제 MCU GPIO C 코드다. CF87 RTL/fit은 변경하지 않았다. 아직 부팅 main에 연결하거나, 관측 이후 mini/TXT/화면까지 실행하는 전체 펌웨어를 만들지 않았다. ARM 결과도 **STM32F401용 오브젝트 컴파일**이며 링크된 설치 펌웨어가 아니다.

## 진입과 종료

`nes_clock_collect088()`은 호출자가 CF87을 구성하고 RESET을 유지하며 USB IRQ를 차단한 상태에서 호출한다. 기존 diagnostic scope가 활성이고 공유fault·SD offload·block transfer·log쓰기 권한이 없어야 한다. FPGA DONE을 확인하고 실제CF query에서87을 요구한다. MCU_RDY를 클록 정상 판정으로 사용하지 않는다.

SPI busy는 최대1000회/1µs의 기존 bounded timer 호출로 기다린다. PB3/4/5와 SPI1 상태를 저장하고 mode0 GPIO로 전환한다. 명령·데이터 bit는 low2µs/high2µs이고 byte 뒤2µs,CS 전후2µs를 둔다. 각 동작 전후 RESET/USB/DONE/공유fault 및 원래 session 예산을 검사한다. 최초fault를 지우거나 새 session 예산으로 다시 시작하지 않는다.

정상 관측 종료에는 CS HIGH 후 GPIO/SPI 설정을 복원한다. 공유fault 뒤에는 CS를 HIGH·SCK를 LOW로 취소하고 SPI를 disabled/GPIO 상태에 남긴다. 잘못된 응답이나 타이머 고장 뒤 원래 AF/SPI를 다시 켜서 뒤따르는 IO를 유발하지 않는다. reader는 RESET을 해제하거나 USB IRQ·로그 쓰기를 허용하지 않는다. reentry는 기존 report/saved GPIO를 덮지 않고 공유fault로 거부한다. 호출자는 유효한 report 포인터를 제공해야 한다.

## 관측과 판정

- 처음 읽은 안정된 snapshot은 기준값으로 보관하고 성공 샘플로 세지 않는다. 전원 기동 동기화 이력이 들어가는 sequence1은 버린다. 그 뒤 새 sequence의 snapshot2개를 수집한다. 같은 값의 반복은 새 측정이 아니다.
- 각 후보는C0를 두 번 읽는다. 같은 sequence의count/window/divisor/예약 값은 같아야 한다. live와ever-gap은 두 frame 사이 정상적으로 바뀔 수 있으므로 두 번째 값을 사용하고 ever-gap이 지워지는 것은 거부한다. 서로 다른 sequence 사이에 걸친 한 쌍은 버리고 다음 query를 기다린다. CRC를 제공하는 프로토콜은 아니며, 동일한 일관된 손상까지 모두 검출한다고 주장하지 않는다.
- ID87,flags상위0,WINDOW8000000,divisor16,예약0,valid/sequence/count 관계와count≤4000000을 검사한다. 순번 회귀/포화FFFFFFFF를 거부한다. 누락된 순번이 있으면 안정된 관측으로 분류하지 않는다.
- 구간2개가 모두valid/live이고 마지막구간gap이 없으며count>0이면 `ACTIVE`, 두 구간 모두live0/count0이면 `ABSENT`, 그 외나순번누락은 `UNSTABLE`이다. ACTIVE는 원시 활동 관측이지20~22MHz 적합성·실측 주파수·CF86 외부 타이밍 승인이 아니다.
- 전체 호출은100Hz tick450개(4.5초)와 query512회로 제한한다. 시간 예산은 bit/delay 사이에도 적용하며 wrap 차이를unsigned로 계산한다. frozen SysTick에서도512회 뒤 종료한다. TIMER 자체 정지는 기존077 bounded timer가 별도 fault로 처리한다. CPU가 실행을 멈춘 상황까지 소프트웨어가 종료한다는 뜻은 아니다.
- 진행하지 못하면 `NO_PROGRESS`와 확보한 원시값·경과tick·attempt/frame수를 남긴다. ACTIVE/ABSENT/UNSTABLE/NO_PROGRESS는 관측 결과라서 공유fault를 새로 만들지 않는다. 전송/형식/타이머/소유권 오류는 false와 공유fault이며 이후SD/SRAM/FPGA 구성 IO를 금지한다.

## 실제 수행한 검증

호스트1966검사는 실제reader C를 컴파일하고 레지스터·시간·MISO를 모형화했다. 정상/부재/불안정/진행없음·tick wrap/freeze,응답15byte 각bit손상120개,delay330위치·공유검사1500위치 실패,RESET/DONE/USB/SD/busy/reentry를 포함한다. flags중live/ever-gap의 정당한 변화와 전송 오류를 동일하게 취급하지 않으며 무결성CRC를 대신했다고 주장하지 않는다.

같은 C가 만든 GPIO write와 **소비한 모든 MISO bit**를 CF87 RTL 핀에 재생했다.20MHz 기준이 있는 경우와 없는 경우 각각541frame/73456응답bit/295453event를3.005436초 동안 비교했다. 둘을 합쳐146912bit다. GPIO 시간은 모형의 명시적delay에 기반하며 실제 MCU instruction 지연·IRQ jitter·기판 전압·SPI 외부 타이밍을 측정한 것이 아니다. RESET/USB/GPIO ownership의 전후 검사는 C호스트에, 실제 FPGA 핀 통신은 RTL replay에 각각 근거한다. 전체 부팅/SD/TXT/화면 session은 아니다.

최종host05에 중복 snapshot 내용 손상 검사를 추가했지만 정상 trace는host04와 바이트·SHA가 같다. 정상wave01은host04 trace를 사용했고 최종host05와 같음을 검증한다. absent06은 부재용 실제C trace다. 생산 C/헤더는ARM object와 같은 해시다. CF87 생성소스2개와087의새fit/STA/배선 경계는 그대로다. 첫 host 빌드의 MinGW printf64bit 호환 오류는ANSI stdio 설정으로 수정했고, 초기불안정 모형이valid0에완료구간gap을 잘못 넣어 거부된 기록도 보존했다.

C 인과 대조는 중복 데이터 비교·전체시간 제한·RESET 소유권 검사를 각각 없애면 기존 검사가 실패함을 확인한다. RTL의분주값을 잘못 바꾸는 대조도C가 소비한MISO 비교에서 실패한다. 실제 ARM은Cortex-M4/hard-float 헤더/호출을 컴파일한21912byte ELF relocatable object이며, 이 크기를firmware.stm 크기로 보고하지 않는다. 기존077 timer/runtime는 변경하지 않았고 실제 하드웨어에서 새reader와 함께 실행한 것은 아니다.

## 다음 작업: TXT/화면까지 한 session

1. CF87의고정fit을별도사본에서ASM/압축하고 payload/configuration용bounded sink를 마련한다. 기존084 main/초기marker 이후 RESET을 재확인한 채 관측 후보를 구성한다. reader를 호출하고 report를RAM에보관한다. 이 단계는 아직 구현/링크하지 않았다.
2. 전체60초/100만IO 예산은 FPGA구성·reader·mini복귀를합산해서검사한다. 정상reader만389972회공유검사를소비하므로 기존byte별configuration검사까지단순히이어붙이면예산을넘을수있다. 실제payload길이/호출수를계측하고검사중복을줄이거나명시적으로분리된bounded phase를설계한다. fault를지우거나매retry마다예산을리셋하는방식은금지한다. 공유fault가 없는 관측 결과만 이검증된예산아래mini로복귀해SD 초기화·mount·공간검색·실제writer/readback·화면에 연결한다. ABSENT/NO_PROGRESS도 명료한 결과로기록한다. false/공유fault뒤복귀나저장을시도하지 않는다. 항상저장성공화면을보이게하려고보호를우회하지 않는다.
3. 새TXT는원시16byte×3,sequence/count/window/divisor/flags,관측판정,elapsed/attempt/frame,가정CLKIN주파수와후보ID를담고 사람이읽을요약을추가한다. 단순반복알파벳저장시험으로대체하지않는다. 실제한session nativeSD/mini 경계와최종ARM callsite를검증한다.
4. SPI 외부조건/구성전환/RESET소유권과동일ASM/ARM/복원manifest가준비된후report-onlytrial을전달한다. 사용자실기에서새TXT/영상을회수한다. 기존084 저장·044복원/menu/GBC PASS, 알려진부품/LED/분해/PCUSB 질문은반복하지않는다. CF86 외부PSRAM/비동기차단/공통고장·최신코어MCU/전체80-96KiB는여전히별도다.

재현 도구는 `test_nes_clock_reader088.py`(pinned084runtime headers), `run_nes_clock_reader088.ps1`(기존FLOAT), `compile_nes_clock_reader088.py`(pinned084headers), `verify_nes_clock_reader088.py`(동결근거)다. 각작업은새절대ASCII출력경로를사용한다. 공개clone만으로개인동결자료까지재현된다고표시하지않는다. 준비도4완료/7부분/1미완료,installable=false를유지한다.
