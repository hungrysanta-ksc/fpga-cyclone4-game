# NES181 — MCU 표시 변환과 SNES 전송 데이터

COMMITTED 부분 행을 실제 MCU 변환 코드가 SNES 패턴·팔레트·행 전환표로 만드는 경로를 구현했다. 새 sink 후보는 이 데이터를 기존 순차 패킷 교환으로 전송한다. C가 만든 데이터를 실제65816/DMA/PPU 모델에서 양쪽 VRAM 뱅크로 표시해 **114,688픽셀**을 비교했다. **배포 SNES mailbox decoder·뱅크 업로더의 새 규격 처리는 아직 미완료**다. 새 실기 패키지나 첫 레벨 정지·60fps 해결을 주장하지 않는다.

## MCU 구현

- 새 후보 `nes_native_video181.[ch]`는 기존 API/type165를 유지한다. 격리된 빌드에서 해당 이름으로 배치하고 새 receiver181과 짝지어 사용한다. 원본180을 덮어쓰지 않았다.
- raw raster를 일반 mask/map 검사 전에 분기한다. 최대7슬롯의 순서·개수·예약비트·256색 범위를 재검사한다. raw 행에 일반 map/fineY 예외가 남아 있으면 거부한다.
- 일반 행 구간은 raw 행에서 끊고, 다음 정상 행의 첫 map 그룹부터 다시 구성한다. group32·BG1024·OBJ128·palette2 등의 기존 한도는 유지한다.7행 이내라도 다른 자원 한도를 넘으면 거부한다.
- raw 픽셀에는 배경·스프라이트·클리핑이 이미 합성되어 있다. 일반 OBJ 패턴에서 raw 행의 mask를 제거하고 해당 행의 표시 모드도 BG1 전용으로 바꾼다. 다음 정상 행에서는 기존 OBJ를 다시 표시한다.
- raw CHR는32개8bpp 타일/2,048바이트다. 보존 행을 fineY0..6에 넣고 fineY7은0으로 둔다. 색은64+NES color6으로 저장해 CGRAM64..127을 사용한다. NES 색0도 투명 픽셀이 되지 않는다.
- 행별 세 HDMA 채널은 mode/BG1 map, TM/TS/TMW/TSW, H/V scroll을 처리한다. raw 행에서는 SNES 왼쪽8픽셀 window를 꺼서 이미 합성한 색을 다시 가리지 않는다. 정상 행에서는 기존1e/18 mask를 유지한다.

추가 영구 배열을 만들지 않았다. BG 타일 할당이 끝나면 더 이상 조회하지 않는 `bg_keys[1024]` 공간을 raw CHR·HDMA에 재사용한다. raw 작업은 BG/OBJ staging이 모두 끝난 뒤 시작한다. receiver의 required/raw union 수명은 이전181 계약을 그대로 따른다.

ARM 구조체 크기는 **receiver18,064 / video15,888바이트**로 기존과 같다. patch_count는 video 구조체 끝의 패딩을 사용해 기존 필드 위치도 보존한다. 초기 후보는 크기만 같고 hofs 이후 위치가2바이트 이동했으므로 수정했다. 최종0행 시험에서 기존180 변환 결과 전체15,888바이트와 BG/OBJ staging이 동일했다.

행 전환표는 각81바이트가 상한이다. 최대7개의 분리된 raw 행은 최대15개의 일반/raw 구간을 만들며, 긴 일반 구간의 HDMA127행 분할1회까지 포함해16×5+종료1=81이다.128,136,…176행 fixture로 이 경계를 실제 검사했다. 기존 독립 설계의 가정만으로76바이트에 제한하지 않는다.

## 새 sink 규격 — 배포 전 SNES 짝 구현 필수

새 `nes_native_sink181.c`는 op/sequence/serial/generation/ACK 검사를 유지한다. section0..4도 기존과 같다. section5만 raw가 있을 때 아래 **3,418바이트 bundle**로 확장한다. 실제 송수신을 위해서는 새 SNES decoder의 길이 상한과 SEAL 검사를 함께 수정해야 한다.

| section5 상대 offset | 길이 | 내용 |
| --- | ---: | --- |
| 0 | 1,121 | 기존 H/V scroll HDMA + 0 padding |
| 1,121 | 2,048 | raw CHR |
| 3,169 | 81 | mode/map HDMA, VRAM A |
| 3,250 | 81 | mode/map HDMA, VRAM B |
| 3,331 | 81 | TM/TS/TMW/TSW HDMA |
| 3,412 | 6 | 위 세 전환표의 uint16 LE 실제 길이 |

raw0행이면 section5는 기존 scroll HDMA 길이만 전송한다. 두 경우 모두 **SEAL24**이며 기존20바이트 뒤에 `uint16 0x1812`, `uint16 patch_count`를 추가한다. FPGA→MCU record version1811과 MCU→SNES SEAL version1812는 서로 다른 인터페이스다.

