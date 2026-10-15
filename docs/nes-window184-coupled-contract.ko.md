# NES184 결합 검증과 실기 시험판

PR115의 기존 [큐 계약](nes-window184-contract.ko.md)을 이어서 실제 C와 실제 SNES1815 실행 코드의 결합을 검증했다. 초기 map01의 −0.258ns stricter budget 미달 때문에 바로 배포하지 않았다. ACK 저장 수명을 바꾼 compact 후보 한 번의 추가 FIT로 이 기준도 통과했다. **이 문서의 선택 후보와 짝지은 release01만 설치 가능**하며 초기183 이름의 compile-only 펌웨어는 배포하지 않는다.

## 작업 의미

4개 화면 패킷을 연속 전송하는 구현을 실제 화면 처리·중단 처리와 연결하고, 설치 가능한 MCU/FPGA 쌍으로 만든 단계다. 완료 ACK의 중복 96비트를 제거해 논리 사용량과 배치 부담을 줄였으며 ACK 검사 자체는 유지한다. 실기 FPS 향상은 아직 미확인이다.

## 바뀐 ACK 저장 계약

기존 `ack_work` 외에 별도로 유지하던 `completed_ack` 96비트를 제거했다. 다음 응답의 첫 바이트를 쓰면 ACK-valid만 내리고 retired credit은 유지한다. 다음 ACK 전체가 검증되면 ACK-valid를 다시 올린다. 각 E0의 152비트 스냅샷은 여전히 불변이다. 첫 ACK 쓰기와 스냅샷이 같은 edge에 일어나면 이전 완성 ACK/valid를 함께 잡으므로 부분 바이트가 노출되지 않는다.

MCU는 큐가 비기 전에는 소비 수만 사용하며, 완전히 비었을 때에는 마지막 실제 ACK까지 확인한다. 따라서 partial ACK 구간의 invalid 표시를 정상적으로 처리한다. fault 뒤 다음 패킷을 공개하지 않고 BEGIN/SEAL barrier, CRC/토큰/세대, COMMON reset과 STOP 계약도 유지한다. F7은 아직 배포 전 변경이므로 기존 배포 F6와 계속 구별된다. compact 생성기는 원본 RTL에서 이 저장 수명 변화만 재현한다.

## 선택 결과

private `probes/nes-window184-coupled/progress.json` 및 [검증 요약](../analysis/window184-coupled-verification.json)이 선택 기준이다.

| 검사 | 결과 |
| --- | --- |
| compact-test01 | normal/phase/wrap 각4182검사. 기존 큐 경계에 partial ACK-valid 해제·credit 유지·완전 drain 후 valid 복원 검사를 추가했다. |
| test03 실제 C+window+65816 | normal7화면219ACK, STOP-copy61ACK, STOP-long27ACK. 3경우 모두 큐 깊이4에 도달했다. CPU가 staging/VRAM/CGRAM/OAM/HDMA를 쓰고 실제 ACK를 만들었다. normal428288픽셀+중단2×61184픽셀 일치. |
| replay02 실제 RTL/bus | 위 C의 SPI 거래와 실제65816 packet/ACK 이벤트 순서를 그대로 재생. normal84161/STOP-copy23316/STOP-long10805검사. 정상219소비, STOP-copy60소비 후 오류, STOP-long26소비 후 오류이며 큐에 남은3개 후속 패킷은 공개하지 않았다. |
| status01 | 실제 RTL 바이트를 최종 C에서 재생해 조건별107실패 주입. CRC/identity 실패 때 진단을 유효한 새 상태로 갱신하지 않고 유효한 fault/status만 보존함을 확인했다. |
| compact-map01/route02 | 13466LE/939LAB/42M9K, 6602FF. 초기 map01보다121LE·96FF 감소, LAB/M9K 수는 동일. nominal과 stricter budget 모두 setup+0.315ns/hold+0.116ns. |
| 변경 배치의 경로 | CDC486행/held reply24행, OAM2220행 최저+0.187ns. 조건부 PSRAM 여유+4.654ns, SNES read envelope73.621ns, SPI reply163.303ns, native payload reset 음수0. 전기·PCB 측정이나 전체 MTBF/full IO signoff라는 뜻은 아니다. |
| arm01/check02 | 전체 펌웨어201392B, static26588/RUN37096/IRQ508/여유1232B. 두 진단 바이트는 구조체 padding에 들어가 상시 RAM이 추가 증가하지 않았다. |
| report01 | 실제 TXT formatter의 타입 최대값·pad16/history16 포함4003/4096바이트. 새 window 필드 존재와 옛 sink_io 필드 부재 확인. |

