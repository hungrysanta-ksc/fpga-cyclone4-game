# 744 · 긴 map DMA 직후의 OBJ 전송

**957의 OBJ descriptor가 이미 수락돼 있으면 두 시작 위상 모두 257선에 64B DMA를 시작한다.** 727의 부팅 ROM, 두 시작 시각, 모든 map 패킷의 발행 시각·payload, 952·957의 1,536B 선행 DMA를 보존한 65816 재생 결과다. 727 ARM이 원래 순서로 발행하면 긴 map 완료 시점에 내부 큐가 비어 있어 이 경로를 사용할 수 없다. 개발 기준은 727을 유지한다.

## 같은 map 발행 시각에서의 결과

905–957의 53화면을 각각 재생했다. 전 구간에서 패킷 순서·헤더·payload 바이트와 출력 RGB가 727과 일치했다. 밀집 간격은 951 공개부터 957 공개까지 여섯 간격의 평균이다. 743 대조군과 744는 같은 OBJ 발행·수락, 같은 map DMA 시작·종료, 같은 첫 scroll 발행 시각을 사용한다. 957에서 마지막 map의 소비를 확인한 후 OBJ·OAM을 앞당긴 조건에는 계측한 E8 조회, D0 입력 서비스, E0 polling과 검사·발행 비용을 포함했다. 두 위상 모두 실제 마지막 map ACK는 마지막 두 E0 표본 사이에 있었다.

| 측정값 | 위상 1 | 위상 2 |
|---|---:|---:|
| 긴 map 마지막 PPU 쓰기 → OBJ MDMAEN, 743 → 744 | 144.34 → 98.90µs | 146.11 → 100.66µs |
| OBJ 실제 시작, 743 → 744 | 258선 H80 → **257선 H468** | 258선 H858 → **257선 H1246** |
| 744의 OBJ 마지막 PPU 쓰기 | 257선 | 258선 |
| OBJ 선행 / SEAL 뒤 전송 | 64 / 224B | 64 / 224B |
| 밀집 평균, 727 → 744 | 49.932319 → 49.929215ms | 49.932304 → 49.928424ms |
| 957 최종 ACK, 727 → 744 (master clock) | 65,725,518 → 65,725,118 | 66,082,774 → 66,082,274 |
| 957 최종 ACK, 743 대조군 → 744 | 246클록 단축 | 동일 |

위상 2에서 실제 시작과 258선 경계의 차이는 118 master clock(약 5.5µs)이다. 두 위상 모두 908·911 표시는 2 VBlank, 951 공개는 236선, 952–957 표시는 각각 3 VBlank, 957 최종 추가 대기는 0회였다. 두 위상에서 743보다 앞당긴 OBJ 시작이 위상 2의 마지막 ACK까지 전파되지는 않았다. [패킷·PPU 시각·뱅크·RGB 대조](../analysis/chain744-verification.json)

## 바꾼 경로

전체 map을 소비한 뒤 내부 descriptor 큐에 항목이 남은 분기에서만 새 코드를 호출한다. 직전 완료가 1,536B map이고 남은 한 건이 수락된 288B OBJ일 때 첫 64B를 전송한다. map 진행을 먼저 공개하고, source의 종류와 주소를 한 번 읽어 레지스터에 보관한다. WRAM의 독립 receipt와 대상 뱅크를 확인하고 큐에 넣는 과정은 기존 경로를 거친다.

- OBJ descriptor에서 실제로 읽은 바이트는 9→6개다. source·destination·길이를 각각 한 번 읽는다. DMA 채널 레지스터 쓰기는 8→4회다. 방금 동기 전송을 끝낸 채널 0의 모드, VRAM 포트, source bank와 VMAIN을 재사용해 source 주소와 길이만 다시 설정한다. VRAM 목적지 주소는 새로 쓴다.
- 새 빔 값을 래치해 VBlank와 9비트 수직선을 검사한다. 이 VBlank에서 기존 입력 서비스가 수행할 latch 초기화를 적용하고, 보관된 STOP에 이어 MDMAEN 직전의 실시간 STOP·새 패킷 검사를 실행한다. 전송 크기는 Y에 담긴 실제 완료 바이트만큼 차감한다. 종단 검사는 OBJ 288B와 먼저 전송한 map의 VRAM 내용을 확인한다.
- 두 위상 각각 OBJ 허가 직전 STOP이면 전송 0회, 첫 PPU 쓰기 중 STOP이면 진행 중인 64B만 완료했다. 두 경우와 손상된 OAM 이력(0xE0) 모두 956 표시를 유지하고 957의 최종 ACK를 차단했다. 허가 직전 scroll이 들어오면 새 패킷을 먼저 수락했다. 기존 60초·장시간 ARM 각각에서 메뉴/base 복귀 5경로와 파일명 4조건도 재검사했다.

