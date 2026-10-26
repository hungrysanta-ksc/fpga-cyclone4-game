# NES376: 60fps 최적화와 MMC4·MMC5 확장 gate

## 판정

375의4.834415ms 부족을 없애도 MMC4·MMC5 지원과 실기60fps가 자동으로 성립하지 않는다. 현재 보드는 MMC3/mapper4로 고정됐고,source/plan/ROM service/loader가 SMB3 용량·주소 형식에 맞춰져 있다. MMC4는 mapper10,MMC5는 mapper5이며 서로 다른 확장이다.

지금 만든 입력/표시 문맥 분리,credit·epoch/serial 수명,독립 expected/read CRC/coverage,STOP·최종 ACK와 기능/전체보드 동일 RTL 검증은 확장에도 재사용할 기반이다. 물리 주소로 읽는 immutable CHR cache도 전체 주소와 content epoch를 보존하면 재사용할 수 있다. 이 성과와 지속60fps 달성은 구분한다. 앞으로는 SMB3 시간만 맞춘 결과를 mapper 공통 기반 완성으로 승인하지 않는다.

## mapper별로 유지할 것과 바꿀 것

|범위|MMC4|MMC5|
|---|---|---|
|CPU/PPU mapper|실제 PPU read 순서에 따른 CHR latch와 trigger 전후 bank 유지|ExRAM/nametable 공급,확장 attribute/CHR 선택,IRQ·audio·PRG RAM 처리|
|현재 compact 주소|128KiB CHR의 물리tag 범위는 맞음. 현재 core/loader가 지원한다는 뜻은 아님|최대1MiB CHR은16bit 물리tile tag 필요. 현재13bit로 부족|
|화면 표현|실제 fetch의 물리주소를 보존하면 bank 변경 이력을 재사용 가능|8픽셀 palette는 표현 가능. 반복 fine-Y/split 예외 한도와 mapper에서 나온 데이터 tap은 별도 확장 필요|
|선행 읽기|이미 캡처한 물리 ROM 주소만 사용. speculative PPU read로 mapper latch를 다시 동작시키지 않음|ExRAM/CHR RAM을 immutable ROM으로 취급하지 않음. 데이터 출처와 변경 epoch를 구분|
|시간·회로 여유|실제 latch/core/ROM 일정과 같은 보드 경계에서 계측 필요|더 넓은 tag/화면 표현/ExRAM/IRQ/audio까지 포함한 전체 비용 필요|

