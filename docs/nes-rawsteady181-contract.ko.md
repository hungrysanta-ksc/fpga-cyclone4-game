# NES1814 — raw 행의 지속적인 부분 갱신

## 작업 의미와 결과

raw 행이 포함됐다는 이유만으로 매번 반대 VRAM 뱅크를 전체 복사하던 SNES 경로를 바꿨다. **직전 표시 화면과 raw 행 수가 같으면 기존 WRAM 비교를 사용하고, 필요한 변경이 기존 5,000 예산에 들어갈 때 현재 표시 뱅크에 적용한다.** 행 수가 달라지거나 변경량/명령 수가 한도를 넘으면 기존 비표시 뱅크 복사를 사용한다. 형식은 DATA2/4·SEAL1814 그대로다.

같은 7행의 색상 변경 fixture에서 이전 네 번의 비표시 뱅크 복사가 없어졌다. 영상 DMA는 raw CHR 2,048B 한 건이며 HDMA 포인터 설정과 함께 다음 fresh VBlank에서 공개했다. 양쪽 VRAM 뱅크 모두 실제65816/PPU 기준 영상과 일치했다. 같은 화면을 다시 받으면 DMA 명령0, raw 위치/배경·OBJ가 함께 달라지는 작은 변경도 부분 갱신했다. 큰 변경은 기존 최대7회 복사로 돌아간다.

이것은 **지속적인 화면 표시를 위한 실제 구현 변경**이다. 전송량 감소나 실제60fps 측정 결과는 아니다. MCU→SNES wire는 이전 sinkpack181과 같고, 여전히 모든 section을 받는다. 합성7frame의 전체 요청을 재대조해 logical DATA50,217B가 동일함을 확인했다. 모델 한 방향 normal15.270ms/raw26.694ms라는 전송 병목도 그대로다.

## 정확성·자원·수명

| 자원 | 기준/용도 | 이번 변경 |
|---|---|---|
| SNES WRAM7F 두 slot | 마지막 display ACK 화면과 새 candidate | 기존 배치 유지; 표시 중인 HDMA source를 덮지 않음 |
| WRAM1022/1024 | 직전 표시 base/유효 여부 | ACK 전후 기존 retire 순서 유지 |
| WRAM1032 | 실제 현재 VRAM 뱅크 | local diff는 이 뱅크 기준; 전체 복사 성공 시 기존 flip |
| WRAM1240/1242 | candidate/마지막 표시 raw 행 수 | 같을 때만 새 비교 경로 허용. 동일 내용으로 간주하지 않음 |
| DP40..6F | section/compare scratch | 기존 scratch 재사용; 일곱 번째 비교 region 추가 |
| raw CHR | candidate base+6961, 항상2,048B | 실제 byte 비교 후 변경 시 한 DMA, 목적지 A5000/B9000 |
| MCU receiver/video/sink | 기존 구조체·수명 | 변경 없음. 추가16KiB plan/이전 frame cache 없음 |
| cartridge save SRAM | 다른 게임 저장 데이터 | 사용하지 않음 |

raw 행 수가 같아도 위치·색·마스크·배경·OBJ가 다를 수 있다. 여섯 기존 section과 raw CHR를 모두 실제 byte로 비교한다. raw의 세 HDMA 표는 기존 validate181 검사 후에만 공개한다. 동일 행 수/해시만으로 데이터를 같다고 취급하지 않는다. raw 진입/이탈과 행 수 변경은 보수적으로 전체 재구성을 유지했다.

HDMA bundle3,418B는 이미 WRAM에 있고 VBlank에 다시 복사하지 않는다. 기존 budget에 이 전체 길이를 더하면 raw CHR를 중복 계산하고 작은 변경도 거절한다. 이번에는 HDMA 명령의 setup96만 부과하고 실제 raw CHR DMA를 별도로 부과한다. fixture의 raw2,048+명령2×96=2,240이다. 데이터가 다른 BG/OBJ/map/CGRAM/OAM의 길이와 명령 비용은 기존대로 남는다. 예산5,000과 명령32개 한도는 올리지 않았다. 이 비용은 기존 admission 모델이며 실제60fps/모든 장면의 VBlank 시간 보증을 뜻하지 않는다; 시험에서는 실제 PPU 쓰기가 VBlank 안인지 확인한다.

부분 비교는 기존64B 단위 service를 유지한다. 변경이 첫 byte에서 발견되는 raw region은 즉시 whole command로 끝나므로 그 region 안에서 service가 실행되지 않을 수 있다. 이런 경우에도 upload의 serviced fresh VBlank 대기와 공개 전 STOP 검사는 유지한다. STOP/실패 후에는 현재 sink를 계속 사용하지 않는 기존 종료 계약이다. 향후 강제로드는 새 전송 epoch와 완전갱신이 필요하며, 오래된 WRAM/delta/ACK를 이어 사용하면 안 된다.

