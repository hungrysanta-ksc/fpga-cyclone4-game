# NES 671 · 실제 증분 생산·65816 복원 비용 판정

**670 B의 이번 커널은 기각하고 MMC666을 유지한다.** 행을 먼저 보낼 수 있는 형식은 만들었지만, SNES에 원본 map 변환과 소프트웨어 독립 CRC를 맡기는 계산 비용이 전송 절감을 크게 넘었다. 전체 제품 연결·새 RTL·FIT·전달본을 만들지 않는다. 이것은 모든 직접 공급 구조의 불가능 증명이 아니라, 이번 역할 배치와 구현의 비용 게이트 실패다.

## 실제 실행한 범위

[행 생산기 C](../tools/nes_supply671.c), [ARM·65816 커널 시험](../tools/probe_nes_supply671.py), [전체 ARM 자원 링크 준비](../tools/prepare_nes_supply671.py), [비용·소유권 분석](../tools/analyze_nes_supply671.py), [검증 JSON](../analysis/supply671-verification.json)을 보존했다.

905/906 cold,907/911,951–955/957의 같은 원본·map·기존 E1 행 순서를 사용했다. ARM은 실제 전체 링크 ELF의 `recipe671`을 Cortex-M4에서 실행했다. 128B slot 발행 bitmap으로 같은 프레임의 binding 중복을 없앴다. 각 행은8B header(row/source group/column/epoch/count/독립CRC)와 새 tag/slot 쌍4B씩으로 생산한다. 한 행 최대140B라240B payload 한도 안이다. 각 행마다 기존 E1 envelope19B를 포함했다.

ARM은 이미 확정된 현재 map과 compact 원본을 함께 읽는다. 기존 planner·slot 배정·독립 expected map 계산은 그대로 필요하다. 이번 시험은 원래의 행 발행 순서에서 커널을 독립 호출한 것이다. 실제 planner callback·SPI enqueue·IRQ와 새 생산기가 연결됐다는 뜻은 아니다. ARM의 row CRC는 lookup table 없이 CCITT 동등식을 사용했고, 65816은 별도512B table 방식으로 검사했다.

65816은 Mesen에서 실제 명령을 실행했다. source aperture를 통해12개 block의1914B를 네이티브 DMA로 WRAM에 받고 CRC를 계산했다. tag lookup 갱신, 직전 표시 뱅크의 행 복사,33열/64열 주소 변환, palette epoch/slot 조합, 행 전체64B의 독립 CRC를 실행했다. 기존4096B map에서 발췌한 행과 바이트까지 대조했다. header/identity의 전달·원본 aperture는 fixture이며 실제 FPGA 연결은 아니다. CRC table의 초기 WRAM 설치도 fixture이며 그 설치 시간은 미포함이다. 코드 fetch는 slow LoROM, 선택본은 WRAM이며 둘 다8master-clock 접근 조건이다. 설정·분기·refresh를 포함한 실제 CPU 시간이고, 다른 제품 작업·IRQ/공유 ROM 경쟁은 없다.

선택 `test06`은 정상 및 fault 복구509개 CPU command를 통과했다. 원본CRC 불일치, 행CRC 불일치, STOP 진입/64B 검사 도중/초기화 도중, fault 뒤 행·입력 재사용 차단, cold 뒤 입력 재수신을 포함한다. STOP/fault가 발생하면 커널의 유효 표시를 지워 cold 이전의 stale 행 실행을 거부한다. 이것은 제한 커널의 동작이며 새 최종 ACK·메뉴 복귀의 종단 시험은 아니다.

## 비용 결과

| 세대 | 기존 map E1 | 행별 새 E1 | wire 절감 | ARM 생산 CPI2 환산 | SNES 원본 DMA·검사 | SNES 행 복원·검사 |
|---|---:|---:|---:|---:|---:|---:|
| 905/906 각각 | 4452B | 2052B | 7.314ms | 1.853ms | 42.58ms | 177.80ms |
| 907 | 524B | 261B | 0.802ms | 0.235ms | 42.58ms | 21.79ms |
| 911 | 844B | 472B | 1.134ms | 0.370ms | 42.58ms | 35.36ms |
| 951 | 1982B | 964B | 3.102ms | 0.860ms | 42.58ms | 81.64ms |
| 952 | 2110B | 1054B | 3.218ms | 0.922ms | 42.58ms | 87.60ms |
| 953 | 927B | 595B | 1.012ms | 0.414ms | 42.58ms | 39.44ms |
| 954 | 2148B | 1094B | 3.212ms | 0.941ms | 42.59ms | 88.99ms |
| 955 | 2065B | 1003B | 3.237ms | 0.900ms | 42.58ms | 85.17ms |
| 957 | 2257B | 1116B | 3.477ms | 0.998ms | 42.58ms | 94.33ms |

