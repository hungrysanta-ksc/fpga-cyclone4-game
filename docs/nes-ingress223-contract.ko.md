# NES223 배경 geometry 묶음 전송

후속224 source02에서 전체 타이밍 기준을 통과했다. 아래 source01 배포 보류는 최초 후보의 이력이다. [후속 검증](nes-counter224-contract.ko.md)과 [시험 안내](nes-game223-ready.ko.md), `analysis/release223-verification.json`의 최종 배포 gate를 함께 확인한다.

PR121 머지93351eb 이후 `codex/nes-geometry-ingress-223`. 기준은 실제222 시작·60초·스크롤 성공판이다. 기존 인덱스/시작 절차/60초 제한/오디오/입력은 유지한다.

## 작업 의미와 범위

222는 D1 encoded payload만 완료당 평균23.81ms였다. 현재 표현을 줄이지 않고 조회만 최적화해서는60fps 예산16.67ms를 맞추기 어렵다.223은 반복되는 레코드 헤더를 줄이는 실제 송신기·SPI·수신기 변경이다. 진단 로그를 늘리지 않으며 새 frame RAM이나 저장SRAM을 사용하지 않는다.

배경 map에는13bit physical CHR tag와2bit attribute를 합친15bit word가 있다. 서로 다른 word4개를 기존64bit 레코드에 넣으면 기존6B×4=24B가12B가 된다. 같은 값이 길게 반복될 때는 기존 최대256개 동일값 run을 유지한다. 전 프레임에 대한 delta나 source cache를 도입하는 변경은 아니다. 따라서 epoch/CHR 내용/매퍼 fetch-time 상태를 잘못 재사용하는 새 조건을 만들지 않는다.

##2231 wire 계약

- BEGIN 버전은2231이며 이전2031 C/FPGA와 혼용하지 않는다. 구조가 바뀐 SPI 송신기와 ARM 수신기를 함께 배포해야 한다.
- kind0,index bit12=1: literal map 묶음. 낮은12bit는 원래 시작 index이고 최대1055다. payload8B의상위4bit는 n(1..4),하위60bit는 순서대로15bit word를 담는다. n은 남은 map word 수와4 중 작은 값이어야 한다. 사용하지 않는 상위 padding은0이다.
- generation16bit는 모든 레코드에 그대로 남는다. 토큰 순서,block CRC16,명령CRC8,READ 완료 후POP,PREPARED/COMMIT와최종displayACK의 의미도 유지한다.
- 수신기는 state/generation/phase/연속 start/count/padding/전체길이를 먼저 검사하고 기존 logical decoder로 확장한다. `records`는 확장된 logical word 수이므로 META_END/END 검증이 같다. tentative 데이터는COMMIT 전에 공개하지 않는다.
- 반복 run은 기존kind7 형식 그대로다. 첫 두 값이 같으면 run으로 전환하고, 다른 값은4개를 모은다. run 뒤 첫 다른 값은 immutable lease에서 다시 조회한다. literal 묶음 중간에서 시작된 반복은 다음 묶음에서 다시 탐지하므로 모든 데이터에서 최적압축을 보장하지 않는다. 마지막 단일 literal은 기존보다6B 클 수 있다.
- 이미 쓰던 held_data64bit와pack_count를 사용하고 map_repeat1bit만 선언상 추가한다. 전체 FPGA 자원 증가는 실제FIT로 판단한다. source의15bit 초과 값을 자르지 않고ABORT한다.
- raw patch/objects/exceptions/raster/palette와META_END/END/COMMIT는 기존 형식이다. SPI 최대레코드12B/256B block/244B room 기준을 유지한다. CDC나clock/SDC/seed는 바꾸지 않는다.

## 검증한 범위

실제220 exporter와223 exporter를 동일 geometry fixture로 실행했다.16장면의 출력 trace를 각각 실제222 C 수신기와223 C 수신기에 넣어 전체 수신 상태/geometry/required tag/patch 데이터를 비교했다. 전송 record 수가 달라지는 next_token만 별도로 정상 연속 증가시킨 뒤 비교에서 정규화했다.15정상 COMMITTED와기존512tag 초과 거부1개가 일치한다. PREPARED는 이 비교에서 fixture이며 실제SNES 출력 검증이라고 부르지 않는다.

추가로5장면을 실제223 SPI RTL로 직렬D0/D1/D2/D3 전송하고 CRC·POP·잘못된POP·명령CRC·짧은READ를 검사했다. 해당D1을 실제C packet decoder로 읽은 결과도 기준과 같았다. source응답/lease/ACK/잘못된상위bit4오류와C phase/generation/index/count/padding/token/길이/duplicate/구버전14거부도 통과했다. 실제C poll loop와RTL을 동시에 실행한 전체보드 결합은 아니다.

| 합성 geometry | 기존 payload |223 payload| 의미 |
|---|---:|---:|---|
|최대32group,서로 다른1056word|6780B|3612B|46.73% 감소. 실기SMB3 캡처가 아닌 부하 fixture|
|최대32group,같은값 반복|504B|504B|기존 run 효율 유지|
|2개씩 같은값 반복|6780B|6780B|개선 없음, 과장하지 않음|
|긴 run과서로 다른값 혼합|5040B|3168B|37.14% 감소|

