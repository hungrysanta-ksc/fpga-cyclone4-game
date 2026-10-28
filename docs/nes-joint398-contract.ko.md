# NES398: 실제 개수 EA와 RAM 바이트 실행기의 전체 비용

## 판정

398은 시간·회로 공동 목표를 충족하지 못해 채택하지 않는 실험 구현이다. production을 변경하거나 보드 구동을 승인하지 않는다. FIFO3584B·ordinary512B·ARM frontier33·2슬롯을 유지하고, 실제 개수의 EA와 host/queue/plan/SPI/hint 제어를 연결했다. **NES source/plan의 나머지 본체, SPI 응답 snapshot, 실제 read/token 처리는 남아 있다. 이를 삭제한 것으로 계산하지 않는다.**

독립 검사·STOP·최종 ACK·VBlank를 유지한다. 현재 전체 Lite MAP은 22,157LE / 17,428comb / 8,916FF / 382,304 logical RAM bits다. 396보다 715LE / 680comb / 117FF 줄지만 RAM은 72,192bits 늘어난다. 조합 논리만으로도 장치 한도를 2,020개 초과한다. 155개 여유를 둔 전체 목표까지는 2,175개가 더 필요하다. FIT/STA는 실행하지 않았다.

## 실제 교체와 남은 경계

|경계|398에서 실행되는 처리|남긴 처리|
|---|---|---|
|ARM|중복을 제거한 실제 n개 tag, EA 길이 `14+2n`과 CRC16 생산|frontier33 예약·accounting·IRQ·공유 SPI 생산 순서|
|host|descriptor 범위·manifest/RLE·receipt/fence/view 순서를 바이트 프로그램으로 실행|실제 SNES read의 CRC·coverage·token·PPU 최종 ACK 신호|
|queue|같은 프로그램이 identity·길이·SS 완료를 검사하고 게시|2슬롯 RAM·명령 시점 예약·accepted/retired/consumed namespace|
|source|공동 IRQ의 footer 서비스와 공통 SPI request 필드 공급|NES record writer·Gray CDC·D4 첫 응답 마감 검사|
|plan|E8/E9/EA 완료·retire 검사를 공동 프로그램에서 실행|2×512B RAM·NES shape/lease 검사·396 NES cursor|
|SPI|길이·generation/token·number의 공통 바이트 공급|SS/SCK·고정 snapshot·CRC 이동·종료 서명 마감|
|hint|identity 검사를 공동 프로그램에서 실행하고 tag를 공통 문맥 RAM에 저장|NES의 tag 읽기·한 건씩 ROM 요청·취소 drain|

기존 host 의미 FSM과 별도 descriptor 범위 검사 인스턴스를 제거했다. 원래 본체를 다른 이름으로 감싼 뒤 전부 절감으로 세지 않는다. 특히 source/NES plan과 SPI snapshot의 비용은 아래 제어 합계에 계속 포함된다.

FPGA 제어 프로그램은 2,410개의 18bit 명령이며 실제 ROM은 4,096×18bit, 즉9,216B다. 마지막 영역의 fault 명령도 RAM 비용에 포함한다. 512word 가정이나 4KiB 상한을 맞추려고 실제 비용을 숨기지 않는다. host와 IRQ는 분리된 return PC를 사용하고, 완료되지 않은 IO 대기는 SPI IRQ가 선점한 뒤 같은 명령을 다시 실행한다.

## RAM 포트와 소유권

tile/context RAM은 기존 1,024×8 TDP를 유지한다. 0..31은 tile mailbox payload, 32..799는 stamp, 800..1023은 공통 문맥이다. 실행기의 문맥 주소는 0..223으로 제한한다. 주소224 이상은 grant를 차단하고 fault로 전환해 tile/stamp 영역으로 wrap하지 못한다. 현재 tag는 문맥128..141, 즉 물리928..941에 저장한다.

host 포트는 프로그램·SNES header·FIFO stamp/binding이 중재한다. 진행 중인 payload copy·stamp write·binding capture는 빼앗지 않는다. NES 포트는 tile 쓰기와 hint tag 읽기를 공유한다. tag당 네 NES 클록의 읽기 동안 tile ready를 내린다. 별도 tag RAM이나 세 번째 RAM 포트를 만들지 않는다. 입력 source RAM과 두 plan bank의 포트·CDC는 계속 별도 비용이다.

수신 슬롯은 E1 명령 시점에 예약한다. SS가 끝난 뒤 프로그램이 검사하는 동안에도 그 슬롯을 credit으로 공개하지 않는다. 검증 완료 후 accepted에 게시하며, packet_ready에는 게시된 슬롯만 보인다. storage_empty는 미게시 예약까지 비어야 참이다. 실제 SNES 소비 완료·최종 표시 ACK는 별도다.

## 실제 마감에서 바꾼 역할

