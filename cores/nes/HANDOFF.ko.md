# NES 현재 인계 — 160 렌더링 재개 주소 예측 실기판

[160 결과](../../analysis/GAME160-RESULT.ko.md) · [실기 안내](../../docs/nes-game160-instructions.ko.md) · [검증](../../analysis/game160-verification.json) · [159 실기](../../analysis/GAME159-HARDWARE-RESULT.ko.md)

PR101 머지7f93ac599a958d9073eb571468cc7dd8d6459ed3 확인.159 월드맵 진입·방향키 이동은 실기 통과. 첫 레벨 A전환은26.240초 뒤 line193/dot336/217000 PPU오류2이며60초 제한이 아니다. CPU03F86E 응답 뒤 reader가 빈 구간에도 현재PPUvalid0이 힌트를 막았고 실제217000 요청은 샘플3클록 전이었다.

160은 실제PPU2001 쓰기→re_sr 재개→ALE/하위래치 경계에서 같은 실패를 재현했다. 직전 ALE가 없는 짝수 패턴 읽기에 옛 하위래치가 남아 일반예측217078/70과 실제217000이 달라진다. re_sr[1]&&!re_sr[2]의 제한된 재개 구간만 보존된 하위래치와 다음상위주소를 한PPU주기 미리 예측하고 현재valid 조건을 우회한다. 가시줄/비스프라이트/지정패턴위상/빈PPUDATA pipeline으로 제한. 실제PPU주소·상태·매퍼/IRQ·서비스/reader/캐시/기한/클록·159raw CPU/DMA읽기 조건은 유지.159의 이전re_sr가 로그에 없어 실기원인 확정은 아니다.

선택test05 실제PPU결선+70ns모델:dot334/336×래치00/5A×위상0/3.5/5.5ns=12수정PASS/12예측차단대조오류2.159회귀39PASS/39대조중18오류 유지. 실제8CE초기화 뒤 unknown거부. 초기PPU위치/name/scroll/latch와CPU출력버스는 설정한 값이므로 전체게임/CPU명령/전체DMA/모든PPUDATA겹침 검증은 아니다. test01잘못된신호명 elaboration실패,02구판재현/03단일수정 탐색,04초기pipelineX발견으로 최종근거제외.05만 선택하고 이전시도보존.

fit01 명목setup-.170FAIL로배포제외. fit02 byte_count→miso_hold 및 loader state→loaded_bytes 두경로에 더엄격한5.3ns배치지침 추가. 추가예산+.076,정확155명목SDC setup+.207/hold+.138,조건부PSRAM+3.026/SNES199.984<270ns. 실제클록/falsepath/multicycle완화없음.13725LE/5005regs/122pins/virtual0/PLL1/56M9K. PCB2ns/reset release음수recovery/전체IO/MTBF한계 유지. test05와최종ASM RTLhash일치;배치만달라 기능반복불필요. ARM188604/NMI15stores0calls/host13회수256마스크. strict69/E3;APU채널차단156 유지.

NEXT:160전체SD폴더 적용→NES GAME 160.nh1→첫Start→1PLAYER Start놓기→월드맵 첫레벨에서A→레벨내 이동·점프. 두160TXT·메뉴복귀·플레이되면짧은영상. 기존적재약3분50초는참고치;60초실행상한 내 월드맵에서지체하지않는다. 044/GBC/159/A-B/무변경전체부팅 반복하지않는다. 실패하면 최초오류·16클록이 재개모델과맞는지 우선비교;추측으로캐시/중재확대금지. 통과하면 실제조작·스크롤 우선후 임시이력RAM축소·음원복구. 오디오/속도/저장/첫레벨플레이 아직미완료.

이전frozen자료·공개핀·ZIP불변,완료finish.py재실행금지. ROM/media/binaries/licenses/privatepaths Git금지. 한국어4PR절(목표/내용/결과/의미),개인hungrysanta-ksc만사용,사용자머지.

---

## 이전 작업 인계

# NES 현재 인계 — 159 월드맵 진입·이동 통과, 첫 레벨 전환 미완료

[159 실기 결과](../../analysis/GAME159-HARDWARE-RESULT.ko.md) · [해시·패드·16클록](../../analysis/game159-hardware-verification.json)

사용자 및 영상: Start로월드맵진입/방향키이동성공. A첫레벨진입의화면축소뒤오류종료/메뉴복귀. 실제레벨플레이미통과. 31.90s영상1fps전체/23~26s4fps표본,음성/모든프레임미분석. 60초제한이아님:run_first_error1/run_rom_error2,DISPLAY232680→258920=26.240s,menu262110. 펌웨어구간/영상/CPU관측카운터/FPS구분. full393216loadcompare/verified1/104records/68E2/STOPcounter75239400유지/stoperror0/baseTXT메뉴PASS. Pad33중last16,방향/SELECT/START/A+release,처음17덮어씀,마지막A/NONE. 물리클릭시각/전체입력완료아님.

다른오류:158line193dot8/217A18→159line193dot336/217000. context e70142e0:00217000 CPUvalid1/PPUvalid0/age2/busyPPU1. CPU03F86E요청-11/응답-6;reader-5/-4비었음;현재217B00→217000변경및즉시요청-3;sample0까지응답없음. 따라서CPU점유만탓하거나시간연장부터하지않는다.

중요: historyhint_valid는rawPPU힌트가아닌 nes_live_joint의 rawhint&&(rom_ppu_valid||local3A0000..3A07FF) 결과다. 마지막16클록모두0;현재CHR217B00invalid로결합조건차단됨. rawhint존재자체는미관측. 힌트비트217078→217070은actual217000과다름. faultsnapshotrender1/sprite0/ALE0/read2007write2007pipeline0/vram0078/latch00이지만이전pipeline/render/ALE전이는알수없음. 레벨전환렌더재개/PPUDATA/ALE외부하위래치와earlyaddress를우선비교. 원인확정아님.

NEXT 실제PPU/latch/service로dot333~336·빈reader·무효217078hint·새217000요청3클록전경계를짧게재현. 159rawread조건과정상CPU/DMA/PPU기한유지,안전한주소/유효시점을검토하고최소수정후같은SMB3첫레벨/A이동점프실기. 힌트단순무조건허용/전역PPU우선/샘플기한해제/무근거캐시확대금지. 부족한관측만필요시추가. 이번은PR101결과기록만,새펌웨어없음. 같은159재시험·044/GBC복원·A/B·전체부팅반복불필요. 임시M9K56/56이력축소는원인해결뒤. APU차단유지/오디오속도저장미완료.

frozen159/완료finalizer/ZIP/publicpins불변;제작당시메타physicalfalse는동결시점이고현재결과는GAME159-HARDWARE가우선. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc.

---

## 이전 제작 기록

# NES 현재 인계 — 159 매퍼 쓰기 중 ROM 읽기 차단 실기판

[159 결과](../../analysis/GAME159-RESULT.ko.md) · [실기 안내](../../docs/nes-game159-instructions.ko.md) · [검증](../../analysis/game159-verification.json) · [158 실기 이력](../../analysis/GAME158-HARDWARE-RESULT.ko.md)

PR100 머지3ef0a0714fd803bdfdfeb0c7208b4f8a84a127c5 확인.158은 새 CHR주소를 일찍 예측했지만 낮은 비트면 응답 뒤CPU03C001→옛205A18→새217A18 순서로 늦어 오류2.159는 실제raw쓰기 중 cart_pre 이전에 prg_allow가1인 구간의 불필요한 조기CPU읽기를 차단한다. rom_cpu_address_valid에 mr_int 하나 추가. 현재MMC3 prg_conflict0이며 다른매퍼 버스충돌까지 검증한 것은 아니다. pendingMMC3hint/actualmapper/IRQ/PPU/service/reader/cache/clock/consumer/pad/fault 모두158동일. 나머지FPGA/ARM은159/68/E2식별만. APU채널 쓰기 차단156 유지.

선택test04: CPU/DMA출력버스·분주위상·PPU위치를 구동하되 rawmux/쓰기/allow/earlyvalid/read/sample 결선은 실제것.12쓰기위상+초기ready/캐시를 설정한158관측경계 ×3메모리위상=39수정통과, 대조39모두불필요읽기1회/18오류2.각실행48자격조건+CPU6/DMA6정상샘플,6실행. 실제CPU명령/전체DMA재생이 아니다. 관측경계19CPU03C001→24옛205A18→29새217A18→31오류가,수정판19새217A18→24응답보관→26새주소유효→31정상으로 바뀐다.158실기rawR/W미관측이므로 물리원인 확정 아님. 오래된낮은캐시/초기busy형성은 기록창이전미확정.

