# NES186 고정256바이트 타일맵 복사

185 실기에서 전체 SPI 바이트는4.49% 줄었지만 표시 큐 패킷이58.36% 늘었고 평균 표시 완료율은 비슷했다. 작은 COPY 요청 비용을 줄이기 위해 기존 COPY6의 고정 단위를64→256바이트로 바꿨다. 가변 길이 명령을 추가하지 않아 SNES body는3776/3776바이트 그대로다. 프로토콜은1861로 구분한다.

## 구현과 제한

기존64개 dirty bit와 제자리 비교는 그대로다. 인접4개 bit가 모두0인256바이트 그룹만 직전 표시 WRAM에서 복사한다. 하나라도 바뀌면 해당 그룹은 기존 literal/RLE span으로 전송한다. 연속 dirty 그룹은 기존 span 계획기로 합친다. 전체 전송이 더 저렴하면 기존 경로를 선택한다. 전체 map이 같으면64개 대신16개 복사 요청이다.

수신기는 MAP section·물리2바이트 payload·expanded256·offset256 정렬·기준 표시 generation·세션 serial/sequence·구간 연속성과 범위를 검증한다. 마지막 그룹은3840..4095이다. 비활성 WRAM의 대상 주소와 반대 bank의 동일 오프셋을 사용한다. 추가 RAM/FPGA RTL/세이브 SRAM 사용은 없다. CHR·raw 전환·최종 표시 ACK 소유권은 기존 계약을 유지한다.

SNES body 변경은7바이트 상수뿐이다. 길이64→256, 정렬mask63→255, MVN count63→255, SEAL1851→1861이다. 모든 label 주소가 같고 입력 service·SPC·VRAM upload 코드 바이트는 유지한다. COPY 한 명령 안에서는 최대256바이트를 복사한 뒤 다음 poll에서 service한다. 이를 기존64바이트 repeat service와 혼동하지 않는다. 무제한 복사나 가변 장문 복사로 바꾸지 않았고, 실제 실기의 최대 응답 시간은 측정하지 않았다.

## 검증과 효과

- 실제 C101검사: 기존 변환 결과30차등계획, raw/normal·세대 wrap·기준 불일치 외에 모든64개 dirty 위치가 해당256바이트 그룹의 복사를 막는지 확인했다. 나머지15그룹의 복사와 재구성4096바이트가 일치한다.
- 실제 C/window+65816:7화면이185의 전체 전송 reference 픽셀과 일치. 잘못된 base/alignment/size/section/expanded/token6종과 upload 중 STOP에서 이전 화면 유지. 추가로 offset64와 옛expanded64 요청을 거부한다.
- 동일 합성7화면의 전체 요청498→259, map 요청356→117, map 요청 바이트14590→10478. COPY319→79. 파일 전달 모델이며 CPU·MCU 동시 주기 모델이나 실제 FPS 측정이 아니다.
- 보관 SMB3 frame12→15 map은185의64요청/1214바이트에서17요청/558바이트. 같은 map 반복은16요청/288바이트. 이 수치를 게임 전체 FPS 개선율로 해석하지 않는다.

생산 MCU 변경은 sink 하나와186 파일명뿐이다. FPGA 큐·버스·패드CDC·전송 길이18바이트·CRC 경로는 같아 이전 큐 검증을 재사용하고 불변 RTL replay/FIT는 반복하지 않는다. 새 SNES 실행 경로는 실제 C/65816 결합 검사로 확인했다. 기존 실제 자동 패드 읽기 검증은 service 바이트 동일성으로 연결하며 실기 입력 품질은 이전185 사용자 관측 범위를 유지한다.

private `probes/nes-copy186`의 build01/test01/coupled03 및 추가경계 coupled04를 선택한다. coupled01은 이전 literal 프로토콜 fixture, coupled02는 normal 사례 없는 fixture 경로라 실행 전 실패했으며 보존했다. 완료 증거는 수정하지 않는다.

전체 ARM/ROM-only 배포 검증 후 SMB3 첫 레벨에서 실기 비용을 확인한다. 수신28.19초 등 다른 큰 비용은 남아 있다. 한쪽만 고쳐60fps라고 주장하지 않고, 다음은 결과에 따라 CHR 중복·capture/수신/표시 직렬 처리 비용을 줄인다. GBC164·세이브 SRAM·MMC4/5/state/mute/frameskip·장기 플레이 요구를 보존한다.
