# NES 670 · 직접 map 공급의 바이트·소유권·교체 예산

**MMC666을 유지한다.** 669의 첫 비교에서 map을 작은 descriptor로 바꿀 데이터 근거는 확인했다. 그러나 현재 FPGA 캡처 RAM을 그대로 재읽는 A안은 입력 COMMIT 뒤 수명이 끝나므로 사용할 수 없다. B안인 **COMMIT 전에 SNES WRAM에 원본 map을 복사하고 ARM의 slot/배치 정보를 적용하는 방식**은 제한된 변환·검사 비용 시험 대상으로 남긴다. 새 제품 ABI나 실기 후보로 선택하지 않았다.

## 같은 입력으로 확인한 범위

[분석 도구](../tools/analyze_nes_supply670.py)와 [프레임별 비용·해시](../analysis/supply670-budget.json)를 추가했다. 905–957의53개 geometry/raw를 기존 sealed hash와 대조하고, 실제653 송신기의 packed/원본 복구 block을 별도로 해석해957개 map cell과 일치시켰다. 두 위상의 D1 길이·순서는 모두 이 송신 바이트와 일치한다. 다음 입력을 선행 수신하는 D1/D2는 실행 중 표시 generation 대신 **input_generation**에 귀속했다.

ARM이 실제 생성했던538 plan 이력을 순서대로 적용해 tag→slot을 구했다. expected map에서 역으로 slot을 추측하지 않았다. 예외가 없는 이53개 입력은 tag별 현재 slot이 하나로 정해졌다. 33열 배치·palette epoch·64열 SNES 주소와 대상 뱅크 이력을 적용한 참조 복원 **106회 모두 기존4096B map과 정확히 일치**했다. 원본CRC 손상·잘못된slot·행expected 누락은 각106회 거부했다. 이는 Python 참조 복원과 산출물 대조이며 새 ARM 생산기·65816 실행·RTL·STOP 시험이 아니다. 새 제어는 아직 없고 선택본의 STOP·독립 검사·캡처 회복·메뉴 복귀 경로는 변경하지 않았다.

입력은 모두 map957개·row224개·exception0개다. 일반 범위 상한1056개, 예외/대체 행·다른 mapper·모든 장면의 새 변환 지원을 입증한 것이 아니다. raw/OBJ는 원래 경로를 유지한다.

## 실제로 생략 가능한 거래

가정한 새 map 명령은 payload 고정16B(버전·수량·행mask·원본CRC), 그룹당4B(원본그룹·목적그룹·열·palette epoch), tag/slot당4B, 업로드64B 행당expected CRC16 2B다. 현재와 같은240B payload 상한과 E1의명령/헤더/CRC19B를 포함했다. 이 형식은 비용 모델이며 실제 ARM 직렬화·65816 parser는 미구현이다. CRC16은 오류 검출이며 무충돌 보증이 아니다.

| 입력 세대 | 기존 map E1 | 새 형식 가정 E1 | 줄일 wire | wire 환산 절감 | 원본 수신 하한을 뺀 직렬 예산 |
|---|---:|---:|---:|---:|---:|
| 905·906 각각 | 4,452B | 641B | 3,811B | 11.614ms | 10.848ms |
| 911 | 844B | 231B | 613B | 1.868ms | 1.102ms |
| 951 | 1,982B | 414B | 1,568B | 4.779ms | 4.012ms |
| 952 | 2,110B | 454B | 1,656B | 5.047ms | 4.280ms |
| 953 | 927B | 352B | 575B | 1.752ms | 0.986ms |
| 954 | 2,148B | 498B | 1,650B | 5.029ms | 4.262ms |
| 955 | 2,065B | 428B | 1,637B | 4.989ms | 4.222ms |
| 957 | 2,257B | 466B | 1,791B | 5.458ms | 4.692ms |
| 밀집951–955 평균 | 1,846.4B | 429.2B | **1,417.2B** | **4.319ms** | **3.553ms** |

양 위상의 바이트 비용은 같다. 밀집 절감은 약1.38KiB이며 wire 환산은2.625MHz 기준이다. 전체 표시 시간 절감이나60fps 달성을 뜻하지 않는다.