test01은 reset동안분주1고정으로cpu_ce를막은시험대watchdog;test02기본위상PASS/test03초기경계추가PASS지만CPU000001;test04 PRGbank6=1E로03C001및뒤의정상읽기까지맞춤. 예전시도 보존,최종통계와혼합금지. host01 13회수/256format, reuse01식한곳+ID정확비교, ARM188604NMI15stores0calls. 기존FLOAT사용,새라이선스불필요.

fit01/asm01 LE13670/5005regs/56M9K/122pins/virtual0/PLL1. 추가5.5ns배치예산-.036FAIL. 같은배치·정확155명목SDC로setup+.095/hold+.160,조건부PSRAM+3.035/SNES202.2<270ns통과. SDC59dbe240...기존과같고실제클록/falsepath/multicycle변경없음. 추가예산실패와명목통과둘다기록. 재배치불필요. PCB2ns/비동기reset recovery음수/전체IO/MTBF한계유지. M9K56/56임시이력축소는원인해결뒤.

NEXT:159전체SD폴더 적용→NES GAME 159.nh1→첫Start→1PLAYER Start한번떼기→진행되면방향키/A/B. 두159TXT와메뉴복귀결과. 플레이되면짧은영상,같은실패영상불필요. 기존적재약3분50초참고/실행약60초상한/오류조기종료,전체7분무반응이면중단기록.044/GBC복원·158재시험·A/B·무변경전체부팅을선행조건으로반복하지않는다. 실패하면실제요청순서와최초오류를비교하고정당한CPU읽기와충돌하는지먼저확인,관측없는캐시/중재확대금지. 진행되면조작/스크롤후음원차단해제.

실기성공·정상오디오·속도·저장미완료. frozen159와이전공개핀/ZIP불변,완료finish.py재실행금지. ROM/media/binary/privatepaths/licenses Git금지. 한국어4PR절/개인hungrysanta-ksc/사용자머지. 포팅참고가이드는158에서기록한고정upstream/기존검증재사용원칙유지.

---

## 이전 작업 인계

# NES 현재 인계 — 158 예측 이후 읽기 발행 지연 확인

[158 실기 결과](../../analysis/GAME158-HARDWARE-RESULT.ko.md) · [해시·16클록 해석](../../analysis/game158-hardware-verification.json)

사용자 Start 스테이지 진입 실패/메뉴 복귀 확인. 영상14.83초 표본도 선택화면 뒤 메뉴를 확인하며 실제 스테이지 플레이는 보이지 않는다. 전체393216바이트 적재·비교,104진행기록,Start/해제2구간,STOP/TXT/base/메뉴 PASS. 같은158 재시험·추가 영상·044복원 불필요. 실기 게임은 미완료다.

핵심: 새217A18 hint가-15..-8 유효하지만 -12 이전205A10응답 때 CPU03C001이 선택된다. -11..-8 use_prefetch1/ready0. -8 낮은 비트면 정상샘플. -7 CPU응답 때 hint_valid0이고 현재PPU205A18이어서 그옛주소 요청. -5 실제PPU217A18전환, -2 옛응답 뒤 새217A18요청, 0샘플미스. 단순 예측생성실패가아니다. line193dot8/PPU상태는157과같지만문맥은e200c2f4:30217a18/CPUvalid0/age1로달라졌다. 응답+요청 행 주소는새요청임.

NEXT 최우선은 source상 불필요CPUread 자격: rom_cpu_address_valid=prg_addr[15]&&prg_allow, prg_write=mw_int&&cart_pre, MMC3 ROMallow=!prg_write. rawwrite/pre0 구간에도 allow1이라 speculative read 가능,선택mapper4 conflict0. 이경로를 실제결선으로 짧게재현하고 확인되면 rawread로정당화된요청만남기는최소수정을한다. 실제이번03C001이해당쓰기였는지는 rawRW/PC없어서미확정. cpumem_read와 busconflict/CPU-DMA sample 계약도같이검토,다른mapper까지일괄변경금지.

기존158TB는 cpumem_addr/read/address_valid를강제하고cpu_sample0, 고정writelead9클록으로실제쓰기자격결선을우회했다. 같은합성72PASS만반복하지말고실기관측lowplane->CPU->hint만료->oldbank순서를회귀사례로넣는다. 정상CPU/DMA와PPUlow/high기한 유지. 이작은수정후에도정당한읽기충돌이남으면hint보관/기한중재검토. 무조건PPU우선/옛뱅크대입/기한해제/무근거캐시확대금지. 최소변경검증뒤같은SMB3실기. M9K56/56 임시이력은원인확인뒤축소. APU차단유지/오디오미완료.

이번PR100은실기결과추가만. frozen158/ZIP/publicpins불변,완료finish.py재실행금지. game158-verification.json의physical_test=false는제작당시동결기록이고현재판정은GAME158-HARDWARE. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc/사용자머지 유지.

---

## 이전158 제작 기록

# NES 현재 인계 — 158 MMC3 변경 전 그래픽 읽기 실기 시험판

[158 결과](../../analysis/GAME158-RESULT.ko.md) · [실기 안내](../../docs/nes-game158-instructions.ko.md) · [검증](../../analysis/game158-verification.json) · [이식 참고 자료](../../docs/nes-porting-reference-guide.ko.md)

PR99 머지289674a14407459a0823b154ab425e9f731f62c9 확인.157 실기의 확정 사실은 dot8 샘플 한 클록 전 물리 CHR주소205A18→217A18 변경, 즉시 승인됐지만 응답이 늦어 오류2로 종료한 것이다. MMC3 쓰기인지 PPU 논리주소 변경인지는 로그에 없어 미확정이다. CPU 점유만 원인으로 단정하지 않는다.

158은 CPU의 mw_int/주소/데이터를 실제 cart_ce보다 먼저 관측해 MMC3 선행 조회에만 예정된8000 CHR모드/8001 CHR뱅크 값을 적용한다. 실제 mapper 레지스터·주소·IRQ·PPU·service·reader·physical-tag·샘플 기한·클록은 그대로다. ARM은 식별/이름만158로 변경.67/E1 엄격검사.156 APU채널 쓰기 차단과 기존 버튼/직전16클록 이력은 유지한다. 실기 수정 성공·오디오 완료로 표시하지 않는다.

선택 test03/host02/reuse03/arm01+armcheck02/fit02+asm01/release01.72개의 뱅크 쓰기 충돌 모델은 정상 CHR 수신,108개 preview-off는 오류2,36개 늦은 논리주소 변경은 여전히 오류2.536 commit에서 정상주소 조기변경·취소·선택/정렬·모드 검사. 실제 CPU 게임 대신 버스/strobe를 구동했고 write lead9클록 고정, 이전 CPU읽기 시작12종/메모리위상3종이다. 전체 위상/게임 성공으로 확대하지 않는다. mapperTB/로그는 별도 해시 고정(result.sources에 누락된 범위를 숨기지 않는다). test01/02도 PASS인 이전 범위. 초기 materializer/정규화 실패와 샌드박스 도구실행 제한은 별도 보존, 라이선스 교체 불필요.

새 배치13731LE/5005regs/56M9K/122physical/0virtual/1PLL. setup+.099ns,hold+.171ns,조건부PSRAM+2.997ns; 추가5.5ns 배치예산도+.099PASS. 동일155SDC를 유지하고 명목 재검사했으며 무변경 재배치는 하지 않았다. PCB2ns 가정/비동기reset recovery 음수/전체IO/MTBF 제한은 기존대로. 임시 이력 포함M9K56/56이므로 여유로 계산하지 말고 원인 확인 후 축소한다.

NEXT:158 전체 SD폴더 적용 → NES GAME 158.nh1 → 첫 Start → 1PLAYER Start 한 번 후 떼기 → 진행되면 이동/A·B. nes-progress-158.txt와nes-game-last-158.txt,메뉴복귀 여부. 게임이 진행되면 짧은 영상; 같은 실패 영상은 불필요. 이전 로딩 약3분50초는 참고치이며158 실측이 아니다. 전체7분 무반응이면 중단/기록.044/GBC 복원·157 재시험·고정뱅크·무변경 전체부팅을 선행조건으로 반복하지 않는다.

