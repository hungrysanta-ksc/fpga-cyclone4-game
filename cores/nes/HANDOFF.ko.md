# 현재 NES 인계

**PR161 · 969 발행 순서.** 실기 기준은 MMC763이다. 777A는 227선 전에 OAM·scroll·padding 196B를 수락하고 496→880B DMA를 확보했다. 두 위상 모두 969는 3 VBlank, 연속 마지막 ACK는 MMC767보다 늦었다. 다음은 첫 VBlank에서 offset 1,024 뒤 1,216 map의 발행이 끊기는 원인과 독립 검사 예산을 맞춘다. [측정·재현](../../docs/progress/pr-161.md)

**PR159 실기 계측.** 기준 MMC763. 769에서 496B 선행 DMA와 두 위상의 3 VBlank를 유지하며 E0 5회를 줄였지만 969 최종 ACK는 −120/+240클록으로 엇갈렸다. 770·771 실기 5–55초는 18.70/18.72fps, 25–30초 출력은 36.25/36.67ms다. 작업량 근접 5쌍의 첫 DMA는 모두 SEAL 다음 VBlank였다. 다음 속도 시험은 직전 ACK→SEAL의 descriptor/E8 준비를 대조한다. 772의 중간 성 프리즈는 764·766과 동일한 162선 dot 0 PPU ROM 읽기 마감으로, 주소·허가·응답 파형 재현이 남았다. [설치·반환 파일](../../docs/nes-mmc770-trial.ko.md) · [검증·재현](../../docs/progress/pr-159.md)

**PR158 실기 A/B 완료.** 767 부팅·60초·메뉴 복귀 성공. 5–55초 A 20.64fps, B 17.96fps로 763을 실기 대조군으로 유지한다. 25–30초와 비슷한 작업량의 출력 지연을 분리한다. 764/766 장시간판은 중간 성 162선 dot 0에서 ROM 오류 2를 기록했다. [결과·후속 재현 경계](../../docs/nes-hardware767-results.ko.md) · [설치](../../docs/nes-mmc767-trial.ko.md)

PR156 병합 `4ee65ac300c3b5eca73848bd0b408c1bc63b6800` 확인 뒤 현재 브랜치는 `codex/nes-bg-deadline-707` / PR157 draft이다. 다음 개발 기준은 MMC690이고 MMC666 대조군은 보존한다. PR154는 master `3f8292795b8a5e53d6cf250fcc568223e748a3d6`에 병합됐다. 이전 대조군 MMC666은 [667 실기 분석](../../docs/nes-hardware667-results.ko.md)과 [설치 안내](../../docs/nes-mmc666-trial.ko.md)를 따른다. MMC662는 이전 비교 기준으로 보존한다.

**현재 753** 최초 7블록을 받은 뒤 warm 뱅크에서 128B 이상인 준비 블록 하나를 선행 수신했다. 956 최종 ACK 대기의 E0는 두 위상 모두 12→9회, 957 입력→planner는 17,750 / 17,751클록 줄었다. 749의 E8 마감과 952·957의 1,536B map 선행을 지키고 OBJ는 양쪽 246선에 시작했다. 727 대비 밀집 평균은 22.489 / 19.850µs, 957 ACK는 360,266 / 2,558클록 빨랐다. [두 위상 결과](../../docs/nes-credit753-results.ko.md)


## 현재 작업

**현재706 실기:** 706 실기: MMC704 1차는 기존690과 같은 stage0 5초 준비 timeout,705 1차는193:230 배경 CHR21E161 deadline2(age2)로 서로 다르다. 704 2차는 정상60초·메뉴 복귀,5–55초19.04fps(700대비−10.10%,작업량 증가로인과미확정)다. 705 2차는298.56초·5957표시·사용자종료/메뉴복귀,스페이드 클리어를 사용자 확인했다. 그러나 여러 장면의 반복 타일 깨짐과 최대430ms 표시 공백이 남아 전체 안정성은 미승인이다. [실패 분리·FPS·화면 정확성](../../docs/nes-hardware706-results.ko.md). 사용자 PR156 병합 후 지시에 따라 배경 CHR 마감 오류만 먼저 재현·수정하고, 검증 후 같은 map·OBJ 작업량의 출력·최종 ACK 속도 최적화로 돌아간다. 스페이드 진입은 실기 해결로 인정한다. 반복 화면 깨짐과 기존 stage0 부팅 timeout은 미해결 관찰로 보존하되 이번 속도 작업의 선결 조건으로 삼지 않는다. 속도 개선이 깨짐을 반드시 해결한다고 가정하지 않는다. 독립 검사·STOP·최종 ACK·메뉴 복귀와 기존 두 위상 표시 일정을 유지한다.