670의954/955 일괄498/428B는 증분 발행 조건에서1094/1003B가 됐다. 기존 D1과 조회 거래를 없앤 것은0B/0회다. 추가 응답·header 검사 비용은 아직 미포함이다. ARM 수치는 실제 명령 수에CPI2를 적용한 모델이며 물리 사이클 측정이 아니다.

SNES source 수신의 검사 전 구간은1.43ms, CRC·완료 반환 구간은41.15ms다. 954 행 처리88.99ms 중 검사 전46.73ms, 행CRC·반환42.26ms다. 955는44.32+40.85ms다. 따라서 CRC 루프만 줄이는 것으로도 이번 역할 배치를 채택할 수 없다. 검사 전 구간에는 행복사·binding 갱신·주소/slot 변환·제어가 함께 포함되므로 이를 전부 순수 변환 시간이라고 부르지 않는다.

실행 전에 가정한 `1914B DMA≈0.713ms`는 데이터 구간만의 값이었다. setup·소프트웨어 검증을 포함하면 전혀 다른 비용이다. 반대로 현재 MMC666의 같은 map load→ACK는954 약6.63–6.68ms,955 약6.12–6.20ms다. SPI 발행과 겹치는 이 기존 비용과 새 SNES 비용을 wire 절감에 단순 가감해 FPS를 만들지 않는다. 새 커널의 SNES 직렬 서비스 자체가 두 위상에서 지켜야 할3 VBlank 처리량보다 크므로, 예산 실패를 확인한 뒤 전체 일정 재생으로 진행하지 않았다.

cold lookup 전체 CPU 초기화는72.06ms, 정상 warm의 이전 key만 제거하는 비용은0.21–0.73ms다. cold 전체 초기화는 별도 DMA 등으로 줄일 수 있으나 steady source·행 처리 실패를 해소하지 못한다. 이 cold 구현을 최적 상한으로 주장하지 않는다. warm/원본/행/ARM 시간을 더한 JSON 값은 직렬 민감도이며 실제 종단 지연이 아니다.

## source RAM과 두 소비자의 완료

실제 DMA read1914회/프레임의 시각을 기록했다. 84MHz 포트에서 SNES read를 우선하고 SPI read를1tick 미루는 **명시적 중재 모델**을256개 상대 오프셋으로 검사했다. 최소 SNES 간격31host tick, 최대23회 SPI 충돌(합계0.274µs)이었다. sealed block 동안 압축기/다음 block이 쓰지 않는 조건이다. 이는 새 RTL·CDC·실제 SPI serializer의 측정치가 아니다. RAM 주소 mux·응답 레지스터·보드 타이밍 및 면적은 아직 검증되지 않았다.

완료 정책은 둘로 구분했다.

1. **CRC까지 source RAM을 붙잡는 정책:** 한 block의 SNES 검사가 끝나야 다음 block을 만들면 비용이 누적된다. 기존 D1 시작 시각을 수신 가능 시각으로 놓은 반사실 모델에서954 마지막 map credit은두 위상 모두30.49ms,955는32.44/31.88ms 늦어진다. 이는 실제 전체 일정 재생이나 불가피한 지연이 아니다.
2. **복사 뒤 저장 credit만 반환하는 정책:** ARM D2와 SNES의 순서대로 완료한 실제 read·identity ACK를 모두 확인하면 source 저장은 재사용할 수 있다. CRC·coverage는 불변 WRAM 사본에서 계속 검사하고, 그 결과와 실제 DMA·VBlank 공개 전에는 최종 ACK를 허용하지 않는다. 다음 입력이 이전 source 사용 종료 전에 도착하는 현재 일정에서는 원본2112B 저장 두 벌과 각각의 generation/token 소유권이 필요하다. CRC 검사를 뒤로 미뤄도 같은 SNES의 총 계산량은 사라지지 않는다.

소유권 모델45개 거부 조건에서 ARM/SNES 완료 순서 교환, 부분 read의 조기 ACK, 사용 중 load, 초과 read, STOP 뒤 같은 generation의 늦은 read/ACK를 검사했다. STOP은 epoch를 바꾸어 저장 identity를 폐기한다. 이 모델은 RTL 구현의 대체 증명이 아니다. 실제 ARM은 pending 응답 뒤 이전 출력·credit·STOP을 계속 처리해야 한다. ARM이 mirror 완료를 기다리는 동안 SNES가 이전 SEAL을 기다리는 순환 대기는 금지한다.

## Flash·RAM·ROM 예산

