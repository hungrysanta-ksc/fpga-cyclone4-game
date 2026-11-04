# 591: 8B 요약·묶음 요청 ARM 실행 — Flash gate 실패

## 판정과 완료 범위

**ARM 실제 수신 경로와 전체 링크까지 구현했지만 제품 예산을 통과하지 못했다.** 최종 후보는214760B로 MMC577보다1852B 크고212992B 한도를1768B 초과한다.590에서 정한 “두 비용 중 하나라도 실패하면 전체 결합 중단” 규칙에 따라 **새 FPGA 구현·Quartus Lite MAP·두 시작 위상/첫BG/최종ACK 결합은 실행하지 않았다.** 해당 수치를 기존 값에서 추정해 채우지 않는다.

완성된 것은 actual ARM의 D0–D4 수신·재사용·복구와 **Python 단일 sealed packet endpoint**다. FPGA와 공동 실행한 결과가 아니다. 최종 표시 ACK/EA runtime은 기존 경로를 유지했으며, 이 수신 시험의 `consumed()` 호출은 이미 표시가 끝났다는 fixture다. 새65816·IRQ·ROM·clock-stop·메뉴 실기 시험이 아니다. MMC577·GBC/save·설치 ZIP·README 상태는 유지한다.

선택: `patch02 / ARM02 / test03 / analysis03`. [검증 수치·해시](../analysis/roles591-verification.json), [교체 도구](../tools/prepare_nes_roles591.py), [실제 수신 코드](../tools/nes_rows591.inc), [ARM 실행 시험](../tools/check_nes_roles591.py), [비용 분석](../tools/analyze_nes_roles591.py).

## 실제로 교체한 것

MMC577의 map repeat/packed4 해석 두 분기, 이전 BEGIN 전체 reset/control, 이전 packet parser를 삭제했다. 새 phase packet 실행기가8B 요약→전체행→nonmap→raw→COMMIT을 처리한다. 이전 map은 기존2112B 배열에 남기고, BEGIN에서는 rows 이후 현재 의미검사/required 상태만 초기화한다. cold 또는 STOP 뒤에는 모든 행을 받아야 유효해진다.

ARM이 각 이전 행에서 실제 CRC32를 계산해 same·left·right를 판정한다. CRC 캐시나 두 번째 map 배열은 없다. 변경 행을 하나의32bit bitmap으로 요청하고, 실제 받는 범위·중복·누락·15bit 값과 fresh map CRC16을 검사한다. map CRC를 통과하기 전에는 required-tag를 공개하지 않는다. 실패하면 같은 source lease에서 전체행 repair를 한 번 요청하며 두 번째 실패는 fail-closed다.

유지한 코드도 비용에 포함했다. nonmap packed/repeat/raster/raw 의미검사,required tag 열거, D1 CRC16,D2 완전 read/retire 확인,D3 PREPARE,최종 ACK/EA runtime을 남겼다. canonical CRC16은 실제 논리 값이 확정될 때 누적하며 raw 전개도 포함한다. source base-valid는 COMMIT 해석만으로 세우지 않고 **최종 D2 뒤 D0 token 진행 확인**까지 끝나야 세운다. source base와 표시 이력은 합치지 않았다.

요청은24B D4와8B D0 확인을 사용한다. epoch/serial/generation/요약 token/bitmap/mode/CRC16을 보낸다. 확인 toggle은 D0의 새bit2다. 기존 reserved-bit 검사도 변경했으며 “기존 D0에 무료 추가”로 취급하지 않았다. 이 형식은 시험용 ARM/모델 계약이며 실제 FPGA command decoder가 구현된 상태가 아니다.

## 590 비용에서 발견한 빠진 소유권 전환

행-END의 D2는 packet 저장소 반환이다. 그 순간 FPGA가 nonmap을 바로 생산하면 ARM의 fresh CRC 실패 뒤 REPAIR 요청보다 nonmap이 먼저 seal될 수 있다. 그러면 repair를 앞에 삽입할 수 없고 현재 phase와 충돌한다.

따라서 source 모델은 행-END 뒤 멈추고 ARM의 **D4 MAP_ACCEPT(mode4) 또는 REPAIR(mode3)**를 기다리도록 고쳤다. 성공 경로에도24B+8B 왕복이 추가된다. 단계 대기 뒤의 추가 D0까지 실제 호출로 계산하면590의dense6.775ms는 **7.121ms**로 바뀐다.590 문서에도 정정 링크를 추가했다. 최초 ARM01은 이 수락 경계 없이 링크 비용만 확인한 중간 산출물로 보존하며 최종 선택이 아니다.

## 실제 링크 비용

| 항목 | MMC577 | ARM591 | 차이 |
|---|---:|---:|---:|
|최종 firmware.stm|212908B|214760B|+1852B|
|212992B 한도|84B 여유|1768B 초과|실패|
|native165 object code|3452B|5248B|+1796B|
|native runtime code|1406B|1414B|+8B|
|planner211 code|3982B|3990B|+8B|
|추가 libgcc popcount helper|0B|40B|+40B|
|BSS|18592B|18592B|0|
|receiver struct|9880B|9920B|+40B|
|native_frames caller stack|31864B|31904B|+40B|

object 차이와 새 helper40B 합이 최종 링크의1852B 증가와 정확히 일치한다. 함수별로 기존 packet1434→2724B,logical_record1112→960B,new request320B,digest76B,canonical52B다. 큰 원인은 새로운 phase/identity/행 완료/복구와 유지된 nonmap 처리의 결합이다. CRC32 표1024B는 원래 링크돼 있어 재사용했다. digest76B나40B helper를 지워도1768B 부족은 해결되지 않는다.

