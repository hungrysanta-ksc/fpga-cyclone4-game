# 582: section 입력·map 소비 ABI의 전체 예산 비교

PR151에서 [581 본문 조사](nes-body581-results.ko.md)를 바탕으로 세 가지 구조의 구체적인 전송 형식과 자원·소유권 경계를 비교했다. Python 참조 형식으로 같은53개 입력과 두 위상의 명령 비용을 계산했다. **제품 구현 후보는 아직 선정하지 않는다.** 평균 wire만 통과한 안도 호출 비용과 느린 개별 화면을 포함하면 전체60Hz 예산을 입증하지 못했다.

MMC577 FW/RTL/65816·실기 기준·기존 FIT/STA는 유지한다. 이번 참조 코드는 제품 ABI와 호환되지 않으며 보드에 적용하지 않았다. 새 Questa/Mesen 공동 실행·합성·전달본은 없다.

## 비교한 구조

| 안 | 입력 | map 출력 | 나머지 출력 |
|---|---|---|---|
| A | 공통 section block, 전체 내용 전송 | 대상 뱅크 stale를8B 단위로 전송 | 현재 palette/OAM/HDMA 유지 |
| B | A + map/row의 정확한 base 비교·변경 마스크 | A와 동일 | 현재 유지 |
| C | B와 동일 | A와 동일 | 대상 뱅크와 같은 packet을 생략하고 범위·CRC·base 선언 추가 |

입력 변경만/출력 변경만의 작은 후보를 다시 배포하려는 비교가 아니다. A/B/C는 같은 새 형식에서 필요한 전체 교체 범위를 구분하기 위한 **참조 예산**이다. 이들의 세부 opcode나 합성 seed를 바꿔 반복하지 않는다.

## 참조 입력 형식

- BEGIN32B: magic/version/flags4, epoch/serial/base serial12, generation2,6개 section count12,patch count/reserved2.
- 각 block의6B header: section1,codec1,start unit2,count2. 값의 폭은 map2,row1,object7,exception4,raster7,palette1,raw1B다. geometry의8B object/raster 저장 폭과 wire 폭을 혼동하지 않는다.
- map/row는 최대32unit literal 또는 changed mask+값이다. mask는ceil(count/8)B이며 같은 값도 mask0을 명시해 전체 주소 coverage를 유지한다. 그 외 section은 literal/repeat/raster-next와 전체 복구 경로를 가진다.
- META_END8B, END8B, COMMIT8B를 별도로 닫는다. META_END와END의 canonical CRC16은 재사용한 값까지 포함해야 한다. 현재 required bitmap→raw 전환, 전체 geometry 의미검사·필요 tile 열거는 삭제하지 않는다.
- 256B packet 안에서 block을 분할하지 않는다. D1 command/CRC3B + D2 8B + D0 한 번8B를 **packet마다** 넣고 D3 8B도 계산한다. CRC16은 기존과 같은 전송 오류 검사이며 인증이나 충돌 없는 동등성 판정이 아니다. base 생략 여부는 정확한 값 비교로 결정한다.

53개 입력에서 literal/base 양쪽 복원이 canonical과 일치했다. raw0–7과 최대 section 크기의 참조 복원16조건, map 복원1조건, 누락·중복·잘못된 mask/base/CRC10조건도 확인했다. 이는 참조 형식의 검사이며 ARM 의미검사, STOP/reset/CDC나 실제65816 DMA를 검증한 결과는 아니다.

참조 BEGIN은 epoch1과 연속serial을 사용한다. 실제 FPGA의 generation/epoch 및 ARM 표시serial을 어떤 handshake에서 결합할지, reset 뒤 늦은 응답을 어떻게 차단할지는 추가 계약이다.32B에 필드를 예약한 것만으로 현재17bit PREPARED mailbox가 새 base 공개를 보장한다고 간주하지 않는다.

## map 소비와 독립 검사 경계