- 새 C 함수를 유지한 실제 **전체 ARM 자원 링크**는212748B로MMC666보다252B 증가, 여유244B다. 함수254B, 관측 stack28B다. data10040/BSS19544B는 그대로다. 기존 함수들을 삭제하지 않았으며 제품 callback도 연결하지 않았다. caller의 sent128B·packet140B·input32B =300B는 아직 제품 컨텍스트에 할당하지 않은 추가 저장이다. 해당 저장과 IRQ/전체 call-chain stack이 포함된 최종 RAM 통과가 아니다.
- SNES 커널730B에는 시험 dispatcher/entry도 들어 있다. CRC table512B가 별도다. 기존 body에 그대로 붙여 같은 compressor를 적용한 저장 민감도는5960B로5056B 영역을904B 초과한다. 이것은 통합 ROM의 순증·최소 부족량이 아니다. 시험 dispatcher 제거·기존 decoder 대체·주소 relocation·실제 boot linkage가 미구현이다. 기존 물리 ROM 여유11B 안에 들어갔다고 할 수 없다.
- WRAM은 tag lookup16384B, 이전 key2048B, CRC table512B, descriptor140B에 더해 중첩 입력용 원본4224B가 필요하다. 독립 source/검사/행/owner 문맥도 필요하다. 시험 주소를 제품의 빈 주소로 간주하지 않았고 실제 allocator/주소 충돌 검증은 진행하지 않았다.
- FPGA는 변경하지 않았다. 실제 기존 source/queue/plan 본체를 삭제한 비용은0LE다. 새 mux/완료 제어의84LE·1LAB 내 수용 여부는 미검증이다. 시간 게이트가 실패했으므로 전체 Lite FIT·STA를 반복하지 않았다. MMC666의 선택 산출물과 기존 FIT/STA 근거를 유지한다.

## 판정과 다음 작업

현재 순수 map 전송을 없애기 위해 SNES로 tag 변환·행CRC를 옮기는 **이번 B 커널은 보류 목록에 넣는다.** 같은 LUT/CRC 루프의 사소한 변형이나 보드 FIT로 성공을 찾지 않는다. 재검토하려면 새 독립 검사 경계와 실제로 대체할 코드/회로를 포함한 다른 역할 배치의 근거가 필요하다. 독립 검사를 생략해서 통과시키지 않는다.

670의 중단 조건에 따라 MMC666의 수락 범위·명령 병합·주사선 예산 비교로 복귀한다. 다음 한 단계는954·957에서 이미 수락/검사된 map 행과 뒤따르는 작은 tile/ordinary 명령의 준비 시각을 묶고, **기존 CPU 변환과 검사를 유지한 채** 한 번에 DMA할 수 있는 확정 범위를 비교하는 것이다. 668 일괄 drain·단독 탐색은 반복하지 않는다. 911 마감·951의246선·952≤3VBlank·954/955 무회귀·957 최종대기0회, 두 위상의 밀집 간격·마지막 ACK 동시 개선을 유지한다. STOP·최종 ACK·캡처 회복·메뉴/base 복귀 제품 경로에는 변경이 없다.

## 재현·보존 범위

선택은 `probes/nes-supply671/arm01` 전체 ARM과 ASCII Temp `nes-supply671-test06`이다. raw fixture는 `probes/nes-delta231/test07`, 기존 일정은 ASCII Temp `nes-entry665-a1/a2`, 송신기는 `nes-reader661-sender/sender.json`이다. 이 로컬 자료가 Git clone에 포함된다는 뜻은 아니다. 입력/ELF/ROM/CPU/read 시각 hash를 검증 JSON에 보존했다.

1. `prepare_nes_supply671.py <trial666/arm01> <새 ARM 디렉터리>` 후 `build_nes_trial577.ps1 -SourceRoot <새 ARM 디렉터리>`로 자원 링크한다.
2. `probe_nes_supply671.py --out <새 ASCII 경로> --traces <ASCII Temp> --data <delta231/test07> --linked-arm <ARM/src/obj-nes-100/sd2snes.elf>`로 명령을 실행한다.
3. `analyze_nes_supply671.py --kernel <커널 출력> --arm <ARM 디렉터리> --traces <ASCII Temp> --out <검증 JSON>`으로 분석한다.

test01의 sandbox DLL 실행 오류, test02의 초기 ROM header 길이/비ASCII 실행 실패, test03/04/05의 중간 결과를 보존했다. test06은 fault 재준비와 정상 warm 측정을 분리했다. 새 Questa 라이선스나 시뮬레이션 좌석은 사용하지 않았다. 새 설치본·실기 FPS·종단 메뉴 복귀 성공을 주장하지 않는다.