정적 RAM 끝은28744B로 같고,candidate caller/callee/IRQ 전 gap은4928→4888B다. 수신 시험의 관측 stack은704B지만 native_frames caller/실제 IRQ 최대치가 포함된 값은 아니다.40B 새 상태는160B 설계 상한 안에 들었지만 Flash gate가 실패했다. 보드 LE/M9K 비용은 **미측정**이다. “추가 FPGA 비용0”이 아니다.

## 기능 검증

전체 링크된 ARM02 ELF를 사용했다. input source는 단일 sealed block, 완전 D1 read 뒤 D2, 단계 요청을 수락할 때만 다음 응답을 생산하는 모델이다. 모델 내부의 fixture packet 목록을4packet producer ring으로 간주하지 않았다.

- 905–957 연속53입력에서 map/row/OBJ/exception/raster/palette/raw 전부 원본과 정확히 일치했다. token65520 시작의16bit wrap도 포함한다. HELLO/REQUEST/MAP_ACCEPT와 D0/D1/D2/D3를 실제 ARM 함수가 발행했다.
- 18조건:1회 repair 성공,2회 CRC 실패 차단,wire CRC·request 확인·D2 확인 오류,잘못된 값·인덱스·중복·누락 행,META/END CRC 오류,수신0/1/2/4회 뒤 reset+cold 복구,거짓 요약의 fresh CRC 실패/repair,retained RAM 손상 뒤 전체행 요청과 synthetic right-shift를 확인했다.
- canonical CRC·값 의미·required coverage를 통과하기 전 실패 상태가 source base를 유효하게 만들지 않았다. 이전 source identity를 표시 ACK 이력으로 사용하지 않았다.

Questa/FPGA가 필요한 clock-stop·실제 CDC,대기 중 실제 STOP pin,IRQ 취소·65816 최종표시·메뉴는 이번 시험 범위 밖이다. 같은 코드의 test01은53입력/15조건,test02는 baseline ARM53입력과 거짓 요약/retained RAM 두 조건을 추가했다. 최종test03은 capture에 없는 right-shift와 모든 정상 warm bitmap의 독립적인 값 비교 oracle를 추가했다. 기능 수정 없는 불필요한 전체 FIT/라이선스 재시험은 하지 않았다.

## 처리 시간: 실제 명령·호출을 이용한 제한 비교

같은 capture에서 MMC577와591의 **실제 ARM 수신 함수**를 실행했다. FPGA/driver callback은 모델이므로 명령 수를84MHz의CPI1/2로 바꾼 값은 민감도다. 새 D4 driver 비용은 기존D3 평균을 대입했다. 실제 Flash wait·IRQ·ROM·query/CRC 생산·첫 BG·SNES 표시 시간은 아니다.

| 입력 구간 |577 입력 I/O ms|591 입력 I/O ms|577 ARM 명령|591 ARM 명령|CPI2 입력 합 577→591 ms|
|---|---:|---:|---:|---:|---:|
|cold905|13.223|12.625|288377|377344|20.089→21.609|
|warm907–957 평균|13.294|6.866|289443|378033|20.186→15.866|
|dense951–955 평균|14.066|7.121|298016|383031|21.162→16.241|

warm/dense는 이 제한된 입력 합에서4.319/4.921ms의 가능성이 있지만 **cold는1.520ms 회귀**한다. raw 전송만 줄었다고 전체가 항상 빨라지는 것이 아니다. 밀집 입력만CPI2에서16.241ms이고 기존 비입력 항목59.983/59.989ms가 별도로 남는다. 전체60Hz·첫 BG·마지막 ACK 개선을 증명하지 않는다.

새 회로/타이밍이 없으므로 두 시작 위상 표는 작성하지 않았다. 기존 두 위상의 결과를 새 후보 결과처럼 재사용하지 않는다. 마지막 ARM 수신까지 개선 가능성이 있어도 Flash/회로 예산을 함께 통과하지 못하면 전달본으로 만들 수 없다.

## 다음 작업과 중단선

**이 혼합 phase parser의 FPGA 확장·전체 일정·실기 패키지는 중단한다.** 새 요청/cold/repair/독립 CRC가 가진 실제 비용을 다음 구조의 필수 항목으로 보존한다. MAP_ACCEPT와 단계 D0를 다시 누락하지 않는다.

다음은 기존 record/nonmap 제어와 새 phase/identity 완료 제어를 하나의 수신 문법으로 대체할 수 있는지, 실제 삭제 가능한 함수/분기와 전체 Flash 상한을 먼저 확정하는 일이다. 이번 전체 parser2724B에 또 adapter를 붙이지 않는다. 기준은 완성 펌웨어212992B 이하이며, 기존1112B 의미검사·request320B를 무료 삭제로 계산하지 않는다. 이미 불합격한589범용FPGA·591혼합parser의 opcode/카운터/CRC table/seed 미세 조정으로 돌아가지 않는다.

실제 삭제 예산이 없으면 새 ARM/FPGA 원형을 시작하지 않고 지원 범위·코드 배치의 구조적 선택으로 되돌린다. 제품은MMC577이다. 전체 시간과 회로가 함께 개선됐다는 판정은 아직 없다.

재현은 `prepare_nes_roles591.py --src <pinned577/src> --out <newpatch>`→격리 전체 source 복사/3파일 적용→기존 `build_nes_trial577.ps1`→`check_nes_roles591.py`→`analyze_nes_roles591.py` 순서다. 각 도구의 `--help`에 필수 경로가 있다. private `probes/nes-roles591/analysis03/evidence.private.zip`에는patch·ELF/object·최종 이미지·build log·시험결과·도구를 보존했다. ROM/capture/license/바이너리는 공개 Git에 넣지 않는다. clean-clone 전체 재현 완료를 주장하지 않는다.
