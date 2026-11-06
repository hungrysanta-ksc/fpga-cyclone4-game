# 951에서 독립 검사를 앞당겼을 때 실제로 남는 시간

**621을 유지한다.** 951의 tile·HDMA 검사를 앞당기면 같은 바이너리의 대조군보다 업로드 루틴에는 1.500 / 1.504 ms 일찍 진입한다. 실제 첫 SEAL DMA는 두 시작 위상 모두 다음 VBlank에서 실행됐다. 950→951은 4 / 4 VBlank였고 951 최종 ACK는 0 / 28 master clock 늦어졌다. [기계 판독 결과](../analysis/seal632-verification.json)

## 두 시작 위상의 비교

단위는 ms다. 시각의 기준인 0은 951을 세 번째 VBlank에 표시할 수 있었던 246번 검사선이다. 양수는 이 마감을 지난 시간이다. ACK 차이의 기준은 같은 632 바이너리의 기존 패킷 재생이다. 음수는 더 빠른 ACK를 뜻한다.

| 951에 적용한 변경 | SEAL 수락 | 업로드 진입 | SEAL 후 첫 PPU DMA | 951 최종 ACK 차이 |
|---|---:|---:|---:|---:|
| 공통 코드 대조군 | 6.546 / 7.311 | 8.191 / 8.955 | 15.293 / 15.288 | 0 / 0 |
| tile만 | 6.080 / 6.819 | 7.165 / 7.905 | 15.304 / 15.304 | +0.0100 / +0.0170 |
| HDMA만 | 6.507 / 7.319 | 7.431 / 8.242 | 15.283 / 15.299 | −0.0108 / +0.0118 |
| 둘 다 | 6.326 / 7.086 | 6.691 / 7.450 | 15.293 / 15.289 | 0 / +0.0013 |

둘 다 적용하면 SEAL 수락 후 업로드 진입까지 1.645 / 1.644 ms가 0.365 / 0.364 ms로 줄었다. 대신 마지막 HDMA 패킷의 수락→소비 ACK가 0.338 / 0.339 ms에서 1.131 / 1.131 ms로 늘었다. 원본 625에서는 그 패킷의 SPI 전송 자체가 목표 검사선보다 4.796 / 5.559 ms 늦게 끝난다. 검사 시간을 모두 숨겨도 이 공급 순서에서는 세 번째 VBlank를 쓸 수 없다. 둘 다 적용한 951 ACK와 원래 625 실행의 차이는 +0.0129 / −0.0136 ms다.

## 무엇을 실행했나

- 625 tables-bg의 실제 ARM·ROM·IRQ 실행에서 기록한 SPI 거래를 순서대로 사용했다. 각 거래는 원래 시작 시각과 직전 변경 거래의 종료 중 늦은 시각에 시작한다. E1 크기 변화는 2.625 MHz에서 바이트당 8클록을 적용했다. tile은 기존 SEAL의 필수 비트맵 144B를 첫 팔레트 패킷으로 옮기고 SEAL을 그만큼 줄였다. HDMA는 길이·표시 mask·patch 수를 선언하는 6B를 더 보냈다. 패킷 수는 모두 30개다. 새 ARM 생산 코드와 IRQ 피드백은 이 재생에 포함되지 않는다. credit이 차면 다음 패킷을 보류하며, 65816은 실제 명령을 실행한다.
- 65816은 활성 세대·serial·순서를 검사한 뒤 비활성 뱅크의 tile 유효성 144B를 요구 비트맵과 대조한다. 그 뒤의 tile bulk는 거부한다. HDMA는 선언 길이만큼 수신한 뒤 기존 compact 복원과 형식 검사를 실행하고 그 프레임의 section 5를 닫는다. SEAL에서 길이·mask·count를 다시 대조한다. map 수신 과정과 SEAL의 map 유효성 8B·섹션 길이 검사는 유지했다. 두 조기 검사 끝에서 STOP을 읽으며 성공·중단·실패 시 해당 플래그를 비운다.
- 각 위상·후보에서 905–951 총 47장의 RGB·map과 최종 ACK를 확인했다. 잘못된 HDMA 형식, identity, 선언 불일치, 선행 검사 없는 축약 SEAL, 미수신 tile과 손상된 map 유효 비트를 거부했다. 두 검사 도중 각각 STOP을 넣어 950 표시 유지와 취소 ACK를 확인했다. 중단된 양 뱅크의 map WRAM·VRAM 16 KiB 및 OAM·HDMA WRAM 3,778B를 다시 넣은 뒤 cold 905·906의 기준 이미지와 최종 ACK를 확인했다.
- 65816 본체는 5,323→5,908 B, 한도 5,984 B에서 76 B가 남는다. 추가 WRAM은 상태 10 B와 임시 2 B다. 보드 LUT·Flash·실기 fps의 개선은 계측 범위 밖이다. 951에서 탈락해 957까지의 공동 재실행·Quartus·전달본 단계로 승격하지 않았다.

## 다음 비교

951·952·953·954·955·957의 실제 출력 바이트를 같은 대상 뱅크의 직전 완료 프레임과 대조했다. 여섯 화면 모두 팔레트 512 B가 일치했다. 951 OAM은 544 B 중 앞 112 B에서만 95 B가 바뀌었다. 팔레트 네 E1은 344 B였고 OAM 후반 두 E1은 이미 압축되어 합계 44 B였다. 따라서 여섯 패킷을 통째로 없앤 이론상 E1 wire 절감도 약 1.18 ms다. 실제 재사용 명령·독립 검사·이력 생성 비용을 넣으면 더 작아진다.

다음은 **최종 ACK로 확정된 대상 뱅크의 팔레트·OAM을 이용했을 때 생기는 빈 큐 시간에 map DMA가 실제로 들어가는지**를 먼저 계산한다. 원래 625 일정에서 여섯 패킷의 생산·거래·65816 서비스까지 모두 제거한 낙관 대조군을 두고, 두 위상에서 실제 DMA가 246번 검사선에 들어오는지 본다. 이 상한도 부족하면 팔레트 재사용 구현을 보류하고, 950의 표시 이전부터 다음 프레임을 준비할 수 있는 구간과 입력·표시 뱅크 소유권을 검토한다. 상한이 통과하면 serial·뱅크·내용을 독립 확인하는 실사용 경로와 cold·STOP 전체 복원을 먼저 구현한다.

## 재현

625 tables-bg 기록 두 벌과 624 client가 필요하다. 아래 명령은 저장소 루트에서 실행한다. `$raw`는 원자료 경로, `$mesen`은 기존 Mesen 실행 파일이다.

```powershell
$client = '../probes/nes-map632/final'
python tools/nes_seal632.py $client
foreach ($phase in 1,2) {
  foreach ($flags in 0,1,2,3) {
    python tools/replay_nes_seal632.py --trace "$raw/nes-seal625-tables-bg-$phase" --client $client --base-client ../probes/nes-raw624/client --mesen $mesen --flags $flags --out "$raw/nes-seal632-$flags-${phase}a"
  }
}
python tools/check_nes_seal632.py --trace "$raw/nes-seal625-tables-bg-1" --client $client --mesen $mesen --out "$raw/nes-seal632-edges-b"
python tools/analyze_nes_seal632.py --root $raw --client $client --out analysis/seal632-verification.json
```
