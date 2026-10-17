# NES211 — 출력 버퍼별 타일 유지와 변경 맵 전달 후보

PR119는 `e0a9247`로 머지됐다. 새 branch `codex/nes-resident-slots-211`은 실제210 C 변환기의 타일 번호 배정과 갱신 선택을 바꾼다. **생산 SPI/65816 연결 전 후보**이며 실기용211 펌웨어/ZIP은 아직 없다. 관측기 추가가 아니라 재사용을 실제로 수행하는 C 구현과 출력 소비 계약이다.

## 작업 의미

기존191/210은 매 프레임 BG/OBJ 슬롯을 처음부터 배정했다. 화면에 같은 물리 패턴이 남아도 순서가 달라지면 번호와 맵이 바뀐다. 195 소비자는 슬롯0부터 연속으로 채운 전체 패턴을 요구하고, 현재65816은 WRAM 전수 비교 후 작은 변경은 활성VRAM, 큰 변경은 비활성VRAM으로 보낸다. 계획만 생략하면 빈 슬롯·오래된 반대편 버퍼를 읽게 된다.

211은 **슬롯 번호 유지 → 출력 버퍼별 내용 유효성 → 변경 타일만 생성 → 이전 버퍼에 누락된 맵 변경까지 전달 → 최종 표시 ACK에서 확정**을 하나로 구현한다. 60fps에 필요한 반복 작업 제거 단계다. 아직 수신 geometry 압축, 원래 NES 좌표를 이용한 순환 scroll-map, 실제65816 dirty 소비는 완료되지 않았다. 실기 속도 개선이나 다양한 매퍼의60fps를 주장하지 않는다.

## 구현과 불변 조건

- `nes_resident211.c/.h`: BG1024슬롯(0번은 빈 패턴), OBJ128슬롯. 일반 BG는 물리tag13bit, OBJ는 물리tag+행mask를 정확 비교한다. 해시만으로 동일성을 추정하지 않는다.
- 원래 video15912B의 임시64bit BG키/32bit OBJ키는 같은 프레임의 정확한 중복 제거에 그대로 사용한다. OBJ 검사와 raw patch가 이 공간을 재사용해도 별도 유지 테이블은 손상되지 않는다. 슬롯 검색은 현재/누적 사용 범위까지만 수행한다.
- 단순 BG만 프레임 간 유지한다. 비identity 행 변환·cross-tag 혼합은 기존대로 다시 생성한다. 그 변환을 지원하지 않는 것이 아니라 **재사용 대상으로 삼지 않는 것**이다.210의59.07% 모델은 일부 행 변환도 포함하므로211 실측 적중률로 옮겨 쓰면 안 된다.
- 두 출력 버퍼 각각의 유효 bit가 있다. 같은 키라도 이번 대상 버퍼에 없으면 반드시 쓴다. 새 키로 슬롯을 재배정하면 두 버퍼의 해당 유효 bit를 모두 지운다. 이미 현재 프레임에 참조된 슬롯은 퇴거하지 않는다. 현재 화면의 실제 메모리는 쓰지 않는다.
- 하나의 immutable CHR-ROM content epoch에서만 유효하다. epoch가 달라지면 모든 패턴 유효성을 무효화한다. CHR-RAM을 `immutable=false`로 호출하면 거절한다. 키가 같은데 내용이 바뀌는 경우를 허용하지 않는다. 이 인자는 향후 실제 loader/source 계약으로 검증하여 전달해야 한다.
- 콜백 성공은 비활성 대상에 패턴 쓰기를 완료했다는 의미이고 최종 표시 성공은 아니다. `prepare` 뒤 serial32/generation16/target bank/표시 여부가 일치하는 최종 ACK로만 `commit`한다. serial32 소진은 중단, generation16 wrap은 별도 serial로 구분한다.
- callback 실패·잘못된 ACK·수용량 초과는 세션을 fault로 잠근다. COMMON STOP/drain과 물리 소비자 재설정 전에는 새 BEGIN을 받지 않는다. 수정된 임시 버퍼를 기존 화면으로 확정하지 않는다.

## 맵: 마지막 표시와 다음 대상 버퍼를 구분

실제210의4096B 맵 비교와64B 그룹 dirty 표시를 사용한다. 슬롯 번호가 안정되면 같은 패턴을 참조하는 맵 단어도 유지된다. 추가 전체 맵 사본은 없다.

