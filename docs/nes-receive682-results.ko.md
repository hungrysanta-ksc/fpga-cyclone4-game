# 682: 최종 ACK 대기와 다음 입력의 실제 진행

실기 선택본은 **MMC666**이다. 이번 변경은681 map 우선·첫 zero 인계를 고정하고 ARM `wait634`의 수신 예산과 출력 credit 대기를 교체한다. 시작7288416/7467100, 입력·map·OBJ·ROM 달력·65816 프로그램은 동일하게 대조한다. 새 실기 FPS가 아니다.

## 확인한 원인과 교체

678은 빈 STATUS가7블록 예산을 소비하지 않도록 map 뒤 reason4를 고쳤지만, 최종 표시 ACK를 기다리는 reason2에는 **poll 호출 전에 예산을 감소시키는 중복 경로**가 남았다. 원본681의 실제 링크 코드에 빈 D0를 주면7→6이 재현된다. 두 경로를 통합하고 D1 CRC·복원과 D2/D0 반환 확인이 모두 성공해 token이 전진한 경우에만 차감한다. 빈 D0와 실패·부분 전송에는 차감하지 않는다.

또한 reason2는 출력 retired가 그대로이면 입력 한 블록을 실제로 처리했어도 `nes_cost474_pause`에서128µs를 더 쉰다. 실제 입력 token 전진을 이미 있는 progress에 반영해 이 대기만 생략한다. 입력이 비어 있으면 원래 대기를 유지한다. 매 블록 사이 E0의 credit·전체 ACK identity 확인과 STOP guard를 그대로 실행하며, 입력 수신 성공을 이전 화면의 표시 ACK나 다음 COMMIT으로 쓰지 않는다.

FINISH credit 후보는 기존 `plan.finished`를 사용한다. 실제 FINISH 확인 뒤에만, 출력 큐 credit/소비를 기다리면서 출력 진행이 없는 reason0/1에서도 같은7블록 입력 예산을 사용할 수 있다. plan 미완료·출력 진행 시에는 입력을 끼워 넣지 않는다. 새 상태·타이머·프레임 번호·위상별 지연을 추가하지 않는다. receiver를 IDLE로 넘기는 것은 기존 consumed 경계이며 최종 ACK·EA retire 전 새 COMMIT 금지는 유지한다.

최종 7블록 경로를 분해하니 첫 D1→일곱 번째 D0는681의6.200ms에서progress/credit의5.019/5.020ms로 줄었다. 그래도 여섯 블록 사이 E0 전송0.654335ms와 호출/검사/IRQ 등 잔여 약0.505–0.508ms가 남았다. credit 후보의 일곱 번째 D0는955 ACK보다0.305654/0.670210ms 늦으며 D0 뒤 검사도 더 필요하다. 128µs만 더 줄이거나 입력 블록의 독립 검사를 없애는 방식은 답이 아니다.

이 근거로 네 번째 batch 후보는 **SEAL 대기(reason2)에서만** 기존7블록 예산을 연속 소비한다. 매 블록마다 D1 CRC·복원·D2/D0 반환 확인·STOP guard는 그대로 실행하고, 빈 STATUS/COMPLETE/예산0에서 즉시 끝낸다. E0의 전체 표시 ACK 확인은 이 제한 묶음 전후에 유지한다. pre-SEAL credit/ordinary(reason0/1)와 map-idle(reason4)은 여전히 한 블록만 처리하므로 새 출력 공급을 최대7블록 동안 독점하지 않는다. 다음 COMMIT은 이전 표시 ACK·EA 뒤에만 가능하다. 현행 호출자의reason2는SEAL 이후이고, reason3은 호출되지 않는 기존 호환 분기다.

마지막 read 후보는 수신한 positive STATUS를 재사용할 때 실제로 전송하지 않는 D0의 `frame()`·CRC8 생성을 생략한다. D0가 필요한 else 경로에서만 헤더를 만들고, 곧 D1의 실제 길이만큼 다시 초기화하는259B 초기 zero도 제거한다. D1 전송 범위는 기존 `memset(n+3)`로 모두 초기화하며 D2/D0의8B frame은 각 byte를 모두 기록한다. 사용하지 않는 stack을0xA5로 채운 검사에서도 wire dummy와 명령 CRC가 같다. 수신 data CRC·cached STATUS CRC·token·POP 확인은 삭제하지 않는다. 같은7블록 명령 수는33,681→30,172(-3,509)이며 이 값은 실제 링크 명령 수이고 실물 ARM 시간으로 주장하지 않는다.

## 비교 판정

