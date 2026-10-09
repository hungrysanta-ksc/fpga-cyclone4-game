# NES 현재 인계 —126 동기화 배치 적용, 다음은 로더·소유권 통합

[126 결과](../../analysis/CONTROL126-RESULT.ko.md) · [검증 메타](../../analysis/control126-verification.json) · [125 데이터 계약](../../analysis/CDC125-RESULT.ko.md)

## 바로 이어서 할 일

**126 fit02를 기준으로 로더 WRITE375ns·CHECK/RUN 메모리 소유권·guard를 실제 코어에 연결한다.** 이번에 제어 체인 구조와 명시적 배치 설정을 완료했으므로 변경 없는 CDC 분석만 다시 수행하지 않는다. 남은 아날로그/외부 조건은 별도로 기록하며 전체 통과로 선언하지 않는다.

새 배치의 출발점은동결126의fit02/candidate다. [bridge QSF](../../src/nes/diagnostic/nes_bridge_sync126.qsf)의 정확한8개설정을 유지한다. QSF는`transport|bridge|ack_sync[0]`같은instance경로를 쓰며,TimeQuest의entity:instance명이나중괄호를그대로쓰지않는다. hierarchy가바뀌면명시적으로갱신하고Fitter의Ignored assignment와실제User Specified인식을검사한다. RTL/배선변경후에는새후보에서데이터372쌍과내부타이밍을재평가한다.

8MHz WRITE3를168MHz로옮기면17.856ns가되어금지한다. 실제write활성/hold/release시간을375ns기준과연결하고READ16/168MHz와독점소유권을분리한다. CHECK에서RUN으로넘길때정지·배타·오류경로를보존하고guard카운터의8MHz전제를그대로옮기지않는다. 이후실제SNES소비자·진행관측·오류종료·독립044복원을묶어최소RUN실기를우선한다. 동일119 full80/BASE/ENTRY나변경없는전체프레임은반복하지않는다.

## 최종 구현과 검증 범위

124매핑DB/47개소스입력을재사용하고bridge4체인의양단계8레지스터QSF속성만추가했다. 실제fit/STA수행,새RTL·MAP·Questa·전체코어프레임·ARM/ASM·설치패키지는없다. 최종13,568LE/933LAB/4,955regs/26M9K/PLL1/46실제핀264가상핀. 동일도메인setup NES8.845/host3.221/reader1.313ns,전체raw−7.976ns로전체타이밍은미통과. 남은30LAB는loader/guard/최종소비자를포함한여유가아니다.

제어6체인과reset해제4체인(core/reader/host/init_release)모두첫단계fanout1,두단계,60개setup/hold양수. 최소4.762/0.196ns. 로컬해제후reset4,290경로최소1.171ns. 기존init_done비동기종착점6비트/36recovery-removal과이번release4체인8비트를혼동하지않는다. bridge4체인의보고가Automatic/No에서UserSpecified/Yes로바뀌었지만MTBF는여전히NotCalculated다. 도구settling에는최종단계출력slack도포함되므로단계간setup수치와같다고하지않는다.

새배치에서도125데이터372쌍×3corner통과:주소/반환/요청/응답slack2.176/37.476/40.862/7.787ns. raw데이터예산4/40/40/10ns,SDC한수신주기5.952/45.454/45.454/11.904ns유지. 원시첫단계비동기/전체reset펄스/아날로그MTBF/외부IO조건미완료,blanket falsepath없음.

124공통reset/도메인별해제유지. RAM scrub는raw_stop만사용하고memory_ready를되먹이지않는다. reader원시reset OR우회/독립reset금지.124 fine_x4프레임의내용·상대tick일치/절대tick−4는역사적기능기준이며126postroute시뮬레이션으로확대하지않는다.

## 실패와 보존

fit01의잘못된QSF표기로8개속성이무시됐으며메타검사가거부했다. 최종fit02는정확한instance표기/무시경고즉시실패/실제보고대조를사용한다. 초기fit02검증의LE13540고정가정은실제packing13568변경으로실패했고장치한도검사로고쳤다.933LAB/4955regs유지,새빌드반복없음. 이전실패·원시로그·공식도움말을모두보존한다.

126동결2,078파일/manifest0b81e9d875b04683f59a0de3599a2770c2b86437bca51e9ce6bdc3d85550a5d0. 완료finalizer와옛archive수정금지.125조건부디지털캡처계약과124의최종evidence-final기준유지. 파일이름만으로031/044소스를혼용하지말고해시부터확인한다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

`nes_control126.py --baseline124 <frozen124-final> --baseline125 <frozen125> --out <newASCII> --quartus-bin <bin64>`는원래매핑을복사하고baseline분석/정확8QSF/fit/STA/새데이터검사를수행한다. 이후`review_nes_control126.py --out <same> --quartus-bin <bin64>`로동일클록/reset감사를새로실행한다. `verify_nes_control126.py --evidence <frozen126>`는재실행없이모든증거를대조한다. 동결DB에서도구를직접실행하지않는다.

PR71병합확인. 한국어제목과작업목표/작업내용/작업결과/작업의미4절,사용자가병합한다. GBC152/원래NES334/모든공개핀보존,ROM·바이너리·미디어·라이선스·개인경로Git제외. 이번에는새실기요청없음.
