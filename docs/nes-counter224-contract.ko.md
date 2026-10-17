# NES224 카운터 응답 판정 경로

PR122의 NES223 geometry 전송 후보를 실기에 배포하기 위한 후속 단계다. 기존223 기능 검증을 통과해도 전체 implementation setup이 -0.006ns였으므로 배포하지 않았다. 대상은 `reader.check_response_address[5]`에서 `control.commit_clear`까지의 6 LUT / 5.441ns 경로였고, interconnect가3.414ns였다.

## 작업 의미

223의 실제 전송량 절감 구현을 타이밍 기준에 맞춰 실기에 가져가기 위한 변경이다. 프레임을 지연시키거나 로그를 늘리는 기능이 아니다. 이 단계 자체로 FPS가 올라갔다고 주장하지 않는다. NES223 wire2231과 ARM 후보는 그대로 사용하며224는 이 로더 경로 수정·검증의 단계 번호다.

## 변경과 보존 조건

기존19bit 응답 주소 비교가 공용 오류 경로를 거쳐 pending 카운터 clear/inc를 승인했다. 각 pending action 가까이에 low9bit/high10bit 응답 조건을 별도로 보존한 뒤, 같은 mem_clk edge에서 AND해 `commit_clear/inc`에 기록한다. 새 레지스터나 파이프라인을 추가하지 않는다.

`pending`, fault, SS-high, check_fault, CHECK 중 boot_fault, check_enable/busy와 response 주소 소유권은 원래 판정 edge 그대로다. C3에서 수락한 counter effect는 C4에 적용되고, 이후에 도착한 오류로 이미 수락한 effect를 취소하지 않는다. 비동기 reset은 취소한다. clear가 inc보다 우선하는 것도 유지한다. 오류 코드 우선순위·READ 데이터·STOP·SPI command/CRC/ACK 및 기존 carry8 사전 계산은 바꾸지 않는다.

선택 source01은 봉인된223 source01 전체90파일을 검증해 복사한 후 `nes_rom_spi.sv`만 수정한다. clock/SDC/qsf/seed/핀 및 배경 exporter/ARM/입력/소리/저장SRAM은 동일하다. 이 변경이 19bit 비교를 없애는 것은 아니다. 논리적으로 동일한 비교를 각 소비 경로 가까이에 분리하는 것이므로 효과는 전체 FIT·STA 결과로 판정한다.

## 기능 검증

선택 test02. 실제 기존/수정 RTL을 같은 입력으로 비교한다.

- 491520 counter 조건 ×2 edge =983040 edge. reset/fault/pending/SS/check_fault/boot_fault/enable/busy/response, 두 pending action, 두 prior commit bit,19개 주소 bit mismatch와일치, counter0/255/최대값을 교차한다. acceptance·기존 counter effect·다음 edge effect를 독립 기대값으로 확인한다.
- 기존1056768 state edge/1024 followup sequence와 real SPI14016bit,100 READ/7 ACK/19 corrupt/72 cancel/2 overlap 회귀를 통과했다.
- high 비교 제거,low 비교 제거,pending gate 제거의3개 음성 대조는 모두 새 counter 검사에서 실패했다.
- 임의로 연속 commit을 주입한 상태는 실제2us 이상 간격 SPI에서 도달하지 않는다. 이 경우에는 원래 carry8 레지스터의 이전 값을 따라 비교한다. 정상 간격으로 수락하는 실제 serial 시험은 따로 통과했다.

첫 test01은 두 회로 간 차이가 아닌 시험 기대값 오류로 중단됐다. 임의의 연속 prior/current commit에 일반 정수+1을 기대했지만 기존 회로는 이전 carry8을 사용한다. RTL은 바꾸지 않고 기대값만 기존 carry 단계에 맞춘 test02가 통과했다. test01 원본과 수정 전 harness는 보존한다.

이 검증은 동일 사이클 로더 회귀이며 전체 게임/실기/60fps 시험이 아니다. 223 exporter와 C receiver·전체ARM 검증은 소스 해시가 같은 부분만 재사용한다. 결과의 최종 채택 여부는 `analysis/counter224-verification.json` 및 HANDOFF에 기록한다. 전체 timing/CDC/조건부 IO를 통과하기 전에는 설치 ZIP을 만들지 않는다.

## 다음 단계