682의 제한 묶음+송신 준비 제거는 두 위상 모두955 ACK 전956 입력7블록 확인(여유0.620/0.516ms), 첫 BG ROM창,952 표시3회·957 최종대기0회·큰묶음·보호조건을 유지했다. 밀집 평균−0.010523/−0.007096ms지만957 마지막ACK+0.115564/−0.120872ms로 동시 개선은 미달해 MMC666을 유지한다.

| 후보 | 955 ACK 전 확인된956 블록: 위상1 / 2 | 밀집 평균 변화(ms) | 957 ACK 변화(ms) | 판정 |
|---|---:|---:|---:|---|
| credit 계산 통합 | 6 / 5 | -0.037938 / -0.036448 | +0.071797 / -0.113422 | 7블록 미달·위상1 ACK 회귀 |
| 실제 입력 진행 반영 | 7 / 7 | +0.061572 / +0.062243 | +0.062392 / +0.071983 | 7블록 통과·911/종단 회귀 |
| FINISH 뒤 출력 credit 결합 | 6 / 6 | -0.003743 / -0.037677 | +0.067979 / -0.213994 | 6/6블록·위상1 ACK 회귀 |
| SEAL 뒤 7블록 제한 묶음 | 7 / 6 | -0.007804 / -0.035759 | +0.105134 / -0.126459 | 7/6블록·위상1 ACK 회귀 |
| 묶음 + 송신 준비 중복 제거 | 7 / 7 | -0.010523 / -0.007096 | +0.115564 / -0.120872 | 7/7블록·보호조건 통과, 위상1 ACK 회귀 |

최종read 후보의 첫D1→일곱째D0는6.199593→4.035271ms다. 개별poll의 CRC/반환 확인까지955 ACK 전에0.620499/0.516011ms 여유를 확보했다. 956 선행DMA는681의map128B·tile0B에서두위상map512B·tile16B로 늘었다. 반면957은map1472B·tile16B로 남는다. map1024/1216 각각192B는이미수락됐지만그사이BG48B를발행해append212의tail병합이끊겼다. 위상1은956에서384B한번이192B두번으로갈려추가128B기회를놓쳤고,957에서도MMC666의384B대신192B만선행됐다. 1216 map ACK125/121선은선행DMA238선보다이르므로단순수신지연으로해석하지않는다. 다섯후보530화면을동일작업량/출력/큰묶음으로대조했고,최종후보의911·951·952·957보호조건과모든기존VBlank횟수를유지했다. 이는 실제 하드웨어 FPS 향상을 뜻하지 않는다.

최종 수치는 아래 검증 JSON과 연결한다. credit 계산만 통합한 대조군(account), 실제 입력 진행으로 quiet 대기를 제거한 후보(progress), FINISH 뒤 출력 credit 대기에 결합한 후보(credit)를 분리한다. batch는 이 세 후보 뒤에 실제 E0 비용을 근거로 추가했다. 각 후보는53화면×두 시작 위상으로 같은 출력/픽셀, map·tile·ordinary 내용, E9 큰 묶음의 count/first/decoded를 비교한다.

## 다음 작업

682 read 입력 경로는 수신 회복 비교 후보로 고정한다. 다음은956/957의 map1024·1216 사이에 들어간 BG48B 때문에 수락 시384B 병합이 사라지는 경계를 다룬다. ARM이 두 map을 연속 발행하는 방식과65816이 이미 수락된 map을 제한적으로 병합하는 방식을 분리 비교한다. 첫 BG ROM창·큰묶음·7블록·STOP·독립 검사·최종 ACK를 유지하고,956의 추가128B 선행 기회와957의 추가192B를 함께 확보해야 한다. 위상1의 이전956 표시 지연0.081295ms와957 자체 간격 증가0.034269ms를 나눠 예산을 잡는다. 현재map 한 패킷의 전송/드라이버0.692830ms를 BG 지연에 공짜로 옮기지 않는다. Flash148B·packedROM0B 안에서 삭제할 코드를 먼저 정하고, 두 위상 전체 시간 통과 뒤에만 전체 Lite FIT/STA를 진행한다. 같은 입력 polling·고정 지연/위상·선택 크기 변형은 반복하지 않는다.

## 안전과 자원

