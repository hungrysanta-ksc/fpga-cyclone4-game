# 697: MMC695 비교판과 MMC696 장시간 오류

**695는60초 실행·메뉴 복귀 정상,696은14분11.36초 실행 후 스테이지 진입 중 NES 스프라이트 ROM 읽기 마감 오류로 종료됐다.** 696도 STOP·base 복구·메뉴 복귀는 성공했다. 사용자 종료 조합 시험으로 계산하지 않는다. [분석](../analysis/hardware697-mmc695-696.json) · [원본6파일 보존](../analysis/hardware697-archive.json) · [전달 구성](../analysis/trial695-package.json)

## 프레임 비교

완료 표시 기준으로 첫·마지막5초를 제외했다.696의 첫55초 완료 카운터는 장시간 실행 뒤에도 고정 보존된다.

| 구간 | MMC690 이전 실기 | MMC695 60초 | MMC696 장시간판의 첫55초 |
|---|---:|---:|---:|
|5–40초|19.97fps /699화면|18.34fps /642화면|21.20fps /742화면|
|40–55초|19.40fps /291화면|21.67fps /325화면|20.07fps /301화면|
|5–55초 평균|19.80fps|19.34fps|20.86fps|

695 전체는60.35초·1207화면,20.00fps다.5–55초는MMC690 대비−2.32%지만 **695와690의 실행 명령은 동일**하다. 이번 초반의 표시당mapdirty는+30.77%,E1전송량+15.62%였고 후반mapdirty는−31.90%,E1전송량−19.68%였다. 동선·장면 작업량 변화가 크므로 구현 회귀나 개선으로 판정하지 않는다.695의 출력·최종ACK 평균은27.19ms(69025.56ms),수신10.42ms,계획·공급11.58ms다. 이 비용에는 IRQ·대기가 포함된다.

696 전체는851.36초·19453화면,22.85fps다. 초기5–55초는690보다+5.35%지만 같은 코드의695 결과도 크게 달라졌고,696의초기작업량bin은 이미 재사용됐다. **장시간 모드 때문에 빨라졌다고 판단하지 않는다.** 마지막epoch는840.18초부터이며287개의frame-start만 남았다. 이를처음60초나전체19453화면의workload로사용하지않는다.696 전체단계평균8.70/11.08/23.50ms 역시 다른14분장면의 평균이다.

## 696 최초 오류의 위치

| 근거 | 해석 |
|---|---|
|`run_first_error=1`, `run_rom_error=2`, `fault_context_valid=1`|ARM이 관측한 최초 NES ROM fault; RTL의PPU sample deadline 분기|
|문맥 `e200c3f7ce21fbe7`|PPU 요청 진행 중,응답 없음,ready0,PPU valid0|
|pending = demand = `0x21fbe7`|필요한 물리CHR주소를 이미 요청했으나 sample까지 응답하지 않음|
|`age=1`|요청 수락 뒤 매우 짧은 시점의 sample;255클록 backend timeout이 아님|
|PPU상태 `604198007f9f9f9c`|주사선192,dot262,sprite fetch1,rendering1,논리주소`0x1fe7`|
|`read/write $2007 pipeline=0`,prefetch0|해당 순간 CPU의$2007읽기/쓰기 겹침은 보이지 않음;현재BG hint는sprite fetch를 제외함|
|plan_error0,CRC errors0,receiver_error0|이 로그는 plan FINISH0x80·입력CRC 오류 서명과 다름|

선택694보드의 `nes_rom_service.sv`는 `ppu_sample && ppu_rom && !ppu_valid`에서고정오류2를기록한다. observer는같은첫fault edge의ROM문맥과PPU상태를보존한다. ARM`native_service165`가이를읽고SERVICE결과2로중단한다. `screen_error=169`는이구성에서유효한SPC초기화readbackA9이며새영상오류가아니다.

중단 당시다음표시serial19454/generation19830의map명령(op2/section2,offset2240,length192)이진행중이며window 미완료3개가남았다. 마지막완료표시는generation19829,850.88초다. 이map명령이나sink/window error2를최초원인으로바꾸지않는다. ROMfault관측에따른guard 중단과양립하며,정확한callback PC는로그에없다.

이번에 **처음 오류를 낸 회로와 소비시각은 확인했지만,요청이 늦은 원인은 미확정**이다. 스프라이트 주소확정/ALE·mapper물리주소갱신이늦었는지,CPU또는tile-plan의선행읽기로대기했는지,backend응답이늦었는지는직전grant/response 이력이없어구분할수없다. `rom_ready=0`은현재요청이busy여도나오므로그값만으로tile경쟁을확정하지않는다. PSRAM잘못된데이터·전기적IO위반·타일수한도초과도이로그만으로는확정되지않는다.

과거551/639/690의첫화면전5초stage0 timeout과다르고,639/642의plan FINISH0x80과도별도경로다. 장시간generation은19830으로16bit generation wrap이아니다. 고정60초제한은넘었지만무한시간·모든wrap안정성이증명된것은아니다. 마지막16개capture reject/recovery는거부시점의ROM요청이력이아니며,최종PPU원인을대체하지않는다.

## 종료·복구 판정

695는`native_result=1`인60초마감이다. 마지막에receiver23/transfer_stops1이남았지만CRC errors0·최종pending0·run_error0이다. 선택코드의입력transfer가마감guard로취소된경로와일치하며중간CRC고장으로분류하지않는다.

696은`native_result=2`인오류종료이고사용자종료8이아니다. 두실행모두STOP·base_restored·safe_to_reload1,최종MENU_PREPARED와사용자메뉴복귀관측이일치한다.696의종료조합은아직실기미검증이다.

## 다음 작업

1. 출력최적화보다이오류의재현경계를우선한다.192/262 전후257–264dot의sprite주소·ALE·mapper tag와native CPU/PPU·tile owner의request/grant/response를선택696 RTL에서같은시간축으로연결한다.
2. 캐시적중/미적중·CHR bank변경·경쟁읽기를나눠현재문맥을재현하고,최초허가가능시각부터sample까지의예산을확정한다. 장면번호는사용자추가정보가오면반영한다.
3. 독립sample마감을끄거나NES클록을임의로늘리거나timeout을완화하지않는다. 원인이확인된경계만고친뒤STOP·최종ACK·기존두위상표시와전체Lite비용을검증한다.
4. 새실기판은계속60초/장시간두종류와고유로그이름으로제공하고RESTORE를제외한다. 안정성수정후692의출력병목개선을재개한다.

이번단계는원본로그·선택소스해석이다. 새RTL수정·시뮬레이션·FIT·설치본은없다.6개원본은바이트그대로보존했고,초기분석기의「transfer_stops는항상0」가정을695의정상마감취소1회에맞춰정정했다.