실패 시158 decoder로 최초 오류와 마지막16클록을157과 비교한다. 매퍼 쓰기와 논리주소 전환 구분이 필요하면 최소 관측만 추가한다. 예측 예외를 계속 덧대기 전에 원본 MiSTer SDRAM의 PPU/CPU 채널과 우리 PSRAM 공유 서비스의 시간 계약을 검토한다. 진행되면 조작·스크롤 먼저, 이후 음원 차단 해제. 고정 MiSTer/Mesen2 MMC3/NESTang/NESdev 자료의 확인 범위와 채택 순서는 참고 가이드에 기록했다. 다른 코어도 기존 검증 재사용→플랫폼 연결 차이→최소 검사→실제 목표ROM 순서다.

frozen158/이전 source pins/배포ZIP 불변. 완료finish.py 재실행 금지. ROM/media/binary/private paths/licenses Git 금지. PR 한국어4절/개인hungrysanta-ksc/사용자 머지. 과거157 메타데이터의hardware_pending은 동결 시점 기록이며157의 현재 실기 사실은GAME157-HARDWARE가 우선한다.

---

## 이전 작업 인계

# NES 현재 인계 — 157 주소 전환 직후 PPU 기한 오류 확인

[157 실기 결과](../../analysis/GAME157-HARDWARE-RESULT.ko.md) · [원본 해시·16클록 해석](../../analysis/game157-hardware-verification.json)

게임 진입 실패/자동 메뉴 복귀는 사용자 확인. 전체393216바이트 적재·비교,104진행기록,패드5건(NONE/START/NONE/START/NONE),16클록 이력,STOP/TXT/base가 통과했다. 게임 플레이·다른 버튼·오디오는 미완료다. 동일157 재시험·추가 영상은 불필요하다.

가장 중요한 새 근거: 상대-13에205A18 선행 요청, -8에그응답과새CPU03C001요청, -3에CPU응답, -2에busy0/ready1/PPU205A18유효1. -1에실제PPU205A18→217A18/예측205A10→217A10이함께바뀌고즉시새요청, 0에PPU샘플/응답0/유효0으로fault2. 응답+새요청동시행의transaction_address는새요청이며이전응답주소는앞선pending에서판독한다. 선행읽기누락/직전CPU점유가이번즉시원인이라는설명과맞지않는다.

line193/dot8/PPU상태60820800:28606060은156과같지만오류문맥은e30042f4:30217a18(CPUvalid1/age0)로156CPUvalid0/age1과다르다. 과거논리PPU주소/매퍼쓰기주소·값/CPU PC는없다. 같은레지스터조합매핑의소스와두물리주소의상위부분동시변경은MMC3매핑전환을유력하게하지만특정bankwrite확정아니다. 논리주소상위변경도대조한다. 사운드채널차단유지;CPU사운드드라이버영향까지배제금지.

NEXT: 실제MMC3/PPU/서비스/reader로dot8직전bank-data,bank-select/invert전환과논리주소변경대조군을짧게재현한다. 새물리주소발생부터샘플까지데이터확보를수정하고NES매퍼동작의미를보존한다. 오래된뱅크데이터대입/기한검사삭제/맹목캐시확대금지. 변경경계최소검증뒤SMB3스테이지/이동/점프실기로간다. 원인해결뒤임시3M9K관측축소·제거(현재56/56). 새대형진단틀·무변경전체부팅·同157/044/GBC/A-B반복금지.

이번PR99는결과추가만. frozen157/배포ZIP/공개pins불변;완료finish.py/publish.py재실행금지. 빌드당시game157-verification.json의physical_test=false는동결기록이며현재판정은GAME157-HARDWARE가우선. 사용자머지후다음구현. 한국어PR4절/개인hungrysanta-ksc/사용자머지규칙유지.

---

## 이전157 시험판 준비 기록

# NES 현재 인계 — 157 실제 게임 정지 직전 이력 시험판

[157 결과](../../analysis/GAME157-RESULT.ko.md) · [실기 안내](../../docs/nes-game157-instructions.ko.md) · [검증](../../analysis/game157-verification.json)

PR98 머지5b82510 확인 후157 준비.156 Select 성공/Start 동일PPU오류는 유지된 사실이며 수정 완료가 아니다. 실제서비스에 CPU선점 대 늦은PPU주소 두 합성경로를 주면 같은156 최초오류 문맥이 나온다. 새16클록 이력은 둘을 구분하지만 실제원인재현은 아니다. 기존 스냅샷만으로 하나를 고르지 않는다.

157은 직전16 NES클록의 line/dot,상태12,전송주소,예측주소,실제PPU주소96비트를 남긴다. 오류클록 포함 후 정지;SPI77헤더/A0-BF 두48비트페이지;MCU STOP 뒤 회수해 TXT추가. fault_seen일 때만 마지막행=최초오류. 응답+새요청동시에는전송주소가새요청이며 이전응답주소는앞선기록과대조한다. 창이전/CPU PC/매퍼레지스터/응답데이터는없다. 게임/서비스/기한/패드/화면/156APU차단 기능은유지,관측제거소스정규화PASS. 새valid0도STOP/복귀계속.16x96은임시3M9K추가하여56/56가득찬상태;원인확인뒤축소/제거. 향후오디오메모리여유로계산금지.

선택test04/host02/reuse01/ARM02+armcheck02/fit02+asm01/release01. test02예약어compile/test03CPU캐시상태모델단언실패보존. fit01/arm01materializer단언수정;초기호스트샌드박스실행제한은기존호스트권한으로해결,새라이선스요구없음. nominalsetup+.055hold+.128/PSRAM조건부+3.763. 추가5.5ns배치예산-.042미달은별도보존. 클록/예외완화없음. 전체IO/MTBF미완료.

NEXT실기: NES GAME157 첫Start→1PLAYER에서Start한번누르고떼기→진행되면이동점프. Select반복불필요. nes-progress-157/nes-game-last-157와메뉴복귀여부. 같은실패영상생략가능. 새이력으로BGdot5~8예측/주소변경/CPU점유/승인/응답/캐시 첫실패경계를선택하고최소수정검증뒤같은게임으로복귀. 같은156/044/GBC/A-B/무변경장시간전체부팅금지. 이번은PPU수정판아님을명시한다.

frozen157/기존공개pins/배포ZIP불변;완료finish.py/publish.py재실행금지. ROM/media/binary/privatepaths/licensesGit금지. PR한국어4절/개인hungrysanta-ksc/사용자머지. 과거156progress.json의hardware_pending은동결당시기록이며현재156결과는GAME156-HARDWARE가우선한다.

---

## 이전156 실기 결과

# NES 현재 인계 — 156 Select 성공, Start 이후 같은 PPU 오류

[156 실기 결과](../../analysis/GAME156-HARDWARE-RESULT.ko.md) · [해시·버튼·진행 기록](../../analysis/game156-hardware-verification.json)

실제 Select 커서 이동과 메뉴 복귀는 사용자 확인. 완료된 패드 읽기15건에 SELECT04/해제4쌍과 마지막 START08/해제가 있다. 초기 START는 두 수신 구간으로 나타나지만 물리 클릭 횟수나 중복 버그는 미확정이다. A/B·이동·점프는 미확인. 입력 전체 고장 가설보다 PPU 경계 수정을 우선한다.

채널 쓰기 차단 상태에서도155와 정확히 같은 PPUerror2, e200c2f4:30217a18,60820800:28606060(line193/dot8,217A18,age1,응답·유효0)이 남았다. 음원만을 유일 원인으로 삼지 않는다. Select 통과의 원인이 음원 차단인지 APU상태/게임 분기/새 배치인지 미확정이며 CPU 사운드 코드는 계속 돈다. 진단 음원 차단을 정상 오디오 수정으로 승격하지 않는다.

NEXT: 일반 BG 상위 비트면 dot5~8의 예측·MMC3물리태그·공유서비스 승인·캐시·응답·샘플을 기존 근거로 좁힌다. 직전 점유/매퍼변경/응답지연을 구분할 수 없을 때만 최소 직전 이력을 추가한다. 원인에 맞춘 변경 검증 뒤 같은SMB3 Start→스테이지→이동·점프 실기로 돌아간다. 기한검사삭제/맹목캐시확대/음원전체재설계/모든버튼진단을 선행조건으로 삼지 않는다. 동일156/044/GBC/A-B/무변경장시간부팅 반복 금지.