- **D1 생략은0B다.** ARM이 현재 planner·slot 할당·OBJ·독립 expected를 유지하는 두 안 모두 입력 map이 필요하다. 원본 map1914B와 이미 압축된 D1을 동시에 절감으로 계산하지 않는다.
- **E0/D0 조회 절감은0회로 잡았다.** 새 명령의 credit·반환·STOP 응답과 공유 SPI 일정은 재실행 전에는 없어졌다고 할 수 없다. 추가 poll은 미확정이다.
- B의 원본 수신은12개 block으로1914B를 옮긴다. block별 immutable header12B를 더하면SNES 읽기2058B, token/gen ACK4B씩48B다. DMA 데이터만 `2058×8 master clock =0.766578ms`이며12회 설정·SNES ACK·포트 경쟁·원본CRC 계산은 아직 포함하지 않았다.
- 표 마지막 열은 wire 절감에서 위 수신 하한을 **직렬로 차감한 민감도**다. 변환·검사·설정·추가 ARM 계산에 허용할 확정 deadline이 아니다. 실제 수신 중첩도 있고 기존 소비 비용 제거도 있다. 911/953의 기존 map load→ACK 합은2.271/2.752ms,954는6.678ms(위상1)이며 ARM 발행·SPI와 겹친다. 이를 wire 절감에 더해 종단 이득으로 만들지 않는다.
- 가장 작은907은직렬 잔여0.401ms다. 매 프레임 동일 복원 경로를 쓰거나 밀집 사례의 이득을 모든 화면에 적용해서는 안 된다.

**묶음 descriptor의 준비 시각도 아직 통과하지 않았다.** 현재 `bg_map_frozen`은 planner가 BG 처리를 끝내고 OAM544B를 초기화하는 시점에서 찍는다(`trace_nes_map527.py`). 첫 map E1보다951은5.748ms,954는7.155ms,955는6.579ms 늦다(양 위상, 반올림). 이 시점까지 전체 recipe를 기다리면 지금의 선행 DMA 기회를 잃을 수 있다. 해당 marker가 각 행의 가장 이른 확정 시각이라는 뜻은 아니다. 이미 확정된 행·slot부터 증분 발행하려면 header·binding·CRC의 반복 전송과 ARM 준비 비용을 다시 포함해야 한다. 위 표의 일괄 최소 바이트를 현재 첫 map 발행 시각에 그대로 공급할 수 있다고 가정하지 않는다.

## 데이터 생산자와 보관 수명

| 데이터 | 현재 생산자·수명 | 직접 공급안에서 유지/추가할 작업 |
|---|---|---|
| NES compact map | NES collector→96bit CDC→host512B scratch; D2 뒤 block 재사용, COMMIT 뒤 collector 재사용 | D2 이전 두 소비자의 완료를 결합하거나 독립 snapshot 보관. geometry는 아직 SNES map이 아님 |
| tag→slot·배치 | ARM resident/planner, 현재 세대의 사용 slot은 재할당 금지 | ARM이 검증된 descriptor를 생산. 예외가 있으면 tag만으로 부족하므로 명시적 fallback 또는 더 넓은 key 필요 |
| SNES map의 보이지 않는 셀 | 직전 표시 map에서 상속, 대상 뱅크는 두 화면 전 상태일 수 있음 | 업로드 행을 직전 표시 뱅크에서 복사한 뒤 visible cell만 덮기. 전부0으로 채우거나 대상 뱅크만 쓰면 일반적으로 다름 |
| palette | ARM이 NES index를 LUT의SNES 색으로 확장 | 현재635 재사용이 이미 적용됨. 원본32B를512B CGRAM과 동일시하거나 기존 생략을 새 이득에 더하지 않음 |
| OAM | ARM이 NES 조각·가시 mask·평가순위·slot을 SNES 객체로 변환 | map 공급 변경으로 제거되지 않음. 대부분의 tail 재사용도 이미 적용됨 |
| HDMA/raw | ARM raster/patch 변환·SEAL 의미검사 | 이번 비용표에서 생략0. 기존 출력·coverage·메뉴 복귀 유지 |