**이전694–696:** 694 통합 검증과 MMC695(60초)/MMC696(장시간) 전달본 준비 완료. packed 부팅·generation wrap·STOP/종료·106화면 공동 재생·전체 Lite FIT/STA 통과. MMC690 대비 위상1 밀집 +0.010728ms/906 대기1회로 엄격한 시간 무회귀는 미달이며 성능 후보로 채택하지 않는다. 기존60초 구현은 보존하고 장시간 기능판을 분리했다. 전체 보드 비용/STA는689D와 동일,Flash 여유695=8B/696=52B. 장시간 실기는 미검증. [결과·재현](../../docs/nes-longrun694-results.ko.md) · [설치·종료·로그 안내](../../docs/nes-mmc695-696-trial.ko.md) · [패키지](../../analysis/trial695-package.json). MMC695를 같은 첫 레벨5–40/40–55초 대조로,MMC696을 장시간·L+R+Start+Select 종료·메뉴 복귀 시험에 사용한다. 자연 발생한 부팅/장시간 실패를 분리 보존한다. 이후692의951 마지막tile ACK→SEAL12.448/11.849ms를 준비·credit·수락으로 나눠 두 위상 밀집간격·957 마지막ACK가 함께 개선되는 최소 후보를 검증한다. 고정지연·위상상수·seed 탐색은 보류한다.

**현재691 실기 확인:** MMC690 두 실기 중1차는 첫 표시 전5초 준비 timeout,2차는1250/60.35초(20.71fps) 실행·메뉴 복귀 성공이다. 5–40초19.97fps(+1.75%),40–55초19.40fps(+0.34%),5–55초19.80fps(+1.33%)다. 출력·최종ACK25.56ms,후반은사실상동일하며map/OBJ작업량차이로구현만의가속은미확정이다. [결과](../../docs/nes-hardware691-results.ko.md) · [분석](../../analysis/hardware691-mmc690.json). MMC690의 출력·최종 ACK25.56ms를 같은 map·OBJ 작업량의 ARM발행·65816수락·DMA·마지막VBlank로 나누고 두 위상의 밀집 간격·마지막ACK를 함께 줄일 경계를 정한다. MMC666 대조군·독립 검사·STOP·캡처 회복·메뉴 복귀·951공개선·952표시3회·957최종대기0회를 유지한다. 551/639/690의 stage0 부팅 실패는 별도 안정성 항목으로 첫fetch·WRAM복원·준비공개 경계를 확인하며, 원인이나 재현 없이 재시도/대기/STA조건을 바꾸지 않는다. 자연 재발 로그를 보존한다.

**689 검증: 688 일정 유지, E0·queue 통합으로 전체 FIT·기존 제약 STA 통과** [결과](../../docs/nes-status689-results.ko.md) · [검증](../../analysis/status689-verification.json). 689D는 688의 ARM·685의 65816 바이너리를 그대로 유지하면서 6 LAB 부족을 해소했다. 전체 Quartus Lite FIT는 15295 LE·963/963 LAB·56/56 M9K로 통과했고, 기존 제약의 최악 setup/hold/recovery/removal은 +0.104/+0.137/+1.460/+0.488ns다. 같은 두 위상106화면 재생은 688과 클록 단위로 일치했다. 실기 기준은 MMC666이다. **MMC690 전달 근거**: [설치 안내](../../docs/nes-mmc690-trial.ko.md) · [패키지 검증](../../analysis/trial690-package.json). MMC690 전달본을 준비했다. 689D 보드·685 CPU는 고정하고 688 ARM의 메뉴/ROM/로그 이름만 변경했다. 799개 함수의 주소·크기·명령 바이트가 동일하며 Flash212984B/free8B다. 실제 프로그래머·ROM읽기·STOP·메뉴/base·5–40/40–55초 집계를 검증했다. 실기 결과는 아래691에 정리했다.

