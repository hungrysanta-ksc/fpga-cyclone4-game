# NES222: ROM 공급 통신부 확인과 시작 메모리 수명 분리

## 작업 의미

221에서 ROM 검증은 통과했지만 SNES READY=3을 받지 못해5초 후 종료했다. 인덱스 검색·프레임 전송 전의 실패라 성능은 미측정이다.222는 **실기 시작 순서를 보강하고 리셋 전후 통신부 상태를 구분하는 변경**이다.221의 원인을 재현하거나 해결했다고 주장하지 않는다. 시작 복구 후 같은221 인덱스로 첫 레벨 성능 측정을 재개한다.

## 시작 순서

기존은 검증된 START 수락 후 SNES 리셋을 해제하고, 큰 RUN 작업 공간을 예약한 함수에서 READY를 기다렸다. 새 순서는 다음과 같다.

1. 검증된 START 수락 뒤, SNES RESET을 유지한 채 기존 E0 상태20B를 한 번 읽는다. ID F7/CRC8과 flags·accepted·retired·ACK 전부0을 확인한다. 이 응답은 부팅 ROM과 수명을 공유하는 host bridge가 시작을 허용했음을 뜻하며 SNES CPU 실행 증거는 아니다.
2. 유효한 빈 응답이면 기존 리셋 해제로 진행한다. 손상·비어 있지 않은 상태·전송 오류는 실행을 허용하지 않는다.
3. 첫 응답이 전부00 또는FF이면 무응답처럼 보이는 표본으로만 분류한다. 실제로 SNES가 RESET 중 /WR을 낮게 유지하면 기존 bridge의 idle_write 조건이 아직 충족되지 않을 수 있다. 따라서 이 경우를 무조건 차단하면 순환 의존이 생긴다. **기존처럼 리셋을 한 번 해제하고 기존1ms 정착 뒤 E0를 한 번 더 확인한다.** 두 번째 응답은 반드시 유효한 빈 F7이어야 한다. 반복 reset/START/패킷 전송이나 대기 시간 확대는 없다.
4. 기존5초 READY gate를 통과한 뒤 별도 noinline 함수에 진입해 프레임 메모리를 확보한다. 기존60초 runtime, 인덱스, 오디오·입력, 최종 display ACK 및 STOP/base/menu 정책을 유지한다.

첫 확인 실패는run_first_error7, 리셋 후 확인 실패는8, 기존 READY 실패는6이다. 리셋을 해제하지 않은 실패에서는 leave를 호출하지 않고 RESET 유지 상태로 STOP한다. 해제된 경우에는 기존 leave로 RESET을 먼저 잡고 STOP한다. CF86/CSS/전송 소유권 실패 시에는 기존 fail-stop을 유지하며 SD/메뉴 강행을 하지 않는다.

## 최소 기록

startup222 구조56B와 budget TXT만 추가한다. runtime budget reset은 이 기록을 지우지 않는다. 신규 SPI는 시작 시20B, 무응답 분기에서만 추가20B이며 게임 중 조회 증가가 아니다. raw 응답의 첫 dummy byte는 검증 대상이 아니다.

- `startup_reason`:0미실행/1정상빈응답/2소유권·RESET조건/3전송실패/4ID·CRC/5비어있지않음/6무응답형태.
- `startup_post_reason`:0은후속조회없음.6은두번째도무응답형태이며성공이아니다.
- `startup_reply_hex`, `startup_post_reply_hex`:각20B. 후속조회없으면후자는0.
- `startup_signals_hex`:하위byte=첫조회전,다음byte=첫조회후,세번째byte=후속조회후. 각byte RESET asserted/DONE/RDY가bit0/1/2. 정상pre-only는0707, 정상deferred는060707. 연속파형이나 FPGA 전체 식별자가 아니다.
- `startup_ticks`:SPI조회구간의10ms tick차 합계. 리셋1ms 및 READY 대기는포함하지않으며0도정상이다.

## 검증·선택

선택 arm02/test03/rtl01/check03/release01. arm01은처음의리셋전필수확인안이며채택하지않았다. RTL검토에서/WR-low 의존을확인해arm02의한번해제후확인분기로수정했다. check01은컴파일러가`.su`에`.isra`,ELF에는`.isra.0`으로남긴함수명이일치하지않아중단했다. check02부터유일함수/실제prologue8+31744+96=31848B와`.su`를대조해대응시켰다. 검사완화나임의스택면제아님. check02는arm01,최종check03은arm02다.

- 실제220 bridge/SPI/ROM RTL: RUN비활성, SPI idle미도달, /WR-low admission차단, 정상admission, 정상E0후현재212 ROM의벡터/첫명령읽기10검사.5개실제20B응답보존. 미선택MISO는fixture에서0으로투영했으며실제전기레벨증명아님.
- 실제222 C handoff/boot/STOP body:19개오류·성공경계+5개RTL응답재생=24검사. 리셋전무응답→리셋후정상,지속무응답,FF응답,ID/CRC/dirty/IO/소유권,기존READY시간초과/SPC오류/상태전송실패와포인터해제검사. 플랫폼·NES runtime은모델이며실시간ARM/RTL/65816전체결합이아니다.
- 전체ARM208952B/static28020B/RUN34984B/IRQ508B/여유1912B. 시작함수local stack은32B. 큰frame함수는31848B로READY후에만호출. 실제high-water측정이나미래mapper여유보장아님.
- budget최대3280/4096B,정확경계/부족버퍼거부및기록retention. post-STOP 저장tail은221과식별자만다름.
- 실행중runtime/planner/resident/sink/입력·소리코드및FPGA220/212ROM은221과바이트동일.221의243645요청차등검사와RUN9프레임검증을재사용하며반복실행하지않는다. 새FIT/ASM없음.

## 실기 판정

`startup_reason1` 또는`6 + post_reason1` 뒤READY3과실제게임화면을확인한다. reason1인데boot_reason5/stage0이면통신부admission이후의SNES reset/vector/bus/status 경계가남는다.6+post6이면리셋해제후에도hostbridge의정상응답이없다. raw와소유권·상태를함께봐야하며로그만으로특정배선불량을단정하지않는다. 성공하면첫레벨숫자1+A 및스크롤로성능자료를받는다.221/044반복·별도영상필수요청없음. saveSRAM/GBC164/기존봉인archive보존.
