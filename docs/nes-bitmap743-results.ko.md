# 743 · 9개 OBJ 슬롯의 65816 수락 비용

727의 ARM 바이너리와 707D 보드를 사용했다. 대상은 957의 마지막 OBJ 288B다. 905–957의 출력에서 32B 슬롯 9개가 한 descriptor에 든 경우는 이 한 건이다. 실제 보드에서 측정한 FPS는 이번 비교에 포함되지 않는다.

## 동일 발행 시각에서의 효과

65816은 기존 descriptor의 길이·정렬·구간과 identity를 검사한 뒤, 9개 슬롯에 해당하는 16비트 마스크로 현재 receipt의 중복을 확인한다. 중복이 없을 때만 receipt와 대상 뱅크의 이력 두 바이트를 갱신한다. 이후에는 기존 descriptor 추가, staging 원본 읽기, 반환 token, OAM 독립 검사와 최종 ACK 경로를 실행한다. 전용 분기는 세대 번호를 사용하지 않는다.

| 727의 패킷 도착 시각 고정 | 위상 1 | 위상 2 |
|---|---:|---:|
| descriptor 마지막 읽기 → 첫 OBJ 원본 읽기, 기존 → 변경 | 439.63 → 218.37µs | 439.53 → 218.28µs |
| 범위 검사 진입 → descriptor 추가 진입, 기존 → 변경 | 308.05 → 88.65µs | 308.05 → 88.65µs |
| 957 최종 ACK 변화 | 0클록 | 0클록 |
| 951 공개 → 957 공개, 여섯 간격 평균 | 49.932319ms | 49.932304ms |

앞선 52화면의 모든 이벤트와 두 뱅크의 952·957 map 1,536B 선행 DMA를 확인했다. 727의 발행 시각에서는 긴 map DMA를 끝낸 뒤 OBJ가 도착해, 단축한 검사 시간만으로 OBJ의 선행 DMA가 생기지 않았다.

## 마지막 map 반환을 먼저 확인하는 경우

742에서 계측한 E8·E0·D0 왕복 비용을 반영한 도착 시각과 741의 DMA 선택 코드를 사용했다. 두 소비기에 같은 패킷을 주고 첫 scroll과 후속 패킷은 727 시각에 고정했다. 이 시험은 WRAM에서 실행한 진단이며, 아래의 완전 링크 실행과 구분한다.

| 957 진단 | 위상 1 | 위상 2 |
|---|---:|---:|
| 마지막 OBJ 288B 중 선행 DMA, 마스크 적용 전 → 후 | 0 → 64B | 0 → 64B |
| 긴 map 마지막 PPU 쓰기 → OBJ MDMAEN 쓰기 | 144.34µs | 146.11µs |
| OBJ DMA 시작 | 258선 H80 | 258선 H858 |
| 727 대비 밀집 간격 변화 | −1.195µs | −3.880µs |
| 727 대비 957 마지막 ACK 변화 | −7.170µs | −23.280µs |

두 위상에서 952·957의 긴 map DMA를 보존했고 224B는 SEAL 뒤에 남았다. 위상 1에서는 257선 H1240에 전송을 **허가**했지만 DMA 레지스터 쓰기는 다음 선이었다. 위상 2에서는 257선 H660에 다음 descriptor를 선택하고 258선 H654에 허가했다. 실제 DMA를 257선 안에 시작하려면 이 일정에서 각각 80·858 master clock보다 더 앞당겨야 한다.

첫 384B map DMA 완료를 확인한 뒤 실제 ARM 콜백 비용(약 13,068클록)을 지불하고 scroll을 발행하는 조건도 따로 재생했다. 두 위상 모두 긴 map DMA 중에 scroll이 도착했고, DMA가 끝나자 새 패킷이 먼저 수락됐다. 그 결과 OBJ 선행량은 0B였고 957 최종 ACK는 727보다 각각 246·334클록 늦었다.

## 부팅부터 이어지는 일정

**727을 유지한다.** ARM 727과 65816을 부팅부터 905–957까지 연결해 같은 출력 작업량과 RGB를 확인했다. 두 위상의 ARM 시작 시각, SPI 드라이버 비용, IRQ, ROM 공급 달력은 기준과 같다. 아래 표의 ACK 변화는 727 대비이며, 양수는 더 늦다는 뜻이다.

| 구성 | 위상 1 밀집 평균 | 위상 1 마지막 ACK 변화 | 위상 2 밀집 평균 | 위상 2 마지막 ACK 변화 |
|---|---:|---:|---:|---:|
| 727 | 49.932319ms | 0 | 49.932304ms | 0 |
| 727 소비기, 96B prefix | 49.935547ms | +16.640288ms | 49.932397ms | +0.559µs |
| 743, 96B prefix | 49.935997ms | +33.297525ms | 49.936479ms | +11.733µs |

첫 패킷 조회는 7,380,660 → 7,805,960 → 7,899,858 master clock이었다. 위상 1의 첫 905 공개는 29 → 30 → 30번째 VBlank였고, 908 표시 간격은 2 → 2 → 3 VBlank였다. 원래 소비기를 재압축한 것만으로도 위상 1에서 한 VBlank가 밀렸다. 743 전체 경로는 여기에 908에서 한 VBlank를 더 사용했다. 위상 2의 908은 세 구성 모두 2 VBlank였다.

두 위상의 952–957은 각각 3 VBlank, 951 공개는 236선, 957 최종 추가 대기는 0회였다. 952·957의 1,536B map 선행 DMA는 보존됐으나 마지막 OBJ 288B는 전부 최종 업로드에 남았다.

