# NES185 — 마지막 표시 타일맵 재사용 후보

PR115 merge `fef83c723df7bf51b857add1bf96b9f8a3abf66b`에서 새 branch `codex/nes-map-inherit-185`로 진행했다. 이 변경은 **후보 구현과 결합 검증**이다. 전체 ARM 링크/RUN·IRQ 검사, ROM 갱신 ASM, 짝패키지와 실기 성능 승인은 아직 없다. 기존184ZIP을 교체하지 않는다.

## 작업 의미

변하지 않은 타일맵을 매번 MCU에서 SNES로 보내는 비용을 줄인다. 별도 이전 프레임 버퍼 없이 기존 MCU 계획 안의 4096B map을 보존하며 새 값을 정확히 비교한다. SNES에는 이미 마지막으로 표시한 WRAM 이미지가 있으므로, 같은 영역의 바이트를 새 후보 이미지로 복사한다. 화면 전송 구현이며 디버그 항목 추가가 아니다. 게임명·MMC3 전용 조건은 없다. 현재 변환기의 PPU/용량 지원 범위는 그대로다.

보관된 SMB3 frame12→frame15 타일맵은 64B 구역64개 중63개가 같다. 실제 C 전송기로 같은 frame15 전체 전송3952B 대비 재사용1214B, 약69.3% 감소했다. 같은 map의 재전송은1152B다. 이 수치는 **map 요청 header+payload**만 포함하며 CHR·음성·상태조회·SPI CRC·MCU/SNES 처리와 실제 FPS는 포함하지 않는다. 실제 첫레벨의 연속 프레임 계측도 아니다.

## 데이터와 소유권

- 새 `nes_native_video185_build(..., inherit, ...)`는 map만 보존하고 다른 작업 공간은 기존대로 초기화한다. 각 16bit map word를 덮어쓰기 전에 비교하여64bit dirty mask를 만든다. 그룹 감소·미사용 열은 명시적으로0으로 되돌린다. 첫 프레임은 전체 전송한다. 비교는 해시가 아니다.
- 런타임은 이전 sink의 표시 완료 이후에만 inherit를 요청한다. 이전 계획의 valid와 generation을 검사한다. sink는 그 기준 generation이 자신의 마지막 성공한 SEAL과 같아야 한다. 실패한 후보는 다시 기준으로 쓰지 않는다.
- `COPY6`: opcode6, section2, aligned offset, physical payload2B(base generation LE16), expanded64. 기존 sequence·serial32·current generation 검증과 section offset 연속성·4096B 범위를 그대로 통과해야 한다. SNES는 기존 표시가 있어야 하며 저장된 마지막 표시 generation과 payload가 같아야 한다.
- BEGIN이 선택한 WRAM 후보 bank는 마지막 표시 bank와0x8000 차이다. 검증된 목적 주소 XOR0x8000에서64B를 MVN으로 복사하며 DBR를 복원한다. 기존 VRAM bank/CHR/CGRAM/OAM/HDMA 비교·upload·최종 SEAL ACK는 유지한다. map이 같다고 CHR를 생략하지 않는다. raw 진입/해제도 기존 upload가 처리한다.
- 실패는 기존과 같이 terminal이며 COMMON reset 전 재시도하지 않는다. generation16 순환은 기존 serial32의 단조 증가와 마지막 성공한 SEAL 순서 안에서만 허용한다. 새 SEAL version은`1851`; 기존1815와 임의 혼용하지 않는다.
- COPY6는 기존 DATA 큐에서 보내며, FPGA의 opcode echo/완전한 ACK 검증 후 credit를 반환한다. FPGA RTL 변경은 없다. COPY 한 번은64B로 유한하며 다음 poll에서 STOP/pad를 서비스한다. **header를 읽기 전 STOP은 기존 quiet 경로여서 ACK가 없을 수 있다.** 이를 새 E4 ACK 보장으로 해석하지 않는다.
- 비용 계획은 기존 반복 압축과 비교하여 낮을 때만 재사용한다. 현재 비용 단위는 기존471/packet+payload 기반이며 queued transport의 실제 처리 시간을 최적화한 모델은 아니다. 성능 채택 시 패킷 수 증가를 반드시 함께 평가한다.

## 검증과 비용

선택: private `probes/nes-map185/build04`, `test07`, `objects03`, `selected-coupled`, `evidence/replay02`, `evidence/pad01`. [기계 판독 결과](../analysis/map185-verification.json).

