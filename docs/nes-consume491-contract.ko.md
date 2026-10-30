# NES491 — 반복 복원과 실제 공급 경계의 조회 통합

PR137 merge `29815faa3887a035091e3169ffa0f751dda3de44`가 origin/master에 도달한 것을 확인하고 `codex/nes-consume-schedule-491`에서 시작했다. 현재 실기는 [MMC489/수신490](nes-hardware490-results.ko.md)의9.60fps·실행/메뉴 복귀 정상이다. 새 후보의 물리 FPS는 없다.

## 교체 경계

489 프로토콜·raw 단일 복원·bank 인증·독립 검사·STOP·최종ACK·VBlank를 유지한다. 새 ABI/버퍼/매퍼/속도/credit 수 변경은 없다.

- ARM의 local plan append는 여전히 guard를 실행한다. 첫 BG는 바로 flush하고,15개/240B 경계와 finish/END에서도 실제 E8 공급·E0 소비 확인을 한다. local buffer에만 추가한 뒤 매번 하던 E8 조회를 삭제했다. bulk pending/tombstone·동일 token 불변성·실제 ACK·EA retire 검사는 그대로다. Guard/오류를 무시하거나 진행 여부를 캐시하지 않는다.
- 65816의2byte word 반복은 encoded 두 byte를 먼저 모두 읽어 WRAM candidate에 seed한다. 같은 byte 단어는 fixed-source DMA,서로 다른 byte는 forward overlap MVN으로 복원한다. seed2B 뒤와 매64B 이하마다 서비스/STOP을 확인한다. MVN의 DBR 변경은 저장·복원한다.
- 기존 DP scratch60..66/7A만 사용한다. WRAM port는 packet 시작마다 다시 설정하며 이전 표시 VRAM을 수정하지 않는다. CRC/bitmap coverage·순서·길이·manifest·HDMA 의미검사·최종 표시 ACK를 생략하지 않는다. 단위 시험의 내부 길이2B는 외부 packet의 최소 길이 검사를 넓힌 것이 아니다.

## 검증된 범위와 비용

실제 linked M4의 기존12 ownership/credit/STOP/오래된 token/변조 ACK 거부와8 burst 경계2/5/14/15/16/29/30/61을 검증했다. E9 바이트·계획 순서는 이전과 같고,최종 display grant 없는 EA는 거부한다. fixture61개에서 E8은268→236회다. endpoint 지연은 명령-clock fixture이며 실제 ARM/SPI/ROM 시간으로 계산하지 않는다. 실제 M4의71개 canonical 상태/계획·serializer도 기존과 일치한다.

실제65816은108개 word/길이2..4096B/양 bank/부분 STOP 단위 시험을 통과했다. 고정71개 입력의 전체 픽셀·raw VRAM·VBlank·최종ACK가 기존과 같으며 같은 masterclock3000000 시작에서 **3903.397→3620.517ms,282.880ms/7.25% 감소**다.12개 비교는49.91ms 절감,시작+4ms는33.28ms 절감이다. VBlank 위상 효과가 섞여 있어 둘을 순수 복원 CPU 비용으로 해석하지 않는다. reset/초기오염부터도813.733→763.822ms로 줄었다. 입력/패킷 SHA와 기존 경로 baseline의71개 완료 시각이 모두 일치한다.

기존 버전/count/길이/mode 거부5종과 복원/low-DMA/final STOP,2→1행 변경으로 clear를 실제 발생시킨 STOP3종을 확인했다. constant2행에서는 cache 덕분에 clear가 발생하지 않으므로 stop_clear를 그 입력에 걸어 성공했다고 표시하지 않는다.

whole Quartus Lite는 **15272LE/14078comb/8392FF/264800logicalbits/51M9K**로489와 같다.136LE·5M9K 여유,관련 구현 setup+0.183/hold+0.168ns,nominal+0.224/+0.168ns다. full compile1회만 수행했고 source closure는 program ROM 내용만 바뀌었다. 새 timing 예외/seed loop는 없다. 전체 reset/CDC/IO는 계속 미승인이다.

ARM은 text202801/data10040/BSS18572B,firmware212844B·Flash148B 잔여다.489보다24B 작고 새 global RAM0B,RUN31848B는 같다. emit static stack32→16B이나 full stack/IRQ 증명은 아니다. SNES body4425B/program5120B,새 persistent/frame RAM0B다. program은 같아도 ROM 내용이 바뀌었으므로 matching whole FIT/관련 timing을 확인했다.

## 공동 실행과 판정

actual C/source·ROM/SPI RTL/65816/STOP 공동 실행을 통과했다. base/menu 코드는 변경하지 않았고491 실물 복귀는 아직 확인 전이다. 실제 NES 첫 프레임57344픽셀과34ACK·최종 표시·STOP을 확인했으며 이전489와 전체 화면 hash가 같다. 기능RPC의 quiet 호출은102→35였지만128us 배정과 물리 M4/IRQ 시계는 별개다. 5124개 코드/header/vector bus읽기·23위상·STOP도 통과했다. raw 결과의482 label은 기존 harness 선택자이며 실제 source closure/프로그램 hash는491이다. 기존 consumer 시험은 실제 IRQ/ROM과 공통 물리 시계를 사용하지 않으므로 위7.25%와 ARM query 수를 합친 실기 가속을 주장하지 않는다. 공동 실행 첫 프레임이 raw0인 기존 범위도 유지한다.

현재 후보는 개발 검증용으로 동결하고 기존489 설치본을 유지한다. 이번 단계만으로 새 사용자 설치본을 발행하지 않는다. 다음은 E8/E0 trace를 실제 source/ROM/65816 소비 시각과 한 일정에 연결하고 D0 source 대기를 비교하는 것이다. 전체 시간의 의미 있는 이득을 확인한 뒤 새 번호/marker/로그/원복을 갖춘 전달본을 준비한다.

## 재현·실패 보존

공개 레시피는 `nes_consume491.py`,ARM burst/ownership·65816 word 경계·joint wrapper와`analyze_nes_consume491.py`다. 기존489 원본/482 board closure·고정 입력·정당한 ROM/도구 의존성은 [재현 범위](../cores/nes/REPRODUCING.ko.md)를 따른다. 없는 private 입력을 다른 것으로 대체하지 않는다.

로컬 선택은 `probes/nes-consume491`의 candidate01/ARM01/client02/audit01/arm-bursts01,ASCII 실행 경로의 board01/snes05/units04/phase01/cold01/guards-snes01..02/transition01이다. 초안client01은 seed 뒤 서비스 누락으로66B 간격이어서client02로 교체했다. 초기 전통 eager-prefix assertion 실패·constant-row stop_clear fixture 실패·준비 전 working-directory 오류를 보존했다.

Mesen managed 리소스의 빈 native DLL 항목이 임시 DLL을0B로 덮는 원인을 소스에서 확인했다. exe/managed가 같은 정상 로컬 native DLL을 private portable 경로에 보존하고 hash를 기록했다. 기존227 baseline71개 시각이 정확히 일치한다. 라이선스 부족 문제가 아니며 Questa는 허가된 FLOAT1좌석으로 순차 실행한다. 원본 ROM/save/영상·원시 로그·도구·라이선스를 Git에 넣지 않는다.
