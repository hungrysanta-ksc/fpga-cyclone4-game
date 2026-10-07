# 075 — 수신 파일의 실제 C 분류와 SD 쓰기 시작 경계

## 결론과 범위

**실제 메뉴를 현재 NES 복귀 조건이 거부하는 문제가 재현됐다.** 받은 메뉴는 `carttype=0x55`로 SRTC 기능을 사용한다. 기존 `carttype>2` 거부가 직접 원인이다. 이는 메뉴 복귀의 별도 문제이며, 메뉴를 실행하지 않는 073/074 수집기의 0바이트 TXT 원인이 아니다. 이번에는 호스트 조사와 재현 도구를 추가했고 제품 펌웨어는 수정하지 않았다.

파일 신원 확보·실제 C 메뉴 분류·베이스 압축 해제 대조·SD 쓰기 시작 클록 조사는 완료했다. **SD 저장 오류 해결, 실제 메뉴 복귀 수정 및 071 설치 준비는 미완료**다. 새 실기 패키지는 없다.

## 받은 자료

| 파일 | 확인 결과 |
| --- | --- |
| firmware.stm | 169056바이트. 기존 NES-H1-SAMPLING-044 SHA와 일치, STM3 본문 길이/CRC 통과. 사용자가 마지막 정상으로 보관한 파일이다. |
| firmware.stm.bak-hwTest | 125260바이트. HWINFO002-C44, 로컬 성공 빌드와 전체 바이트 일치, STM3 본문 CRC 통과. 사용자가 HW002000.TXT 쓰기 성공에 사용한 별도 진단 기준이다. |
| m3nu.bin | 65536바이트, CRC c014b571. 실제 C 결과: 헤더0xffb0, HiROM mapper0, map31/carttype55, ROM65536, SRAM8192, FEAT_SRTC, base FPGA 경로, SGB/EGBC 아님. |
| fpga_base.bi3 | 168440바이트, CRC7cd299cc. Python 복원과 고정069 실제 C 프로그래머의 출력214981바이트가 모두 일치. 복원 CRC3505d27a. 실제 FPGA DONE/파일 호환성은 미확인이다. |

전체 SHA는 [검증 메타](offline075-verification.json)에 있다. 원본과 실행 자료는 비공개 증거에 보존했다. `firmware.before-sdinfo072.stm`은 없으며 진단 파일을 그 이름으로 대체하지 않는다. 044 일반 복원 기준과 HWINFO002 TXT 성공 기준을 혼동하지 않는다. 이번 작업에서 사용자의 SD를 수정하거나 복원하지 않았다.

## 실행한 검사와 한계