이전 표시와의 차이만 보내면 두 프레임 전 상태인 비활성 버퍼를 잘못 유지할 수 있다. 따라서 각 버퍼에64bit `map_stale`을 둔다. 새 프레임의 변경 그룹을 두 버퍼에 누적하고, 이번 대상의 누적 mask 전체를 보낸다. 표시 ACK 후 해당 대상의 mask만 지운다. A에서 바뀐 맵이 다음 B에서도 필요하지만 현재-vs-A 비교는0인 경계를 검사했다.

이것은 목적 버퍼를 고려한 맵 갱신이지 완성된 순환 scroll-map이 아니다. coarse scroll로 맵 단어가 이동하면 아직 여러 그룹을 갱신한다. source raster의 원래 좌표/row remap을 이용해 그 이동까지 줄이는 후속 계약이 남는다.

## 기존 FPGA를 활용하는 경계

193 collector의 `append_ok`는 같은 kind/다음 slot/2048B 조건을 만족할 때만 현재 묶음에 이어 붙이며, 불연속 슬롯은 SEAL 후 새 descriptor로 시작한다. 따라서 sparse slot 자체를 위해 큰 새 FPGA 캐시를 만들 필요는 없다. 이번에는 소스 검토만 했고 sparse 후보의 실제board SPI/RTL 합동 실행은 아직 하지 않았다.

현재193은 `END && !in_frame`을 오류로 처리한다. 이를 바꾸기 위한 RTL/FIT 반복 대신 **매 프레임 slot0 빈 타일16B를 먼저 보낸다**. 양쪽 버퍼가 준비된 동일 화면도 일반 타일0개+빈 타일1개를 보낸다. 기존 END/lease/retire 의미를 유지할 수 있는 계약이며 불필요한 전체 타일 재생성은 하지 않는다.

기존195 C/SNES의 `offset==next`와 `bg_count==bg_next` 검사를 단순 삭제해서는 안 된다. 새 sparse 소비자는 아래 조건을 모두 만족해야 한다.

1. BEGIN에서 세션·표시base·대상 bank를 확인하고, WRAM 대상과 VRAM 대상을 같은 bank로 고정한다. 현재 활성VRAM에 작은 diff를 바로 적용하는169 경로와 섞지 않는다. **211의항상교대 가정에 실제 소비자가 동의한 뒤에만 활성화한다.**
2. descriptor의token/generation/section/정렬/범위를 그대로 검사한다. 변경 범위는 비활성 WRAM에만 쓰고 같은 범위만 비활성 VRAM DMA 대상으로 등록한다. untouched 영역을 초기화하거나 전수 비교하지 않는다. map_stale 선택 그룹도 같은 방식으로 처리한다.
3. 패턴이 없는 슬롯은 OAM/map이 참조하지 않으며, 참조되는 슬롯은 대상 bank에 이미 유효하거나 이번 세대에서 실제로 쓴 슬롯이어야 한다. 예전의 연속 전체 길이 검사를 대체하는 coverage/기반 유효성 검사가 필요하다. `bg_count`는 이제 사용 수가 아니라 최대 주소+1일 수 있다.
4. palette/OAM/HDMA/raw는 기존 정확한 결과를 유지하고, 모든 필요한 DMA가 끝난 뒤 VBlank에서 표시 bank를 바꾼다. SNES가 낸 실제 최종 ACK를 확인한 다음211 commit과200 retire를 수행한다. transport consume은 표시 ACK를 대신하지 않는다.
5. sparse 순서 때문에193 chunk가 늘어날 수 있으므로 실제 E8/E9/E1/descriptor 수를 포함해 비교한다. 부분 전송·STOP·잘못된 bank/epoch/마지막 ACK를 실제 C+65816 경로에서 검사한다. 데이터가 줄었다는 이유로 모든 대기가 사라진다고 가정하지 않는다.

## 검증과 자원

선택 `test04/arm03`. [기계 판독 증거](../analysis/resident211-verification.json).