## 적용 조건과 비용

727의 원래 OBJ 패킷은 두 위상 모두 긴 map DMA 도중 발행됐지만 65816은 DMA를 끝낸 뒤에야 수락했다. 이때 큐가 비어 있는 분기를 건드리지 않도록 구현한 결과, 727의 원래 발행과 새 코드를 함께 썼을 때 53화면의 이벤트·시각이 양쪽 모두 원본과 일치했다. OBJ만 일찍 도착하고 727의 기존 소비기를 쓰면 map 뒤의 다음 descriptor가 48B BG였다. OBJ 선행 전송을 재현하려면 BG를 먼저 처리하고, map 다음에 이미 수락된 OBJ가 남아야 한다. 첫 384B map 완료에 맞춰 scroll을 앞당기는 조건에서도 새 패킷이 긴 DMA 중에 도착해 OBJ 선행량이 0B가 됐다.

이 시험은 원래 압축 ROM으로 부팅한 후 실행 중인 65816 WRAM에 시험 코드를 연결해 부팅 시간을 고정했다. 변경된 ARM·FPGA·65816을 함께 링크한 설치본은 없다. 727의 512B 비압축 prefix로 같은 형식에 정적으로 배치하면 새 루틴 155B와 실제 길이 차감을 포함한 기존 소비기는 5KiB ROM 한도를 81B 초과한다. 741의 선택 코드와 743의 독립 범위 검사까지 묶은 본문은 6,362B이며 압축 ROM은 279B 초과한다. FPGA RTL 변경과 새 보드 FIT·STA는 없었다.

다음 단계는 952의 긴 map 전송을 보존하는 실제 ARM 발행 경로에서, 957의 48B BG와 마지막 map·OBJ가 이 순서로 수락되는지부터 확인하는 것이다. 이 조건이 성립하면 중복 selector를 기존 ROM 본체에서 제거하고, 같은 부팅 시각에 위상 2의 118클록 여유가 남는지 확인한다.

## 재현

[743 재현 절차](nes-bitmap743-results.ko.md)의 727·740 기록, 694 client01, Mesen을 사용한다. 아래 이름의 N은 1 또는 2이며 출력은 ASCII 임시 디렉터리에 둔다.

1. `tools/replay_nes_chain744.py --phase N --client <694> --mesen <Mesen.exe> --calendar 727 --trace <temp>/nes-pair727-aN --out <temp>/nes-chain744-stocktailN`을 실행한다. `--control`을 추가한 기준 출력은 `refN`이다. 이하에서 출력 이름 앞에는 모두 `nes-chain744-`를 붙인다.
2. `--calendar early --trace <temp>/nes-gap740-firstN-trace`로 바꿔 `finalN`에 기록한다. `--control`은 `baseN`, `--stock`은 `stockearlyN`, 두 옵션을 함께 주면 `stockearlybaseN`이다. 첫 scroll 조건은 `--scroll first --pulse-folder <finalN>`으로 `feedbackN`에 둔다.
3. early 경로에 `--fault head`, `--mode stop --inject during_obj --fault prestop`, `--mode stop --inject during_obj`, `--mode stale`을 각각 적용해 `headN`, `preN`, `midN`, `staleN`을 생성한다. `check_nes_menu533.py`로 727 arm01과 normal01에 각각 trial 690과 704를 검사해 `<temp>/nes-chain744-menu690.json`, `menu704.json`(동일 접두어)에 저장한다.
4. `tools/analyze_nes_chain744.py --temp <temp> --client <694> --out analysis/chain744-verification.json`을 실행한다. 두 위상의 모든 map 발행과 앞선 52화면 이벤트, 53개 RGB, 실제 DMA 쓰기와 종료, 독립 검사·메뉴 결과를 검증한다.