이번PR98은 결과만 추가. frozen156/기존publicpins/배포ZIP 불변, 완료finish.py/publish.py 재실행 금지. 원본2TXT는 로컬 nes-game156-hardware에 별도 보관. 기존 GAME156-RESULT/검증의 physical_pending은 빌드 당시 동결 기록이며 현재 실기 판정은 위 결과가 우선한다. 새 패키지는 없다. 사용자 머지 후 다음 구현을 시작한다.

---

## 이전156 시험판 준비 기록

# NES 현재 인계 — 156 음원 차단·버튼 이력, 실제 SMB3 비교 대기

[156 결과](../../analysis/GAME156-RESULT.ko.md) · [실기 안내](../../docs/nes-game156-instructions.ko.md) · [검증](../../analysis/game156-verification.json)

155 실제 Select에서도 PPUerror2가 나고 메뉴로 복귀했다. 사용자가 사운드 시작과 겹침을 제안했다.155 외부DAC는0이지만 내부APU/DMC는활성이다. Mesen240프레임3비교에서Select는pulse1쓰기/2PLAYER변경,4015DMCenable없음;Start는이후DMCenable4회다. 참조일뿐FPGA활동·원인확정아니다. DMC만으로양쪽실패를단정하지않는다.

156은APU.CS에서읽기/4017쓰기만허용해음원채널/DMC쓰기를차단한다.전체APUreset/클록변경/ROM패치없음. OAM DMAget/put·PPU·mapper·서비스·기한·입력전달·화면전송유지. 음원상태가달라져게임분기가바뀔수있어최종수정아니다. CPU사운드드라이버는계속실행되므로실패해도그코드의ROM접근영향을배제못한다.

새패드관측은8비트완독후변화만최근16건+NESmasterticks(256tick내림)에저장한다. 맨처음완독은기준상태로기록;중복held는생략;부분/추가읽기는새완독으로기록하지않음. 사용자물리클릭/모든입력증거아니다. 오류/STOP후RAM불변,MCU76/80..8F로읽고최종TXT버튼이름/비트/시각/total을저장한다. SD쓰기RUN중금지. badauxvalid0은새gamefault가아니며기존보호·STOP는유지한다.

짧은actualAPU/DMA와실제gate추출시험,원본pad와256mask,ring260,last16,partial/overread/duplicate/STOP/SPI,actualC13recoverycases/256formatmasks,linkedARM을확인했다. 긴실제ROM부팅/155합성충돌반복없음. 초기test01필수parameter/02packageimport/03강제입력의net전파오류는test04수정;fit02setup-.437거부후ring640비트레지스터를M9K+2clockresponse로바꾸고test05통과;fit03-.093/fit04-.038/fit05-.614거부후512비트1M9K/256tick양자화test08/fit06setup-.092PSRAM-.096거부후CHECK5.5ns/activeIO12ns배치예산fit07배치선택;추가5.5ns목표-.010은미달보존,동일155실제clockSDC기준nominal07setup+.246/hold+.153/PSRAM+4.571PASS. ARM01들여쓰기Werror->ARM02수정. DLL623 sandbox호스트실행은권한부여실행으로통과,라이선스오류아님.

다음은한번156실기:첫Start선택->Select. 통과하면Select로1P복귀->Start->이동점프. nes-progress-156/nes-game-last-156와실제메뉴/장면을받는다. 같은실패는영상생략. 버튼로그로Start/Select정상완독·해제·동시입력부터확인하고PPU오류와대조한다. 정상진행해도APU원인확정/사운드완성으로승격금지. 같은155/044/GBC/A-B재시험금지.

개인용ZIP/ROM/media/licenses는Git금지. frozen156과옛publicpins는불변. 완료freezer재실행금지. 한국어PR4절(목표/내용/결과/의미),hungrysanta-ksc만,사용자머지. 표시속도·DMA입력공백·오디오·저장·외부IO/MTBF는미완료.

---

## 이전155 실기 기록

# NES 현재 인계 — 155 Select에서도 PPU 오류, 입력 이후 경계 재조사

[155 실기 결과](../../analysis/GAME155-HARDWARE-RESULT.ko.md) · [원본 해시·해석](../../analysis/game155-hardware-verification.json)

**155는 실제 정지를 해결하지 못했다.** 첫Start로선택화면,Select입력에서화살표이동대신오류후메뉴복귀.154두번째Start/스테이지전환과다른트리거다. 모든두번째버튼실패/Select비트정상수신/스테이지플레이를확정하지않는다. 사용자관찰상Select에서도실패하므로스테이지진입만재현대상으로삼지않는다. 추가영상/같은155/044/GBC/A-B재시험불필요.

실제로그64/DE/393216loadcomparePASS. ROMerror2/PPUdeadline,contexte200c2f4:30217a18:actual=pending217a18/age1/busyPPU1/readyresponsevalid0. PPU60820800:28606060:line193/dot8/render1/sprite0/bgtable0/logical0A18/latchpins18/readwrite2007=0/ALEhintaddrvalid0. dot8은BG상위비트면,normal155는dot3~6만켜므로hint0자체정상.154는dot6/0A10/217A10이나사용자트리거가다르므로lowplane해결·2dot개선으로승격금지. 이전2007영향·매퍼변경·직전점유·예측발행·캐시교체는현재스냅샷만으로미확인.

STOPcount14220446유지/stop_error0/base/safe1/최종TXT741바이트/사용자실제메뉴PASS. 104x512seq0..103;DISPLAY_NEXT232670->STOPPED237640=4970ms/MENU240800까지3160ms. 입력시각/FPS아님;screenframes9/trusted0. 기존회수경로는수용하고게임실패와분리한다.

NEXT:선택화면Start대Select에서실제패드바이트/strobe/read/shift를대조하고BGdot5~8의예측논리주소/실제주소/같은MMC3뱅크물리태그/요청승인/응답/캐시교체이력을연결한다. 패드가직접ROMerror2를생성하지않지만입력오류가게임경로를바꿀가능성은열어둔다. 주기적CPU점유/고정뱅크/강제PPU타일모델만다시통과시키지않는다. 기존소스·증거로좁힌뒤부족할때만최소직전이력. 실제게임을우선하고긴전체부팅/무조건캐시확대/기한삭제를피한다.

이번PR97에는결과·인계만추가한다.155펌웨어/FPGA/ZIP/frozen2359/manifest485444c85297c1cf610d4d2db6e77d4959827c3a51b0b7334aa6079c9f9ff654불변. 새로운구현·빌드·패키지없음. 다음구현은사용자머지후진행. 원본TXT는privateprobes/nes-game155-hardware. 한국어PR4절/개인GitHub/usermerges유지.

---

## 이전155 준비 기록

# NES 현재 인계 — 155 일반 배경 선행 읽기, 다음 SMB3 실기

[155 결과](../../analysis/GAME155-RESULT.ko.md) · [실기 안내](../../docs/nes-game155-instructions.ko.md) · [고정값](../../analysis/game155-verification.json)

PR96 머지4639d4b4e5ac2e054ebdb429b8ca410782095b56에서 시작. 다음은 NES GAME 155.nh1 한 번이다. 첫 Start로 선택 화면, 버튼을 뗀 뒤 다음 Start로 전환한다. 같은 지점에서 종료되는지, 진행된다면 방향/A/B가 동작하는지 확인한다. twoTXT nes-progress-155/nes-game-last-155와 실제 메뉴 복귀 여부를 받는다. 같은 증상이면 영상 생략 가능.154/044/GBC/A-B/변경 없는 전체 부팅을 다시 요구하지 않는다.

155는 실기154의 일반 BG line193/dot6 기한 실패를 겨냥한 선행 읽기 후보다. dot2 뒤 타일 이름이 확정된 구간에서 low/high plane 예측을 순서대로 준비한다. 실제 MMC3 lookup을 재사용하며 old PPUDATA overlap이 우선한다. 서비스의 demand priority/physical tags/READ16/샘플기한/클록/캐시크기/IRQ 입력/표시/패드 동작은 유지했다. 오류 검사를 지우거나 코어를 늦추지 않았다. 기존64비트 상태의 hint는 이제 일반 선행 읽기도 포함한다.

선택 collision01은 actual155 PPU/MMC3/service/READ16/70ns에 합성된4타일과12개 CPU상대시점을 넣어 메모리3위상,후보36조건 모두정확바이트/기한통과. 같은소스normal155만0으로강제한대조는각위상PPUerror2. 정확한154요청이력·실기원인확정·전체게임PASS 아님. 초기탐색의X는 내부reset_noSS해제전시작한모델설정문제였고 선택시험은해제대기+unknown거부를포함한다. 오래걸린154core05/초기30프레임을재실행하지않았다.

