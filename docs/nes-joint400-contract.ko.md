# NES 400 — 고정 transaction·read 완료 소유자·다음 입력 수신

PR132의 398/399 증거를 보존하고 같은 브랜치에서 구현한 실험이다. 생산 선택은 하지 않는다. 최종 수치는 `analysis/joint400-verification.json`의 선택 run과 함께 읽는다. 전체 MAP 통과는 장치 수용·FIT·STA·실기 통과를 뜻하지 않는다.

고정 SPI 필드 수신과 CRC8/A5/CRC16 terminal 판정을 physical endpoint에서 처리한다. queue의 byte-event IRQ 어댑터와 host 프로그램의 IRQ routine을 제거했다. E1 opcode에서 두 슬롯 중 하나를 예약하고, 길이·identity·CRC가 맞는 SS 종료에서만 accepted를 공개한다. 예약 중에는 저장 credit을 재사용할 수 없다. E9 plan과 EA의 실제 tag 개수 1~7, 짧은 EA7 retire를 구분한다. hint의 prelease·이전 display lease 배제·immutable guard는 유지한다. tag는 기존 metadata RAM 928..941에만 쓴다.

이는 고정 transaction 수신 교체다. descriptor·manifest·receipt의 일반 실행 프로그램 1,979명령과 4,096×18 ROM, 임의 IO 선택기, source writer·NES plan decode·SPI snapshot 본체는 남는다. 이를 삭제한 것으로 세지 않는다. 수신기만 고정하면 전체 제어 예산을 달성한다는 가설은 합성 결과로 기각됐다.

`nes_read_owner400`가 실제 read capture, latched data/address/token, read end, 독립 checker event, byte count·position 진행을 소유한다. CRC·coverage event는 read end에서 한 번만 발생한다. 완료 token 공개에는 정확한 read 수, pending 해소, checker ready, 동일 token, mask와 서명이 모두 필요하다. capture 승인·staging·DMA 완료·최종 표시 ACK는 서로 다른 사건이다. 독립 expected/CRC/coverage 및 중복 검사는 제거하지 않는다.

ARM은 현재 출력 record 발행과 retire 요청 뒤의 표시 대기 중 다음 N5 입력을 한 블록 수신·CRC 검사한 뒤 양보한다. 기존 plan/ACK 응답을 다시 확인하고, 아직 표시 대기가 남으면 다음 블록을 받는다. generation·pop·hint 상태를 보존하며 pop 후 빈 응답도 양보하므로 같은 packet을 두 번 pop하지 않는다. 이전 표시의 epoch/serial/raw_count를 별도로 저장하고, publish352는 실제 이전 final ACK가 끝난 identity만 공개한다. 다음 receiver가 부분 수신 중이어도 저장한 이전 identity와 resident/dirty의 정상 완료를 검사하며, 다음 identity를 대신 공개하지 않는다. 이전 표시 ACK·resident commit 뒤 deferred causal hint를 보내고, 부분 수신이면 나머지를 이어 받는다. 전체 입력을 먼저 받았으면 마지막 source packet과 semantic D5 commit을 보류했다가 이 순서 뒤 공개한다. 다음 planner·bank 재사용은 전체 입력 검사와 D5 뒤에만 한다. STOP은 저장한 표시 identity와 부분 수신·선행 수신 상태를 함께 취소한다. 일반 STOP 이후 정상 재시작 전체 증명은 별도 미완료 사항이다.

65816은 immutable 17B header를 00:6080..6090에서 B-bus 2180을 통해 기존 WRAM 0030..0040으로 DMA한다. 추가 WRAM은 없다. 실제 CPU component의 bounds·zero/ref·token·PPU·VBlank·ACK 검사는 유지한다. kernel은 1,778B로 40B 커졌다. 전체 resident 프로그램 증명은 아니다. 통합 bus 모델은 native event의 8 master-clock 간격과 200ns read pulse를 사용하며, 기존 task가 덧붙이던 200ns idle을 없앴다. 물리 pin timing signoff로 해석하지 않는다.