서로 다른값 부하의 실제SPI 총4095B/17blocks는2.625MHz에서순수wire12.48ms다. payload3612B만11.01ms이며 기존payload6780B는20.66ms다. 여기에는 실제C 계산·E8/E9 계획·E0/E1 맵·SNES 소비·오디오 service가 모두 들어 있지 않으므로 **60fps 달성 수치가 아니다**.222의전체D1 중map 비율을계측하지않았으므로실기D1전체가46.73%준다고추정하지않는다.

전체ARM209168B/static28020/RUN34984/IRQ508/여유1912B로 기존1024B gate를 통과했다. receiver9880B/tiles4B와 큰frame31848B·startup32B는 그대로다. 실제 수신기 분기 증가를 포함한 linked graph를 다시 계산했다. 기존GBC/menu 모든경로의실측high-water 또는 미래mapper 예산을 보장하는 수치는 아니다.

## 전체 FPGA 결과와 배포 보류

선택 test01/source01/arm01/check01/mapfit01/timing01/io01/paths01. 단 한 번의 전체 FIT에서 15230 LE / 8353 FF / 961 LAB / 47 M9K로 배치에 성공했다. 220 대비 +74 LE / +1 FF / +4 LAB이며 여유는 178 LE / 2 LAB / 9 M9K다. 새 메모리 블록은 없다.

세 코너의 nominal setup 최솟값은 +0.268ns, hold는 +0.130ns다. 그러나 기존 implementation 기준 setup은 **-0.006ns로 실패**했다. 대상은 `reader|check_response_address[5]` → `control|commit_clear`, 6 LUT / 5.441ns 경로다. interconnect 합계는 3.414ns(약62.7%)다. 새 native_export 대상 경로는 strict +24.358ns였지만, 전체 보드 기준 미달을 무시할 수 없다. 로더 RTL 자체는 이번 변경에서 동일하며 전역 배치 변화로 드러난 경로다. seed 변경이나 clock/SDC 완화로 통과시키지 않았다.

CDC 3984행 / sole-fanout first stage45개 / 새 미분류 direct-path crossing0개, held 최대6.532ns / Gray6.743ns, epoch reset96개·576경로를 확인했다. 조건부 IO 모델은 PSRAM +4.385ns / SNES +80.059ns / SPI +165.972ns 여유이며 native payload reset 경로는 통과했다. 전체 IO/MTBF/전기적 signoff는 아니다. 기존 reset 관련 음수39행을 새 문제 없음이라는 표현으로 감추지 않으며 조건부 IO 검사의 기존 범위를 유지한다.

**223은 기능·ARM·FIT 검증을 통과한 미채택 후보이며 실기 배포 가능 상태가 아니다.** ASM/ZIP 및 설치용 FPGA 조합을 만들지 않았다. 기존222 실기판을 계속 기준으로 둔다. 정확한 다음 대상은 `counter_retire_ok`의 response address 일치와 `commit_clear/inc` 경로다. response 소유권, SS/pending/fault/STOP 우선순위와 판정 사이클을 유지하는 국소 qualification 분리를 먼저 증명해야 한다. 기존 CHECK fault split 시험만으로 commit counter 동치까지 증명했다고 취급하지 않는다. 수정 후 전체 타이밍·CDC/IO, paired ARM/SNES212 ROM 및 실제 첫 레벨을 확인한다.

## 다음 통합과60fps 계획

선택 source01은220 전체보드에서 exporter/SPI 두 파일만 변경하며 qsf/sdc/핀/타이밍 제약을 그대로 사용한다. ARM은222의수신기와223식별자3파일만 바꾼다. 보드 검증 결과와 실제 배포 여부는 `analysis/ingress223-verification.json` 및HANDOFF가 최종 기준이다. 아직 실기 성능을 확인한 것으로 취급하지 않는다.

다음 맵 개선은 원본 좌표·scroll과SNES HDMA를 함께 다뤄야 한다. 현재 planner는 fineY/palette/33word행 변화에 따라 group을 재구성하고,visible33열을 화면 기준으로 다시배치한다. 단순히 맵주소만 회전시키면split/예외행/대체tag/패치/두VRAMbank의누적변경을잘못처리할수있다. stable source-row/column과physicalpattern slot을보존하는경로와fallback을설계하고,전체16.67ms비용을따져야한다. 이PR은그맵개선이끝났다고주장하지않는다.

ARM1912B여유와FPGA여유는별도계산하며큰배열추가를피한다. sourceepoch/fullkey/row-alt/mask/activebank/finaldisplayACK를유지한다.223의최소검증뒤실제첫레벨RIGHT+B/A반복스크롤에서222와비교한다. 같은222/044재시험,캐시추가·조회·loader·FIT seed만반복하는작업은후속목표가아니다. GBC164/저장SRAM/이전봉인증거는보존한다.
