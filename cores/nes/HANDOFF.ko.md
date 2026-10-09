# NES 현재 인계 —120 정상속도 코어 메모리 후보 선정

[120 결과](../../analysis/CORE120-RESULT.ko.md) · [검증 메타](../../analysis/core120-verification.json) · [119 시험 패키지 절차 기록](../../docs/nes-full118-instructions.ko.md)

119 전체80KiB ARM116/CF86 적재·비교·STOP·base·메뉴와사용자044복원은실기통과했다. 새메뉴준비491.34초는펌웨어경과이며사용자는벽시계10분여부불확실했다. GBC플레이미보고. 정상기준선을보존하고전체80/짧은BASE/ENTRY를반복하지않는다.113원인은미확정이며새로그의타이밍영향가능성을남긴다.

## 다음 작업

READ_CYCLES8/70ns를실제코어전체8프레임과추가위상에적용한다. 현재120은부팅·PPU128샘플까지만검사했다.핀단위16위상통과를코어전체위상통과로오인하지않는다. 입력ROM/CPU·PPU/주소기준은변경하지않고데이터기한오류를숨기기위한NES감속·프레임버림을하지않는다. 실패하면읽기서비스/캐시/선행읽기구조를개선한다. 통과하면같은전체후보의보호/클록/보드핀/자원(과거0594LAB여유)/실제SNES영상소비자를검토해최소RUN실기후보를만든다. 단순96KiB재시험이나CPU없는적재검증을먼저반복하지않는다.

8클록70ns는시뮬레이션후보이며현재SD에설치할새비트스트림이없다.116과097CF86/044복원은계속성공기준선이다. 외부전기E1/E2·8µs·양클록정지lockedHIGH CE9µs반례는미해결이다.

## 현재 근거

core04: 3클록25ns 두입력통과,3클록70ns 두CPU데이터오류,7/8클록70ns각두입력통과. 정상각59492응답/CPU123314/PPU128,tick854269,반환4→5NES클록. 모델은실제052코어/early service/CDC와고정지연PSRAM이며보드PLL·SPI로더·MCU·전체게임아님. 동일prefix결과를독립게임호환성으로세지않는다. unit01:8클록70ns16위상/8400읽기/208취소/110ns거부. 선언주기와1ps양자화주기를구분한다(메모리11.904ns/코어46.560ns). 8클록95.232ns에서70ns를뺀값은전기승인이아니다.

공개052 artifact의live source+fixture를핀해재사용했고미완료HDL채택원본을Git에추가하지않았다. wrapper는기존FLOAT를1석으로직렬실행하고끝나면서버를정리한다. 초기사료목록KeyError/의도중단02/선언오류03/구문실패보존. core04와unit01이최종이며완료finalizer를재실행하거나과거044–113/116/118/120동결자료를수정하지않는다.

## 재현과 관리

`run_nes_core_memory120.ps1`에Python/FloatWrapper/QuestaBin/Baseline(핀된052live)/새ASCII Out을전달한다.단위검사는동일FLOAT RunOnly 안에서 `nes_memory120_unit.py --out <new> --questa-bin <bin>`을실행한다. `verify_nes_core120.py --evidence <frozen120>`으로결과/해시를확인한다. 라이선스새smoke나uncounted경로재시도금지.

PR65병합459358e31d29b36cf9b817cbb48c437e67f7ad29 확인. 한국어PR제목과작업목표/내용/결과/의미4항목,사용자가병합한다. 최신체크리스트6완료/5부분/1미완료는정상80진단범위이며게임완성률아님. SMB3(J) mapper4 PRG256KiB+CHR128KiB/393232bytes/dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49 첫목표유지. GBC152/최초NES334/과거공개핀보존. ROM/바이너리/미디어/라이선스/private경로Git금지.
