# NES 현재 인계 —124 도메인별 reset 구현, 다음은 묶음 데이터 CDC

[124 결과](../../analysis/RESET124-RESULT.ko.md) · [검증 메타](../../analysis/reset124-verification.json) · [123 물리 기준](../../analysis/CLOCK123-RESULT.ko.md)

## 바로 이어서 할 일

**같은124 fit01의 reader/영상 bridge CDC를 분석하고 실제 안정 유지 시간에 맞는 제한을 검증한다.** reader address_hold→PSRAM주소, data_hold→서비스/CPU 직접 소비 경로,request/ack 첫 동기화 단계,bridge req/reply 및 peer-up 신호를 구분한다. 단순 handshake 존재나 음수 raw slack만으로 통과/불가능을 선언하지 않는다. 실제 수신 캡처 시점과 종착점까지의 최대 지연,새 요청이 데이터를 덮어쓰는 시점을 함께 확인한다. 전체 클록 false-path는 금지한다. RTL 변화 없이 분석·제약 검사를 할 때124 DB 사본을 재사용하고 재합성/전체 프레임 반복부터 하지 않는다.

`init_done`의 비동기 reset 종착점은 합성 후 core_release/host_release/memory_reset의 각2비트,총6개다. 1,272경로 중36 recovery/removal과1,236 로컬 setup/hold를 보존했다. 원시 reset→release 레지스터의 비동기 회복 검사는 아직 면제하지 않았다. reset helper의 clock-stop/짧은 펄스 시험은 디지털 기능이고 실물 최소 펄스/MTBF/PLL 공통 고장 검증이 아니다.

## 구현과 검증 기준

`nes_reset124.py`는 옛 소스를 수정하지 않고 정확한 문자열 일치 후 새 작업 폴더의 RTL만 바꾼다. init_release는 raw_stop만 사용해 RAM scrub를 시작한다. core_release의 common_reset은 raw_stop 또는 memory_ready 미완료다. reader/transport는 common_reset을 받아 각 도메인에서 해제한다. RAM init에 common_reset을 되먹이면 교착이므로 금지한다. reader의 raw reset OR 우회를 되살리지 않는다. bridge/host 단계의 동기 해제를 유지하며 독립 reset은 지원하지 않는다.

fit01:13,540LE,933/963LAB,26M9K,PLL1,46실제핀/264가상핀. 코어 STA22MHz,PLL84/168MHz;동일도메인setup10.263/2.610/0.816ns. 같은클록 setup/hold/recovery/removal은 모두양수,전체 raw−8.477ns로미통과.30LAB는최종여유아님. 로더/CHECK·guard·실제SNES프로그램 제외.

unit01:16위상8,400읽기/208취소,110ns·no-HOLD 거부. transport04:reset14검사,bridge3조합×13,frontend13,raw-bypass 거부. core01:변경된 같은RTL fine_x/3.5ns4프레임245,760픽셀/65,552이벤트/8,032바이트 일치,상대시각동일/절대tick−4. 기존122의다른입력·위상은역사적기준이며124모든위상시험으로확대하지않는다. core로그numeric40경고보존;publicdriver는실행뒤두개메타문구만수정했고검증기가정확히대조한다.

그다음 로더 WRITE375ns와 guard 감시시간·소유권을 보존해통합한다.8MHz WRITE3를168MHz에그대로옮기면17.856ns라금지한다. 실제SNES소비자/DMA/표시기한,새RUN진행관측·오류종료·독립044복원준비후실기를우선한다. 같은119 full80/BASE/ENTRY,변경없는124프레임·fit을반복하지않는다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 이번 시험 도구 보정 이력

처음 transport01은 원래 공개031 frontend라 배치의044와달랐고 최종해시검증이거부했다. transport02/03은정확한044에서구031시험의5클록응답/overread8기대가실패했다. 최종transport04는044두샘플확인에맞는6클록/복합오류9로고치고120ns기한과다른검사를유지했다. 수정전고정044원본도동일13항목PASS,최종6RTL은fit와바이트일치한다. 최초`evidence`715파일은수정하지않았고현재는`evidence-final`을검증한다. 앞으로같은파일명만으로시험소스를선택하지말고실제배치입력해시부터대조한다.

## 재현과 보존

`nes_reset124_fit.py --baseline <pinned059fit> --out <newASCII> --quartus-bin <bin64>`과같은폴더의`nes_reset124_audit.tcl`로배치/경로를재현한다. unit/core/transport의`run_nes_reset124_*.ps1`은기존1seat FLOAT wrapper를직렬로사용한다. core baseline은고정052입력이다. `verify_nes_reset124.py --evidence <frozen124>`는재실행없이검증하며기준비교용임시폴더만쓴다. 동결DB에서직접타이밍도구를실행하지않는다.

044–113/116/118/120–124 증거와완료finalizer는불변이다. 제품GBC152·원래NES334·모든공개핀보존,ROM/바이너리/라이선스/개인경로Git제외. PR69병합확인. 한국어제목과작업목표/작업내용/작업결과/작업의미4절,사용자가병합한다. 새SD패키지나실기시험요청없음.