Header와 일반 DMA는 channel 0, 기존 HDMA는 channel 1~3 및 enable mask 2/14를 사용해 register 소유권을 분리한다. 연속 resident CPU에서 이전 표시의 HDMA가 CPU·일반 DMA와 경합하는 전체 지연은 아직 실측하지 않았다. native component service를 전체 CPU lockstep이나 WCET로 부르지 않는다.

통합 시험의 12 view reads는 기존 400ns read task이며 native indexed-loop의 모든 CPU 간격을 재생하지 않는다. 마지막 view 뒤의 pre-gate 비용과 PPU tail은 native 기록에 연결했지만, 이 차이와 이전 HDMA 경합을 포함한 resident 전체 일정은 미완료다. 따라서 아래 capture 여유는 동일 실행 모델의 관측값이며 실기 시간 상한이 아니다. 이 누락을 최적화 이득으로 세지 않는다.

호스트 metadata RAM A 포트는 immutable header 읽기, 보류 tag 쓰기, core 응답, staging 순서로 중재한다. stage atomic 구간에는 tag/header를 끼워 넣지 않는다. NES B 포트와 payload FIFO·source ring·plan bank의 기존 소유권은 유지한다. FIFO 3,584B·ordinary 예약 512B, ARM frontier 33, 출력 2슬롯·입력 4슬롯, MASK·SHIFT와 단일 확장도 유지한다. 세 번째 RAM 포트나 이전 표시의 조기 해제를 가정하지 않는다.

분리 시험에서 고정 수신 tag 1~7, EA7 generation 0/1/12/13/65530, E9 512B·16 plans, 오류 9건, STOP 256클록과 late DONE 32클록을 확인했다. 실제 host 12프레임·25,462 reads·20 오류/STOP·24,000 bounds vectors가 통과했다. 같은 M4의 71개 기록 계획 coverage, frontier 1,770건, END/MAP 소유권 3건 및 다음 입력 수신 중 이전 표시 identity 보존·D5 이전 STOP도 통과했다. 이는 긴 연속 일정이나 실기 전체 통과와 구별한다.

첫 전체 Quartus Lite MAP은 22,114 LE / 조합 17,376 / FF 8,903 / RAM 382,304bit다. 398 대비 −43 LE / −52 조합 / −13 FF / RAM 동일이다. 중복 없이 self cells를 세면 제어는 3,465개로 3,471개에서 6개 줄었고, 1,172개 예산보다 2,293개 많다. host+core+read owner 1,374, source·plan·hint 1,065, SPI 723, queue 215, tile 48, ROM decode 40을 모두 포함한다. 보존 codec/checker 2,333과 외부 11,578을 더하면 전체 17,376과 일치한다. 장치 조합 용량 15,408보다 1,968개, 155개 여유를 둔 15,253 목표보다 2,123개 많다. MAP LE도 장치 한도보다 6,706개 많다. 조합 예산만으로 LE·레지스터 packing·M9K 수용을 보증하지 않는다. FIT/STA를 반복해 해결할 상태가 아니다.

선택 연속 시험은 고정 capture 5,371,247, master 46,561ps, SNES phase 0, 제한 ROM window, 실제 M4 명령·공유 SPI·IRQ·2슬롯과 native CPU service를 사용한다. 최초 시각을 리셋해 얻은 ROM 위상 이득과 실제 연속 일정의 지연을 혼동하지 않는다. audit에 표시·capture·source 시작·materialization·ARM SPI 비용과 선행 수신 횟수를 기록한다. time01은 worker hook이 덮어써져 선행 수신이 꺼졌던 실패를 보존한 것으로, 통합 경로의 결과로 사용하지 않는다. live01은 전체 입력을 한 번에 선행 수신해 907의 최종 ACK 281.568036ms 뒤에도 ARM이 283.117339ms까지 돌아오지 않은 실제 실패다. 908 hint가 283.265018ms로 ROM 허용 구간을 놓쳤고 911 캡처가 누락됐다. live02의 한 블록 비교판은 cold 중 최종 스케줄러로 교체하기 위해 중단했으며 917 결과가 없다.