**이전678: 수신 예산 수정·957 DMA 회복, 전체 채택 미달.** [결과·다음 경계](../../docs/nes-handoff678-results.ko.md) · [검증](../../analysis/handoff678-verification.json). 678 수정본은 빈 D0가 7블록 수신 예산을 소모하지 않도록 하고 END 발행 중 map→tile 전환을 연결했다. 952는 두 위상3회·큰묶음·보호조건을 유지했고, 밀집 평균은−0.04567/−0.05654ms다. 마지막ACK는+0.01043/−0.18270ms로 동시개선은 미달해 MMC666을 유지한다. 다음은956의 실제 DMA 진행 공개·identity·STOP 경계와 삭제 예산을 먼저 정한다. 선행 조회34/35회가 모두 빈 D0였고956 선행map은128B로 남았으므로, 같은 조회/고정대기/위상별상수 변형은 보류한다. 선택보드84LE·1LAB·0M9K, ARM192B(678)/496B(MMC666), SNES ROM11B 안의 전체비용을 판정한 뒤에만 구현한다. 새FIT/ZIP은 없다.

**이전676 입력 진행·마지막 plan 허가: 기능 통과·시간 실패, MMC666 유지.** [결과·다음 경계](../../docs/nes-idle676-results.ko.md) · [검증 JSON](../../analysis/idle676-verification.json). 676에서 map 뒤 40회 대기를 실제 입력 한 블록으로 교체하고 마지막 13-record plan 허가를 결합했다. 입력 단독·결합 모두 기능은 통과했지만 952는 두 위상 4회로 실패했다. 결합 후보의 밀집 평균 +3.272/+3.282ms·957 마지막 ACK +16.948/+16.711ms로 MMC666을 유지한다. tile은 약 10ms 빨라졌고 대기는 6.561→0.716ms지만 선행 map은 1536→192B, 입력 callback 중 실제 DMA는 0회다. Flash 212688B/free304B, static RAM·기존 보드·65816은 동일하다. 다음은 952 offset2048–3392의 준비·bulk 우선권·수락·빈 큐 DMA 선택을 묶어 원본 수락 마감 33.125/33.405ms의 예산을 확정한다. map 뒤 대기는 이미 VBlank 밖이므로 고정 대기/pair/위상 상수 반복은 보류한다. 실제 DMA 완료 공개가 필요하면 읽기 완료·CDC·STOP·Flash/LE 예산부터 정하고 E0 수신 ACK와 구분한다. 새FIT/ZIP없음.

**이전675 초기 허가 결합: 기능 통과·시간 회귀, MMC666 유지.** [결과·다음 경계](../../docs/nes-bg675-results.ko.md) · [검증 JSON](../../analysis/bg675-verification.json). 675 첫 zero 소비+BG grant는 실제 RTL/ARM 기능과 후속 큰 묶음을 통과했지만952가3→5/4회로 회귀했다. 밀집 평균+6.702/+3.311ms,957 마지막ACK+33.763/+16.926ms로MMC666을 유지한다. 마지막 tile ACK는약10ms 빨라졌으나 기존 map drain 뒤40회 대기가새로걸려ordinary 요청공백0.094→6.561ms,선행map DMA1536→192/768B다. 다음은952 map drain 뒤 대기를 실제 DMA 진행·큐 유휴 기회·다음 입력 수신으로 나눠,도착순서에따라40회 대기가붙는조건을대체할경계를검증한다. tile이득과map 선행1536B·SEAL마감을함께회복하는후보하나를두위상으로대조한다. 첫pair크기/고정위상/대기횟수만의반복조정은보류한다. 새FIT/ZIP없음.

**이전674 BG 쌍 선행 전송: 기능 통과·시간 회귀, MMC666 유지.** [결과·다음 경계](../../docs/nes-bg674-results.ko.md) · [검증 JSON](../../analysis/bg674-verification.json). 두 위상106화면의 출력·최종 ACK는 일치하지만952는3→4/5회,밀집 평균+9.903/+13.230ms,957 마지막ACK+49.911/+66.333ms다. 911 마감·951 공개선·957 최종대기0회와STOP/메뉴 경계는 유지했다. 957은plan bank 허가가 있어도zero tile소비를 기다려E9가늦고,954는반복pair의plan bank 대기로계산이멈춘다. 다음은첫zero소비+BG grant의실제두slot/bank 검증과954 준비경로 예산을 함께 다룬다. 새ZIP/FIT없음.