E9 마지막 A5 처리를 바이트 IRQ로 미루면 실제 ARM 일정의40.596971ms에서 SS 종료와 이벤트가 겹쳤다. 마지막 byte 뒤의 SS 유지 시간은 바이트 간격과 다르다. 따라서 CRC8·A5와 EA의 마지막 CRC16 수신은 고정 체크섬 경로에서 즉시 처리한다. 펌웨어가 이 검사 결과를 임의로 쓰는 포트는 두지 않는다. 공동 실행기는 해석과 완료 승인을 맡는다. 수신 클록이나 SS 시간을 늘려 통과시키지 않는다.

## 전체 비용과 예산

MAP은 같은 전체 보드 경계에서 Quartus Lite로 실행했다. parent inclusive 비용을 child self 비용과 더하지 않는다. 기능·합성의 RTL/프로그램 해시는 최종 분석에서 대조한다. 논리 RAM bits는 물리 M9K 배치 성공을 뜻하지 않는다.

|동일 전체 보드 경계|MAP LE|comb|FF|logical RAM bits|
|---|---:|---:|---:|---:|
|396 기준|22,872|18,108|9,033|310,112|
|실제 개수 EA만 연결|22,899|18,131|9,045|310,112|
|398 공동 실행기|22,157|17,428|8,916|382,304|

EA만 바꾸면 회로는23comb 늘어난다. 공동 실행기의680comb 감소와 tag 전송의 시간 이득을 같은 원인으로 묶지 않는다.

최신 전체 결과의 제어 합계는3,471comb다. 397의1,172개 예산보다2,299개 많다. 독립 codec/validator는2,335개, 그 밖의 전체 회로는11,622개다. `3,471+2,335+11,622=17,428`으로 전체와 맞춘다. 기존 경계의4,027개에서 실제 제어 절감은556개다. 나머지 전체 감소는 같은 MAP의 retained/outside 변화로 구분한다.

host self938 + byte core484 + ROM decode40 =1,462개다. 다른 제어를 무료로 모두 제거한다고 가정해도 이 부분만으로1,172개를 넘는다. 이 실행기를 선택한 채 나머지 FSM을 감싸는 방식으로 목표를 달성했다고 주장할 수 없다. 본체 교체 미완료와 예산 실패를 모두 기록하며, 다음 구조 판단에는 host의 실제 read/publication 제어와 source/plan 역할까지 포함해야 한다.

현재 retained/outside를 고정한 조건부 전체 상한도 `15,253−2,335−11,622=1,296`개다.1,172개 예산을 이 숫자로 완화하지 않는다. 그 상한보다도 host+실행기+ROM1462가166개 많다. 따라서 남은 source/plan/SPI를 같은 실행기에 단순 흡수하는 추가 작업을 선택하지 않는다. 실제 read/publication 상태·metadata 포트 중재와 source/plan 데이터 수명까지 바꾸거나 역할·장치 용량을 재비교해야 한다. 이 판정은398의 구체적 구현에 대한 것으로 모든 공동 실행기의 불가능성 증명은 아니다.

1,172개는 필요한 조합 논리 예산이다. 이를 만족해도 FF/LUT packing·M9K·LAB·배치·타이밍 성공이 보장되지는 않는다. MAP의 LE 감소를 기존 FIT의 부족분에서 빼지 않는다.

## 실제 ARM에서 드러난 END 소유권 오류

강한 backpressure를 연결한 live09에서는915의 최종 ACK가 거부됐다. 원인은 FPGA 검사가 아니라 ARM의 두 map 생산자였다. 기존 MAP fragment 경로가 전송을 마쳤는데 증분 whole-map 생산자가 부분 준비 상태로 남아 있었다. END를 발행한 뒤 drain이 그 생산자를 재개해 AB MAP을 추가 전송했다. 원시 기록의 END는434.690911ms, 뒤따른130B AB MAP은435.286732ms다. 이때 queue가 비지 않았으므로 최종 ACK 거부가 맞다.

기존 MAP fragment를 발행할 때 증분 생산자를 비활성화하고, END는 SPI 발행·credit 대기 전에 terminal phase를 예약한다. incremental 경로가 먼저 완료한 경우 legacy 경로는 기존처럼 생략한다. ACK의 storage_empty·tile_empty·fence·12read 조건을 완화하지 않았다. 이전 ELF에서 중복을 재현하고 수정 ELF의 세 소유권 전환, frontier1,770건,71개 recorded-plan의 정확한 job/payload/map coverage를 검사했다. 이는 별도의 endpoint component 검사이며 전체 일정의 대체 증거가 아니다.

ARM text는35,780B로396보다4B 늘고 data4B/BSS48,728B는 같다. component의 observed stack304B는 전체 resident/IRQ stack 한도가 아니다. component와 live ELF는 GCC 임시 assembler FILE symbol 때문에 원시 해시가 다르므로 각각 보존하고, 모든 PT_LOAD byte·주소·크기·속성과 FILE을 제외한 모든 named symbol 주소를 대조한다. 전체 일정에서는 실제 live ELF를 사용한다.

공동 실행기의 지연으로 응답·poll 비용이 증가한 것도 포함한다. 실제 SPI 총량은 아래와 같고 source 수신의 dummy TX·header·출력·commit까지 센다.908의 실제 ARM 명령 보고값은 EA 단독549,476에서 공동판565,855로16,379개 늘었다. 명령 수와 wire 시간을 실제 일정에 다시 더하지 않는다.