- 메뉴: 실제 `smc_id` 전체와 `sgb_id` 전체를 호스트 컴파일하고, 실제 `memory.c`의 복귀 거부 식을 추출했다. 실물 파일 결과와 carttype 단독 변경 대조 3개를 통과했다. carttype만0으로 놓으면 거부가 사라진다. 이를 실제 파일 수정이나 승인으로 해석하지 않는다.
- 호스트 전용 분류 방어 실험15개: 선택 헤더/리셋 opcode의 짧은 읽기, 헤더 없음, SRAM 지수32 입력을 추가로 확인했다. 짧은 읽기의 sticky fault는 호스트 callback이 주입한다. 실제 FatFS/native 오류 전달과 일반 메뉴 승인 정책을 검증한 것이 아니며 펌웨어에 적용하지 않았다.
- SD: 실제 `send_command_fast`, `send_datablock`과 네 GPIO 클록 함수를 그대로 추출했다. SET/CLEAR를 실제 상승·하강으로 모델링했고 장벽/명령 실행 시간은 모델링하지 않았다. CMD24/25, 초기 클록0/1, 응답 지연1/2/8/64, 추가 클록0/8의32조합을 검사했다. 데이터 시작의 첫 상승 에지에서 중단하므로 DATA 본문/CRC 상태/busy/전기 타이밍 시험이 아니다. CMD25는 현재 함수에 명령만 바꾼 대조이며 과거 펌웨어 전체 실행이 아니다.
- 현재 CMD24 경로는 응답 종료 비트의 상승 에지부터 DATA 시작 상승 에지까지2클록, 추가8클록 대조는10클록이다. 따라서 “추가8클록 누락 자체가 규격 위반”이라는 가설은 이 모형으로 입증되지 않는다. [SanDisk Product Manual v2.2, 표4-24, 인쇄 p.4-46](https://www.openimpulse.com/blog/wp-content/uploads/wpsc/downloadables/SD-Card-Simplified-Specification.pdf)은 NWR 최소2클록을 제시한다. 이 오래된 제조사 문서는 사용자 카드의 신원·현대 카드 전체 규격·전기 타이밍 보증이 아니다.
- 베이스: 기존 고정069 실제 C 프로그래머를 새 파일에 실행하여 전체214981바이트와 오류 대조13개를 확인했다. FatFS/FPGA 핀은 모형이다. 복원 크기가071 진단 RBF510856과 다르다는 사실만으로 호환 또는 손상을 판단하지 않는다. 기존 정상044와의 파일 대응 및 실제 FPGA 구성 완료는 다음 확인 대상이다.

최초 메뉴 빌드는 원본 SGB switch의 의도된 fallthrough 경고를 `-Werror`가 거부했다. 원본 코드는 유지하고 해당 경고만 오류 승격에서 제외했다. 경고와 실패 로그를 보존했다. SD 원본 switch도 같은 경고1개를 남긴다. ARM/Questa/Quartus/새 물리 시험은 실행하지 않았다. 기존044–074 증거와 제품/GBC 소스는 변경하지 않았다.

## 재현

공개 clone만으로 원본 사용자 파일·플랫폼·고정069 비공개 증거를 얻을 수는 없다. 각 경로는 해당 입력의 별도 사본을 지정하며 새 출력 디렉터리를 사용한다.

```text
python tools/nes_offline_menu075.py --platform <074-source/src> --menu <m3nu.bin> --gcc <gcc.exe> --out <new-menu-out>
python tools/nes_offline_sd075.py --source <074-source/src/stm32f4xx/sdnative.c> --gcc <gcc.exe> --out <new-sd-out>
python tools/nes_cf68_pair_programmer.py --mcu-evidence <frozen069> --packed <fpga_base.bi3> --raw <Python-decoded-base> --gcc <gcc.exe> --out <new-base-out>
python tools/verify_nes_offline075.py --evidence <frozen075>
```

## 다음 작업과 완료 조건

1. 메뉴는 확인된 SRTC/base 구성을 제한적으로 지원하는 새 승인 정책과 실제 분류 IO 오류 처리를 설계한다. 단순히 carttype 제한을 삭제하지 않는다. 실제 메뉴·지원하지 않는 copro·짧은 읽기·잘못된 크기 대조를 실제 호출 경로에 연결하고 ARM 호출·메뉴 버퍼 검증·RESET 복귀를 확인한다.
2. SD는 성공 HW002의 legacy CMD25/flush CMD12와 현재 CMD24/응답 검증/유한 예산 차이를 계속 분리한다. 다음은 실제 DATA CRC 응답 샘플·busy·FatFS 할당/보고서 분할 경계의 인과 대조다. 단순 gap 연장·CRC 완화·무제한 legacy fallback을 수정으로 내놓지 않는다.
3. 사용자에게 보이는 결과가 확보된 뒤에만 새 실기 패키지를 준비한다. 반복074·LED 영상·기판 분해·PC USB·이미 받은 파일을 다시 요구하지 않는다. 비어 있지 않은 TXT 검증, 독립 원본 복원, 메뉴/GBC 재진입, 외부 IO 조건이 남아 있다. 071 설치 불가와 준비도5완료/6부분/1미완료는 유지한다.
