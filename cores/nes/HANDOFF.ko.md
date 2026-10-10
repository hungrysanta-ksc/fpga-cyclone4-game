# NES 현재 인계 —139 실기 최초 오류 확인, 읽기 응답 마감 수정

[139 결과](../../analysis/FAULT139-RESULT.ko.md) · [실행 안내](../../docs/nes-fault139-instructions.ko.md) · [메타](../../analysis/fault139-verification.json)

139 실기에서 CPU 주소=pending 주소0xE184,CPU pending/age3/응답0/유효0,오류1과샘플123028을 확인했다. 해당 요청 시작→reader 응답/ACK→CPU 소비 경계와 이전CPU/PPU 중재를 집중 재현한 뒤 원인 경계만 수정한다. 같은139 재시험·영상·저장/부품/전체 적재/무변경 fit은 요구하지 않는다.

[139 실기 결과](../../analysis/SCREEN139-HARDWARE-RESULT.ko.md): 전체80KiB 적재·대조,최초상태수집,STOP오류0,base/menu준비,사용자복원 성공. 표시단계 체크포인트80ms,메뉴준비528100ms. 글리치여부·메뉴복귀육안·이번GBC플레이는미확인. 화면/RUN성공으로승격하지않는다.

138은80KiB 적재/전체 비교·STOP·메뉴·사용자 복원 성공,CPU ROM deadline1로 화면 실패다. 첫/마지막/STOP 카운터123028,실기 화면 직전522580ms/메뉴536040ms. [138 실기 결과](../../analysis/SCREEN138-HARDWARE-RESULT.ko.md)를 유지한다. 21.48MHz/위상3.5ns 이상모델100ms에서는 미재현했다.139는 원인 수집판이며 화면 오류 수정 완료가 아니다.

## 실기 후속

두139 TXT를 확보했고 복원 성공을 확인했다. 같은139 시험과 추가 영상은 필요 없다. 다음은 위 최초 실패 경계의 재현·수정이며 새 실기 후보를 준비할 때 실행 안내를 제공한다.139 제작/실행 안내는 당시 패키지의 고정 기록으로 유지한다.

## 선택본과 재사용

fit02/arm03/armcheck03/host05/rtl01/inventory01/sta01/io01/asm01/release01. fit01준비파일명오류와host02/arm01 CRC치환실패는제외. arm02/host04뒤보고서초기화추가로arm03/host05확정. source/ROM reader/control 타이밍은유지하며관측배선+식별만변경.137전체픽셀·SNES소비자검증재사용;이번46검사는동일에지와STOP후보존/후속사건보존경계다. testscript print의5A/D5만5B/D6로교정했으며실제RTL/검사는처음부터5B/D6였다.

## 로그 해석/다음 수정

`run_first_error`는RUN실패,`run_stop_error`는종료관측실패다. 기존run_error는최초RUN오류우선. fault_context_valid1일때 hi/lo를결합하며 bit63=0,62busy/61pending_ppu/60ready/59response/58cpu_sample/57ppu_sample/56cpu_valid/55ppu_valid,54:47age,46:25pending주소,24:0CPU주소다. 주소는PC가아닌매핑주소,age는NES클록. `tools/read_nes_fault139.py <report>`사용. 같은클록의최초fault발생에지에캡처하며STOP후에도남는다. 오류없이기존70만조회하고71/72는오류후조회한다. RUN중SD기록은금지. 공유SPI/RDY고장은종료후SD를강행하지않는다.

같은클록+.108/+.179ns,363heldpairs/17chains조건부통과. config240쌍은CHR승인값이RUN전고정되는계약이며새observer fanout포함. raw−8.454ns/MTBF/실제PCB지연/전기조건미승인. I/O+2.478ns는PCB2ns가정이다. 이미완료된부품/저장/모형/배치를반복하지말고새실기결과로다음수정선택.

첫게임목표SMB3(J),mapper4/PRG256KiB+CHR128KiB,SHA dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49. 입력·오디오·실제게임은미완료. GBC152/원래NES334·044·136·E1/E2·8µs/양클록정지CE9µs·124격리·source-lock4유지. 동결044–139/완료finalizer수정금지. PR한국어4절,사용자머지.