**이전673 확정·credit·ROM 마감 분해 완료, MMC666 유지.** [결과·예산](../../docs/nes-ready673-results.ko.md) · [계측 JSON](../../analysis/ready673-budget.json). 두 위상106화면의 모든 ACK/출력 바이트가 원본과 같다. 957은 준비된 BG의 묶음 대기7.41ms,954는 마지막 BG 생성이 이전 ROM 창보다2.38–2.64ms 늦다. ordinary 조립0.106ms만 줄이거나 현재 ROM 응답을 고정한 credit 절감으로는 이전246선에 못 들어간다. 다음은957 조기 BG 인계와954 계산 선행 예산을 각각 확인하고 immutable ordinary와 결합한다. 보호 조건 모두 유지, 새제품/FIT/ZIP 없음. 기존672의 마지막 ROM 응답에 캐시 공급이 포함됐음을673에서 정정했다.

**이전672 수락 범위 선택: 기능 통과·시간 실패, MMC666 유지.** [결과·재현](../../docs/nes-extent672-results.ko.md) · [검증 JSON](../../analysis/extent672-verification.json). 두 위상106개 화면과 STOP/새 패킷·독립 coverage·부분 DMA 뒤 cold 복구·최종 ACK 취소를 통과했다. 954 위상2 선행 map384→1344B지만 밀집 평균은+0.022200/+0.036262ms,957 마지막ACK는+0.004563/−0.045630ms다. 911 마감·951 공개선·952 3회·957 최종대기0회 유지. ROM 여유42B지만 시간 실패로 새 FIT/ZIP은 없다. 다음은MMC666 마지막 tile·ordinary의 의미상 확정→실제 준비/credit/수락을 묶어 이전 VBlank 마감 예산부터 세운다. 선택기 단독 변형을 반복하지 않는다.

**이전671 실제 커널 비용 실패.** [결과·다음 단계](../../docs/nes-supply671-results.ko.md) · [검증](../../analysis/supply671-verification.json). 실제 전체링크 ARM 생산기와65816 변환/독립CRC를 실행했다. source42.58ms,954/955 행88.99/85.17ms로 wire절감3.21/3.24ms보다 크다. ARM 자원링크free244B지만 제품 callback·문맥·source RTL은 미연결이다. 509개CPU command와45개소유권 모델 검사 범위만 통과했다. 그 후672에서 수락범위 선택을 실제 비교했다. 새제품/실기ZIP은 없다.

**이전670 비용표.** [참조 복원·소유권](../../docs/nes-supply670-results.ko.md) · [근거](../../analysis/supply670-budget.json). 106개 참조 map 일치와 일괄 descriptor의 바이트 절감 가정을 확인했다. 그 뒤671에서 행별 반복 header와 실제 CPU 비용을 포함하자 시간 게이트에 실패했다. COMMIT 뒤 collector 재읽기 기각과 저장 credit/최종 표시 ACK 분리는 유지한다.

**668 두 후보 검증 완료·둘 다 기각, MMC666 유지.** [668 비용·결과·다음 순서](../../docs/nes-output668-results.ko.md) · [검증 JSON](../../analysis/output668-verification.json). 같은 map/OBJ의 실제 ARM·65816 재생에서 반복 탐색은 약 0.75→0.14–0.18ms로 줄었지만, 위상 1의 선행 DMA가 감소해 마지막 ACK가 0.215ms 늦어졌다. map 소비 완료를 기다리는 결합 후보는 911의 업로드 VBlank를 하나 놓쳐 마지막 ACK가 16.849/16.640ms 늦어졌다. 안전 검사는 통과했으나 시간 조건은 실패했다.

**669 소스 재검토의 원래 계획.** [직접 공급·주사선 예산 계획](../../docs/nes-reference669-plan.ko.md) · [소스/선택본 대조](../../analysis/reference669-review.json). 첫 예산 비교는670에서 진행했다. 16KiB mailbox를 추가하거나 NES 원본을 SNES map과 같은 데이터로 가정하지 않는다. 954·957 수락 범위·병합·주사선 예산은 별도 비교 후 결합한다.