- account/progress 각각20개, credit44개, 최종batch/read 각각48개와read의cached STATUS 손상2개 실제 링크 수신 검사: 빈 D0 두 번 뒤 정상 수신, CRC·POP 반환 불일치, STOP 전/READ 뒤, IO 실패, token wrap, COMPLETE, 예산0, 출력 진행 우선, plan 미완료 차단. 실제 `nes_cost474_pause` 진입의 progress도 확인한다. 전체 시간은 별도 연속 재생으로 검증한다.
- progress의 기존 E0 진행·identity·인계28조건, BG/OBJ·CRC·STOP5조건과 메뉴/base5조건·marker4조건을 확인했다. credit/batch/read도 메뉴/base 경계를 실제 링크 코드에서 확인했다. 새 물리 메뉴 복귀 시험은 아니다.
- ARM source 차이는 account/progress/credit/batch는 `nes_native_runtime165.c`만, read는 추가로 `nes_native165.c`의 송신 준비만 바꾼다. generator 재실행과 준비된 source 바이트가 일치한다. data10,040B/BSS19,544B는 유지한다. account/progress/credit callback은32B, batch/read는40B로8B 늘며 전체 연속 실행의 stack 하한도 함께 확인한다. ARM 전체 링크 및 실제 firmware 길이를 사용하며 object 크기를 Flash 여유로 대신하지 않는다.
- 65816은681 `client02` 그대로다. body5,967B/physical5,120B/packed spare0B. FPGA RTL은680과 같다. 변경 없는 독립 검사·STOP·최종 ACK·늦은 DMA 경합은681의 고정 hash 근거를 유지한다. 새 회로 절감으로 계산하지 않는다.
- 전체 Lite FIT/STA는 두 위상 종단 시간 게이트 통과 후에만 진행한다. 기존680 MAP+35comb/+3FF를 전체 FIT84LE·1LAB 여유에서 빼서 통과로 간주하지 않는다. 실기 MMC666과 GBC·save·기존 ZIP은 변경하지 않는다.

## 재현과 근거

[검증](../analysis/receive682-verification.json) · [원시 archive](../analysis/receive682-archive.json) · [생성기](../tools/prepare_nes_receive682.py) · [입력/STOP 검사](../tools/check_nes_receive682.py) · [실제 공동 재생 관측](../tools/test_nes_receive682.py) · [분석기](../tools/analyze_nes_receive682.py).

생성 기준은681 `arm02` firmware hash로 고정한다. `--progress`는 실제 수신 진행, `--credit`는 FINISH 뒤 출력 credit 대기 연결이며 두 옵션을 함께 쓴다. `--batch`는 이 둘을 유지하면서 SEAL 뒤에만 제한 묶음을 실행한다. `--read`는 이 묶음의 송신 준비 중복 제거다. private `replay.ps1`에53화면·두 시작 시각·공유SPI/IRQ·ROM 달력·실제65816 호출을 보존한다. 첫 account/progress 관측기는reason2/4만, credit 관측기는0/1도 기록하며 target 코드/시간을 바꾸지 않는다. batch는 개별poll 성공 반환을 추가 관측하고, read는 시작 때 firmware hash도 기록해 종료 hash와 대조한다. 단계별 관측기 원문과 실행 명령을 archive에 남긴다.

D2 요청 시각만으로 수신 완료를 주장하지 않는다. `receive956.checked_blocks_before_ACK`는 D0 반환·CRC/identity 검사가 끝난 뒤 성공 반환까지 완료된 개수다. account/progress/credit은 전체wait callback, batch/read는 개별poll 반환을 사용한다. D0 전송 완료는 별도 시각이며, 그 자체를 검사 완료로 보지 않는다. account의 callback 시각에는 기존 quiet 대기도 포함된다. 반복 ROM 달력은 실제 게임의 NES/PSRAM 전체 공동 실행이 아니고, IRQ·SPI driver 평균/CPI2의 한계를 유지한다. 실기 출력·ACK26.84ms를 모델 개선 비율로 환산하지 않는다.

추가 batch 검사의 첫7블록 fixture는 header8B와 map값2B의 서로 다른 record 폭을 구분해야 한다. 최초 fixture가map도8B로 보내 거절된 실패 로그를 보존하고6B record로 수정했다. 주석 수정 후 incremental build가 timestamp 기반 fwhdr를 바꾼 중간 두 재생은 중단·제외했다. 최종 바이너리를 고정한 `batchb1/2`만 채택 판정에 사용한다. 제외 사유·이전 이미지 hash와 실패 로그는 archive에 남기며 성공 횟수에 포함하지 않는다.

Flash 전체 링크는 account 212,796B/free196B, progress 212,800B/free192B, credit 212,832B/free160B, batch 212,860B/free132B, read 212,844B/free148B다. 두 위상 종단 시간 게이트 미달로 새 합성/FIT/STA·설치본은 없다. 681과동일한ROM/680RTL 보드입력의모든hash만대조했다. 기존680 MAP+35comb/+3FF를전체배치여유84LE·1LAB에서차감해통과로주장하지않는다. 실기선택본MMC666과README의실기수치를유지한다.

최종 ARM 실행의 workspace 끝은0x2000f0d0, 관측된 최저SP는0x2000f7b0/0x2000f814로 최소1,760B 간격을 유지했다. 정적RAM을새로확보했다고계산하지않으며, 모든호출조합의실물stack상한을뜻하지않는다.