전체 보드 기준을 통과하면 실제 SNES212 ROM을 같은 route에 넣고 ROM-only CDB/ASM·netlist4096B 일치를 확인한 뒤 NES223 이름의 paired 시험판을 만든다. 첫 레벨 숫자1+A → 오른쪽+B 유지/A 반복 스크롤에서222와 비교한다. 변경 없는222/044 반복 시험은 요구하지 않는다.

geometry 압축 외에 scroll-aware map·C 처리·SNES service 비용을 포함한16.67ms 예산은 여전히 남아 있다. 합성 부하의46.73% payload 감소를 실기 FPS 개선율로 부르지 않는다. 미래 mapper fetch-time CHR/row-alt/mask/epoch/base-bank/finaldisplayACK, GBC164와save SRAM 보존 조건은 유지한다.

## source01의 결과와 source02 수정

source01 전체 FIT15180LE/8353FF/962LAB/47M9K, strict counter 경로는-0.006→+0.878ns로 개선됐다. 그러나 command[6]→raw_run이 nominal/strict-0.013ns로 남았다. 이 경로는2LUT/5.883ns 중 interconnect4.473ns(76%)였으며, 외부 실행 상태를 저장하는 enable에 명령 판정이 연결돼 있었다. source01은 미채택으로 보존한다.

source02는 raw_loaded/raw_run/raw_ready/raw_load_ready 네 비공개 레지스터를 매 mem_clk마다 샘플링한다. 실제로 C1에서 sampled=1일 때 사용하는 값은 바로 전 C0 edge의 값이므로 소비 시점을 바꾸지 않는다. command 판정은 sampled/raw_causes/raw_select에 남는다. 단순히 live 입력을 C1에서 읽으면 C0와 C1 사이에 바뀐 입력이 섞이므로 그런 변경은 하지 않는다.

이 네 레지스터는 sampled=0일 때 기존과 달라도 소비되지 않는다. 따라서 시험은 C0 publication(sampled=1)에서 네 값이 일치하는지 확인하고, 나머지 소비 상태·명령 출력·카운터 효과는 매 edge 그대로 비교한다. 별도1024조건은 C0의4bit 외부값과 C1의4bit 값을 모두 바꾸며4명령의 pending_causes가 원래 C0 값을 사용하는지 확인한다. C1 live RUN을 잘못 대입한 음성 대조도 포함한다. 이 관측 조건 완화는 소비되지 않는 네 비공개 샘플에만 적용한다.


source02의 test03은 정상 후보 회귀를 통과했지만 live-RUN 음성 대조를 잡지 못했다. START의 미검증(verified=0) 오류가 외부 RUN 검사 결과를 가린 시험 설정 때문이었다. 원본 로그와 수정 전 harness를 보존하고, test04에서는 각 명령의 기존 lifecycle 조건을 충족시켜 외부 입력 변화 자체를 관찰한다. RTL은 test03과 test04 사이에 바꾸지 않았다. 이 검출 실패를 제품 통과 근거로 사용하지 않는다.


## 선택 source02 검증 결과

source02/test04/mapfit02/timing02/io02/paths02를 선택했다. counter983040edge/state1056768edge/C0-C1 1024조건·실제SPI 및4음성 대조가 통과했다. 전체 FIT15249LE/8353FF/961LAB/47M9K이며 여유159LE/2LAB/9M9K다. 세 코너 nominal/implementation setup 최솟값은 모두+0.276ns, hold는+0.147ns다. 223 후보 대비+19LE/0FF/0LAB/0M9K이며 seed/clock/SDC 변경은 없다.

CDC3984행/45 sole-fanout first stage/새 미분류 direct crossing0개, held6.799ns/Gray6.614ns 및96 epoch reset 레지스터의576경로를 확인했다. 조건부 IO 기준도 통과했으며 전체 전기적/MTBF signoff는 아니다. inherited reset crossing과기존 검증 범위는223과 같다. ARM은223/check01의209168B/static28020/RUN34984/IRQ508/여유1912B를 바이트 동일하게 재사용한다.

보드 gate와 배포 gate는 별도다. 최종 설치 승인과 파일 해시는 `analysis/release223-verification.json`의 trial_ready 및 paired ROM 검사 결과가 기준이다. 이후의 물리 FPS 개선은 사용자 실기 시험 전까지 미확정이다.