911 SEAL 수락189/검사 완료214번 선의 기존 여유, 951 공개선·952 3회 이하·957 추가 대기0회·STOP·독립 검사·캡처 회복·메뉴 복귀와 두 위상의 밀집 평균·마지막 ACK 동시 개선을 요구한다. 단독 탐색/일괄 drain/위상별 고정 지연 반복과 659 작은 타일 직접 PSRAM DMA 재시도는 새 근거 전까지 보류한다. 669·670은 소스·참조 복원·예산 검토이며 새 target 기능·속도·합성 검증은 아니다.

선택 산출물은 `probes/nes-trial666/arm01/src` ARM, `probes/nes-entry665/client02` 65816, ASCII Temp `nes-entry665-board01`이다. MMC666 패키지 SHA256 `67dfd6e294542c188463b889cd27f98587ae6db4fc582e52b43075f9304d4b56`, [패키지 근거](../../analysis/trial666-package.json). Flash 212,496B·여유496B, data/BSS10,040/19,544B, 전체15,324LE·962LAB·56M9K. 새 ZIP은 만들지 않았다. ROM/save/RESTORE 제외·사용자 SD 설치 방식은 유지한다.

## 최신 실기와 비교 기준

MMC666은 60.32초에 1,221회(20.24fps), 5–40초19.63fps·40–55초19.33fps·5–55초19.54fps다. 출력·최종 ACK는26.84ms이며 map/OBJ 작업량이 달라 MMC662 대비 구현 가속을 단정하지 않는다. 실행·STOP·캡처 회복·메뉴 복귀를 확인했다. [실기 비교](../../docs/nes-hardware667-results.ko.md)

**MMC509 /507 FPGA /489 SNES**:60.08초770회 **12.82fps**, 실행·입력 흔적·STOP/base 복구와 사용자 메뉴 복귀 정상. 체감 개선은 작았다. 이전 MMC502는60.07초636회10.59fps이며 복구 기준으로 보존한다. 같은 동선·첫 레벨 전용 비교는 아니다. 원본 로그는 `probes/nes-hardware510/run01`, 선택 증거는 `termination01`/`analysis02.json`이다.

[MMC509 패키지](../../analysis/service509-package.json)와 `probes/nes-service509/trial01/MMC509-OVERLAP.zip`, ARM03,507 board01,489 client04를 고정한다. 게임 ROM/save/RESTORE는 전달하지 않는다. 사용자가 SD에 설치해3개 로그를 반환하는 절차이며 보드·SD를 PC에 연결하도록 요청하지 않는다.502 ZIP/기존 백업·GBC/save는 변경하지 않는다.

수신19.88 / 계획·공급14.30 / 출력·최종ACK43.17ms다. 계획17.02ms 감소에는 bulk 대기를 SEAL로 옮긴 효과가 포함된다. 마지막771번째 ordinary section5 요청은4credit 대기 중60초 제한에 걸려 제외했다. 실제 ARM03로1/2/2·pending4를 재현했고 진짜IO/CRC를 구분했다. 전체 무손실·모든 mapper·60fps는 아니다.

## 다음 작업 순서

