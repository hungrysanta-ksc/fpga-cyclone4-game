# NES396: 선행 tile 저장·발행 frontier 구현과 부분 공동 제어의 전체 비용

## 판정

**3584B tile FIFO·ordinary512B 예약·실제 ARM 발행 제한은 연결했고,394의 고정907 시작 실패를 해소했다. 그러나 연속 일정의 첫 캡처 누락은911로 남았고,whole Lite 조합 논리는17574→18108으로534개 늘었다. 시간과 회로 여유의 공동 목표는 실패다.** production375RTL/377ARM 및 production227/GBC164/saveSRAM은 바꾸지 않는다.

395에서 선택한 **host/source/plan/queue/SPI 전체 RAM 실행기 본체 교체는 완료하지 못했다.** TAKE 선점중소비gate 누락을마지막검토에서찾았다. unit07-regression은수정전RTL의중복소비fault를재현했고,수정후unit08은모든fragment의TAKE를14host clocks 강제로중단해도정상/19guard를통과했다.

이번396은 실제 FIFO와 frontier를 구현하면서 descriptor 산술·source footer·NES 필드 cursor·SPI 응답 byte 선택을 공통화한 부분 교체다. host1750comb와 별도 checker300comb,source/plan/queue/SPI 본체가 여전히 남는다. RAM800..1023의 host/source/plan 문맥 register file은 구현하지 않았다. 따라서 이 결과를395 전체 구조의 구현 완료나 그 구조가 불가능하다는 증명으로 해석하지 않는다. 이 부분 교체 후보는 회로 목표에 미달하므로 채택하지 않는다.

## 실제 연결한 경계

- 기존4096×8 staging RAM을 tile0..3583/ordinary3584..4095로 분할했다. 별도 tile payload RAM을 추가하지 않았다. 동기 read 포트는 실제 SNES source 읽기에,write 포트는 prefill/ordinary에 쓴다. tile copy가 겹치면 ordinary byte_ready를 내려 write를 중재한다.
- 기존 tile_link 논리32B RAM을1024B로 확장했다.0..31 CDC payload,32..799에192×4B generation/kind/slot stamp를 저장한다. mailbox 반환은 payload와stamp가 모두 저장된 뒤다. prefill은 DMA record/token/목적지를 생성하지 않는다.
- ARM final record가 도착하면 FIFO head부터kind/slot/generation·전체 길이를 정확히 결합한다. TILE≤2048B는 FPGA admission에서도 검사한다. 충분한 byte/stamp가 없으면 prefill을 계속 허용한다. 초기 실험의 이 순환 대기는build02에서 수정했다.
- record 결합 뒤만 SNES aperture를 공개한다. 실제 순차 read·독립 CRC/coverage drain·fresh token 소비가 끝나야 tile head/stamp를 반환한다. ordinary storage credit과 마지막 packet consumed는 구분한다. END와 BG-close도 구분하며 남은 tile/stamp가 있으면 최종 표시로 진행하지 않는다.
- ordinary repeat의decoded 길이가512B를 넘으면 같은 ARM record 안에서≤512B 내부 fragment로 나눈다. 각 fragment는 fresh token/receipt,연속 offset,첫/마지막 flag를 갖는다. E1 저장 retirement는 한 번,record consumed는 마지막 fragment에서만 증가한다. 기존1100B ROM-zero-DMA shortcut은2B seed를 유지한다.
- 실제M4에published/accounted32bit 두 개를 추가했다. E9 전 `published+count<=accounted+33`을 검사하고 송신 전에 예약한다. account는기존 at290 commit 성공에서만 증가한다. full이면추가 발행/계획 작업을 멈추고 foreground accounting으로 돌아간다. unsigned 차감으로accounted가앞선 경우를 오판하지 않는다.

독립 expected bitmap/중복·CRC·최종 검사,STOP 공통 취소·source ROM drain·token/serial 소각,정확한12view·PPU 실행·VBlank·최종 ACK는 보존한다. 단순 staging 완료를 display ACK로 취급하지 않는다.

## 실제 삭제와 남은 제어

