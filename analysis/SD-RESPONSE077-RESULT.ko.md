# 077 — SD 쓰기 응답 종료와 후속 클록 보완

## 이번 결과

실제 C의 CMD24→512바이트 DATA→4개 lane CRC→카드 응답→busy 처리에서 두 반례를 재현하고 보완했다.

| 경계 | 기존 코드의 모형 결과 | 077 결과 |
| --- | --- | --- |
| CRC 상태 토큰의 종료 비트가0 | status010만 검사하여 성공 반환 | 종료 비트1을 검사하고 shared RESPONSE 오류 반환 |
| busy0/1/2클록 | 상태 토큰 종료 뒤6/6/7클록만 출력 후 반환 | 각각10/10/11클록 출력 후 반환 |

**두 응답 경계의 구현·호스트 검증·ARM 연결은 완료했다. 사용자의 0바이트 TXT 원인으로 확인한 것은 아니다.** 실기 카드가 실제로 잘못된 종료 비트를 보냈는지, 짧은 busy가 있었는지 관측하지 않았다. 따라서 실기 저장 오류 수정 완료/저장 성공으로 표시하지 않는다. 새 설치 패키지·074 재시험 요청은 없다.

## 근거와 실제 변경

[SanDisk SD Card Product Manual v2.2 §4.5, 인쇄p.4-28](https://www.openimpulse.com/blog/wp-content/uploads/wpsc/downloadables/SD-Card-Simplified-Specification.pdf)은 쓰기 CRC 상태 토큰 이후8클록을 제공하는 clock-control 조건을 기술한다. §4.12의 DATA 종료→두 전환 구간→start/status/end→busy 순서를 모형에 적용했다. 오래된 제조사 문서를 참조한 프로토콜 모형이며 사용자 카드의 제품·현대 규격 전체·전기 지연을 입증하지 않는다.

GPIO는 SET/CLEAR를 실제 상승·하강 전환으로 처리한다. 상태 start는 DATA 종료 후3번째 상승, 세 status 비트는4~6번째, end는7번째로 놓았다. busy가 없거나 이미 끝난 경우 기존 wait_busy의 후속4클록만으로는 참조 조건의8클록에 못 미쳤다. 함수 호출 횟수를 클록 수로 대신하지 않았다.

동결076에서 **sdnative.c와 VERSION만** 바꾼 별도 `NES-SD077-CF68` 후보를 만들었다. active 진단에서만 상태 종료 비트를 확인하고 wait_busy의 후속 클록을8개로 늘렸다. inactive 일반/GBC 경로는 기존4개와 기존 동작을 유지한다. 종료 비트 오류는 반환하고 재시도하지 않는다. busy의100tick/2,000,000poll 종료 조건과 shared fault/RESET·USB 보호를 완화하지 않았다.

후속8개는 상태 토큰 종료 이후 전체간격8개와 같은 표현이 아니다. 현재 코드에서는 최소 전체10개가 된다. 대기 함수를 다른 호출에서도 사용하므로 active CMD12 등에서 후속 클록이 늘어나는 영향은 보수적으로 남긴다.

## 실행 증거와 범위

- 실제 sdnative.c에서 명령 생성/전송, 응답검사, 데이터 쓰기, wait_busy, GPIO clock helper, single-block write helper를 전체 함수로 추출했다. 원본 고지를 유지한다. card/GPIO/시간과 변경하지 않은 ARM CRC assembly primitive는 C 모형이다. 원본 ARM CRC 자체를 호스트 실행했다는 뜻은 아니다.
- 기존·수정 각각43검사: 4종 payload×6 busy 길이의24경우, 손상 end1, 거부 토큰15, R1 CRC 오류1, busy 무한/정지tick 및 tick wrap2. 모든 payload nibble과4lane 직렬 CRC를 독립 bit accumulator로 확인했다. CRC 입력 함수와 lane monitor를 같은 packed-byte 구현으로 복제하지 않았다.
- 정상 모형의 CMD24 응답 종료→DATA 시작은075와 같은2클록이다. 이번 변경은 기존8클록 gap 가설을 수정했다고 주장하지 않는다.
- 실패 이후 두 번째 쓰기가 새 클록·명령을 발생시키지 않는지 확인했다. timeout은 실제 MCU 경과시간 보장이 아니라 모형의 tick/poll 한계 검증이다.
- end 검사 제거와 짧은 tail 복원2대조는 각각 해당 응답 거부 assertion과 tail>=8 assertion에서 실패했다. baseline의 반례 관측을 정상 프로토콜 적합 판정으로 오해하지 않는다.
- 최종 ARM180128바이트 SHA `179bff93a3f967f25abffe1f37562d112ffe740fb7f66b051e407339f88df420`. STM3 길이/본문CRC/077 ID, sdn_write→send_datablock→wait_busy 및 오류 helper→nes_diag_fail 호출을 확인했다. 기존 manual marker3/shared run1+branch2, READY/CF68 검사는 같은 새 ELF에서 통과했다. builder/OBJDIR069 명칭은 재사용 도구 이름이다.
- 최종 ARM 입력 sdnative.c는43검사 후보와 같은 SHA다. 076 메뉴 변경은 그대로이고 해당853검사 결과는 같은 소스의 과거 증거로 재사용한다. 새로853검사를 실행한 것은 아니다. RTL/Questa/Quartus/ASM/실기 실행은 없다.

run-01의 Windows DWORD 중복 컴파일 실패를 보존했다. 최초 ELF checker는 direct nes_diag_fail을 기대했으나 실제 helper/tail-call 경로를 확인하여 수정했다. 그 stderr는 터미널에서 받아 별도 설명으로 전사했고 원시 로그로 둔갑시키지 않는다. 원본 switch fallthrough 경고도 로그에 유지한다.

## 재현

비공개074 materialized source와 frozen076 archive, 명시한 컴파일러가 필요하다. 공개 clone만으로 원본 플랫폼/사용자 파일을 복원할 수 없다.

```text
python tools/nes_sd_response077.py --src <074-source/src> --gcc <gcc.exe> --out <new-edge-output>
python tools/nes_sd077_prepare.py --evidence076 <frozen076> --out <new077-source>
```

ARM은 기존 `tools/build_nes_cf68_mcu_arm.ps1`에077 source와 별도 경로의 해시 검증된 mini를 지정한다. 실제 테스트 폴더의run-03과arm-01.log를 대상으로 `tools/check_nes_sd077.py --source ... --tests ... --objdump ...`를 실행했다. 동결 검사는 `tools/verify_nes_sd077.py --evidence ...`를 사용한다.

## 남은 작업

보고서/FatFS의 할당·분할 쓰기·sync·readback 전체 세션과 실제 시간 예산을 새 SD 경계에 연결해야 한다. 현재 card 모형은 단일 CMD24 한 블록을 다루며 전체 SD카드/파일시스템/사용자 카드의 전기 특성을 모델링하지 않는다. HW002의 legacy CMD25/flush 성공이 bounded 보호 제거의 근거는 아니다.

0바이트 원인과 사용자에게 보이는 결과가 확보된 뒤에만 새 실기 진단을 제안한다. 반복074/LED 영상/분해/PC USB/같은 파일 재요청을 하지 않는다. 원본044 복원·메뉴/GBC·base 실제 호환성과 외부IO는 남아 있다. 077은 compile-only이며071 쌍과 혼합 설치하지 않는다. 준비도5완료6부분1미완료/071 설치 보류를 유지한다.
