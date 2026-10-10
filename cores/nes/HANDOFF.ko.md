# NES 현재 인계 —140 실기 재실패와 메뉴 복귀 실패

[140 결과](../../analysis/RESPONSE140-RESULT.ko.md) · [실행 안내](../../docs/nes-response140-instructions.ko.md) · [메타](../../analysis/response140-verification.json)

**140 실기 확인 완료: 적재·대조·TXT는 성공했지만 NES 실행과 메뉴 복귀는 실패했다.** [실기 결과](../../analysis/SCREEN140-HARDWARE-RESULT.ko.md)와 [관측 메타](../../analysis/screen140-hardware-observation.json)를 현재 판정으로 우선한다.

140 실기의 동일 CPU ROM 마감 실패와 검은 화면/메뉴 복귀 실패를 해결한다. 메뉴 준비 이후 reset·CIC·SRAM·보호 상태와0xE184 요청/응답 경계의 모델 차이를 좁혀 확인한 수정 후보로 간다. 동일140 재시험·추가 영상·무변경 fit/부품/저장 시험·동일044 반복 복원은 생략한다. 정상 화면 뒤 패드·SMB3 mapper4/384KiB·오디오로 진행한다.

## 원인 근거와 실제 변경

139 실기는0xE184 CPU pending/age3/응답0/오류1,샘플123028에서 실패했다. 같은139 실제 코어의 무지연 모델은 이 경계에서age4/응답1로 통과했다. 요청5ns/ACK8ns 디지털 지연을 적용하면 최초context까지 실기와 같아진다.140은 ACK를 데이터 sample 다음 HOLD(핀 해제) 에지에서 발행하며 기존 RELEASE까지의 한 메모리 클록 대기를 없앴다. PSRAM READ16/168MHz95.232ns·post-sampleHOLD·CHECK·주소/데이터레지스터·2단동기화는 그대로다. 측정된 물리 원인 확정이나 metastability 해결을 주장하지 않는다.

## 선택본과 재사용

fit01/arm01/armcheck01/host01/reader01/sta01/io01/asm01/release01. unit03은12위상 중 기존10실패/수정0실패. full01은139식별자의 실제코어에서EARLY_ACK를0/1로 바꾼 비교;후자는생산140 reader와주석/공백·시험지연을제거해동일함을검증한다. loader5C/observerD7는상수변경이며MCU호스트20/ARM으로확인한다. 단일위상67.161ms/198527샘플통과,61440픽셀한프레임은trace01무지연139와완전일치. 전체픽셀/소비자는137근거재사용. reader01은16위상8400읽기208취소와CDC/setuphold/110ns/noHOLD반례검사다. unit01예약어컴파일실패와unit02ACTIVE-ACK실험은채택하지않았다. 최종은HOLD-ACK다.

## 실기 결과와 다음 작업 경계

strict5C/D7 확인, 적재·대조81920바이트/47기록 정상. 최초context440181c30800e184, 유효샘플123028, CPU/pending0xE184·age3·응답0·오류1이139와 같다. STOP오류0, 기본FPGA 복원과 메뉴 준비는 완료했지만 사용자 관찰은 검은 화면 지속/리셋 복귀 실패/전원 재인가 메뉴 성공이다. 140 지연 모델 PASS를 실기 원인 해결로 승격하지 않는다.

DISPLAY_NEXT524870ms→STOPPED524940ms, MENU_PREPARED528110ms.70ms는 MCU 처리 포함 간격이다. main.c는 준비 로그 뒤 reset 해제/CIC/SRAM 검사/메뉴 처리를 한다. released 보고는 persist=false(UART만)이므로 최종 TXT만으로 reset 미해제나 MCU 정지 위치를 단정할 수 없다. 다음 후보는 이 복귀 경계를 좁혀 확인하며 기존 RUN 중 SD 금지/오류 시 reset 유지 원칙을 보존한다. 별도 디버그 체계 완성보다 정상 화면/메뉴 실기 후보 전달을 우선한다.

## 044 반복 시험 생략 — 사용자 정책

사용자 지시: 동일044 복원본의 매회 재설치·메뉴/GBC 반복 시험은 생략한다. 후보 자체 STOP/base/menu 복귀는 별도 기록한다. 복원본/경로 변경이나 구체적 회귀 근거가 생길 때만 재확인 이유와 범위를 명시한다. 과거 동결 실행 안내보다 현재 정책을 우선하며 미시험을 PASS로 기록하지 않는다.

동일140 재시험이나 추가 영상은 필요 없다. 이번 결과 반영에서 새 펌웨어/패키지는 만들지 않았으며140 제작 증거·패키지·고정 실행 안내는 역사 자료로 보존한다. 첫 게임 목표와 미완료 기능은 아래와 같다.

## 물리 여유와 보류

13640LE/932LAB/5184reg/50M9K/PLL1/122핀. 같은클록setup+.199/hold+.179ns,363heldpairs/17chains 통과. GPIO/PSRAM 조건부읽기여유+.430ns(PCB왕복2ns/setup등2ns가정)는139+2.478ns보다작다. 보드지연·MTBF·raw교차/reset전부승인아님. 현재ACK/REQ첫단계data-skew최대4.385/3.896ns가8/5ns모델범위안임을확인했지만모든아날로그실패보증아님. E1/E2·8µs/양클록정지CE9µs·124격리·source-lock4유지.

첫게임SMB3(J),mapper4/PRG256KiB+CHR128KiB,SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 입력·오디오·실제게임미완료. GBC152/원래NES334와동결044–140자료보존;완료finalizer재실행금지. PR한국어4절,사용자머지.
