# NES 현재 인계 —125 묶음 데이터 검증, 다음은 제어 동기화와 통합

[125 결과](../../analysis/CDC125-RESULT.ko.md) · [검증 메타](../../analysis/cdc125-verification.json) · [124 배선·배치 기준](../../analysis/RESET124-RESULT.ko.md)

## 바로 이어서 할 일

**같은124 배치의 첫 동기화 단계6쌍을 실제 체인/fanout/단계 간 slack과 연결해 확인한다.** reader request/ack,bridge request/ack,두 방향 peer-up이 대상이다. 첫 단계 출력의 다른 소비 여부,동기화 속성의 실제 합성 결과,다음 단계까지의 settling 시간을 확인한다. reset→release6비트와 로컬 해제 경계를 포함하며,MTBF에 필요한 물리 전제와 디지털 기능 검사를 구분한다. 숫자 근거 없는 MTBF나 모든 클록 false-path 면제는 금지한다. 회로 변경 없으면124 DB 사본을 쓰며 재합성부터 하지 않는다.

그다음 로더 WRITE375ns·guard·독점 소유권·전체 자원·실제 SNES 소비자를 통합한다.8MHz WRITE3를168MHz로 그대로 옮기면17.856ns이므로 금지한다. 진행 관측·오류 종료·독립044복원이 가능한 최소 RUN을 준비하면 실기 데이터를 우선한다. 변경 없는119 full80/BASE/ENTRY,124 전체프레임·fit,125 데이터 시험 반복은 피한다.

## 이번에 완료한 범위

같은124 fit01의 교차setup1,218행/378쌍 중 데이터372쌍만 제약했다. 주소22/반환257/bridge요청46/응답47쌍. 주소 레지스터는 합성 후service pending_address이며 반환 데이터에는 CPU/PPU/APU/DMA 직접 소비가 포함된다. 데이터 예산4/40/40/10ns와 SDC한수신주기5.952/45.454/45.454/11.904ns는 다른 검사다. 최소 slack1.777/36.975/40.859/7.955ns. 두 동기화 단계 뒤 캡처라는 디지털 조건에서 최소2주기를 확보하고 새 데이터 덮어쓰기까지의1주기유지도 검사했다. 아날로그 metastability/모든 위상/전체 타이밍은 증명하지 않았다.

protocol01은 정확한124 reader/bridge/queue RTL이다. reader두위상1,050읽기26취소,bridge세위상각13검사/6,426응답,한단계빠른캡처부정대조2개통과. 새 productionRTL/코어프레임/fit/ARM/ASM/SD패키지는 없다. raw−8.477ns·제어6쌍·비동기reset회복·외부IO는 남는다.124의13,540LE/933LAB/26M9K/PLL1/46실제핀264가상핀과 도메인 내부setup10.263/2.610/0.816ns를 재사용한다. 남은30LAB는 최종 여유가 아니다.

124 공통reset/도메인별동기해제 유지: RAM scrub는 raw_stop만 사용하고 memory_ready 조건을 되먹이지 않는다. reader 원시reset OR우회나 독립reset을 추가하지 않는다.124 fine_x4프레임의 내용/상대tick일치·절대tick−4는 역사적 기준이다.

## 실패와 증거 보존

sta02의 SDC4ns는 clock skew까지 포함되어−0.175ns였다. sta03은 raw데이터4ns를 유지하고 수신주기에서 SDC값을 유도했다. 같은 원시inventory와 첫 실패 모두 보존한다. TimeQuest가 바꾼 DB는live.taw.rdb 하나이며 실제배치/incremental DB는124해시와 같다. 초기동결전검사의이파일동일성오류도기록했다. protocol01의원래드라이버/모니터는바이트일치하며,당시STA02에서가져온sha/put은최종함수와AST일치한다.

125 동결910파일/manifest36a3effc9f2ce72ca3bd660724b9bc9392f0f9d0fe52aa0c95f54e6171c3039c. 완료finalizer 재실행·이전archive변경 금지.124의최종기준은evidence-final이며 initial715파일과transport01/02/03실패도불변이다. 이름만보고이전031/044시험소스를혼용하지말고먼저배치입력해시를검사한다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

`nes_cdc125_sta.py --evidence124 <frozen124-final> --out <newASCII> --quartus-bin <bin64>`는동결DB를복사해STA만수행한다. `run_nes_cdc125_protocol.ps1`의Baseline은같은124-final이며기존1seat FLOATwrapper로실행한다. `verify_nes_cdc125.py --evidence <frozen125>`는시험재실행없이검증한다. 원본동결DB에서Quartus를직접실행하지않는다.

PR70병합확인. 한국어제목과작업목표/작업내용/작업결과/작업의미4절,사용자가병합한다. 제품GBC152/원래NES334/모든공개핀보존. ROM·바이너리·미디어·라이선스·개인경로Git제외. 이번에는새실기요청없음.