MCU155는154에서ID63/DD→64/DE와표식·경로·버전만변경. 모든소스와SPI관측기는정규화비교통과.154의실제C/FatFS/menu회수및관측기시험재사용;새host/observer전체시험을실행했다고쓰지않는다.155실제C해독960정상10비정상/ARM187124/NMI15stores0calls통과. fit01 setup+.015ns/hold+.178ns,조건부PSRAM+2.736ns/SNES203.311<270ns. 여유작음/전체IO·MTBF미완료. selectedasm01/reuse02/decoder01/armcheck01;재사용검사01의0x64전역치환실패는검사기오류다.

실기실패시새최종로그의주소/line/dot/age/2007/힌트를154와비교하고변경경계만좁힌다. successfulRUN이라도이동·점프는사용자화면으로판정. 로딩/held30vblank/DMA입력공백/무음/저장은그대로미완료다. 초기파일과동결155·옛publicpin은보존한다. 완료freezer재실행금지. ROM/ZIP/바이너리/라이선스/개인경로를Git에올리지않는다. 한국어PR4절/개인hungrysanta-ksc만/사용자머지를유지한다.

---

## 이전154 기록

# NES 현재 인계 — 154 PPU 상태 실기 회수, 일반 배경 읽기 기한 수정으로 진행

[154 실기 결과](../../analysis/GAME154-HARDWARE-RESULT.ko.md) · [실제 로그 해석](../../analysis/game154-hardware-verification.json)

154 추가 관측은 실기 수용 완료다. ROM393216바이트 적재·비교, 오류2 문맥·추가 PPU 상태 TXT, STOP/기본 FPGA/실제 메뉴 복귀가 통과했다. 게임은 실패했다. 사용자의 첫 Start는 선택 화면, 두 번째 Start는 다음 장면 진입 후 정지·복귀다. 선택 화면 기준 한 번과 전체 흐름 두 번은 모순이 아니며 중복 입력 결함으로 분류하지 않는다. 다른 버튼과 실제 스테이지 플레이는 미확인이다.

실제 오류 문맥 `e200c2f4:20217a10`은153과 같다. actual=pending0x217A10,age1,busy/PPUsample1,ready/response/valid0. 새 상태 `60818800:28404040`은 line193/dot6,render1,sprite0,bgtable0,VRAM0x0A10,latch/pins0x10,read2007/write2007파이프0,ALE/hint/address_valid0이다. dot6은 일반 배경 패턴 읽기다. 현재 ALE/address_valid/hint0은 해당 단계에서 예상되므로 곧바로 결함으로 판정하지 않는다. `$2007` 겹침 전용 힌트 확장만을 해법으로 가정하지 않는다. 파이프0으로 더 앞선2007영향까지 배제하지도 않는다.

NEXT:일반 배경 dot5→6의 논리/물리주소 유효화→공유서비스 승인→응답→샘플을 짧게 재현한다. 직전 CPU/PPU 요청 점유, 샘플 직전 MMC3 주소 변경, 백엔드 응답 위상을 구분하여 처음 어긋난 경계를 고친다. 현재 관측에는 직전 이력이 없어 이들은 가설이다. 필요한 실제 PPU/서비스 결선을 사용하되 인위적 조건 통과를 실기 원인 확정으로 올리지 않는다. 원인 없이 큰 캐시/클록 변경·기한 검사 삭제·전체110/240프레임 재시작을 하지 않는다. 최소 수정 검증 뒤 같은 SMB3 실기로 돌아간다. 추가 일반화 진단 체계나 같은154/044/GBC/A-B 시험을 요구하지 않는다.

진행104기록seq0..103,DISPLAY232670→STOPPED242030=9360ms,메뉴준비245210ms. 사용자 메뉴복귀 확인. screen_frames17/trusted0은 FPS가 아니다. 실제 PPU 상태를154 합성 모델 값60b6a800:484043fe 또는153주입문맥30217a19와 혼동하지 않는다. 이번 영상 없음; 장면 독립 확인이 아닌 사용자 관찰로 보존한다.

이번 PR96 업데이트는 결과·인계만이다. firmware/FPGA/ZIP/frozen2330/공개 도구 pin은 불변이다. 원본두TXT는private probes/nes-game154-hardware. 구현·시험판은 다음 작업이며 PR은 사용자가 머지한다. 한국어4절/개인계정 정책 유지.

---

## 이전154 준비 기록

# NES 현재 인계 — 154 PPU 오류 순간 상태 수집, 실기 대기

[154 결과](../../analysis/GAME154-RESULT.ko.md) · [설치](../../docs/nes-game154-instructions.ko.md) · [검증](../../analysis/game154-verification.json)

153은 실제 PPU 오류2 뒤 STOP·TXT·자동 메뉴 복귀에 성공했다. Start 중복이 없었고 다른 버튼은 미확인이다. 실제 문맥은 `e200c2f4:20217a10`: 요구=대기주소0x217a10/age1이며 응답·유효값이 없다. 원인은 아직 미확정이다.154는 오류 순간64비트 PPU 상태만 추가한 시험판이며 게임 정지 수정이나 플레이 성공으로 계산하지 않는다.

다음은 같은 SMB3(J)의 실기 한 번이다. `NES GAME 154.nh1` 실행 후 선택 화면에서 Start 한 번으로 WORLD1 쪽으로 간다. 사용자가 현재 선택 화면의 진입 방법을 확인했다. 초기 타이틀 연출의 입력과 구분하며 무조건 두 번 연타시키지 않는다. 두 TXT와 메뉴 복귀 여부를 받는다. 같은 증상이면 영상 생략 가능, 진행되면 방향/A/B를 확인한다. 원격 실기이므로 PC 연결을 요구하지 않는다. 같은153/044/GBC/A-B 시험이나 변경 없는30프레임을 반복하지 않는다.

154의 SPI74/75는 최초 오류 에지의 line/dot, 배경패턴/스프라이트/렌더링/ALE, read/write2007파이프, vram주소/래치/핀, hint/address-valid를 보존한다. 기존 주소 문맥과 같은 에지다. MCU는 기존 STOP와 상태 유지 검사를 통과한 뒤 읽고 보조 응답 형식 불일치는valid0으로만 남긴다. 전송/클록 보호는 유지한다. `tools/decode_nes_game154.py`로 최종 TXT를 해독한다. 상태는 요청 이력이 아니므로 이전 요청 점유나 PSRAM 정상 여부까지 단정하지 않는다.

FPGA·MCU는 새63/DD 조합이다. ROM서비스/캐시/샘플기한/매퍼/게임 입력·전송 결정은152와 같고153 복귀 수정은 유지했다. 실제보드 정보는 기존확정 Rev.D/STM32F401RCT6/EP4CE15F17C8N/IS66WVE4M16EBLL-70BLI×2를 재사용한다. 새배치 setup+.084/hold+.173,조건부PSRAM3.257ns. 전체IO/MTBF 완료아님. ARM187124/NMI/수신960정상10음성/실제C-FatFS메뉴 모델의 정상보조·잘못된ID 모두통과. 합성주입값을실제153관측값으로인용하지않는다.

실제152코어와 같은 ROM으로 Start 경로를 조사했으며 최종 범위는 검증JSON/core_investigation을 따른다. 추상5NESedge백엔드는 실제PSRAM/CDC/MCU/SNES가 아니다. 참조 Mesen의 두입력30/90은 WORLD1까지가지만 FPGA검증이아니다. 초기core01 선언순서실패,core02~04 조사설정변경을 위한 의도적중단은 제품실패·라이선스오류로분류하지 않는다. 최신 core05 결과와 이전 중단 증거는동결 investigation에 있다.

실기로그가오면 read2007파이프와 dot/렌더링/주소래치로 실패경계를선택해 최소재현·수정→같은게임으로진행한다. 추가일반화관측/무조건캐시확대/기한검사삭제는하지않는다. 스테이지플레이,표시속도,입력DMA공백,소리,저장은미완료다. 동결154와옛공개pin/ROM/GBC는보존한다. ROM/ZIP/바이너리/영상/라이선스/개인경로를Git에올리지않는다. 한국어PR4절,사용자가머지,GitHub는hungrysanta-ksc만사용한다.

---

## 이전153 기록