`nes_capture_lease201`은 export COMMIT 때 collector를 해제하고 **ROM lease만** 표시까지 유지한다. 현재 캡처를 다음 화면이 덮을 수 있다. 현재 D2도 source scratch의cell/header를 지운다. 마지막 map D1부터 첫 map E1까지는8.595–19.665ms다. 단순히 포인터를 넘겨 나중에 읽는 A0는 이 수명과 맞지 않는다. 이 간격을 실기 캡처 누락 횟수로 환산하지 않는다.

A1에서 원본과 descriptor를 FPGA에 보관하면 이 fixture의 필요량은2036–2498B이고 **53개 중52개가 한2KiB bank를 넘는다.** 일반1056셀·최대1023 BG binding·32그룹·64행 상한은6476B다. 기존 bulk4KiB와 ordinary queue1KiB는 모두 사용 중이며 합쳐도 이 직접 보관 형식의 상한보다 작다. 특히 두 bulk bank를 map 보관으로 점유하면 먼저 끝나야 할 tile 공급을 막는다. source 해제를 늦추거나 tile을 멈추는 방법의 비용을0으로 둘 수 없다. A1 전체 구조가 불가능하다는 증명은 아니지만 **현재 저장을 그대로 재사용하는 안은 선택할 수 없다.**

B는 source를 host에서 곧바로 SNES WRAM으로 복사하므로 FPGA에 프레임 사본을 추가하지 않는다. 대신 현재512B source scratch가 단일 read/write 포트인 것을 반영해야 한다. 압축기의 주소 순회·SPI D1 읽기·SNES DMA 읽기를 중재하고, `(generation,token,start,count,CRC)`가 고정된 동안 두 소비자가 같은 block을 읽도록 한다. 원본cell CRC를 현재 wire CRC와 혼동하지 않으며 보관/계산 비용을 추가한다.

## 삭제 예산과 새 제어의 조건

| 기존 경계 | 현재 비용의 범위 | 이번 A/B에서 실제로 제거 가능한가 |
|---|---:|---|
| ARM `map527` / `nes_sink527_early` | 실제 ELF216 /96B | 전체 대체 시 최대312B 함수 범위. fallback이나 선행 callback을 유지하면 전부 삭제할 수 없음 |
| ARM `packet_wire` / `span` | 692 /188B | 일반 명령·새 descriptor에도 필요. 전체 삭제0B |
| ARM `nes_native165_packet` / resident slot / SEAL | 1730 /976 /1348B | 입력·할당·검사·최종 ACK 유지. 전체 삭제0B |
| FPGA source SPI / 그 내부codec | FIT906 LE /324 LE | 포함 관계이며 더하지 않음. D1 압축·원본 복구가 유지되므로 전체 삭제0LE |
| FPGA output SPI endpoint | FIT733 LE, queue1M9K | nonmap·descriptor·credit 유지. 전체 삭제0LE/0M9K |
| FPGA tile bulk / 내부aperture | FIT727 /330 LE,5 /4M9K | 포함 관계. 기존 tile 소유권·두bank DMA를 유지하므로 전체 삭제0LE/0M9K |

이 수치는 선택665 전체 FIT의 entity 범위와 선택666 ELF에서 읽었다. parent-child 자원을 합산하지 않았다. **검증된 순삭제는 ARM0B·FPGA0LE**다. 다음 최소 경계는 source block 완료를 `ARM read 완료 + SNES read 완료`로 바꾸는 제어이며 기존 D1/D2·압축기·출력 queue 본체를 없앨 수 있다고 예산을 잡지 않는다. 여유는 ARM496B, FPGA84LE/1LAB/0M9K, 물리 SNES ROM11B다. SNES 해제 후 본문 여유192B와 물리 ROM11B는 다른 값이다.

B의 가능한 빠른 조회안은WRAM의8192tag×2B lookup과 이전 key 목록2KiB, 원본2112B, 행/CRC/control272B로 **20,816B** 추가다. 아직 주소를 할당하지 않았으며 기존 WRAM 배치와 겹치지 않는지 확인해야 한다. 작은 선형/해시 표는 공간을 줄이지만 검색·손상 검사 비용이 늘어난다. 매 프레임16KiB lookup 전체를 DMA 초기화하면 데이터 전송만6.103ms로 밀집wire 절감4.319ms보다 크다. 이 초기화안은 제외하고 이전 key만 무효화하는 비용을 반드시 포함한다. cold·STOP 뒤에는 전체 초기화·전체 행 복구를 별도 계상한다.

