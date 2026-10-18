# NES247: ROM 확대 허용 후 저장 구조와 실제 수신 시간

2026-10-18, PR128. **사용자 목표는60프레임이며4KiB 유지는 필수 조건이 아니다.** 코드 크기 때문에 처리가 비효율적이면 확대를 검토한다. 이전4398B 소비기는 “현재4KiB 유지 후보” 판정을 이력으로 보존하고, 이번에는 동일 바이너리를 실행했다. 저장 공간 확대 가능성을 확인했지만 현재 디코더의 처리시간은 충분하지 않아 P2 제품 후보는 미선정이다.

[공개 검증](../analysis/maskrun247-verification.json) · [71 frame 표](../analysis/maskrun247-frames.csv) · [이전 통합 경계](nes-maskboundary247-contract.ko.md).

## 저장 공간은 전체 자원과 함께 선택

같은 Cyclone IV E/Quartus 조건에서 실제 bus 전체를 standalone MAP했다.4KiB는 기존3903B 소비기,8/5KiB는 같은4398B 소비기를 담는다.5KiB는4096+1024 동기 ROM으로 나누고 header/vector를 마지막64B에 둔다. 주소 tag와 읽기 지연 단계를 유지했다.

|구성|MAP LE|조합/FF|ROM bits|추론 배열|
|---|---:|---:|---:|---|
|기존4KiB|253|101/157|32768|4096×8|
|직접8KiB|248|96/157|65536|8192×8|
|분할5KiB|249|97/158|40960|4096×8+1024×8|

이 수치는 standalone MAP이며 보드 LE 절감량이나 배치·타이밍 여유가 아니다. M9K ROM 추론을 확인했고 ROM write 핀의 기본0 관련 경고를 보존했다. 전체 보드 FIT는 실행하지 않았다.

기존240 FIT 보고서는 프로그램 ROM4M9K와 전체54/56M9K를 기록했지만240은 LE/LAB 부족으로 미배치다. 위 배열 형상에 따른 용량 계산에서는5KiB가1블록 추가로55/56, 직접8KiB가4블록 추가로58/56이 된다. **이는 전체 재합성 결과가 아니며1블록 여유로 mapper·새source까지 승인하지 않는다.** 생산224/227의47M9K와 미래source가 들어간240의54M9K도 혼동하지 않는다.

5KiB 본문 수용량은4960B여서 현재4398B를 담고562B가 남는다.5KiB를 새 절대 한도로 삼지는 않는다. 필요하면6/8KiB나 다른 적재 구조를 전체 비용으로 비교한다. 프로그램은 부팅 때 WRAM으로 복사하므로 저장 ROM 증대가 정상 프레임마다 같은 크기의 전송을 추가하는 구조는 아니다.

실제5/8KiB bus RTL의 읽기33,029개(LoROM 전체32,768주소+packet256+control4+확장 경계1)와 raw read/reset/inactive/write 배제4조건을 비교했다. 모든 vector·빈 영역·확장 영역이 같은 프로그램을 반환했다. 이는 ROM bus 기능 시험이며 보드 IO/STA 승인은 아니다.

외부 PSRAM 재사용은 검토 대상으로 유지한다. 현재 보드에서는 loader/CHECK/RUN이 단일 PSRAM 버스를 소유하고, 수신기 bus는 별도 내부 ROM을 읽는다. 기존 bulk 창도 token이 붙은 타일 payload 창이다. 수신 코드 적재에 재사용하려면 부트 순서·영역 예약·소유권·무결성·공통 reset을 연결해야 하며 무료 기존 기능으로 계산하지 않는다. 이번에는 그 경로를 새로 구현하지 않았다.

## 동일4398B 바이너리의 실제65816 검증

SELECT `maskrun-host01/test01/fault01/analysis01`, `storage-map01/rtl01`. 과거 map 모델만으로 성공을 주장하지 않고 실제 C 송신 fixture와 Mesen65816으로71 frame을 재생했다.

