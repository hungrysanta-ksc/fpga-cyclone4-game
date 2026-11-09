# 702: MMC700·701 실기와 699 검증 범위 정정

> 후속703에서 실기 CPU/PPU 문맥을 정확히 재현하고 다음 sprite까지 포함한 수정 B를 검증했다. 아래702의 미재현 판단은 당시 결과다. [703 수정·검증 범위](nes-bonus703-results.ko.md)

**MMC700은 정상 종료했지만 일시적인 타일 깨짐이 보고됐다. MMC701은 같은 스페이드 진입에서 다시 종료됐으며, 최초 오류는 이전 PPU CHR 읽기2가 아니라 CPU PRG 읽기1이다. 699를 스페이드 오류 해결 완료로 판정하지 않는다.** [분석·원본 SHA](../analysis/hardware702-mmc700-701.json) · [원시 근거 보존](../analysis/hardware702-archive.json)

## 완료 표시와 작업량

| 구간 | 이전 MMC695 | MMC700 | MMC701의 첫55초 |
|---|---:|---:|---:|
|5–40초|18.34fps|20.89fps|20.23fps|
|40–55초|21.67fps|21.87fps|19.87fps|
|5–55초|19.34fps|21.18fps|20.12fps|

700 전체는60.35초/1290화면,21.38fps이며 이전695의20.00fps보다 높다. 하지만5–55초 +9.51%를 구현 가속률로 보지 않는다. 이번 초반 표시당 mapdirty는−33.47%,E1전송량−18.22%,OBJ−8.97%였고 후반 mapdirty−22.85%,OBJ−31.81%였다. 두 ARM의799개 함수와65816은 기존판과 동일하며 이번 변경 목적도 속도 향상이 아니다. 같은 작업량의 대조가 아니므로 체감 차이가 없었다는 관측과 모순되지 않는다.

700 수신/계획·공급/출력·최종ACK 평균은8.61/11.34/26.08ms다. 이전695는10.42/11.58/27.19ms지만 서로 다른 작업량·대기 시간을 포함한다. IRQ·SPI 세부 비용을 다시 더하지 않는다.

701은263.31초(4분23.31초)/5452화면 뒤 종료됐다. 전체 평균20.71fps와 단계8.31/11.10/28.35ms는 다른4분 장면의 평균이므로700과 직접 성능 비교하지 않는다. 첫5–40/40–55초 완료 카운터는 보존되지만 상세bin은240.12초 epoch로 바뀌었다. 이를 첫55초의 작업량이라고 해석하지 않는다.

## 이번 최초 오류

| 항목 | MMC696 이전 | MMC701 이번 |
|---|---|---|
|오류코드|2: PPU CHR sample deadline|1: CPU PRG sample deadline|
|PPU 위치|192선/262dot|192선/265dot|
|대기/필요 물리주소|`0x21FBE7`|`0x03FB34`|
|요청 age|1 NES master clock|2 NES master clocks|
|문맥|`e200c3f7ce21fbe7`|`440107f66803fb34`|
|PPU 상태|`604198007f9f9f9c`|`60425c008c03bc01`|

701은 CPU sample1/valid0, CPU 소유 요청busy1, response0/ready0다. 요청한 주소는 현재 필요한 주소와 같다. 선택 `nes_rom_service.sv`의 `cpu_sample && cpu_rom && !cpu_valid` 분기가 오류1을 기록한다. backend255클록 timeout이나 잘못된 응답 주소가 아니다. 해당 물리주소는699에서 실행한 원본 ROM 명령의 다음 `$FB34` fetch와 연결된다.

같은 장면에서 발생했지만 로그만으로 「699가 CPU 오류를 새로 만들었다」거나 「PPU 오류는 완전히 해결됐다」고 단정할 수 없다. 공유 reader의 이전 CHR/CPU 요청·응답 이력이 없어서 CPU 요청이 왜 늦게 수락됐는지는 아직 미확정이다. plan_error/CRC/receiver/video/trace_abort는0이다. `screen_error=169`는 유효한 SPC 초기화readback A9이며 타일 오류 코드가 아니다.

701의 runtime SERVICE2→window guard2·sink plan-progress5는 최초 ROM fault에 따른 중단과 일치한다. pending4개는 중단 시 미완료 출력이며 최초 원인으로 바꾸지 않는다. STOP·base_restored·safe_to_reload·MENU_PREPARED와 사용자 메뉴 복귀가 일치한다. 자발적인 종료 조합 시험은 아니다.