# NES 현재 인계 — 153 오류 회수 실기 통과, PPU 기한 원인 수정으로 진행

[153 실기 결과](../../analysis/GAME153-HARDWARE-RESULT.ko.md) · [원시 기록·해석](../../analysis/game153-hardware-verification.json)

153의오류문맥수신·TXT·STOP·기본FPGA·자동메뉴복귀를실기로수용했다. loaded/compared393216,verified1,stop_ok/base_restored1,stop_error0. RUN은실패:run_rom_error2,first_error1. **실제**문맥e200c2f4:20217a10,bit63PPUtag1,actual=pending0x217a10,age1,busy/pendingPPU1,ready/response/cpu_sample/cpu_valid/ppu_valid0,ppu_sample1. 모델주입값e200c2f4:30217a19와혼동금지.151pending0x217a18과8바이트차이지만151actual없어동일원인확정금지.

104개512byte진행기록seq0..103. LOAD완료95290/CHECK233010/DISPLAY_NEXT233020/DISPLAY_STOPPED242230/BASE243090/MENU_PREPARED245380ms. RUN구간9.210s,STOP표시→메뉴준비3.150s는MCU시각이며정확한실제화면/오류시각아님. count26415116STOP후유지. 최종PREPARED_RESET_HELD는저장시점이며사용자가후속실제메뉴복귀확인. 화면stage6/frames17/trusted0은FPS나화면정상증거아님.

사용자는이전과같은스테이지시작지점에서멈춘듯한뒤바로메뉴복귀,이번Start중복없음을확인. 다른버튼미확인. 새영상없음;정확한장면독립확인이나실제스테이지플레이PASS로승격금지. 같은153영상/실행/044복원요구불필요.

NEXT:실제SMB3Start이후0x217a10주변요청/응답/PPU샘플순서를좁힌다. 오류순간주소는맞고busyage1인데유효데이터/응답없음. 늦은요청발행,직전요청점유,선행읽기·캐시교체,백엔드응답전달을구분한다. addr일치만으로PSRAM정상/고장·prefetch원인확정금지. 현재로그엔직전이력/PPUscanline/cycle/mapperregs없음. 초기30프레임만무변경반복금지;실기진입에필요한변경경계검증후같은게임으로진행. 재현부족할때만최소추가관측. 오류검사삭제/무조건캐시확대/클록늘이기로PASS만들지않음. Start중복은이번없으므로입력수정을먼저추가하지않고PPU해결후방향/A/B를확인.

이번PR95는실기결과/인계업데이트만.153firmware/FPGA/ZIP/frozen1845/공개sourcepin불변. 원본두TXT는private probes/nes-game153-hardware. 새RTL/ARM/Questa/FIT/패키지없음. 이전153수정목표달성,정상게임플레이·표시속도·DMA입력공백·소리·저장·기존IO/MTBF는미완료. 다음구현은사용자머지후새PR;한국어4절/개인계정만사용.

---

## 이전153 준비 기록 — 현재 실기 결과는 위를 따른다

# NES 현재 인계 — 153 오류 회수 수정판, 실기 결과 대기

[153 결과](../../analysis/GAME153-RESULT.ko.md) · [설치](../../docs/nes-game153-instructions.ko.md) · [검증](../../analysis/game153-verification.json)

PR94 머지 b01e7cf5926b9e637987c49cb4e135ae65416970에서 시작. 153의 다음 행동은 **SMB3(J) 한 번의 실기 실행**이다. `NES GAME 153.nh1`, `nes-progress-153.txt`/`nes-game-last-153.txt`, 화면 이후 영상·누른 버튼·첫 화면/메뉴 시각을 받는다. 사용자는 원격 실기이며 PC 직접 연결은 하지 않는다.151 첫 화면 실측 약3분50초, RUN 최대약60초/오류시조기종료, 전체7분은 사용자 관찰 상한. 기존044/GBC 반복 보고는 요구하지 않는다.

153에서 `context146()`의 `(hi[3]&0x80u)` 거부만 제거했다. 이 비트는152의PPU주소표식이다. 양쪽DC식별·유효성·오류일치/비영·버전1은 그대로. 변경4파일은run136/include,메뉴표식·파일이름,checkpoint이름,VERSION. 새하드웨어ID를 추가하지 않았고62/DC를엄격히유지한다. `fpga_n153.bi3`는152선택FPGA와바이트동일. 이수정때MAP/FIT/Questa/SNES/core반복없음. 생산자비트변경시실제수신→STOP→TXT→메뉴를확인하는공통규칙도추가했다.

선택 arm02/armcheck01/host04/context01/release01. 실제153 C+FatFS+메뉴 모델에서384KiB적재/비교와합성PPUerror2→문맥e200c2f4:30217a19→STOP→기본FPGA→TXT쓰기/읽기→64KiB메뉴→RESET해제통과. 이전비트거부조건만복원하면STOP/BASE/MENU미도달 재현. 정상문맥30/잘못된응답10통과. 전송만이전bitbang어댑터이며SPI149엔진/GPIO/시간/SD/FPGA응답은모델: 실제ARM/전기증거아님. unchanged149SPI검증재사용. ARM186852/NMI15stores0calls3DSB2ISB검사. 초기arm01문자열개수/host01-03소스위치·헤더실패보존,제품오류·라이선스아님.

**게임최초정지원인과복귀결함을분리한다.** 151은실제PPUdeadline2였지만152에는최종TXT가없어실제오류코드·문맥미확인.153은복귀결함만수정,PPU원인/Start중복입력수정완료아님. 새로그bit63=1이면low25는PPU실제요구주소(상위3비트0),0이면CPU물리주소. pending는bits46:25,age54:47. 표식은오류종류가아님. 실제와pending주소및error/age/busy/ready/response/valid를대조하고특정경계만재현한다. 주소일치/불일치만으로PSRAM원인단정금지. 모델에주입한주소를실기관측값으로인용금지.

성공수용은실제오류문맥TXT+자동메뉴복귀. 게임이WORLD1에서같이멈춰도새문맥이남으면다음원인수정으로넘어간다. 무복귀가남으면가장늦은checkpoint와컨텍스트검사/guard/STOP/base/menu중새실패경계를좁힌다. 같은152/044/A-B/변경없는전체부팅/배치반복금지. 30vblank표시/입력DMA대기공백/오디오·emphasis·저장/기존IO·MTBF제한은유지한다.

동결153 manifest와소스pin은검증JSON에있다. 완료freezer/옛증거를재실행·수정하지않는다. 새실기결과는별도hardware폴더/결과JSON에보존. ROM/ZIP/바이너리/영상/라이선스/개인경로는Git에올리지않는다. PR은한국어제목과작업목표·작업내용·작업결과·작업의미4절;사용자가머지한다. GitHub는hungrysanta-ksc만사용하고musinsa선택금지.

---

## 이전152 기록 — 현재 작업은 위153을 따른다

# NES 현재 인계 — 152 오류 문맥 수신 결함, 복귀·최종로그 실패

[152 실기 결과](../../analysis/GAME152-HARDWARE-RESULT.ko.md) · [원시 로그·재현](../../analysis/game152-hardware-verification.json)

현재152 재시험하지 않는다.83행 seq0..82,마지막DISPLAY_NEXT232740ms;LOAD/CHECK393216완료경로. 실제RUN 코드는START직전 기록,그 이후SD금지이므로 마지막행이멈춘위치라는뜻아님. 최종nes-game-last없음.94.13초영상14~15제목→16초WORLD1/MARIO×4 시작안내월드맵,이후90초대까지동일. 실제스테이지플레이미확인. 사용자프리즈후60초이상대기/메뉴FAIL/본체RESET메뉴FAIL/전원재인가메뉴PASS.14초Start1회보고;중복입력은미확정(30vblank표시샘플/held상태의다중단계소비가능). 다른버튼은정지후이므로판정불가.

확정결함:152서비스새context bit63=1(PPUactual주소) vs배포MCU context146의 `(hi[3]&0x80u)` 거부. 실제run136/context146 C를사용한host시험에서taggedPPU오류→contextfalse→fail094→leave/STOP/DISPLAY_STOPPED각0을재현. 거부한조건제거대조는각1/문맥정상,기존형식·invalidID/valid/error3개거부유지. 실제152 faultcode/context는없으므로실기관측이오류2였다고단정하지않는다. 잠재경로fail094는SNESRESET유지/cleanupbase건너뜀/finalpersistfalse로증상과부합. 게임최초정지원인과복귀실패를분리한다.