SNES WRAM candidate offset6500..7259, 두 번째 candidate e500..f259에 들어가므로32KiB별 기존 경계를 넘지 않는다.6개 section 크기 배열을 늘리지 않으므로1000/1010의 기존 metadata를 확장하다 겹치게 만들지 않는다. 기존 SNES client는1121 초과 section5/SEAL24를 거부하며, 이 후보와 혼합 배포하면 안 된다.

padding은 MCU flash의 읽기 전용240바이트 상수를 최대 payload 단위로 전송한다. 새 RAM 배열이 아니다. 초기32바이트 단위 전송과 비교해7행 fixture의 callback이76회에서47회로 줄었다. 같은 최종 데이터를 유지한 최적화이며 실기 속도 측정은 아니다.

## 검증

최종 `test06`은0/1/7행·일반 unclipped/clipped·127행 분할 경계의5장면, 총47확인을 통과했다. 실제 receiver에 record를 넣고 converter와 sink까지 실행했다. 입력 미완결·잘못된 raw 색/슬롯·개수, staging IO 실패, raw 전송 실패, SEAL 오류/세대 불일치 후 표시 금지·재시도 금지도 확인했다. 구조체 canary를 유지했다.

sink의 ACK는 **host callback이 합성**한다. 실제 SNES packet decoder/ACK/STOP에 연결한 시험이 아니다. 이후 C의 raw CHR·CGRAM·OAM·map·세 HDMA 출력을 실제65816/DMA/PPU 시험 ROM으로 올려 양쪽 뱅크 전체 visible image114,688픽셀을 독립 기대값과 비교했다. raw 행을 가로지르는 OBJ, 첫/마지막 행, 정상 구간의 왼쪽8픽셀 clipping과 raw 구간 window 해제가 포함된다. 시험 ROM의 uploader는 배포용 뱅크 전환 로직이 아니다.

ARM `-Os` 함수별 stack은 video build688→696바이트, sink seal136바이트다. 패딩 상수는 오브젝트의 읽기 전용 r 심볼240바이트로 확인했다. **전체 runtime call chain/IRQ/링크 승인은 아직 아니다.** 기존180의 RUN 여유1040바이트를 새 후보에 그대로 적용하지 않는다.

실패 기록도 보존했다. test01은 sandbox GCC DLL 재배치 오류, test02는 host 시험의 미사용 함수 경고, test03/04는 위 구조체 필드 이동을 발견한 비교 실패다. 수정 후 test05가 통과했고, padding 전송을 묶은 최종 test06도 통과했다. 기존 receiver·collector·독립 SNES 근거는 변경하지 않았다.

## 다음 작업

1. **배포 SNES client에 section5/SEAL24를 연결한다.** descriptor·실제 수신 길이·patch_count·HDMA 종료/길이를 검사하고, 기존 malformed packet은 거부한다. raw0과 raw>0 전환을 모두 처리한다.
2. 초기 forced blank에서 정적 raw map 두 개를 VRAM A7000/Bb000에 준비한다. 첫32 map entry는 각각tile320/832부터이며 raw CHR 목적지는 A5000/B9000이다. 일반 BG/OBJ/map 영역과 충돌시키지 않는다. 아직 배포 boot 코드에 추가하지 않았다.
3. 현재 표시 중인 뱅크의 raw CHR를 도중에 덮지 않는다. 비표시 뱅크를 준비하고 최종 vblank에서 palette/OAM, raw 여부에 맞는3HDMA, 실제뱅크/scroll/window를 함께 적용한다. 모든 전송·대기 중 STOP/패드·시간 처리를 유지하고, 실제 표시 완료 뒤에만 성공 ACK를 반환한다. 기존 raw 화면→일반 화면 전환에서도 남은 mode3/window 상태를 정리한다.
4. 부트ROM4096바이트·WRAM metadata·HDMA 동작 중 source 소유권을 확인한다. 필요한 최소 실제 packet/ACK/STOP 결합 시험 후 실제 보드 color/emphasis/frame181/export181 배선, ARM 전체 stack와 단일 변경 FIT/타이밍 승인을 거쳐 SMB3 숫자1→A 실기로 간다.
5. 영상 정지 해결과 전송 속도는 별도다. 앞 단계 최대7행 wire 모델53ms와 반복 table 전송 비용은 여전히 미해결이다. raw 묶음 전송·차분/base-generation/최종ACK 개선을 유지하며, 프레임 수/60초를 실측 FPS로 오인하지 않는다.

새 실기 FW/FPGA/ZIP은 없다. GBC·164 복구판·180 배포본·세이브 SRAM과 완료된 근거를 유지한다. 동일180/044·완료된 독립 PPU 시험·긴 부팅을 반복하지 않는다. [검증](../analysis/consume181-verification.json) · [인계](../cores/nes/HANDOFF.ko.md).
