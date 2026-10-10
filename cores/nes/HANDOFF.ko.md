# NES 현재 인계 —140 응답 경계 수정 실기 대기

[140 결과](../../analysis/RESPONSE140-RESULT.ko.md) · [실행 안내](../../docs/nes-response140-instructions.ko.md) · [메타](../../analysis/response140-verification.json)

140 실기의 두 TXT와 화면·메뉴 복귀·044 메뉴/GBC 복원 결과를 받는다. RUN통과와 화면정상은 구분한다. 재실패하면 최초context/샘플수를139와 대조하며 무변경 fit/적재/부품/저장 시험은 반복하지 않는다. 정상화면 뒤 패드·SMB3 mapper4/384KiB·오디오로 간다.

## 원인 근거와 실제 변경

139 실기는0xE184 CPU pending/age3/응답0/오류1,샘플123028에서 실패했다. 같은139 실제 코어의 무지연 모델은 이 경계에서age4/응답1로 통과했다. 요청5ns/ACK8ns 디지털 지연을 적용하면 최초context까지 실기와 같아진다.140은 ACK를 데이터 sample 다음 HOLD(핀 해제) 에지에서 발행하며 기존 RELEASE까지의 한 메모리 클록 대기를 없앴다. PSRAM READ16/168MHz95.232ns·post-sampleHOLD·CHECK·주소/데이터레지스터·2단동기화는 그대로다. 측정된 물리 원인 확정이나 metastability 해결을 주장하지 않는다.

## 선택본과 재사용

fit01/arm01/armcheck01/host01/reader01/sta01/io01/asm01/release01. unit03은12위상 중 기존10실패/수정0실패. full01은139식별자의 실제코어에서EARLY_ACK를0/1로 바꾼 비교;후자는생산140 reader와주석/공백·시험지연을제거해동일함을검증한다. loader5C/observerD7는상수변경이며MCU호스트20/ARM으로확인한다. 단일위상67.161ms/198527샘플통과,61440픽셀한프레임은trace01무지연139와완전일치. 전체픽셀/소비자는137근거재사용. reader01은16위상8400읽기208취소와CDC/setuphold/110ns/noHOLD반례검사다. unit01예약어컴파일실패와unit02ACTIVE-ACK실험은채택하지않았다. 최종은HOLD-ACK다.

## 실기 요청과 판정

`NES140-SCREEN-and-RESTORE044.zip`의01-SCREEN140-SD-ROOT 내용을SD최상위복사,0바이트 `NES SCREEN 140.nh1`한번실행. 적재·대조약9분,정상표시약10초,전체10분관찰기준. 두TXT `nes-progress-140.txt`, `nes-screen-last-140.txt`,화면/메뉴복귀/044메뉴GBC를받는다. 화면보이면사진한장/짧은영상유용하지만필수아님. RUN중SD금지/RESET재유지→STOP→base/menu→저장/044유지.139처럼최초오류와STOP오류를구분하고오류시조기복귀한다. run_passed는영상자동판정이아니다.

## 물리 여유와 보류

13640LE/932LAB/5184reg/50M9K/PLL1/122핀. 같은클록setup+.199/hold+.179ns,363heldpairs/17chains 통과. GPIO/PSRAM 조건부읽기여유+.430ns(PCB왕복2ns/setup등2ns가정)는139+2.478ns보다작다. 보드지연·MTBF·raw교차/reset전부승인아님. 현재ACK/REQ첫단계data-skew최대4.385/3.896ns가8/5ns모델범위안임을확인했지만모든아날로그실패보증아님. E1/E2·8µs/양클록정지CE9µs·124격리·source-lock4유지.

첫게임SMB3(J),mapper4/PRG256KiB+CHR128KiB,SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 입력·오디오·실제게임미완료. GBC152/원래NES334와동결044–140자료보존;완료finalizer재실행금지. PR한국어4절,사용자머지.
