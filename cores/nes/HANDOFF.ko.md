# NES 현재 인계 —136 최초 최소 RUN 실기 패키지

[136 결과](../../analysis/RUN136-RESULT.ko.md) · [검증메타](../../analysis/run136-verification.json) · [실기 안내](../../docs/nes-run136-instructions.ko.md) · [A–E 계획](../../docs/development/NES-MILESTONE-AUDIT-135.ko.md)

## 지금 할 일

사용자136 실기에서 두 TXT·메뉴 복귀·044 메뉴/GBC 복원 결과를 확인한다. 실패 시 마지막 성공 단계~첫 실패 경계만 수정한다. 정상 CPU 활동 확인 뒤 기존H1 소비자와 실제 NES 화면·입력을 연결한다. 새 실패 없이 같은 오프라인 시험·배치·로그 확장을 반복하지 않는다.

`NES RUN 136.nh1`은빈선택파일이며 새NES-RUN136 펌웨어·fpga_n136.bi3·합성run136.nes를함께사용한다. RUN 대기16ms와전체SD적재시간을구분한다. 기존119약491초,이번실기미측정,사용자관찰기준10분. 영상필수아님. 로그는 `/sd2snes/nes-progress-136.txt`, `/sd2snes/nes-run-last-136.txt`. 최종메뉴PREPARED는RESET해제/화면복귀증명이아니므로사용자확인필요.

## 선택본과 재사용

135fit03 RTL/QSF/라우팅불변,ARM136은실제116소스기반. selectedhost05/RTL02/ARM03/ARM-check03/STA01/IO03/ASM01/release01. 로더59/관측D4만허용. **RUN STOP응답flags2/count81920**; 구형적재전STOP idle0규칙으로되돌리지않는다. 초기RTL대조실패로발견해수정했다. RUN중SD쓰지않고고장후로그강행하지않는다. 정상경로만STOP/base/menu복구.

현재배치270heldpairs/12chains검토,음수reset80행은동기화체인비동기입력. 패드지연포함읽기조건부여유1.935ns는PCB왕복2ns미측정가정하에서만성립한다. 전체IO/MTBF/모든고장안전성미완료. E1/E2/8µs/양클록정지CE9µs반례보존. 더넓은signoff는이번정상한번의시험과구분한다.

실기활동미확인상태. 16관측/카운터증가는CPU명령정확성·PPU화면·게임성공과다르다. 기존H1영상진단과실제NESproducer연결은다음C. 135셸885LAB/12M9K/95실핀의자원여유를화면/MMC3제품여유로상속하지않는다.

## 보존과 이후 목표

119 동일116/CF86 전체80KiB 적재/검증/메뉴·044복원실기통과,해당GBC미보고.044기존GBC정상근거유지.113정지근본원인미확정.124archive격리와125독립핀근거유지. 완료finalizer재실행·동결044–136수정금지.136새실기결과는별도관측기록으로추가한다.

SMB3(J)첫목표: mapper4/PRG256KiB+CHR128KiB/393232bytes/SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재80KiB합성NROM진단을게임384KiB지원으로해석하지않는다. C화면/입력→D SMB3플레이/오디오→E맵퍼호환성. 기존6/5/1은제한진단지표.

source-lock 보류4건미해결;새upstream원본반입/공개바이너리없음. Git은소스/도구/문서만,개인ZIP은로컬. GBC152/원래NES334/과거공개핀보존. 한국어PR제목및작업목표/내용/결과/의미4항목,사용자머지. PR81병합확인.