1. R1은580 전체비용표와581 제한 조사로 결측을 명시하고 마감했다. 53개 입력·106D1경계·3378E1 publish/load/ACK와 map/palette/OAM 복원을 대조했다. 물리 ROM/capture/입력 지연·대표 장면·clean-clone 전체실행은 여전히 미완료다. 같은 분석을 반복하지 않는다.
2. [594 ARM 결과](../../docs/nes-report594-results.ko.md). 594 전체 ARM이 212,064 B로 링크돼 928 B가 남았다. 같은 ELF에서 cold 905는 17.984 ms(CPI 2), 53입력·27수신 조건·3표시 ACK 조건을 통과했다. 종료 보고 때만 서식을 복원하며 기존 로그와 바이트가 같다. 595에서 이 ARM과 FPGA를 연결했다. 596의 한 페이지 예약 방식은 입력당 26페이지·고정 78거래·546 B를 줄인다. 결합 진단 MAP은 2,708 LE로 892 LE와 새 제어 비용이 남았다. 597은 595 핀 경로에서 묶음 전송으로 905·906 각각 97거래·698 B를 줄였다. 결합 진단은 2,625 LE로 809 LE 초과, 외부 생산 비용을 0으로 둬도 1,909 LE다. 598의 collector 요약은 53입력·1,537그룹에서 일치하고 905/906의 D0를 11/10회 줄였다. 결합 MAP은 4,910 LE로 새 경계 상한보다 907 LE 크다. [599 출력 실측](../../docs/nes-output599-results.ko.md)에서 상속 CRC만으로 두 위상의 기준 최종 ACK보다 12.077–15.995 ms 늦었다. [600 실제 SPI·ROM 비용](../../docs/nes-wire600-results.ko.md)에서 562/558 B를 줄였지만 필수 조회를 포함한 wire 하한은 16.808/17.030 ms였다. 601에서 현재 PPU 캡처를 재사용해 952·954의 208/272개 요청을 모두 충족했다. 두 위상의 낙관 표시 간격은 31.443–31.900 ms다. [601 검증](../../docs/nes-snoop601-results.ko.md) 602의 4 B D2는 두 장면에서 60 B를 절감했다. 한 슬롯의 D1 중첩은 0이고 두 슬롯을 가정해도 표시 전 5.144–5.587 ms가 더 필요하다. [602 검증](../../docs/nes-overlap602-results.ko.md) 603의 compact palette는 290 B를 줄이지만 65816 복원·검사가 12.014 ms로 기존 palette ACK보다 8.585–8.708 ms 늦다. [603 검증](../../docs/nes-palette603-results.ko.md) 604에서 실제 행 압축·ARM 복원으로 278 B와 첫 BG 1.668 ms를 줄였으나 두 위상의 첫 ROM 허용 시각은 같았다. [604 측정](../../docs/nes-rows604-results.ko.md) 605에서 직전 표시 뱅크 이력으로 첫 BG 48 B를 골랐다. 전체 ROM 읽기 단축은 두 위상에서 0.121–0.145 ms였고 954의 60 Hz 마감 전 ROM 공급 상한은 8/272 B였다. [605 근거](../../docs/nes-prefix605-results.ko.md) 606에서 954의 현재 캡처가 272/272 B를 보존했다. 이전 ACK 대기에 입력 6블록을 옮겨도 첫 E9는 EA 뒤 16.852 ms다. 입력을 전부 숨긴 조합에서도 필수 드라이버 비용까지 16.162 ms가 걸렸다. [606 검증](../../docs/nes-overlap606-results.ko.md) 607의 MMC577 ARM 후보는 최근 두 슬롯을 재사용해 Flash 16 B를 남겼다. 두 위상 53화면에서 밀집 25→24 VBlank, 마지막 ACK −17.799/−50.809 ms였다. 952·954의 SPI 거래는 증가했고 957 최종 대기는 0→1회여서 실기 기준은 MMC577이다. [607 검증](../../docs/nes-planner607-results.ko.md) 608에서 팔레트 DMA만 바꾸면 957의 최종 대기가 두 위상 모두 1→0회이고 밀집 구간 24 VBlank를 유지한다. ARM 조회까지 결합하면 24 / 25 VBlank로 위상 2가 회귀한다. 실기 기준은 MMC577을 유지한다. [608 검증](../../docs/nes-quiet608-results.ko.md) 609의 두 캡처 뱅크가 OBJ 96 B를 모두 공급해 마지막 OBJ 응답은 약 26 / 15 ms 앞당겨졌다. 선행 DMA가 줄어 952 표시는 두 위상 모두 한 VBlank 늦어졌고 957 최종 대기는 0회를 유지했다. 공유 포트 RTL은 229 LE·38,400 bit로 단독 추가 예산은 81 LE 부족하다. MMC577을 유지한다. [609 검증](../../docs/nes-obj609-results.ko.md) 610에서 OBJ bulk 뒤에만 map을 겹치면 두 위상 모두 952는 6→5 VBlank, 밀집 합계는 24→23, 마지막 ACK는 −49.917 / −16.670 ms이며 957 최종 대기는 0회를 유지했다. 실제 source는 1,244→1,073 LE, 산술 여유 319 LE·M9K 0개다. ARM Flash는 212,992 B로 여유가 없다. 기존 BG 적중 48회와 보드 lifecycle은 아직 함께 검증하지 않았으므로 MMC577을 유지한다. [610 검증](../../docs/nes-pace610-results.ko.md) MMC613을 실기 기준으로 삼는다. 같은 map·OBJ 작업량에서 출력 발행·65816 수락/DMA·마지막 VBlank와 ACK를 대조해 31.63 ms 중 줄일 시간을 구분한다. STOP·독립 검사·최종 ACK·메뉴 복귀를 유지한다.
3. R3: 후보 하나만 구현·동일입력/두위상·대표장면 검증. 같은 가설 두 변형에 종단 이득이 없으면 새 증거 전까지 보류한다. 안정성 보완은 성능과 별도 판정한다.
4. R4: 의미 있는 후보만 고유파일명/RESTORE없이 실기. 5–40/40–55초, STOP·독립검사·최종ACK·VBlank·메뉴 유지. 외부IO/capture/지속60fps는 별도 미완료다.