- 실제210 geometry planner를 재사용하여 수정하고, 실제186 reference converter와 대조했다. 일반/행변환/cross-tag/OBJ mask·rank/팔레트 분리/raw1·7행 등8종 장면을 반복하고 합성 스크롤96프레임을 포함했다.
- 정상/경계 준비 프레임129회, 참조되는 planar bytes4,234,944B 및 CGRAM/OAM 속성/HDMA/좌표/raw 자료가 일치했다. slot 번호가 달라질 수 있어 참조하는 내용으로 비교했다. 별도 게임CPU 실행이나 실제65816 픽셀 출력 시험은 아니다.
- 두 버퍼를 데운 동일 프레임은 일반 패턴 쓰기0, 빈 타일16B만 쓰고 맵 갱신0. generation wrap·epoch 변경·다른 대상 버퍼에 남은 이전 변경을 포함했다.
- 오류 경계11개: serial/generation/bank/표시ACK 오류, 중간 callback 실패, mutable 거절,serial 소진,prepare 전 commit,중복BEGIN,슬롯 포화,뒤처진 맵 버퍼. 실패 전에 보이던 modeled active bank가 보존됨을 확인했다.
- 합성 스크롤96프레임의 패턴 쓰기 **182784→5664B(-96.90%)**, 맵 쓰기 **393216→87040B(-77.86%)**. source patterns는 immutable fixture이며 실제 SMB3 스크롤 결과가 아니다. 직접 aperture/VRAM 자료량을 SPI 바이트로 합산하지 않는다. 이 수치만으로 FPS를 예측하지 않는다.
- ARM 상태3200B, 기존 video15912B 유지.210의RUN-only 관찰cache2560B를 교체하면 상태 증가640B. 이 상태를 상시 global로 추가하지 않는다. 기존 여유5744B에서 단순 차감한5104B는 **새 호출 경로·IRQ·패킷 버퍼 반영 전 계산**이며 full RUN 승인값이 아니다.
- ARM object: resident1536B+planner3288B, 기존planner3296B; data/BSS0. planner stack240→248B, slot 함수64B. 콜백 체인/guard/service/IRQ를 포함한 전체 stack 검사는 소비 연결 후 수행한다.
- test01은 Windows printf 형식/trace 의존성 누락으로 컴파일 실패, test02는 전체슬롯 검색판, test03은16B anchor 도입 전 중간판. arm01은 상대tool경로 때문에cc1 실행 실패, arm02는 anchor 전. 선택판은test04/arm03이며 이전 기록은 보존한다.

## 바로 다음 작업과 실기 기준

**동일 후보를 sparse C transport + 실제65816 dirty 소비로 연결하는 것이 다음 작업이다.** 새 캐시 microbenchmark나 새 상태 조회 실험을 반복하지 않는다. 현재4KiB SNES ROM 본문 여유1B는 부족하므로 더 이상 필요하지 않은 전수비교/전체후퇴 경로를 대체하는 방식으로 코드 예산을 먼저 확보한다. 단순 안전검사 삭제나 새8KiB ROM/FIT를 기본 해법으로 삼지 않는다.

연결 후 기존 정상/실패 경계와 full ARM 자원 검사를 하고 필요한 최소 board 변경만 확인해 실기판으로 간다. 수신 geometry/control 비용은 아직 줄지 않았으므로60fps 전체16.67ms 예산도 다시 계산한다. 실제 PSRAM 경쟁·SNES DMA/VBlank와cold 첫화면/steady 스크롤을 구분한다.

사용자는 다음 개선판에서 로딩 종료 직전부터 메뉴 복귀까지 영상을 찍기로 했다. 숫자1+A→첫 레벨 RIGHT+B/A를 가능한 만큼 진행하되 현재 끊김 때문에 동일210 연속주행을 재요구하지 않는다.210은 약6–7초 첫 레벨 진입/사망·스테이지선택 반복/**마지막약5초 첫레벨 내부**였다는 최종 정정을 유지한다.

저장 SRAM·GBC164·기존210배포·원본 ROM/이전 archive는 변경하지 않는다. MMC4/5는 fetch 당시 physical identity/내용 epoch/추가 변환을 보존해야 하며 추가 매퍼의 동작 검증은 아직 없다. state load/reset에서는 두 버퍼의 residency를 무효화하고, frameskip은 실제 표시한 bank만 ACK로 확정한다. mute는 오디오 경로로 별도 유지한다. 사운드와 약60fps 확보 후 장기 플레이·오류/리셋 로그·조작 품질 순서를 유지한다.