NEXT153: 기존152/frozen/패키지는그대로보존하고 MCU수신에bit63형식반영. 소스함수실제연결로 taggedPPU error→context→STOP→최종TXT·메뉴복귀 검증,잘못된응답/guard거부는유지. 같은FPGA와배치를재사용할수있으니단순MCU수정때MAP/FIT/30프레임/fullwrite/A-B/044반복금지. 이후한번의SMB3실기로actualPPU주소확보. 수신기호환시험은비트정의변경의필수경계;FPGA단위/ARM링크별개PASS로대체금지. 오류를숨기거나느슨한응답허용으로우회금지.

이번은PR94에결과/인계/공개재현도구추가만. 새firmware/RTL/ZIP없음. 공개도구 tools/reproduce_nes_game152_context.py --baseline <probes> --out <freshASCII> --gcc <hostgcc>;현재GCC는sandbox DLL WinError623일수있어허용host실행필요,라이선스아님. private probes/nes-game152-hardware에원본/188프레임/접촉시트/재현보존. 모든152 pin/manifest/ZIP불변.

---

## 이전152 제작 기록 — 위 실기 결과가 우선

# NES 현재 인계 — 152 입력 개선판 준비, PPU 원인 미해결

[152 결과](../../analysis/GAME152-RESULT.ko.md) · [설치](../../docs/nes-game152-instructions.ko.md) · [검증](../../analysis/game152-verification.json)

PR93 merged9b26d7b6a8375ff2cc10e8a6774bf5cced39d2d2.152는62/DC 조합. 사용자에게 NES GAME 152.nh1 한 번 실행, nes-progress-152.txt/nes-game-last-152.txt와 화면 이후 영상·버튼 이름·첫 화면/메뉴 시각을 받는다. 같은SMB3 ROM/384KiB 적재·대조·최대60초RUN·오류STOP/base/menu. 로딩 가속은 변경하지 않았다.151 실측 약3분50초, 실행총7분 관찰 상한이다.

**PPU 오류 수정은 미완료. 실제151 오류를 모델에서 재현한 것이 아니다.** 같은 서비스 동작을 유지하며 fault_context bit63=1일 때 low25에 실제PPU 요구주소(상위3비트0)를 기록한다.0이면 기존CPU물리주소. pending주소는bits46:25,age는54:47. bit63은주소형식표식이지오류원인아님;backenderror가동시에있으면기존우선순위가우선. 다음로그에서pending과actual을비교한다. 같으면요청기한/백엔드점유/응답,다르면주소변경·선행읽기·캐시 경계를 우선검토하되주소만으로원인확정금지. 부족할경우에만해당경계의최소추적추가.

입력은30vblank 화면유지루프에서매vblank수집. 실제SNES모델62회/8개버튼1프레임펄스PASS,기존1512회/0개;2RGB114688픽셀동일. 전체DMA/프레임대기공백의frame34펄스는여전히누락. 처음검증기가이펄스까지기대해실패한client01보존,제한을명시한client02+old01선택. 실제버튼/게임소비확인아님. 약0.2~0.5초누르고떼며제목→맵→스테이지를확인한다. 표시자체는30vblank유지이고NES로직은계속실행;60fps/음성/저장미완료.

선택asm01에fit01전체DB/소스/보고서포함.13648LE927LAB4989reg52M9K1PLL122physical0virtual;setup+.102hold+.179,조건부PSRAM+1.725ns/SNES200.273<270ns. 기존151서비스에서context배선외코드일치.6문맥경계/32768ROM주소/ARM186860 strongNMI/압축복원·패키지PASS. 전체IO/MTBF/전기실측아님. 변경없는부팅30프레임/19초전체핀모델/전량적재/044/A-B반복안함. 이번범위는입력개선+빠진오류주소,원인수정완료라고승격금지.151자료및이전공개pin보존,freezer/완료시험재실행금지.

---

## 이전151 인계 — 현재 다음 작업은 위152를 따른다

# 151 화면 성공, PPU 읽기 오류 기록

[151 실기 결과](../../analysis/GAME151-HARDWARE-RESULT.ko.md) · [원시 로그·문맥](../../analysis/game151-hardware-verification.json)

151 실제 SMB3 제목·캐릭터·갱신 및393216바이트 적재/대조/STOP/base/메뉴 복귀 PASS. 정상60초RUN은 FAIL이다. run_rom_error2(PPU 샘플 기한),first_error1(MCU 관측오류),context6200c2f4:3003f887. pendingPPU 물리0x217a18/age1/busy1/ppu_sample1/valid0/response0/ready0. cpumem_addr0x3f887은PC아님. 실제요구ppumem_addr/scanline/cycle은기존문맥에없다. pending주소가요구주소와같다고가정금지.

NEXT 같은SMB3의 제목/Start이후 PPU요청·중재·선행읽기·캐시 경계를 실제 오류 문맥에 맞춰 재현한다. 초기30프레임만무변경반복하거나기한검사를없애지않는다. 재현추적에서 부족한 PPU요구주소/시점을 확보하고 필요시에만최소실기관측추가. 이어패드수집을0.5초화면유지와분리해짧은눌림누락을줄인다. 사용자Start반응보고는보존하되자동제목전환과구분불가,다른버튼/맵/스테이지미확인. 입력전체정상/고장단정금지. 같은151/A-B/044재시험요구없음.

로그ENTRY→DISPLAY233.010초(사용자약230초와부합),RUN19.270초,MENU255.510초. 영상23.90초/약20초메뉴. 사용자35~40초는추정으로별도보존;60초타이머오류가아니라검출오류조기종료. stage6/frames34는그럴듯하나trusted0유지,원본FPS아님. flags3은STOP후reset+sticky,처음부터reset주장금지. 이번에는결과/PR93만갱신,코드·패키지·frozen151불변. 새구현은다음작업.

---

## 151 제작 시점 기록 — 위 실기 결과가 대체

[151 결과](../../analysis/GAME151-RESULT.ko.md) · [실기 안내](../../docs/nes-game151-instructions.ko.md)

## 다음 작업

사용자의151 실기 두TXT·게임 화면 영상·메뉴 복귀·실측 시간을 받는다. 표식 NES GAME 151.nh1,결과 nes-game-last-151.txt,진행 nes-progress-151.txt. 패키지 식별61/DB.150의5~6분 체감은 사용자가 철회했으므로 원인·성능 근거에서 제외한다. 다음에는 표식 실행→첫 화면 변화→메뉴 복귀를 초시계로 측정한다.

기존 소비자는 쓰기 초반 stale data를 확정할 수 있었다. 늦은 데이터 모델에서150의 A5 반환 누락·초기A5 오인식·stage0x70을 재현했고151은 /WR 종료 직전 tuple로36검사·18인과 대조를 통과했다. 실기 버스 파형을 측정한 것은 아니므로 물리 원인 확정으로 쓰지 않는다. 상태 표식은 같은 방식으로 고쳤지만 MCU의 trusted=0은 유지한다. stage/frames는 FPS가 아니다.

실제 게임 화면을30vblank(약0.5초) 유지한다. 게임 CPU/PPU는 계속 실행하며 지난 프레임은 버린다. 거친 표시·짧은 DMA 검정 구간은 예상되므로 이번에는 그림과 조작을 먼저 본다. 패드도 화면마다 수집하므로 Start/방향/A/B를 약1초 유지한다. 같은 SMB3 ROM이다. 새로운 A/B 패턴,변경 없는30프레임/전량쓰기/044복원 시험 금지.151에서도 그림이 없으면 원본PPU/고정버퍼/물리SNES수신의 최소 요약을 비교한다.

fit01:13644LE/916LAB/4986reg/52M9K/1PLL/122핀,같은클록setup+0.021/hold+0.174ns. 조건부PSRAM+3.387ns,SNES읽기201.566<270ns,배선/MTBF 미실측. 선택test01:늦은쓰기36/인과18,픽셀57344/패드80/ROM32768;client01:2프레임114688RGB. ARM01/검사02:186860바이트,61/DB명칭만변경,NMI15store0call3DSB2ISB. SPI명령60·크기0x60000/적재·비교·60초RUN/STOP/base/menu 유지. CPU/PPU/MMC3/PSRAMreader/loader/frameRAM 기존소스 재사용. ASM01/release01만사용.