|경계|삭제/교체|남은 본체|
|---|---|---|
|host TILE|TILECHECK/TILEREAD/TILEPUT의record 종속 복사·tile_at/tile_bytes 제거|packet/manifest/receipt protocol FSM·hot registers|
|descriptor|병렬 목적지/span/store 계산을17bit ALU+64×24 microprogram으로 교체|immutable96bit active record·형식 검사·순서/최종 검사|
|host source footer|별도 loading/load_step FSM 제거,host field walker가6byte read/capture 수행|source D4/D5 ACK·길이/CRC hot cache·codec|
|NES source/plan|source footer counter와plan READ/CAPTURE phase를단일owner/phase/cursor로 교체|plan field 의미 decode·lifetime·endpoint·source codec FSM|
|SPI|200bit회전 snapshot을고정176bit view+첫byte로 교체,CRC8/응답에byte lane공유|SPI edge/capture/response lifecycle·queue storage/credit|

footer가host protocol CASE를중단하는 동안 source actual read/CRC capture는계속 유지한다. handshake중복을막도록 protocol publication을gate했다. checker 완료는다음 start까지 유지해 footer선점으로done을놓치지않는다. `rst` 선언 전참조는Questa가잡았으며최종build08/live07/map03는수정된동일소스다.

## 기능·경계 검증

선택된증거는상위workspace `probes/nes-joint396/`에원본으로보존한다.

|시험|결과와범위|
|---|---|
|actualM4 component arm01|71frame output wire가394와byte동일,원래dirty map coverage정확|
|compiledM4 frontier armguard03|1770경계,full450건/accounted선행150건;E9 physical전에예약,full에서E2뒤accounting복귀. 짧은dummy batch는공급loop용이며hardware plan 의미검사는아님|
|RTL unit08|12frame,25462actualread bytes,max2credit,19오류/STOP·RAM freeze. short/E0 MISO CRC8를실제SCK로확인|
|repeat-unit05|일반repeat1100B를512+512+76으로실행;12frame26560reads,max2credit|
|actual65816 native01|같은1738Bbody/ROMhash로cold905 일반repeat분할·전체map/tile/CGRAM/OAM/HDMA·VBlank ACK PASS;907 STOP은PPU0/finalACK없음|
|edges03 ABI|원본71frame record의bit mutation/필드경계를샘플한24000vector,정수형독립범위오라클과실제checker일치|
|edges03 FIFO|미공개tile3584B full에서도ordinary512B진행,10240actualread bytes,192stamp full·stamp/payload wrap·다중record·복사중STOP PASS|
|edges03 NESwalker|동시요청에서source6writes우선·plan재개,6footer index별취소와pendingplan reset뒤DONE없음|

일반repeat1100B 시험은cold905의zero-tail flag만제거해동일decoded zero를생성하는**directed equivalent ABI**다. 실제M4 정상71frame에새1100B 일반repeat가생겼다는뜻이아니다. 정상경로의ROM-zero shortcut은변경하지않았다. 이번native시험은RTL과CPU의완전lockstep이아니다. live시험은394에서측정한actual65816 service를같은bus/PPU모델에연결한다. fullresident/audio/input/WCET·실기검증은아직없다.

초기unit01의삭제된계층참조,unit04의TB hex literal,unit05의rst선언순서,edges01의두번째SNES screen stride 오라클오류,armguard01/02의반복fixture plan_accepted초기화누락을보존한다. 이는새라이선스문제가아니다. 최종선택은unit08/edges03/armguard03이다.

## 실제 ARM·IRQ·SPI·ROM 연속 일정

MASTER46561ps/SNESphase0/ROM_WINDOW1/고정capture5371247/49104clock·512reserve·cutoff를그대로썼다. actualM4 기계어와sharedSPI,IRQ·WFI,2outputslot,source input ring/ROM경쟁을실행했다. CPI1/checkpoint exception배분은WCET가아니다.

|프레임|source시작ms|완료ms|경과ms|SPI bytes/E2요청|WFI|exception배분|
|---|---:|---:|---:|---:|---:|---:|
|905cold|14.242474|114.312423|100.069949|16233/60|11|1248|
|906cold|128.554758|230.789700|102.234942|10916/66|19|1272|
|907warm|264.333059|281.649584|17.316525|1958/33|13|600|
|908warm|280.972517|314.552706|33.580189|1604/30|8|504|

394의cold906 완료264.068430ms에비해396은230.789700ms로,연속startup이33.278730ms 빨라졌다. 고정907 capture250.090631567ms보다19.300932ms 먼저cold를끝내 **394의startup 실패를해소했다**. cold906의시작도앞당겨졌으므로33.278730ms를동일위상단일프레임의속도차로보지않는다.

