# NES 현재 인계 —132 현재 배치 CDC·reset 검증

[132 결과](../../analysis/CDC132-RESULT.ko.md) · [검증 메타](../../analysis/cdc132-verification.json) · [131 회로 계약](../../analysis/COUNTER131-RESULT.ko.md)

## 다음 작업

131fit05와132 경로 목록을 재사용해 CHR 설정 안정 구간과 RUN/STOP/오류→core/reader reset 해제 계약을 실제 결선에서 검증한다. 비동기 reset 체인 입력107음수행은 기능 하류와 구분하고 pulse/release 조건을 확인한다. 이어 실제 외부IO·SNES 소비자·관측 가능한 최소 RUN+044 복원으로 진행한다. 변경 없는 MAP/FIT/전체쓰기/371쌍 재검증은 반복하지 않는다.

다음 검사는 `nes_live_joint.sv`의raw_stop/common_reset/init_release/core_release, `nes_spi_boot.sv`의spi_fault, `nes_rom_boot.sv`의reader_reset/run_enable, reader source_reset/memory_reset과실제rom_request를 함께 다뤄야 한다. CHR16/32K 적재 전후·START·최초요청·STOP/오류·클록정지에서 설정이 안정되기 전 소비하거나중지 후추가요청하는지 검사한다. 131의전체쓰기는 반복하지 말고 이미검증된이미지fixture와 실제결선/상태전이로 범위를 좁힌다. 필요한 수정은 원시 fault 취소·WRITE/HOLD drain을 보존해야 한다.

reset 음수107행은 모두다른release-chain 비동기 입력이다. 기능 레지스터로 가는6,168보고행최소+0.498ns와구분한다. 단순delay나blanketfalsepath로 없애지 않는다. 실제문제가 발견되기전 기존정상동기화체인을 재작성하거나 재배치하지 않는다. pulse/release/reconvergence/MTBF는 별도미완료다.

## 현재 고정 근거

- 선택131fit05,14,078LE/954LAB/5,320regs/26M9K/PLL1. 같은클록memory+0.041ns,원시crossclock−10.408ns. RTL/QSF/SDC/배치변경없음. STA캐시`taw.rdb`와해당IOsimcache만복사본에서변경됐다.
- 현재보고3,426행/677쌍: 데이터371/제어8/CHR설정183/RUN오류115. 데이터만세코너1,113검사통과,최소2.188/35.044/40.580/7.957ns. 캡처전후안정조건을가정한조건부검증이며최초RUN계약을대신하지않는다.
- actual131reader2위상1,050읽기·26취소·request_sync0조기사용거부. fixture는해시확인125보관본,bridge2RTL/프로토콜은정확히같아재사용. 전체SPI/CPU/MCU/SNES실물/아날로그증명아님.
- 제어8+reset해제8=16체인,첫fanout1,단계간96setup/hold최소4.076/.194ns. 하류reset6,492행,107음수모두10개release-chain입력끝점,전체최소−4.601ns. 실제외부IO입력83/출력227무제약이며가상포트포함. MTBF계산되지않음.
- 131비활성counter사전설정/activecounter·drain계약유지. READ16/168MHz/write22-64-22-22/guard21-672-33603. 새MAP/FIT/RTL/ARM/ASM/설치패키지/실기시험없음.

## 재현·실패 보존

`nes_cdc132_inventory.py --baseline <probes> --out <freshASCII> --quartus-bin <bin>`은고정131fit05복사와보고만수행한다. `nes_cdc132_sta.py --inventory <firstOut> --out <freshASCII> --quartus-bin <bin>`은현재분류·데이터제약·체인을확인한다. `run_nes_cdc132_protocol.ps1`은기존FLOATwrapper/Python/Questa/새ASCIIOut/Baseline을받으며1seat직렬이다. `verify_nes_cdc132.py --evidence <frozen132>`은인접125/131증거와함께검증한다. 이미통과한이번검사를변경없이반복하지않는다.

124manifest의공개핀60a577…와현재관측4e0d6d…가불일치해입력을거부했다. 원인은미확정,124수정금지/무결성재검증주장금지. 독립고정125fixture를사용했다. 132에는관측manifest·실패로그가보존돼있다. sandbox하위shell의시험전종료후허용된host에서FLOAT실행;실제라이선스오류·승인거부없음.

동결967파일 manifest`2dbee394e209ba2e40a49c737d08496c81ed4d1a9a00457ec537f3346858e214`. archive044–132/완료finalizer재작성금지. 실기설치승인·8µs·E1E2·전체MTBF가추가된것은아니다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR77 병합확인. 한국어제목과작업목표/작업내용/작업결과/작업의미4절,사용자병합. GBC152/원래NES334/과거공개핀보존. ROM·바이너리·미디어·라이선스·개인경로Git제외. 준비도6/5/1은게임완성률아님.