현재 `map_word185`의64B dirty와 양쪽 `map_stale` 누적을8B 그룹으로 바꾼다고 가정했다. 새 입력과 바로 전 표시의 변화는 두 뱅크에 누적하고 대상 뱅크의 최종ACK 뒤에만 소거한다. **현재 값과 목적지의 정확한 byte oracle만 비교해서 불필요한 stale를 임의 삭제하지 않았다.**

map record는 row1B +8group mask1B +set bit마다8B다. 여러 row를240B payload에 묶고 기존16B E1 header와3B command/CRC를 유지한다. 별도70B prelude에는64개 expected mask,actual-read CRC16,대상 뱅크의 이전 serial을 둔다. 기존 BEGIN의epoch/generation/대상 identity 및 SEAL168B·tile used 정보도 유지한다.

소비자는 expected mask·중복·범위·누락을 검사하고 실제 수신/소비 바이트에서CRC를 계산해야 한다. unchanged 영역은 최종ACK한 이력만 사용할 수 있다. cold/STOP/부분전송/identity 불일치에서는 전체512group 복구를 요구한다. **유지된 데이터 손상 검출과 CRC 저장·갱신 비용은 아직 구현/검증되지 않았으므로 독립 검사 gate는 미통과다.** 과거514의 생략 바이트 전체 재순회로 이 공백을 메우지 않는다.

또한 prelude는 map이 완전히 확정된 뒤 만들 수 있다. 기존 첫map 선행 공급을 지연시킬 위험을 별도 비용으로 남겼다. 원래 발행 시각에 새 prelude가 공짜로 준비된다고 가정하지 않는다.

| map 평균 | 현재 전송 B | 새 wire B(검사 prelude 포함) | 새 DMA B | 새64B 이하 DMA run |
|---|---:|---:|---:|---:|
| 초기 두 뱅크 | 4452.0 | 4731.0 | 4096.0 | 64.0 |
| 초기 두 화면 이후51개 | 1817.86 | 402.86 | 231.69 | 26.16 |
| 밀집951–955 | 1846.4 | 463.8 | 284.8 | 27.6 |

전송/DMA 바이트 감소와 setup 횟수 감소는 같지 않다. 실제65816 검사·DMA setup·VBlank 비용을 위 바이트로 환산하지 않는다.

## C의 추가 이력도 비용을 낸다

palette/OAM/HDMA에서 같은 **전체 packet**만 생략한다. 동일 patch layout과 대상 뱅크를 요구하고, 인접 생략 범위를 합친 뒤8B base/layout/count header +범위당7B(section,start,length,CRC16)를 보내는 선언을 추가했다. 선언도 E1 header/CRC와 큐 응답 비용을 낸다.

밀집 구간에는4–6개 범위 선언으로55–69B가 추가되며 재사용 대상은2359–2551B다. 이 바이트의 이력을 어떻게 저렴하게 검사할지는 미해결이다. 선언에CRC를 넣은 사실만으로 소비자가 이전 RAM 손상을 검출하거나 stale 이력을 거절했다고 주장하지 않는다. 현재 제품에 모든 section의 신뢰할 수 있는 cache가 이미 있다고 가정하지도 않는다.

생략 여부를 판단할 **ARM 생산자 측 이력**도 필요하다. 전체 section을 양쪽 뱅크별로 단순 복사하면 현재 fixture에서는5620B, 최대512+544+3418B를 두 벌 저장하면8948B다. 이는 이번에 확보한 RAM이 아니다. 입력 identity나 더 작은 표현으로 정확한 재사용을 증명할 수 있는지와 실제 ARM workspace/stack 여유를 확인하기 전까지 C의 저장 예산도 미통과다.

## 조회·호출 비용을 포함한 결과

아래는 밀집5개 평균이다. 같은 입력/출력 작업에서 E9/EA·observer와 **기존 E8 횟수**를 유지했다. E0는 새 출력 네 packet마다 한 번+초기/BEGIN/SEAL 여유3회를 가정한 낙관적 시나리오다. 현재 map의3credit 여유 정책·barrier와 실제 소비 일정에서 이 횟수가 가능한지는 미검증이다. 관측된 E0 횟수를 유지한 시나리오도 JSON에 별도로 저장했다.