512·514의 제외 근거는 [전송 형식 비교](../../docs/nes-transfer512-results.ko.md)와 [해당 PR 기록](../../docs/progress/pr-141.md)에 남아 있다.

## 재현 위치와 실패 보존

공개 entry는 `tools/nes_raw506.py`와 `test_nes_raw506_*`, `prepare_nes_raw506_board.py`, `analyze_nes_raw506.py`다. 저장소 부모의 `probes/nes-raw506`에 candidate01/ARM02/arm-test02/guards01/clock01/analysis03을 보존한다. Temp의 `nes-raw506-rtl02`, `nes-raw506-board01`, `nes-raw506-joint11`(후보)/`joint13`(기준)이 선택 근거다. Temp 시험과 보드 원본의 보관본은 `probes/nes-raw506/archive01/evidence.zip`과 파일별 SHA inventory에 있다. 공개 검증에는 입력·firmware·보고서 SHA를 기록하고 상용 ROM/raw/바이너리/license는 넣지 않는다.

joint05/06은 atomic DMA overshoot를 ARM 대기로 더하고 capture를 EA 뒤로 늦춘 시간 모형이라 기능 근거로만 남긴다.11/13은 미래 ACK를 시각까지 보류하고 COMMIT에서 다음 capture를 재개한다. 초기 END 상태 오류·Windows 공유 잠금·emulator 초기 RPC watchdog(정확한 원인 미확정)·nominal SDC 누락·분석 문자 인코딩 실패도 남긴다. 이를 제품이나 새 Questa license 실패로 오인하지 않는다.

Questa는 기존 Starter FLOAT1좌석 wrapper로 순서대로 실행한다. Quartus는 Lite를 사용한다. README는 실기 상태나 중요한 작업 경계가 바뀔 때만 갱신하며 PR은 목표/작업내용/성과/후속작업 양식을 유지한다.

507 선택 근거는 `probes/nes-fault507`과 Temp의 `nes-fault507-test02`, `nes-fault507-board01`, `nes-fault507-trace01`이다. test01의 STOP offset 오류와 최초 wrapper sandbox 실패는 보존한다. 단일 Lite FIT 뒤 같은 DB에서 경로를 분석했으며 추가 seed를 시도하지 않았다.

507 공개 entry는 `tools/nes_fault507.py`, `test_nes_fault507.py`, `trace_nes_fault507_schedule.py`, `analyze_nes_fault507.py`다. 선택 집계는 `probes/nes-fault507/analysis02`, 보관본은 `archive01/evidence.zip`과 파일별 SHA inventory다.

508 entry는 `tools/nes_overlap508.py`, `test_nes_overlap508_arm.py`, `analyze_nes_overlap508.py`이며 공동 일정은 기존 `test_nes_raw506_joint.py`를 사용한다. 선택은 `probes/nes-overlap508/candidate03`(ARM02동일코드)/`ARM02`/`arm-test02`/`analysis01`/Temp `nes-overlap508-joint01`이다. ARM01의 Flash4B 초과를 보존한다. `archive01/evidence.zip`의15889개 파일을 전부 SHA로 검증했으며 license/상용ROM/raw/firmware는 Git에 넣지 않는다.

509 entry는 `tools/*service509*.py`다. 선택 ARM01/ARM03,arm-test01,parity02,analysis01,trial01과Temp rom03/joint01/calendar01·02/assembly01/programmer02를사용한다. private archive01은Temp원본을SHA로보존한다. ARM02 상대경로/rom01·02 harness/프로그램검사01 sandboxDLL 실패도보존하며새라이선스문제로오인하지않는다.