파일 기반 결합은 wall-clock 스케줄링을 사용한다. C가 실제 SNES 응답을 받았고 그 사건 순서의 RTL 일치도 확인했지만, CPU/MCU/FPGA를 동일 시간축으로 동시에 시뮬레이션한 성능 결과는 아니다. 기존 독립 큐 테스트의 동시 송수신/스냅샷 경계를 함께 사용한다. synthetic scene이며 실제 SMB3 실행·실기 FPS 증거가 아니다. poll 수1321/1265 등의 차이는 PC 스케줄링 영향이므로 속도 개선 수치로 쓰지 않는다.

test01은 sandbox GCC WinError623으로 실행 실패했다. test02는 초기 C/원본 큐의 결합, replay01도 원본 큐의 재생 기록이며 보존한다. check01은 전체 스택 계산 뒤 제거한 옛 `sink_io170=` 문자열을 요구하는 검사기 조건에서 실패했다. 새 형식의 존재와 옛 형식의 부재를 검증하도록 고친 check02가 선택 결과다. firmware bytes는 check01/02 사이에 바꾸지 않았다.

## 로그와 배포

`sink_window_schema=184`, error/sent/retired/flags/ack를 기록한다. error1은 호출 형식,2는 guard,3은 SPI transfer,4는 상태 identity/CRC/flags/fault,5는 카운터·점유 일관성,6은 ACK-valid/초기 상태,7은 poll 한도,8은 최종 ACK 불일치다. sent/retired는 MCU 관측값이다. flags/ack는 마지막 CRC/F7 검증을 통과한 상태이며 첫 오류의 순간 값이 아닐 수 있다. ACK-valid가 없으면 ack 필드는0이다. 기존 sink_trace는 BEGIN/SEAL barrier 실패를 보조하지만 모든 queued DATA의 오류 ACK를 직접 보존하지 않는다.

ZIP `NES184-SMB3-WINDOW-VIDEO.zip` SHA256 `68a4310f9c67e27e944d2da9fe9e1f46fad4506ecb8d04f14c35e1eded16f9bc`.
펌웨어 `da4c776ac2733aabea2dabdc58c3a1f668fa2bba70a11803e1d7660e7a6f549f`, FPGA `6e86b54c7821beae97c2bf7d786c689bce5e31d958b1cc275fe9e0db2450148b`.
ASM/CPF는 새 DB 복사본에서 수행했고 RBF 압축 왕복과 ZIP의 모든 파일/보존 파일 해시를 확인했다. 실제 설치·실기 통과는 아직 아니다. [실기 안내](nes-game184-ready.ko.md)에 따라 펌웨어와 FPGA를 함께 사용한다.

## 다음 작업

이번184를 SMB3 숫자1 타일→A에서 시험한다. 화면 끊김 변화, 화면만 멈추는지, 사운드/입력, 약60초 후 메뉴 복귀와 두TXT를 받는다. 같은183/044 복원·불변 FIT/boot 테스트는 반복하지 않는다. 결과가 오기 전 추가 seed/FIT 미세 조정은 하지 않는다.

이전 계산의 raw7 전송 하한18.667ms가 여전히16.7ms를 넘는다. 후속은 목적 bank 기준 세대 차등·raw map/CHR payload 감소·capture/전송/표시 겹침이다. 큐가 고장 나면 first window error/observed credit/실기 증상에서 시작하고 ACK 검사를 해제하지 않는다. GBC164/세이브 SRAM/완료 archives는 유지한다. AV60fps→장기 플레이와 오류/reset 시 로그→입력 유지, 이후 MMC4/5·state·mute·frameskip 여유 계획을 이어간다.
