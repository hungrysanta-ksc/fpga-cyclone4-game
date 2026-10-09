# NES 현재 인계 —116 기본 FPGA 복구 전용 실기 대기

[116 결과](../../analysis/BASE116-RESULT.ko.md) · [실기 안내](../../docs/nes-base116-instructions.ko.md).

115 사용자로그는113펌웨어/09480 표식으로10분이상 실행한결과다.80KiB전체적재·읽기비교/CHECK_FINISH·STOP통과,BASE_START487.45초 이후 미확인이다.최종094TXT없음.이번복원은재시험하지않았으며이전복원성공과구별한다.물리원인을SPI나파일로단정하지않는다.

## 다음 행동

`NES BASE 116.nh1`한번만실행,최대60초,`nes-progress-116.txt`와최종094TXT유무/실제메뉴복귀를받는다.일상사용전정확044복원.영상/LED/분해/PC USB요구없음.새표식과옛09480/ENTRY113표식을혼동하지않게안내한다.동일한8분적재시험을반복하지않는다.

짧은진단은CF86구성→식별→빈상태STOP→기본FPGA복구→실제메뉴SRAM재적재다.ROM입력/적재/비교/RUN없음.최종verified=0정상.기존113의SD CMD12인계수정/CSS/NMI/차단보호유지.최초로그전실패가능성도유지한다.

BASE_FILE_OPEN_NEXT/OPENED/PINS_READY/STREAM_END/DONE_HIGH또는TIMEOUT/PGM_OK또는REJECT/SPI_STATE_NEXT/TOKEN_NEXT/TOKEN_RESULT/BASE_DONE으로원인범위를좁힌다.모든로그SPI_SR/CR1포함.공유고장뒤SD/FPGA새IO금지;오류뒤닫기/기록을무조건추가하지않는다.짧은실행과추가로그가타이밍/이력의존오류를가릴수있으므로성공해도전체80KiB복구통과로승격하지않는다.

## 검증과 현재 상태

PR62/63 merged/master043c4381d50de42ddf11111eaa3330f565b4fec8에서분기.최종host03정상/6고장/80KiB회귀8개와FatFS재열기2개PASS.ARM185680바이트,변경C/구성디코더동일·강한NMI벡터/15store0call확인.원시실기114/115도116증거에보존.카드/핀/시간/초기상태/응답모형한계유지.새RTL/fit/ASM/Questa없음.

host01시험기선언순서/host02잘못된SD고장phase와인자/arm-check01역사적빌드도구해시가정오류보존.제품소스수정없이시험기와검사기수정후같은ARM검증.완료finalizer재실행/동결044–113및116변경금지.113공개핀과GBC152/최초NES334보존.

## 유지할 원칙

최소보호·관측·정확한파일쌍·독립복원이준비되면실기자료로다음범위를결정한다.이미승인된제한진단의재승인은요청하지않는다.한국어PR제목과작업목표/작업내용/작업결과/작업의미4절,사용자가머지한다.새PR상태는다음턴에확인한다.

전체준비도4완료/7부분/1미완료.첫게임SMB3(J) mapper4 PRG256KiB/CHR128KiB,ROM393232바이트 SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49.제한80KiB의실기PASS는384KiB게임지원/RUN증거가아니다.E1/E2/8µs미해결·양클록정지lockedHIGH CE9µs반례유지.ROM/바이너리/미디어/라이선스/private경로Git금지.