실행환경 실패도 보존: FLOAT 선검사 호스트조회·objdump DLL은 sandbox실패 후 기존승인 호스트 실행으로 통과;로그 취합UTF16 인코딩 오류는 같은원문 재처리. 재시험으로 기능실패를 덮은 것이 아니다. 완료151freeze/이전archive변경 금지. verify_nes_game151.py는해시검사용. ROM·미디어·라이선스·개인경로를Git에넣지않는다. 개인hungrysanta-ksc만사용. 한국어PR4절,사용자머지.

---

## 이전150 기록 — 다음 계획은 위151이 대체

[150 실기 결과](../../analysis/GAME150-HARDWARE-RESULT.ko.md) · [검증 메타데이터](../../analysis/game150-hardware-verification.json)

## 지금 바로 할 일 — 아래의 실기 대기 기록을 대체

150의 384KiB 적재·전량 대조, 약60초 RUN 활동·관측 오류0, STOP/base/실제 메뉴 복귀는 통과했다. 게임 그림은 밝고 거의 균일한 점멸로 표시되지 않았고 조작은 미확인이다. `run_passed=1`을 게임 성공으로 해석하지 않는다. stage112/frames47/mask8은 trusted=0이며 FPS·DMA 완료 근거가 아니다.

다음은 같은 SMB3의 PPU 원본→고정 프레임→물리 SNES 읽기/DMA 결과를 최소 요약으로 구분해 첫 차단 지점을 고친다. 필요하면 실제 게임 한 프레임을 유지해 내용을 확인한다. 기존 모델은 저장된 초기30번 프레임 재생과 모델 바이트를 받은 SNES 표시를 별도로 검증했으며, 물리 동시 연결/60초 게임 정답은 검증하지 않았다. 270ns 버스 샘플 가정을 실제 DMA 구간과 대조한다. 점멸은 forced-blank 전체DMA의 영향일 수 있지만 게임 그림 부재까지 정상이라고 단정하지 않는다. 원인 확정 전 클록·맵퍼를 무작정 바꾸지 않는다.

104개 진행 기록: LOAD92.230초, CHECK137.590초, ENTRY→표시232.740초, 표시 구간60.650초, MENU_PREPARED296.550초. 사용자 체감5~6분은 별도 보존한다. 전송 대기 개선은 필요하나 현재 게임 화면의 차단 원인과 구분한다. RUN 중 SD 쓰기 추가 금지, 필요한 요약은 안전한 STOP 후 저장. 같은150 재시험·A/B·변경 없는30프레임/전체쓰기·044복원을 다시 요구하지 않는다. 다음 수정에 필요한 경계 검사 후 곧바로 실제 ROM 실기로 간다.

이번에는 결과 기록과 PR92 갱신만 수행했다. 기존150 frozen4235/패키지/공개 소스 pin 불변, 새 펌웨어 없음. 사용자 머지. 한국어 PR4절과 개인 GitHub 계정 규칙 유지.

---

## 150 패키지 제작 시점 기록 — 아래 실기 대기 문구는 위 결과로 대체

[150 결과](../../analysis/GAME150-RESULT.ko.md) · [실기 안내](../../docs/nes-game150-instructions.ko.md) · [149 적재](../../analysis/GAME149-RESULT.ko.md) · [148 코어](../../analysis/GAME148-RESULT.ko.md)

## 지금 바로 할 일

**150 패키지의 실제 SMB3 화면·Start/방향/A·B·메뉴 복귀와 두TXT/영상 확인이 다음 작업이다.** PR91은9f97bb7ae4c6a96b57d19ac2b250679edd3d3a0b로 머지됐다. 이번 별도PR은150이다. 추가A/B,동일30프레임,무변경 전량 적재,044복원 보고를 요구하지 않는다. 모든 코어는 최소 필수 경계를 확인한 뒤 실제 목표 ROM 실기를 우선한다.

표식 `NES GAME 150.nh1`,진행 `nes-progress-150.txt`,결과 `nes-game-last-150.txt`. 패키지 안의 firmware와fpga_n150은 **60/DA**만 허용한다.149의5F/D9나146과 혼용 금지.60초 유한 RUN·오류 조기 종료·STOP/base/menu·강한NMI를 재사용한다. 실기PC연결·추가부품·새라이선스를 요구하지 않는다. 사용자 제공 ROM을 포함한ZIP은 로컬전용이며GitHub에 올리지 않는다.

## 이번에 완성된 연결과 제한

최종 PPU6비트 픽셀 → 38개의512×18 RAM → SNES8bpp DMA.256×224(위아래8줄제외),한 프레임 고정·release후다음완성프레임,게임CPU/PPU는 계속 실행. 스프라이트·스크롤·CHR은행변화는 PPU의 실제 합성 결과를 사용한다. 패드 snapshot/ACK + CPU읽기 하강후 직렬이동을 연결했다.

**전체57344바이트 복사 중 forced blank이므로 검정 구간·낮은 화면갱신률이 예상된다.** 60fps/부드러운마리오 완료가 아니다. 실기에서 게임·입력 경로를 먼저 확인하고 전송량·표시 속도를 후속 개선한다. 오디오0,emphasis무시,저장지속성없음. stage/frames는 소프트웨어 표식으로 TV정상/FPS 근거가 아니다. 새로딩시간은 미측정이며5분 관찰상한 후 로그회수를 안내했다.

## 재사용할 선택 근거

video02 전체57344바이트/패드80 + 동시 덮어쓰기차단/release/recapture/reset PASS.rom01 32768주소2KiB미러·벡터·rawownership PASS.client03 실제SNES CPU/DMA/PPU에서 실제게임스냅샷+64색2프레임 RGB전부 일치. 새 CPU30프레임은 돌리지 않았고148의30프레임/CPU1425678/PPU384638/mapper468/오류0 근거를 재사용한다. 독립게임정답·실기 구동 확인은 여전히 아니다.

선택fit02:13590LE923LAB4937reg52M9K1PLL122physical0virtual.setup+0.010/hold+0.179ns.원래rawCDC/reset음수는 보존.새 호스트reset은 local2FF.패드 held-data6.516ns/2단계동기화.14hostcycle+배선가정 SNES201.355ns<270ns.ROMreader 주소17클록/CE·OE16클록 단계별 계산으로 PSRAM조건부+5.088/+0.780ns. 작고 미측정인 여유이며 전체IO/MTBF승인 아니다. 기존8µs/양클록정지CE9µs/E1E2/ACK16/124격리/source-lock4 제한 유지.

ARM02 186860bytes SHA94aa2def9f8a03fa6f297160b443308c2eed2dae1364436b66f053c71eb8ab19.149하드웨어SPI·헤더/CRC/전량대조/FINISH후START동작 유지,식별/파일명만변경.강한NMI15store0call3DSB2ISB.선택asm01 압축복원,release01 ZIP12개내부해시 PASS.펌웨어 단독검사 installable=false는 단독범위 표시이고 최종 조합만normal_trial_ready다.

## 실패 보존·다음 판단

fit01 -2.816ns 주소계산 미채택 → 32항목상수열조회+행/열합산분리.동일fit02의 초기PSRAM계산 -0.864는 주소와CE를같은16클록으로 합친보수식;동일경로표에서실제17/16구분.원래실패JSON보존,데이터시트70ns/배선여유를 줄이지 않음.초기Quartus중단/잘못된Mesen실행위치/239행RGB검사기/MCU준비역치환오류는150결과문서에 명시했다.

다음은 실제결과가 나오면 최초막힌단계를 고친다.적재/대조성공과게임화면을구분하고,물리ROM오류가있으면first-fault문맥/PSRAM경로를우선한다.게임과입력성공이면전송갱신/검정시간개선으로간다.새진단체계완성을구동조건으로추가하지않는다.

이전146~149 및150 frozen은 불변.완료freezer/전체build재실행금지.검증은verify_nes_game150.py로해시확인.공개Git에는ROM/바이너리/미디어/라이선스/개인경로없음.GBC152/NES334/기존public pin보존.한국어PR4절(작업목표/내용/결과/의미),사용자머지.개인hungrysanta-ksc만사용하며구회사계정·대화형인증fallback금지.

보드:FXPAK Pro Mk.III Rev.D/2022-05-02,STM32F401RCT6,EP4CE15F17C8N,IS66WVE4M16EBLL-70BLI×2.목표SMB3(J) SHA256 dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49,mapper4,PRG256KiB+CHR128KiB.기존StarterFLOAT1seat 래퍼와개인GitHub설정을사용한다.