## 기존 시험의 부족과 추가 확인

699의 실제 T65 시험은 `step699>=59`에서 끝났다. 이는263dot에서 첫 CHR 하위 비트를 확인한 직후로,264dot의 상위 비트와 뒤따르는 CPU 읽기 마감까지 검증하지 않았다. **24조건 통과는 첫 CHR 요청 수정의 제한된 근거이며, 전체 스페이드 진입 안정성 근거로 부족했다.**

702에서는 생산 RTL을 바꾸지 않고 기존 T65·실제 native arbiter fixture를step79까지 연장했다. 독립 committed mapper 주소·CHR 바이트 검사와 STOP을 유지했다. 기존8조건×3메모리위상 중18조건은 통과했고,6조건은192선/264dot의 다음CHR `0x21FBEF`에서 오류2가 발생했다. 문맥은`e301c3f7de21fbef`다. 중간 CPU `$FB34` 공급 뒤 CHR 상위 비트의 응답이 마감에 늦는 조건이다. 실제701의CPU 오류1/265dot/age2를 그대로 재현한 것은 아니다.

이 결과는 후속 읽기 경쟁이 미검증 상태였음을 입증한다. 먼저 CPU와CHR 양쪽 마감을 같은 연속 구간에서 통과시키고, 그 뒤에만 실기판을 갱신한다. 699의 첫CHR 바이트 통과·FIT·두 위상 출력 모델 결과는 지우지 않고 범위를 정정한다. 이번에는 새RTL/ARM/65816 수정·FIT·ZIP이 없다.

## MMC700 타일 깨짐

한 번 타일이 밀려 보였다는 사용자 관측을 별도 미해결 시각 오류로 등록한다. 해당 시점의 영상·좌표·픽셀/VRAM 이력이 없어 원인을 특정하지 못했다. ROM/CRC/영상검사 오류0은 전송된 데이터의 일관성을 뜻하며 NES 장면과 실제 표시 픽셀이 항상 같다는 증명은 아니다.

700의 최종 runtime결과1은60초 deadline이다. 종료 시window error3/sink error2와pending1개가 있지만, runtime의 deadline guard가 전송 전후에 false를 반환하면 같은 window 전송 실패가 기록된다. `failed_transfers=0`,sticky ROM fault0과 함께 보면 이 종료 수치만으로 플레이 도중 SPI가 손상됐다고 볼 수 없다. 이값을 중간 타일 깨짐의 원인으로 연결하지 않는다. 향후 재발하면 장면·대략적인 시각·짧은 영상이 원인 분리에 유용하지만 지금 재시험을 요구하지 않는다.

## 다음 작업 순서

1. 701 CPU문맥`03FB34/192:265/age2`를 목표로 기존 IRQ명령·CHR 두plane·캐시 적중/미적중·공유 PSRAM grant/response를 같은 시간축에 연결한다. 정상 raw CPU 주소 안정 시각과 최초 허가 가능 시각을 분리한다.
2. 699 원본/수정 대조로 CPU sample과CHR 하위·상위 sample을 모두 검사한다. 첫 성공 후 종료하지 않고 다음sprite까지 진행하며 STOP·독립 검사·최종ACK를 유지한다. 임의 clock stretch/timeout 완화/오류 무시는 하지 않는다.
3. 원인 경계만 수정하고 두 위상 표시 일정·전체Lite FIT/STA·메뉴 복귀를 통과한 뒤 새60초/장시간판을 제공한다. 현재 예산은59LE/LAB0/M9K0이다.
4. 타일 깨짐은 별도 추적하며 안정성 확인 전 출력 속도 최적화를 재개하지 않는다.

## 재현 위치

원본6파일과선택소스는 `WORKSPACE/probes/nes-hardware702/analysis01/evidence.zip`에 SHA로 보존했다. 분석 entry는 `tools/analyze_nes_hardware702.py`; 보드는ASCII Temp `nes-bonus699-board01`, ARM은 `WORKSPACE/probes/nes-trial700/arm700/src`다.

추가 시험은 `tools/probe_nes_bonus702_cpu.py`로원본SMB3(J) SHA를확인해생성한ASCII Temp `nes-bonus702-cpu01..03`, phase0.5/3.5/5.5다. 기존 `probe_nes_bonus698.py run`과허가된Starter FLOAT1좌석을순차사용했다. 원본ROM·세이브는변경하지않았고ROM·라이선스는공개하지않는다.