743의 WRAM 실행 코드는 6,020→6,104B다. 5,120B 프로그램 ROM에서 기존 512B 비압축 prefix를 유지하면 55B 초과한다. 96B prefix로 재압축해 743은 남는 공간이 0B이고, 같은 96B prefix로 기존 코드만 압축한 대조군에는 81B가 남는다. payload 및 뱅크별 이력용 RAM은 늘지 않았다.

## 검사와 복구

- 9슬롯 시작 120곳과 중복 없음·각 위치의 중복 9가지를 두 뱅크에서 실행했다. 기존 108건을 포함해 2,508건이 통과했다. 실패 시 어느 바이트도 갱신하지 않았고, 성공 시 양옆 비트와 반대편 뱅크를 보존했다.
- 보류 중인 scroll과 DMA가 동시에 가능한 시점에 새 패킷을 먼저 수락했다. OBJ 64B의 첫 PPU 쓰기 도중 STOP을 유지하자 진행 중이던 64B가 끝나고 다음 DMA가 차단됐다. 잘못된 OAM 이력은 0xE0으로 거부했다. 두 경우 모두 956 화면을 보존하고 957의 최종 ACK를 막았다.
- STOP 뒤 quiet에서 receipt·뱅크 이력 등 472B를 저장하고, 새 부팅의 WRAM 실행 진입 때 같은 주소에 복원했다. 해당 53화면의 이벤트 시각과 RGB가 깨끗하게 부팅한 743과 일치했다. 이 검사는 지정한 WRAM 범위를 대상으로 한다.
- 기존 727 ARM의 60초판·장시간판에서 메뉴/base 복귀 경로 5개와 파일명 4조건을 각각 재검사했다. 이번 변경과 검증은 65816에 한정했고 ARM Flash와 정적 RAM 증가는 0B다. FPGA RTL 변경이나 새 ROM을 실은 전체 보드 FIT·STA, 실기 전달은 없었다.

## 다음 작업

727의 첫 패킷 조회와 map 발행을 고정한다. 먼저 957의 긴 map 마지막 PPU 쓰기부터 다음 descriptor 선택·DMA 설정 사이 144–146µs에서 어떤 읽기를 재사용할 수 있는지 확인한다. 새 패킷과 STOP을 다시 확인한 상태에서 실제 MDMAEN 쓰기가 257선에 들어가는지 잰 뒤, 압축 ROM 부팅과 연속 일정까지 다시 비교한다.

## 재현

1. `tools/build_nes_bitmap743.py --client <694 client01> --raw <635 client04> --out <probe>/client`로 압축 ROM을 생성한다. 같은 명령에 `--control96`을 추가하고 출력을 `<probe>/control96`으로 바꾸면 기존 소비기의 부팅 대조군이 된다.
2. [727의 905–957 연속 실행](nes-pair727-results.ko.md)과 같은 ARM·ROM 허가 달력·SPI 비용으로 `tools/test_nes_observer717.py`를 실행한다. 두 시작 master clock은 7,288,416과 7,467,100이다. 마스크 ROM은 `<temp>/nes-bitmap743-live1/2`, 부팅 대조군은 `nes-bitmap743-control1/2`에 기록한다.
3. `tools/test_nes_admit556_ranges.py --nine-obj --client <probe>/client --out <temp>/nes-bitmap743-ranges --mesen <Mesen.exe>`로 두 뱅크의 범위 검사를 실행한다. `check_nes_menu533.py`에 727 장시간판·60초판 ARM과 각각 `--trial 690|704`를 주고 결과를 `<probe>/menu-690.json`, `menu-704.json`에 저장한다.
4. `tools/replay_nes_bitmap743.py --phase N --calendar 727 --trace <temp>/nes-pair727-aN --client <694 client01> --mesen <Mesen.exe> --out <출력>`을 사용한다. 원본(`--baseline`)은 `nes-bitmap743-baselineN`, 마스크는 `nes-bitmap743-fixedN`에 둔다. `--calendar early`는 [742의 재생 입력](nes-receipt742-results.ko.md) `nes-gap740-firstN-trace`를 쓰며 출력은 `nes-bitmap743-earlyN`이다. 마스크는 마지막 OBJ를 받을 때 설치한다. 첫 scroll 피드백 시험은 early 명령에 `--scroll first --pulse-folder <temp>/nes-bitmap743-earlyN`을 추가해 `nes-bitmap743-scrollN`에 둔다.
5. 위상 1의 727 재생에 `--mode stop|stale`을 주어 각각 `nes-bitmap743-stop1|stale1`에 둔다. early 재생에 `--inject head`, `--mode stop --inject during_obj`를 주어 각각 `nes-bitmap743-head1|mid1`에 둔다. 후자에 `--save-quiet`를 추가해 `nes-bitmap743-quiet1`에 저장한다. `--calendar 727 --baseline --restore-quiet <quiet1>/aborted-banks.bin`으로 마스크 ROM과 `nes-bitmap743-live1` 기록을 읽어 `nes-bitmap743-reboot1`에서 cold 재생을 확인한다.
6. `tools/analyze_nes_bitmap743.py --temp <temp> --probe <probe> --original <694 client01> --out analysis/bitmap743-verification.json`을 실행한다. 이전 단계의 기준 기록과 이번 작업의 검증 결과를 함께 검사한다. [시간·원시 해시·보호 조건](../analysis/bitmap743-verification.json)