warm907/908은392의source 시작시각과ROMcycle5677131/6034500이 **정확히일치**했다. 392의17.226011/33.543825ms에비해396은17.316525/33.580189ms로,0.090514/0.036364ms 느리다. 표시VBlank16/18은같다. cold개선을warm의60fps 개선에합산하지않는다.

capture908/909/910은수락했지만316.648557725ms에 **first missed capture911 owned1/release0/fault0**로실패했다. ROM45566request/reply·pending0,입력8564request/reply·pending0이다. 최종시험전체는FAIL이며,capture911 통과나장기60fps 증거는없다. 908의33.58ms와다음source 소유권이여전히문제다.

ARM text/data/BSS는35776/4/48728이다. 394대비+84text/+8BSS다. component stack304B는IRQ를포함한전체상한이아니다. frontier/추가응답의명령비용은live 실행에포함했다.

## Quartus Lite 전체 비용

기능live07의32RTL파일과whole map03를SHA256으로일치확인했다. unit08의10RTL도같다. 보드4KiB program ROM은native01의실제65816 image와byte가같다. 미연결warning0이다. **MAP만실행했으며FIT/STA는실행하지않았다.**

|whole|394|396|차이|
|---|---:|---:|---:|
|LE|22416|22872|+456|
|comb|17574|18108|+534|
|FF|9024|9033|+9|
|RAM bits|300640|310112|+9472|
|device15408comb까지부족|2166|2700|+534|
|155comb여유포함부족|2321|2855|+534|

부모inclusive를중복합산하지않고self로분해한다.

|제어경계self comb|394|396|
|---|---:|---:|
|host|2022|1750|
|새descriptor checker|0|300|
|source transport|398|388|
|plan+새walker|354|376|
|plan endpoint|99|96|
|SPI|579|700|
|queue|221|219|
|tile_link|43|43|
|소계|3716|3872|

host만의-272을절감으로보면틀린다. checker300을지불하면 **host+checker는+28**이다. 고정snapshot/variable byte lane도SPI를+121늘렸다. 새FIFO는기존aperture207→538comb로+331다. 보존codec/checker2347→2351,나머지11511→11885이다. 전체는 `3872+2351+11885=18108` 으로일치한다.

32Bmailbox의논리용량확장7936bits+checker ROM1536bits=추가9472bits다. FIFO payload RAM은기존32768bits다. FF9033은기존392의8985상한보다48많다. 395의1395comb 제어cap에비해현재3872로 **제어만2477초과**하며,나머지증가분도흡수해야한다.

## 다음 판단

이번증거는미공개tile 저장과ARM 발행frontier로startup 순환대기를풀수있음을지지한다. 부분ALU/FSM/byte-lane 공통화의누적으로는면적예산을충족하지못했다. 396을production으로승격하지않으며opcode/seed/FIT 반복도하지않는다.

미구현인공유context RAM 실행기를진행하려면packet/manifest/receipt·queue credit·SPI lifecycle까지본체를대체하고,source/plan의재개문맥을RAM으로옮겨야한다. 기존1395comb cap은새outside 증가를반영하지못한다. 현재outside11885+보존2351를유지하면,whole15253을위한제어상한은 **1017comb**이며현재3872에서2855를실제로삭제해야한다. 새FIFO까지포함한전체삭제대장이먼저필요하다. 시간은동일위상908/911을gate로삼고fixed907 회복만으로승인하지않는다. 전체cap과연속capture를함께충족할전망이없다면ROM중재·역할분담·FPGA용량을다시비교한다. 현재MMC4/5 추가나실기60fps 여유가있다고말할수없다.

재현도구: `tools/build_nes_joint396.py`, `tools/probe_nes_joint396.py`, `tools/probe_nes_joint396_rtl.py`, `tools/guard_nes_joint396_arm.py`, `tools/probe_nes_joint396_edges.py`, `tools/probe_nes_joint396_native.py`, `tools/map_nes_joint396.py`. Questa는기존Starter FLOAT 래퍼,합성은Lite를쓴다. 증거감사는 `tools/analyze_nes_joint396.py`다. `audit_passed` 는실패결과를포함한대조성공이며,time/area/full_RAM_executor 성공이아니다.