live03의 블록 단위 스케줄러는 12프레임 표시·ACK와 917을 포함한 캡처 10/10을 통과했다. 916 materialization은 416.204193ms로 기존보다 2.310776ms 빨라져 917 기한에 0.280833ms 여유가 생겼다. 908 hint는 282.576032ms에 채워져 ROM 구간 종료보다 0.166944208ms 빨랐다. 907/908 시작·ROM cycle은 기존과 같았다. 다만 914/915는 여전히 VBlank 24/26이며 23/25를 놓쳤다. 필요한 추가 선행의 하한은 마지막 source-job 완료와 반드시 뒤따르는 12 view reads·native pre-gate 시간을 기준으로 914 약 1.0322ms, 915 약 0.1094ms다. exact gate나 WCET 측정값은 아니다.

live03에는 source 전송이 없는 no-op에서도 plan cache와 WFI arm을 지우는 polling 버그가 있었다. 전체 SPI가 48,678→68,083B로 늘어난 비용을 숨기지 않고 원본·audit03을 보존했다. live04는 helper가 실제 source SPI를 수행한 경우에만 plan 상태를 갱신하도록 고친 동일 RTL의 재계측이다. current ARM은 text 36,800B / data 4B / BSS 48,792B로 398 대비 text +1,020B, BSS +64B다. 최종 선택은 최신 audit의 live04 결과를 따른다. 917 한 번의 수락을 918+ 장기 연속 일정이나 지속 60fps로 확대 해석하지 않는다.

최종 live04는 12프레임 표시·정확한 최종 ACK와 917을 포함한 캡처 10/10을 모두 통과했다. 916 source 시작은 415.595873ms, materialization은 416.178165ms다. 기존보다 2.336804ms 빨라졌으며 917 기한 416.485026ms에 모델상 0.306861ms 여유가 있다. ROM 71,964 request/reply와 입력 중 17,355 request/reply가 모두 짝을 맞췄고 pending은 0이다. 914/915의 VBlank 24/26 건너뜀은 남아 time goal은 false다.

live04의 추가 선행 하한은 914 약 1.0322ms, 915 약 0.0833ms이며, 최대 warm 표시 완료 간격은 34.044940ms다. 하한은 모델의 마지막 job·view service로 계산한 필요 조건일 뿐, 모든 미측정 resident 비용을 포함한 충분 조건이 아니다.

12프레임의 실제 M4 명령은 8,735,423→8,853,510, SPI는 48,678→52,962B다. 앞선 polling 버그판보다는 15,121B 줄었지만 398보다 4,284B 늘었다. source peek·응답·IRQ 비용을 공짜로 취급하지 않는다. 관측 component stack 최대 1,288B는 기존과 같다. 이는 CPI1·foreground IRQ/물리 SPI 모델이며 하드웨어 CPU cycle·full RUN WCET나 resident 전체 stack 증명이 아니다.

실기 첫 시험은 아직 가능하지 않다. 실제 장치에 들어가는 전체 이미지와 새 clock/IO/CDC의 FIT·STA, 짝이 맞는 resident ARM·65816 이미지 및 전체 RAM/stack·입력·소리·STOP 복구 패키지가 먼저 필요하다. 제한된 첫 보드 시험은 MMC4/5나 완전한 60fps 전체 검증을 기다릴 필요가 없지만, 현재 수치로 달력상의 완료 날짜를 약속할 수 없다. 기존 375 RTL·377 ARM·227 및 GBC164·saveSRAM 복구 기준은 보존한다.