- 정상71 display commits/1100 ACK, 기존 C 독립reference4,066,624 checks.
- 독립 Python encoder와 실제 C mask 패킷·manifest가 일치한다. 목적 은행 map290,816B 및71개 command 목록이 일치한다. Lua는 CPU가 쓴 WRAM·사용 VRAM pattern·map·raw·metadata·OAM 및 VBlank 표시 ACK를 검사한다.
- DMA426개/132,270B, 기존193 묶음178개/12,944B. warm multi-VBlank는952/955 두 개다. cold2는 별도이며67 single-VBlank commits를60fps로 부르지 않는다.
- zero mask, 다른 mode, 잘린 word, 중복 group, manifest offset/내용, manifest 이후 map, 조기SEAL, 불완전 cold map+일치 manifest, map/manifest/final STOP의12개 실제 오류 시험이 terminal rejection 및 기존 화면 보존을 확인했다. cold 누락은 manifest까지 일치시켜 초기화 검사 자체를 시험했다. STOP은 두 초기화 상태를 무효화했다.
- 752개의 미초기화 읽기 주소는 독립 oracle에서 허용한 사용하지 않는 pattern gap에만 속한다. 사용 map/metadata/pattern을 미초기화 상태로 통과시키지 않았다.

PC fixture는 독립 이전map4096B와 stale bits512B를 보유한다. 새 ARM 할당이나 전체 RUN/IRQ 여유가 아니다. 실물 FPGA producer·shared SPI·ARM 실행을 함께 재생한 결과도 아니다.

## ROM보다 처리시간이 현재 병목

실제 instruction 진입/복귀의 master clock 차이로 측정했다. 따로 설치한 callback의 wall-clock 지연을 CPU 실행시간으로 계산하지 않는다. mask 복귀는 공통 manifest 복귀 주소도 지나므로116개 해당 관측을 packet/start pairing으로 분리했다.

|warm69의 routine 시간|최소ms|최대ms|
|---|---:|---:|
|mask decode·값 저장·DMA 목록 생성|2.42638|16.73239|
|manifest 두 패킷 비교|1.81634|1.81820|
|최종 coverage|1.50922|1.51202|
|위 세 항목의 frame별 합|5.75399|20.05851|
|기타 mark|0.68351|3.25386|

현재 mask 경로는 비트별 반복과 선택 word별 append를 사용하고, manifest/coverage도 반복 비교한다. 공간을 더 확보했어도 같은 코드 자체가 빨라지는 것은 아니다. 이전 mark 계측에는 payload copy가 빠져 있었으므로 현재 mask routine과 단순 차감해 개선/악화율을 만들지 않는다.

앞선 ready4 wire 모델에 이번 전체 routine 합을 직렬로 더한 조건부 비용은14.29708..33.73118ms이며58/69가16.67ms를 넘는다. source·ARM·나머지 dispatch/copy·대기·DMA/display 비용은 아직 모두 포함되지 않았다. 이것은 전체 병렬 일정의 불가능 증명이나 실제FPS가 아니다. wire 감소만으로 현재 디코더를 채택할 수 없다는 근거다.

## 다음 작업

4KiB 제한으로 단독 기각하는 경로는 종료한다. **공간을 사용해 반복 처리 비용을 줄이는 완전한 수신 경계**를 비교한다. bit별 분기·word별 append 대신 group/span 처리, manifest/coverage의 블록 비교·루프 전개·조회표 등의 비용을 코드/메모리/시간으로 함께 계산한다. 안전 검사를 삭제하거나 작은 opcode·seed 변경을 반복하지 않는다.5KiB562B 여유도 고정 제약이 아니며 더 커진 후보는 저장 구조 비용을 다시 계산한다.

같은 시점에952 순서 비용과955 최소4198>4192 전송, source449B/rowshift 전체 면적과 mapper 여유, 새 입력 ARM RUN/IRQ, host/NES firstfault·CDC/IO·final display lease/retire를 유지한다. 수신 기능 시험만으로 P2·전체FIT·실기를 승인하지 않는다. 생산227·240미배치·기각241/246·GBC164·save SRAM·과거 자료는 변경하지 않았다.

## 재현 도구

`prepare_nes_maskrun247.py`는 private 기존C fixture를 복사해 sender를 만든다. `test_nes_maskrun247.py`는 기존maskboundary-build01과 이 sender로71-frame 재생을 한다. `test_nes_maskfault247.py`는 정상 packet trace에서12개 반례를 만든다. `nes_storage247.py`는4/8/5KiB bus MAP, `test_nes_storage247.py`는 기존 승인된 FLOAT wrapper 안에서 실제 bus RTL 비교를 한다. `analyze_nes_maskrun247.py`가 패킷·map·command·시간·로그를 독립 검증한다. 각 도구의CLI와 private snapshot에 실행 입력이 남는다. 공개 자료에 게임 ROM·그래픽·license bytes는 포함하지 않는다.