|프레임|396 SPI bytes|EA 단독|공동 실행기|
|---|---:|---:|---:|
|905|16,233|16,233|17,031|
|906|10,916|10,916|11,742|
|907|1,958|1,958|2,140|
|908|1,604|1,456|1,582|

908은 실제3tag/20B를 전송한다. 공동판의 hint 완료282.736388ms는 ROM 창 끝282.742976208ms보다6.588208µs 이르다. EA 단독 완료282.733035ms보다3.353µs 늦지만 VBlank17을 지킨다. 이는 해당 위상의 관측값이며 다중 위상의 최악 지연 증명이 아니다. `hint_start/end`는 ARM 전송 호출의 마커이며 물리 SS edge와 구분한다.

## 증거와 적용 한계

실제 개수 EA만을396 RTL에 연결한 분리 시험에서는908 VBlank17·911 캡처를 확인했다. 그러나917 캡처를 놓쳤으므로 연속60fps 성공이 아니다. 이 분리 실행은 END 소유권 수정 전이다. 최종 공동판은 새 ARM을 실제 실행해905..916의12프레임 표시·최종 ACK를 마쳤다.915의 최종 ACK도 정상이며 END 뒤 추가 MAP은 없다. 유일한 종료 실패는 `capture coverage367`이다. 조건을 완화하지 않은 결과는 다음과 같다.

|항목|최종 공동판 live11|
|---|---|
|cold906 완료|230.788676ms, 고정907 기한250.090632ms보다 빠름|
|907 시작 / ROM cycle|264.333059ms / 5,677,131,396과 정확히 같음|
|908 시작 / ROM cycle|280.972517ms / 6,034,500,396과 정확히 같음|
|908 표시|297.832032ms / VBlank17,396의 VBlank18에서 개선|
|911 캡처|316.648558ms 승인, 표시·최종 ACK도 완료|
|914 /915 표시|VBlank24 /26, 각각23 /25를 건너뜀|
|다음 캡처|10회 중9회 승인, 첫 누락917/416.485026ms|
|916 source 시작 / materialized|417.932677 /418.514969ms|
|최대 warm 완료 간격|34.043308ms(913→914), 지속60fps 실패|
|ROM|71,962 request/reply pairs, 입력 출처17,761쌍, pending0|

917의 기한보다916 source 시작이1.447651ms, materialized가2.029943ms 늦다.2.029943ms는 이 입력 소유권 기한의 관측 부족분이며 모든 VBlank·ARM·ROM 위상을 포괄하는 최적화 필요량이 아니다. 개별 warm 프레임의 시작 시각을 재정렬하거나 ROM 위상을 초기화하지 않았다. 함수별 instruction 보고값도 전체 일정의 바깥에 더하지 않는다.

새 바이트 프로그램의24,000개 독립 범위 검사,12프레임25,462 actual read,20개 오류·STOP 검사,EA1..7·E9 뒤 EA7 retire·잘못된 identity/CRC·중간 STOP 검사를 수행했다. EA7은 generation0/1/12/13/65530에서 확인하고 E9는512B/16plan 경계를 검사했다. repeat16/repeat32의1,100B 출력은 각각512+512+76으로 나눠 같은 canonical bytes26,560개를 실제 읽었다. 문맥 주소224는 tile/stamp write 전에 거부하고 STOP 뒤256클록의 RAM 동결을 확인했다. 실제 hint ROM request 한 건을 대기시킨 뒤 STOP하고, 정지 중256클록과 해제 뒤 늦은 response32클록에서 request·DONE 부활이 없는 것도 확인했다. 정상 새 프레임으로 복귀하는 전체 STOP 회복 시험과는 구분한다.

선택 증거는 build16/map15/live11/host10/exec07/hint07/repeat02/repeat03/arm02/armguard02/owner04다.33개 기능 RTL·ROM 프로그램을 전체 보드 합성 입력과 대조했다. `analysis/joint398-verification.json`은319개 파일 해시와 비용·일정·실패 조건을 검증한다. `audit_passed=true`는 보고가 증거와 맞다는 뜻이며 `time_goal_met=false`, `area_goal_met=false`를 함께 기록한다. 중간 PASS를 최종판의 전체 PASS로 대체하지 않는다. 원시 로그·전송·바이너리와 중간 실패는 workspace 상위 `probes/nes-joint398/`에 보존하며 기존 private fixture가 필요한 재현 도구다.

65816 서비스는 기존 실제 CPU에서 얻은 bus/PPU 이벤트를 연결한다. 전체 resident 펌웨어·CPU lockstep·ARM WCET·71 heavy/multiple ROM phases·정상 STOP 뒤 복구·MMC4/MMC5·실기60fps는 승인하지 않는다. production375RTL/377ARM/227/GBC164/saveSRAM을 유지하며 자동 merge·유료 라이선스 구매를 하지 않는다.