ARM 임시 저장도 공짜로 두지 않는다. 기존 BG key 저장은 BG 완료 뒤 OBJ 검사448B에 재사용되고, 이후 상위4096B에는 raw patch가 들어간다. BG 중 descriptor를 만들 때 이 저장 전체가 비어 있다고 볼 수 없다. 다음 시험은240B 단위 생산 버퍼의 수명과 stack·IRQ 간섭, 원본 map/독립 expected 유지 비용을 포함한다.

필수 완료 순서는 다음과 같다.

1. 원본block seal 뒤 내용·identity 고정. ARM D1과 SNES 수신을 각각 추적한다. SNES 실제 read 순서·길이와 후속ACK를 확인하기 전 D2로 덮어쓰지 않는다.
2. ARM의 다음 입력 선행 수신은 비차단 진행 상태로 반환한다. 이전 표시를 끝내는 ARM이 mirror D2를 기다리고 SNES가 그 ARM의SEAL을 기다리는 순환 대기를 허용하지 않는다. 반대로 SNES mirror 완료만으로 ARM read를 완료 처리하지 않는다.
3. WRAM source와 recipe의identity/CRC/행coverage·slot 범위·독립 ARM expected를 확인한 뒤 비활성 뱅크만 수정한다. sourceCRC와expected를 같은 새 FPGA 변환 결과에서 함께 만들지 않는다.
4. STOP은 양 소비자의 진행을 폐기하고 늦은 read/ACK를 차단한다. 다음 세대는 cold로 복구한다. 저장credit·map소비·실제DMA·표시최종ACK를 구분하고, 이전 표시 이력은 최종ACK까지 보존한다.

현재 Python 참조 시험은 위4단계 제어를 실행한 것이 아니다. 이 제어를 추가했을 때84LE/1LAB에 들어가는지, 앞당긴 D1과새SNES 수신이 기존 첫BG/ROM 허가 구간을 지키는지는 미검증이다.

## 다음 한 단계와 중단 조건

S1의 원본/descriptor 복원·거래 비교와 S2의 교체 경계·소유권·예산표를 작성했다. **전체 비용 통과는 아직 아니다.** 다음은 B를 바로 제품에 연결하는 대신907·911·953·954·955의 실제65816 변환/CRC/행복사·lookup 무효화 커널과 ARM descriptor 생성 비용을 제한 시험한다. ROM 압축 후 전체 링크 비용과WRAM 주소표를 먼저 확인한다. 그다음 source 단일포트·두 소비자 credit의 최소 제어를 가격 매긴다. 실패하면 한 번 결과를 남기고669의 수락 범위·병합·주사선 예산 비교로 복귀한다.

이 단계가 통과하기 전 새 전체 FIT·53화면 시뮬레이션·실기 ZIP을 만들지 않는다. 통과한 한 후보만 원본/공통코드 대조군/적용본의 두 위상으로 연결하며911 마감·951의246선·952≤3VBlank·954/955 무회귀·957 최종대기0회와 밀집 간격/마지막ACK 동시 개선을 요구한다. 물리26.84ms를 이 비용표 비율로 나누지 않는다. 선택본의 실제 표시 간격과마지막ACK는 이번에 변경·재측정하지 않았다.

재현 인자는 `--data probes/nes-delta231/test07`, `--plans probes/nes-seal538/plans01`, `--sender ASCII-Temp/nes-reader661-sender/sender.json`, `--traces ASCII-Temp`, `--arm probes/nes-trial666/arm01/src`, `--board ASCII-Temp/nes-entry665-board01`, `--out analysis/supply670-budget.json`이다. 경로는 실제 환경에 맞춰 절대경로로 전달한다. 분석은ROM을 읽지 않으며 로컬 자료의식별값은JSON에 보존했다. probes/Temp가 clone에 포함된다는 뜻은 아니다.
