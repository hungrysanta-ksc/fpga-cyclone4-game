# NES088: 실제 MCU GPIO 클록 reader와 CF87 응답 검증

## 작업 목표

CF87의원시snapshot을실제MCUGPIO코드로읽고,클록부재·진행정지와전송/타이머/소유권오류를구분한다. 같은C가소비한응답을실제RTL핀출력과대조한다. PR38 병합/master `72ed581bd6c333b1cd8c37ce776b2bb847dd9895` 도달을확인했다.

## 작업 내용

088은 CF87을 읽는 실제 MCU GPIO reader다. 1966호스트 검사·C보호제거3개와 기준클록 있음/없음의 실제C파형→RTL 응답146912bit·RTL대조1개를 통과했다. 같은 C로 STM32F401 ARM 오브젝트를 컴파일했다. 전체 main/구성/mini/TXT session·링크된 펌웨어·ASM/실기 패키지는 아직 미완료다. CF87 RTL/fit과CF86·084 실기 성공은 보존한다.

중복C0의고정데이터일치,새sequence2개,초기window제외,형식/회귀검사와450tick/512query예산을구현했다. RESET/USB/DONE/SDoffload/sharedfault는bit/delay경계에서검사한다. 정상관측시GPIO/SPI를복원하고,공유fault뒤에는CS해제/SCKLOW와SPI차단을유지한다. ABSENT/UNSTABLE/NO_PROGRESS는저장가능한관측결과이고,IO/PROTOCOL오류는후속SD/SRAM/구성IO를금지한다.

## 작업 결과

**reader와실제C↔RTL통신검증목표는달성했다. TXT/화면까지의단일수집펌웨어는아직완성하지않았다.** 1966검사에는tickwrap/freeze,byte손상120개,delay330위치·공유check1500위치오류,RESET/DONE/USB/SD/busy/reentry가포함된다. 중복비교·deadline·RESET검사제거대조3개는의도한실패를검출한다.

기준20MHz와기준없음각각541frame/73456소비bit/295453event를3.005436초동안실제CF87핀에서대조했다. 합146912bit일치. 잘못된분주RTL은응답비트불일치로실패했다. 타이밍은모형delay이며실제MCUinstruction/IRQ/전압/PCB측정이아니다. ARM21912byte는Cortex-M4오브젝트이며firmware.stm이아니다. 새RTL·fit·ASM은없고,생산CF87소스2개와087 fit경계를보존한다.

초기MinGW printf64호환빌드오류,불안정모형의잘못된valid0/gap1기대자료실패를보존했다. host04통과후host05에같은구간의payload손상검사를추가했으며정상trace해시는동일하다. 정상wave는host04trace이며최종host05와동일성을검증한다. [계약](../docs/nes-clock-reader088-contract.ko.md)에검증경계와재현을기록했다.

다음은고정CF87 fit의ASM/압축구성sink와088reader→RAM→084mini/SD/TXT/화면의ONEsession이다. reader정상경로만공유검사389972회를쓴다. 기존60초/100만IO예산에구성·복귀를그대로합치면초과할수있으므로실제payload/호출수계측과명시적boundedphase설계가필요하다. fault초기화나retry별예산리셋으로회피하지않는다. 그뒤최종ARM링크/callsite·SPI/전환/RESET·동일쌍/044복원을확인해report-only실기패키지를준비한다. CF86메모리/공통고장·전체코어는별도다.

동결 `probes/nes-clock-reader088/evidence/` 416파일,manifest `a4f589d7c30af2b5d76057c85778097a7a8154a793dfb4009d716fc84e0d4b94`. [메타데이터](clock-reader088-verification.json)/verifier088 사용. 완료finalizer/044–087archive수정금지. 준비도4완료/7부분/1미완료,installable=false. 성공한084 저장·정상044복원/menu/GBC와기존GBC/NES보호소스는유지한다.