MMC4의 PPU-read latch와 MMC5의 확장 기능 요구는 [NESdev MMC4](https://www.nesdev.org/wiki/MMC4),[NESdev MMC5](https://www.nesdev.org/wiki/MMC5)를 확인했다. [MiST mapper 구현](https://github.com/mist-devel/nes/blob/master/src/mappers/MMC5.sv)은 인터페이스 비교 근거이며 이 프로젝트에 가져오거나 검증 완료로 세지 않았다.

## 실제375 RTL에서 확인한 경계

- `cart_nrom.sv`는 이름과 달리 현재 MMC3를 `.flags(32'd4)`로 고정 연결한다.
- planes collector는 physical address의상위bits로 `$200000..$21FFFF`만 허용하고 tile은13bit다. plan decoder도tag high byte 상위3bit를 거부한다.
- ROM service는 PRG256KiB/CHR128KiB만 immutable ROM으로 처리한다. loader도 총393,216B의 고정 배치다. mapper module 하나만 교체해서 일반 게임 loader가 되지 않는다.
- compact BG cell은13bit tile+2bit palette다.1MiB CHR 전체를 구분하려면 최소16bit tile+2bit palette가 필요하며 N5/ARM/plan/cache/독립 검사 ABI도 함께 바꿔야 한다.
- 현재1056cell의 논리bit는15,840,18bit 확장 시 최소19,008이다. 이것은 M9K 증가량 증명이 아니다. depth/width/port packing과 전체 보드로 계측한다.
- 현재8192tag membership bitmap은1,024B다.65536tag 전체 bitmap은8,192B로7,168B 늘어난다. bitmap 자체를 유지할지 sparse key 방식으로 바꿀지도 실제 ARM 시간·RAM으로 비교한다.

기존13bit를 억지로 재사용해 높은 bank를 alias시키지 않는다. SMB3용 compact profile을 유지하고,확장 profile은 버전·capability·데이터 출처·범위를 입구에서 구분하는 것이 다음 검토 범위다. 아직 확장 ABI를 구현한 것은 아니다.

## 실제 기능 경계 검사6개

선택375 보드의 planes/compact/plan/mailbox/reset module5개를 해시 그대로 사용했다. 다음은 실제 mapper를 연결한 게임 테스트가 아니라,resolved fetch와 화면 표현의 재현이다.

|case|검사|결과|
|---|---|---|
|0|trigger tile의 기존 bank와 이후 같은 logical tile의 서로 다른 물리bank 주소|3개tag1FD/512/112를 각기 보존,valid|
|1|CHR128KiB 밖 resolved address|event를 만들지 않고 frame 거부.낮은 bank alias 없음|
|2|224행/28group에서 cell마다 palette0..3 변경|모든33cell query의tag/palette 일치,예외0/valid|
|3|224행의 오른쪽17cell에3pixel fine-Y 차이를 둔 split 자극|예외128개에서 용량 초과 검출,valid0/errors04|
|4|최대13bit tag8191|정상 plan 승인|
|5|다음 tag8192|정상 길이/CRC에도 plan 거부,tag0으로 승인하지 않음|

case3은 선택한 split 자극에서17×224=3808개의 cell 예외를 요구한다. 현재128개 한도로 이 형태를 일반 지원할 수 없다는 반례다. 모든 MMC5 게임이 이 패턴을 사용한다는 뜻은 아니다. segment/split 표현을 별도로 두거나 SNES layer/window·합성 tile에 옮기는 대안의 비용을 비교해야 한다. case2는 palette가8픽셀 단위라는 이유만으로 기존 경로를 전부 버릴 필요는 없음을 보여준다. mapper의 실제 attribute 출력이 collector까지 전달되는 검증은 남는다.

최종guards02는6case 모두 오류0/경고0이다. guards01의case0..3은 완료됐지만 plan decoder의 기존 reset module을 test compile 목록에 빠뜨려case4에서 load가 실패했다. 의존성을 추가한 최종 실행과 실패 로그를 모두 보존했다. RTL/라이선스 오류로 바꾸어 기록하지 않는다.

## 4.8ms의 실제 원인과 후속 후보

375 frame914의 첫BG plan tag는6136인데 early hint는6653/6552/6553만 읽었다. 첫BG 요청8.533806ms/실제 back request8.534170ms 뒤 첫결과16.857025ms까지 **8.322855ms**가 걸렸다. 첫ROM 허용창은 source 기준 대략0.612~1.729ms다. ARM plan을8.5ms에 조금 빠르게 만드는 것만으로 그 창을 되돌릴 수 없다.

이 시간은 전체4.834415ms 부족에 더하는 별도 비용이 아니다. 실제 critical path에 포함된 대기다. 현재 CRC 확인 geometry와 이전 표시 bank의 첫 부족 physical tag를 먼저 준비해,기존7entry cache 안에서 첫창에 읽는 후보를377에서 검증한다. 어떤tag가 필요한지 실행 후 정답에서 가져오지 않고 호출 직전 RAM만 사용한다. 추가ARM scan·SPI·IRQ·다음 capture·ROM/core 우선권까지 포함한다.

375의 최대warm 완료 간격25.804417ms도 별도 관찰치다. frame914 처리시간 하나를16.666667ms로 맞춘 것을 연속 표시60fps 증명으로 쓰지 않는다. 무누락·무backlog·각 presentation deadline과 실제 VBlank 정렬을 함께 검사한다.

## 확장 후 통과 예산

시간은 `기본 실제 일정 + mapper/core/render 추가 비용 + IRQ/SPI/DMA/VBlank/WCET 여유 <= 표시 기한`으로 검사한다. MMC4/5의 추가 비용은 아직 측정하지 않아null이다.4.8ms만 없애고 여유0인 설계는 이 gate를 통과하지 못한다.

회로는 현재2,255comb 부족에 같은 경계의 mapper/render/IO 증분과 placement/timing 여유를 더해 순삭제해야 한다. mapper 교체 시 기존MMC3 비용과 새 비용의 차이를 전체보드로 측정하며 별도module 합성을 그냥 더하지 않는다.375의155개 예비 여유는 MMC5 비용 예산이 아니다. 현재RAM300,640bit도 M9K packing/FIT 여유의 증명이 아니다.

현재 timing fixture는`core_safe=1`과 합성 core request를 사용한다. 실기 보드는 native_fill_slot과native_core_safe가 모두 필요하고,cpu/PPU/ROM 상태에 따라 허용 기회가 줄어든다. MMC5의PRG RAM/ExRAM/추가 IRQ 등은 이 조건에서 실제 workload로 확인해야 한다. 같은 이름의 ROM window라는 이유로 fixture를 mapper 최악 시간으로 사용하지 않는다.

ARM에서 전체256×224×4bpp를 만들어 SPI로 다시 보낼 경우에만,28,672B의wire 하한은 현재2.625MHz에서87.381333ms다. 이 대안을60fps 해법으로 채택하지 않는다. 이는 direct FPGA 합성이나 delta tile 방식의 하한/불가능 증명이 아니다.

다음 작업은 공통 DMA/receipt/소유권 기반을 유지하면서 첫 ROM 대기의 실제 단축을 검증하고,확장 profile의 물리tag·mapper 데이터·split 표현과 전체 회로 비용을 함께 정하는 것이다.71/heavy7·다중 위상·전체65816/VBlank·live core/mapper·WCET·FIT/STA·실기 전에는60fps/MMC4/5 지원을 승인하지 않는다. production227/GBC164/saveSRAM은 그대로다.
