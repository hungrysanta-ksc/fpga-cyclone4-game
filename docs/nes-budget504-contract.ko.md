# NES504 — 전송·표시 비용과 다음 교체 경계

[측정·계산 JSON](../analysis/budget504-verification.json) · [다음 실행 순서](nes-budget504-plan.json) · [실기502](nes-hardware503-results.ko.md).

PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`와 head `afbd8874b32669cd411bbcb5e80e49a3efd9f0c6`의 origin/master 도달 및 tree 일치를 확인했다. 새 브랜치는 `codex/nes-bandwidth-dma-budget-504`다. 실기 선택은502/10.59fps를 유지한다. 이번 결과는 A2의 비용 분해·후보 축소이며 전체60Hz 예산 통과나 새 제품 구현은 아니다.

## 1. 같은 실기 경계의 바이트 예산

실기636개 최종 표시로 driver 총량을 나눈 값이다. 마지막 미완료 시도와70/73도 포함한다. SPI는현재2.625MHz이며 한16.667ms에5468.75B, 초기12ms wire 예산은3937.5B다.12ms는설계예약이지실측상한이아니다.

| 항목 | B/표시 | wire ms/표시 | 포함 범위 |
|---|---:|---:|---|
| 전체 driver | 9840.85 | 29.99 | 실제 기록된 모든 op |
| D0/E0/E8 조회 | 3929.34 | 11.98 | 단계 내부, 별도 가산 금지 |
| 조회 제외 | 5911.51 | 18.02 | framing/CRC/ACK/70/73 포함 |
| D1/E1/E9 본문 | 5195.94 | 15.84 | 기존헤더 제외,압축된본문 |

조회가 모두 공짜여도 한주기보다 **442.76B** 많고,12ms 예산까지는 **1974.01B**를 더 줄여야 한다. 실제조회도0이될수없다. 이것은다른ABI/중첩/평균대상까지불가능하다는증명이아니라현재전송구조의예산이다.

driver DWT−wire는13.79ms지만 여기에는설정뿐아니라guard·poll·IRQ가포함된다. 모든호출의4×2µs를제거한다고가정한단순할당도2.245ms다.70/73의byte경로까지공통소유권을만들어야하며SS경계·완료/CRC/STOP검사를삭제해서는안된다. 지속SPI설정단독으로60Hz를목표로하지않는다.

## 2. 실제65816에서 새로 분리한 구간

기존client의PC 경계에관찰callback만추가했다. 프로그램·요청·시작시각을그대로두고 **픽셀과모든최종ACK masterclock이원본과같음**을검증했다. 새Questa/FIT/firmware는없다.

| 기존fixture | SEAL진입→upload진입 | upload진입→최종ACK | upload중wait169호출 |
|---|---:|---:|---:|
| 실제502 source의cold1개 | 2.17ms | 57.68ms | 4 |
| 과거496의연속12개 평균 | 2.24ms | 23.65ms | 각1~3 |

후자는기존493/502와동일한65816으로실행한과거입력이며 **502실기의warm시간이아니다**. actual ARM/IRQ/ROM이같은시계로실행되지않는file-aperture 모델이다. upload구간에는DMA·wait·palette/OAM·최종표시가함께있으며순수대기시간으로쓰지않는다. SEAL검사시간2.24ms만없애서해결될구조가아니다.

현재수신은이미tile bulk와ordinary를WRAM에모은다. `nes_dirty212.emit_upload`는SEAL뒤에list cursor를0으로초기화하고,4192byte-equivalent budget과descriptor당96을차감하며여러VBlank에걸쳐VRAM을갱신한다. 마지막CGRAM512B/OAM544B·register/HDMA/표시선택은최종단계다.

실기tile plan출력은평균182.14B/표시,dirty map행은12.69개/표시(64B행)다. **tile만일찍보내는것으로40.27ms의실기SEAL전체를회수한다고계산하지않는다.** tile·map dirty list와나머지최종비용을함께다뤄야한다.

## 3. 비교한 구조

| 후보 | 근거/비용 | 판단 |
|---|---|---|
| RUN공통SPI설정 | 호출마다GPIO/CR1/DMA저장·복구;고정wait할당2.245ms,나머지는분리미측정 | 보조후보;단독60Hz해법아님 |
| 전체이전입력exact delta | canonical5741B+raw최대1792B=7533B. bit만으로도M9K최소7개,1024×8이면8개 | 현재남은5개에추가불가.메모리회수없이는기각;CRC일치만으로동일판정금지 |
| packet공통generation | 한actual502 cold의332record를공통header로재부호화 | 아래byte시험통과;게임평균절감/실제RTL면적미확인 |
| 확정된dirty-prefix의비활성VRAM선행DMA | 기존WRAM/list/CRC/coverage를유지하고upload의늦은실행순서대체 | **다음실행검증경계**.단독으로입력wire문제까지해결했다고주장하지않음 |

packet공통generation은순수Python ABI 시제품이다. packet마다4B(version/count/generation),record마다kind/index2B+기존값으로표현하고terminal COMMIT은별도packet을유지했다. 원본record byte열로정확히복원됐고version/generation/count/truncate/trailer 반례5개를거부했다. 기존17packet/3982payloadB→15packet/3378payloadB. packet당D0한번/D1CRC/D2를동일하게할당한wire는4305→3663B, **계산상1.957ms** 차이다. 실제ARM·CRC·queue·전체시간/면적성과가아니며이cold값을실기평균1974B목표에대입하지않는다. kind/index·generation검사는공통문맥에서유지하고상태코드/왕복만의미세변경으로축소하지않는다.

## 4. 다음교체의구체경계

먼저SNES의기존dirty-list 실행기를교체해데이터생산과VRAM전송의직렬화를검증한다. source502·ARM502·SPI/queue/plan ABI는유지한다. 새범용FPGA실행기를추가하지않는다.

- **삭제/이동:** upload진입때의cursor0초기화를BEGIN으로이동;완료한prefix를SEAL때다시DMA하는경로제거;기존transfer본체를공통한번만사용. 기존list/coverage/bank주소를재사용한다.
- **안정된소유권:** `append212`는마지막entry를4096B까지합칠수있다. 열린tail은읽지않고이전불변prefix만대상으로한다. `mark212`는payloadcopy보다먼저list를만들수있으므로전역service안에서무조건DMA하지않는다. packet완료뒤/main-poll에서만실행하며실제수신완료watermark를검증한다.
- **비차단VBlank:** 단순히wait169를앞으로이동하면queue소비를막는다. 현재VBlank에남은실제시간으로한descriptor가들어갈때만DMA하고부족하면바로수신으로돌아간다. VBlank중간진입을전체4192예산으로취급하지않는다. 경계/refresh/HDMA/IRQ/service·DMA setup을실제65816시각으로검증한다.
- **검사/표시:** copy·범위검사/전송CRC/중복범위거부를유지한다. 선행VRAM은미공개상태이며최종manifest·coverage·CRC·semantic검사가끝나기전표시/최종ACK금지. CGRAM/OAM/HDMA/global bank선택은최종검증된VBlank에남긴다.
- **STOP/재사용:** 변경전inactive bank의이력인증을무효화하고실패·취소뒤부분VRAM을정상base로재사용하지않는다. 이전active화면과identity를유지하고다음cold/reuse를구분한다. ACK의의미를staging수신완료로바꾸지않는다.

설계할당은SNES body **추가512B이내**(현재4311/4960B,649B여유),새WRAM **8B이내**,추가frame buffer/M9K **0**,ARM새실행코드 **0**,새FPGA제어 **0**이다. 실제달성수치가아니며최종ROM내용변경의wholeLite관련timing/배선은후속gate에서확인한다. 이예산에서공통화가안되면기존업로드코드대체범위를넓히고먼저재검토한다.

## 5. 순서와중지조건

1. 한cold+warm/연속입력에서불변prefix·열린tail·packet완료·부분VBlank·STOP/재사용을실제65816으로연결한다. 기존RGB와최종ACK·활성bank보존,수신대기/새setup비용을확인한다.
2. ARM·공유SPI/IRQ/ROM을연결한전체일정에서처리시간을비교한다. VBlank대기위치만옮겨합계가줄지않으면기각한다. 독립검사를앞당겨생략하지않는다.
3. 입력common-context/선택영역exact delta의실제원본분포와삭제면적을검토해남은wire예산을닫는다. 전체history가안맞는다는이유로hash-only검사를택하지않는다.
4. 유의미한후보만Quartus Lite전체1회와새고유파일명실기로진행한다. RESTORE폴더는제외한다. 현재502설치본은교체하지않는다.

**A2의전체60Hz gate는아직미통과**다. 입력본문·최종VBlank·actual ARM/IRQ/ROM·새 제어비용이모두예산에들어간것으로표시하지않는다. 이번에확정한것은삭제대상·소유권·검증순서와기각한후보다.

재현은 [측정기](../tools/measure_nes_budget504.py),[분석기](../tools/analyze_nes_budget504.py)를사용한다. `probes/nes-budget504/evidence`에cold01/sequence01의raw CSV·Lua·로그·입력hash를보존한다. 실패한제품시험은없으며Temp전체탐색은불필요해중단했다. 상용ROM/사용자save/라이선스는새파일에포함하지않는다.
