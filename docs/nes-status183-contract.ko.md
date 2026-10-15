# NES183 — 다음 블록 상태의 중복 조회 절감

## 작업 의미와 한계

182 실기에서 표시 완료율은 약26% 증가했지만 여전히 평균351ms/완료였다. 이번 변경은 FPGA→MCU 경로에서 이미 검증한 준비 완료 상태를 다시 묻는 왕복을 줄인다. **작은 전송 개선이며60fps 달성이나 대폭 개선을 약속하지 않는다.** 큰 구조 과제는 조각마다 멈추는 전송을 bounded FIFO/credit 방식으로 바꿔 수집·전송·표시를 겹치는 것이다.

처음 검토한224바이트 타일 버퍼는 채택하지 않았다. 실제182 converter가 이미 OAM/CGRAM 임시 공간으로 BG240B·OBJ224B를 묶고 있었다. 단일 타일을 넣은 합성 입력의1158→99packet 결과는 현재 생산 경로의 개선 근거가 아니다. 그 후보의 추가228B상시RAM·ZIP·검증은 private probes/nes-batch183에 폐기 사유와 함께 보존하며 설치하면 안 된다. 이번 선택은 probes/nes-status183이다. 앞으로 최적화 전에는 실제 배포 converter의 callback 크기까지 먼저 확인한다.

## 선택한 변경

기존 순서는 D0 STATUS→D1 READ→D2 POP→D0 POP확인, 다음poll에서 다시 D0 STATUS였다. POP확인 응답이 다음블록의sealed=1을 이미 알려준 경우에만 응답8바이트를 저장한다. 다음poll은 저장응답의CRC/flags를 재검사하고 곧바로D1로 진행한다.

- 저장은RECEIVING 상태의 유효한positive응답에만 허용한다. 빈 상태는 저장하지 않아 다음poll에서 새 준비 여부를 조회한다.
- READ 데이터CRC, 레코드/세대/토큰 검사, D2 POP, D0의token+1 소비확인은 매 블록 유지한다. 검증 전COMMITTED 공개나소비확인 생략은 없다.
- 준비 승인 단계에서는 저장상태를 폐기한다. 새 BEGIN/reset은구조체초기화로폐기한다. COMPLETE/PREPARED/COMMITTED는저장하지 않는다. 실패 뒤 재시도도없다.
- 조회를 생략해도 다음 실제D1 전송의 runtime guard와 DMA session guard가 실행된다. 새세대·리셋을 가로질러 재사용하지 않는다.
- FPGA의sealed블록은record_ready=0이고, 버퍼/token은유효한D2 POP 또는COMMON reset까지바뀌지 않는다. 이소유권이성립하는현재endpoint만대상이다. 향후비동기FIFO/다른reader가추가되면이계약도재검토해야한다.
- 기존DMA182, SPI2.625MHz/SS간격, SNES1815, 송신기·변환기, ROMloader/STOP은그대로다. 저장공간은RUN receiver에만포함되고추가상시RAM은0이다.

## 검증

실제배포181 FPGA의nes_native_spi165.sv와기존1813 RTL통신fixture의endpoint해시가같음을확인했다. 기존응답과완전히동일한positive D0만제거해실제C수신기로재생했다. 이는새RTL타이밍실행이나실기성능측정이아니다.

|fixture|기존transaction|변경후|생략D0|
|---|---:|---:|---:|
|raw0|23|21|2|
|raw1|31|27|4|
|raw7|59|47|12|
|32groups/raw7|60|48|12|

네조건의논리수신구조18060바이트가원본과일치한다. 실제재사용뒤READ CRC/전송실패,최종COMMIT확인실패,prepared실패,저장응답CRC오류,유효CRC이지만잘못된토큰을검사했다. 기존packed레코드오류·중단·재시작검사도동일C로통과했다. 일반포인터/패딩까지전체구조체를동일하다고표현하지않는다. 재생은지연단축에따른생산자스케줄변화를모델링하지않는다.

전체ARM200924B/static26564B/RUN36976B/IRQ508B/여유1376B. 182대비RUN8B증가이며상시RAM증가0,receiver크기18064→18072. 기존13개platform/library명령동일성·NMI·STOP·메뉴경로·noinline workspace수명도검사했다. 로그최대3921/4096B. FPGA/SNES/변환기바이너리·소스그대로여서동일FIT·화면회귀검사를반복하지않았다.

SELECT arm01/test02/check01/report01/release01. test01은기본재생통과후재사용경계의오류검사를강화해test02를선택했다. 폐기된batch후보의검증을선택후보의증거로섞지않는다. 새실기결과와60fps는미확인이다.

## 다음 구조: 매 조각 ACK 대신 제한된 연속 전송

사용자는TCP식왕복보다UDP식연속전송이가능한지질문했다. SPI에TCP/UDP를그대로도입하는문제는아니지만, 조각마다ACK를기다리지않는방향은타당하다. 현재확인은CRC뿐아니라단일블록/단일mailbox를재사용할수있다는소유권신호다. 응답만지우면수신도중덮어쓸수있다.

후속은**bounded FIFO/credit + 프레임완성 확인**을우선한다. 몇개조각을연속전송하고수신자가소비한범위를묶어서확인하며,CRC·순번·세대로오류를검출한다. SNES는완성된후보만공개하고마지막표시ACK로해당버퍼를재사용한다. ACK지연·FIFO가득참·STOP·reset·세대순환·오류시기존화면보존이필수경계다. 상태조회만더빠르게반복하거나검사없이덮어쓰는방식은채택하지않는다.

한계시화면전체를건너뛰는정책은가능하지만,부분타일손상을노출해서는안된다. 프레임스킵을늘려놓고60fps목표달성으로계산하지않는다. 유효payload절감과공유SPI16.7ms서비스예산도함께필요하며,raw7 egress하한22.154ms와단일capture lease문제가남아있다.

다음순서는①실제양쪽endpoint의FIFO/credit·수명표와wire예산②목적bank기준세대가확인된차등전송③작은통합검사후실제SMB3다. 타일묶음/1813·1815압축중복구현·미세최적화만반복하는루프는피한다. GBC164/세이브SRAM/완료자료/MMC4·5/state/mute/frameskip계획과AV60fps→장기플레이·리셋오류로그→입력유지우선순위유지.

[실기 안내](nes-game183-ready.ko.md) · [검증 색인](../analysis/status183-verification.json)
