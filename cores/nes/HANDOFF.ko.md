# NES 현재 인계 —137 실제 화면 경로 구현

[137 결과](../../analysis/SCREEN137-RESULT.ko.md) · [검증 메타](../../analysis/screen137-verification.json) · [A–E 계획](../../docs/development/NES-MILESTONE-AUDIT-135.ko.md)

## 현재 판정

A 패키지 전달과 B 최초CPU활동 실기는 완료했다.136 두 TXT의47기록/491600ms/81920바이트 적재·비교/오류0/CPU7002→124484→STOP132438을 확인했다. 사용자 메뉴 복귀·복원 확인, 이번 GBC플레이는 별도 미보고다. 같은136을 다시 실행하도록 요구하지 않는다.

C는 화면 구현/제한 디지털 시험까지 진전했다.137test01 실제 코어3프레임184320픽셀·SNES포트,client06 실제65816/PPU183552픽셀,client07/08잘못된 길이/헤더 차단,bus01compact ROM64KiB매핑이 통과했다. 실제 보드 화면·입력·오디오는 아직 미확인이다.

## 바로 이어 할 일

선택137fit03와 test01+counter01/bus01/client06–08을 재사용해 MCU 표시 전용 식별·SNES RESET 해제/재유지·유한 표시·STOP/base/menu/044 복원을 실기 패키지로 연결한다. 새 배치의 활성 SNES/PSRAM I/O와 CDC/reset 변경 경계만 확인하며, 같은 영상·전체 적재·MAP/FIT를 이유 없이 반복하지 않는다.

- 실제136 `nes_cf86_session094.c`의owner094는 get_snes_reset()을 요구한다. 표시 전용 상태와 reset 해제/재유지 경계를 구현하고 기존USB IRQ 차단·CSS/NMI·bit별RDY/shared fault 검사를 유지한다. 단순 조건 삭제나 전체세션 보호 우회 금지.
- 현재137의59/D4는 내부 배선 시험용이다. 화면용 단일 식별을 새 MCU와 FPGA에 맞추고136/구형86을 무조건 허용하지 않는다. 표시 중에는ROM/packet 버스만활성화하며 SD기록은 표시 전과STOP/복구 뒤로 제한한다.
- 표시 시간을 유한하게 정하고 종료 전SNES RESET을 다시 유지한다. RUN→READY STOP은flags2/count81920이다. 정상STOP/base/menu와044복원을 포함한 단일 패키지를 전달한다. 고장 뒤SD/UART복구를강행하지 않는다.
- 137fit03의 새로운 SNES 활성핀·programROM 출력 경로와PSRAM/CDC/reset 변경을 확인한다. 같은 클록통과를 전체signoff로 확대하지 않는다. source/식별 변경이 필요하면 그 변경에 따른 새 배치를 수행하며, 무변경 배치는 반복하지 않는다.
- 첫 화면실기를 얻은 뒤 패드 입력을 붙인다. 전체PC trace·장시간조합을 화면실기의 선행조건으로 만들지 않는다. 이것은C전체완료가 아니라 최소화면피드백순서다.

## 정확한 선택본

선택fit03(13592LE/924LAB/50M9K/122핀/0가상/PLL1), 같은 클록setup+.060/hold+.176ns; raw−6.600ns는별도CDC/reset미완료. test01과fit03의RTL 차이는 loaded_bytes 독립 갱신 하나뿐이다. counter01이135대비26112조합/잘못된증가대조군으로검사했다. 전체영상재시험으로표현하지 않는다. builder137의ROM/atlas는fit01/fit03/실제client가동일하다.

현재고정fine_x 진단 PRG64KiB+CHR16KiB,3프레임 검증,고정16KiB SNESatlas·239행 crop. 내부cart_nrom.sv라는 이름과 달리 기존제한MMC3진단결선이포함된다. 이를SMB3의384KiB제품지원으로확대하지 않는다. 데이터가바뀌는CHR/일반PPU/입력/오디오는별도다.

fit01 timing실패·fit02 준비assert(6개를7개로예상)·초기Mesen설정/runtime/Lua IO·startup vblank225검증기수정·초기진행parser수정은새증거에보존한다. 이전044–136을수정하지않았다. 완료finalizer재실행금지.

## 유지할 기준

136실기정상RUN과119전체적재/복구,044메뉴/GBC근거 유지. 첫게임SMB3(J) mapper4/PRG256KiB+CHR128KiB/SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. D는시작·이동·스크롤·장면전환·종료·오디오구분, E는실제실패중심맵퍼확장이다.

E1/E2·MTBF·8µs/양클록정지CE9µs반례·124격리·source-lock4건 유지. GBC152/원래NES334/기존공개핀보존. Git에는소스/도구/문서만, 바이너리·개인로그·미디어·라이선스공개금지. PR제목한국어, 작업목표/내용/결과/의미4항목, 사용자머지. PR82병합확인.