- 실제 기존 C 변환기와 새 변환기의30개 연속 계획·BG/OBJ 바이트가 같다. raw 진입/해제, 그룹 증감, generation wrap, 초기 오염 메모리, dirty mask의 독립 비교를 포함한다. 전송 재구성·기준 불일치·invalid 계획을 더한37검사 통과. 이 단계 ACK는 mock이다.
- 실제 C sink/window와 실제65816 실행: reference7화면268ACK와 inherit7화면498ACK가 픽셀 단위로 같다. raw0/1/7 및 복귀 포함. 잘못된 base/alignment/size/section/expanded/token6종과 후보 upload 중 STOP에서 이전 화면을 유지했다. 전체 입력은 합성된 적법한 복잡한 map이며 전체 게임 실행은 아니다.
- 합성7화면 map 요청30688→14590B, map 패킷126→356개. 패킷 수 증가가 분명하다. 큐4개를 매번 한 번의 poll로 회수한다는 낙관적 SPI 하한은 전체7화면157.569→116.450ms다. CPU 처리·추가 poll·FPGA→MCU·capture 대기를 제외했으므로 이를60fps 달성으로 해석하지 않는다.
- 실제 C SPI/65816 ACK 사건을 기존 compact RTL·버스로 재생: 정상498ACK/89492검사, STOP121ACK/26912검사 통과. 새로운 실시간3프로세서 동시 성능 모델이 아니며 재생 ROM은 버스 검사용 기존 이미지다. 새 CPU 이미지는 앞의 실제65816 시험에서 검증했다.
- ARM 객체: video15888→15912B(+24), sink28→32B(+4). converter 자체 stack256→248B, seal144→152B, runtime step40B. wrapper16B. 객체 수치를 더해 전체 RUN 여유를 추정하지 않는다. **전체 링크·콜백 그래프·IRQ 여유 재계산이 필요하다.**
- pad185 수정 포함: actual autopoll240fields, 안정186표본의 오입력0. 전체 실기 컨트롤러/FPGA CDC 승인은 아니다. SNES body3776/3776B, compact4096B로 여유0. map 메타데이터2B, pad stack2B. 세이브 SRAM과 추가 FPGA 메모리는 사용하지 않는다.

build01은9B 초과, build02/test02는 indentation warning, test01은 sandbox623, test03은 부정 시험 base가 우연히 맞은 fixture, test05는 실패 후 계획 초기화 누락이었다. 모두 보존했다. objects01은 compiler 경로, objects02는 배열 인자 선언 warning, objects03 통과. build03→04는 C 배열 인자 선언만 통일했고 SNES body·ROM·sink/window 코드는 동일하다. coupled01의 마지막 early STOP은 기존 quiet/noACK로 fixture가 대기하여 제외; 그 앞8case는 완료 결과를 검증했다. coupled02는 COPY 후 upload 중 STOP을 검증했다. replay01 잘못된 소스 경로는 보존하고 replay02로 수정했다.

## 다음 실행 순서

1. 선택된184 full ARM source에 build04 변경을 결합하고 전체 링크/RUN·IRQ·정적 RAM을 확인한다. 새185 identity와 짝 SNES1851을 함께 사용한다. 객체만 통과한 현재 후보를 설치하지 않는다.
2. 기존184의 배치/RTL을 보존하여 SNES ROM MIF만 갱신하고 CDB/ASM·정확한 ROM/패키지 검사를 진행한다. RTL이 동일하므로 반복 FIT는 필요하지 않다. body 여유0을 지키며 unrelated 기능을 추가하지 않는다.
3. 최소 짝패키지 검사 후 SMB3 숫자1 타일+A로 실제 첫레벨, 화면/소리/메뉴 복귀를 확인한다. pad 수정도 함께 확인하고 별도pad-only/동일184/044 재시험은 요청하지 않는다.
4. 60fps는 여전히 목표다. map만으로 충분하다고 가정하지 말고, 패킷 수를 줄이는 연속 재사용 표현·CHR/나머지 payload 차등·capture/전송/표시 수명 겹침을 실제 receive/build/seal 시간과 함께 판단한다. 기존 RLE/CHR 배치를 다시 구현하지 않는다.

GBC164, 기존184 배포판, save SRAM, 완료 archive는 보존한다. 사운드·연속 화면 우선, 이후 장기 플레이/오류·reset 로그/입력 유지 품질 순서와 MMC4/5·state·mute·frameskip 확장 요구를 유지한다.