| 안 | wire ms 위상1/2 | wire+드라이버 평균비용 ms 위상1/2 | 판정 |
|---|---:|---:|---|
| A | 18.799 /18.821 | 25.092 /25.124 | 전송부터 미달 |
| B | 14.133 /14.155 | 19.502 /19.533 |12ms·전체예산 미달 |
| C | 11.807 /11.829 | **16.454 /16.485** | 평균wire만 통과; 전체 gate 미통과 |

드라이버 항은 기존503의 opcode별 평균 추가 비용 약48–50µs/호출을 새 호출 수에 적용한 **직렬 I/O 민감도**다. 실제 새 드라이버 계측이나 새로운 전체 표시 시간은 아니다. 원래 평균에 포함된IRQ를 또 더하지 않았다. observer 추가 overhead,새 ARM 복원/계획,독립 검사,ROM 공급,남은 DMA·VBlank는 아직 해결하지 못했다. 모든 과거 실기 DWT 항을 이 표에 다시 더하지도 않는다.

C는 평균95.0/95.2 SPI 호출로 드라이버 항만4.647/4.656ms다.16.667ms에서 남는 공간은0.213/0.181ms뿐이다. 초기 두 화면 이후51개 평균은 wire8.489ms/I/O11.468ms(위상1)지만 평균만으로 선정할 수 없다.

| C의 밀집 개별 화면 | wire ms 위상1/2 | 직렬 I/O 시나리오 ms 위상1/2 |
|---|---:|---:|
| 951 | 12.715 /12.702 | 16.653 /16.593 |
| 952 | 10.191 /10.313 | 14.637 /14.855 |
| 953 | 10.182 /10.133 | 15.103 /15.054 |
| 954 | **15.326 /15.253** | **20.813 /20.643** |
| 955 | 10.621 /10.743 | 15.063 /15.281 |

954의B/C 입력 wire는2429B로952의897B보다 크다. E8도954에서900B이며, 소비가 빨라지면 조회 횟수가 어떻게 바뀌는지는 새 실제 일정에서 확인해야 한다. 따라서 이 표를 모든 새 구조의 불가능성으로 확대하지 않는다. 반대로 E8을0으로 채우거나 평균만 보고60Hz가 된다고 하지 않는다. cold 두 뱅크는C에서도 약43ms wire로 남으며 warm와 분리한다.

## RAM·클록·삭제 예산

선택 보드에서 exporter는NES 클록,`nes_native_spi165`는host 클록이다. 현재96bit record mailbox를 없앤다고 가정하지 않는다. 새 block의 payload는 예를 들어 generation16/count4/flags12/data64의96bit 조각으로 넘길 수 있지만, 이는 **제안된 새 CDC 데이터 계약**이며576의 timing/safety 검증이 자동으로 승계되지 않는다.

| 저장/제어 | 필요한 소유권 | 예산·미해결 |
|---|---|---|
| map/row base | NES 실행기가 query 응답과 정확히 비교. BEGIN에서 base 유효성을 잠정 해제하고 실패/STOP 시cold. 성공 표시ACK/EA 뒤에만 다음 base 공개 | 최대2336B,3M9K 이상. 나머지 공간에약128B block scratch·identity를 넣는 배치 제안. 전체 소스 snapshot7533B는남은5M9K에 안 들어감 |
| base/scratch RAM 포트 | old 값 read 완료 뒤 해당 위치 write. changed값 scratch와 base write는 충돌 시순차. EMIT 동안 scratch read→기존 mailbox→host packet RAM | 별도 RAM 추가 시잔여5→2블록. 비교기·주소/phase 제어·CDC 비용 미합성. 추가 source 조회나 RAM cycle을0으로 두지 않음 |
| ARM source | map/row 배열을 유지하되 receiver metadata/bitmap·raw lifetime은 분리. 모든 geometry 의미검사·required tile 열거·canonicalCRC 유지 | BEGIN의 전체reset을그대로둘수없음. 추가 fullcopy는가정하지않지만 retained base 무효화/검사코드가필요 |
| ARM map masks | current dirty64B +target stale128B +upload64B의상한 배치 | 기존8+16+8=32B 대비 최대+224B. 이식 시필드 공유/스택은 별도 확인 |
| SNES map | 기존map WRAM/VRAM과inactive bank를유지. mask64B·CRC/진행·base identity가추가됨 | 기존row coverage와공유할범위,레코드보관/DMA run queue,이력손상검사비용 미확정 |
| 기타section 이력 | 공개된대상뱅크/base/layout로범위검증 | 현재paired WRAM의수명/포트와검사값보관을증명해야하며분석용cache를무료RAM으로합산하지않음 |

