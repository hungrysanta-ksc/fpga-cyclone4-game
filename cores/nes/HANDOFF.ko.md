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