## 코드 공간

추가 비교 코드를 그대로 넣으면 본문3,822B로 기존3,776B 한도를 넘는다. 새 저장 영역이나 부팅 ROM 크기 확장 대신, assembler가 명시적인 JMP 지점만 짧은 상대분기로 완화하도록 했다. `emit(반대조건,3)+JMP`는 같은 조건의 상대분기로, 가까운 단순 JMP는 BRA로 바꾼다. JSR·기존 수동분기·일반 byte stream은 변환하지 않는다.

각 pass는 코드·table 주소를 처음부터 다시 생성한다. 이미 줄인 지점은 유지하고 추가로 가능한 지점만 줄인다. 최종 모든 분기 거리를 Asm.finish에서 다시 검사한다. 본문3,822→3,574→3,560B, 짧아진 jump104곳, 총262B 절약이다. 최종 program4,096B, 본문 여유216B다. 중간 pass00의 oversized ROM은 선택/실행/배포용이 아니며 최종 루트 산출물만 사용한다. 최종3,776B 제한도 다시 검사한다.

MCU C 후보는 sinkpack181과 byte-identical이므로 이번 변경의 ARM stack 증가분은 없다. 앞선 ingress1813/sink1814 전체 ARM 재링크·IRQ 여유 검사는 여전히 필요하다. 이 SNES 변경으로 FPGA 배선 타이밍이 해결됐다고 주장하지 않는다.

## 검증과 실패 이력

실제 C sink→held file mailbox→실제65816→DMA/PPU→실제 ACK 경로를 사용한다. mailbox/pad/SPC 경계만 모델링하며 WRAM/PPU 쓰기나 ACK를 주입하지 않는다. 모든 DATA의 ACK 시점에 실제 WRAM bytes를 검사하고, 완료 장면은 전체256×239 기준 영상과 비교한다. ACK 횟수는 FPS가 아니다.

선택 근거는 test02/normal, test03/steady, test04/large_steady, test05의 나머지16경우다. 앞3개 디렉터리의 전체 suite 성공을 주장하지 않고 완료된 개별 case만 선택한다. 최종 C/ROM byte 동일성과 개별 producer/consumer PASS·기준영상을 check01에서 재대조했다. 총19경우, 실제 ACK2,764개, 완료45장면·2,753,280픽셀이 통과했다. 잘못된 버전/표/행 수, DATA4 길이·section·offset·token 오류, 기존 copy/final STOP과 새 raw 비교/final STOP을 포함한다. 상세 수치는 [검증 데이터](../analysis/rawsteady181-verification.json)에 기록한다.

- build01: generator 중첩 import 문자열의 줄바꿈 오류. build02: CLI `__main__`과 import된 assembler class가 달라 pass 정보를 못 찾음. build03에서 수정; 제품 동작 오류로 해석하지 않는다.
- test01: sandbox GCC WinError623으로 컴파일 전 실패. 기존 host 실행 경로 사용.
- test03/steady는 통과. 이어진 large_steady의 불필요한10장면이 emulator50초 한도에 걸렸다. 실제 제품 timeout을 늘리지 않고 큰 변경 확인에 필요한6장면으로 줄였다. test04/large_steady가 통과했다.
- test04/stop_steady는 첫 byte가 달라 raw 비교 service 지점에 도달하지 않는 fixture여서 STOP 주입이 일어나지 않았다. test05는 동일 raw 비교의64B service 지점에서 STOP을 주입하고, 변경 raw는 final STOP으로 별도 검사한다. 생산 C/ROM은 바뀌지 않았다.

## 다음 경계

1. 이번 raw 지속 갱신을 재구현하지 않는다. 남은 전송 병목은 모든 section 송신과 capture/export 단일 lease다. 추가 ARM frame copy 없이 wire 감소를 진행하며, 실제 표시/대상 bank의 기준 세대와 보관 위치를 명시한다. 손실 없는 packet 구간 압축과 이전 frame delta를 구분하고 hash만으로 동일성을 단정하지 않는다.
2. source identity/dirty 수명·프레임 생략·강제로드 후 기준 무효화, capture/export 겹침과 host RUN/STOP 소유권을 함께 유지한다. 같은PLL 타이밍을 false path로 숨기지 않는다.
3. 변경된 구간의 최소 검사 후 전체 ARM/IRQ 및 정당한 통합 FIT/조건부IO를 통과시켜 SMB3 숫자1 타일+A 실기로 간다. 단순 합성시험 확대만 반복하지 않는다. 정상 약60fps+음성→장기플레이/오류·리셋로그→입력유지 순서를 유지한다.

새 펌웨어/ZIP/실기 승인 없음. 배포180/GBC164/저장 데이터와 기존 완료 archives는 보존한다. 재현 도구: `nes_rawsteady181.py`, `test_nes_rawsteady181.py`, `check_nes_rawsteady181.py`.