기존 exporter의 map record pack,host SPI width/position/tag/generation 해석,ARM record decode,64B map dirty/stale·행 소비를 함께 교체하는 범위다. source lease/query·watchdog·COMMIT/ABORT,token/packetCRC,필요tile 검사,최종ACK·VBlank·메뉴는 남는다.

581에서 고정한 함수 전체 크기를 순삭제로 계산하지 않았다. **확정된 Flash/LE 순삭제는0**,현재 여유는Flash84B/LE148/M9K5다. 새3M9K가 산술적으로 들어가는 것과 전체 FIT·STA가 되는 것은 다르다. 제품 code/RTL을 만들기 전에 유지 검사와 새 control의 순예산을 확보해야 한다.

## R2 판정과 다음 순서

**A/B/C 모두 R3 제품 구현으로 승격하지 않는다.** C는 후보 형식의 좋은 평균 전송량을 확인했지만 개별 밀집 화면,호출 비용,유지 데이터 검사·RAM 포트·Flash/LE gate가 미통과다. 이 설계의 작은 packet 크기·poll 주기 변형은 반복하지 않는다.

다음 R2는 두 원인을 함께 닫는 한 가지 설계다.

1. 951/954의 큰 입력 변화가 map의 실제 값 변화인지, 기존 base의 행/열 좌표 변화인지 확인하고 **유효한 base 주소를 명시한 block**으로 전송을 줄일 수 있는지 비교한다. 정확한 비교·cold/STOP·포트 소유권을 유지하고 hash만으로 생략하지 않는다.
2. 같은 ABI에 소비 완료/credit/plan 진행 응답을 결합해 **독립 D0/D2/E0/E8 호출을 실제로 대체**할 범위를 정한다. busy poll을 생략하거나 이전 응답을 무조건 재사용하는 변경이 아니다. 응답 snapshot 시각·세대·CRC·취소 후 늦은 완료를 검사하고 full-duplex 응답의 padding/바이트도 계산한다.
3. 그 뒤 필요한 작은 ARM/65816 커널·RAM 포트의 실측 비용을 제시한다. 기존53화면 전체와 FIT를 먼저 반복하지 않는다. 검증 가능한 전체 예산이 없으면 지원 범위/역할을 재검토하고 미달을 명시한다.

이는60fps 달성 보장이 아니다. 입력과 출력의 형식을 줄여도 현재95회 수준의 SPI 호출 및 처리 비용이 남는다는 결과로 설계 범위를 수정한 것이다. 실기577·독립 검사·STOP·최종 ACK·메뉴 복귀는 변경 없이 보존한다.

## 재현

```powershell
python tools/check_nes_abi582.py
python tools/nes_abi582.py --data ../probes/nes-delta231/test07 --capture ../probes/nes-output489/audit01 --traces <원본-Temp> --out <새-폴더>
```

[참조 코드](../tools/nes_abi582.py) · [범위 검사](../tools/check_nes_abi582.py) · [예산 JSON](../analysis/abi582-verification.json) · [검사 결과](../analysis/abi582-guards.json)

로컬 `probes/nes-abi582/reference01`은A/B,02는C의범위선언추가,선택03은최대값/초과화면/호출별driver항까지포함한다. guards01은17정상/10거절조건통과다. 전부호스트참조시험이며새실기/기능/합성통과로집계하지않는다.
